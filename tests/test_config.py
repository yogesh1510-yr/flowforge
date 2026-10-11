import pytest

from flowforge.config import get_settings


def test_settings_load_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://user:pass@localhost:5434/flowforge",
    )

    settings = get_settings()

    assert settings.database_url == (
        "postgresql+psycopg://user:pass@localhost:5434/flowforge"
    )
    get_settings.cache_clear()


def test_settings_fail_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    get_settings.cache_clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL is not configured"):
        get_settings()

    get_settings.cache_clear()
