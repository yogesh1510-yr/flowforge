from unittest.mock import patch

from fastapi.testclient import TestClient

from flowforge.main import app

client = TestClient(app)


def test_readiness_returns_ready_when_database_is_connected() -> None:
    with patch("flowforge.main.check_database_connection", return_value=True):
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "connected",
    }


def test_readiness_returns_503_when_database_is_unavailable() -> None:
    with patch("flowforge.main.check_database_connection", return_value=False):
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable"}
