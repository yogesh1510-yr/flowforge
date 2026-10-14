"""Database engine and connectivity helpers."""

from functools import lru_cache

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from flowforge.core.config import get_settings


@lru_cache(maxsize=1)
def get_database_engine() -> Engine:
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
    )


def check_database_connection() -> bool:
    try:
        with get_database_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
