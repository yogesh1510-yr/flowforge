from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from flowforge.core.enums import WarehouseStatus


class WarehouseCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    address_line1: str = Field(min_length=1, max_length=250)
    city: str = Field(min_length=1, max_length=100)
    country_code: str = Field(min_length=2, max_length=2)
    timezone: str = Field(min_length=1, max_length=50)
    status: WarehouseStatus = WarehouseStatus.ACTIVE

    @field_validator("code", "name", "address_line1", "city", "timezone")
    @classmethod
    def strip_and_reject_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be blank")
        return value

    @field_validator("code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.upper()

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        value = value.strip().upper()
        if len(value) != 2 or not value.isalpha() or not value.isascii():
            raise ValueError("Country code must contain two ASCII letters")
        return value


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    address_line1: str
    city: str
    country_code: str
    timezone: str
    status: WarehouseStatus
    created_at: datetime
