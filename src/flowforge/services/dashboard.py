from decimal import Decimal

from sqlalchemy.orm import Session

from flowforge.core.enums import OrderStatus
from flowforge.repositories import dashboard as dashboard_repository
from flowforge.api.schemas.dashboard import (
    DashboardSummary,
    LowStockItem,
    OrderStatusSummary,
    RecentMovement,
)


def get_summary(session: Session) -> DashboardSummary:
    rows = dashboard_repository.get_order_summary(session)

    orders_by_status = []
    total_orders = 0
    active_orders = 0
    total_order_value = Decimal("0")

    inactive_statuses = {
        OrderStatus.DELIVERED.value,
        OrderStatus.CANCELLED.value,
    }

    for status, count, order_value in rows:
        status_value = status.value if hasattr(status, "value") else str(status)

        orders_by_status.append(
            OrderStatusSummary(
                status=status_value,
                count=count,
                order_value=order_value,
            )
        )

        total_orders += count

        if status_value not in inactive_statuses:
            active_orders += count

        if status_value != OrderStatus.CANCELLED.value:
            total_order_value += order_value

    return DashboardSummary(
        total_orders=total_orders,
        active_orders=active_orders,
        total_order_value=total_order_value,
        orders_by_status=orders_by_status,
    )


def get_low_stock(
    session: Session,
    *,
    threshold: int = 5,
    limit: int = 50,
) -> list[LowStockItem]:
    rows = dashboard_repository.get_low_stock(
        session,
        threshold=threshold,
        limit=limit,
    )

    return [
        LowStockItem(
            inventory_id=row[0],
            warehouse_code=row[1],
            product_id=row[2],
            sku=row[3],
            product_name=row[4],
            on_hand_quantity=row[5],
            reserved_quantity=row[6],
            available_quantity=row[7],
        )
        for row in rows
    ]


def get_recent_movements(
    session: Session,
    *,
    limit: int = 20,
) -> list[RecentMovement]:
    rows = dashboard_repository.get_recent_movements(
        session,
        limit=limit,
    )

    return [
        RecentMovement(
            movement_id=row[0],
            sku=row[1],
            warehouse_code=row[2],
            movement_type=(row[3].value if hasattr(row[3], "value") else str(row[3])),
            quantity_delta=row[4],
            reference_type=row[5],
            reference_id=row[6],
            reason=row[7],
            created_at=row[8],
        )
        for row in rows
    ]
