"""
Example demonstrating ORM-style query system with Flexmodel
"""
from pymongo import MongoClient
from flexschema import Schema, Flexmodel, field


class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(float, default=0.0),
        category=field(str, nullable=False),
        in_stock=field(bool, default=True),
        quantity=field(int, default=0),
    )


if __name__ == "__main__":
    print("=== ORM-Style Query API Examples ===\n")
    print("This example demonstrates the query builder without connecting to MongoDB.\n")
    
    # Note: To actually run queries against a database, uncomment these lines:
    # client = MongoClient("mongodb://localhost:27017/testdb")
    # Product.attach(client, "products")
    
    # Create a mock select object for demonstration
    # (In real usage, this would be: select = Product.select())
    class MockSelect:
        def __init__(self):
            self.conditions = []
            
        def __getattr__(self, name):
            return MockStatement(name)
            
        def where(self, *args):
            self.conditions.extend(args)
            return self
            
        def sort(self, *args):
            return self
            
        def match(self, *args):
            return {"$and": list(args)}
            
        def at_least(self, *args):
            return {"$or": list(args)}
    
    class MockStatement:
        def __init__(self, name):
            self.name = name
            
        def __gt__(self, value):
            return {self.name: {"$gt": value}}
            
        def __ge__(self, value):
            return {self.name: {"$gte": value}}
            
        def __lt__(self, value):
            return {self.name: {"$lt": value}}
            
        def __le__(self, value):
            return {self.name: {"$lte": value}}
            
        def __eq__(self, value):
            return {self.name: value}
            
        def __ne__(self, value):
            return {self.name: {"$ne": value}}
            
        def is_true(self):
            return {self.name: {"$eq": True}}
            
        def is_false(self):
            return {self.name: {"$eq": False}}
            
        def is_between(self, start, end):
            return {self.name: {"$gte": start, "$lte": end}}
            
        def is_in(self, items):
            return {self.name: {"$in": items}}
            
        def asc(self):
            return {self.name: 1}
            
        def desc(self):
            return {self.name: -1}
    
    select = MockSelect()
    
    print("1. Simple comparison:")
    query = select.price > 100
    print(f"   select.price > 100")
    print(f"   → {query}\n")
    
    print("2. Range query:")
    query = select.price.is_between(start=50, end=500)
    print(f"   select.price.is_between(start=50, end=500)")
    print(f"   → {query}\n")
    
    print("3. IN query:")
    query = select.category.is_in(items=["electronics", "furniture"])
    print(f"   select.category.is_in(items=['electronics', 'furniture'])")
    print(f"   → {query}\n")
    
    print("4. Boolean query:")
    query = select.in_stock.is_true()
    print(f"   select.in_stock.is_true()")
    print(f"   → {query}\n")
    
    print("5. Logical AND (match):")
    query = select.match(
        select.price > 50,
        select.price < 500,
        select.in_stock.is_true()
    )
    print(f"   select.match(")
    print(f"       select.price > 50,")
    print(f"       select.price < 500,")
    print(f"       select.in_stock.is_true()")
    print(f"   )")
    print(f"   → {query}\n")
    
    print("6. Logical OR (at_least):")
    query = select.at_least(
        select.price < 50,
        select.price > 1000
    )
    print(f"   select.at_least(")
    print(f"       select.price < 50,")
    print(f"       select.price > 1000")
    print(f"   )")
    print(f"   → {query}\n")
    
    print("7. Sorting:")
    asc_sort = select.price.asc()
    desc_sort = select.name.desc()
    print(f"   select.price.asc() → {asc_sort}")
    print(f"   select.name.desc() → {desc_sort}\n")
    
    print("8. Complex nested query:")
    query = select.at_least(
        select.match(
            select.category == "electronics",
            select.price >= 100
        ),
        select.match(
            select.category == "furniture",
            select.in_stock.is_true()
        )
    )
    print(f"   select.at_least(")
    print(f"       select.match(")
    print(f"           select.category == 'electronics',")
    print(f"           select.price >= 100")
    print(f"       ),")
    print(f"       select.match(")
    print(f"           select.category == 'furniture',")
    print(f"           select.in_stock.is_true()")
    print(f"       )")
    print(f"   )")
    print(f"   → {query}\n")
    
    print("✅ ORM-style query examples completed!")
    print("\nTo use with actual MongoDB:")
    print("  client = MongoClient('mongodb://localhost:27017/testdb')")
    print("  Product.attach(client, 'products')")
    print("  select = Product.select()")
    print("  select.where(select.price > 100)")
    print("  products = select.fetch_all()")
