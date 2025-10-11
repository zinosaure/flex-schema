# Flex-Schema

A flexible and powerful schema validation library for Python with MongoDB integration. Flex-Schema provides a declarative way to define data models with built-in validation, type checking, and seamless database operations.

## Features

- **Declarative Schema Definition**: Define your data models with a clean, intuitive syntax
- **Type Safety**: Built-in type checking for common Python types (str, int, float, bool, list, tuple)
- **Field Validation**: Comprehensive validation with constraints (min/max length, patterns, nullable fields)
- **MongoDB Integration**: Seamless integration with MongoDB for CRUD operations
- **Nested Models**: Support for complex nested data structures
- **Auto-generated IDs**: Automatic UUID generation and timestamp tracking
- **Callbacks**: Transform field values with custom callback functions
- **Pagination**: Built-in pagination support for queries

## Installation

Install from GitHub for the latest changes:

```bash
pip install git+https://github.com/zinosaure/flex-schema.git@main
```

## Quick Start

Here's a simple example to get you started:

```python
from flexschema import Schema, Flexmodel, field, field_constraint
from pymongo import MongoClient

class User(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        email=field(
            str,
            nullable=False,
            constraint=field_constraint(pattern=r"[^@]+@[^@]+\.[^@]+"),
        ),
        age=field(int, default=0),
    )

# Connect to MongoDB
User.attach(MongoClient("mongodb://localhost:27017/mydb"), "users")

# Create and save a user
user = User(name="John Doe", email="john@example.com", age=30)
if user.commit():
    print("User saved successfully!")
    print(user.to_json(indent=2))
```

## Core Concepts

### Schema

A `Schema` defines the structure and validation rules for your data models. There are two ways to create a schema:

- `Schema(**fields)`: Basic schema without auto-generated fields
- `Schema.ident(**fields)`: Schema with auto-generated `_id` and `_updated_at` fields

### Field Types

Flex-Schema supports the following field types:

- **Primitives**: `str`, `int`, `float`, `bool`
- **Collections**: `list`, `tuple`
- **Nested Models**: Any class inheriting from `Flex` or `Flexmodel`

### Field Definition

Use the `field()` function to define schema fields with validation rules:

```python
field(
    type,                    # Field type (required)
    default=None,           # Default value
    nullable=True,          # Allow None values (True/False or int for min occurrences)
    constraint=...,         # Field constraints
    callback=None           # Value transformation function
)
```

### Field Constraints

Define validation rules using `field_constraint()`:

```python
field_constraint(
    item_type=None,         # Type for list items
    min_length=None,        # Minimum length/value
    max_length=None,        # Maximum length/value
    pattern=None            # Regex pattern (for strings)
)
```

## Models

### Flex

The `Flex` class is the base class for data models without database persistence:

```python
from flexschema import Schema, Flex, field

class Metadata(Flex):
    schema: Schema = Schema(
        created_by=field(str, default="system"),
        last_modified=field(str, nullable=True),
    )

meta = Metadata(created_by="admin")
print(meta.to_dict())
```

**Available Methods:**
- `is_schematic()`: Check if the model is valid
- `evaluate()`: Get validation errors
- `update(**data)`: Update model attributes
- `to_dict(commit=False)`: Convert to dictionary
- `to_json(indent=4, commit=False)`: Convert to JSON string

### Flexmodel

The `Flexmodel` class extends `Flex` with MongoDB persistence capabilities:

```python
from flexschema import Schema, Flexmodel, field
from pymongo import MongoClient

class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(float, default=0.0),
        in_stock=field(bool, default=True),
    )

# Attach to database
Product.attach(MongoClient("mongodb://localhost:27017/shop"), "products")

# Create and save
product = Product(name="Laptop", price=999.99)
product.commit()
```

**Instance Methods:**
- `commit(commit_all=True)`: Save to database
- `delete()`: Remove from database
- `id`: Get the document ID
- `updated_at`: Get last update timestamp

**Class Methods:**
- `attach(database, collection_name=None)`: Connect to MongoDB
- `detach()`: Disconnect from MongoDB
- `collection()`: Get the MongoDB collection
- `load(_id)`: Load a document by ID
- `fetch(queries)`: Find one document matching queries
- `fetch_all(queries={}, position=1, position_limit=10)`: Get paginated results
- `count()`: Count documents in collection
- `truncate()`: Drop the collection

## Complete Example

Here's a comprehensive example demonstrating nested models and validation:

```python
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
            callback=lambda v: v.title(),  # Transform to title case
        ),
        email=field(
            str,
            nullable=False,
            constraint=field_constraint(pattern=r"[^@]+@[^@]+\.[^@]+"),
        ),
        date_of_birth=field(
            str, 
            constraint=field_constraint(pattern=r"\d{4}-\d{2}-\d{2}")
        ),
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
        self.name: str = self.schema["name"].default
        self.login: Login = self.schema["login"].default
        super().__init__(**data)


if __name__ == "__main__":
    # Connect to MongoDB
    client = MongoClient("mongodb://localhost:27017/testdb")
    User.attach(client, "users")
    Login.attach(client, "logins")

    # Create a user
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

    # Save to database
    if user.commit():
        print(user.to_json(indent=4))
    else:
        print("Failed to save user:\n", user.evaluate())
```

## Validation

Flex-Schema provides comprehensive validation:

```python
from flexschema import Schema, Flexmodel, field, field_constraint

class Article(Flexmodel):
    schema: Schema = Schema.ident(
        title=field(
            str,
            nullable=False,
            constraint=field_constraint(min_length=5, max_length=100)
        ),
        content=field(
            str,
            nullable=False,
            constraint=field_constraint(min_length=50)
        ),
        tags=field(
            list,
            default=[],
            constraint=field_constraint(item_type=str)
        ),
    )

article = Article(title="Hi", content="Too short")

# Check if valid
if not article.is_schematic():
    errors = article.evaluate()
    print(errors)
    # Output will show validation errors:
    # {
    #   'title': "Field 'title': must have at least: 5 characters.",
    #   'content': "Field 'content': must have at least: 50 characters."
    # }
```

## Querying

### Fetch Single Document

```python
# Find by ID
user = User.load("user-id-123")

# Find by query
user = User.fetch({"email": "john@example.com"})
```

### Fetch Multiple Documents with Pagination

```python
# Get first page (10 items by default)
pagination = User.fetch_all(
    queries={"is_active": True},
    position=1,
    position_limit=20
)

print(f"Total items: {pagination.total_items}")
print(f"Current page: {pagination.position}")

for user in pagination:
    print(user.name)

# Convert to dict
result = pagination.to_dict()
```

### Count and Truncate

```python
# Count documents
total_users = User.count()

# Delete all documents
User.truncate()
```

## Advanced Features

### Callbacks

Transform field values automatically:

```python
class Person(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(
            str,
            callback=lambda v: v.strip().title()
        ),
        email=field(
            str,
            callback=lambda v: v.lower()
        ),
    )

person = Person(name="  john doe  ", email="JOHN@EXAMPLE.COM")
# name will be "John Doe", email will be "john@example.com"
```

### Nested References

When using `to_dict(commit=True)`, nested `Flexmodel` instances are converted to references:

```python
user = User(
    name="Alice",
    email="alice@example.com",
    login=Login(username="alice", password="password123")
)

# Save nested models
user.commit()

# Export with references
user_dict = user.to_dict(commit=True)
# login field will be: {"$id": "login-uuid"}
```

### Pattern Validation

Use regex patterns for complex validation:

```python
class Contact(Flexmodel):
    schema: Schema = Schema.ident(
        phone=field(
            str,
            constraint=field_constraint(
                pattern=r"^\+?1?\d{9,15}$"
            )
        ),
        zip_code=field(
            str,
            constraint=field_constraint(
                pattern=r"^\d{5}(-\d{4})?$"
            )
        ),
    )
```

## Error Handling

Flex-Schema raises `SchemaDefinitionException` for invalid schema definitions:

```python
from flexschema import Schema, field, SchemaDefinitionException

try:
    # This will raise an exception
    Schema(
        invalid_field=field(
            list,  # Missing item_type constraint
        )
    )
except SchemaDefinitionException as e:
    print(f"Schema error: {e}")
```

## Requirements

- Python >= 3.9
- pymongo

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Gino D. (@zinosaure) - zinosaure@outlook.com

## Links

- **Documentation**: https://github.com/zinosaure/flex-schema#readme
- **Issues**: https://github.com/zinosaure/flex-schema/issues
- **Source**: https://github.com/zinosaure/flex-schema