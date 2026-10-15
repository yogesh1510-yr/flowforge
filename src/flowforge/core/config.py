import os
from dataclasses import dataclass
from functools import lru_cache
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


@dataclass(frozen=True)
class Settings:
    database_url: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL")

    if not database_url or not database_url.strip():
        raise RuntimeError("DATABASE_URL is not configured")

    try:
        parsed_url = make_url(database_url)
    except ArgumentError as exc:
        raise RuntimeError("DATABASE_URL is malformed") from exc

    if parsed_url.drivername not in {
        "postgresql",
        "postgresql+psycopg",
    }:
        raise RuntimeError("DATABASE_URL must use PostgreSQL with the psycopg driver")

    if not parsed_url.host or not parsed_url.database:
        raise RuntimeError(
            "DATABASE_URL must include a database host and database name"
        )

    return Settings(database_url=database_url)
