"""Variant product detail page API."""

from __future__ import annotations

import logging
import secrets
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from sqlite3 import Connection
from typing import Any

from fastapi import Depends, FastAPI, Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import config, db, services
from .errors import ERROR_CODES, ApiError, error_payload
from .schemas import AddCartItemOut, AddCartItemRequest, CartOut, ProductDetailOut

logger = logging.getLogger("variant_pdp.api")

IDEMPOTENCY_HEADER = "Idempotency-Key"


def _request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if not request_id:
        request_id = f"req_{secrets.token_hex(8)}"
        request.state.request_id = request_id
    return request_id


def _validate_idempotency_key(raw: str | None) -> str:
    if raw is None or not raw.strip():
        raise ApiError(
            400,
            "idempotency_key_missing",
            f"The {IDEMPOTENCY_HEADER} header is required for this endpoint.",
            {"header": IDEMPOTENCY_HEADER},
        )
    key = raw.strip()
    if len(key) > config.IDEMPOTENCY_KEY_MAX_LENGTH:
        raise ApiError(
            400,
            "idempotency_key_invalid",
            f"The {IDEMPOTENCY_HEADER} header must be at most "
            f"{config.IDEMPOTENCY_KEY_MAX_LENGTH} characters.",
            {"header": IDEMPOTENCY_HEADER, "max_length": config.IDEMPOTENCY_KEY_MAX_LENGTH},
        )
    if not all(33 <= ord(character) <= 126 for character in key):
        raise ApiError(
            400,
            "idempotency_key_invalid",
            f"The {IDEMPOTENCY_HEADER} header must contain printable ASCII characters only.",
            {"header": IDEMPOTENCY_HEADER},
        )
    return key


def create_app(db_path: str | Path | None = None) -> FastAPI:
    """Build the ASGI app. Tests pass their own database path."""
    resolved_db_path = Path(db_path) if db_path is not None else config.db_path()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        db.init_db(resolved_db_path)
        yield

    application = FastAPI(
        title="Variant PDP API",
        version="1.0.0",
        summary="Server-authoritative product, stock and cart API for the variant PDP.",
        description=(
            "Prices and stock are always resolved on the server. "
            "`POST /api/cart/items` requires an `Idempotency-Key` header. "
            "Full request/response examples live in `app/README.md`."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    application.state.db_path = resolved_db_path
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins(),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", IDEMPOTENCY_HEADER, "X-Request-Id"],
        expose_headers=["X-Request-Id", "Idempotent-Replay"],
        max_age=600,
    )

    def get_connection(request: Request) -> Iterator[Connection]:
        connection = db.connect(request.app.state.db_path)
        try:
            yield connection
        finally:
            connection.close()

    @application.middleware("http")
    async def attach_request_id(request: Request, call_next: Any) -> Any:
        request_id = request.headers.get("X-Request-Id") or f"req_{secrets.token_hex(8)}"
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response

    def error_response(
        request: Request,
        status_code: int,
        payload: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> JSONResponse:
        """Build an error response that always carries the correlation header.

        The header is set here as well as in the middleware because an unhandled
        exception is answered by Starlette's outermost error middleware, which
        never returns through the request-id middleware.
        """
        response_headers = {"X-Request-Id": _request_id(request)}
        if headers:
            response_headers.update(headers)
        return JSONResponse(status_code=status_code, content=payload, headers=response_headers)

    @application.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return error_response(
            request,
            exc.status_code,
            error_payload(exc.code, exc.message, exc.details, _request_id(request)),
        )

    @application.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {
            "errors": [
                {
                    "location": [str(part) for part in error.get("loc", ())],
                    "message": error.get("msg", "Invalid value."),
                    "type": error.get("type", "value_error"),
                }
                for error in exc.errors()
            ]
        }
        return error_response(
            request,
            422,
            error_payload(
                "request_validation_error",
                ERROR_CODES["request_validation_error"],
                details,
                _request_id(request),
            ),
        )

    @application.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
        message = ERROR_CODES.get(code, str(exc.detail))
        return error_response(
            request,
            exc.status_code,
            error_payload(code, message, {}, _request_id(request)),
            headers=exc.headers or None,
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        request_id = _request_id(request)
        logger.exception("Unhandled error for request %s", request_id, exc_info=exc)
        return error_response(
            request,
            500,
            error_payload("internal_error", ERROR_CODES["internal_error"], {}, request_id),
        )

    @application.get("/api/health", tags=["system"], summary="Liveness probe")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get(
        "/api/products/{product_id}",
        response_model=ProductDetailOut,
        tags=["catalogue"],
        summary="Product, option dimensions and SKUs",
        responses={404: {"description": "Unknown product (`product_not_found`)."}},
    )
    def get_product(
        product_id: str,
        connection: Connection = Depends(get_connection),
    ) -> dict[str, Any]:
        return services.fetch_product_detail(connection, product_id)

    @application.get(
        "/api/cart",
        response_model=CartOut,
        tags=["cart"],
        summary="Current cart, item count and subtotal",
    )
    def get_cart(connection: Connection = Depends(get_connection)) -> dict[str, Any]:
        return services.fetch_cart(connection, config.DEMO_CART_ID)

    @application.post(
        "/api/cart/items",
        response_model=AddCartItemOut,
        status_code=201,
        tags=["cart"],
        summary="Add a SKU to the cart (idempotent)",
        responses={
            201: {"description": "Line added or increased; stock reserved."},
            400: {"description": "Missing or malformed Idempotency-Key."},
            404: {"description": "Unknown SKU (`sku_not_found`)."},
            409: {
                "description": (
                    "Not enough stock (`insufficient_stock`) or the key was reused with "
                    "a different request (`idempotency_key_conflict`)."
                )
            },
            422: {"description": "Invalid body (`request_validation_error`)."},
        },
    )
    def add_cart_item(
        payload: AddCartItemRequest,
        connection: Connection = Depends(get_connection),
        idempotency_key: str | None = Header(default=None, alias=IDEMPOTENCY_HEADER),
    ) -> JSONResponse:
        key = _validate_idempotency_key(idempotency_key)
        body, status_code, replayed = services.add_cart_item(
            connection,
            cart_id=config.DEMO_CART_ID,
            sku_id=payload.sku_id,
            quantity=payload.quantity,
            idempotency_key=key,
        )
        return JSONResponse(
            status_code=status_code,
            content=body,
            headers={"Idempotent-Replay": "true" if replayed else "false"},
        )

    return application


app = create_app()
