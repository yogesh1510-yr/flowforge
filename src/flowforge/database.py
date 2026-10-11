import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


def create_database_engine() -> Engine:
    return create_engine(
        get_database_url(),
        pool_pre_ping=True,
    )


def check_database_connection() -> bool:
    engine = create_database_engine()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        engine.dispose()
