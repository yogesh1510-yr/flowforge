"""Pure transformations for Debezium order CDC events."""

import base64
import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

MONEY_FIELDS = (
    "subtotal",
    "tax_amount",
    "shipping_amount",
    "discount_amount",
    "total_amount",
)

ORDER_FIELDS = (
    "id",
    "order_number",
    "customer_id",
    "status",
    "currency",
    *MONEY_FIELDS,
    "created_at",
    "updated_at",
)


def _find_field_schema(schema: Any, field_name: str) -> dict:
    """Find a Connect field schema by its field name."""
    if isinstance(schema, dict):
        if schema.get("field") == field_name:
            return schema
        for value in schema.values():
            try:
                return _find_field_schema(value, field_name)
            except LookupError:
                pass
    elif isinstance(schema, list):
        for value in schema:
            try:
                return _find_field_schema(value, field_name)
            except LookupError:
                pass

    raise LookupError(f"No schema metadata found for field: {field_name}")


def decode_decimal(value: str, scale: int) -> Decimal:
    """Decode Debezium Connect Decimal bytes into an exact Decimal."""
    if not isinstance(value, str):
        raise ValueError("Decimal payload must be a Base64 string")

    try:
        raw = base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError("Invalid Base64 decimal payload") from exc

    if not raw:
        raise ValueError("Decimal payload cannot be empty")

    unscaled = int.from_bytes(raw, byteorder="big", signed=True)
    return Decimal(unscaled).scaleb(-scale)


def _parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("Timestamp must be a string")

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed


def transform_order_event(
    raw_event: str | dict,
    *,
    topic: str,
    partition: int,
    offset: int,
) -> dict | None:
    """
    Transform a Debezium order event into a typed projection record.

    Returns None for non-order events.
    For deletes, returns the prior row with is_deleted=True.
    Does not write to any database.
    """
    event = json.loads(raw_event) if isinstance(raw_event, str) else raw_event

    if not isinstance(event, dict):
        raise ValueError("CDC event must be a JSON object")

    payload = event.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("CDC event is missing its payload envelope")

    source = payload.get("source") or {}
    if source.get("table") != "orders" or source.get("schema") != "public":
        return None

    operation = payload.get("op")
    if operation not in {"r", "c", "u", "d"}:
        raise ValueError(f"Unsupported order CDC operation: {operation!r}")

    is_deleted = operation == "d"
    record = payload.get("before") if is_deleted else payload.get("after")

    if not isinstance(record, dict):
        raise ValueError(f"CDC operation {operation!r} has no usable row")

    missing = [name for name in ORDER_FIELDS if name not in record]
    if missing:
        raise ValueError(f"Order payload missing fields: {', '.join(missing)}")

    created_at = _parse_timestamp(record["created_at"])
    updated_at = _parse_timestamp(record["updated_at"])

    result = {
        "order_id": UUID(record["id"]),
        "order_number": record["order_number"],
        "customer_id": UUID(record["customer_id"]),
        "status": record["status"],
        "currency": record["currency"],
        "created_at": created_at,
        "updated_at": updated_at,
        "order_age_seconds": max(
            Decimal("0"),
            Decimal(str((updated_at - created_at).total_seconds())),
        ),
        "source_lsn": int(source["lsn"]) if source.get("lsn") is not None else None,
        "source_txid": int(source["txId"]) if source.get("txId") is not None else None,
        "source_topic": topic,
        "source_partition": partition,
        "source_offset": offset,
        "is_deleted": is_deleted,
    }

    for field in MONEY_FIELDS:
        metadata = _find_field_schema(event.get("schema", {}), field)
        if metadata.get("name") != "org.apache.kafka.connect.data.Decimal":
            raise ValueError(f"Unexpected decimal schema for {field}")

        scale = int((metadata.get("parameters") or {}).get("scale", 0))
        result[field] = decode_decimal(record[field], scale)

    return result
