"""Register or update the local PostgreSQL Debezium connector."""

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONNECT_URL = os.getenv("CONNECT_URL", "http://connect:8083")
CONNECTOR_NAME = os.getenv("CONNECTOR_NAME", "flowforge-orders")

config = {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": os.getenv("POSTGRES_HOST", "postgres"),
    "database.port": os.getenv("POSTGRES_PORT", "5432"),
    "database.user": os.getenv("POSTGRES_USER", "flowforge"),
    "database.password": os.getenv("POSTGRES_PASSWORD", "flowforge_dev_only"),
    "database.dbname": os.getenv("POSTGRES_DB", "flowforge"),
    "topic.prefix": "flowforge",
    "plugin.name": "pgoutput",
    "slot.name": "flowforge_orders",
    "publication.name": "flowforge_orders",
    "publication.autocreate.mode": "filtered",
    "schema.include.list": "public",
    "table.include.list": "public.orders",
    "snapshot.mode": "initial", 
    "decimal.handling.mode": "precise",
    "tombstones.on.delete": "false",
}


def request(method: str, path: str, payload: dict | None = None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = Request(
        f"{CONNECT_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urlopen(req, timeout=10) as response:
        return response.status, response.read()


def main() -> None:
    for attempt in range(60):
        try:
            request("GET", "/connectors")
            break
        except HTTPError as error:
            if error.code < 500 or attempt == 59:
                raise
            time.sleep(5)
        except (URLError, TimeoutError):
            if attempt == 59:
                raise
            time.sleep(5)

    path = f"/connectors/{CONNECTOR_NAME}/config"
    try:
        request("PUT", path, config)
        print(f"Updated Debezium connector {CONNECTOR_NAME}")
    except HTTPError as error:
        if error.code != 404:
            raise
        request("POST", "/connectors", {"name": CONNECTOR_NAME, "config": config})
        print(f"Registered Debezium connector {CONNECTOR_NAME}")


if __name__ == "__main__":
    main()
