"""Order request validation.

Validates the JSON body of POST /orders requests.
Returns (True, None) when valid, (False, "reason") when invalid.
"""
from __future__ import annotations

from typing import Any

_REQUIRED_FIELDS: list[str] = [
    "customerName",
    "customerEmail",
    "customerPhone",
    "productId",
    "quantity",
    "preferredPickupDate",
]

_MAX_STRING_LENGTH = 500
_MAX_NOTES_LENGTH = 2000


def validate_order(body: dict[str, Any]) -> tuple[bool, str | None]:
    """Validate an order request body.

    Returns (True, None) on success, (False, error_message) on failure.
    """
    if not isinstance(body, dict):
        return False, "Request body must be a JSON object"

    # Required-field presence
    for field in _REQUIRED_FIELDS:
        if not body.get(field):
            return False, f"Missing required field: {field}"

    # Type checks
    if not isinstance(body["quantity"], int) or body["quantity"] < 1:
        return False, "quantity must be a positive integer"

    # Length limits (basic input-size guard)
    for field in ("customerName", "customerEmail", "customerPhone", "productId", "preferredPickupDate"):
        val = body.get(field, "")
        if isinstance(val, str) and len(val) > _MAX_STRING_LENGTH:
            return False, f"{field} exceeds maximum length"

    notes = body.get("notes", "")
    if isinstance(notes, str) and len(notes) > _MAX_NOTES_LENGTH:
        return False, "notes exceeds maximum length"

    # Basic email sanity (not full RFC, just catches obvious junk)
    email: str = body["customerEmail"]
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "customerEmail is not a valid email address"

    return True, None
