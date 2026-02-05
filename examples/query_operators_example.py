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

    try:
        client = MongoClient("mongodb://localhost:27017/testdb", serverSelectionTimeoutMS=1000)
        Product.attach(client, "products")
        select = Product.select()
        print("✓ Using MongoDB\n")
    except Exception:
        print("⚠️  MongoDB not available. Falling back to demo mode.\n")
        select = Product.select()

    print("1. Simple comparison:")
    query = select.price > 100
    print("   select.price > 100")
    print(f"   → {query}\n")

    print("2. Range query:")
    query = select.price.is_between(start=50, end=500)
    print("   select.price.is_between(start=50, end=500)")
    print(f"   → {query}\n")

    print("3. IN query:")
    query = select.category.is_in(items=["electronics", "furniture"])
    print("   select.category.is_in(items=['electronics', 'furniture'])")
    print(f"   → {query}\n")

    print("4. Boolean query:")
    query = select.in_stock.is_true()
    print("   select.in_stock.is_true()")
    print(f"   → {query}\n")

    print("5. Logical AND (match):")
    query = select.match(select.price > 50, select.price < 500, select.in_stock.is_true())
    print("   select.match(")
    print("       select.price > 50,")
    print("       select.price < 500,")
    print("       select.in_stock.is_true()")
    print("   )")
    print(f"   → {query}\n")

    print("6. Logical OR (at_least):")
    query = select.at_least(select.price < 50, select.price > 1000)
    print("   select.at_least(")
    print("       select.price < 50,")
    print("       select.price > 1000")
    print("   )")
    print(f"   → {query}\n")

    print("7. Sorting:")
    asc_sort = select.price.asc()
    desc_sort = select.name.desc()
    print(f"   select.price.asc() → {asc_sort}")
    print(f"   select.name.desc() → {desc_sort}\n")

    print("8. Complex nested query:")
    query = select.at_least(select.match(select.category == "electronics", select.price >= 100), select.match(select.category == "furniture", select.in_stock.is_true()))
    print("   select.at_least(")
    print("       select.match(")
    print("           select.category == 'electronics',")
    print("           select.price >= 100")
    print("       ),")
    print("       select.match(")
    print("           select.category == 'furniture',")
    print("           select.in_stock.is_true()")
    print("       )")
    print("   )")
    print(f"   → {query}\n")

    print("✅ ORM-style query examples completed!")
