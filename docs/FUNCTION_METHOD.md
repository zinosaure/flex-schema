# Function Method Documentation

## Overview

The `function` method allows you to apply custom Python functions to document fields during queries, enabling complex transformations and comparisons that go beyond standard MongoDB operators.

## Basic Usage

```python
from flexschema import Flexmodel, Schema, field

class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(float, default=0.0)
    )

# Apply a discount function
def apply_discount(document, discount: float):
    return document.price * discount

select = Product.select()
select.where(
    select.price.function(apply_discount, args=(0.75,)) > 50
)
```

## Features

### 1. Function with Arguments

Pass additional arguments to your function using the `args` parameter:

```python
def calculate_total(document, tax_rate: float, shipping: float):
    return document.price * (1 + tax_rate) + shipping

select.where(
    select.price.function(calculate_total, args=(0.08, 10.0)) > 100
)
```

### 2. Function without Arguments

Functions can also work without additional arguments:

```python
def double_price(document):
    return document.price * 2

select.where(
    select.price.function(double_price) > 100
)
```

### 3. List Aggregation

Process list fields with custom aggregation logic:

```python
def sum_reviews(document):
    if isinstance(document.reviews, list):
        return sum([review.get('score', 0) for review in document.reviews])
    return 0

select.where(
    select.reviews.function(sum_reviews) > 4.5
)
```

### 4. Chaining Functions

Chain multiple functions together, where each function processes the result of the previous one:

```python
def clean_name(document):
    return document.name.strip().lower()

def count_length(document):
    return len(document.name)

select.where(
    select.name.function(clean_name).function(count_length) < 10
)
```

## Implementation Details

### Client-Side Filtering

Function-based queries use client-side filtering because Python functions cannot be executed directly in MongoDB. Documents are fetched from the database and then filtered using the Python functions client-side.

### Performance Considerations

**Important**: When using function filters, be aware of these performance characteristics:

1. **Memory Usage**: Documents are loaded into memory for filtering
2. **Network I/O**: More documents may be fetched than ultimately returned
3. **CPU Usage**: Functions are executed client-side for each document

**Best Practices**:

- Combine function filters with MongoDB filters to reduce the dataset
- Use the `function_filter_limit` parameter to prevent memory issues
- Consider creating MongoDB indexes on frequently queried fields

## Subset Method

The `subset` method checks if all items in a list are present in the document field using MongoDB's `$all` operator:

```python
# Find products that have both "electronics" and "computers" tags
select.where(
    select.tags.subset(["electronics", "computers"])
)
```

This generates the MongoDB query:
```json
{"tags": {"$all": ["electronics", "computers"]}}
```

## Testing

Comprehensive tests are available in:
- `tests/test_function_method.py` - Full test suite
- `tests/test_function_method_mock.py` - Mock-based tests
- `examples/function_example.py` - Working examples
