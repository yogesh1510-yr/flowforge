import pytest

from flowforge.core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_settings_load_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    database_url = "postgresql+psycopg://user:pass@localhost:5434/flowforge"
    monkeypatch.setenv("DATABASE_URL", database_url)

    settings = get_settings()

    assert settings.database_url == database_url


def test_settings_fail_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        get_settings()


def test_settings_rejects_empty_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "   ")

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        get_settings()


def test_settings_rejects_non_postgres_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite:///test.db")

    with pytest.raises(RuntimeError, match="PostgreSQL"):
        get_settings()


def test_settings_rejects_malformed_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "://invalid-url")

    with pytest.raises(RuntimeError, match="malformed"):
        get_settings()


def test_settings_requires_host_and_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://localhost")

    with pytest.raises(RuntimeError, match="host and database name"):
        get_settings()
