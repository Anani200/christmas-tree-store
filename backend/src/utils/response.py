"""HTTP response helpers used by the Order API Lambda."""
from __future__ import annotations

import json
import os
from typing import Any


def _cors_headers() -> dict[str, str]:
    origin = os.environ.get("CORS_ALLOWED_ORIGIN", "http://localhost:5173")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
        "Access-Control-Allow-Credentials": "true",
    }


def ok(body: Any, status: int = 200) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **_cors_headers()},
        "body": json.dumps(body, default=str),
    }


def error(message: str, status: int = 500) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **_cors_headers()},
        "body": json.dumps({"message": message}),
    }


def bad_request(message: str) -> dict[str, Any]:
    return error(message, 400)


def unauthorized(message: str = "Authentication required to place an order") -> dict[str, Any]:
    return error(message, 401)


def not_found(message: str = "Resource not found") -> dict[str, Any]:
    return error(message, 404)
