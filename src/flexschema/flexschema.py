import re
import json
import uuid
import logging
import pymongo

from datetime import datetime, timezone
from typing import Any, Callable, Optional, Type, Union


logging.basicConfig(level=logging.INFO)
logging.getLogger("pymongo").setLevel(logging.WARNING)


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


class Flexmodel(Flex):
    schema: Schema = Schema.ident()
    database: pymongo.database.Database
    collection_name: str = "collections"

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

    def is_committable(self) -> bool:
        return self.schema.is_submittable(self.__dict__)

    def commit(self, commit_all: bool = True) -> bool:
        if not self.is_committable():
            return False

        if commit_all:
            for item in [item for _, item in self.__dict__.items() if isinstance(item, Flexmodel)]:
                if not item.commit():
                    return False

        self.update(_updated_at=datetime.now(timezone.utc).isoformat())

        collection = self.database[self.collection_name]
        return collection.replace_one({"_id": self.id}, self.to_dict(commit=commit_all), upsert=True).acknowledged

    def delete(self) -> bool:
        collection = self.database[self.collection_name]
        return collection.delete_one({"_id": self.id}).deleted_count > 0

    @classmethod
    def attach(cls, database: Union[pymongo.MongoClient, pymongo.database.Database], collection_name: Optional[str] = None):
        # Accept both MongoClient and Database for flexibility
        if isinstance(database, pymongo.MongoClient):
            # If MongoClient is provided, get the default database from the connection string
            database = database.get_default_database()
        elif not isinstance(database, pymongo.database.Database):
            raise FlexmodelException("Cannot attach to the database: invalid database type. Only 'pymongo.MongoClient' or 'pymongo.database.Database' is supported.")

        cls.database = database
        cls.collection_name = collection_name or cls.__name__.lower() + "s"

        # Try to create index if database is available, but don't fail if it's not
        try:
            collection = cls.database[cls.collection_name]
            if not collection.index_information().get("_id_"):
                collection.create_index("_id", unique=True)
        except Exception:
            # Database might not be available during initialization
            pass

    @classmethod
    def detach(cls):
        cls.database = None
        cls.collection_name = "collections"

    @classmethod
    def load(cls, id: str) -> Optional["Flexmodel"]:
        collection = cls.database[cls.collection_name]
        document = collection.find_one({"_id": id})
        if document:
            return cls(**document)

    @classmethod
    def count(cls) -> int:
        collection = cls.database[cls.collection_name]
        return collection.count_documents({})

    @classmethod
    def select(cls) -> "Flexmodel.Select":
        return Flexmodel.Select(cls())

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
            def serialize_for_display(obj):
                """Custom serializer for displaying queries with functions"""
                if isinstance(obj, dict):
                    result = {}
                    for key, value in obj.items():
                        if key == "$__function__" and isinstance(value, dict):
                            # Serialize function metadata in a readable way
                            func_info = value.copy()
                            if "functions" in func_info:
                                func_list = []
                                for func, args in func_info["functions"]:
                                    func_name = getattr(func, '__name__', 'anonymous')
                                    func_list.append({"function": func_name, "args": args})
                                func_info["functions"] = func_list
                            result[key] = func_info
                        else:
                            result[key] = serialize_for_display(value)
                    return result
                elif isinstance(obj, list):
                    return [serialize_for_display(item) for item in obj]
                else:
                    return obj
            
            serialized = serialize_for_display({"$where": self.statements, "$sort": self.sorts})
            return json.dumps(serialized, indent=4, ensure_ascii=False)

        @property
        def to_sql(self) -> str:
            sql: str = "SELECT * FROM " + self.model.collection_name

            if len(self.statements) == 0:
                return sql

            def parse_condition(condition: dict[str, Any]) -> str:
                clauses: list[str] = []

                for key, value in condition.items():
                    if key == "$and":
                        clauses.append("(" + " AND ".join([parse_condition(item) for item in value]) + ")")
                    elif key == "$or":
                        clauses.append("(" + " OR ".join([parse_condition(item) for item in value]) + ")")
                    elif key == "$not":
                        clauses.append("NOT (" + parse_condition(value) + ")")
                    else:
                        if isinstance(value, dict):
                            for op, val in value.items():
                                if op == "$ne":
                                    clauses.append(f"{key} != '{val}'")
                                elif op == "$lt":
                                    clauses.append(f"{key} < '{val}'")
                                elif op == "$gt":
                                    clauses.append(f"{key} > '{val}'")
                                elif op == "$lte":
                                    clauses.append(f"{key} <= '{val}'")
                                elif op == "$gte":
                                    clauses.append(f"{key} >= '{val}'")
                                elif op == "$in":
                                    clauses.append(f"{key} IN ({', '.join([json.dumps(v) for v in val])})")
                                elif op == "$nin":
                                    clauses.append(f"{key} NOT IN ({', '.join([json.dumps(v) for v in val])})")
                                elif op == "$regex":
                                    clauses.append(f"{key} REGEXP '{val}'")
                                elif op == "$not":
                                    clauses.append(f"NOT ({parse_condition({key: val})})")
                        else:
                            clauses.append(f"{key} = '{value}'")

                return " AND ".join(clauses)

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

        def _extract_function_filters(self, conditions: dict[str, Any]) -> tuple[dict[str, Any], list[tuple[str, dict]]]:
            """
            Extract function-based filters from conditions.
            Returns a tuple of (mongodb_conditions, function_filters).
            """
            mongodb_conditions = {}
            function_filters = []
            
            def process_condition(cond: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
                result = {}
                for key, value in cond.items():
                    if key in ["$and", "$or", "$not"]:
                        # Process logical operators recursively
                        if isinstance(value, list):
                            processed = [process_condition(item) for item in value]
                            result[key] = processed
                        elif isinstance(value, dict):
                            result[key] = process_condition(value)
                        else:
                            result[key] = value
                    elif isinstance(value, dict) and "$__function__" in value:
                        # Extract function filter
                        function_filters.append((key, value["$__function__"]))
                        # Don't add to MongoDB conditions
                    else:
                        result[key] = value
                return result
            
            mongodb_conditions = process_condition(conditions)
            return mongodb_conditions, function_filters

        def _apply_function_filters(self, documents: list[dict[str, Any]], function_filters: list[tuple[str, dict]]) -> list[dict[str, Any]]:
            """
            Apply function-based filters to documents client-side.
            """
            if not function_filters:
                return documents
            
            # Define DocWrapper class once, outside the loop
            class DocWrapper:
                """Simple wrapper to allow dot notation access to document fields"""
                def __init__(self, data):
                    for k, v in data.items():
                        setattr(self, k, v)
            
            filtered = []
            for doc in documents:
                match = True
                for field_name, func_info in function_filters:
                    # Apply each function in the chain
                    doc_wrapper = DocWrapper(doc)
                    result = None
                    
                    for func, args in func_info["functions"]:
                        if args:
                            result = func(doc_wrapper, *args)
                        else:
                            result = func(doc_wrapper)
                        # Update doc_wrapper with the result for next function in chain
                        # This allows chained functions to process the result of previous functions
                        doc_wrapper = DocWrapper({field_name: result})
                    
                    # Apply comparison operator
                    operator = func_info["operator"]
                    compare_value = func_info["value"]
                    
                    if operator == "$eq":
                        if result != compare_value:
                            match = False
                            break
                    elif operator == "$ne":
                        if result == compare_value:
                            match = False
                            break
                    elif operator == "$lt":
                        if not (result < compare_value):
                            match = False
                            break
                    elif operator == "$gt":
                        if not (result > compare_value):
                            match = False
                            break
                    elif operator == "$lte":
                        if not (result <= compare_value):
                            match = False
                            break
                    elif operator == "$gte":
                        if not (result >= compare_value):
                            match = False
                            break
                
                if match:
                    filtered.append(doc)
            
            return filtered

        def count(self) -> int:
            # Check if we have function filters
            mongodb_conditions, function_filters = self._extract_function_filters(self.statements)
            
            if function_filters:
                # Need to fetch all and filter client-side
                collection = self.model.database[self.model.collection_name]
                cursor = collection.find(mongodb_conditions)
                documents = list(cursor)
                filtered = self._apply_function_filters(documents, function_filters)
                return len(filtered)
            else:
                collection = self.model.database[self.model.collection_name]
                return collection.count_documents(self.statements)

        def fetch(self, function_filter_limit: int = 1000) -> Optional["Flexmodel"]:
            """
            Fetch a single document matching the query.
            
            Args:
                function_filter_limit: Maximum number of documents to fetch from database
                                      when using function filters (default: 1000)
            """
            mongodb_conditions, function_filters = self._extract_function_filters(self.statements)
            collection = self.model.database[self.model.collection_name]
            
            if function_filters:
                # Fetch candidates and filter client-side
                # Note: Function filters require client-side filtering, so we need to fetch
                # multiple documents. The limit prevents memory issues with large collections.
                cursor = collection.find(mongodb_conditions).limit(function_filter_limit)
                documents = list(cursor)
                
                if len(documents) == function_filter_limit:
                    FlexmodelException.silent_log(
                        f"Warning: Reached function_filter_limit ({function_filter_limit}) in fetch(). "
                        "Consider adding MongoDB-compatible filters or increasing the limit."
                    )
                
                filtered = self._apply_function_filters(documents, function_filters)
                if filtered:
                    return self.model.__class__(**filtered[0])
            else:
                document = collection.find_one(mongodb_conditions)
                if document:
                    return self.model.__class__(**document)

        def fetch_all(self, current: int = 1, results_per_page: int = 10, function_filter_limit: Optional[int] = None) -> "Flexmodel.Select.Pagination":
            """
            Fetch all documents matching the query with pagination.
            
            Args:
                current: Current page number (min 1)
                results_per_page: Number of results per page (min 1)
                function_filter_limit: Maximum number of documents to fetch when using
                                      function filters. If None, fetches all documents.
                                      Use with caution on large collections.
            """
            count: int = 0
            results: list["Flexmodel"] = []

            if current < 1:
                current = 1

            if results_per_page < 1:
                results_per_page = 10

            mongodb_conditions, function_filters = self._extract_function_filters(self.statements)
            collection = self.model.database[self.model.collection_name]
            
            if function_filters:
                # Fetch all matching MongoDB conditions, then filter client-side
                # Warning: This loads all documents into memory
                cursor = collection.find(mongodb_conditions).sort(self.sorts)
                
                if function_filter_limit:
                    cursor = cursor.limit(function_filter_limit)
                
                documents = list(cursor)
                
                if function_filter_limit and len(documents) == function_filter_limit:
                    FlexmodelException.silent_log(
                        f"Warning: Reached function_filter_limit ({function_filter_limit}) in fetch_all(). "
                        "Some results may be missing. Consider adding MongoDB-compatible filters or increasing the limit."
                    )
                
                filtered = self._apply_function_filters(documents, function_filters)
                count = len(filtered)
                
                # Apply pagination to filtered results
                start = (current - 1) * results_per_page
                end = start + results_per_page
                paginated = filtered[start:end]
                results = [self.model.__class__(**document) for document in paginated]
            else:
                count = collection.count_documents(mongodb_conditions)
                if count > 0:
                    cursor = collection.find(mongodb_conditions).skip((current - 1) * results_per_page).sort(self.sorts).limit(results_per_page)
                    results = [self.model.__class__(**document) for document in cursor]

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
                    "count": self.count,
                    "results": [item.to_dict() for item in self.results],
                    "pagination": {
                        "current": self.current,
                        "results_per_page": self.results_per_page,
                    },
                }

        class Statement:
            def __init__(self, name: str, model: Any, functions: Optional[list[tuple[Callable, tuple]]] = None):
                self.name: str = name
                self.model: Any = model
                self.functions: list[tuple[Callable, tuple]] = functions if functions is not None else []

            def __getattr__(self, name: str) -> "Flexmodel.Select.Statement":
                if not isinstance(self.model, Flex) or name not in self.model.schema.fields:
                    raise FlexmodelException(f"Select statement: field '{self.name}' is not a Flex object, cannot access sub-field '{name}'.")

                return Flexmodel.Select.Statement(f"{self.name}.{name}", self.model.__dict__.get(name, self.model.schema[name].default))

            def __getitem__(self, name: str) -> "Flexmodel.Select.Statement":
                if not isinstance(self.model, Flex) or name not in self.model.schema.fields:
                    raise FlexmodelException(f"Select statement: field '{self.name}' is not a Flex object, cannot access sub-field '{name}'.")

                return Flexmodel.Select.Statement(f"{self.name}.{name}", self.model.__dict__.get(name, self.model.schema[name].default))

            def __eq__(self, value: Any) -> dict[str, Any]:  # type: ignore
                if self.functions:
                    return {self.name: {"$__function__": {"functions": self.functions, "operator": "$eq", "value": value}}}
                return {self.name: value}

            def __ne__(self, value: Any) -> dict[str, Any]:  # type: ignore
                if self.functions:
                    return {self.name: {"$__function__": {"functions": self.functions, "operator": "$ne", "value": value}}}
                return {self.name: {"$ne": value}}

            def __lt__(self, value: Any) -> dict[str, Any]:  # type: ignore
                if self.functions:
                    return {self.name: {"$__function__": {"functions": self.functions, "operator": "$lt", "value": value}}}
                return {self.name: {"$lt": value}}

            def __gt__(self, value: Any) -> dict[str, Any]:  # type: ignore
                if self.functions:
                    return {self.name: {"$__function__": {"functions": self.functions, "operator": "$gt", "value": value}}}
                return {self.name: {"$gt": value}}

            def __le__(self, value: Any) -> dict[str, Any]:  # type: ignore
                if self.functions:
                    return {self.name: {"$__function__": {"functions": self.functions, "operator": "$lte", "value": value}}}
                return {self.name: {"$lte": value}}

            def __ge__(self, value: Any) -> dict[str, Any]:  # type: ignore
                if self.functions:
                    return {self.name: {"$__function__": {"functions": self.functions, "operator": "$gte", "value": value}}}
                return {self.name: {"$gte": value}}

            def __contains__(self, item: Any) -> dict[str, Any]:  # type: ignore
                return {self.name: {"$in": item}}

            def asc(self) -> dict[str, Any]:
                return {self.name: 1}

            def desc(self) -> dict[str, Any]:
                return {self.name: -1}

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

            def function(self, func: Callable, args: tuple = ()) -> "Flexmodel.Select.Statement":
                """
                Apply a function to the field value. Returns a new Statement instance 
                that allows chaining additional functions or comparison operators.
                
                Args:
                    func: A callable that takes a document (or the result of previous functions) as first argument
                    args: Optional tuple of additional arguments to pass to the function
                
                Returns:
                    A new Statement instance with the function added to the chain
                    
                Example:
                    def apply_discount(document, discount: float):
                        return document.price * discount
                    
                    select.where(
                        select.price.function(apply_discount, args=(0.75,)) > 50
                    )
                """
                # Create a new Statement with the function added to the chain
                new_functions = self.functions.copy()
                new_functions.append((func, args))
                return Flexmodel.Select.Statement(self.name, self.model, functions=new_functions)


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
