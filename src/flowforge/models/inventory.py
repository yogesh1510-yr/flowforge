"""SQLAlchemy models for the FlowForge platform."""

import uuid
from uuid import UUID
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
        "'" + str(member.value).replace("'", "''") + "'" for member in enum_class
    )


class Inventory(Base):
    __tablename__ = "inventory"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    on_hand_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    reserved_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    warehouse: Mapped["Warehouse"] = relationship(back_populates="inventory_records")
    product: Mapped["Product"] = relationship(back_populates="inventory_records")
    reservations: Mapped[list["InventoryReservation"]] = relationship(
        back_populates="inventory"
    )
    movements: Mapped[list["InventoryMovement"]] = relationship(
        back_populates="inventory"
    )

    __table_args__ = (
        UniqueConstraint(
            "warehouse_id", "product_id", name="uq_inventory_warehouse_product"
        ),
        CheckConstraint(
            "on_hand_quantity >= 0", name="ck_inventory_on_hand_nonnegative"
        ),
        CheckConstraint(
            "reserved_quantity >= 0", name="ck_inventory_reserved_nonnegative"
        ),
        CheckConstraint(
            "reserved_quantity <= on_hand_quantity",
            name="ck_inventory_reserved_lte_on_hand",
        ),
        Index("ix_inventory_product_warehouse", "product_id", "warehouse_id"),
    )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


class InventoryReservation(Base):
    __tablename__ = "inventory_reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("order_items.id", ondelete="RESTRICT"),
        nullable=False,
    )
    inventory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory.id", ondelete="RESTRICT"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        String(20),
        default=ReservationStatus.RESERVED,
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    order_item: Mapped["OrderItem"] = relationship(back_populates="reservations")
    inventory: Mapped["Inventory"] = relationship(back_populates="reservations")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_reservations_quantity_positive"),
        CheckConstraint(
            f"status IN ({enum_values(ReservationStatus)})",
            name="ck_reservations_status",
        ),
        Index("ix_reservations_inventory_status", "inventory_id", "status"),
    )


class InventoryMovement(Base):
    __tablename__ = "inventory_movements"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    inventory_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("inventory.id", ondelete="RESTRICT"),
        nullable=False,
    )
    movement_type: Mapped[InventoryMovementType] = mapped_column(
        String(30), nullable=False
    )
    quantity_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True,
    )

    reference_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    inventory: Mapped["Inventory"] = relationship(back_populates="movements")

    __table_args__ = (
        CheckConstraint(
            f"movement_type IN ({enum_values(InventoryMovementType)})",
            name="ck_inventory_movements_type",
        ),
        CheckConstraint(
            "quantity_delta <> 0", name="ck_inventory_movements_delta_nonzero"
        ),
        Index("ix_inventory_movements_inventory_created", "inventory_id", "created_at"),
    )


# ---------------------------------------------------------------------------
# Order event history
# ---------------------------------------------------------------------------
