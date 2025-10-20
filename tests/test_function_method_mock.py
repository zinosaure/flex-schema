"""
Test the function method with a mock MongoDB setup
"""
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


def test_apply_function_filters():
    """Test the _apply_function_filters method directly"""
    print("\n=== Test: Apply function filters ===")
    
    # Create test documents
    documents = [
        {"_id": "1", "name": "Laptop", "price": 1000.0, "reviews": [{"score": 4}, {"score": 5}], "tags": ["electronics", "computers"]},
        {"_id": "2", "name": "Mouse", "price": 20.0, "reviews": [{"score": 3}, {"score": 4}], "tags": ["electronics", "accessories"]},
        {"_id": "3", "name": "Desk", "price": 300.0, "reviews": [{"score": 5}], "tags": ["furniture"]},
    ]
    
    # Create a select instance
    select = Product.select()
    
    # Test 1: Discount function
    def apply_discount(document, discount: float):
        return document.price * discount
    
    function_filters = [
        ("price", {
            "functions": [(apply_discount, (0.75,))],
            "operator": "$gt",
            "value": 100
        })
    ]
    
    filtered = select._apply_function_filters(documents, function_filters)
    print(f"Documents with discounted price > 100: {len(filtered)}")
    # Laptop: 1000 * 0.75 = 750 > 100 ✓
    # Mouse: 20 * 0.75 = 15 < 100 ✗
    # Desk: 300 * 0.75 = 225 > 100 ✓
    assert len(filtered) == 2
    assert filtered[0]["name"] == "Laptop"
    assert filtered[1]["name"] == "Desk"
    
    # Test 2: List aggregation
    def sum_reviews(document):
        if isinstance(document.reviews, list) and len(document.reviews) > 0:
            return sum([review.get('score', 0) for review in document.reviews if isinstance(review, dict)])
        return 0
    
    function_filters = [
        ("reviews", {
            "functions": [(sum_reviews, ())],
            "operator": "$gte",
            "value": 7
        })
    ]
    
    filtered = select._apply_function_filters(documents, function_filters)
    print(f"Documents with review sum >= 7: {len(filtered)}")
    # Laptop: 4 + 5 = 9 >= 7 ✓
    # Mouse: 3 + 4 = 7 >= 7 ✓
    # Desk: 5 < 7 ✗
    assert len(filtered) == 2
    assert filtered[0]["name"] == "Laptop"
    assert filtered[1]["name"] == "Mouse"
    
    # Test 3: Chained functions
    def get_first_tag(document):
        if isinstance(document.tags, list) and len(document.tags) > 0:
            return document.tags[0]
        return ""
    
    def tag_length(document):
        # Get the result from previous function (which is stored in document.tags)
        if hasattr(document, 'tags'):
            return len(document.tags)
        return 0
    
    function_filters = [
        ("tags", {
            "functions": [(get_first_tag, ()), (tag_length, ())],
            "operator": "$gt",
            "value": 5
        })
    ]
    
    filtered = select._apply_function_filters(documents, function_filters)
    print(f"Documents with first tag length > 5: {len(filtered)}")
    # Laptop: "electronics" (11 chars) > 5 ✓
    # Mouse: "electronics" (11 chars) > 5 ✓
    # Desk: "furniture" (9 chars) > 5 ✓
    assert len(filtered) == 3
    
    # Test 4: Multiple comparison operators
    function_filters = [
        ("price", {
            "functions": [(lambda doc: doc.price, ())],
            "operator": "$eq",
            "value": 1000.0
        })
    ]
    filtered = select._apply_function_filters(documents, function_filters)
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Laptop"
    
    function_filters = [
        ("price", {
            "functions": [(lambda doc: doc.price, ())],
            "operator": "$ne",
            "value": 1000.0
        })
    ]
    filtered = select._apply_function_filters(documents, function_filters)
    assert len(filtered) == 2
    
    function_filters = [
        ("price", {
            "functions": [(lambda doc: doc.price, ())],
            "operator": "$lt",
            "value": 100
        })
    ]
    filtered = select._apply_function_filters(documents, function_filters)
    assert len(filtered) == 1
    assert filtered[0]["name"] == "Mouse"
    
    function_filters = [
        ("price", {
            "functions": [(lambda doc: doc.price, ())],
            "operator": "$lte",
            "value": 300
        })
    ]
    filtered = select._apply_function_filters(documents, function_filters)
    assert len(filtered) == 2
    
    print("✅ Test passed: Function filters apply correctly")


def test_extract_function_filters():
    """Test the _extract_function_filters method"""
    print("\n=== Test: Extract function filters ===")
    
    select = Product.select()
    
    # Test with function filter
    conditions = {
        "name": "Test",
        "price": {
            "$__function__": {
                "functions": [(lambda doc: doc.price, ())],
                "operator": "$gt",
                "value": 100
            }
        }
    }
    
    mongodb_cond, func_filters = select._extract_function_filters(conditions)
    
    print(f"MongoDB conditions: {mongodb_cond}")
    print(f"Function filters: {len(func_filters)}")
    
    assert "name" in mongodb_cond
    assert mongodb_cond["name"] == "Test"
    assert "price" not in mongodb_cond or "$__function__" not in str(mongodb_cond.get("price", {}))
    assert len(func_filters) == 1
    assert func_filters[0][0] == "price"
    
    # Test with nested logical operators
    conditions = {
        "$and": [
            {"name": "Test"},
            {
                "price": {
                    "$__function__": {
                        "functions": [(lambda doc: doc.price, ())],
                        "operator": "$gt",
                        "value": 100
                    }
                }
            }
        ]
    }
    
    mongodb_cond, func_filters = select._extract_function_filters(conditions)
    
    print(f"MongoDB conditions with $and: {mongodb_cond}")
    print(f"Function filters: {len(func_filters)}")
    
    assert "$and" in mongodb_cond
    assert len(func_filters) == 1
    
    print("✅ Test passed: Function filters extracted correctly")


if __name__ == "__main__":
    test_apply_function_filters()
    test_extract_function_filters()
    
    print("\n" + "=" * 50)
    print("✅ All mock tests passed!")
    print("=" * 50)
