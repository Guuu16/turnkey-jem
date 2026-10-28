"""SQLite access helpers.

The API is deliberately built on the standard-library ``sqlite3`` driver so the
transaction boundaries that protect stock are explicit and reviewable:

* one connection per request,
* WAL journal so readers never block the single writer,
* ``BEGIN IMMEDIATE`` for every write transaction so two writers cannot both
  read a stock level before either of them updates it,
* a bounded ``busy_timeout`` so a contended writer waits instead of failing.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    currency    TEXT NOT NULL,
    image_url   TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS option_dimensions (
    id          TEXT PRIMARY KEY,
    product_id  TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    position    INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS option_values (
    id           TEXT PRIMARY KEY,
    dimension_id TEXT NOT NULL REFERENCES option_dimensions(id) ON DELETE CASCADE,
    label        TEXT NOT NULL,
    swatch       TEXT,
    position     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS skus (
    id          TEXT PRIMARY KEY,
    product_id  TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    code        TEXT NOT NULL UNIQUE,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0),
    stock       INTEGER NOT NULL CHECK (stock >= 0),
    image_url   TEXT NOT NULL,
    active      INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1))
);

CREATE TABLE IF NOT EXISTS sku_options (
    sku_id          TEXT NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    dimension_id    TEXT NOT NULL REFERENCES option_dimensions(id),
    option_value_id TEXT NOT NULL REFERENCES option_values(id),
    PRIMARY KEY (sku_id, dimension_id)
);

CREATE TABLE IF NOT EXISTS carts (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
    cart_id          TEXT NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
    sku_id           TEXT NOT NULL REFERENCES skus(id),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    unit_price_cents INTEGER NOT NULL CHECK (unit_price_cents >= 0),
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL,
    PRIMARY KEY (cart_id, sku_id)
);

CREATE TABLE IF NOT EXISTS idempotency_keys (
    key                 TEXT PRIMARY KEY,
    request_fingerprint TEXT NOT NULL,
    response_status     INTEGER NOT NULL,
    response_body       TEXT NOT NULL,
    created_at          TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_option_values_dimension
    ON option_values (dimension_id, position);
CREATE INDEX IF NOT EXISTS idx_skus_product
    ON skus (product_id, code);
CREATE INDEX IF NOT EXISTS idx_cart_items_cart
    ON cart_items (cart_id, created_at);
"""


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp with millisecond precision."""
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection configured for concurrent, single-writer access."""
    conn = sqlite3.connect(
        str(db_path),
        timeout=5.0,
        isolation_level=None,  # autocommit; transactions are started explicitly
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    """Run a write transaction that takes the SQLite write lock up front.

    ``BEGIN IMMEDIATE`` acquires the reserved lock immediately, so the
    read-then-write sequence inside the block cannot interleave with another
    writer. Combined with the conditional stock ``UPDATE`` this is what makes
    the last-unit race safe.
    """
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def init_db(db_path: str | Path, *, seed: bool = True) -> None:
    """Create the schema and, on an empty database, load the demo catalogue."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        conn.executescript(SCHEMA)
        if seed:
            from .seed import seed_database

            with transaction(conn):
                seed_database(conn)
    finally:
        conn.close()
