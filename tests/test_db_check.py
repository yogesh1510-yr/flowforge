from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from flowforge.db.session import get_db_session
from flowforge.main import app

client = TestClient(app)


def test_db_check_returns_ok_when_query_succeeds() -> None:
    session = MagicMock()
    session.execute.return_value = None

    def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        response = client.get("/db-check")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "connected",
    }
    session.execute.assert_called_once()


def test_db_check_returns_503_when_query_fails() -> None:
    session = MagicMock()
    session.execute.side_effect = Exception("Database query failed")

    def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    try:
        response = client.get("/db-check")
    finally:
        app.dependency_overrides.pop(get_db_session, None)

    assert response.status_code == 503
    assert response.json() == {"detail": "Database query failed"}
    session.execute.assert_called_once()
