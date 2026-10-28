"""Demo catalogue.

One product, two option dimensions, seven SKUs. The catalogue intentionally
contains:

* an out-of-stock SKU (Ink / S),
* an unavailable combination that has no SKU at all (Olive / S and Ink / L),
* a single-unit SKU (Sand / L) used to demonstrate the last-unit race.

Seeding is idempotent: it fills an empty catalogue and does nothing otherwise.
"""

from __future__ import annotations

import sqlite3

from . import config
from .db import utc_now

PRODUCT = {
    "id": "prod_aurora_field_jacket",
    "name": "Aurora Field Jacket",
    "description": (
        "A weatherproof shell for shoulder-season days. Fully seam-sealed, "
        "with a two-way zip, a packable hood and four utility pockets."
    ),
    "currency": "USD",
    "image_url": "/images/aurora-field-jacket.svg",
}

DIMENSIONS = [
    {
        "id": "colour",
        "name": "Colour",
        "values": [
            {"id": "colour_sand", "label": "Sand", "swatch": "#c9b79a"},
            {"id": "colour_olive", "label": "Olive", "swatch": "#6b7a54"},
            {"id": "colour_ink", "label": "Ink", "swatch": "#2b2f3a"},
        ],
    },
    {
        "id": "size",
        "name": "Size",
        "values": [
            {"id": "size_s", "label": "S", "swatch": None},
            {"id": "size_m", "label": "M", "swatch": None},
            {"id": "size_l", "label": "L", "swatch": None},
        ],
    },
]

#: price is in minor currency units (cents); stock is units available to sell.
SKUS = [
    {
        "id": "sku_aurora_sand_s",
        "code": "AUR-SAND-S",
        "price_cents": 12900,
        "stock": 4,
        "image_url": "/images/aurora-sand.svg",
        "options": {"colour": "colour_sand", "size": "size_s"},
    },
    {
        "id": "sku_aurora_sand_m",
        "code": "AUR-SAND-M",
        "price_cents": 12900,
        "stock": 6,
        "image_url": "/images/aurora-sand.svg",
        "options": {"colour": "colour_sand", "size": "size_m"},
    },
    {
        "id": "sku_aurora_sand_l",
        "code": "AUR-SAND-L",
        "price_cents": 12900,
        "stock": 1,
        "image_url": "/images/aurora-sand.svg",
        "options": {"colour": "colour_sand", "size": "size_l"},
    },
    {
        "id": "sku_aurora_olive_m",
        "code": "AUR-OLIVE-M",
        "price_cents": 13400,
        "stock": 3,
        "image_url": "/images/aurora-olive.svg",
        "options": {"colour": "colour_olive", "size": "size_m"},
    },
    {
        "id": "sku_aurora_olive_l",
        "code": "AUR-OLIVE-L",
        "price_cents": 13400,
        "stock": 2,
        "image_url": "/images/aurora-olive.svg",
        "options": {"colour": "colour_olive", "size": "size_l"},
    },
    {
        "id": "sku_aurora_ink_s",
        "code": "AUR-INK-S",
        "price_cents": 13900,
        "stock": 0,
        "image_url": "/images/aurora-ink.svg",
        "options": {"colour": "colour_ink", "size": "size_s"},
    },
    {
        "id": "sku_aurora_ink_m",
        "code": "AUR-INK-M",
        "price_cents": 13900,
        "stock": 5,
        "image_url": "/images/aurora-ink.svg",
        "options": {"colour": "colour_ink", "size": "size_m"},
    },
]


def seed_database(conn: sqlite3.Connection) -> bool:
    """Insert the demo catalogue into an empty database. Returns True if it wrote."""
    existing = conn.execute("SELECT 1 FROM products LIMIT 1").fetchone()
    conn.execute(
        "INSERT OR IGNORE INTO carts (id, created_at) VALUES (?, ?)",
        (config.DEMO_CART_ID, utc_now()),
    )
    if existing is not None:
        return False

    now = utc_now()
    conn.execute(
        """
        INSERT INTO products (id, name, description, currency, image_url, created_at)
        VALUES (:id, :name, :description, :currency, :image_url, :created_at)
        """,
        {**PRODUCT, "created_at": now},
    )

    for dimension_position, dimension in enumerate(DIMENSIONS, start=1):
        conn.execute(
            """
            INSERT INTO option_dimensions (id, product_id, name, position)
            VALUES (?, ?, ?, ?)
            """,
            (dimension["id"], PRODUCT["id"], dimension["name"], dimension_position),
        )
        for value_position, value in enumerate(dimension["values"], start=1):
            conn.execute(
                """
                INSERT INTO option_values (id, dimension_id, label, swatch, position)
                VALUES (?, ?, ?, ?, ?)
                """,
                (value["id"], dimension["id"], value["label"], value["swatch"], value_position),
            )

    for sku in SKUS:
        conn.execute(
            """
            INSERT INTO skus (id, product_id, code, price_cents, stock, image_url, active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
            """,
            (
                sku["id"],
                PRODUCT["id"],
                sku["code"],
                sku["price_cents"],
                sku["stock"],
                sku["image_url"],
            ),
        )
        for dimension_id, option_value_id in sku["options"].items():
            conn.execute(
                """
                INSERT INTO sku_options (sku_id, dimension_id, option_value_id)
                VALUES (?, ?, ?)
                """,
                (sku["id"], dimension_id, option_value_id),
            )

    return True
