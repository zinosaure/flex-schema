"""
Comprehensive example demonstrating the ORM-style query API
"""
from typing import cast
from pymongo import MongoClient
from flexschema import Schema, Flexmodel, field


class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(float, default=0.0),
        in_stock=field(bool, default=True),
        category=field(str, nullable=False),
    )

    def __init__(self, **kwargs):
        self.name: str = self.default["name"]
        self.price: float = self.default["price"]
        self.in_stock: bool = self.default["in_stock"]
        self.category: str = self.default["category"]
        super().__init__(**kwargs)


if __name__ == "__main__":
    print("=== ORM-Style Query API Examples ===\n")
    
    # Try to connect to MongoDB (will work without actual connection for demo)
    try:
        client = MongoClient("mongodb://localhost:27017/testdb", serverSelectionTimeoutMS=1000)
        Product.attach(client, "products")
        print("✓ Connected to MongoDB\n")
    except Exception as e:
        print("⚠️  MongoDB not available. Showing API examples only.\n")
    
    # Create a Select query builder
    select = Product.select()
    
    print("1. Basic equality query:")
    select.where(select.name == "Laptop")
    print(f"   Query: {select.query_string}")
    print(f"   SQL equivalent: {select.to_sql}\n")
    select.discard()  # Clear previous query
    
    print("2. Comparison operators:")
    select.where(select.price > 100)
    print(f"   price > 100: {select.to_sql}")
    select.discard()
    
    select.where(select.price >= 50)
    print(f"   price >= 50: {select.to_sql}")
    select.discard()
    
    select.where(select.price < 1000)
    print(f"   price < 1000: {select.to_sql}")
    select.discard()
    
    select.where(select.price <= 500)
    print(f"   price <= 500: {select.to_sql}")
    select.discard()
    
    select.where(select.name != "Mouse")
    print(f"   name != 'Mouse': {select.to_sql}\n")
    select.discard()
    
    print("3. Boolean queries:")
    select.where(select.in_stock.is_true())
    print(f"   in_stock is true: {select.to_sql}")
    select.discard()
    
    select.where(select.in_stock.is_false())
    print(f"   in_stock is false: {select.to_sql}\n")
    select.discard()
    
    print("4. Null checks:")
    select.where(select.name.is_null())
    print(f"   name is null: {select.query_string}")
    select.discard()
    
    select.where(select.name.is_not_null())
    print(f"   name is not null: {select.query_string}\n")
    select.discard()
    
    print("5. Empty checks:")
    select.where(select.name.is_empty())
    print(f"   name is empty: {select.query_string}")
    select.discard()
    
    select.where(select.name.is_not_empty())
    print(f"   name is not empty: {select.query_string}\n")
    select.discard()
    
    print("6. Range queries:")
    select.where(select.price.is_between(start=50, end=500))
    print(f"   price between 50 and 500: {select.query_string}")
    select.discard()
    
    select.where(select.price.is_not_between(start=50, end=500))
    print(f"   price not between 50 and 500: {select.query_string}\n")
    select.discard()
    
    print("7. IN queries:")
    select.where(select.category.is_in(items=["electronics", "furniture"]))
    print(f"   category in [electronics, furniture]: {select.query_string}")
    select.discard()
    
    select.where(select.category.is_not_in(items=["stationery"]))
    print(f"   category not in [stationery]: {select.query_string}\n")
    select.discard()
    
    print("8. Pattern matching (regex):")
    select.where(select.name.match("^Lap", options="i"))
    print(f"   name matches '^Lap' (case-insensitive): {select.query_string}")
    select.discard()
    
    select.where(select.name.not_match("^Mouse", options="i"))
    print(f"   name doesn't match '^Mouse': {select.query_string}\n")
    select.discard()
    
    print("9. Logical AND (match):")
    select.where(
        select.match(
            select.price > 50,
            select.price < 500,
            select.in_stock.is_true()
        )
    )
    print(f"   price > 50 AND price < 500 AND in_stock: {select.query_string}\n")
    select.discard()
    
    print("10. Logical OR (at_least):")
    select.where(
        select.at_least(
            select.price < 50,
            select.price > 1000
        )
    )
    print(f"   price < 50 OR price > 1000: {select.query_string}\n")
    select.discard()
    
    print("11. Complex nested query:")
    select.where(
        select.at_least(
            select.match(
                select.category == "electronics",
                select.price >= 100
            ),
            select.match(
                select.category == "furniture",
                select.in_stock.is_true()
            )
        )
    )
    print(f"   Complex OR with AND conditions: {select.query_string}\n")
    select.discard()
    
    print("12. Sorting:")
    select.where(select.price > 0)
    select.sort(select.price.asc())
    print(f"   Sort by price ascending: {select.query_string}")
    select.discard()
    
    select.where(select.price > 0)
    select.sort(select.price.desc())
    print(f"   Sort by price descending: {select.query_string}\n")
    select.discard()
    
    print("13. Pagination:")
    select.where(select.in_stock.is_true())
    print(f"   Query: {select.query_string}")
    print(f"   Fetch page 1 with 10 items per page:")
    print(f"   pagination = select.fetch_all(current=1, results_per_page=10)")
    print(f"   for product in pagination:")
    print(f"       print(product.name)\n")
    select.discard()
    
    print("14. Counting:")
    select.where(select.category == "electronics")
    print(f"   Count electronics: select.count()")
    print(f"   Total count: Product.count()\n")
    select.discard()
    
    print("15. Fetching single item:")
    select.where(select.name == "Laptop")
    print(f"   Fetch one: product = select.fetch()")
    print(f"   Or directly: Product.load(product_id)\n")
    select.discard()
    
    print("✅ All ORM-style API examples completed!")
    print("\nFor more information, see the README.md")
