"""Catalogue contract: product, option dimensions and SKU availability."""

from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import PRODUCT_ID, PRODUCT_URL


def test_returns_product_with_two_option_dimensions(client: TestClient) -> None:
    response = client.get(PRODUCT_URL)

    assert response.status_code == 200
    body = response.json()

    assert body["product"]["id"] == PRODUCT_ID
    assert body["product"]["currency"] == "USD"
    assert body["product"]["price_min_cents"] == 12900
    assert body["product"]["price_max_cents"] == 13900

    dimensions = {dimension["id"]: dimension for dimension in body["options"]}
    assert set(dimensions) == {"colour", "size"}
    assert [value["label"] for value in dimensions["colour"]["values"]] == [
        "Sand",
        "Olive",
        "Ink",
    ]
    assert [value["label"] for value in dimensions["size"]["values"]] == ["S", "M", "L"]


def test_catalogue_has_seven_skus_with_one_out_of_stock(client: TestClient) -> None:
    body = client.get(PRODUCT_URL).json()
    skus = body["skus"]

    assert len(skus) == 7
    out_of_stock = [sku for sku in skus if sku["stock"] == 0]
    assert len(out_of_stock) == 1
    assert out_of_stock[0]["id"] == "sku_aurora_ink_s"
    assert out_of_stock[0]["stock_status"] == "out_of_stock"
    assert out_of_stock[0]["purchasable"] is False


def test_single_unit_sku_is_marked_low_stock(client: TestClient) -> None:
    body = client.get(PRODUCT_URL).json()
    skus = {sku["id"]: sku for sku in body["skus"]}

    assert skus["sku_aurora_sand_l"]["stock"] == 1
    assert skus["sku_aurora_sand_l"]["stock_status"] == "low_stock"
    assert skus["sku_aurora_sand_l"]["purchasable"] is True


def test_unavailable_combinations_have_no_sku(client: TestClient) -> None:
    """Olive/S and Ink/L are combinations without a SKU, so the UI can disable them."""
    body = client.get(PRODUCT_URL).json()
    combinations = {(sku["options"]["colour"], sku["options"]["size"]) for sku in body["skus"]}

    assert ("colour_olive", "size_s") not in combinations
    assert ("colour_ink", "size_l") not in combinations
    assert len(combinations) == 7


def test_sku_carries_its_own_price_image_and_options(client: TestClient) -> None:
    body = client.get(PRODUCT_URL).json()
    skus = {sku["id"]: sku for sku in body["skus"]}

    ink_m = skus["sku_aurora_ink_m"]
    assert ink_m["price_cents"] == 13900
    assert ink_m["image_url"].endswith("aurora-ink.svg")
    assert ink_m["options"] == {"colour": "colour_ink", "size": "size_m"}


def test_unknown_product_returns_structured_error(client: TestClient) -> None:
    response = client.get("/api/products/does-not-exist")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "product_not_found"
    assert body["error"]["message"]
    assert body["error"]["details"] == {"product_id": "does-not-exist"}
    assert body["request_id"] == response.headers["X-Request-Id"]


def test_unknown_route_returns_structured_error(client: TestClient) -> None:
    response = client.get("/api/nope")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
