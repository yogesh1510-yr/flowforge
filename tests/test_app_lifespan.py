from unittest.mock import patch

from fastapi.testclient import TestClient

from flowforge.main import app


def test_application_shutdown_disposes_database_engine() -> None:
    with patch("flowforge.main.dispose_database_engine") as dispose:
        with TestClient(app):
            pass

    dispose.assert_called_once()
