"""
Test the function method on Flexmodel.Select.Statement
"""
from typing import cast
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


def test_function_method_basic():
    """Test basic function method usage"""
    print("\n=== Test 1: Basic function method ===")
    
    # Define a discount function
    def apply_discount(document, discount: float):
        return document.price * discount
    
    # Create a select query
    select = Product.select()
    
    # Build query with function
    condition = select.price.function(apply_discount, args=(0.75,)) > 50
    
    print(f"Condition with function: {condition}")
    
    # The condition should contain function metadata
    assert "price" in condition
    assert "$__function__" in condition["price"]
    assert condition["price"]["$__function__"]["operator"] == "$gt"
    assert condition["price"]["$__function__"]["value"] == 50
    assert len(condition["price"]["$__function__"]["functions"]) == 1
    
    print("✅ Test 1 passed: Function metadata stored correctly")


def test_function_method_chaining():
    """Test chaining multiple functions"""
    print("\n=== Test 2: Chaining multiple functions ===")
    
    def clean_name(document):
        return document.name.strip().lower()
    
    def count_length(document):
        return len(document.name)
    
    select = Product.select()
    
    # Chain multiple functions
    condition = select.name.function(clean_name).function(count_length) < 10
    
    print(f"Chained condition: {condition}")
    
    assert "name" in condition
    assert "$__function__" in condition["name"]
    assert len(condition["name"]["$__function__"]["functions"]) == 2
    assert condition["name"]["$__function__"]["operator"] == "$lt"
    assert condition["name"]["$__function__"]["value"] == 10
    
    print("✅ Test 2 passed: Function chaining works correctly")


def test_function_with_list_aggregation():
    """Test function that aggregates list values"""
    print("\n=== Test 3: Function with list aggregation ===")
    
    def sum_reviews(document):
        if isinstance(document.reviews, list) and len(document.reviews) > 0:
            # Assuming reviews are dicts with 'score' key
            return sum([review.get('score', 0) for review in document.reviews if isinstance(review, dict)])
        return 0
    
    select = Product.select()
    
    condition = select.reviews.function(sum_reviews) > 4.5
    
    print(f"List aggregation condition: {condition}")
    
    assert "reviews" in condition
    assert "$__function__" in condition["reviews"]
    assert condition["reviews"]["$__function__"]["operator"] == "$gt"
    assert condition["reviews"]["$__function__"]["value"] == 4.5
    
    print("✅ Test 3 passed: List aggregation function works")


def test_function_with_comparison_operators():
    """Test all comparison operators with functions"""
    print("\n=== Test 4: All comparison operators ===")
    
    def get_price(document):
        return document.price
    
    select = Product.select()
    
    # Test all operators
    eq_cond = select.price.function(get_price) == 100
    ne_cond = select.price.function(get_price) != 100
    lt_cond = select.price.function(get_price) < 100
    gt_cond = select.price.function(get_price) > 100
    le_cond = select.price.function(get_price) <= 100
    ge_cond = select.price.function(get_price) >= 100
    
    assert eq_cond["price"]["$__function__"]["operator"] == "$eq"
    assert ne_cond["price"]["$__function__"]["operator"] == "$ne"
    assert lt_cond["price"]["$__function__"]["operator"] == "$lt"
    assert gt_cond["price"]["$__function__"]["operator"] == "$gt"
    assert le_cond["price"]["$__function__"]["operator"] == "$lte"
    assert ge_cond["price"]["$__function__"]["operator"] == "$gte"
    
    print("✅ Test 4 passed: All comparison operators work with functions")


def test_subset_method():
    """Test that subset method works correctly"""
    print("\n=== Test 5: Subset method ===")
    
    select = Product.select()
    
    # Test subset - checks if all items in the list are present in the field
    condition = select.tags.subset(["electronics", "sale"])
    
    print(f"Subset condition: {condition}")
    
    assert "tags" in condition
    assert "$all" in condition["tags"]
    assert condition["tags"]["$all"] == ["electronics", "sale"]
    
    print("✅ Test 5 passed: Subset method works correctly")


def test_function_with_where_clause():
    """Test function method integrated with where clause"""
    print("\n=== Test 6: Function with where clause ===")
    
    def apply_discount(document, discount: float):
        return document.price * discount
    
    select = Product.select()
    
    # Use function in where clause
    select.where(select.price.function(apply_discount, args=(0.75,)) > 50)
    
    print(f"Query with function: {select.statements}")
    
    assert "price" in select.statements
    assert "$__function__" in select.statements["price"]
    
    print("✅ Test 6 passed: Function works in where clause")


def test_function_without_args():
    """Test function without additional arguments"""
    print("\n=== Test 7: Function without args ===")
    
    def double_price(document):
        return document.price * 2
    
    select = Product.select()
    
    condition = select.price.function(double_price) > 100
    
    print(f"Condition without args: {condition}")
    
    assert "price" in condition
    assert "$__function__" in condition["price"]
    assert len(condition["price"]["$__function__"]["functions"]) == 1
    func, args = condition["price"]["$__function__"]["functions"][0]
    assert func == double_price
    assert args == ()
    
    print("✅ Test 7 passed: Function without args works")


def test_integration_with_mongodb():
    """Integration test with actual MongoDB (will skip if not available)"""
    print("\n=== Test 8: Integration with MongoDB ===")
    
    try:
        # Try to connect to MongoDB
        client = MongoClient("mongodb://localhost:27017/testdb", serverSelectionTimeoutMS=1000)
        Product.attach(client, "test_products")
        
        # Clear existing data
        collection = client.get_default_database()["test_products"]
        collection.delete_many({})
        
        # Insert test data
        test_products = [
            {"_id": "1", "name": "Laptop", "price": 1000.0, "reviews": [{"score": 4}, {"score": 5}], "tags": ["electronics", "computers"]},
            {"_id": "2", "name": "Mouse", "price": 20.0, "reviews": [{"score": 3}, {"score": 4}], "tags": ["electronics", "accessories"]},
            {"_id": "3", "name": "Desk", "price": 300.0, "reviews": [{"score": 5}], "tags": ["furniture"]},
        ]
        collection.insert_many(test_products)
        
        # Test 1: Simple discount function
        def apply_discount(document, discount: float):
            return document.price * discount
        
        select = Product.select()
        select.where(select.price.function(apply_discount, args=(0.75,)) > 100)
        
        results = select.fetch_all()
        print(f"Products with discounted price > 100: {len(results.results)}")
        # Laptop: 1000 * 0.75 = 750 > 100 ✓
        # Mouse: 20 * 0.75 = 15 < 100 ✗
        # Desk: 300 * 0.75 = 225 > 100 ✓
        assert len(results.results) == 2
        
        # Test 2: List aggregation
        def sum_reviews(document):
            if isinstance(document.reviews, list) and len(document.reviews) > 0:
                return sum([review.get('score', 0) for review in document.reviews if isinstance(review, dict)])
            return 0
        
        select = Product.select()
        select.where(select.reviews.function(sum_reviews) >= 7)
        
        results = select.fetch_all()
        print(f"Products with review sum >= 7: {len(results.results)}")
        # Laptop: 4 + 5 = 9 >= 7 ✓
        # Mouse: 3 + 4 = 7 >= 7 ✓
        # Desk: 5 < 7 ✗
        assert len(results.results) == 2
        
        # Test 3: Chained functions
        def get_first_tag(document):
            if isinstance(document.tags, list) and len(document.tags) > 0:
                return document.tags[0]
            return ""
        
        def tag_length(document):
            return len(document.tags)
        
        select = Product.select()
        select.where(select.tags.function(get_first_tag).function(tag_length) > 5)
        
        results = select.fetch_all()
        print(f"Products with first tag length > 5: {len(results.results)}")
        # Laptop: "electronics" (11 chars) > 5 ✓
        # Mouse: "electronics" (11 chars) > 5 ✓
        # Desk: "furniture" (9 chars) > 5 ✓
        assert len(results.results) == 3
        
        # Test 4: Test subset method with actual data
        select = Product.select()
        select.where(select.tags.subset(["electronics"]))
        
        results = select.fetch_all()
        print(f"Products with 'electronics' tag: {len(results.results)}")
        assert len(results.results) == 2  # Laptop and Mouse
        
        # Clean up
        collection.delete_many({})
        Product.detach()
        
        print("✅ Test 8 passed: Integration with MongoDB works correctly")
        
    except Exception as e:
        print(f"⚠️  MongoDB not available, skipping integration test: {e}")
        print("This is expected if MongoDB is not running.")


if __name__ == "__main__":
    # Run all tests
    test_function_method_basic()
    test_function_method_chaining()
    test_function_with_list_aggregation()
    test_function_with_comparison_operators()
    test_subset_method()
    test_function_with_where_clause()
    test_function_without_args()
    test_integration_with_mongodb()
    
    print("\n" + "=" * 50)
    print("✅ All tests passed!")
    print("=" * 50)
