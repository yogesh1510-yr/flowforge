from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from flowforge.core.enums import ReservationStatus


class ReservationCreate(BaseModel):
    order_item_id: UUID
    inventory_id: UUID
    quantity: int = Field(gt=0)
    expires_at: datetime | None = None


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_item_id: UUID
    inventory_id: UUID
    quantity: int
    status: ReservationStatus
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
