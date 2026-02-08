# Migration Guide: Python to Node.js/TypeScript

This guide helps you migrate your Python flexschema code to Node.js/TypeScript.

## Quick Reference

| Operation | Python | Node.js/TypeScript |
|-----------|--------|-------------------|
| Import | `from flexschema import ...` | `import { ... } from 'flexschema'` |
| Types | `str, int, float, bool, list` | `String, Number, Boolean, Array` |
| Static Schema | `schema: Schema = ...` | `static schema = ...` |
| Comparison | `select.age > 18` | `select.age.gt(18)` |
| Equality | `select.name == "x"` | `select.name.eq('x')` |
| DB Operations | Synchronous | `await` (async) |
| Naming | `snake_case` | `camelCase` |

## Step-by-Step Migration

### Step 1: Install Dependencies

**Python:**
```bash
pip install flexschema
```

**Node.js:**
```bash
npm install flexschema
# or
yarn add flexschema
```

### Step 2: Update Imports

**Python:**
```python
from flexschema import Schema, Flex, Flexmodel, field, field_constraint
from pymongo import MongoClient
```

**Node.js:**
```javascript
const { Schema, Flex, Flexmodel, field, fieldConstraint } = require('flexschema');
const { MongoClient } = require('mongodb');
```

**TypeScript:**
```typescript
import { Schema, Flex, Flexmodel, field, fieldConstraint } from 'flexschema';
import { MongoClient } from 'mongodb';
```

### Step 3: Convert Model Definitions

**Python:**
```python
class User(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        email=field(
            str,
            nullable=False,
            constraint=field_constraint(pattern=r"[^@]+@[^@]+\.[^@]+"),
        ),
        age=field(int, default=0),
        is_active=field(bool, default=True),
        tags=field(list, default=[], constraint=field_constraint(item_type=str)),
    )
```

**Node.js/JavaScript:**
```javascript
class User extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, { nullable: false }),
    email: field(String, {
      nullable: false,
      constraint: fieldConstraint({ pattern: '[^@]+@[^@]+\\.[^@]+' }),
    }),
    age: field(Number, { default: 0 }),
    isActive: field(Boolean, { default: true }),
    tags: field(Array, { 
      default: [], 
      constraint: fieldConstraint({ itemType: String })
    }),
  });
}
```

**TypeScript (with type annotations):**
```typescript
class User extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, { nullable: false }),
    email: field(String, {
      nullable: false,
      constraint: fieldConstraint({ pattern: '[^@]+@[^@]+\\.[^@]+' }),
    }),
    age: field(Number, { default: 0 }),
    isActive: field(Boolean, { default: true }),
    tags: field(Array, { 
      default: [], 
      constraint: fieldConstraint({ itemType: String })
    }),
  });

  // Optional: Add TypeScript properties for IDE support
  _id!: string;
  _updated_at!: string;
  name!: string;
  email!: string;
  age!: number;
  isActive!: boolean;
  tags!: string[];
}
```

### Step 4: Update Database Connection

**Python:**
```python
client = MongoClient("mongodb://localhost:27017/mydb")
User.attach(client, "users")
```

**Node.js:**
```javascript
const client = new MongoClient('mongodb://localhost:27017');
await client.connect();
User.attach(client.db('mydb'), 'users');
```

### Step 5: Convert CRUD Operations to Async

**Python:**
```python
# Create
user = User(name="John", email="john@example.com")
if user.commit():
    print("Saved!")

# Read
user = User.load("id123")

# Delete
user.delete()
```

**Node.js:**
```javascript
// Create
const user = new User({ name: 'John', email: 'john@example.com' });
if (await user.commit()) {
  console.log('Saved!');
}

// Read
const user = await User.load('id123');

// Delete
await user.delete();
```

### Step 6: Convert Query Operators

This is the most significant change due to JavaScript's lack of operator overloading.

**Python:**
```python
select = User.select()

# Comparisons
select.where(select.age > 18)
select.where(select.age >= 21)
select.where(select.age < 65)
select.where(select.age <= 100)
select.where(select.name != "Admin")
select.where(select.email == "john@example.com")

# Boolean
select.where(select.is_active.is_true())
select.where(select.is_active.is_false())

# Null checks
select.where(select.phone.is_null())
select.where(select.phone.is_not_null())

# Range
select.where(select.age.is_between(start=18, end=65))

# IN
select.where(select.role.is_in(items=["admin", "user"]))

# Pattern
select.where(select.name.match("^John", options="i"))

# Sorting
select.sort(select.name.asc())

# Fetch
users = select.fetch_all(current=1, results_per_page=10)
```

**Node.js:**
```javascript
const select = User.select();

// Comparisons - use method calls
select.where(select.age.gt(18));
select.where(select.age.gte(21));
select.where(select.age.lt(65));
select.where(select.age.lte(100));
select.where(select.name.ne('Admin'));
select.where(select.email.eq('john@example.com'));

// Boolean
select.where(select.isActive.isTrue());
select.where(select.isActive.isFalse());

// Null checks
select.where(select.phone.isNull());
select.where(select.phone.isNotNull());

// Range
select.where(select.age.isBetween(18, 65));

// IN
select.where(select.role.isIn(['admin', 'user']));

// Pattern
select.where(select.name.match('^John', 'i'));

// Sorting
select.sort(select.name.asc());

// Fetch (note: async!)
const users = await select.fetchAll(1, 10);
```

### Step 7: Update Logical Operators

**Python:**
```python
# AND
select.where(
    select.match(
        select.age > 18,
        select.is_active.is_true()
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

**Node.js:**
```javascript
// AND
select.where(
  select.match(
    select.age.gt(18),
    select.isActive.isTrue()
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

## Common Pitfalls

### 1. Forgetting `await`

❌ **Wrong:**
```javascript
const user = User.load('id123');  // Returns a Promise!
console.log(user.name);  // Error: user is a Promise
```

✅ **Correct:**
```javascript
const user = await User.load('id123');
console.log(user.name);  // Works!
```

### 2. Using Python Operators

❌ **Wrong:**
```javascript
select.where(select.age > 18);  // This doesn't work in JavaScript!
```

✅ **Correct:**
```javascript
select.where(select.age.gt(18));
```

### 3. Forgetting `static` Keyword

❌ **Wrong:**
```javascript
class User extends Flexmodel {
  schema = Schema.ident({...});  // Missing 'static'
}
```

✅ **Correct:**
```javascript
class User extends Flexmodel {
  static schema = Schema.ident({...});
}
```

### 4. Wrong Type Constructors

❌ **Wrong:**
```javascript
name: field(str, { nullable: false })  // Python types don't exist
```

✅ **Correct:**
```javascript
name: field(String, { nullable: false })
```

### 5. Naming Convention

❌ **Python style:**
```javascript
is_active: field(Boolean, { default: true })
```

✅ **JavaScript style:**
```javascript
isActive: field(Boolean, { default: true })
```

## Migration Checklist

- [ ] Install Node.js dependencies
- [ ] Update all imports
- [ ] Convert `schema:` to `static schema =`
- [ ] Change type names: `str` → `String`, `int` → `Number`, `bool` → `Boolean`, `list` → `Array`
- [ ] Update field names from `snake_case` to `camelCase`
- [ ] Change `field_constraint` to `fieldConstraint`
- [ ] Add `await` to all database operations
- [ ] Replace comparison operators with method calls (`.gt()`, `.eq()`, etc.)
- [ ] Update `is_between(start=x, end=y)` to `isBetween(x, y)`
- [ ] Update `is_in(items=[...])` to `isIn([...])`
- [ ] Replace `r"pattern"` with `'pattern'` or escape backslashes
- [ ] Test all queries with the new syntax
- [ ] Update error handling for async operations

## Full Example Migration

### Before (Python)

```python
from pymongo import MongoClient
from flexschema import Schema, Flexmodel, field, field_constraint

class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(float, default=0.0),
        in_stock=field(bool, default=True),
        tags=field(list, default=[], constraint=field_constraint(item_type=str)),
    )

# Connect
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

### After (Node.js)

```javascript
const { MongoClient } = require('mongodb');
const { Schema, Flexmodel, field, fieldConstraint } = require('flexschema');

class Product extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, { nullable: false }),
    price: field(Number, { default: 0.0 }),
    inStock: field(Boolean, { default: true }),
    tags: field(Array, { 
      default: [], 
      constraint: fieldConstraint({ itemType: String })
    }),
  });
}

async function main() {
  // Connect
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

  await client.close();
}

main().catch(console.error);
```

## Need Help?

- Check `README-NODEJS.md` for complete API documentation
- See `examples-js/comparison_with_python.md` for side-by-side examples
- Review the example files in `examples-js/` directory
- Open an issue on GitHub if you encounter migration problems

## TypeScript Benefits

If you're using TypeScript, you get additional benefits:

```typescript
class User extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, { nullable: false }),
    age: field(Number, { default: 0 }),
  });

  // Add type annotations for IDE support
  name!: string;
  age!: number;
}

// TypeScript will now provide autocomplete and type checking!
const user = new User({ name: 'John', age: 30 });
user.name.toUpperCase();  // IDE knows name is a string
user.age.toFixed(2);      // IDE knows age is a number
```

Happy migrating! 🚀
