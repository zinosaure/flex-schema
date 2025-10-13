"""
Test suite for MongoDB operator support in SQLite
"""
import sqlite3
import tempfile
import os
from flexschema import Schema, Flexmodel, field


def test_comparison_operators():
    """Test MongoDB comparison operators ($gt, $gte, $lt, $lte, $ne, $eq)"""
    print("Testing comparison operators...")
    
    class Product(Flexmodel):
        schema: Schema = Schema.ident(
            name=field(str, nullable=False),
            price=field(float, default=0.0),
            quantity=field(int, default=0),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        Product.attach(conn, "products")
        
        # Create test data
        products = [
            Product(name="Laptop", price=999.99, quantity=10),
            Product(name="Mouse", price=29.99, quantity=50),
            Product(name="Keyboard", price=79.99, quantity=30),
            Product(name="Monitor", price=299.99, quantity=15),
        ]
        for p in products:
            p.commit()
        
        # Test $gt
        result = Product.fetch({"price": {"$gt": 100}})
        assert result is not None, "$gt should find a product"
        assert result.price > 100, f"Product price should be > 100, got {result.price}"
        
        # Test $gte
        result = Product.fetch({"price": {"$gte": 299.99}})
        assert result is not None, "$gte should find a product"
        assert result.price >= 299.99, f"Product price should be >= 299.99, got {result.price}"
        
        # Test $lt
        result = Product.fetch({"price": {"$lt": 50}})
        assert result is not None, "$lt should find a product"
        assert result.price < 50, f"Product price should be < 50, got {result.price}"
        
        # Test $lte
        result = Product.fetch({"price": {"$lte": 29.99}})
        assert result is not None, "$lte should find a product"
        assert result.price <= 29.99, f"Product price should be <= 29.99, got {result.price}"
        
        # Test $ne
        result = Product.fetch({"name": {"$ne": "Mouse"}})
        assert result is not None, "$ne should find a product"
        assert result.name != "Mouse", f"Product name should not be Mouse, got {result.name}"
        
        # Test $eq
        result = Product.fetch({"name": {"$eq": "Laptop"}})
        assert result is not None, "$eq should find a product"
        assert result.name == "Laptop", f"Product name should be Laptop, got {result.name}"
        
        # Test fetch_all with comparison operators
        results = Product.fetch_all({"quantity": {"$gte": 30}})
        assert len(results.items) == 2, f"Should find 2 products with quantity >= 30, got {len(results.items)}"
        
        conn.close()
        print("✅ Comparison operators test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_array_operators():
    """Test MongoDB array operators ($in, $nin)"""
    print("\nTesting array operators...")
    
    class Product(Flexmodel):
        schema: Schema = Schema.ident(
            name=field(str, nullable=False),
            category=field(str, nullable=False),
            price=field(float, default=0.0),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        Product.attach(conn, "products")
        
        # Create test data
        products = [
            Product(name="Laptop", category="electronics", price=999.99),
            Product(name="Mouse", category="electronics", price=29.99),
            Product(name="Desk", category="furniture", price=299.99),
            Product(name="Chair", category="furniture", price=199.99),
            Product(name="Pen", category="stationery", price=1.99),
        ]
        for p in products:
            p.commit()
        
        # Test $in
        result = Product.fetch({"category": {"$in": ["electronics", "stationery"]}})
        assert result is not None, "$in should find a product"
        assert result.category in ["electronics", "stationery"], f"Category should be in list, got {result.category}"
        
        # Test $in with fetch_all
        results = Product.fetch_all({"category": {"$in": ["electronics", "furniture"]}})
        assert len(results.items) == 4, f"Should find 4 products, got {len(results.items)}"
        
        # Test $nin
        result = Product.fetch({"category": {"$nin": ["electronics", "furniture"]}})
        assert result is not None, "$nin should find a product"
        assert result.category not in ["electronics", "furniture"], f"Category should not be in list, got {result.category}"
        
        # Test $nin with fetch_all
        results = Product.fetch_all({"category": {"$nin": ["electronics"]}})
        assert len(results.items) == 3, f"Should find 3 products, got {len(results.items)}"
        
        conn.close()
        print("✅ Array operators test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_existence_operator():
    """Test MongoDB existence operator ($exists)"""
    print("\nTesting existence operator...")
    
    class Product(Flexmodel):
        schema: Schema = Schema.ident(
            name=field(str, nullable=False),
            description=field(str, nullable=True, default=None),
            price=field(float, default=0.0),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        Product.attach(conn, "products")
        
        # Create test data
        p1 = Product(name="Laptop", description="A powerful laptop", price=999.99)
        p1.commit()
        
        p2 = Product(name="Mouse", price=29.99)  # No description
        p2.commit()
        
        # Test $exists: true
        result = Product.fetch({"description": {"$exists": True}})
        assert result is not None, "$exists True should find a product"
        assert result.description is not None, "Product should have description"
        
        # Test $exists: false
        result = Product.fetch({"description": {"$exists": False}})
        assert result is not None, "$exists False should find a product"
        assert result.description is None, "Product should not have description"
        
        conn.close()
        print("✅ Existence operator test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_logical_operators():
    """Test MongoDB logical operators ($and, $or)"""
    print("\nTesting logical operators...")
    
    class Product(Flexmodel):
        schema: Schema = Schema.ident(
            name=field(str, nullable=False),
            price=field(float, default=0.0),
            in_stock=field(bool, default=True),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        Product.attach(conn, "products")
        
        # Create test data
        products = [
            Product(name="Laptop", price=999.99, in_stock=True),
            Product(name="Mouse", price=29.99, in_stock=True),
            Product(name="Keyboard", price=79.99, in_stock=False),
            Product(name="Monitor", price=299.99, in_stock=True),
        ]
        for p in products:
            p.commit()
        
        # Test $or
        results = Product.fetch_all({"$or": [{"price": {"$lt": 50}}, {"price": {"$gt": 500}}]})
        assert len(results.items) == 2, f"Should find 2 products with $or, got {len(results.items)}"
        
        # Test $and (implicit)
        result = Product.fetch({"price": {"$gt": 50}, "in_stock": True})
        assert result is not None, "Implicit $and should find a product"
        assert result.price > 50 and result.in_stock, "Product should match both conditions"
        
        # Test explicit $and
        results = Product.fetch_all({"$and": [{"price": {"$gt": 50}}, {"in_stock": True}]})
        assert len(results.items) == 2, f"Should find 2 products with $and, got {len(results.items)}"
        
        conn.close()
        print("✅ Logical operators test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_combined_operators():
    """Test combined use of multiple operators"""
    print("\nTesting combined operators...")
    
    class Product(Flexmodel):
        schema: Schema = Schema.ident(
            name=field(str, nullable=False),
            price=field(float, default=0.0),
            category=field(str, nullable=False),
            in_stock=field(bool, default=True),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        Product.attach(conn, "products")
        
        # Create test data
        products = [
            Product(name="Laptop", price=999.99, category="electronics", in_stock=True),
            Product(name="Mouse", price=29.99, category="electronics", in_stock=True),
            Product(name="Desk", price=299.99, category="furniture", in_stock=False),
            Product(name="Chair", price=199.99, category="furniture", in_stock=True),
        ]
        for p in products:
            p.commit()
        
        # Test multiple operators on same field (range query)
        results = Product.fetch_all({
            "price": {"$gte": 100, "$lte": 500}
        })
        assert len(results.items) == 2, f"Should find 2 products in price range 100-500, got {len(results.items)}"
        for item in results.items:
            assert 100 <= item.price <= 500, f"Price should be between 100-500, got {item.price}"
        
        # Complex query: electronics with price >= 50 OR furniture in stock
        results = Product.fetch_all({
            "$or": [
                {"$and": [{"category": "electronics"}, {"price": {"$gte": 50}}]},
                {"$and": [{"category": "furniture"}, {"in_stock": True}]}
            ]
        })
        assert len(results.items) == 2, f"Complex query should find 2 products, got {len(results.items)}"
        
        # Query with $in and comparison
        results = Product.fetch_all({
            "category": {"$in": ["electronics", "furniture"]},
            "price": {"$lt": 300}
        })
        assert len(results.items) == 3, f"Should find 3 products, got {len(results.items)}"
        
        conn.close()
        print("✅ Combined operators test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    print("Running MongoDB Operators test suite for SQLite...\n")
    print("=" * 60)
    
    test_comparison_operators()
    test_array_operators()
    test_existence_operator()
    test_logical_operators()
    test_combined_operators()
    
    print("\n" + "=" * 60)
    print("✅ All MongoDB operator tests passed successfully!")
