import { MongoClient } from 'mongodb';
import {
  Schema,
  Flex,
  Flexmodel,
  field,
  fieldConstraint,
} from '../src-js/index';

// Example 1: Simple Flex class (no database)
class Address extends Flex {
  static schema = new Schema({
    street: field(String, { nullable: false }),
    city: field(String, { nullable: false }),
    zipCode: field(String, {
      constraint: fieldConstraint({ pattern: '^\\d{5}$' }),
    }),
  });

  // TypeScript properties for better IDE support
  street!: string;
  city!: string;
  zipCode!: string;
}

// Example 2: Flexmodel with MongoDB (with database)
class User extends Flexmodel {
  static schema = Schema.ident({
    name: field(String, {
      nullable: false,
      callback: (v: string) => v.trim().toLowerCase(),
    }),
    email: field(String, {
      nullable: false,
      constraint: fieldConstraint({ pattern: '[^@]+@[^@]+\\.[^@]+' }),
    }),
    age: field(Number, {
      constraint: fieldConstraint({ minLength: 0, maxLength: 150 }),
    }),
    address: field(Address, {
      nullable: false,
      default: new Address(),
    }),
    tags: field(Array, {
      default: [],
      constraint: fieldConstraint({ itemType: String }),
    }),
  });

  // TypeScript properties
  _id!: string;
  _updated_at!: string;
  name!: string;
  email!: string;
  age!: number;
  address!: Address;
  tags!: string[];
}

async function main(): Promise<void> {
  try {
    // Connect to MongoDB
    const client = new MongoClient('mongodb://localhost:27017', {
      serverSelectionTimeoutMS: 1000,
    });

    await client.connect();
    console.log('✅ Connected to MongoDB\n');

    // Attach User model to database
    User.attach(client.db('testdb'), 'users');

    // Example 1: Create a user
    console.log('Example 1: Creating a user');
    const user = new User({
      name: '  John Doe  ',
      email: 'john.doe@example.com',
      age: 30,
      address: new Address({
        street: '123 Main St',
        city: 'Springfield',
        zipCode: '12345',
      }),
      tags: ['developer', 'typescript', 'nodejs'],
    });

    console.log('User object created:');
    console.log(user.toJson(2));

    // Validate
    if (user.isSchematic()) {
      console.log('✅ User is valid\n');

      // Save to database
      if (await user.commit()) {
        console.log('✅ User saved to database\n');
      }
    } else {
      console.log('❌ User validation failed:');
      console.log(user.evaluate());
    }

    // Example 2: Query users
    console.log('Example 2: Querying users');
    const select = User.select();

    // Build a complex query using TypeScript with type safety
    select.where(
      select.match(
        (select as any).age.gte(18),
        (select as any).age.lte(65)
      )
    );

    select.sort((select as any).name.asc());

    console.log('Query SQL representation:');
    console.log(select.toSql);
    console.log();

    // Fetch results
    const users = await select.fetchAll(1, 10);
    console.log(`Found ${users.length} users\n`);

    for (const u of users) {
      console.log(`- ${u.name} (${u.email}), Age: ${u.age}`);
    }

    // Example 3: Load by ID
    console.log('\nExample 3: Loading user by ID');
    const loadedUser = await User.load(user.id);
    if (loadedUser) {
      console.log('✅ User loaded:');
      console.log(`   Name: ${loadedUser.name}`);
      console.log(`   Email: ${loadedUser.email}`);
    }

    // Example 4: Update user
    console.log('\nExample 4: Updating user');
    user.update({ age: 31 });
    if (await user.commit()) {
      console.log('✅ User updated');
    }

    // Example 5: Delete user
    console.log('\nExample 5: Deleting user');
    if (await user.delete()) {
      console.log('✅ User deleted from database');
    }

    await client.close();
    console.log('\n✅ All examples completed successfully!');
  } catch (error) {
    console.error('❌ Error:', error);

    // Show offline example
    console.log('\n⚠️  MongoDB not available. Showing offline example:\n');

    const user = new User({
      name: '  jane smith  ',
      email: 'jane@example.com',
      age: 25,
      address: new Address({
        street: '456 Oak Ave',
        city: 'Portland',
        zipCode: '97201',
      }),
      tags: ['designer', 'creative'],
    });

    console.log('User object (without database):');
    console.log(user.toJson(2));

    if (user.isSchematic()) {
      console.log('\n✅ User is valid');
    }
  }
}

// Run the example
main().catch(console.error);
