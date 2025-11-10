# Flex-Schema - Node.js/TypeScript Port

A flexible and powerful schema validation library for Node.js/TypeScript with MongoDB integration and ORM-style query API. This is a complete port of the Python flexschema library to Node.js/TypeScript.

## Features

- **Declarative Schema Definition**: Define your data models with a clean, intuitive syntax
- **Type Safety**: Built-in type checking with TypeScript support
- **Field Validation**: Comprehensive validation with constraints (min/max length, patterns, nullable fields)
- **MongoDB Integration**: Seamless integration with MongoDB for CRUD operations
- **ORM-Style Query API**: Intuitive, chainable query builder with type-safe field access
- **Nested Models**: Support for complex nested data structures
- **Auto-generated IDs**: Automatic UUID generation and timestamp tracking
- **Callbacks**: Transform field values with custom callback functions
- **Pagination**: Built-in pagination support for queries

## Installation

```bash
npm install flexschema
```

Or install from source:

```bash
git clone https://github.com/zinosaure/flex-schema.git
cd flex-schema
npm install
npm run build
```

## Quick Start

Here's a simple example to get you started:

```typescript
import { MongoClient } from 'mongodb';
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

// Connect to MongoDB
const client = new MongoClient('mongodb://localhost:27017');
await client.connect();
User.attach(client.db('mydb'), 'users');

// Create and save a user
const user = new User({
  name: 'John Doe',
  email: 'john@example.com',
  age: 30,
});

if (await user.commit()) {
  console.log('User saved successfully!');
  console.log(user.toJson());
}
```

## Core Concepts

### Schema

A `Schema` defines the structure and validation rules for your data models. There are two ways to create a schema:

- `new Schema({...fields})`: Basic schema without auto-generated fields
- `Schema.ident({...fields})`: Schema with auto-generated `_id` and `_updated_at` fields

### Field Types

Flex-Schema supports the following field types:

- **Primitives**: `String`, `Number`, `Boolean`
- **Collections**: `Array`
- **Nested Models**: Any class extending `Flex` or `Flexmodel`

### Field Definition

Use the `field()` function to define schema fields with validation rules:

```typescript
field(
  type,                   // Field type (required)
  {
    default: null,        // Default value
    nullable: true,       // Allow null values (true/false or number for min occurrences)
    constraint: ...,      // Field constraints
    callback: null        // Value transformation function
  }
)
```

### Field Constraints

Define validation rules using `fieldConstraint()`:

```typescript
fieldConstraint({
  itemType: null,         // Type for array items
  minLength: null,        // Minimum length/value
  maxLength: null,        // Maximum length/value
  pattern: null           // Regex pattern (for strings)
})
```

## Models

### Flex

The `Flex` class is the base class for data models without database persistence:

```typescript
import { Schema, Flex, field } from 'flexschema';

class Metadata extends Flex {
  static schema = new Schema({
    createdBy: field(String, { default: 'system' }),
    lastModified: field(String, { nullable: true }),
  });
}

const meta = new Metadata({ createdBy: 'admin' });
console.log(meta.toDict());
```

**Available Methods:**
- `isSchematic()`: Check if the model is valid
- `evaluate()`: Get validation errors
- `update(data)`: Update model attributes
- `toDict(commit)`: Convert to object
- `toJson(indent, commit)`: Convert to JSON string

### Flexmodel

The `Flexmodel` class extends `Flex` with MongoDB persistence capabilities:

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

// Attach to database
const client = new MongoClient('mongodb://localhost:27017');
await client.connect();
Product.attach(client.db('shop'), 'products');

// Create and save
const product = new Product({ name: 'Laptop', price: 999.99 });
await product.commit();
```

**Instance Methods:**
- `commit(commitAll)`: Save to database
- `delete()`: Remove from database
- `id`: Get the document ID
- `updatedAt`: Get last update timestamp

**Class Methods:**
- `attach(database, collectionName)`: Connect to MongoDB (accepts MongoClient or Db)
- `detach()`: Disconnect from MongoDB
- `load(id)`: Load a document by ID
- `count()`: Count documents in collection
- `select()`: Create an ORM-style query builder

## ORM-Style Query API

**Important Note:** Unlike Python, JavaScript/TypeScript doesn't allow overriding comparison operators (`==`, `<`, `>`, etc.). Therefore, the query API uses method calls instead:

```typescript
const select = Product.select();

// Instead of: select.where(select.price > 100)
// Use: select.where(select.price.gt(100))

// Comparison methods
select.where(select.price.gt(100));        // Greater than
select.where(select.price.gte(50));        // Greater than or equal
select.where(select.price.lt(1000));       // Less than
select.where(select.price.lte(500));       // Less than or equal
select.where(select.name.ne('Mouse'));     // Not equal
select.where(select.name.eq('Laptop'));    // Equal

// Boolean queries
select.where(select.inStock.isTrue());
select.where(select.inStock.isFalse());

// Null and empty checks
select.where(select.name.isNull());
select.where(select.name.isNotNull());
select.where(select.name.isEmpty());
select.where(select.name.isNotEmpty());

// Range queries
select.where(select.price.isBetween(50, 500));
select.where(select.price.isNotBetween(50, 500));

// IN queries
select.where(select.category.isIn(['electronics', 'furniture']));
select.where(select.category.isNotIn(['stationery']));

// Pattern matching (regex)
select.where(select.name.match('^Lap', 'i'));
select.where(select.name.notMatch('^Mouse', 'i'));

// Logical AND (match)
select.where(
  select.match(
    select.price.gt(50),
    select.price.lt(500),
    select.inStock.isTrue()
  )
);

// Logical OR (atLeast)
select.where(
  select.atLeast(
    select.price.lt(50),
    select.price.gt(1000)
  )
);

// Sorting
select.sort(select.price.asc());   // Ascending
select.sort(select.price.desc());  // Descending

// Fetch results
const products = await select.fetchAll({ current: 1, resultsPerPage: 10 });
for (const product of products) {
  console.log(product.name);
}

// Count results
const total = await select.count();

// SQL conversion (for debugging/logging)
const sqlQuery = select.toSql;
console.log(sqlQuery);  // SELECT * FROM products WHERE ...

// Clear query and start fresh
select.discard();
```

## Complete Example

```typescript
import { MongoClient } from 'mongodb';
import { Schema, Flex, Flexmodel, field, fieldConstraint } from 'flexschema';

class Login extends Flexmodel {
  static schema = Schema.ident({
    username: field(String, { nullable: false }),
    password: field(String, {
      nullable: false,
      constraint: fieldConstraint({ minLength: 8 }),
    }),
  });
}

class Metadata extends Flex {
  static schema = new Schema({
    createdBy: field(String, { nullable: false, default: 'system' }),
    lastLogin: field(Number, { default: Math.floor(Date.now() / 1000) }),
  });
}

class User extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, {
      default: 'prenom et nom',
      callback: (v) => v.charAt(0).toUpperCase() + v.slice(1),
    }),
    email: field(String, {
      nullable: false,
      constraint: fieldConstraint({ pattern: '[^@]+@[^@]+\\.[^@]+' }),
    }),
    dateOfBirth: field(String, {
      constraint: fieldConstraint({ pattern: '\\d{4}-\\d{2}-\\d{2}' }),
    }),
    login: field(Login, {
      nullable: false,
      default: new Login(),
    }),
    tags: field(Array, {
      nullable: false,
      default: [],
      constraint: fieldConstraint({ itemType: String }),
    }),
    isActive: field(Boolean, { default: true }),
    score: field(Number, { default: 0.0 }),
    metadata: field(Metadata, {
      nullable: false,
      default: new Metadata(),
    }),
  });
}

async function main() {
  // Connect to MongoDB
  const client = new MongoClient('mongodb://localhost:27017');
  await client.connect();
  
  User.attach(client.db('testdb'), 'users');
  Login.attach(client.db('testdb'), 'logins');

  // Create a user
  const user = new User({
    name: 'john doe',
    email: 'john.doe@example.com',
    dateOfBirth: '1990-01-01',
    login: new Login({
      username: 'johndoe',
      password: 'securepassword',
    }),
    tags: ['user', 'admin'],
    isActive: true,
    score: 100.0,
    metadata: new Metadata({
      createdBy: 'admin',
      lastLogin: Math.floor(Date.now() / 1000),
    }),
  });

  // Save to database
  if (await user.commit()) {
    console.log(user.toJson(4));
  } else {
    console.log('Failed to save user:', user.evaluate());
  }

  await client.close();
}

main().catch(console.error);
```

## Validation

Flex-Schema provides comprehensive validation:

```typescript
import { Schema, Flexmodel, field, fieldConstraint } from 'flexschema';

class Article extends Flexmodel {
  static schema = Schema.ident({
    title: field(String, {
      nullable: false,
      constraint: fieldConstraint({ minLength: 5, maxLength: 100 }),
    }),
    content: field(String, {
      nullable: false,
      constraint: fieldConstraint({ minLength: 50 }),
    }),
    tags: field(Array, {
      default: [],
      constraint: fieldConstraint({ itemType: String }),
    }),
  });
}

const article = new Article({
  title: 'Hi',
  content: 'Too short',
});

// Check if valid
if (!article.isSchematic()) {
  const errors = article.evaluate();
  console.log(errors);
  // Output will show validation errors
}
```

## Differences from Python Version

1. **Operator Overloading**: JavaScript/TypeScript doesn't support operator overloading, so comparison operations use method calls:
   - Python: `select.price > 100`
   - Node.js: `select.price.gt(100)`

2. **Type System**: TypeScript provides static type checking, while Python uses runtime type hints

3. **Async/Await**: All database operations are async and return Promises

4. **Class Properties**: Static schema properties are declared differently in JavaScript

## Requirements

- Node.js >= 16.0.0
- MongoDB driver (`mongodb` package)
- TypeScript >= 5.0.0 (for TypeScript projects)

## Building

```bash
npm run build
```

## Running Examples

```bash
# Build first
npm run build

# Run basic example
npm run example:basic

# Run query example
npm run example:query
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Author

Gino D. (@zinosaure) - zinosaure@outlook.com

## Links

- **Python Version**: https://github.com/zinosaure/flex-schema
- **Issues**: https://github.com/zinosaure/flex-schema/issues
- **Source**: https://github.com/zinosaure/flex-schema
