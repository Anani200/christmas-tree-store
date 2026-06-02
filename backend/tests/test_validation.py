"""Tests for order request validation."""
from __future__ import annotations

import pytest

from src.utils.validation import validate_order

_VALID_BODY = {
    "customerName": "Jane Doe",
    "customerEmail": "jane@example.com",
    "customerPhone": "555-555-5555",
    "productId": "tree-001",
    "quantity": 1,
    "preferredPickupDate": "2026-12-10",
    "notes": "Please wrap it.",
}


def test_valid_order_passes():
    valid, reason = validate_order(_VALID_BODY.copy())
    assert valid is True
    assert reason is None


@pytest.mark.parametrize("missing_field", [
    "customerName",
    "customerEmail",
    "customerPhone",
    "productId",
    "quantity",
    "preferredPickupDate",
])
def test_missing_required_field_rejected(missing_field):
    body = _VALID_BODY.copy()
    del body[missing_field]
    valid, reason = validate_order(body)
    assert valid is False
    assert missing_field in (reason or "")


def test_non_dict_body_rejected():
    valid, reason = validate_order("not a dict")  # type: ignore[arg-type]
    assert valid is False


def test_zero_quantity_rejected():
    body = {**_VALID_BODY, "quantity": 0}
    valid, reason = validate_order(body)
    assert valid is False


def test_negative_quantity_rejected():
    body = {**_VALID_BODY, "quantity": -1}
    valid, reason = validate_order(body)
    assert valid is False


def test_string_quantity_rejected():
    body = {**_VALID_BODY, "quantity": "one"}
    valid, reason = validate_order(body)
    assert valid is False


def test_oversize_customer_name_rejected():
    body = {**_VALID_BODY, "customerName": "A" * 501}
    valid, reason = validate_order(body)
    assert valid is False


def test_oversize_notes_rejected():
    body = {**_VALID_BODY, "notes": "x" * 2001}
    valid, reason = validate_order(body)
    assert valid is False


def test_invalid_email_rejected():
    body = {**_VALID_BODY, "customerEmail": "not-an-email"}
    valid, reason = validate_order(body)
    assert valid is False


def test_optional_notes_absent_is_ok():
    body = _VALID_BODY.copy()
    del body["notes"]
    valid, reason = validate_order(body)
    assert valid is True
