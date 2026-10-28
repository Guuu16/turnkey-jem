"""Request and response models.

Money is transported as integer minor units (cents) so no price ever passes
through a float. The client formats it for display.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StockStatus = Literal["in_stock", "low_stock", "out_of_stock"]


class ProductSummaryOut(BaseModel):
    id: str
    name: str
    description: str
    currency: str
    image_url: str
    price_min_cents: int
    price_max_cents: int


class OptionValueOut(BaseModel):
    id: str
    label: str
    swatch: str | None = None


class OptionDimensionOut(BaseModel):
    id: str
    name: str
    values: list[OptionValueOut]


class SkuOut(BaseModel):
    id: str
    code: str
    price_cents: int
    stock: int
    stock_status: StockStatus
    purchasable: bool
    image_url: str
    options: dict[str, str] = Field(
        description='Dimension id to option-value id, e.g. {"colour": "colour_sand"}.',
    )


class ProductDetailOut(BaseModel):
    product: ProductSummaryOut
    options: list[OptionDimensionOut]
    skus: list[SkuOut]


class CartLineSkuOut(BaseModel):
    id: str
    code: str
    price_cents: int
    stock: int
    stock_status: StockStatus
    image_url: str
    options: dict[str, str]
    option_labels: dict[str, str] = Field(
        description='Dimension name to option label, e.g. {"Colour": "Sand"}.',
    )


class CartItemOut(BaseModel):
    sku_id: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    sku: CartLineSkuOut


class CartOut(BaseModel):
    id: str
    currency: str
    items: list[CartItemOut]
    item_count: int
    total_quantity: int
    subtotal_cents: int


class AddCartItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sku_id: str = Field(
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]*$",
        description="SKU identifier returned by GET /api/products/{id}.",
    )
    quantity: int = Field(
        default=1,
        ge=1,
        description="Units to add to the cart. Never a price or a stock value.",
    )


class AddCartItemOut(BaseModel):
    cart: CartOut
    item: CartItemOut
    replayed: bool
