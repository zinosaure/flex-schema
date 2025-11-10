const { MongoClient } = require('mongodb');
const { Schema, Flexmodel, field } = require('../dist/index');

class Product extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, { nullable: false }),
    price: field(Number, { default: 0.0 }),
    inStock: field(Boolean, { default: true }),
  });

  constructor(data = {}) {
    super(data);
    if (!this.name) {
      this.name = Product.schema.get('name').default;
    }
    if (this.price === undefined) {
      this.price = Product.schema.get('price').default;
    }
    if (this.inStock === undefined) {
      this.inStock = Product.schema.get('inStock').default;
    }
  }
}

async function main() {
  try {
    const client = new MongoClient('mongodb://localhost:27017/testdb', {
      serverSelectionTimeoutMS: 1000,
    });
    
    await client.connect();
    
    Product.attach(client.db(), 'products');

    // Create a select query using Proxy-based field access
    const select = Product.select();

    // Note: In JavaScript/TypeScript, we can't override comparison operators (==, <, >, etc.)
    // So we need to use method calls instead
    select.where(select.name.eq('Shoes'));
    select.where(
      select.match(
        select.atLeast(
          select.inStock.isFalse(),
          select.inStock.isTrue()
        ),
        select.price.lt(100)
      )
    );

    console.log('Query built successfully!');
    console.log(`Query: ${select.queryString}`);
    console.log(`SQL: ${select.toSql}`);

    // Try to fetch results (will fail if MongoDB is not running)
    try {
      const results = await select.fetchAll();
      for (const item of results) {
        console.log(`Product: ${item.name}, Price: ${item.price}, In Stock: ${item.inStock}`);
      }
    } catch (e) {
      console.log(`\n⚠️  Could not fetch from database: ${e.message}`);
      console.log('This is expected if MongoDB is not running.');
    }

    await client.close();
  } catch (e) {
    console.log(`⚠️  MongoDB not available: ${e.message}`);
    console.log('To run this example with database access, start MongoDB at localhost:27017');
  }
}

main().catch(console.error);
