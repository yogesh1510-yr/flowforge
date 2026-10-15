from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

from flowforge.core.enums import InventoryMovementType


class InventoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_id: UUID
    product_id: UUID
    on_hand_quantity: int
    reserved_quantity: int
    updated_at: datetime


class InventoryMovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inventory_id: UUID
    movement_type: InventoryMovementType
    quantity_delta: int
    reference_type: str | None
    reference_id: UUID | None
    reason: str | None
    created_at: datetime


class StockReceipt(BaseModel):
    warehouse_id: UUID
    product_id: UUID
    quantity: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=2000)


class StockAdjustment(BaseModel):
    inventory_id: UUID
    quantity_delta: int
    reason: str = Field(min_length=1, max_length=2000)


class StockTransfer(BaseModel):
    source_warehouse_id: UUID
    destination_warehouse_id: UUID
    product_id: UUID
    quantity: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("reason cannot be blank")
        return value

    @model_validator(mode="after")
    def validate_warehouses(self):
        if self.source_warehouse_id == self.destination_warehouse_id:
            raise ValueError("Source and destination warehouses must be different")
        return self


class StockTransferResult(BaseModel):
    transfer_id: UUID
    product_id: UUID
    quantity: int
    source_inventory: InventoryRead
    destination_inventory: InventoryRead
