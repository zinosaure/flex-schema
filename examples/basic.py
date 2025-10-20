import time

from typing import Any
from pymongo import MongoClient
from flexschema import Schema, Flex, Flexmodel, field, field_constraint


class Login(Flexmodel):
    schema: Schema = Schema.ident(
        username=field(str, nullable=False),
        password=field(
            str,
            nullable=False,
            constraint=field_constraint(min_length=8),
        ),
    )


class Metadata(Flex):
    schema: Schema = Schema(
        created_by=field(str, nullable=False, default="system"),
        last_login=field(int, default=int(time.time())),
    )


class User(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(
            str,
            default="prenom et nom",
            callback=lambda v: v.title(),
        ),
        email=field(
            str,
            nullable=False,
            constraint=field_constraint(pattern=r"[^@]+@[^@]+\.[^@]+"),
        ),
        date_of_birth=field(str, constraint=field_constraint(pattern=r"\d{4}-\d{2}-\d{2}")),
        login=field(
            Login,
            nullable=False,
            default=Login(),
        ),
        tags=field(
            list,
            nullable=False,
            default=[],
            constraint=field_constraint(item_type=str),
        ),
        is_active=field(bool, default=True),
        score=field(float, default=0.0),
        metadata=field(
            Metadata,
            nullable=False,
            default=Metadata(),
        ),
    )

    def __init__(self, **data: Any):
        self.name: str = self.schema["name"].default  # setting default value from schema
        self.login: Login = self.schema["login"].default  # setting default value from schema

        super().__init__(**data)


if __name__ == "__main__":
    try:
        # Try to connect to MongoDB
        User.attach(client := MongoClient("mongodb://localhost:27017/testdb", serverSelectionTimeoutMS=1000), "users")
        Login.attach(client, "logins")

        user = User(
            name="john doe",
            email="john.doe@example.com",
            date_of_birth="1990-01-01",
            login=Login(username="johndoe", password="securepassword"),
            tags=["user", "admin"],
            is_active=True,
            score=100.0,
            metadata=Metadata(created_by="admin", last_login=int(time.time())),
        )

        if user.commit():
            print(user.to_json(indent=4))
        else:
            print("Failed to save user:\n", user.evaluate())
    except Exception as e:
        print(f"⚠️  MongoDB not available: {e}")
        print("\nShowing user data without saving to database:")
        user = User(
            name="john doe",
            email="john.doe@example.com",
            date_of_birth="1990-01-01",
            login=Login(username="johndoe", password="securepassword"),
            tags=["user", "admin"],
            is_active=True,
            score=100.0,
            metadata=Metadata(created_by="admin", last_login=int(time.time())),
        )
        print(user.to_json(indent=4))
        print("\nTo save to database, start MongoDB at localhost:27017")
