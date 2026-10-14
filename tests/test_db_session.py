
import pytest

from flowforge.db import session as db_session


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_get_db_session_closes_session_after_use(monkeypatch):
    fake = FakeSession()

    monkeypatch.setattr(
        db_session,
        "get_session_factory",
        lambda: lambda: fake,
    )

    generator = db_session.get_db_session()

    assert next(generator) is fake
    assert fake.closed is False

    with pytest.raises(StopIteration):
        next(generator)

    assert fake.closed is True


def test_get_db_session_closes_session_after_exception(monkeypatch):
    fake = FakeSession()

    monkeypatch.setattr(
        db_session,
        "get_session_factory",
        lambda: lambda: fake,
    )

    generator = db_session.get_db_session()
    assert next(generator) is fake

    with pytest.raises(RuntimeError, match="simulated failure"):
        generator.throw(RuntimeError("simulated failure"))

    assert fake.closed is True
