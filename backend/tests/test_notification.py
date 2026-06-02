"""Tests for the Notification Lambda handler (LOCAL_MOCK=true, no AWS calls)."""
from __future__ import annotations

import json
import os

import pytest

os.environ["LOCAL_MOCK"] = "true"
os.environ["SNS_TOPIC_ARN"] = "arn:aws:sns:us-east-1:123456789:test-topic"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test-notification-fn"

from src.handlers.notification import handler, _build_notification  # noqa: E402


def _sqs_event(order: dict) -> dict:
    return {
        "Records": [
            {
                "messageId": "msg-001",
                "body": json.dumps({
                    "eventType": "ORDER_CREATED",
                    **order,
                }),
            }
        ]
    }


_SAMPLE_ORDER = {
    "orderId": "ord-123",
    "productId": "tree-001",
    "productName": "Fraser Fir",
    "customerName": "Jane Doe",
    "customerEmail": "jane@example.com",
    "customerPhone": "555-555-5555",
    "quantity": 1,
    "preferredPickupDate": "2026-12-10",
    "status": "PENDING",
    "createdAt": "2026-05-29T00:00:00+00:00",
}


def test_notification_handler_runs_without_error():
    event = _sqs_event(_SAMPLE_ORDER)
    handler(event, None)  # Should not raise


def test_notification_handler_multiple_records():
    event = {
        "Records": [
            {"messageId": "msg-001", "body": json.dumps({"eventType": "ORDER_CREATED", **_SAMPLE_ORDER})},
            {"messageId": "msg-002", "body": json.dumps({"eventType": "ORDER_CREATED", **{**_SAMPLE_ORDER, "orderId": "ord-124"}})},
        ]
    }
    handler(event, None)  # Should process both without error


def test_notification_handler_raises_on_bad_json():
    event = {"Records": [{"messageId": "msg-bad", "body": "not-json"}]}
    with pytest.raises(json.JSONDecodeError):
        handler(event, None)


def test_build_notification_contains_order_id():
    subject, message = _build_notification(_SAMPLE_ORDER)
    assert "ord-123" in message
    assert subject == "New Christmas Tree Order Received"


def test_build_notification_contains_all_fields():
    subject, message = _build_notification(_SAMPLE_ORDER)
    assert "Jane Doe" in message
    assert "Fraser Fir" in message
    assert "555-555-5555" in message
    assert "2026-12-10" in message


def test_notification_handler_raises_on_sns_failure(monkeypatch):
    """When LOCAL_MOCK is off and SNS publish fails, exception must propagate."""
    os.environ["LOCAL_MOCK"] = "false"

    import src.handlers.notification as notif_module

    mock_sns = type("MockSNS", (), {"publish": staticmethod(lambda **kw: (_ for _ in ()).throw(RuntimeError("SNS down")))})()
    monkeypatch.setattr(notif_module, "_sns", mock_sns)

    event = _sqs_event(_SAMPLE_ORDER)
    with pytest.raises(RuntimeError, match="SNS down"):
        notif_module.handler(event, None)

    os.environ["LOCAL_MOCK"] = "true"  # restore


def test_seed_data_has_5_products():
    from src.seed.products import PRODUCTS
    assert len(PRODUCTS) == 5


def test_seed_data_all_have_required_fields():
    from src.seed.products import PRODUCTS
    required = {"productId", "name", "type", "height", "price", "description",
                "careInstructions", "availabilityStatus", "quantityAvailable"}
    for product in PRODUCTS:
        missing = required - product.keys()
        assert not missing, f"Product {product.get('productId')} missing: {missing}"
