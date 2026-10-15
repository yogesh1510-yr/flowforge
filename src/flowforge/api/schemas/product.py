from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from flowforge.core.enums import ProductStatus


class ProductCreate(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category_id: UUID | None = None
    current_price: Decimal = Field(
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    currency: str = Field(min_length=3, max_length=3)
    status: ProductStatus = ProductStatus.ACTIVE

    @field_validator("sku", "name")
    @classmethod
    def strip_required_strings(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("Currency must be a three-letter code")
        return value


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sku: str
    name: str
    description: str | None
    category_id: UUID | None
    current_price: Decimal
    currency: str
    status: ProductStatus
    created_at: datetime
    updated_at: datetime
