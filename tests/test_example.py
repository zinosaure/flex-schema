from typing import cast
from flexschema import Schema, Flexmodel, field

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

select = Product().select()

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

for item in select.fetch_all():
    item = cast(Product, item)
    print(f"Product: {item.name}, Price: {item.price}, In Stock: {item.in_stock}")