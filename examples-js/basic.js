const { MongoClient } = require('mongodb');
const {
  Schema,
  Flex,
  Flexmodel,
  field,
  fieldConstraint,
} = require('../dist/index');

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
      callback: (v) => v.charAt(0).toUpperCase() + v.slice(1).toLowerCase(),
    }),
    email: field(String, {
      nullable: false,
      constraint: fieldConstraint({ pattern: /[^@]+@[^@]+\.[^@]+/.source }),
    }),
    dateOfBirth: field(String, {
      constraint: fieldConstraint({ pattern: /\d{4}-\d{2}-\d{2}/.source }),
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

  constructor(data = {}) {
    super(data);
    if (!this.name) {
      this.name = User.schema.get('name').default;
    }
    if (!this.login) {
      this.login = User.schema.get('login').default;
    }
  }
}

async function main() {
  try {
    // Try to connect to MongoDB
    const client = new MongoClient('mongodb://localhost:27017/testdb', {
      serverSelectionTimeoutMS: 1000,
    });
    
    await client.connect();
    
    User.attach(client.db(), 'users');
    Login.attach(client.db(), 'logins');

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

    if (await user.commit()) {
      console.log(user.toJson(4));
    } else {
      console.log('Failed to save user:\n', user.evaluate());
    }

    await client.close();
  } catch (e) {
    console.log(`⚠️  MongoDB not available: ${e.message}`);
    console.log('\nShowing user data without saving to database:');
    
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
    
    console.log(user.toJson(4));
    console.log('\nTo save to database, start MongoDB at localhost:27017');
  }
}

main().catch(console.error);
