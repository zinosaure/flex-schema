import re
import json
import uuid
import logging

from datetime import datetime, timezone
from typing import Any, Optional
from typing import Callable, Type

try:
    import pymysql
except Exception:  # pragma: no cover - optional dependency
    pymysql = None


logging.basicConfig(level=logging.INFO)
logging.getLogger("pymysql").setLevel(logging.WARNING)


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
            _id=Schema.Field(int, default=None),
            _uuid=Schema.Field(str, default=None),
            _updated_at=Schema.Field(str, default=None),
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
            raise SchemaDefinitionException(f"Field '{name}': is not instance of 'type'.")

        # Check if type is a primitive or a subclass of Flex
        if not (field.type in (str, int, float, bool, list, tuple) or (hasattr(field.type, "__mro__") and any(base.__name__ == "Flex" for base in field.type.__mro__))):
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

    @property
    def default(self) -> dict[str, Any]:
        return {name: field.default for name, field in self.schema.fields.items()}

    def update(self, **data: Any):
        for name, field in self.schema:
            value = data.get(name, self.__dict__.get(name, field.default))

            if issubclass(field.type, Flexmodel) and isinstance(value, dict) and (id := value.get("$id")):
                value = field.type.load(id)
            elif issubclass(field.type, Flexmodel) and isinstance(value, (int, str)):
                value = field.type.load(value)
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
                return value.id
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


class Flexmodel(Flex):
    schema: Schema = Schema.ident()
    database: Any
    collection_name: str = "collections"

    @staticmethod
    def _now_str() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    @property
    def id(self) -> Optional[int]:
        return self.__dict__.get("_id")

    @property
    def uuid(self) -> str:
        if "_uuid" not in self.__dict__ or not self.__dict__["_uuid"]:
            self.__dict__["_uuid"] = str(uuid.uuid4())

        return self.__dict__["_uuid"]

    @property
    def updated_at(self) -> str:
        return self.__dict__.get("_updated_at", self._now_str())

    def update(self, **data: Any):
        result = super().update(**data)

        if "_uuid" not in data and not self.__dict__.get("_uuid"):
            _ = self.uuid

        return result

    def is_committable(self) -> bool:
        return self.schema.is_submittable(self.__dict__)

    def commit(self, commit_all: bool = True) -> bool:
        if not self.is_committable():
            return False

        if commit_all:
            for item in [item for _, item in self.__dict__.items() if isinstance(item, Flexmodel)]:
                if not item.commit():
                    return False

        self.update(_updated_at=self._now_str())
        _ = self.uuid

        row = self._serialize_for_db(commit_all)
        return self._save_row(row)

    def delete(self) -> bool:
        if self.id is None:
            return False

        sql = f"DELETE FROM `{self.collection_name}` WHERE `_id` = %s"
        with self.connection().cursor() as cursor:
            cursor.execute(sql, (self.id,))
        self.connection().commit()
        return True

    @classmethod
    def attach(cls, database: Any, collection_name: Optional[str] = None):
        if pymysql is None:
            raise FlexmodelException("Cannot attach to MySQL: pymysql is not installed.")

        if isinstance(database, dict):
            cls.database = pymysql.connect(**database)
        elif pymysql and hasattr(pymysql, "connections") and isinstance(database, pymysql.connections.Connection):
            cls.database = database
        else:
            raise FlexmodelException("Cannot attach to the database: invalid database type. Only 'pymysql.Connection' or connection params dict is supported.")

        cls.collection_name = collection_name or cls.__name__.lower() + "s"
        cls._ensure_table()

    @classmethod
    def detach(cls):
        if cls.database is not None:
            try:
                cls.database.close()
            except Exception:
                pass
        cls.database = None
        cls.collection_name = "collections"

    @classmethod
    def connection(cls) -> Any:
        if pymysql is None:
            raise FlexmodelException("MySQL is not available because pymysql is not installed.")

        if cls.database is None:
            raise FlexmodelException("MySQL connection is not initialized. Call attach() first.")

        return cls.database

    @classmethod
    def load(cls, id: int | str) -> Optional["Flexmodel"]:
        sql = f"SELECT * FROM `{cls.collection_name}` WHERE `_id` = %s LIMIT 1"
        with cls.connection().cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql, (id,))
            row = cursor.fetchone()

        if row:
            return cls._from_row(row)

    @classmethod
    def count(cls) -> int:
        sql = f"SELECT COUNT(*) AS total FROM `{cls.collection_name}`"
        with cls.connection().cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(sql)
            row = cursor.fetchone()
        return int(row.get("total", 0)) if row else 0

    @classmethod
    def select(cls) -> "Flexmodel.Select":
        return Flexmodel.Select(cls())

    @classmethod
    def _column_type(cls, name: str, field: Schema.Field) -> str:
        if name == "_id":
            return "BIGINT AUTO_INCREMENT PRIMARY KEY"
        if name == "_uuid":
            return "CHAR(36) NOT NULL UNIQUE"
        if name == "_updated_at":
            return "DATETIME"

        if hasattr(field.type, "__mro__") and any(base.__name__ == "Flexmodel" for base in field.type.__mro__):
            return "BIGINT"
        if field.type in (list, tuple) or (hasattr(field.type, "__mro__") and any(base.__name__ == "Flex" for base in field.type.__mro__)):
            return "JSON"
        if field.type is str:
            return "TEXT"
        if field.type is int:
            return "BIGINT"
        if field.type is float:
            return "DOUBLE"
        if field.type is bool:
            return "TINYINT(1)"
        return "TEXT"

    @classmethod
    def _ensure_table(cls):
        columns: list[str] = []

        for name, field in cls.schema:
            column = f"`{name}` {cls._column_type(name, field)}"
            if name not in ("_id", "_uuid") and field.nullable is False:
                column += " NOT NULL"
            columns.append(column)

        sql = f"CREATE TABLE IF NOT EXISTS `{cls.collection_name}` ({', '.join(columns)})"
        with cls.connection().cursor() as cursor:
            cursor.execute(sql)
        cls.connection().commit()

    @classmethod
    def _serialize_value(cls, value: Any) -> Any:
        if isinstance(value, Flexmodel):
            return value.id
        if isinstance(value, Flex):
            return json.dumps(value.to_dict(), ensure_ascii=False)
        if isinstance(value, list):
            return json.dumps([cls._serialize_value(item) for item in value], ensure_ascii=False)
        if isinstance(value, tuple):
            return json.dumps([cls._serialize_value(item) for item in value], ensure_ascii=False)
        if isinstance(value, dict):
            return json.dumps({key: cls._serialize_value(item) for key, item in value.items()}, ensure_ascii=False)
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value

    @classmethod
    def _deserialize_value(cls, value: Any, field: Schema.Field) -> Any:
        if value is None:
            return None

        if field.type is bool:
            return bool(value)

        if field.type is int:
            return int(value)

        if field.type is float:
            return float(value)

        if field.type in (list, tuple):
            if isinstance(value, (str, bytes)):
                try:
                    parsed = json.loads(value)
                except Exception:
                    parsed = []
            else:
                parsed = value
            return tuple(parsed) if field.type is tuple else parsed

        if hasattr(field.type, "__mro__") and any(base.__name__ == "Flexmodel" for base in field.type.__mro__):
            return field.type.load(value)

        if hasattr(field.type, "__mro__") and any(base.__name__ == "Flex" for base in field.type.__mro__):
            if isinstance(value, (str, bytes)):
                try:
                    parsed = json.loads(value)
                except Exception:
                    parsed = {}
            else:
                parsed = value
            return field.type().update(**parsed)

        return value

    def _serialize_for_db(self, commit_all: bool) -> dict[str, Any]:
        data = self.to_dict(commit=commit_all)
        return {name: self._serialize_value(value) for name, value in data.items()}

    def _save_row(self, row: dict[str, Any]) -> bool:
        if self.id is None:
            columns = [name for name in row.keys() if name != "_id"]
            values = [row[name] for name in columns]
            placeholders = ", ".join(["%s"] * len(columns))
            sql = f"INSERT INTO `{self.collection_name}` ({', '.join(['`' + name + '`' for name in columns])}) VALUES ({placeholders})"
            with self.connection().cursor() as cursor:
                cursor.execute(sql, values)
                self.__dict__["_id"] = cursor.lastrowid
            self.connection().commit()
            return True

        columns = [name for name in row.keys() if name != "_id"]
        values = [row[name] for name in columns]
        assignments = ", ".join([f"`{name}` = %s" for name in columns])
        sql = f"UPDATE `{self.collection_name}` SET {assignments} WHERE `_id` = %s"
        with self.connection().cursor() as cursor:
            cursor.execute(sql, values + [self.id])
        self.connection().commit()
        return True

    @classmethod
    def _from_row(cls, row: dict[str, Any]) -> "Flexmodel":
        data: dict[str, Any] = {}
        for name, field in cls.schema:
            if name in row:
                data[name] = cls._deserialize_value(row[name], field)
        return cls(**data)

    class Select:
        def __init__(self, model: "Flexmodel"):
            self.model: "Flexmodel" = model
            self.sorts: dict[str, Any] = {}
            self.statements: dict[str, Any] = {}

        def __getattr__(self, name: str) -> "Flexmodel.Select.Statement":
            if name not in self.model.schema.fields:
                raise FlexmodelException(f"Select statement: field '{name}' does not exist in the model schema.")

            return Flexmodel.Select.Statement(name, self.model.__dict__.get(name, self.model.schema[name].default))

        def __getitem__(self, name: str) -> "Flexmodel.Select.Statement":
            if name not in self.model.schema.fields:
                raise FlexmodelException(f"Select statement: field '{name}' does not exist in the model schema.")

            return Flexmodel.Select.Statement(name, self.model.__dict__.get(name, self.model.schema[name].default))

        def __len__(self) -> int:
            return self.count()

        def __iter__(self):
            for item in self.fetch_all():
                yield item

        @property
        def query_string(self) -> str:
            return json.dumps({"$where": self.statements, "$sort": self.sorts}, indent=4, ensure_ascii=False)

        @property
        def to_sql(self) -> str:
            sql: str = "SELECT * FROM `" + self.model.collection_name + "`"

            if len(self.statements) == 0:
                return sql

            def sql_literal(value: Any) -> str:
                if value is None:
                    return "NULL"
                if isinstance(value, bool):
                    return "1" if value else "0"
                if isinstance(value, (int, float)):
                    return str(value)
                return json.dumps(value)

            def field_expr(name: str) -> str:
                if "." not in name:
                    return f"`{name}`"
                root, rest = name.split(".", 1)
                path = "$." + rest
                return f"JSON_EXTRACT(`{root}`, '{path}')"

            def parse_condition(condition: dict[str, Any]) -> str:
                clauses: list[str] = []

                for key, value in condition.items():
                    if key == "$and":
                        parts = [parse_condition(item) for item in value]
                        parts = [part for part in parts if part]
                        if parts:
                            clauses.append("(" + " AND ".join(parts) + ")")
                    elif key == "$or":
                        parts = [parse_condition(item) for item in value]
                        parts = [part for part in parts if part]
                        if parts:
                            clauses.append("(" + " OR ".join(parts) + ")")
                    elif key == "$not":
                        inner = parse_condition(value)
                        if inner:
                            clauses.append("NOT (" + inner + ")")
                    else:
                        expr = field_expr(key)
                        if isinstance(value, dict):
                            for op, val in value.items():
                                if op == "$eq":
                                    clauses.append(f"{expr} = {sql_literal(val)}")
                                if op == "$ne":
                                    clauses.append(f"{expr} != {sql_literal(val)}")
                                elif op == "$lt":
                                    clauses.append(f"{expr} < {sql_literal(val)}")
                                elif op == "$gt":
                                    clauses.append(f"{expr} > {sql_literal(val)}")
                                elif op == "$lte":
                                    clauses.append(f"{expr} <= {sql_literal(val)}")
                                elif op == "$gte":
                                    clauses.append(f"{expr} >= {sql_literal(val)}")
                                elif op == "$in":
                                    clauses.append(f"{expr} IN ({', '.join([sql_literal(v) for v in val])})")
                                elif op == "$nin":
                                    clauses.append(f"{expr} NOT IN ({', '.join([sql_literal(v) for v in val])})")
                                elif op == "$regex":
                                    clauses.append(f"{expr} REGEXP {sql_literal(val)}")
                                elif op == "$exists":
                                    clauses.append(f"{expr} IS {'NOT ' if val else ''}NULL")
                                elif op == "$all":
                                    parts = [f"JSON_CONTAINS({expr}, {sql_literal(json.dumps(v))})" for v in val]
                                    clauses.append(" AND ".join(parts))
                                elif op == "$not":
                                    clauses.append(f"NOT ({parse_condition({key: val})})")
                        else:
                            clauses.append(f"{expr} = {sql_literal(value)}")

                return " AND ".join([clause for clause in clauses if clause])

            return sql + " WHERE " + parse_condition(self.statements)

        def match(self, *conditions: dict[str, Any]) -> dict[str, Any]:
            if len(conditions) == 0:
                return {}

            return {"$and": list(conditions)}

        def not_match(self, *conditions: dict[str, Any]) -> dict[str, Any]:
            if len(conditions) == 0:
                return {}

            return {"$not": {"$and": list(conditions)}}

        def at_least(self, *conditions: dict[str, Any]) -> dict[str, Any]:
            if len(conditions) == 0:
                return {}

            return {"$or": list(conditions)}

        def not_at_least(self, *conditions: dict[str, Any]) -> dict[str, Any]:
            if len(conditions) == 0:
                return {}

            return {"$not": {"$or": list(conditions)}}

        def where(self, *conditions: dict[str, Any]):
            for condition in conditions:
                for logical, value in condition.items():
                    self.statements[logical] = value

        def sort(self, *conditions: dict[str, Any]):
            if len(conditions) == 0:
                return

            for condition in conditions:
                for logical, value in condition.items():
                    self.sorts[logical] = value

        def discard(self):
            self.sorts = {}
            self.statements = {}

        def count(self) -> int:
            sql, params = self._build_query(count_only=True)
            with self.model.connection().cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
            return int(row.get("total", 0)) if row else 0

        def fetch(self) -> Optional["Flexmodel"]:
            sql, params = self._build_query(limit=1)
            with self.model.connection().cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()

            if row:
                return self.model.__class__._from_row(row)

        def fetch_all(self, current: int = 1, results_per_page: int = 10) -> "Flexmodel.Select.Pagination":
            count: int = 0
            results: list["Flexmodel"] = []

            if current < 1:
                current = 1

            if results_per_page < 1:
                results_per_page = 10

            count = self.count()
            if count > 0:
                sql, params = self._build_query(limit=results_per_page, offset=(current - 1) * results_per_page)
                with self.model.connection().cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                results = [self.model.__class__._from_row(row) for row in rows]

            return Flexmodel.Select.Pagination(count, results, current=current, results_per_page=results_per_page)

        class Pagination:
            def __init__(self, count: int, results: list["Flexmodel"], *, current: int, results_per_page: int):
                self.count: int = count
                self.results: list["Flexmodel"] = results
                self.current: int = current
                self.results_per_page: int = results_per_page

            def __len__(self) -> int:
                return self.count

            def __iter__(self):
                for item in self.results:
                    yield item

            def map(self, callback: Callable[["Flexmodel"], "Flexmodel"]) -> list["Flexmodel"]:
                return [callback(item) for item in self.results]

            def to_dict(self) -> dict[str, Any]:
                return {
                    "results": [item.to_dict() for item in self.results],
                    "pagination": {
                        "count": self.count,
                        "current": self.current,
                        "results_per_page": self.results_per_page,
                    },
                }

        class Statement:
            def __init__(self, name: str, model: Any):
                self.name: str = name
                self.model: Any = model

            def __getattr__(self, name: str) -> "Flexmodel.Select.Statement":
                if not isinstance(self.model, Flex) or name not in self.model.schema.fields:
                    raise FlexmodelException(f"Select statement: field '{self.name}' is not a Flex object, cannot access sub-field '{name}'.")

                return Flexmodel.Select.Statement(f"{self.name}.{name}", self.model.__dict__.get(name, self.model.schema[name].default))

            def __getitem__(self, name: str) -> "Flexmodel.Select.Statement":
                if not isinstance(self.model, Flex) or name not in self.model.schema.fields:
                    raise FlexmodelException(f"Select statement: field '{self.name}' is not a Flex object, cannot access sub-field '{name}'.")

                return Flexmodel.Select.Statement(f"{self.name}.{name}", self.model.__dict__.get(name, self.model.schema[name].default))

            def __eq__(self, value: Any) -> dict[str, Any]:  # type: ignore
                return {self.name: value}

            def __ne__(self, value: Any) -> dict[str, Any]:  # type: ignore
                return {self.name: {"$ne": value}}

            def __lt__(self, value: Any) -> dict[str, Any]:  # type: ignore
                return {self.name: {"$lt": value}}

            def __gt__(self, value: Any) -> dict[str, Any]:  # type: ignore
                return {self.name: {"$gt": value}}

            def __le__(self, value: Any) -> dict[str, Any]:  # type: ignore
                return {self.name: {"$lte": value}}

            def __ge__(self, value: Any) -> dict[str, Any]:  # type: ignore
                return {self.name: {"$gte": value}}

            def __contains__(self, item: Any) -> dict[str, Any]:  # type: ignore
                return {self.name: {"$in": item}}

            def exists(self) -> dict[str, Any]:
                return {self.name: {"$exists": True}}

            def not_exists(self) -> dict[str, Any]:
                return {self.name: {"$exists": False}}

            def is_true(self) -> dict[str, Any]:
                return {self.name: {"$eq": True}}

            def is_false(self) -> dict[str, Any]:
                return {self.name: {"$eq": False}}

            def is_null(self) -> dict[str, Any]:
                return {self.name: {"$eq": None}}

            def is_not_null(self) -> dict[str, Any]:
                return {self.name: {"$ne": None}}

            def is_empty(self) -> dict[str, Any]:
                return {self.name: {"$in": [None, ""]}}

            def is_not_empty(self) -> dict[str, Any]:
                return {self.name: {"$nin": [None, ""]}}

            def is_between(self, *, start: int | str, end: int | str) -> dict[str, Any]:
                return {self.name: {"$gte": start, "$lte": end}}

            def is_not_between(self, *, start: int | str, end: int | str) -> dict[str, Any]:
                return {self.name: {"$lt": start, "$gt": end}}

            def is_in(self, *, items: list[Any]) -> dict[str, Any]:
                return {self.name: {"$in": items}}

            def is_not_in(self, *, items: list[Any]) -> dict[str, Any]:
                return {self.name: {"$nin": items}}

            def match(self, pattern: str, *, options: str = "i") -> dict[str, Any]:
                return {self.name: {"$regex": pattern, "$options": options}}

            def not_match(self, pattern: str, *, options: str = "i") -> dict[str, Any]:
                return {self.name: {"$not": {"$regex": pattern, "$options": options}}}

            def subset(self, items: list[Any]) -> dict[str, Any]:
                return {self.name: {"$all": items}}

            def not_subset(self, items: list[Any]) -> dict[str, Any]:
                return {self.name: {"$not": {"$all": items}}}

            def function(self, js_code: str) -> dict[str, Any]:
                return {self.name: {"$where": js_code}}

            # sorting helpers
            def asc(self) -> dict[str, Any]:
                return {self.name: 1}

            def desc(self) -> dict[str, Any]:
                return {self.name: -1}

        def _build_query(self, *, count_only: bool = False, limit: Optional[int] = None, offset: Optional[int] = None) -> tuple[str, list[Any]]:
            select_clause = "SELECT COUNT(*) AS total" if count_only else "SELECT *"
            sql = f"{select_clause} FROM `{self.model.collection_name}`"
            params: list[Any] = []

            def field_expr(name: str) -> str:
                if "." not in name:
                    return f"`{name}`"
                root, rest = name.split(".", 1)
                path = "$." + rest
                return f"JSON_EXTRACT(`{root}`, '{path}')"

            def parse_condition(condition: dict[str, Any]) -> str:
                clauses: list[str] = []

                for key, value in condition.items():
                    if key == "$and":
                        parts = [parse_condition(item) for item in value]
                        parts = [part for part in parts if part]
                        if parts:
                            clauses.append("(" + " AND ".join(parts) + ")")
                    elif key == "$or":
                        parts = [parse_condition(item) for item in value]
                        parts = [part for part in parts if part]
                        if parts:
                            clauses.append("(" + " OR ".join(parts) + ")")
                    elif key == "$not":
                        inner = parse_condition(value)
                        if inner:
                            clauses.append("NOT (" + inner + ")")
                    else:
                        expr = field_expr(key)
                        if isinstance(value, dict):
                            for op, val in value.items():
                                if op == "$eq":
                                    if val is None:
                                        clauses.append(f"{expr} IS NULL")
                                    else:
                                        clauses.append(f"{expr} = %s")
                                        params.append(val)
                                elif op == "$ne":
                                    if val is None:
                                        clauses.append(f"{expr} IS NOT NULL")
                                    else:
                                        clauses.append(f"{expr} != %s")
                                        params.append(val)
                                elif op == "$lt":
                                    clauses.append(f"{expr} < %s")
                                    params.append(val)
                                elif op == "$gt":
                                    clauses.append(f"{expr} > %s")
                                    params.append(val)
                                elif op == "$lte":
                                    clauses.append(f"{expr} <= %s")
                                    params.append(val)
                                elif op == "$gte":
                                    clauses.append(f"{expr} >= %s")
                                    params.append(val)
                                elif op == "$in":
                                    if not val:
                                        clauses.append("FALSE")
                                    else:
                                        placeholders = ", ".join(["%s"] * len(val))
                                        clauses.append(f"{expr} IN ({placeholders})")
                                        params.extend(val)
                                elif op == "$nin":
                                    if not val:
                                        clauses.append("TRUE")
                                    else:
                                        placeholders = ", ".join(["%s"] * len(val))
                                        clauses.append(f"{expr} NOT IN ({placeholders})")
                                        params.extend(val)
                                elif op == "$regex":
                                    clauses.append(f"{expr} REGEXP %s")
                                    params.append(val)
                                elif op == "$exists":
                                    clauses.append(f"{expr} IS {'NOT ' if val else ''}NULL")
                                elif op == "$all":
                                    for item in val:
                                        clauses.append(f"JSON_CONTAINS({expr}, %s)")
                                        params.append(json.dumps(item))
                                elif op == "$not":
                                    clauses.append(f"NOT ({parse_condition({key: val})})")
                                elif op == "$where":
                                    raise FlexmodelException("MySQL does not support $where JavaScript functions.")
                        else:
                            if value is None:
                                clauses.append(f"{expr} IS NULL")
                            else:
                                clauses.append(f"{expr} = %s")
                                params.append(value)

                return " AND ".join([clause for clause in clauses if clause])

            if self.statements:
                where_sql = parse_condition(self.statements)
                if where_sql:
                    sql += " WHERE " + where_sql

            if not count_only and self.sorts:
                order_clauses: list[str] = []
                for name, direction in self.sorts.items():
                    direction_sql = "ASC" if direction == 1 else "DESC"
                    order_clauses.append(f"{field_expr(name)} {direction_sql}")
                if order_clauses:
                    sql += " ORDER BY " + ", ".join(order_clauses)

            if not count_only and limit is not None:
                sql += " LIMIT %s"
                params.append(limit)
                if offset is not None:
                    sql += " OFFSET %s"
                    params.append(offset)

            return sql, params


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
