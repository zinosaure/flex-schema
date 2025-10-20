"""
Test that the exact examples from the problem statement work correctly
"""
from flexschema import Schema, Flexmodel, field, field_constraint


class Product(Flexmodel):
    schema: Schema = Schema.ident(
        name=field(str, nullable=False),
        prize=field(float, default=0.0),  # Note: 'prize' as in problem statement
        review_score=field(float, default=0.0),
        reviews=field(list, default=[], constraint=field_constraint(item_type=dict)),
    )

    def __init__(self, **kwargs):
        self.name: str = self.default["name"]
        self.prize: float = self.default["prize"]
        self.review_score: float = self.default["review_score"]
        self.reviews: list = self.default["reviews"]

        super().__init__(**kwargs)


def test_example_1_discount():
    """Test the first example from the problem statement"""
    print("\n=== Example 1: Apply discount ===")
    
    def apply_discount(document, discount: float):
        return document.prize * discount
    
    select = Product.select()
    condition = select.prize.function(apply_discount, args=(1 - .25,)) > 50
    
    print(f"select.prize.function(apply_discount, args=(1 - .25,)) > 50")
    print(f"Result: {condition}")
    
    assert "prize" in condition
    assert "$__function__" in condition["prize"]
    assert condition["prize"]["$__function__"]["operator"] == "$gt"
    assert condition["prize"]["$__function__"]["value"] == 50
    
    print("✅ Example 1 works correctly")


def test_example_2_sum_reviews():
    """Test the second example from the problem statement"""
    print("\n=== Example 2: Sum reviews ===")
    
    def sum_reviews(document):
        if isinstance(document.reviews, list):
            return sum([review.get('score', 0) for review in document.reviews if isinstance(review, dict)])
        return 0
    
    select = Product.select()
    condition = select.review_score.function(sum_reviews) > 4.5
    
    print(f"select.review_score.function(sum_reviews) > 4.5")
    print(f"Result: {condition}")
    
    assert "review_score" in condition
    assert "$__function__" in condition["review_score"]
    assert condition["review_score"]["$__function__"]["operator"] == "$gt"
    assert condition["review_score"]["$__function__"]["value"] == 4.5
    
    print("✅ Example 2 works correctly")


def test_example_3_chained_functions():
    """Test the third example from the problem statement (chained functions)"""
    print("\n=== Example 3: Chained functions ===")
    
    def clean_name(document):
        if hasattr(document, 'name') and isinstance(document.name, str):
            return document.name.strip().lower()
        return ""
    
    def count_length(document):
        if hasattr(document, 'name'):
            return len(document.name)
        return 0
    
    select = Product.select()
    condition = select.name.function(clean_name).function(count_length) < 3
    
    print(f"select.name.function(clean_name).function(count_length) < 3")
    print(f"Result: {condition}")
    
    assert "name" in condition
    assert "$__function__" in condition["name"]
    assert len(condition["name"]["$__function__"]["functions"]) == 2
    assert condition["name"]["$__function__"]["operator"] == "$lt"
    assert condition["name"]["$__function__"]["value"] == 3
    
    print("✅ Example 3 works correctly")


def test_subset_method():
    """Verify that the subset method works as specified"""
    print("\n=== Subset method verification ===")
    
    class Product2(Flexmodel):
        schema: Schema = Schema.ident(
            tags=field(list, default=[], constraint=field_constraint(item_type=str)),
        )
    
    select = Product2.select()
    
    # Test that subset checks if a list is present in another list
    condition = select.tags.subset(["electronics", "sale"])
    
    print(f"select.tags.subset(['electronics', 'sale'])")
    print(f"Result: {condition}")
    print("This checks if ALL items in the provided list are present in the tags field")
    
    assert "tags" in condition
    assert "$all" in condition["tags"]
    assert condition["tags"]["$all"] == ["electronics", "sale"]
    
    print("✅ Subset method works correctly")


if __name__ == "__main__":
    test_example_1_discount()
    test_example_2_sum_reviews()
    test_example_3_chained_functions()
    test_subset_method()
    
    print("\n" + "=" * 50)
    print("✅ All problem statement examples work correctly!")
    print("=" * 50)
