import re
import json
import uuid

from datetime import datetime, timezone
from typing import Any, Callable, Optional, Type

from pymongo import MongoClient
from pymongo.collection import Collection


class SchemaDefinitionException(Exception):
    pass


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

        if field.type not in (str, int, float, bool, list, tuple) and not issubclass(field.type, (Flex, Flexmodel)):
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
            if commit and isinstance(value, Flexmodel):
                return {"$id": value.id}
            elif isinstance(value, (Flex, Flexmodel)):
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
    database: Optional[MongoClient] = None
    collection_name: str = "not_defined"

    @property
    def id(self) -> str:
        return self.__dict__.get("_id", str(uuid.uuid4()))

    @property
    def updated_at(self) -> str:
        return self.__dict__.get("_updated_at", datetime.now(timezone.utc).isoformat())

    def commit(self, commit_all: bool = True) -> bool:
        if not self.is_schematic():
            return False

        if commit_all:
            for item in [item for _, item in self.__dict__.items() if isinstance(item, Flexmodel)]:
                if not item.commit():
                    return False

        self.update(_updated_at=datetime.now(timezone.utc).isoformat())

        return self.collection().replace_one({"_id": self.id}, self.to_dict(commit=commit_all), upsert=True).acknowledged

    def delete(self) -> bool:
        return self.collection().delete_one({"_id": self.id}).deleted_count > 0

    @classmethod
    def attach(cls, database: MongoClient, collection_name: Optional[str] = None):
        cls.database = database

        if not collection_name:
            cls.collection_name = cls.__name__.lower() + "s"
        else:
            cls.collection_name = collection_name

    @classmethod
    def detach(cls):
        cls.database = None
        cls.collection_name = "not_defined"

    @classmethod
    def collection(cls) -> Collection:
        if cls.database is None:
            raise Exception(f"Flexmodel '{cls.__name__}': has no database attached. Use '{cls.__name__}.attach(database, collection_name)' to attach a database.")

        return cls.database[cls.collection_name]

    @classmethod
    def load(cls, _id: str) -> Optional["Flexmodel"]:
        if document := cls.collection().find_one({"_id": _id}):
            return cls(**document)

    @classmethod
    def count(cls) -> int:
        return cls.collection().count_documents({})

    @classmethod
    def truncate(cls):
        return cls.collection().drop()

    @classmethod
    def fetch(cls, queries: dict[str, Any]) -> Optional["Flexmodel"]:
        if document := cls.collection().find_one(queries):
            return cls(**document)

    @classmethod
    def fetch_all(cls, queries: dict[str, Any] = {}, position: int = 1, position_limit: int = 10) -> "Flexmodel.Pagination":
        if position < 1:
            position = 1

        if position_limit < 1:
            position_limit = 1

        cursor = cls.collection().find(queries).skip((position - 1) * position_limit).limit(position_limit)

        return Flexmodel.Pagination(
            position=position,
            position_limit=position_limit,
            total_items=cls.collection().count_documents(queries),
            items=[cls(**document) for document in cursor],
        )

    class Pagination:
        def __init__(self, *, position: int, position_limit: int, total_items: int, items: list["Flexmodel"]):
            self.position: int = position
            self.position_limit: int = position_limit
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
                    "position": self.position,
                    "position_limit": self.position_limit,
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
    return Schema.Field(
        _type,
        default=default,
        nullable=nullable,
        constraint=constraint,
        callback=callback,
    )


def field_constraint(
    *,
    item_type: Optional[Type] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    pattern: Optional[str] = None,
) -> Schema.Field.Constraint:
    return Schema.Field.Constraint(
        item_type=item_type,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
    )


def default(flex: Flex | Flexmodel, name: str) -> Any:
    return flex.schema[name].default
