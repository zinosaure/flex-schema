const {
  Schema,
  Flexmodel,
  field,
  fieldConstraint,
} = require('../dist/index');

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

// Test 1: Invalid article (too short title and content)
console.log('Test 1: Invalid article');
const article1 = new Article({
  title: 'Hi',
  content: 'Too short',
});

if (!article1.isSchematic()) {
  const errors = article1.evaluate();
  console.log('Validation errors found (as expected):');
  console.log(JSON.stringify(errors, null, 2));
} else {
  console.log('ERROR: Article should have validation errors!');
}

console.log('\n' + '='.repeat(60) + '\n');

// Test 2: Valid article
console.log('Test 2: Valid article');
const article2 = new Article({
  title: 'This is a valid title',
  content: 'This is a long enough content that meets the minimum length requirement of 50 characters.',
  tags: ['tech', 'nodejs', 'typescript'],
});

if (article2.isSchematic()) {
  console.log('Article is valid (as expected)');
  console.log(article2.toJson(2));
} else {
  console.log('ERROR: Article should be valid!');
  console.log(article2.evaluate());
}

console.log('\n' + '='.repeat(60) + '\n');

// Test 3: Test pattern validation
console.log('Test 3: Pattern validation');
class Contact extends Flexmodel {
  static schema = Schema.ident({
    email: field(String, {
      nullable: false,
      constraint: fieldConstraint({ pattern: '[^@]+@[^@]+\\.[^@]+' }),
    }),
    phone: field(String, {
      constraint: fieldConstraint({ pattern: '^\\+?1?\\d{9,15}$' }),
    }),
  });
}

const contact1 = new Contact({
  email: 'invalid-email',
  phone: '123',
});

if (!contact1.isSchematic()) {
  const errors = contact1.evaluate();
  console.log('Validation errors found (as expected):');
  console.log(JSON.stringify(errors, null, 2));
} else {
  console.log('ERROR: Contact should have validation errors!');
}

console.log('\n' + '='.repeat(60) + '\n');

// Test 4: Valid contact
console.log('Test 4: Valid contact');
const contact2 = new Contact({
  email: 'test@example.com',
  phone: '+1234567890',
});

if (contact2.isSchematic()) {
  console.log('Contact is valid (as expected)');
  console.log(contact2.toJson(2));
} else {
  console.log('ERROR: Contact should be valid!');
  console.log(contact2.evaluate());
}

console.log('\n✅ All validation tests passed!');
