"""Idempotency semantics for POST /api/cart/items."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import (
    CART_URL,
    SKU_OLIVE_M,
    SKU_SAND_S,
    add_item,
    cart_quantity,
    stock_of,
)


def test_repeat_with_same_key_does_not_add_twice(
    client: TestClient, connection: sqlite3.Connection
) -> None:
    first = add_item(client, sku_id=SKU_SAND_S, quantity=1, idempotency_key="key-replay-1")
    second = add_item(client, sku_id=SKU_SAND_S, quantity=1, idempotency_key="key-replay-1")

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.headers["Idempotent-Replay"] == "true"
    assert second.json()["replayed"] is True
    assert second.json()["cart"] == first.json()["cart"]

    assert cart_quantity(connection, SKU_SAND_S) == 1
    assert stock_of(connection, SKU_SAND_S) == 3
    assert client.get(CART_URL).json()["total_quantity"] == 1


def test_same_key_with_different_body_is_a_conflict(client: TestClient) -> None:
    add_item(client, sku_id=SKU_SAND_S, quantity=1, idempotency_key="key-conflict-1")

    response = add_item(client, sku_id=SKU_OLIVE_M, quantity=1, idempotency_key="key-conflict-1")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "idempotency_key_conflict"
    assert body["error"]["details"] == {"idempotency_key": "key-conflict-1"}


def test_same_key_with_different_quantity_is_a_conflict(client: TestClient) -> None:
    add_item(client, sku_id=SKU_SAND_S, quantity=1, idempotency_key="key-conflict-2")

    response = add_item(client, sku_id=SKU_SAND_S, quantity=2, idempotency_key="key-conflict-2")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "idempotency_key_conflict"


def test_failed_request_does_not_consume_the_key(
    client: TestClient, connection: sqlite3.Connection
) -> None:
    """A rejected request rolls back, so the key can be retried once stock allows it."""
    rejected = add_item(client, sku_id=SKU_SAND_S, quantity=5, idempotency_key="key-retry-1")
    accepted = add_item(client, sku_id=SKU_SAND_S, quantity=2, idempotency_key="key-retry-1")

    assert rejected.status_code == 409
    assert accepted.status_code == 201
    assert accepted.json()["replayed"] is False
    assert cart_quantity(connection, SKU_SAND_S) == 2
    assert stock_of(connection, SKU_SAND_S) == 2


def test_replay_survives_a_restart(db_path: Path, client: TestClient) -> None:
    """The cached response lives in SQLite, so a fresh process can replay it."""
    add_item(client, sku_id=SKU_SAND_S, quantity=1, idempotency_key="key-restart-1")

    with TestClient(create_app(db_path=db_path)) as restarted:
        response = add_item(
            restarted, sku_id=SKU_SAND_S, quantity=1, idempotency_key="key-restart-1"
        )

        assert response.status_code == 201
        assert response.headers["Idempotent-Replay"] == "true"
        assert response.json()["cart"]["total_quantity"] == 1
        assert restarted.get(CART_URL).json()["total_quantity"] == 1


def test_distinct_keys_add_separate_lines(client: TestClient) -> None:
    add_item(client, sku_id=SKU_SAND_S, quantity=1, idempotency_key="key-distinct-a")
    add_item(client, sku_id=SKU_OLIVE_M, quantity=1, idempotency_key="key-distinct-b")

    body = client.get(CART_URL).json()
    assert body["item_count"] == 2
    assert body["total_quantity"] == 2
