"""SQLAlchemy models for the FlowForge platform."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any
from enum import Enum

from sqlalchemy import (
    CHAR,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flowforge.db.base import Base
from flowforge.core.enums import (
    CustomerStatus,
    InventoryMovementType,
    OrderStatus,
    ProductStatus,
    ReservationStatus,
    WarehouseStatus,
)


def enum_values(enum_class: type[Enum]) -> str:
    """Return enum values as a SQL-safe, quoted list."""
    return ", ".join(
        "'" + str(member.value).replace("'", "''") + "'"
        for member in enum_class
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[OrderStatus] = mapped_column(
        String(20),
        default=OrderStatus.PENDING,
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(CHAR(3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default=text("0")
    )
    shipping_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default=text("0")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0"), server_default=text("0")
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_address_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    customer: Mapped["Customer"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order")
    events: Mapped[list["OrderEvent"]] = relationship(back_populates="order")

    __table_args__ = (
        CheckConstraint(
            f"status IN ({enum_values(OrderStatus)})",
            name="ck_orders_status",
        ),
        CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_nonnegative"),
        CheckConstraint("tax_amount >= 0", name="ck_orders_tax_nonnegative"),
        CheckConstraint("shipping_amount >= 0", name="ck_orders_shipping_nonnegative"),
        CheckConstraint("discount_amount >= 0", name="ck_orders_discount_nonnegative"),
        CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        Index("ix_orders_customer_created", "customer_id", "created_at"),
        Index("ix_orders_status_created", "status", "created_at"),
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    sku_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    product_name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")
    reservations: Mapped[list["InventoryReservation"]] = relationship(
        back_populates="order_item"
    )

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_price_nonnegative"),
        CheckConstraint("line_total >= 0", name="ck_order_items_total_nonnegative"),
        Index("ix_order_items_order_id", "order_id"),
    )


# ---------------------------------------------------------------------------
# Inventory reservations and movements
# ---------------------------------------------------------------------------


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("orders.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    event_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    order: Mapped["Order"] = relationship(back_populates="events")

    __table_args__ = (
        CheckConstraint("event_version > 0", name="ck_order_events_version_positive"),
        Index("ix_order_events_order_occurred", "order_id", "occurred_at"),
    )

