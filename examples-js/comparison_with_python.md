# Python vs Node.js/TypeScript API Comparison

This document shows the API differences between the Python and Node.js/TypeScript versions of flexschema.

## Basic Model Definition

### Python
```python
from flexschema import Schema, Flexmodel, field, field_constraint

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
```

### Node.js/TypeScript
```typescript
import { Schema, Flexmodel, field, fieldConstraint } from 'flexschema';

class User extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, { nullable: false }),
    email: field(String, {
      nullable: false,
      constraint: fieldConstraint({ pattern: '[^@]+@[^@]+\\.[^@]+' }),
    }),
    age: field(Number, { default: 0 }),
  });
}
```

## Database Connection

### Python
```python
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/mydb")
User.attach(client, "users")
```

### Node.js/TypeScript
```typescript
import { MongoClient } from 'mongodb';

const client = new MongoClient('mongodb://localhost:27017');
await client.connect();
User.attach(client.db('mydb'), 'users');
```

## CRUD Operations

### Python
```python
# Create
user = User(name="John Doe", email="john@example.com", age=30)
if user.commit():
    print("Saved!")

# Read
user = User.load("user-id-123")

# Update
user.update(age=31)
user.commit()

# Delete
user.delete()
```

### Node.js/TypeScript
```typescript
// Create
const user = new User({ name: 'John Doe', email: 'john@example.com', age: 30 });
if (await user.commit()) {
  console.log('Saved!');
}

// Read
const user = await User.load('user-id-123');

// Update
user.update({ age: 31 });
await user.commit();

// Delete
await user.delete();
```

## Query API - The Main Difference!

This is where the biggest differences appear due to JavaScript's lack of operator overloading.

### Python - Using Operators
```python
select = User.select()

# Comparison operators work naturally
select.where(select.age > 18)
select.where(select.age >= 21)
select.where(select.age < 65)
select.where(select.age <= 100)
select.where(select.name != "Admin")
select.where(select.email == "john@example.com")

# Fetch results
users = select.fetch_all(current=1, results_per_page=10)
```

### Node.js/TypeScript - Using Methods
```typescript
const select = User.select();

// Must use method calls instead of operators
select.where(select.age.gt(18));       // Greater than
select.where(select.age.gte(21));      // Greater than or equal
select.where(select.age.lt(65));       // Less than
select.where(select.age.lte(100));     // Less than or equal
select.where(select.name.ne('Admin')); // Not equal
select.where(select.email.eq('john@example.com')); // Equal

// Fetch results (note: async!)
const users = await select.fetchAll(1, 10);
```

## Boolean and Null Checks

### Python
```python
select.where(select.is_active.is_true())
select.where(select.is_active.is_false())
select.where(select.phone.is_null())
select.where(select.phone.is_not_null())
```

### Node.js/TypeScript
```typescript
select.where(select.isActive.isTrue());
select.where(select.isActive.isFalse());
select.where(select.phone.isNull());
select.where(select.phone.isNotNull());
```

## Range and IN Queries

### Python
```python
# Range
select.where(select.age.is_between(start=18, end=65))

# IN
select.where(select.role.is_in(items=["admin", "user"]))
```

### Node.js/TypeScript
```typescript
// Range
select.where(select.age.isBetween(18, 65));

// IN
select.where(select.role.isIn(['admin', 'user']));
```

## Logical Operators

### Python
```python
# AND
select.where(
    select.match(
        select.age > 18,
        select.age < 65
    )
)

# OR
select.where(
    select.at_least(
        select.age < 18,
        select.age > 65
    )
)
```

### Node.js/TypeScript
```typescript
// AND
select.where(
  select.match(
    select.age.gt(18),
    select.age.lt(65)
  )
);

// OR
select.where(
  select.atLeast(
    select.age.lt(18),
    select.age.gt(65)
  )
);
```

## Pattern Matching

### Python
```python
select.where(select.name.match("^John", options="i"))
```

### Node.js/TypeScript
```typescript
select.where(select.name.match('^John', 'i'));
```

## Sorting

### Python
```python
select.sort(select.age.asc())
select.sort(select.name.desc())
```

### Node.js/TypeScript
```typescript
select.sort(select.age.asc());
select.sort(select.name.desc());
```

## Type Definitions

### Python
```python
# Uses Python's type hints
name: str
age: int
is_active: bool
tags: list
```

### Node.js/TypeScript
```typescript
// Uses TypeScript types or JavaScript constructors
name: String  // or string in TypeScript
age: Number   // or number in TypeScript
isActive: Boolean  // or boolean in TypeScript
tags: Array   // or Array<string> in TypeScript
```

## Summary of Key Differences

| Feature | Python | Node.js/TypeScript |
|---------|--------|-------------------|
| **Comparison Operators** | `select.age > 18` | `select.age.gt(18)` |
| **Equality** | `select.name == "John"` | `select.name.eq('John')` |
| **Database Operations** | Synchronous | Async (returns Promises) |
| **Type System** | Runtime type hints | Compile-time TypeScript |
| **Pattern in Constraints** | `r"pattern"` | `'pattern'` or `/pattern/` |
| **Naming Convention** | snake_case | camelCase |
| **Array Syntax** | `list` | `Array` |
| **Class Properties** | `schema: Schema = ...` | `static schema = ...` |

## Full Working Example Comparison

### Python
```python
from pymongo import MongoClient
from flexschema import Schema, Flexmodel, field, field_constraint

class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(float, default=0.0),
        in_stock=field(bool, default=True),
    )

# Setup
client = MongoClient("mongodb://localhost:27017/shop")
Product.attach(client, "products")

# Query
select = Product.select()
select.where(select.price > 100)
select.where(select.in_stock.is_true())
products = select.fetch_all(current=1, results_per_page=10)

for product in products:
    print(f"{product.name}: ${product.price}")
```

### Node.js/TypeScript
```typescript
import { MongoClient } from 'mongodb';
import { Schema, Flexmodel, field } from 'flexschema';

class Product extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, { nullable: false }),
    price: field(Number, { default: 0.0 }),
    inStock: field(Boolean, { default: true }),
  });
}

// Setup
const client = new MongoClient('mongodb://localhost:27017');
await client.connect();
Product.attach(client.db('shop'), 'products');

// Query
const select = Product.select();
select.where(select.price.gt(100));
select.where(select.inStock.isTrue());
const products = await select.fetchAll(1, 10);

for (const product of products) {
  console.log(`${product.name}: $${product.price}`);
}
```

## Why These Differences?

1. **Operator Overloading**: Python supports `__eq__`, `__gt__`, etc. operators. JavaScript does not, so we use methods.

2. **Async Operations**: Node.js is inherently asynchronous, so database operations return Promises.

3. **Type System**: TypeScript provides compile-time type checking, while Python uses runtime type hints.

4. **Language Conventions**: Python uses snake_case, JavaScript/TypeScript uses camelCase.

Despite these differences, the overall API design and functionality remain the same, making it easy to port code between the two versions.
