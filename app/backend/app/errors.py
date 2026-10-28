"""Structured API errors.

Every failure leaves the API as the same envelope so the client never has to
sniff prose:

.. code-block:: json

    {
      "error": {"code": "insufficient_stock", "message": "...", "details": {...}},
      "request_id": "req_1f0c..."
    }
"""

from __future__ import annotations

from typing import Any


class ApiError(Exception):
    """An error with an HTTP status, a stable machine code and optional details."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}


def error_payload(
    code: str,
    message: str,
    details: dict[str, Any] | None,
    request_id: str,
) -> dict[str, Any]:
    """Build the response envelope shared by every error handler."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "request_id": request_id,
    }


# Stable error codes. Documented in ``app/README.md`` and the OpenAPI schema.
ERROR_CODES: dict[str, str] = {
    "product_not_found": "The requested product does not exist.",
    "sku_not_found": "The requested SKU does not exist or is no longer sold.",
    "cart_not_found": "The requested cart does not exist.",
    "insufficient_stock": "The requested quantity is not available right now.",
    "idempotency_key_missing": "The Idempotency-Key header is required for this endpoint.",
    "idempotency_key_invalid": "The Idempotency-Key header is malformed.",
    "idempotency_key_conflict": "The Idempotency-Key was already used for a different request.",
    "request_validation_error": "The request body or query parameters are invalid.",
    "not_found": "The requested endpoint does not exist.",
    "method_not_allowed": "The HTTP method is not allowed for this endpoint.",
    "http_error": "The request could not be completed.",
    "internal_error": "The server could not complete the request.",
}
