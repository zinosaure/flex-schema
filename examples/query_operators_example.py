"""
Example demonstrating MongoDB-style query operators with SQLite
"""
import sqlite3
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
    # Connect to SQLite in-memory database
    conn = sqlite3.connect(":memory:")
    Product.attach(conn, "products")

    # Create sample products
    products = [
        Product(name="Laptop", price=999.99, category="electronics", in_stock=True, quantity=10),
        Product(name="Mouse", price=29.99, category="electronics", in_stock=True, quantity=50),
        Product(name="Keyboard", price=79.99, category="electronics", in_stock=False, quantity=0),
        Product(name="Monitor", price=299.99, category="electronics", in_stock=True, quantity=15),
        Product(name="Desk", price=199.99, category="furniture", in_stock=True, quantity=5),
        Product(name="Chair", price=149.99, category="furniture", in_stock=False, quantity=0),
        Product(name="Pen", price=1.99, category="stationery", in_stock=True, quantity=100),
    ]

    for p in products:
        p.commit()

    print("=== MongoDB-Style Query Examples ===\n")

    # Comparison operators
    print("1. Products with price > 100:")
    results = Product.fetch_all({"price": {"$gt": 100}})
    for product in results.items:
        print(f"   - {product.name}: ${product.price}")

    print("\n2. Products with quantity >= 10:")
    results = Product.fetch_all({"quantity": {"$gte": 10}})
    for product in results.items:
        print(f"   - {product.name}: {product.quantity} units")

    print("\n3. Cheap products (price < 50):")
    results = Product.fetch_all({"price": {"$lt": 50}})
    for product in results.items:
        print(f"   - {product.name}: ${product.price}")

    # Array operators
    print("\n4. Electronics or furniture:")
    results = Product.fetch_all({
        "category": {"$in": ["electronics", "furniture"]}
    })
    for product in results.items:
        print(f"   - {product.name} ({product.category})")

    print("\n5. Not stationery:")
    results = Product.fetch_all({
        "category": {"$nin": ["stationery"]}
    })
    for product in results.items:
        print(f"   - {product.name} ({product.category})")

    # Logical operators
    print("\n6. Cheap OR expensive (< $50 OR > $500):")
    results = Product.fetch_all({
        "$or": [
            {"price": {"$lt": 50}},
            {"price": {"$gt": 500}}
        ]
    })
    for product in results.items:
        print(f"   - {product.name}: ${product.price}")

    print("\n7. In stock AND price between $50-$300:")
    results = Product.fetch_all({
        "in_stock": True,
        "price": {"$gte": 50, "$lte": 300}
    })
    for product in results.items:
        print(f"   - {product.name}: ${product.price}")

    # Complex combined query
    print("\n8. Complex query - Electronics >= $100 OR furniture in stock:")
    results = Product.fetch_all({
        "$or": [
            {
                "$and": [
                    {"category": "electronics"},
                    {"price": {"$gte": 100}}
                ]
            },
            {
                "$and": [
                    {"category": "furniture"},
                    {"in_stock": True}
                ]
            }
        ]
    })
    for product in results.items:
        print(f"   - {product.name} ({product.category}): ${product.price}, in_stock={product.in_stock}")

    # Existence operator
    print(f"\n9. Total products in database: {Product.count()}")

    # Cleanup
    conn.close()
    print("\n✅ All queries executed successfully!")
