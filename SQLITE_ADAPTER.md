# FlexmodelSQLite - SQLite3 Adapter for Flex-Schema

## Overview

FlexmodelSQLite is a SQLite3 adapter for Flex-Schema that provides the same functionality as Flexmodel but uses SQLite instead of MongoDB.

**Note:** FlexmodelSQLite is now an alias to Flexmodel. The unified Flexmodel class supports both MongoDB and SQLite backends seamlessly.

## Key Features

### 1. SQLite Table Structure

Each model is stored in a SQLite table with the following structure:
- **_id** (TEXT PRIMARY KEY): Unique UUID identifier
- **_updated_at** (TEXT): ISO format timestamp
- **document** (TEXT): Complete JSON representation of the document

### 2. Available Methods

FlexmodelSQLite provides exactly the same methods as Flexmodel:

#### Instance Methods:
- `commit(commit_all=True)`: Save to database
- `delete()`: Remove from database
- `id`: Get the document ID
- `updated_at`: Get the last update timestamp

#### Class Methods:
- `attach(database, table_name=None)`: Connect to SQLite database
- `detach()`: Disconnect from database
- `load(_id)`: Load a document by ID
- `fetch(queries)`: Find one document matching queries
- `fetch_all(queries={}, page=1, item_per_page=10)`: Get paginated results
- `count()`: Count documents in table
- `truncate()`: Delete all records from table

### 3. Usage Example

```python
import sqlite3
from flexschema import Schema, FlexmodelSQLite, field, field_constraint

# Define a model
class User(FlexmodelSQLite):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        email=field(
            str,
            nullable=False,
            constraint=field_constraint(pattern=r"[^@]+@[^@]+\.[^@]+"),
        ),
        age=field(int, default=0),
    )

# Connect to SQLite
conn = sqlite3.connect("database.sqlite")
User.attach(conn, "users")

# Create and save
user = User(name="John Doe", email="john@example.com", age=30)
user.commit()

# Load by ID
loaded_user = User.load(user.id)

# Search
found_user = User.fetch({"email": "john@example.com"})

# Pagination
results = User.fetch_all({}, page=1, item_per_page=10)
for user in results:
    print(user.to_json())
```

### 4. Advanced Features

#### Nested Models
FlexmodelSQLite supports nested models like Flexmodel:

```python
class Address(Flex):
    schema = Schema(
        street=field(str, nullable=False),
        city=field(str, nullable=False),
    )

class Person(FlexmodelSQLite):
    schema = Schema.ident(
        name=field(str, nullable=False),
        address=field(Address, nullable=False, default=Address()),
    )
```

#### Schema Validation
All schema validations work exactly like with Flexmodel:

```python
class Product(FlexmodelSQLite):
    schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(
            float,
            nullable=False,
            constraint=field_constraint(min_length=0),
        ),
    )

product = Product(name="Laptop", price=999.99)
if product.commit():
    print("Product saved!")
else:
    print("Errors:", product.evaluate())
```

#### MongoDB-Style Query Operators

FlexmodelSQLite fully supports MongoDB-style query operators for advanced filtering:

```python
# Comparison operators
products = Product.fetch_all({"price": {"$gt": 100}})
products = Product.fetch_all({"quantity": {"$gte": 10}})
products = Product.fetch_all({"price": {"$lt": 50}})

# Array operators
products = Product.fetch_all({
    "category": {"$in": ["electronics", "computers"]}
})

# Logical operators
products = Product.fetch_all({
    "$or": [
        {"price": {"$lt": 50}},
        {"price": {"$gt": 1000}}
    ]
})

# Existence operator
users = User.fetch_all({"phone": {"$exists": True}})

# Complex combined queries
results = Product.fetch_all({
    "$or": [
        {"$and": [{"category": "electronics"}, {"price": {"$gte": 100}}]},
        {"$and": [{"category": "furniture"}, {"in_stock": True}]}
    ]
})
```

All query operators work identically to MongoDB, making it easy to switch between databases.

## Tests

Comprehensive tests are available in `tests/test_sqlite.py` and `tests/test_mongodb_operators.py`:
- Basic CRUD tests
- Nested model tests
- Schema validation tests
- Table structure tests
- Pagination tests
- MongoDB operator tests (comparison, array, logical, existence)

To run the tests:
```bash
python tests/test_sqlite.py
python tests/test_mongodb_operators.py
```

## Differences with Flexmodel

The only major difference is the underlying storage:
- **Flexmodel**: Uses MongoDB (collections, documents)
- **FlexmodelSQLite**: Uses SQLite (tables, JSON)

The API remains identical to facilitate migration between the two backends.

## SQLite Advantages

- No server required (file-based database)
- Perfect for embedded applications
- Excellent for development and testing
- Portable and simple to deploy
- Full ACID transactions
