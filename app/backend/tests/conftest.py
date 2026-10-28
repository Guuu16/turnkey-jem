"""Shared pytest fixtures.

Each test gets its own SQLite file under ``tmp_path`` so the suite never touches
the development database and tests can run in any order.
"""

from __future__ import annotations

import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import connect  # noqa: E402
from app.main import create_app  # noqa: E402
from app.seed import PRODUCT, SKUS  # noqa: E402

PRODUCT_ID = PRODUCT["id"]
CART_URL = "/api/cart"
CART_ITEMS_URL = "/api/cart/items"
PRODUCT_URL = f"/api/products/{PRODUCT_ID}"

SKU_BY_KEY = {sku["code"]: sku["id"] for sku in SKUS}
SKU_SAND_S = SKU_BY_KEY["AUR-SAND-S"]  # stock 4
SKU_SAND_M = SKU_BY_KEY["AUR-SAND-M"]  # stock 6
SKU_SAND_L = SKU_BY_KEY["AUR-SAND-L"]  # stock 1, used for the last-unit race
SKU_OLIVE_M = SKU_BY_KEY["AUR-OLIVE-M"]  # stock 3
SKU_INK_S = SKU_BY_KEY["AUR-INK-S"]  # stock 0, out of stock


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "shop-test.db"


@pytest.fixture()
def client(db_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(db_path=db_path)) as test_client:
        yield test_client


@pytest.fixture()
def connection(db_path: Path, client: TestClient) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


def add_item(
    client: TestClient,
    *,
    sku_id: str,
    quantity: int = 1,
    idempotency_key: str,
) -> httpx.Response:
    return client.post(
        CART_ITEMS_URL,
        json={"sku_id": sku_id, "quantity": quantity},
        headers={"Idempotency-Key": idempotency_key},
    )


def stock_of(connection: sqlite3.Connection, sku_id: str) -> int:
    row = connection.execute("SELECT stock FROM skus WHERE id = ?", (sku_id,)).fetchone()
    assert row is not None
    return int(row["stock"])


def cart_quantity(connection: sqlite3.Connection, sku_id: str) -> int:
    row = connection.execute(
        "SELECT quantity FROM cart_items WHERE cart_id = 'cart_demo' AND sku_id = ?",
        (sku_id,),
    ).fetchone()
    return int(row["quantity"]) if row is not None else 0
