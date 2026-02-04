import os
import json
import logging
import re
import sqlite3
import uuid

from datetime import datetime, timezone
from typing import Any, Optional, Union

from .flexschema import Schema, Flex


logging.basicConfig(level=logging.INFO)


class FlexmodelLiteException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        logging.getLogger("flexschema_lite").error(message)

    @staticmethod
    def silent_log(message: str):
        logging.getLogger("flexschema_lite").info(message)


class FlexmodelLite(Flex):
    schema: Schema = Schema.ident()
    connection: Optional[sqlite3.Connection] = None
    collection_name: str = "collections"
    _owns_connection: bool = False

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

    @classmethod
    def attach(cls, database: Union[str, sqlite3.Connection], collection_name: Optional[str] = None):
        if isinstance(database, str):
            cls.connection = sqlite3.connect(database)
            cls._owns_connection = True
        elif isinstance(database, sqlite3.Connection):
            cls.connection = database
            cls._owns_connection = False
        else:
            raise FlexmodelLiteException("Cannot attach to the database: invalid database type. Only 'str' or 'sqlite3.Connection' is supported.")

        cls.connection.row_factory = sqlite3.Row
        cls.collection_name = collection_name or cls.__name__.lower() + "s"
        cls._ensure_table()

    @classmethod
    def detach(cls):
        if cls.connection and cls._owns_connection:
            cls.connection.close()

        cls.connection = None
        cls.collection_name = "collections"
        cls._owns_connection = False

    @classmethod
    def collection(cls) -> sqlite3.Connection:
        if not cls.connection:
            raise FlexmodelLiteException("Database is not attached. Call attach() first.")

        return cls.connection

    @classmethod
    def _ensure_table(cls):
        cls.collection().execute(
            f"""
            CREATE TABLE IF NOT EXISTS {cls.collection_name} (
                _id TEXT PRIMARY KEY,
                _updated_at DATETIME NOT NULL,
                document JSON NOT NULL
            )
            """
        )
        cls.collection().commit()

    @classmethod
    def _execute(cls, query: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cursor = cls.collection().execute(query, params)
        cls.collection().commit()
        return cursor

    def is_committable(self) -> bool:
        return self.schema.is_submittable(self.__dict__)

    def commit(self, commit_all: bool = True) -> bool:
        if not self.is_committable():
            return False

        if commit_all:
            for item in [item for _, item in self.__dict__.items() if isinstance(item, FlexmodelLite)]:
                if not item.commit(commit_all=commit_all):
                    return False

        self.update(_updated_at=datetime.now(timezone.utc).isoformat())

        document = json.dumps(self.to_dict(commit=False), ensure_ascii=False)

        self._execute(
            f"""
            INSERT INTO {self.collection_name} (_id, _updated_at, document)
            VALUES (?, ?, ?)
            ON CONFLICT(_id) DO UPDATE SET
                _updated_at = excluded._updated_at,
                document = excluded.document
            """,
            (self.id, self.updated_at, document),
        )

        return True

    def delete(self) -> bool:
        cursor = self._execute(f"DELETE FROM {self.collection_name} WHERE _id = ?", (self.id,))
        return cursor.rowcount > 0

    @classmethod
    def load(cls, id: str) -> Optional["FlexmodelLite"]:
        cursor = cls._execute(f"SELECT _id, _updated_at, document FROM {cls.collection_name} WHERE _id = ?", (id,))
        row = cursor.fetchone()

        if not row:
            return None

        data = json.loads(row["document"])
        data.setdefault("_id", row["_id"])
        data.setdefault("_updated_at", row["_updated_at"])

        return cls(**data)

    @classmethod
    def count(cls) -> int:
        cursor = cls._execute(f"SELECT COUNT(*) AS count FROM {cls.collection_name}")
        row = cursor.fetchone()
        return int(row["count"]) if row else 0

    @classmethod
    def all(cls) -> list["FlexmodelLite"]:
        cursor = cls._execute(f"SELECT _id, _updated_at, document FROM {cls.collection_name}")
        rows = cursor.fetchall()
        results: list[FlexmodelLite] = []

        for row in rows:
            data = json.loads(row["document"])
            data.setdefault("_id", row["_id"])
            data.setdefault("_updated_at", row["_updated_at"])
            results.append(cls(**data))

        return results

    @classmethod
    def select(cls) -> "FlexmodelLite.Select":
        return FlexmodelLite.Select(cls())

    class Select:
        def __init__(self, model: "FlexmodelLite"):
            self.model: "FlexmodelLite" = model
            self.sorts: dict[str, Any] = {}
            self.statements: dict[str, Any] = {}

        def __getattr__(self, name: str) -> "FlexmodelLite.Select.Statement":
            if name not in self.model.schema.fields:
                raise FlexmodelLiteException(f"Select statement: field '{name}' does not exist in the model schema.")

            return FlexmodelLite.Select.Statement(name, self.model.__dict__.get(name, self.model.schema[name].default))

        def __getitem__(self, name: str) -> "FlexmodelLite.Select.Statement":
            if name not in self.model.schema.fields:
                raise FlexmodelLiteException(f"Select statement: field '{name}' does not exist in the model schema.")

            return FlexmodelLite.Select.Statement(name, self.model.__dict__.get(name, self.model.schema[name].default))

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
            sql: str = "SELECT * FROM " + self.model.collection_name

            if len(self.statements) == 0:
                return sql

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
                        if isinstance(value, dict):
                            for op, val in value.items():
                                if op == "$eq":
                                    clauses.append(f"{key} = '{val}'")
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
                                elif op == "$exists":
                                    clauses.append(f"{key} IS {'NOT ' if not val else ''}NULL")
                                elif op == "$all":
                                    clauses.append(f"{key} CONTAINS ALL ({', '.join([json.dumps(v) for v in val])})")
                                elif op == "$where":
                                    clauses.append(f"{val}  -- JavaScript function, cannot be directly translated to SQL")
                                elif op == "$not":
                                    clauses.append(f"NOT ({parse_condition({key: val})})")
                        else:
                            clauses.append(f"{key} = '{value}'")

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

        @staticmethod
        def _get_value(data: dict[str, Any], path: str) -> tuple[bool, Any]:
            current: Any = data
            for part in path.split("."):
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return False, None
            return True, current

        def _eval_field(self, data: dict[str, Any], key: str, expected: Any) -> bool:
            exists, current = self._get_value(data, key)

            if isinstance(expected, dict):
                options = expected.get("$options", "")

                for op, val in expected.items():
                    if op == "$options":
                        continue
                    if op == "$eq":
                        if not exists or current != val:
                            return False
                    if op == "$ne":
                        if current == val:
                            return False
                    elif op == "$lt":
                        if not exists or current >= val:
                            return False
                    elif op == "$gt":
                        if not exists or current <= val:
                            return False
                    elif op == "$lte":
                        if not exists or current > val:
                            return False
                    elif op == "$gte":
                        if not exists or current < val:
                            return False
                    elif op == "$in":
                        if not isinstance(val, (list, tuple, set)) or current not in val:
                            return False
                    elif op == "$nin":
                        if isinstance(val, (list, tuple, set)) and current in val:
                            return False
                    elif op == "$regex":
                        if not exists or not isinstance(current, str):
                            return False
                        flags = re.IGNORECASE if "i" in options else 0
                        if not re.search(val, current, flags=flags):
                            return False
                    elif op == "$exists":
                        if bool(val) and not exists:
                            return False
                        if not bool(val) and exists:
                            return False
                    elif op == "$all":
                        if not isinstance(current, (list, tuple, set)):
                            return False
                        if not all(item in current for item in val):
                            return False
                    elif op == "$not":
                        if self._eval_field(data, key, val):
                            return False
                    elif op == "$where":
                        return False
                return True

            if not exists:
                return False

            return current == expected

        def _eval_condition(self, data: dict[str, Any], condition: dict[str, Any]) -> bool:
            for key, value in condition.items():
                if key == "$and":
                    if not all(self._eval_condition(data, item) for item in value):
                        return False
                elif key == "$or":
                    if not any(self._eval_condition(data, item) for item in value):
                        return False
                elif key == "$not":
                    if self._eval_condition(data, value):
                        return False
                else:
                    if not self._eval_field(data, key, value):
                        return False
            return True

        def _apply_sort(self, items: list[tuple["FlexmodelLite", dict[str, Any]]]) -> list[tuple["FlexmodelLite", dict[str, Any]]]:
            if not self.sorts:
                return items

            results = items[:]
            for field, direction in reversed(list(self.sorts.items())):
                results.sort(
                    key=lambda item: self._get_value(item[1], field)[1],
                    reverse=direction < 0,
                )
            return results

        def count(self) -> int:
            return len(self.fetch_all().results)

        def fetch(self) -> Optional["FlexmodelLite"]:
            pagination = self.fetch_all(current=1, results_per_page=1)
            return pagination.results[0] if pagination.results else None

        def fetch_all(self, current: int = 1, results_per_page: int = 10) -> "FlexmodelLite.Select.Pagination":
            count: int = 0
            results: list[FlexmodelLite] = []

            if current < 1:
                current = 1

            if results_per_page < 1:
                results_per_page = 10

            items = [(item, item.to_dict(commit=False)) for item in self.model.__class__.all()]

            if self.statements:
                items = [item for item in items if self._eval_condition(item[1], self.statements)]

            items = self._apply_sort(items)
            count = len(items)

            start = (current - 1) * results_per_page
            end = start + results_per_page
            results = [item[0] for item in items[start:end]]

            return FlexmodelLite.Select.Pagination(count, results, current=current, results_per_page=results_per_page)

        class Pagination:
            def __init__(self, count: int, results: list["FlexmodelLite"], *, current: int, results_per_page: int):
                self.count: int = count
                self.results: list["FlexmodelLite"] = results
                self.current: int = current
                self.results_per_page: int = results_per_page

            def __len__(self) -> int:
                return self.count

            def __iter__(self):
                for item in self.results:
                    yield item

            def map(self, callback):
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

            def __getattr__(self, name: str) -> "FlexmodelLite.Select.Statement":
                if not isinstance(self.model, Flex) or name not in self.model.schema.fields:
                    raise FlexmodelLiteException(f"Select statement: field '{self.name}' is not a Flex object, cannot access sub-field '{name}'.")

                return FlexmodelLite.Select.Statement(f"{self.name}.{name}", self.model.__dict__.get(name, self.model.schema[name].default))

            def __getitem__(self, name: str) -> "FlexmodelLite.Select.Statement":
                if not isinstance(self.model, Flex) or name not in self.model.schema.fields:
                    raise FlexmodelLiteException(f"Select statement: field '{self.name}' is not a Flex object, cannot access sub-field '{name}'.")

                return FlexmodelLite.Select.Statement(f"{self.name}.{name}", self.model.__dict__.get(name, self.model.schema[name].default))

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

            def asc(self) -> dict[str, Any]:
                return {self.name: 1}

            def desc(self) -> dict[str, Any]:
                return {self.name: -1}
