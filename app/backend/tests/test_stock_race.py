"""Last-unit race: concurrent buyers must never oversell a SKU.

The requests run in separate threads, each with its own ASGI client and its own
SQLite connection, against the same database file. That is the closest the test
suite gets to two production workers hitting the same row at once.
"""

from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import CART_ITEMS_URL, SKU_SAND_L, cart_quantity, stock_of


def _fire_concurrently(
    app: object,
    *,
    requests: list[tuple[str, int, str]],
) -> list[object]:
    """Send every request after a shared barrier so they contend at the same moment."""
    barrier = Barrier(len(requests))

    def send(request_spec: tuple[str, int, str]) -> object:
        sku_id, quantity, key = request_spec
        client = TestClient(app)
        barrier.wait(timeout=15)
        return client.post(
            CART_ITEMS_URL,
            json={"sku_id": sku_id, "quantity": quantity},
            headers={"Idempotency-Key": key},
        )

    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        return list(pool.map(send, requests))


def test_two_buyers_racing_for_last_unit(
    client: TestClient, db_path: Path, connection: sqlite3.Connection
) -> None:
    app = create_app(db_path=db_path)

    responses = _fire_concurrently(
        app,
        requests=[(SKU_SAND_L, 1, "race-a"), (SKU_SAND_L, 1, "race-b")],
    )

    statuses = sorted(response.status_code for response in responses)
    assert statuses == [201, 409]

    rejected = next(response for response in responses if response.status_code == 409)
    assert rejected.json()["error"]["code"] == "insufficient_stock"
    assert rejected.json()["error"]["details"]["available"] == 0

    assert stock_of(connection, SKU_SAND_L) == 0
    assert cart_quantity(connection, SKU_SAND_L) == 1


def test_many_buyers_never_drive_stock_negative(
    client: TestClient, db_path: Path, connection: sqlite3.Connection
) -> None:
    app = create_app(db_path=db_path)
    buyers = 8

    responses = _fire_concurrently(
        app,
        requests=[(SKU_SAND_L, 1, f"race-many-{index}") for index in range(buyers)],
    )

    successes = [response for response in responses if response.status_code == 201]
    rejections = [response for response in responses if response.status_code == 409]

    assert len(successes) == 1
    assert len(rejections) == buyers - 1
    assert all(
        rejection.json()["error"]["code"] == "insufficient_stock" for rejection in rejections
    )

    assert stock_of(connection, SKU_SAND_L) == 0
    assert cart_quantity(connection, SKU_SAND_L) == 1

    negative = connection.execute("SELECT COUNT(*) AS n FROM skus WHERE stock < 0").fetchone()["n"]
    assert negative == 0


def test_concurrent_duplicate_keys_add_once(
    client: TestClient, db_path: Path, connection: sqlite3.Connection
) -> None:
    """The idempotency claim and the stock reservation commit together."""
    app = create_app(db_path=db_path)

    responses = _fire_concurrently(
        app,
        requests=[(SKU_SAND_L, 1, "race-same-key") for _ in range(4)],
    )

    assert {response.status_code for response in responses} == {201}
    assert sum(response.headers["Idempotent-Replay"] == "true" for response in responses) >= 1

    carts = {response.json()["cart"]["total_quantity"] for response in responses}
    assert carts == {1}
    assert stock_of(connection, SKU_SAND_L) == 0
    assert cart_quantity(connection, SKU_SAND_L) == 1
