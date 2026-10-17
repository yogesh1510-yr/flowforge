import pytest

from flowforge.analytics.order_projection_writer import (
    _validate_order_record,
)


def valid_record():
    return {
        "source_lsn": 100,
        "source_partition": 0,
        "source_offset": 12,
        "source_topic": "flowforge.public.orders",
        "is_deleted": False,
    }


def test_accepts_valid_ordering_metadata():
    _validate_order_record(valid_record())


@pytest.mark.parametrize(
    "field",
    ["source_lsn", "source_partition", "source_offset"],
)
def test_rejects_missing_ordering_metadata(field):
    record = valid_record()
    record[field] = None

    with pytest.raises(ValueError, match=field):
        _validate_order_record(record)


@pytest.mark.parametrize(
    "field",
    ["source_lsn", "source_partition", "source_offset"],
)
def test_rejects_negative_ordering_metadata(field):
    record = valid_record()
    record[field] = -1

    with pytest.raises(ValueError, match=field):
        _validate_order_record(record)


@pytest.mark.parametrize(
    "field",
    ["source_lsn", "source_partition", "source_offset"],
)
def test_rejects_boolean_ordering_metadata(field):
    record = valid_record()
    record[field] = True

    with pytest.raises(ValueError, match=field):
        _validate_order_record(record)


def test_rejects_empty_topic():
    record = valid_record()
    record["source_topic"] = " "

    with pytest.raises(ValueError, match="source_topic"):
        _validate_order_record(record)


def test_rejects_non_boolean_delete_flag():
    record = valid_record()
    record["is_deleted"] = "false"

    with pytest.raises(ValueError, match="is_deleted"):
        _validate_order_record(record)
