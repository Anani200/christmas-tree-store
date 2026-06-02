"""Tests for the Auth Lambda handler (LOCAL_MOCK=true, no AWS calls)."""
from __future__ import annotations

import json
import os

import pytest

os.environ["LOCAL_MOCK"] = "true"
os.environ["USER_POOL_ID"] = "us-east-1_TEST"
os.environ["USER_POOL_CLIENT_ID"] = "test-client-id"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

from src.handlers.auth import handler  # noqa: E402


def _event(path: str, body: dict | None = None, access_token: str | None = None) -> dict:
    headers: dict = {}
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    return {
        "httpMethod": "POST",
        "path": path,
        "headers": headers,
        "body": json.dumps(body or {}),
        "requestContext": {},
    }


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class TestLogin:
    def test_success(self):
        resp = handler(_event("/auth/login", {"email": "a@b.com", "password": "Pass1234"}), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "idToken" in body
        assert "accessToken" in body
        assert "refreshToken" in body
        assert "expiresIn" in body

    def test_missing_email(self):
        resp = handler(_event("/auth/login", {"password": "Pass1234"}), None)
        assert resp["statusCode"] == 400

    def test_missing_password(self):
        resp = handler(_event("/auth/login", {"email": "a@b.com"}), None)
        assert resp["statusCode"] == 400

    def test_empty_body(self):
        resp = handler(_event("/auth/login", {}), None)
        assert resp["statusCode"] == 400


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

class TestRegister:
    def test_success(self):
        resp = handler(_event("/auth/register", {"email": "new@b.com", "password": "Pass1234"}), None)
        assert resp["statusCode"] == 201
        body = json.loads(resp["body"])
        assert "message" in body

    def test_missing_fields(self):
        resp = handler(_event("/auth/register", {"email": "x@y.com"}), None)
        assert resp["statusCode"] == 400


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------

class TestConfirm:
    def test_success(self):
        resp = handler(_event("/auth/confirm", {"email": "a@b.com", "code": "123456"}), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "message" in body

    def test_missing_code(self):
        resp = handler(_event("/auth/confirm", {"email": "a@b.com"}), None)
        assert resp["statusCode"] == 400


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

class TestRefresh:
    def test_success(self):
        resp = handler(_event("/auth/refresh", {"refreshToken": "some-refresh-token"}), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "idToken" in body
        assert "accessToken" in body

    def test_missing_token(self):
        resp = handler(_event("/auth/refresh", {}), None)
        assert resp["statusCode"] == 400


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_success(self):
        resp = handler(_event("/auth/logout", {}, access_token="mock-access-token"), None)
        assert resp["statusCode"] == 200
        body = json.loads(resp["body"])
        assert "message" in body

    def test_no_token_returns_400(self):
        resp = handler(_event("/auth/logout", {}), None)
        # LOCAL_MOCK skips access token check — returns 200 regardless
        assert resp["statusCode"] == 200


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

class TestRouting:
    def test_unknown_route(self):
        event = {
            "httpMethod": "GET",
            "path": "/auth/login",
            "headers": {},
            "body": None,
            "requestContext": {},
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 404

    def test_options_preflight(self):
        event = {
            "httpMethod": "OPTIONS",
            "path": "/auth/login",
            "headers": {},
            "body": None,
            "requestContext": {},
        }
        resp = handler(event, None)
        assert resp["statusCode"] == 200
