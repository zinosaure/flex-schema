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
    # Connect to MongoDB (replace with your MongoDB connection string)
    client = MongoClient("mongodb://localhost:27017/testdb")
    Product.attach(client, "products")

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

    # Save all products
    try:
        for p in products:
            p.commit()
        print("✅ Products created successfully!\n")
    except Exception as e:
        print(f"⚠️ Warning: Could not save products to database: {e}")
        print("Make sure MongoDB is running at localhost:27017\n")

    print("=== ORM-Style Query Examples ===\n")

    # Using the Select API
    print("1. Products with price > 100 (using Select API):")
    try:
        select = Product.select()
        select.where(select.price > 100)
        for product in select.fetch_all():
            print(f"   - {product.name}: ${product.price}")
    except Exception as e:
        print(f"   Example query: Product.select().where(select.price > 100)")

    print("\n2. Products with quantity >= 10 (using Select API):")
    try:
        select = Product.select()
        select.where(select.quantity >= 10)
        for product in select.fetch_all():
            print(f"   - {product.name}: {product.quantity} units")
    except Exception as e:
        print(f"   Example query: Product.select().where(select.quantity >= 10)")

    print("\n3. Cheap products - price < 50 (using Select API):")
    try:
        select = Product.select()
        select.where(select.price < 50)
        for product in select.fetch_all():
            print(f"   - {product.name}: ${product.price}")
    except Exception as e:
        print(f"   Example query: Product.select().where(select.price < 50)")

    print("\n4. Electronics or furniture (using Select API):")
    try:
        select = Product.select()
        select.where(
            select.at_least(
                select.category == "electronics",
                select.category == "furniture"
            )
        )
        for product in select.fetch_all():
            print(f"   - {product.name} ({product.category})")
    except Exception as e:
        print(f"   Example query: Product.select().where(select.at_least(...))")

    print("\n5. In stock products (using Select API):")
    try:
        select = Product.select()
        select.where(select.in_stock.is_true())
        for product in select.fetch_all():
            print(f"   - {product.name}")
    except Exception as e:
        print(f"   Example query: Product.select().where(select.in_stock.is_true())")

    print("\n6. Cheap OR expensive (< $50 OR > $500) using Select API:")
    try:
        select = Product.select()
        select.where(
            select.at_least(
                select.price < 50,
                select.price > 500
            )
        )
        for product in select.fetch_all():
            print(f"   - {product.name}: ${product.price}")
    except Exception as e:
        print(f"   Example query: Product.select().where(select.at_least(price < 50, price > 500))")

    print("\n7. In stock AND price between $50-$300 (using Select API):")
    try:
        select = Product.select()
        select.where(
            select.match(
                select.in_stock.is_true(),
                select.price.is_between(start=50, end=300)
            )
        )
        for product in select.fetch_all():
            print(f"   - {product.name}: ${product.price}")
    except Exception as e:
        print(f"   Example query: Product.select().where(select.match(in_stock, price.is_between(...)))")

    print("\n8. Complex query - Electronics >= $100 OR furniture in stock (using Select API):")
    try:
        select = Product.select()
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
        for product in select.fetch_all():
            print(f"   - {product.name} ({product.category}): ${product.price}, in_stock={product.in_stock}")
    except Exception as e:
        print(f"   Example query: Complex nested match and at_least conditions")

    print("\n9. Sorted by price (ascending):")
    try:
        select = Product.select()
        select.sort(select.price.asc())
        for product in select.fetch_all(results_per_page=5):
            print(f"   - {product.name}: ${product.price}")
    except Exception as e:
        print(f"   Example query: Product.select().sort(select.price.asc())")

    print(f"\n10. Total products in database: {Product.count()}")

    print("\n✅ ORM-style query examples completed!")
    print("\nNote: If MongoDB is not running, queries will fail.")
    print("To run with actual database, start MongoDB at localhost:27017")

