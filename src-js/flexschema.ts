import { MongoClient, Db, Collection, Filter, Document, FindOptions } from 'mongodb';
import { v4 as uuidv4 } from 'uuid';

/**
 * Exception thrown when schema definition is invalid
 */
export class SchemaDefinitionException extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SchemaDefinitionException';
    console.error(`[flexschema] ${message}`);
  }

  static silentLog(message: string): void {
    console.info(`[flexschema] ${message}`);
  }
}

/**
 * Exception thrown when Flexmodel operations fail
 */
export class FlexmodelException extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'FlexmodelException';
    console.error(`[flexmodel] ${message}`);
  }

  static silentLog(message: string): void {
    console.info(`[flexmodel] ${message}`);
  }
}

/**
 * Type definition for field types
 */
export type FieldType = 
  | StringConstructor 
  | NumberConstructor 
  | BooleanConstructor 
  | ArrayConstructor
  | typeof Flex;

/**
 * Field constraint configuration
 */
export class FieldConstraint {
  itemType?: FieldType;
  minLength?: number;
  maxLength?: number;
  pattern?: string;

  constructor(options: {
    itemType?: FieldType;
    minLength?: number;
    maxLength?: number;
    pattern?: string;
  } = {}) {
    this.itemType = options.itemType;
    this.minLength = options.minLength;
    this.maxLength = options.maxLength;
    this.pattern = options.pattern;
  }
}

/**
 * Field definition in a schema
 */
export class Field {
  name: string = '';
  type: FieldType;
  default: any;
  nullable: boolean | number;
  callback?: (value: any) => any;
  constraint: FieldConstraint;

  constructor(
    type: FieldType,
    options: {
      default?: any;
      nullable?: boolean | number;
      callback?: (value: any) => any;
      constraint?: FieldConstraint;
    } = {}
  ) {
    this.type = type;
    this.default = options.default ?? null;
    this.nullable = options.nullable ?? true;
    this.callback = options.callback;
    this.constraint = options.constraint ?? new FieldConstraint();
  }

  isValuable(value: any): boolean {
    return !this.evaluate(value);
  }

  evaluate(value: any): string | null {
    if (this.nullable && value === null) {
      return null;
    } else if (!this.nullable && value === null) {
      return `Field '${this.name}': is required and cannot be null.`;
    }

    // Type checking
    if (this.type === String && typeof value !== 'string') {
      return `Field '${this.name}': must be of type string, got '${typeof value}' instead.`;
    } else if (this.type === Number && typeof value !== 'number') {
      return `Field '${this.name}': must be of type number, got '${typeof value}' instead.`;
    } else if (this.type === Boolean && typeof value !== 'boolean') {
      return `Field '${this.name}': must be of type boolean, got '${typeof value}' instead.`;
    } else if (this.type === Array && !Array.isArray(value)) {
      return `Field '${this.name}': must be of type array, got '${typeof value}' instead.`;
    } else if (typeof this.type === 'function' && this.type.prototype instanceof Flex) {
      if (!(value instanceof this.type)) {
        return `Field '${this.name}': must be an instance of ${this.type.name}.`;
      }
    }

    // List item type checking
    if (Array.isArray(value) && this.constraint && this.constraint.itemType) {
      for (let i = 0; i < value.length; i++) {
        const item = value[i];
        if (this.constraint.itemType === String && typeof item !== 'string') {
          return `Field '${this.name}[${i}]': must be of type string, got ${typeof item}.`;
        } else if (this.constraint.itemType === Number && typeof item !== 'number') {
          return `Field '${this.name}[${i}]': must be of type number, got ${typeof item}.`;
        } else if (this.constraint.itemType === Boolean && typeof item !== 'boolean') {
          return `Field '${this.name}[${i}]': must be of type boolean, got ${typeof item}.`;
        }
      }
    }

    // Length/range constraints
    if (typeof value === 'string' || Array.isArray(value)) {
      const length = value.length;
      const suffix = typeof value === 'string' ? 'characters' : 'items';

      if (this.constraint.minLength && length < this.constraint.minLength) {
        return `Field '${this.name}': must have at least: ${this.constraint.minLength} ${suffix}.`;
      }

      if (this.constraint.maxLength && length > this.constraint.maxLength) {
        return `Field '${this.name}': must have at most: ${this.constraint.maxLength} ${suffix}.`;
      }
    } else if (typeof value === 'number') {
      if (this.constraint.minLength && this.constraint.minLength > 0 && value < this.constraint.minLength) {
        return `Field '${this.name}': must be greater than or equal to: ${this.constraint.minLength}.`;
      }

      if (this.constraint.maxLength && this.constraint.maxLength > 0 && value > this.constraint.maxLength) {
        return `Field '${this.name}': must be less than or equal to: ${this.constraint.maxLength}.`;
      }
    }

    // Pattern matching
    if (this.constraint.pattern && typeof value === 'string') {
      const regex = new RegExp(this.constraint.pattern);
      if (!regex.test(value)) {
        return `Field '${this.name}': must match the pattern: '${this.constraint.pattern}'.`;
      }
    }

    return null;
  }
}

/**
 * Schema definition for models
 */
export class Schema {
  fields: Map<string, Field> = new Map();

  constructor(fields: Record<string, Field> = {}) {
    for (const [name, field] of Object.entries(fields)) {
      this.addField(name, field);
    }
  }

  /**
   * Create a schema with auto-generated _id and _updated_at fields
   */
  static ident(fields: Record<string, Field> = {}): Schema {
    return new Schema({
      _id: new Field(String, { default: uuidv4() }),
      _updated_at: new Field(String, { default: new Date().toISOString() }),
      ...fields,
    });
  }

  get(name: string): Field {
    return this.fields.get(name) ?? new Field(String);
  }

  isSubmittable(data: Record<string, any>): boolean {
    for (const [name, field] of this.fields) {
      const item = data[name] ?? field.default;

      if (item && typeof item === 'object' && item.schema instanceof Schema) {
        if (!item.schema.isSubmittable(item)) {
          return false;
        }
      } else if (!field.isValuable(item)) {
        return false;
      }
    }

    return true;
  }

  addField(name: string, field: Field): void {
    // Validate field type
    if (
      field.type !== String &&
      field.type !== Number &&
      field.type !== Boolean &&
      field.type !== Array &&
      !(typeof field.type === 'function' && field.type.prototype instanceof Flex)
    ) {
      throw new SchemaDefinitionException(
        `Field '${name}': has not a valid type '${field.type}'.`
      );
    }

    // Validate list constraints
    if (field.type === Array && field.constraint && !field.constraint.itemType) {
      throw new SchemaDefinitionException(
        `Field '${name}': type 'Array' must have a 'constraint.itemType' defined.`
      );
    }

    // Validate default value
    if (field.default !== null) {
      if (field.type === String && typeof field.default !== 'string') {
        throw new SchemaDefinitionException(
          `Field '${name}': default value must be of type 'string' or null. Got '${typeof field.default}' instead.`
        );
      } else if (field.type === Number && typeof field.default !== 'number') {
        throw new SchemaDefinitionException(
          `Field '${name}': default value must be of type 'number' or null. Got '${typeof field.default}' instead.`
        );
      } else if (field.type === Boolean && typeof field.default !== 'boolean') {
        throw new SchemaDefinitionException(
          `Field '${name}': default value must be of type 'boolean' or null. Got '${typeof field.default}' instead.`
        );
      } else if (field.type === Array && !Array.isArray(field.default)) {
        throw new SchemaDefinitionException(
          `Field '${name}': default value must be of type 'array' or null. Got '${typeof field.default}' instead.`
        );
      }
    }

    // Validate nullable
    if (typeof field.nullable === 'number' && field.nullable < 0) {
      throw new SchemaDefinitionException(
        `Field '${name}': nullable must be a boolean or a positive integer.`
      );
    }

    // Validate pattern
    if (field.constraint && field.constraint.pattern) {
      if (field.type !== String && field.type !== Number) {
        throw new SchemaDefinitionException(
          `Field '${name}': 'constraint.pattern' works only on type of 'number' or 'string'.`
        );
      }
      try {
        new RegExp(field.constraint.pattern);
      } catch (e) {
        throw new SchemaDefinitionException(
          `Field '${name}': 'constraint.pattern' is not a valid RegEx: '${field.constraint.pattern}'.`
        );
      }
    }

    // Validate callback
    if (field.callback && typeof field.callback !== 'function') {
      throw new SchemaDefinitionException(
        `Field '${name}': has not a valid 'constraint.callback'.`
      );
    }

    field.name = name;
    this.fields.set(name, field);
  }

  *[Symbol.iterator](): Iterator<[string, Field]> {
    yield* this.fields.entries();
  }
}

/**
 * Base class for data models without database persistence
 */
export class Flex {
  static schema: Schema = new Schema();
  [key: string]: any;

  constructor(data: Record<string, any> = {}) {
    this.update(data);
  }

  get default(): Record<string, any> {
    const result: Record<string, any> = {};
    const schema = (this.constructor as typeof Flex).schema;
    for (const [name, field] of schema.fields) {
      result[name] = field.default;
    }
    return result;
  }

  isSchematic(): boolean {
    return Object.keys(this.evaluate()).length === 0;
  }

  update(data: Record<string, any> = {}): this {
    const schema = (this.constructor as typeof Flex).schema;
    
    for (const [name, field] of schema) {
      let value = data[name] ?? this[name] ?? field.default;

      // Handle nested Flexmodel references
      if (
        typeof field.type === 'function' &&
        field.type.prototype instanceof Flexmodel &&
        typeof value === 'object' &&
        value !== null &&
        '$id' in value
      ) {
        value = (field.type as typeof Flexmodel).load(value.$id);
      } else if (
        typeof field.type === 'function' &&
        field.type.prototype instanceof Flex &&
        typeof value === 'object' &&
        value !== null &&
        !(value instanceof Flex)
      ) {
        value = new field.type(value);
      }

      this[name] = value;
    }

    return this;
  }

  evaluate(): Record<string, any> {
    const messages: Record<string, any> = {};
    const schema = (this.constructor as typeof Flex).schema;

    for (const [name, field] of schema.fields) {
      const value = this[name] ?? field.default;
      const error = field.evaluate(value);

      if (error) {
        messages[name] = error;
      }

      if (value instanceof Flex) {
        const nestedErrors = value.evaluate();
        if (Object.keys(nestedErrors).length > 0) {
          messages[name] = nestedErrors;
        }
      }
    }

    return messages;
  }

  toDict(commit: boolean = false): Record<string, any> {
    const schema = (this.constructor as typeof Flex).schema;
    const result: Record<string, any> = {};

    const serialize = (value: any, field?: Field): any => {
      if (commit && value instanceof Flexmodel && value.id) {
        return { $id: value.id };
      } else if (value instanceof Flex) {
        return value.toDict(commit);
      } else if (Array.isArray(value)) {
        return value.map((item) => serialize(item));
      } else if (value instanceof Date) {
        return value.toISOString();
      } else if (typeof value === 'object' && value !== null) {
        const obj: Record<string, any> = {};
        for (const [k, v] of Object.entries(value)) {
          obj[k] = serialize(v);
        }
        return obj;
      }

      if (field && field.callback) {
        return field.callback(value);
      }

      return value;
    };

    for (const [name, field] of schema.fields) {
      result[name] = serialize(this[name] ?? field.default, field);
    }

    return result;
  }

  toJson(indent: number = 4, commit: boolean = false): string {
    return JSON.stringify(this.toDict(commit), null, indent);
  }
}

/**
 * Base class for models with MongoDB persistence
 */
export class Flexmodel extends Flex {
  static schema: Schema = Schema.ident();
  static database: Db | null = null;
  static collectionName: string = 'collections';

  get id(): string {
    if (!this._id || this._id === (this.constructor as typeof Flexmodel).schema.get('_id').default) {
      this._id = uuidv4();
    }
    return this._id;
  }

  get updatedAt(): string {
    return this._updated_at ?? new Date().toISOString();
  }

  isCommittable(): boolean {
    const schema = (this.constructor as typeof Flexmodel).schema;
    return schema.isSubmittable(this);
  }

  async commit(commitAll: boolean = true): Promise<boolean> {
    if (!this.isCommittable()) {
      return false;
    }

    if (commitAll) {
      for (const value of Object.values(this)) {
        if (value instanceof Flexmodel) {
          if (!(await value.commit())) {
            return false;
          }
        }
      }
    }

    this.update({ _updated_at: new Date().toISOString() });

    const collection = (this.constructor as typeof Flexmodel).collection();
    const result = await collection.replaceOne(
      { _id: this.id },
      this.toDict(commitAll) as Document,
      { upsert: true }
    );

    return result.acknowledged;
  }

  async delete(): Promise<boolean> {
    const collection = (this.constructor as typeof Flexmodel).collection();
    const result = await collection.deleteOne({ _id: this.id });
    return result.deletedCount > 0;
  }

  static attach(database: MongoClient | Db, collectionName?: string): void {
    if (database instanceof MongoClient) {
      this.database = database.db();
    } else if (database instanceof Db) {
      this.database = database;
    } else {
      throw new FlexmodelException(
        'Cannot attach to the database: invalid database type. Only MongoClient or Db is supported.'
      );
    }

    this.collectionName = collectionName ?? `${this.name.toLowerCase()}s`;

    // Try to create index if database is available
    try {
      this.collection().createIndex({ _id: 1 }, { unique: true }).catch(() => {
        // Ignore errors during index creation
      });
    } catch (e) {
      // Database might not be available during initialization
    }
  }

  static detach(): void {
    this.database = null;
    this.collectionName = 'collections';
  }

  static collection(): Collection {
    if (!this.database) {
      throw new FlexmodelException('Model is not attached to a database.');
    }
    return this.database.collection(this.collectionName);
  }

  static async load(id: string): Promise<Flexmodel | null> {
    const document = await this.collection().findOne({ _id: id });
    if (document) {
      return new this(document as Record<string, any>);
    }
    return null;
  }

  static async count(): Promise<number> {
    return this.collection().countDocuments({});
  }

  static select(): Select {
    return new Select(new this() as Flexmodel);
  }
}

/**
 * Query builder for ORM-style queries
 */
export class Select {
  model: Flexmodel;
  sorts: Record<string, number> = {};
  statements: Record<string, any> = {};

  constructor(model: Flexmodel) {
    this.model = model;
  }

  [key: string]: any;

  get queryString(): string {
    return JSON.stringify(
      { $where: this.statements, $sort: this.sorts },
      null,
      4
    );
  }

  get toSql(): string {
    let sql = `SELECT * FROM ${(this.model.constructor as typeof Flexmodel).collectionName}`;

    if (Object.keys(this.statements).length === 0) {
      return sql;
    }

    const parseCondition = (condition: Record<string, any>): string => {
      const clauses: string[] = [];

      for (const [key, value] of Object.entries(condition)) {
        if (key === '$and') {
          clauses.push('(' + (value as any[]).map(parseCondition).join(' AND ') + ')');
        } else if (key === '$or') {
          clauses.push('(' + (value as any[]).map(parseCondition).join(' OR ') + ')');
        } else if (key === '$not') {
          clauses.push('NOT (' + parseCondition(value) + ')');
        } else {
          if (typeof value === 'object' && value !== null) {
            for (const [op, val] of Object.entries(value)) {
              if (op === '$ne') {
                clauses.push(`${key} != '${val}'`);
              } else if (op === '$lt') {
                clauses.push(`${key} < '${val}'`);
              } else if (op === '$gt') {
                clauses.push(`${key} > '${val}'`);
              } else if (op === '$lte') {
                clauses.push(`${key} <= '${val}'`);
              } else if (op === '$gte') {
                clauses.push(`${key} >= '${val}'`);
              } else if (op === '$in') {
                clauses.push(`${key} IN (${(val as any[]).map((v) => JSON.stringify(v)).join(', ')})`);
              } else if (op === '$nin') {
                clauses.push(`${key} NOT IN (${(val as any[]).map((v) => JSON.stringify(v)).join(', ')})`);
              } else if (op === '$regex') {
                clauses.push(`${key} REGEXP '${val}'`);
              } else if (op === '$exists') {
                clauses.push(`${key} IS ${val ? '' : 'NOT '}NULL`);
              }
            }
          } else {
            clauses.push(`${key} = '${value}'`);
          }
        }
      }

      return clauses.join(' AND ');
    };

    return sql + ' WHERE ' + parseCondition(this.statements);
  }

  match(...conditions: Record<string, any>[]): Record<string, any> {
    if (conditions.length === 0) {
      return {};
    }
    return { $and: conditions };
  }

  notMatch(...conditions: Record<string, any>[]): Record<string, any> {
    if (conditions.length === 0) {
      return {};
    }
    return { $not: { $and: conditions } };
  }

  atLeast(...conditions: Record<string, any>[]): Record<string, any> {
    if (conditions.length === 0) {
      return {};
    }
    return { $or: conditions };
  }

  notAtLeast(...conditions: Record<string, any>[]): Record<string, any> {
    if (conditions.length === 0) {
      return {};
    }
    return { $not: { $or: conditions } };
  }

  where(...conditions: Record<string, any>[]): void {
    for (const condition of conditions) {
      for (const [logical, value] of Object.entries(condition)) {
        this.statements[logical] = value;
      }
    }
  }

  sort(...conditions: Record<string, any>[]): void {
    if (conditions.length === 0) {
      return;
    }

    for (const condition of conditions) {
      for (const [logical, value] of Object.entries(condition)) {
        this.sorts[logical] = value;
      }
    }
  }

  discard(): void {
    this.sorts = {};
    this.statements = {};
  }

  async count(): Promise<number> {
    const collection = (this.model.constructor as typeof Flexmodel).collection();
    return collection.countDocuments(this.statements as Filter<Document>);
  }

  async fetch(): Promise<Flexmodel | null> {
    const collection = (this.model.constructor as typeof Flexmodel).collection();
    const document = await collection.findOne(this.statements as Filter<Document>);
    if (document) {
      return new (this.model.constructor as any)(document);
    }
    return null;
  }

  async fetchAll(current: number = 1, resultsPerPage: number = 10): Promise<Pagination> {
    let count = 0;
    let results: Flexmodel[] = [];

    if (current < 1) {
      current = 1;
    }
    if (resultsPerPage < 1) {
      resultsPerPage = 10;
    }

    const collection = (this.model.constructor as typeof Flexmodel).collection();
    count = await collection.countDocuments(this.statements as Filter<Document>);

    if (count > 0) {
      const options: FindOptions = {
        skip: (current - 1) * resultsPerPage,
        limit: resultsPerPage,
      };

      if (Object.keys(this.sorts).length > 0) {
        options.sort = this.sorts;
      }

      const cursor = collection.find(this.statements as Filter<Document>, options);
      const documents = await cursor.toArray();
      results = documents.map((doc) => new (this.model.constructor as any)(doc));
    }

    return new Pagination(count, results, current, resultsPerPage);
  }
}

// Proxy handler to create Statement objects for field access
const selectProxyHandler: ProxyHandler<Select> = {
  get(target: Select, prop: string | symbol): any {
    if (typeof prop === 'string' && prop in target) {
      return (target as any)[prop];
    }

    if (typeof prop === 'string') {
      const schema = (target.model.constructor as typeof Flexmodel).schema;
      if (!schema.fields.has(prop)) {
        throw new FlexmodelException(
          `Select statement: field '${prop}' does not exist in the model schema.`
        );
      }

      const value = target.model[prop] ?? schema.get(prop).default;
      return new Statement(prop, value);
    }

    return undefined;
  },
};

// Override Select constructor to return a proxy
const OriginalSelect = Select;
(Select as any) = new Proxy(OriginalSelect, {
  construct(target, args) {
    const instance = new target(...args);
    return new Proxy(instance, selectProxyHandler);
  },
});

/**
 * Statement builder for ORM-style field conditions
 */
export class Statement {
  name: string;
  model: any;

  constructor(name: string, model: any) {
    this.name = name;
    this.model = model;
  }

  eq(value: any): Record<string, any> {
    return { [this.name]: value };
  }

  ne(value: any): Record<string, any> {
    return { [this.name]: { $ne: value } };
  }

  lt(value: any): Record<string, any> {
    return { [this.name]: { $lt: value } };
  }

  gt(value: any): Record<string, any> {
    return { [this.name]: { $gt: value } };
  }

  lte(value: any): Record<string, any> {
    return { [this.name]: { $lte: value } };
  }

  gte(value: any): Record<string, any> {
    return { [this.name]: { $gte: value } };
  }

  exists(): Record<string, any> {
    return { [this.name]: { $exists: true } };
  }

  notExists(): Record<string, any> {
    return { [this.name]: { $exists: false } };
  }

  isTrue(): Record<string, any> {
    return { [this.name]: { $eq: true } };
  }

  isFalse(): Record<string, any> {
    return { [this.name]: { $eq: false } };
  }

  isNull(): Record<string, any> {
    return { [this.name]: { $eq: null } };
  }

  isNotNull(): Record<string, any> {
    return { [this.name]: { $ne: null } };
  }

  isEmpty(): Record<string, any> {
    return { [this.name]: { $in: [null, ''] } };
  }

  isNotEmpty(): Record<string, any> {
    return { [this.name]: { $nin: [null, ''] } };
  }

  isBetween(start: number | string, end: number | string): Record<string, any> {
    return { [this.name]: { $gte: start, $lte: end } };
  }

  isNotBetween(start: number | string, end: number | string): Record<string, any> {
    return { [this.name]: { $lt: start, $gt: end } };
  }

  isIn(items: any[]): Record<string, any> {
    return { [this.name]: { $in: items } };
  }

  isNotIn(items: any[]): Record<string, any> {
    return { [this.name]: { $nin: items } };
  }

  match(pattern: string, options: string = 'i'): Record<string, any> {
    return { [this.name]: { $regex: pattern, $options: options } };
  }

  notMatch(pattern: string, options: string = 'i'): Record<string, any> {
    return { [this.name]: { $not: { $regex: pattern, $options: options } } };
  }

  subset(items: any[]): Record<string, any> {
    return { [this.name]: { $all: items } };
  }

  notSubset(items: any[]): Record<string, any> {
    return { [this.name]: { $not: { $all: items } } };
  }

  asc(): Record<string, any> {
    return { [this.name]: 1 };
  }

  desc(): Record<string, any> {
    return { [this.name]: -1 };
  }
}

/**
 * Pagination wrapper for query results
 */
export class Pagination {
  count: number;
  results: Flexmodel[];
  current: number;
  resultsPerPage: number;

  constructor(
    count: number,
    results: Flexmodel[],
    current: number,
    resultsPerPage: number
  ) {
    this.count = count;
    this.results = results;
    this.current = current;
    this.resultsPerPage = resultsPerPage;
  }

  get length(): number {
    return this.count;
  }

  map(callback: (item: Flexmodel) => Flexmodel): Flexmodel[] {
    return this.results.map(callback);
  }

  toDict(): Record<string, any> {
    return {
      results: this.results.map((item) => item.toDict()),
      pagination: {
        count: this.count,
        current: this.current,
        resultsPerPage: this.resultsPerPage,
      },
    };
  }

  *[Symbol.iterator](): Iterator<Flexmodel> {
    yield* this.results;
  }
}

/**
 * Helper function to create a field
 */
export function field(
  type: FieldType,
  options: {
    default?: any;
    nullable?: boolean | number;
    constraint?: FieldConstraint;
    callback?: (value: any) => any;
  } = {}
): Field {
  return new Field(type, options);
}

/**
 * Helper function to create a field constraint
 */
export function fieldConstraint(options: {
  itemType?: FieldType;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
} = {}): FieldConstraint {
  return new FieldConstraint(options);
}
