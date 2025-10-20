"""
Example demonstrating the function method for Flexmodel.Select.Statement

This example shows how to use custom functions with the query API to apply
transformations and comparisons on document fields.
"""
from pymongo import MongoClient
from flexschema import Schema, Flexmodel, field, field_constraint


class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(float, default=0.0),
        reviews=field(list, default=[], constraint=field_constraint(item_type=dict)),
        tags=field(list, default=[], constraint=field_constraint(item_type=str)),
    )

    def __init__(self, **kwargs):
        self.name: str = self.default["name"]
        self.price: float = self.default["price"]
        self.reviews: list = self.default["reviews"]
        self.tags: list = self.default["tags"]

        super().__init__(**kwargs)


if __name__ == "__main__":
    print("=== Function Method Examples ===\n")
    
    # Example 1: Apply discount to price
    print("1. Apply discount function:")
    print("-" * 40)
    
    def apply_discount(document, discount: float):
        """Apply a discount to the product price"""
        return document.price * discount
    
    select = Product.select()
    condition = select.price.function(apply_discount, args=(1 - 0.25,)) > 50
    
    print("Code:")
    print("  def apply_discount(document, discount: float):")
    print("      return document.price * discount")
    print()
    print("  select.where(")
    print("      select.price.function(apply_discount, args=(1 - .25,)) > 50")
    print("  )")
    print()
    print(f"Generated condition: {condition}")
    print()
    
    # Example 2: Sum review scores
    print("2. Sum review scores:")
    print("-" * 40)
    
    def sum_reviews(document):
        """Calculate total review score"""
        if isinstance(document.reviews, list):
            return sum([review.get('score', 0) for review in document.reviews if isinstance(review, dict)])
        return 0
    
    select = Product.select()
    condition = select.reviews.function(sum_reviews) > 4.5
    
    print("Code:")
    print("  def sum_reviews(document):")
    print("      if isinstance(document.reviews, list):")
    print("          return sum([review.score for review in document.reviews])")
    print("      return 0")
    print()
    print("  select.where(")
    print("      select.reviews.function(sum_reviews) > 4.5")
    print("  )")
    print()
    print(f"Generated condition: {condition}")
    print()
    
    # Example 3: Chain multiple functions
    print("3. Chain multiple functions:")
    print("-" * 40)
    
    def clean_name(document):
        """Clean and normalize the name"""
        if hasattr(document, 'name') and isinstance(document.name, str):
            return document.name.strip().lower()
        return ""
    
    def count_length(document):
        """Count the length of the cleaned name"""
        if hasattr(document, 'name'):
            return len(document.name)
        return 0
    
    select = Product.select()
    condition = select.name.function(clean_name).function(count_length) < 3
    
    print("Code:")
    print("  def clean_name(document):")
    print("      return document.name.strip().lower()")
    print()
    print("  def count_length(document):")
    print("      return len(document.name)")
    print()
    print("  select.where(")
    print("      select.name.function(clean_name).function(count_length) < 3")
    print("  )")
    print()
    print(f"Generated condition: {condition}")
    print()
    
    # Example 4: Using subset method (verify it works)
    print("4. Using subset method:")
    print("-" * 40)
    
    select = Product.select()
    condition = select.tags.subset(["electronics", "computers"])
    
    print("Code:")
    print("  select.where(")
    print("      select.tags.subset(['electronics', 'computers'])")
    print("  )")
    print()
    print(f"Generated condition: {condition}")
    print("This checks if all items in the list are present in the tags field.")
    print()
    
    # Example 5: Complex query with multiple conditions
    print("5. Complex query with functions and logical operators:")
    print("-" * 40)
    
    select = Product.select()
    
    print("Code:")
    print("  select.where(")
    print("      select.match(")
    print("          select.price.function(apply_discount, args=(0.75,)) > 50,")
    print("          select.reviews.function(sum_reviews) >= 5,")
    print("          select.tags.subset(['electronics'])")
    print("      )")
    print("  )")
    print()
    
    select.where(
        select.match(
            select.price.function(apply_discount, args=(0.75,)) > 50,
            select.reviews.function(sum_reviews) >= 5,
            select.tags.subset(["electronics"])
        )
    )
    
    print(f"Generated query: {select.query_string}")
    print()
    
    print("=" * 50)
    print("✅ Function method examples completed!")
    print()
    print("Note: To use with actual MongoDB:")
    print("  client = MongoClient('mongodb://localhost:27017/testdb')")
    print("  Product.attach(client, 'products')")
    print("  results = select.fetch_all()")
