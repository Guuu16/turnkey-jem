"""Runtime configuration for the Variant PDP API."""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "shop.db"

#: The demo storefront has a single server-side cart. Multi-user carts would add
#: a session or customer identifier; the cart semantics stay the same.
DEMO_CART_ID = "cart_demo"

#: At or below this many units a SKU is presented as "low stock" in the UI.
LOW_STOCK_THRESHOLD = 2

IDEMPOTENCY_KEY_MAX_LENGTH = 128

DEFAULT_CORS_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def db_path() -> Path:
    """Resolve the SQLite file path, allowing tests to point at a temp directory."""
    configured = os.environ.get("APP_DB_PATH")
    return Path(configured) if configured else DEFAULT_DB_PATH


def cors_origins() -> list[str]:
    raw = os.environ.get("APP_CORS_ORIGINS")
    if not raw:
        return list(DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
