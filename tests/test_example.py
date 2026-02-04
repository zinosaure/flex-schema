from typing import cast
from flexschema import Schema, Flexmodel, FlexmodelLite, field

class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        price=field(float, default=0.0),
        in_stock=field(bool, default=True),
    )

    def __init__(self, **kwargs):
        self.name: str = self.default["name"]
        self.price: float = self.default["price"]
        self.in_stock: bool = self.default["in_stock"]

        super().__init__(**kwargs)

# Choose storage
choice = input("Select storage [mongo/sqlite]: ").strip().lower()

if choice.startswith("s"):
    class ProductLite(FlexmodelLite):
        schema: Schema = Product.schema

    try:
        ProductLite.attach(":memory:", "products")
        ProductLite(name="Shoes", price=79.99, in_stock=True).commit()
        ProductLite(name="Boots", price=120.0, in_stock=False).commit()

        select = ProductLite.select()

        select.where(select.name == "Shoes")
        select.where(
            select.match(
                select.at_least(
                    select.in_stock.is_false(),
                    select.in_stock.is_true(),
                ),
                select.price < 100,
            )
        )

        print("Query built successfully!")
        print(f"Query: {select.query_string}")
        print(f"SQL: {select.to_sql}")

        for item in select.fetch_all():
            item = cast(ProductLite, item)
            print(f"Product: {item.name}, Price: {item.price}, In Stock: {item.in_stock}")
    except Exception as e:
        print(f"⚠️  SQLite not available: {e}")
else:
    # Connect to MongoDB (will fail gracefully if not available)
    try:
        from pymongo import MongoClient

        client = MongoClient("mongodb://localhost:27017/testdb", serverSelectionTimeoutMS=1000)
        Product.attach(client, "products")
        
        # Create a select query
        select = Product.select()

        select.where(select.name == "Shoes")
        select.where(
            select.match(
                select.at_least(
                    select.in_stock.is_false(),
                    select.in_stock.is_true(),
                ),
                select.price < 100,
            )
        )

        print("Query built successfully!")
        print(f"Query: {select.query_string}")
        print(f"SQL: {select.to_sql}")
        
        # Try to fetch results (will fail if MongoDB is not running)
        try:
            for item in select.fetch_all():
                item = cast(Product, item)
                print(f"Product: {item.name}, Price: {item.price}, In Stock: {item.in_stock}")
        except Exception as e:
            print(f"\n⚠️  Could not fetch from database: {e}")
            print("This is expected if MongoDB is not running.")
            
    except Exception as e:
        print(f"⚠️  MongoDB not available: {e}")
        print("To run this example with database access, start MongoDB at localhost:27017")