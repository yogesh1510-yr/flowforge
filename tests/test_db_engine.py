from unittest.mock import MagicMock, patch

from flowforge.db import engine as db_engine


def test_dispose_database_engine_disposes_engine() -> None:
    fake_engine = MagicMock()

    with patch.object(
        db_engine,
        "get_database_engine",
        return_value=fake_engine,
    ):
        db_engine.dispose_database_engine()

    fake_engine.dispose.assert_called_once()
