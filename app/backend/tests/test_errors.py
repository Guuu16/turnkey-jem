"""Unexpected failures still leave the API with a structured, safe response."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from app import services


def test_unexpected_error_is_structured_and_leaks_nothing(
    client: TestClient, monkeypatch: object
) -> None:
    def explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(services, "fetch_cart", explode)

    with TestClient(client.app, raise_server_exceptions=False) as failing_client:
        response = failing_client.get("/api/cart")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"]
    assert body["request_id"] == response.headers["X-Request-Id"]
    assert "secret internal detail" not in json.dumps(body)


def test_wrong_method_returns_structured_error(client: TestClient) -> None:
    response = client.delete("/api/cart")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"
