"""Tests for the Order API Lambda handler (LOCAL_MOCK=true, no AWS calls)."""
from __future__ import annotations

import json
import os

import pytest

os.environ["LOCAL_MOCK"] = "true"
os.environ["PRODUCTS_TABLE"] = "test-products"
os.environ["ORDERS_TABLE"] = "test-orders"
os.environ["ORDER_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/123/test-queue"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test-fn"

from src.handlers.order_api import handler  # noqa: E402


def _api_event(method: str, resource: str, body=None, claims=None) -> dict:
    event: dict = {
        "httpMethod": method,
        "resource": resource,
        "pathParameters": {},
        "queryStringParameters": {},
        "requestContext": {},
        "body": json.dumps(body) if body else None,
    }
    if claims:
        event["requestContext"]["authorizer"] = {"claims": claims}
    return event


_VALID_CLAIMS = {"sub": "user-abc", "email": "jane@example.com"}
_VALID_ORDER_BODY = {
    "customerName": "Jane Doe",
    "customerEmail": "jane@example.com",
    "customerPhone": "555-555-5555",
    "productId": "tree-001",
    "quantity": 1,
    "preferredPickupDate": "2026-12-10",
}


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_ok():
    event = _api_event("GET", "/health")
    resp = handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["status"] == "ok"
    assert body["service"] == "christmas-tree-api"


# ---------------------------------------------------------------------------
# GET /products
# ---------------------------------------------------------------------------

def test_list_products_returns_5_items():
    event = _api_event("GET", "/products")
    resp = handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert len(body["products"]) == 5


def test_list_products_no_auth_required():
    event = _api_event("GET", "/products")
    resp = handler(event, None)
    assert resp["statusCode"] == 200


# ---------------------------------------------------------------------------
# GET /products/{productId}
# ---------------------------------------------------------------------------

def test_get_product_found():
    event = _api_event("GET", "/products/{productId}")
    event["pathParameters"] = {"productId": "tree-001"}
    resp = handler(event, None)
    assert resp["statusCode"] == 200
    body = json.loads(resp["body"])
    assert body["productId"] == "tree-001"
    assert body["name"] == "Fraser Fir"


def test_get_product_not_found_returns_404():
    event = _api_event("GET", "/products/{productId}")
    event["pathParameters"] = {"productId": "tree-999"}
    resp = handler(event, None)
    assert resp["statusCode"] == 404


# ---------------------------------------------------------------------------
# POST /orders
# ---------------------------------------------------------------------------

def test_create_order_unauthenticated_returns_401():
    event = _api_event("POST", "/orders", body=_VALID_ORDER_BODY)
    resp = handler(event, None)
    assert resp["statusCode"] == 401


def test_create_order_invalid_body_returns_400():
    event = _api_event("POST", "/orders", body={"customerName": "Jane"}, claims=_VALID_CLAIMS)
    resp = handler(event, None)
    assert resp["statusCode"] == 400


def test_create_order_unknown_product_returns_404():
    body = {**_VALID_ORDER_BODY, "productId": "tree-999"}
    event = _api_event("POST", "/orders", body=body, claims=_VALID_CLAIMS)
    resp = handler(event, None)
    assert resp["statusCode"] == 404


def test_create_order_happy_path():
    event = _api_event("POST", "/orders", body=_VALID_ORDER_BODY, claims=_VALID_CLAIMS)
    resp = handler(event, None)
    assert resp["statusCode"] == 201
    body = json.loads(resp["body"])
    assert "orderId" in body
    assert body["status"] == "PENDING"
    assert body["notificationStatus"] == "QUEUED"
    assert body["message"] == "Order submitted successfully"


def test_create_order_response_does_not_contain_jwt():
    event = _api_event("POST", "/orders", body=_VALID_ORDER_BODY, claims=_VALID_CLAIMS)
    resp = handler(event, None)
    assert "Bearer" not in resp["body"]
    assert "eyJ" not in resp["body"]


def test_unknown_route_returns_404():
    event = _api_event("GET", "/nonexistent")
    resp = handler(event, None)
    assert resp["statusCode"] == 404


def test_cors_headers_present():
    event = _api_event("GET", "/health")
    resp = handler(event, None)
    assert "Access-Control-Allow-Origin" in resp["headers"]
