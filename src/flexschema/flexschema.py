import re
import json
import uuid
import logging
import sqlite3
import pymongo

from datetime import datetime, timezone
from typing import Any, Callable, Optional, Type


logging.basicConfig(level=logging.INFO)
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("sqlite3").setLevel(logging.WARNING)


class SchemaDefinitionException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        logging.getLogger("flexschema").error(message)

    @staticmethod
    def silent_log(message: str):
        logging.getLogger("flexschema").info(message)


class FlexmodelException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        logging.getLogger("flexmodel").error(message)

    @staticmethod
    def silent_log(message: str):
        logging.getLogger("flexmodel").info(message)


class Schema:
    def __init__(self, **fields: "Schema.Field"):
        self.fields: dict[str, Schema.Field] = {}

        for name, field in fields.items():
            self.add_field(name, field)

    def __getitem__(self, name: str) -> "Schema.Field":
        return self.fields.get(name, Schema.Field(str))

    def __iter__(self):
        for item in self.fields.items():
            yield item

    @staticmethod
    def ident(**fields: "Schema.Field") -> "Schema":
        return Schema(
            _id=Schema.Field(str, default=str(uuid.uuid4())),
            _updated_at=Schema.Field(str, default=datetime.now(timezone.utc).isoformat()),
            **fields,
        )

    def is_submittable(self, data: dict[str, Any]) -> bool:
        for name, field in self.fields.items():
            item = data.get(name, field.default)

            if hasattr(item, "schema") and isinstance(item.schema, Schema):
                if not item.schema.is_submittable(item.__dict__):
                    return False
            elif not field.is_valuable(item):
                return False

        return True

    def add_field(self, name: str, field: "Schema.Field"):
        if not isinstance(field.type, type):
            raise SchemaDefinitionException(f"Field '{name}': has not a valid type.")

        # Check if type is a primitive or a subclass of Flex
        is_valid_type = field.type in (str, int, float, bool, list, tuple) or (hasattr(field.type, "__mro__") and any(base.__name__ == "Flex" for base in field.type.__mro__))

        if not is_valid_type:
            raise SchemaDefinitionException(f"Field '{name}': has not a valid type '{field.type.__name__}'.")

        if field.type in (list, tuple) and field.constraint and field.constraint.item_type is None:
            raise SchemaDefinitionException(f"Field '{name}': type 'list' must have a 'constraint.item_type' defined.")

        if field.default is not None and not isinstance(field.default, field.type):
            raise SchemaDefinitionException(f"Field '{name}': default value must be of type '{field.type.__name__}' or None. Got '{type(field.default).__name__}' instead.")

        if isinstance(field.nullable, int) and field.nullable < 0:
            raise SchemaDefinitionException(f"Field '{name}': nullable must be a boolean or a positive integer.")

        if not isinstance(field.constraint, Schema.Field.Constraint):
            raise SchemaDefinitionException(f"Field '{name}': has not a valid constraint.")

        if field.constraint and field.constraint.pattern and field.type not in (int, float, str):
            raise SchemaDefinitionException(f"Field '{name}': 'constraint.pattern' works only on type of 'int', 'float', or 'str'.")

        if field.constraint and field.constraint.pattern:
            try:
                re.compile(field.constraint.pattern)
            except re.error:
                raise SchemaDefinitionException(f"Field '{name}': 'constraint.pattern' is not a valid ReGex: '{field.constraint.pattern}'.")

        if field.callback and not callable(field.callback):
            raise SchemaDefinitionException(f"Field '{name}': has not a valid 'constraint.callback'.")

        field.name = name
        self.fields[name] = field

    class Field:
        def __init__(
            self,
            _type: Type,
            *,
            default: Any = None,
            nullable: bool | int = True,
            callback: Optional[Callable[[Any], Any]] = None,
            constraint: Optional["Schema.Field.Constraint"] = None,
        ):
            self.name: str = ""
            self.type: Type = _type
            self.default: Any = default
            self.nullable: bool | int = nullable
            self.callback: Optional[Callable[[Any], Any]] = callback
            self.constraint: Schema.Field.Constraint = Schema.Field.Constraint() if not constraint else constraint

        def is_valuable(self, value: Any) -> bool:
            return False if self.evaluate(value) else True

        def evaluate(self, value: Any) -> Optional[str]:
            if self.nullable and value is None:
                return
            elif not self.nullable and value is None:
                return f"Field '{self.name}': is required and cannot be null."

            if not isinstance(value, self.type):
                return f"Field '{self.name}': must be of type {self.type.__name__}, got '{type(value).__name__}' instead."

            if self.type is list and self.constraint and self.constraint.item_type:
                for i, item in enumerate(value):
                    if not isinstance(item, self.constraint.item_type):
                        return f"Field '{self.name}[{i}]': must be of type {self.constraint.item_type.__name__}, got {type(item).__name__}."

            if self.type in (str, list, tuple):
                length = len(value)
                suffix = "characters" if self.type is str else "items"

                if self.constraint.min_length and length < self.constraint.min_length:
                    return f"Field '{self.name}': must have at least: {self.constraint.min_length} {suffix}."

                if self.constraint.max_length and length > self.constraint.max_length:
                    return f"Field '{self.name}': must have at most: {self.constraint.max_length} {suffix}."
            elif self.type in (int, float):
                if self.constraint.min_length and self.constraint.min_length > 0 and value < self.constraint.min_length:
                    return f"Field '{self.name}': must be greater than or equal to: {self.constraint.min_length}."

                if self.constraint.max_length and self.constraint.max_length > 0 and value > self.constraint.max_length:
                    return f"Field '{self.name}': must be less than or equal to: {self.constraint.max_length}."

            if self.constraint.pattern and isinstance(value, str):
                import re

                if not re.match(self.constraint.pattern, value):
                    return f"Field '{self.name}': must match the pattern: '{self.constraint.pattern}'."

        class Constraint:
            def __init__(self, *, item_type: Optional[Type] = None, min_length: Optional[int] = None, max_length: Optional[int] = None, pattern: Optional[str] = None):
                self.item_type: Optional[Type] = item_type
                self.min_length: Optional[int] = min_length
                self.max_length: Optional[int] = max_length
                self.pattern: Optional[str] = pattern


class Flex:
    schema: Schema = Schema()

    def __init__(self, **data: Any):
        self.update(**data)

    def is_schematic(self) -> bool:
        return self.schema.is_submittable(self.__dict__)

    def update(self, **data: Any):
        for name, field in self.schema:
            value = data.get(name, self.__dict__.get(name, field.default))

            if issubclass(field.type, Flexmodel) and isinstance(value, dict) and (id := value.get("$id")):
                value = field.type.load(id)
            elif issubclass(field.type, Flex) and isinstance(value, dict):
                value = field.type().update(**value)

            self.__dict__[name] = value

        return self

    def evaluate(self) -> dict[str, Any]:
        messages: dict[str, Any] = {}

        for name, field in self.schema.fields.items():
            if e := field.evaluate(value := self.__dict__.get(name, field.default)):
                messages[name] = e

            if isinstance(value, (Flex, Flexmodel)):
                if len(e := value.evaluate()) > 0:
                    messages[name] = e

        return messages

    def to_dict(self, commit: bool = False) -> dict[str, Any]:
        def serialize(value, field: Optional[Schema.Field] = None):
            if commit and isinstance(value, Flexmodel) and hasattr(value, "id"):
                return {"$id": value.id}
            elif isinstance(value, Flex):
                value = value.to_dict()
            elif isinstance(value, list):
                value = [serialize(item) for item in value]
            elif isinstance(value, dict):
                value = {k: serialize(v) for k, v in value.items()}
            elif isinstance(value, object) and hasattr(value, "__dict__"):
                value = {k: serialize(v) for k, v in value.__dict__.items()}
            elif isinstance(value, datetime):
                value = value.isoformat()

            if field and callable(field.callback):
                value = field.callback(value)

            return value

        return {name: serialize(self.__dict__.get(name, field.default), field) for name, field in self.schema.fields.items()}

    def to_json(self, indent: int = 4, commit: bool = False) -> str:
        return json.dumps(self.to_dict(commit), indent=indent, ensure_ascii=False)


def _mongodb_to_sqlite_query(queries: dict[str, Any], table_name: str) -> tuple[str, list[Any]]:
    """
    Convert MongoDB-style queries to SQLite JSON queries.
    
    Supports:
    - Simple equality: {"name": "John"}
    - Comparison operators: {"age": {"$gt": 18}}
    - Logical operators: {"$or": [{"age": {"$lt": 18}}, {"age": {"$gt": 65}}]}
    - Array operators: {"status": {"$in": ["active", "pending"]}}
    - Existence operator: {"email": {"$exists": True}}
    
    Returns:
        tuple: (where_clause, params) for use in SQLite query
    """
    params = []
    conditions = []
    
    def process_value(key: str, value: Any, is_nested: bool = False) -> str:
        """Process a single key-value pair and return the SQL condition."""
        nonlocal params
        
        # Handle MongoDB operators
        if isinstance(value, dict):
            # Check for MongoDB operators
            for op_key, op_value in value.items():
                if op_key == "$gt":
                    params.append(json.dumps(op_value) if not isinstance(op_value, (str, int, float)) else op_value)
                    return f"json_extract(document, '$.{key}') > ?"
                elif op_key == "$gte":
                    params.append(json.dumps(op_value) if not isinstance(op_value, (str, int, float)) else op_value)
                    return f"json_extract(document, '$.{key}') >= ?"
                elif op_key == "$lt":
                    params.append(json.dumps(op_value) if not isinstance(op_value, (str, int, float)) else op_value)
                    return f"json_extract(document, '$.{key}') < ?"
                elif op_key == "$lte":
                    params.append(json.dumps(op_value) if not isinstance(op_value, (str, int, float)) else op_value)
                    return f"json_extract(document, '$.{key}') <= ?"
                elif op_key == "$ne":
                    params.append(json.dumps(op_value) if not isinstance(op_value, (str, int, float)) else op_value)
                    return f"json_extract(document, '$.{key}') != ?"
                elif op_key == "$eq":
                    params.append(json.dumps(op_value) if not isinstance(op_value, (str, int, float)) else op_value)
                    return f"json_extract(document, '$.{key}') = ?"
                elif op_key == "$in":
                    if not isinstance(op_value, list):
                        raise ValueError(f"$in operator requires a list, got {type(op_value)}")
                    placeholders = []
                    for item in op_value:
                        params.append(json.dumps(item) if not isinstance(item, (str, int, float)) else item)
                        placeholders.append("?")
                    return f"json_extract(document, '$.{key}') IN ({', '.join(placeholders)})"
                elif op_key == "$nin":
                    if not isinstance(op_value, list):
                        raise ValueError(f"$nin operator requires a list, got {type(op_value)}")
                    placeholders = []
                    for item in op_value:
                        params.append(json.dumps(item) if not isinstance(item, (str, int, float)) else item)
                        placeholders.append("?")
                    return f"json_extract(document, '$.{key}') NOT IN ({', '.join(placeholders)})"
                elif op_key == "$exists":
                    if op_value:
                        return f"json_extract(document, '$.{key}') IS NOT NULL"
                    else:
                        return f"json_extract(document, '$.{key}') IS NULL"
            
            # If no MongoDB operators found, treat as regular equality with dict value
            params.append(json.dumps(value))
            return f"json_extract(document, '$.{key}') = ?"
        else:
            # Simple equality
            params.append(json.dumps(value) if not isinstance(value, (str, int, float)) else value)
            return f"json_extract(document, '$.{key}') = ?"
    
    def process_logical_operator(op: str, conditions_list: list) -> str:
        """Process logical operators like $and, $or, $not."""
        nonlocal params
        
        if op == "$and":
            sub_conditions = []
            for condition_dict in conditions_list:
                for k, v in condition_dict.items():
                    if k.startswith("$"):
                        sub_conditions.append(process_logical_operator(k, v))
                    else:
                        sub_conditions.append(process_value(k, v))
            return f"({' AND '.join(sub_conditions)})" if sub_conditions else "1=1"
        
        elif op == "$or":
            sub_conditions = []
            for condition_dict in conditions_list:
                for k, v in condition_dict.items():
                    if k.startswith("$"):
                        sub_conditions.append(process_logical_operator(k, v))
                    else:
                        sub_conditions.append(process_value(k, v))
            return f"({' OR '.join(sub_conditions)})" if sub_conditions else "1=1"
        
        elif op == "$not":
            # $not is typically used with a single condition
            if isinstance(conditions_list, dict):
                sub_conditions = []
                for k, v in conditions_list.items():
                    if k.startswith("$"):
                        sub_conditions.append(process_logical_operator(k, v))
                    else:
                        sub_conditions.append(process_value(k, v))
                return f"NOT ({' AND '.join(sub_conditions)})" if sub_conditions else "1=1"
        
        return "1=1"
    
    # Process the queries
    for key, value in queries.items():
        if key.startswith("$"):
            # Logical operator at root level
            if key in ("$and", "$or"):
                conditions.append(process_logical_operator(key, value))
            elif key == "$not":
                conditions.append(process_logical_operator(key, value))
        else:
            # Regular field query
            conditions.append(process_value(key, value))
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    return where_clause, params


class Flexmodel(Flex):
    schema: Schema = Schema.ident()
    database: pymongo.MongoClient | sqlite3.Connection = sqlite3.Connection(":memory:")
    database_engine: str = "sqlite3"  # or "mongodb"
    table_name: str = "not_defined"

    @property
    def is_mongodb(self) -> bool:
        return self.__class__.database_engine == "mongodb"

    @property
    def is_sqlitedb(self) -> bool:
        return self.__class__.database_engine == "sqlite3"

    @property
    def id(self) -> str:
        if "_id" not in self.__dict__ or self.__dict__["_id"] == self.schema["_id"].default:
            self.__dict__["_id"] = str(uuid.uuid4())

        return self.__dict__["_id"]

    @property
    def updated_at(self) -> str:
        return self.__dict__.get("_updated_at", datetime.now(timezone.utc).isoformat())

    def update(self, **data: Any):
        result = super().update(**data)

        if "_id" not in data and self.__dict__.get("_id") == self.schema["_id"].default:
            _ = self.id

        return result

    def commit(self, commit_all: bool = True) -> bool:
        if not self.is_schematic():
            return False

        if commit_all:
            for item in [item for _, item in self.__dict__.items() if isinstance(item, Flexmodel)]:
                if not item.commit():
                    return False

        self.update(_updated_at=datetime.now(timezone.utc).isoformat())

        try:
            if self.is_mongodb and (collection := self.database[self.table_name]):
                return collection.replace_one({"_id": self.id}, self.to_dict(commit=commit_all), upsert=True).acknowledged
            elif self.is_sqlitedb and (c := self.database.cursor()):
                c.execute(
                    f"""
                        INSERT OR REPLACE INTO {self.table_name} 
                            (_id, _updated_at, document) 
                        VALUES (?, ?, ?);
                    """,
                    (self.id, self.updated_at, json.dumps(self.to_dict(commit=commit_all), ensure_ascii=False)),
                )
                self.database.commit()

                return True
        except Exception as e:
            FlexmodelException.silent_log(f"Commit error: {e}")

        return False

    def delete(self) -> bool:
        try:
            if self.is_mongodb and (collection := self.database[self.table_name]):
                return collection.delete_one({"_id": self.id}).deleted_count > 0
            elif self.is_sqlitedb and (c := self.database.cursor()):
                c.execute(f"DELETE FROM {self.table_name} WHERE _id = ?", (self.id,))
                self.database.commit()

                return c.rowcount > 0
        except Exception as e:
            FlexmodelException.silent_log(f"Delete error: {e}")

        return False

    @classmethod
    def attach(cls, database: pymongo.MongoClient | sqlite3.Connection, table_name: Optional[str] = None):
        if isinstance(database, pymongo.MongoClient):
            cls.database_engine = "mongodb"
        elif isinstance(database, sqlite3.Connection):
            cls.database_engine = "sqlite3"
        else:
            raise FlexmodelException("Cannot attach to the database: invalid database type. Only 'pymongo.MongoClient' or 'sqlite3.Connection' are supported.")

        cls.database = database
        cls.table_name = table_name or cls.__name__.lower() + "s"

        try:
            if cls.database_engine == "mongodb" and (collection := cls.database[cls.table_name]):
                collection.create_index("_id", unique=True)
            elif cls.database_engine == "sqlite3" and (c := cls.database.cursor()):
                c.execute(
                    f"""
                        CREATE TABLE IF NOT EXISTS {cls.table_name} (
                            _id TEXT PRIMARY KEY,
                            _updated_at TEXT NOT NULL,
                            document TEXT NOT NULL
                        )
                    """
                )
                cls.database.commit()
        except Exception as e:
            raise FlexmodelException(f"Cannot create index/table in the database: {e}")

    @classmethod
    def detach(cls):
        if cls.database_engine == "sqlite3":
            cls.database.close()

        cls.database = sqlite3.Connection(":memory:")
        cls.database_engine = "sqlite3"

    @classmethod
    def load(cls, _id: str) -> Optional["Flexmodel"]:
        try:
            if cls.database_engine == "mongodb" and (collection := cls.database[cls.table_name]):
                if document := collection.find_one({"_id": _id}):
                    return cls(**document)
            elif cls.database_engine == "sqlite3" and (c := cls.database.cursor()):
                c.execute(f"SELECT document FROM {cls.table_name} WHERE _id = ?", (_id,))

                if (item := c.fetchone()) and (document := json.loads(item[0])):
                    return cls(**document)
        except Exception as e:
            FlexmodelException.silent_log(f"Load error: {e}")

    @classmethod
    def count(cls) -> int:
        try:
            if cls.database_engine == "mongodb" and (collection := cls.database[cls.table_name]):
                return collection.count_documents({})
            elif cls.database_engine == "sqlite3" and (c := cls.database.cursor()):
                c.execute(f"SELECT COUNT(*) FROM {cls.table_name}")

                if item := c.fetchone():
                    return item[0]
        except Exception as e:
            FlexmodelException.silent_log(f"Count error: {e}")

        return 0

    @classmethod
    def truncate(cls):
        try:
            if cls.database_engine == "mongodb" and (collection := cls.database[cls.table_name]):
                collection.drop()
            elif cls.database_engine == "sqlite3" and (c := cls.database.cursor()):
                c.execute(f"DELETE FROM {cls.table_name}")
                cls.database.commit()
        except Exception as e:
            FlexmodelException.silent_log(f"Truncate error: {e}")

    @classmethod
    def fetch(cls, queries: dict[str, Any]) -> Optional["Flexmodel"]:
        try:
            if cls.database_engine == "mongodb" and (collection := cls.database[cls.table_name]):
                if document := collection.find_one(queries):
                    return cls(**document)
            elif cls.database_engine == "sqlite3" and (c := cls.database.cursor()):
                where_clause, params = _mongodb_to_sqlite_query(queries, cls.table_name)
                c.execute(f"SELECT document FROM {cls.table_name} WHERE {where_clause} LIMIT 1", params)

                if (item := c.fetchone()) and (document := json.loads(item[0])):
                    return cls(**document)
        except Exception as e:
            FlexmodelException.silent_log(f"Fetch error: {e}")

    @classmethod
    def fetch_all(cls, queries: dict[str, Any] = {}, page: int = 1, item_per_page: int = 10) -> "Flexmodel.Pagination":
        if page < 1:
            page = 1

        if item_per_page < 1:
            item_per_page = 10

        total_items = 0
        items: list["Flexmodel"] = []

        try:
            if cls.database_engine == "mongodb" and (collection := cls.database[cls.table_name]):
                if c := collection.find(queries).skip((page - 1) * item_per_page).limit(item_per_page):
                    total_items = collection.count_documents(queries)
                    items = [cls(**document) for document in c]
            elif cls.database_engine == "sqlite3" and (c := cls.database.cursor()):
                where_clause, params = _mongodb_to_sqlite_query(queries, cls.table_name)

                if c.execute(f"SELECT COUNT(*) FROM {cls.table_name} WHERE {where_clause}", params):
                    total_items = c.fetchone()[0]

                offset = (page - 1) * item_per_page

                if c.execute(f"SELECT document FROM {cls.table_name} WHERE {where_clause} LIMIT ? OFFSET ?", params + [item_per_page, offset]):
                    items = [cls(**json.loads(item[0])) for item in c.fetchall()]
        except Exception as e:
            FlexmodelException.silent_log(f"Fetch all error: {e}")

        return Flexmodel.Pagination(page=page, item_per_page=item_per_page, total_items=total_items, items=items)

    class Pagination:
        def __init__(self, *, page: int, item_per_page: int, total_items: int, items: list["Flexmodel"]):
            self.page: int = page
            self.item_per_page: int = item_per_page
            self.total_items: int = total_items
            self.items: list["Flexmodel"] = items

        @property
        def count(self) -> int:
            return self.total_items

        def __len__(self) -> int:
            return self.total_items

        def __iter__(self):
            for item in self.items:
                yield item

        def to_dict(self) -> dict[str, Any]:
            return {
                "metadata": {
                    "page": self.page,
                    "item_per_page": self.item_per_page,
                    "total_items": self.total_items,
                },
                "items": [item.to_dict() for item in self.items],
            }


def field(
    _type: Type,
    *,
    default: Any = None,
    nullable: bool | int = True,
    constraint: Schema.Field.Constraint = Schema.Field.Constraint(),
    callback: Optional[Callable[[Any], Any]] = None,
) -> Schema.Field:
    return Schema.Field(_type, default=default, nullable=nullable, constraint=constraint, callback=callback)


def field_constraint(
    *, item_type: Optional[Type] = None, min_length: Optional[int] = None, max_length: Optional[int] = None, pattern: Optional[str] = None
) -> Schema.Field.Constraint:
    return Schema.Field.Constraint(item_type=item_type, min_length=min_length, max_length=max_length, pattern=pattern)


def default(flex: Flex | Flexmodel, name: str) -> Any:
    return flex.schema[name].default


# Alias for backward compatibility
FlexmodelSQLite = Flexmodel
