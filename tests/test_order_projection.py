import base64
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from flowforge.analytics.order_projection import (
    decode_decimal,
    transform_order_event,
)


def test_decode_positive_decimal():
    encoded = base64.b64encode((12345).to_bytes(4, "big", signed=True)).decode()
    assert decode_decimal(encoded, 2) == Decimal("123.45")


def test_decode_negative_decimal():
    encoded = base64.b64encode((-12345).to_bytes(4, "big", signed=True)).decode()
    assert decode_decimal(encoded, 2) == Decimal("-123.45")


def test_reject_invalid_base64():
    with pytest.raises(ValueError, match="Base64"):
        decode_decimal("not valid!", 2)


def test_reject_empty_decimal():
    with pytest.raises(ValueError, match="empty"):
        decode_decimal("", 2)


def test_timestamp_requires_timezone():
    from flowforge.analytics.order_projection import _parse_timestamp

    with pytest.raises(ValueError, match="timezone"):
        _parse_timestamp("2026-10-17T12:00:00")


def test_non_order_event_is_ignored():
    event = {"payload": {"source": {"schema": "public", "table": "products"}}}
    assert transform_order_event(
        event, topic="flowforge.public.products", partition=0, offset=0
    ) is None


def test_reject_missing_payload():
    with pytest.raises(ValueError, match="payload"):
        transform_order_event(
            {}, topic="flowforge.public.orders", partition=0, offset=0
        )
