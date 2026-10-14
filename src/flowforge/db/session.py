from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session, sessionmaker

from flowforge.db.engine import get_database_engine


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return a reusable factory for database sessions."""
    return sessionmaker(
        bind=get_database_engine(),
        autoflush=False,
        expire_on_commit=False,
    )


def get_db_session() -> Generator[Session, None, None]:
    """Provide a database session and close it when finished."""
    session = get_session_factory()()

    try:
        yield session
    finally:
        session.close()
