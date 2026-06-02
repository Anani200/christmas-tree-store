"""Order API Lambda handler.

Routes:
  GET  /health                — public health check
  GET  /products              — list all products (public)
  GET  /products/{productId}  — single product detail (public)
  POST /orders                — create order (Cognito-protected via API GW)

Environment variables (set by SAM / environment):
  PRODUCTS_TABLE     — DynamoDB products table name
  ORDERS_TABLE       — DynamoDB orders table name
  ORDER_QUEUE_URL    — SQS order queue URL
  LOCAL_MOCK         — set to "true" to skip AWS calls (unit tests / local dev)
  CORS_ALLOWED_ORIGIN — origin for CORS headers (default: http://localhost:5173)
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.utils.logger import get_logger
from src.utils.response import bad_request, error, not_found, ok, unauthorized
from src.utils.validation import validate_order

log = get_logger("order-api")

_BOTO_CONFIG = Config(retries={"max_attempts": 3, "mode": "standard"})

# ---------------------------------------------------------------------------
# AWS clients (lazy — not initialised in test mode)
# ---------------------------------------------------------------------------
_dynamodb = None
_sqs = None


def _get_dynamodb():
    global _dynamodb
    if _dynamodb is None:
        _dynamodb = boto3.resource(
            "dynamodb",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            config=_BOTO_CONFIG,
        )
    return _dynamodb


def _get_sqs():
    global _sqs
    if _sqs is None:
        _sqs = boto3.client(
            "sqs",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            config=_BOTO_CONFIG,
        )
    return _sqs


# ---------------------------------------------------------------------------
# Mock data — used when LOCAL_MOCK=true
# ---------------------------------------------------------------------------
from src.seed.products import PRODUCTS as _SEED_PRODUCTS  # noqa: E402

_MOCK_ORDERS: list[dict] = []


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def _health(_event: dict, _context: Any) -> dict:
    log.info("health_check", status="ok")
    return ok({"status": "ok", "service": "christmas-tree-api"})


def _list_products(_event: dict, _context: Any) -> dict:
    log.info("list_products_request")
    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        log.info("list_products_response", source="mock", count=len(_SEED_PRODUCTS))
        return ok({"products": _SEED_PRODUCTS})

    try:
        table = _get_dynamodb().Table(os.environ["PRODUCTS_TABLE"])
        items: list[dict] = []
        resp = table.scan()
        items.extend(resp.get("Items", []))
        while "LastEvaluatedKey" in resp:
            resp = table.scan(ExclusiveStartKey=resp["LastEvaluatedKey"])
            items.extend(resp.get("Items", []))
        log.info("list_products_response", source="dynamodb", count=len(items))
        return ok({"products": _decimal_to_float(items)})
    except ClientError as exc:
        log.error("list_products_dynamodb_error", error=str(exc))
        return error("Failed to retrieve products", 500)


def _get_product(event: dict, _context: Any) -> dict:
    product_id = event.get("pathParameters", {}).get("productId", "")
    log.info("get_product_request", product_id=product_id)

    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        product = next((p for p in _SEED_PRODUCTS if p["productId"] == product_id), None)
        if not product:
            return not_found(f"Product '{product_id}' not found")
        return ok(product)

    try:
        table = _get_dynamodb().Table(os.environ["PRODUCTS_TABLE"])
        resp = table.get_item(Key={"productId": product_id})
        item = resp.get("Item")
        if not item:
            log.warning("get_product_not_found", product_id=product_id)
            return not_found(f"Product '{product_id}' not found")
        return ok(_decimal_to_float(item))
    except ClientError as exc:
        log.error("get_product_dynamodb_error", product_id=product_id, error=str(exc))
        return error("Failed to retrieve product", 500)


def _create_order(event: dict, _context: Any) -> dict:
    # 1. Extract Cognito claims from API Gateway authorizer context
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    claims = authorizer.get("claims") or {}
    user_id = claims.get("sub")
    user_email = claims.get("email")

    if not user_id:
        log.warning("create_order_unauthorized", reason="no_cognito_claims")
        return unauthorized()

    log.info("create_order_request", user_id=user_id)

    # 2. Parse and validate body
    try:
        body: dict = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        log.warning("create_order_invalid_json", user_id=user_id)
        return bad_request("Request body must be valid JSON")

    valid, reason = validate_order(body)
    if not valid:
        log.warning("create_order_validation_failed", user_id=user_id, reason=reason)
        return bad_request(reason or "Invalid request")

    # 3. Resolve product (server-side — prevents client from injecting productName)
    product_id: str = body["productId"]
    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        product = next((p for p in _SEED_PRODUCTS if p["productId"] == product_id), None)
    else:
        try:
            products_table = _get_dynamodb().Table(os.environ["PRODUCTS_TABLE"])
            resp = products_table.get_item(Key={"productId": product_id})
            product = resp.get("Item")
        except ClientError as exc:
            log.error("create_order_product_lookup_error", user_id=user_id, product_id=product_id, error=str(exc))
            return error("Failed to verify product. Please try again.", 500)

    if not product:
        log.warning("create_order_product_not_found", user_id=user_id, product_id=product_id)
        return not_found(f"Product '{product_id}' not found")

    # 4. Build order record
    now = datetime.now(timezone.utc).isoformat()
    order_id = str(uuid.uuid4())

    order: dict[str, Any] = {
        "orderId": order_id,
        "userId": user_id,
        "userEmail": user_email,
        "productId": product_id,
        "productName": product["name"],
        "customerName": body["customerName"],
        "customerEmail": body["customerEmail"],
        "customerPhone": body["customerPhone"],
        "quantity": body["quantity"],
        "preferredPickupDate": body["preferredPickupDate"],
        "notes": body.get("notes", ""),
        "status": "PENDING",
        "notificationStatus": "QUEUED",
        "createdAt": now,
        "updatedAt": now,
    }

    # 5. Persist order
    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        _MOCK_ORDERS.append(order)
        log.info("create_order_ddb_write_success", order_id=order_id, user_id=user_id, source="mock")
    else:
        try:
            orders_table = _get_dynamodb().Table(os.environ["ORDERS_TABLE"])
            orders_table.put_item(Item=order)
            log.info("create_order_ddb_write_success", order_id=order_id, user_id=user_id)
        except ClientError as exc:
            log.error("create_order_ddb_write_failure", order_id=order_id, user_id=user_id, error=str(exc))
            return error("Failed to save order. Please try again.", 500)

    # 6. Enqueue SQS notification
    sqs_message = {
        "eventType": "ORDER_CREATED",
        "orderId": order_id,
        "productId": product_id,
        "productName": product["name"],
        "customerName": body["customerName"],
        "customerEmail": body["customerEmail"],
        "customerPhone": body["customerPhone"],
        "quantity": body["quantity"],
        "preferredPickupDate": body["preferredPickupDate"],
        "status": "PENDING",
        "createdAt": now,
    }

    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        log.info("create_order_sqs_send_success", order_id=order_id, source="mock")
    else:
        try:
            _get_sqs().send_message(
                QueueUrl=os.environ["ORDER_QUEUE_URL"],
                MessageBody=json.dumps(sqs_message),
            )
            log.info("create_order_sqs_send_success", order_id=order_id)
        except Exception as exc:
            # Non-fatal: order is persisted; notification will be retried via DLQ inspection.
            log.error("create_order_sqs_send_failure", order_id=order_id, error=str(exc))

    # 7. Respond
    response_body = {
        "message": "Order submitted successfully",
        "orderId": order_id,
        "status": "PENDING",
        "notificationStatus": "QUEUED",
    }
    log.info("create_order_complete", order_id=order_id, user_id=user_id)
    return ok(response_body, status=201)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_ROUTES: dict[tuple[str, str], Any] = {
    ("GET", "/health"): _health,
    ("GET", "/products"): _list_products,
    ("GET", "/products/{productId}"): _get_product,
    ("POST", "/orders"): _create_order,
}


def handler(event: dict, context: Any) -> dict:
    method = (event.get("httpMethod") or "").upper()
    resource = event.get("resource") or event.get("path") or ""

    log.info(
        "request_received",
        method=method,
        resource=resource,
        request_id=(event.get("requestContext") or {}).get("requestId", "local"),
    )

    route_fn = _ROUTES.get((method, resource))
    if route_fn is None:
        return not_found("Route not found")

    return route_fn(event, context)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _decimal_to_float(obj: Any) -> Any:
    """Recursively convert DynamoDB Decimal types to float for JSON serialisation."""
    if isinstance(obj, list):
        return [_decimal_to_float(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, Decimal):
        return float(obj)
    return obj
