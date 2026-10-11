import os

import pytest
from sqlalchemy import create_engine, text


@pytest.mark.integration
def test_postgres_connection() -> None:
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        pytest.skip("DATABASE_URL is not configured for integration tests")

    engine = create_engine(database_url, pool_pre_ping=True)

    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()

        assert result == 1
    finally:
        engine.dispose()
