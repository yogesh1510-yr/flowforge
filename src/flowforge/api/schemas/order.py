from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from flowforge.core.enums import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    customer_id: UUID
    currency: str = Field(min_length=3, max_length=3)
    shipping_address_snapshot: dict[str, str]
    items: list[OrderItemCreate] = Field(min_length=1)
    tax_amount: Decimal = Field(default=Decimal("0"), ge=0)
    shipping_amount: Decimal = Field(default=Decimal("0"), ge=0)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0)

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isascii() or not value.isalpha():
            raise ValueError("Currency must contain three ASCII letters")
        return value

    @field_validator("shipping_address_snapshot")
    @classmethod
    def validate_shipping_address(cls, value: dict[str, str]) -> dict[str, str]:
        cleaned = {key: item.strip() for key, item in value.items()}
        if not cleaned or any(
            not key.strip() or not item for key, item in cleaned.items()
        ):
            raise ValueError("Shipping address fields must not be blank")
        return cleaned


class OrderItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_id: UUID
    sku_snapshot: str
    product_name_snapshot: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    created_at: datetime


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_number: str
    customer_id: UUID
    status: OrderStatus
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    shipping_address_snapshot: dict[str, str]
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    event_type: str
    event_version: int
    payload: dict
    occurred_at: datetime
    recorded_at: datetime
