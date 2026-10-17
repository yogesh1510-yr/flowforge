
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class OrderIntelligenceSummary(BaseModel):
    total_orders: int
    orders_by_status: dict[str, int]
    total_value_by_currency: dict[str, Decimal]
    latest_projection_at: datetime | None
    latest_order_updated_at: datetime | None
