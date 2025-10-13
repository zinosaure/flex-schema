"""
Test suite for FlexmodelSQLite functionality
"""
import sqlite3
import tempfile
import os
from flexschema import Schema, Flex, FlexmodelSQLite, field, field_constraint


def test_basic_sqlite_operations():
    """Test basic CRUD operations with SQLite"""
    print("Testing basic SQLite operations...")
    
    # Create a simple model
    class Product(FlexmodelSQLite):
        schema: Schema = Schema.ident(
            name=field(str, nullable=False),
            price=field(float, default=0.0),
            in_stock=field(bool, default=True),
        )
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        Product.attach(conn, "products")
        
        # Test create and commit
        product = Product(name="Laptop", price=999.99, in_stock=True)
        assert product.commit(), "Failed to save product"
        assert product.id is not None, "Product ID should be set"
        product_id = product.id
        
        # Test load
        loaded_product = Product.load(product_id)
        assert loaded_product is not None, "Failed to load product"
        assert loaded_product.name == "Laptop", "Loaded product name mismatch"
        assert loaded_product.price == 999.99, "Loaded product price mismatch"
        
        # Test count
        assert Product.count() == 1, "Count should be 1"
        
        # Create another product
        product2 = Product(name="Mouse", price=29.99, in_stock=False)
        product2.commit()
        assert Product.count() == 2, "Count should be 2"
        
        # Test fetch
        fetched = Product.fetch({"name": "Mouse"})
        assert fetched is not None, "Failed to fetch product"
        assert fetched.price == 29.99, "Fetched product price mismatch"
        
        # Test fetch_all
        pagination = Product.fetch_all({}, page=1, item_per_page=10)
        assert len(pagination.items) == 2, "fetch_all should return 2 items"
        assert pagination.total_items == 2, "Total items should be 2"
        
        # Test update
        product.price = 899.99
        product.commit()
        reloaded = Product.load(product_id)
        assert reloaded.price == 899.99, "Price update failed"
        
        # Test delete
        assert product.delete(), "Failed to delete product"
        assert Product.count() == 1, "Count should be 1 after delete"
        
        # Test truncate
        Product.truncate()
        assert Product.count() == 0, "Count should be 0 after truncate"
        
        conn.close()
        print("✅ Basic SQLite operations test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_nested_models():
    """Test nested models with SQLite"""
    print("\nTesting nested models with SQLite...")
    
    class Address(Flex):
        schema: Schema = Schema(
            street=field(str, nullable=False),
            city=field(str, nullable=False),
            zipcode=field(str, default="00000"),
        )
    
    class Person(FlexmodelSQLite):
        schema: Schema = Schema.ident(
            name=field(str, nullable=False),
            age=field(int, default=0),
            address=field(Address, nullable=False, default=Address()),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        Person.attach(conn, "persons")
        
        # Create person with nested address
        person = Person(
            name="Alice",
            age=30,
            address=Address(street="123 Main St", city="Springfield", zipcode="12345")
        )
        assert person.commit(), "Failed to save person"
        
        # Load and verify nested data
        loaded = Person.load(person.id)
        assert loaded is not None, "Failed to load person"
        assert loaded.name == "Alice", "Name mismatch"
        assert loaded.address.street == "123 Main St", "Nested street mismatch"
        assert loaded.address.city == "Springfield", "Nested city mismatch"
        
        conn.close()
        print("✅ Nested models test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_schema_validation():
    """Test schema validation with SQLite"""
    print("\nTesting schema validation...")
    
    class ValidatedModel(FlexmodelSQLite):
        schema: Schema = Schema.ident(
            email=field(
                str,
                nullable=False,
                constraint=field_constraint(pattern=r"[^@]+@[^@]+\.[^@]+"),
            ),
            password=field(
                str,
                nullable=False,
                constraint=field_constraint(min_length=8),
            ),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        ValidatedModel.attach(conn, "validated")
        
        # Test invalid data (should not commit)
        invalid_model = ValidatedModel(email="invalid-email", password="short")
        assert not invalid_model.commit(), "Should fail validation"
        
        # Test valid data
        valid_model = ValidatedModel(email="test@example.com", password="longenoughpassword")
        assert valid_model.commit(), "Should pass validation and save"
        
        conn.close()
        print("✅ Schema validation test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_table_structure():
    """Verify that SQLite table has the correct structure"""
    print("\nTesting table structure...")
    
    class TestModel(FlexmodelSQLite):
        schema: Schema = Schema.ident(
            data=field(str, default="test"),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        TestModel.attach(conn, "test_table")
        
        # Verify table structure
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(test_table)")
        columns = cursor.fetchall()
        
        column_names = [col[1] for col in columns]
        assert "_id" in column_names, "Table should have _id column"
        assert "_updated_at" in column_names, "Table should have _updated_at column"
        assert "document" in column_names, "Table should have document column"
        
        # Verify _id is PRIMARY KEY
        primary_keys = [col for col in columns if col[5] == 1]  # col[5] is the pk flag
        assert len(primary_keys) == 1, "Should have exactly one primary key"
        assert primary_keys[0][1] == "_id", "Primary key should be _id"
        
        conn.close()
        print("✅ Table structure test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


def test_pagination():
    """Test pagination functionality"""
    print("\nTesting pagination...")
    
    class Item(FlexmodelSQLite):
        schema: Schema = Schema.ident(
            name=field(str, nullable=False),
        )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.sqlite') as f:
        db_path = f.name
    
    try:
        conn = sqlite3.connect(db_path)
        Item.attach(conn, "items")
        
        # Create 15 items
        for i in range(15):
            item = Item(name=f"Item {i+1}")
            item.commit()
        
        # Test first page
        page1 = Item.fetch_all({}, page=1, item_per_page=5)
        assert len(page1.items) == 5, "First page should have 5 items"
        assert page1.total_items == 15, "Total should be 15"
        assert page1.page == 1, "Page should be 1"
        
        # Test second page
        page2 = Item.fetch_all({}, page=2, item_per_page=5)
        assert len(page2.items) == 5, "Second page should have 5 items"
        
        # Test last page
        page3 = Item.fetch_all({}, page=3, item_per_page=5)
        assert len(page3.items) == 5, "Third page should have 5 items"
        
        # Test page beyond limit
        page4 = Item.fetch_all({}, page=4, item_per_page=5)
        assert len(page4.items) == 0, "Fourth page should be empty"
        
        conn.close()
        print("✅ Pagination test passed")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)


if __name__ == "__main__":
    print("Running FlexmodelSQLite test suite...\n")
    print("=" * 60)
    
    test_basic_sqlite_operations()
    test_nested_models()
    test_schema_validation()
    test_table_structure()
    test_pagination()
    
    print("\n" + "=" * 60)
    print("✅ All tests passed successfully!")
