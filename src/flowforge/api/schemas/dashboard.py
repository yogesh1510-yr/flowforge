from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class OrderStatusSummary(BaseModel):
    status: str
    count: int
    order_value: Decimal


class DashboardSummary(BaseModel):
    total_orders: int
    active_orders: int
    total_order_value: Decimal
    orders_by_status: list[OrderStatusSummary]


class LowStockItem(BaseModel):
    inventory_id: UUID
    warehouse_code: str
    product_id: UUID
    sku: str
    product_name: str
    on_hand_quantity: int
    reserved_quantity: int
    available_quantity: int


class RecentMovement(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    movement_id: UUID
    sku: str
    warehouse_code: str
    movement_type: str
    quantity_delta: int
    reference_type: str | None
    reference_id: UUID | None
    reason: str | None
    created_at: datetime
