from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrderIntelligenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: UUID
    order_number: str
    customer_id: UUID
    status: str
    currency: str
    subtotal: Decimal
    tax_amount: Decimal
    shipping_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    created_at: datetime
    updated_at: datetime
    order_age_seconds: Decimal | None
    source_topic: str
    source_partition: int
    source_offset: int
    projected_at: datetime
