"""Catalogue and cart services.

All business rules live here, behind the HTTP layer, so the tests can exercise
them either through the API or directly against a transaction.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from . import config
from .db import transaction, utc_now
from .errors import ApiError


def stock_status(stock: int) -> str:
    if stock <= 0:
        return "out_of_stock"
    if stock <= config.LOW_STOCK_THRESHOLD:
        return "low_stock"
    return "in_stock"


# ---------------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------------


def _product_row(conn: sqlite3.Connection, product_id: str) -> sqlite3.Row:
    row = conn.execute(
        "SELECT id, name, description, currency, image_url FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    if row is None:
        raise ApiError(
            404,
            "product_not_found",
            f"Product '{product_id}' does not exist.",
            {"product_id": product_id},
        )
    return row


def _dimensions_with_values(conn: sqlite3.Connection, product_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT d.id AS dimension_id, d.name AS dimension_name,
               v.id AS value_id, v.label, v.swatch
        FROM option_dimensions d
        JOIN option_values v ON v.dimension_id = d.id
        WHERE d.product_id = ?
        ORDER BY d.position, v.position
        """,
        (product_id,),
    ).fetchall()

    dimensions: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        dimension = index.get(row["dimension_id"])
        if dimension is None:
            dimension = {"id": row["dimension_id"], "name": row["dimension_name"], "values": []}
            index[row["dimension_id"]] = dimension
            dimensions.append(dimension)
        dimension["values"].append(
            {"id": row["value_id"], "label": row["label"], "swatch": row["swatch"]}
        )
    return dimensions


def _sku_option_map(conn: sqlite3.Connection, sku_ids: list[str]) -> dict[str, dict[str, str]]:
    """Return ``{sku_id: {dimension_id: option_value_id}}`` for the given SKUs."""
    if not sku_ids:
        return {}
    placeholders = ",".join("?" for _ in sku_ids)
    rows = conn.execute(
        f"""
        SELECT sku_id, dimension_id, option_value_id
        FROM sku_options
        WHERE sku_id IN ({placeholders})
        ORDER BY dimension_id
        """,
        sku_ids,
    ).fetchall()
    options: dict[str, dict[str, str]] = {sku_id: {} for sku_id in sku_ids}
    for row in rows:
        options[row["sku_id"]][row["dimension_id"]] = row["option_value_id"]
    return options


def _sku_option_labels(conn: sqlite3.Connection, sku_ids: list[str]) -> dict[str, dict[str, str]]:
    """Return ``{sku_id: {dimension_name: label}}`` for cart line rendering."""
    if not sku_ids:
        return {}
    placeholders = ",".join("?" for _ in sku_ids)
    rows = conn.execute(
        f"""
        SELECT so.sku_id, d.name AS dimension_name, v.label
        FROM sku_options so
        JOIN option_dimensions d ON d.id = so.dimension_id
        JOIN option_values v ON v.id = so.option_value_id
        WHERE so.sku_id IN ({placeholders})
        ORDER BY d.position
        """,
        sku_ids,
    ).fetchall()
    labels: dict[str, dict[str, str]] = {sku_id: {} for sku_id in sku_ids}
    for row in rows:
        labels[row["sku_id"]][row["dimension_name"]] = row["label"]
    return labels


def fetch_product_detail(conn: sqlite3.Connection, product_id: str) -> dict[str, Any]:
    product = _product_row(conn, product_id)
    sku_rows = conn.execute(
        """
        SELECT id, code, price_cents, stock, image_url
        FROM skus
        WHERE product_id = ? AND active = 1
        ORDER BY code
        """,
        (product_id,),
    ).fetchall()

    option_map = _sku_option_map(conn, [row["id"] for row in sku_rows])

    skus = [
        {
            "id": row["id"],
            "code": row["code"],
            "price_cents": row["price_cents"],
            "stock": row["stock"],
            "stock_status": stock_status(row["stock"]),
            "purchasable": row["stock"] > 0,
            "image_url": row["image_url"],
            "options": option_map.get(row["id"], {}),
        }
        for row in sku_rows
    ]
    prices = [sku["price_cents"] for sku in skus] or [0]

    return {
        "product": {
            "id": product["id"],
            "name": product["name"],
            "description": product["description"],
            "currency": product["currency"],
            "image_url": product["image_url"],
            "price_min_cents": min(prices),
            "price_max_cents": max(prices),
        },
        "options": _dimensions_with_values(conn, product_id),
        "skus": skus,
    }


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------


def build_cart(conn: sqlite3.Connection, cart_id: str) -> dict[str, Any]:
    cart_row = conn.execute(
        "SELECT id FROM carts WHERE id = ?",
        (cart_id,),
    ).fetchone()
    if cart_row is None:
        raise ApiError(
            404, "cart_not_found", f"Cart '{cart_id}' does not exist.", {"cart_id": cart_id}
        )

    rows = conn.execute(
        """
        SELECT ci.sku_id, ci.quantity, ci.unit_price_cents,
               s.code, s.price_cents, s.stock, s.image_url
        FROM cart_items ci
        JOIN skus s ON s.id = ci.sku_id
        WHERE ci.cart_id = ?
        ORDER BY ci.created_at, ci.sku_id
        """,
        (cart_id,),
    ).fetchall()

    sku_ids = [row["sku_id"] for row in rows]
    option_ids = _sku_option_map(conn, sku_ids)
    option_labels = _sku_option_labels(conn, sku_ids)

    items: list[dict[str, Any]] = []
    subtotal = 0
    total_quantity = 0
    for row in rows:
        line_total = row["quantity"] * row["unit_price_cents"]
        subtotal += line_total
        total_quantity += row["quantity"]
        items.append(
            {
                "sku_id": row["sku_id"],
                "quantity": row["quantity"],
                "unit_price_cents": row["unit_price_cents"],
                "line_total_cents": line_total,
                "sku": {
                    "id": row["sku_id"],
                    "code": row["code"],
                    "price_cents": row["price_cents"],
                    "stock": row["stock"],
                    "stock_status": stock_status(row["stock"]),
                    "image_url": row["image_url"],
                    "options": option_ids.get(row["sku_id"], {}),
                    "option_labels": option_labels.get(row["sku_id"], {}),
                },
            }
        )

    return {
        "id": cart_id,
        "currency": _currency(conn, cart_id),
        "items": items,
        "item_count": len(items),
        "total_quantity": total_quantity,
        "subtotal_cents": subtotal,
    }


def _currency(conn: sqlite3.Connection, cart_id: str) -> str:
    row = conn.execute(
        """
        SELECT p.currency
        FROM cart_items ci
        JOIN skus s ON s.id = ci.sku_id
        JOIN products p ON p.id = s.product_id
        WHERE ci.cart_id = ?
        LIMIT 1
        """,
        (cart_id,),
    ).fetchone()
    if row is not None:
        return row["currency"]
    row = conn.execute("SELECT currency FROM products LIMIT 1").fetchone()
    return row["currency"] if row is not None else "USD"


def fetch_cart(conn: sqlite3.Connection, cart_id: str) -> dict[str, Any]:
    return build_cart(conn, cart_id)


def _fingerprint(cart_id: str, sku_id: str, quantity: int) -> str:
    canonical = json.dumps(
        {
            "operation": "add_cart_item",
            "cart_id": cart_id,
            "sku_id": sku_id,
            "quantity": quantity,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def add_cart_item(
    conn: sqlite3.Connection,
    *,
    cart_id: str,
    sku_id: str,
    quantity: int,
    idempotency_key: str,
) -> tuple[dict[str, Any], int, bool]:
    """Add a SKU to the cart exactly once per idempotency key.

    Returns ``(payload, status_code, replayed)``. The whole operation — the
    idempotency claim, the stock decrement and the cart-line upsert — runs in
    one ``BEGIN IMMEDIATE`` transaction, so either all of it is visible or none
    of it is.

    Stock is reserved when the item enters the cart: the decrement is a single
    conditional ``UPDATE ... WHERE stock >= :quantity``. Two concurrent requests
    for the last unit therefore cannot both succeed; the second one sees
    ``rowcount == 0`` and is rejected with ``insufficient_stock``.
    """
    fingerprint = _fingerprint(cart_id, sku_id, quantity)

    with transaction(conn):
        claim = conn.execute(
            """
            SELECT request_fingerprint, response_status, response_body
            FROM idempotency_keys
            WHERE key = ?
            """,
            (idempotency_key,),
        ).fetchone()

        if claim is not None:
            if claim["request_fingerprint"] != fingerprint:
                raise ApiError(
                    409,
                    "idempotency_key_conflict",
                    "This Idempotency-Key was already used for a different request.",
                    {"idempotency_key": idempotency_key},
                )
            payload = json.loads(claim["response_body"])
            payload["replayed"] = True
            return payload, int(claim["response_status"]), True

        sku = conn.execute(
            "SELECT id, price_cents, stock, active FROM skus WHERE id = ?",
            (sku_id,),
        ).fetchone()
        if sku is None or not sku["active"]:
            raise ApiError(
                404,
                "sku_not_found",
                f"SKU '{sku_id}' does not exist or is no longer sold.",
                {"sku_id": sku_id},
            )

        reserved = conn.execute(
            """
            UPDATE skus
            SET stock = stock - :quantity
            WHERE id = :sku_id AND active = 1 AND stock >= :quantity
            """,
            {"quantity": quantity, "sku_id": sku_id},
        ).rowcount
        if reserved == 0:
            raise ApiError(
                409,
                "insufficient_stock",
                "There is not enough stock left for this SKU.",
                {
                    "sku_id": sku_id,
                    "requested": quantity,
                    "available": int(sku["stock"]),
                },
            )

        now = utc_now()
        conn.execute(
            """
            INSERT INTO cart_items (
                cart_id, sku_id, quantity, unit_price_cents, created_at, updated_at
            )
            VALUES (:cart_id, :sku_id, :quantity, :unit_price_cents, :now, :now)
            ON CONFLICT (cart_id, sku_id) DO UPDATE SET
                quantity = cart_items.quantity + excluded.quantity,
                updated_at = excluded.updated_at
            """,
            {
                "cart_id": cart_id,
                "sku_id": sku_id,
                "quantity": quantity,
                "unit_price_cents": sku["price_cents"],
                "now": now,
            },
        )

        cart = build_cart(conn, cart_id)
        item = next(line for line in cart["items"] if line["sku_id"] == sku_id)
        payload = {"cart": cart, "item": item, "replayed": False}

        conn.execute(
            """
            INSERT INTO idempotency_keys (
                key, request_fingerprint, response_status, response_body, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                idempotency_key,
                fingerprint,
                201,
                json.dumps(payload, separators=(",", ":")),
                now,
            ),
        )

    return payload, 201, False
