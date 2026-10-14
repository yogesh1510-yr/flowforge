from enum import StrEnum


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProductStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class WarehouseStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ReservationStatus(StrEnum):
    RESERVED = "reserved"
    RELEASED = "released"
    CONSUMED = "consumed"
    EXPIRED = "expired"


class InventoryMovementType(StrEnum):
    RECEIPT = "receipt"
    DISPATCH = "dispatch"
    ADJUSTMENT = "adjustment"
    DAMAGE = "damage"
    RETURN = "return"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
