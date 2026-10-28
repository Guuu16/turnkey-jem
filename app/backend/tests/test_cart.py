"""Cart contract: success paths, validation, stock limits and structured errors."""

from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from conftest import (
    CART_ITEMS_URL,
    CART_URL,
    PRODUCT_URL,
    SKU_INK_S,
    SKU_OLIVE_M,
    SKU_SAND_M,
    SKU_SAND_S,
    add_item,
    cart_quantity,
    stock_of,
)

PRICE_SAND_M = 12900
PRICE_OLIVE_M = 13400


def test_cart_starts_empty(client: TestClient) -> None:
    response = client.get(CART_URL)

    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["item_count"] == 0
    assert body["total_quantity"] == 0
    assert body["subtotal_cents"] == 0
    assert body["currency"] == "USD"


def test_add_item_returns_line_and_cart_totals(client: TestClient) -> None:
    response = add_item(client, sku_id=SKU_SAND_M, quantity=2, idempotency_key="key-add-1")

    assert response.status_code == 201
    assert response.headers["Idempotent-Replay"] == "false"
    body = response.json()

    assert body["replayed"] is False
    assert body["item"]["sku_id"] == SKU_SAND_M
    assert body["item"]["quantity"] == 2
    assert body["item"]["unit_price_cents"] == PRICE_SAND_M
    assert body["item"]["line_total_cents"] == 2 * PRICE_SAND_M
    assert body["item"]["sku"]["option_labels"] == {"Colour": "Sand", "Size": "M"}

    cart = body["cart"]
    assert cart["item_count"] == 1
    assert cart["total_quantity"] == 2
    assert cart["subtotal_cents"] == 2 * PRICE_SAND_M

    # The client can now read the same cart back.
    assert client.get(CART_URL).json() == cart


def test_add_item_reserves_stock(client: TestClient, connection: sqlite3.Connection) -> None:
    add_item(client, sku_id=SKU_SAND_M, quantity=2, idempotency_key="key-stock-1")

    assert stock_of(connection, SKU_SAND_M) == 4

    body = client.get(PRODUCT_URL).json()
    sku = next(sku for sku in body["skus"] if sku["id"] == SKU_SAND_M)
    assert sku["stock"] == 4


def test_second_add_increases_the_same_line(client: TestClient) -> None:
    add_item(client, sku_id=SKU_SAND_M, quantity=1, idempotency_key="key-inc-1")
    response = add_item(client, sku_id=SKU_SAND_M, quantity=2, idempotency_key="key-inc-2")

    assert response.status_code == 201
    cart = response.json()["cart"]
    assert len(cart["items"]) == 1
    assert cart["items"][0]["quantity"] == 3
    assert cart["subtotal_cents"] == 3 * PRICE_SAND_M


def test_multiple_skus_are_counted_separately(client: TestClient) -> None:
    add_item(client, sku_id=SKU_SAND_M, quantity=1, idempotency_key="key-multi-1")
    add_item(client, sku_id=SKU_OLIVE_M, quantity=2, idempotency_key="key-multi-2")

    cart = client.get(CART_URL).json()
    assert cart["item_count"] == 2
    assert cart["total_quantity"] == 3
    assert cart["subtotal_cents"] == PRICE_SAND_M + 2 * PRICE_OLIVE_M


def test_out_of_stock_sku_is_rejected(client: TestClient, connection: sqlite3.Connection) -> None:
    response = add_item(client, sku_id=SKU_INK_S, quantity=1, idempotency_key="key-oos-1")

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "insufficient_stock"
    assert body["error"]["details"] == {
        "sku_id": SKU_INK_S,
        "requested": 1,
        "available": 0,
    }
    assert client.get(CART_URL).json()["item_count"] == 0
    assert stock_of(connection, SKU_INK_S) == 0


def test_cannot_add_more_than_remaining_stock(
    client: TestClient, connection: sqlite3.Connection
) -> None:
    add_item(client, sku_id=SKU_SAND_S, quantity=4, idempotency_key="key-limit-1")

    response = add_item(client, sku_id=SKU_SAND_S, quantity=1, idempotency_key="key-limit-2")

    assert response.status_code == 409
    assert response.json()["error"]["details"]["available"] == 0
    assert cart_quantity(connection, SKU_SAND_S) == 4
    assert stock_of(connection, SKU_SAND_S) == 0


def test_quantity_must_be_a_positive_integer(client: TestClient) -> None:
    for quantity in (0, -1):
        response = add_item(
            client,
            sku_id=SKU_SAND_M,
            quantity=quantity,
            idempotency_key=f"key-invalid-qty-{quantity}",
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "request_validation_error"
        assert body["error"]["details"]["errors"]


def test_quantity_upper_bound_comes_from_stock(
    client: TestClient, connection: sqlite3.Connection
) -> None:
    connection.execute("UPDATE skus SET stock = 12 WHERE id = ?", (SKU_SAND_M,))
    connection.commit()

    response = add_item(
        client,
        sku_id=SKU_SAND_M,
        quantity=11,
        idempotency_key="key-large-qty-1",
    )

    assert response.status_code == 201
    assert response.json()["item"]["quantity"] == 11
    assert stock_of(connection, SKU_SAND_M) == 1


def test_client_cannot_supply_price_or_stock(client: TestClient) -> None:
    """Prices and stock are server-owned, so unknown fields are rejected outright."""
    response = client.post(
        CART_ITEMS_URL,
        json={
            "sku_id": SKU_SAND_M,
            "quantity": 1,
            "price_cents": 1,
            "stock": 999,
        },
        headers={"Idempotency-Key": "key-price-1"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "request_validation_error"


def test_unknown_sku_returns_structured_404(client: TestClient) -> None:
    response = add_item(client, sku_id="sku_missing", quantity=1, idempotency_key="key-404-1")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "sku_not_found"
    assert body["error"]["details"] == {"sku_id": "sku_missing"}


def test_missing_idempotency_key_is_rejected(client: TestClient) -> None:
    response = client.post(CART_ITEMS_URL, json={"sku_id": SKU_SAND_M, "quantity": 1})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "idempotency_key_missing"


def test_malformed_idempotency_key_is_rejected(client: TestClient) -> None:
    too_long = client.post(
        CART_ITEMS_URL,
        json={"sku_id": SKU_SAND_M, "quantity": 1},
        headers={"Idempotency-Key": "k" * 129},
    )
    whitespace = client.post(
        CART_ITEMS_URL,
        json={"sku_id": SKU_SAND_M, "quantity": 1},
        headers={"Idempotency-Key": "bad key"},
    )

    assert too_long.status_code == 400
    assert too_long.json()["error"]["code"] == "idempotency_key_invalid"
    assert whitespace.status_code == 400
    assert whitespace.json()["error"]["code"] == "idempotency_key_invalid"


def test_rejected_add_does_not_change_cart_or_stock(
    client: TestClient, connection: sqlite3.Connection
) -> None:
    add_item(client, sku_id=SKU_SAND_M, quantity=6, idempotency_key="key-rollback-1")
    response = add_item(client, sku_id=SKU_SAND_M, quantity=1, idempotency_key="key-rollback-2")

    assert response.status_code == 409
    assert cart_quantity(connection, SKU_SAND_M) == 6
    assert stock_of(connection, SKU_SAND_M) == 0
    assert client.get(CART_URL).json()["total_quantity"] == 6
