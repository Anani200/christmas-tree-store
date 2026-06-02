"""Auth Lambda handler — Cognito proxy.

Routes (all public, no Cognito authorizer):
  POST /auth/login    — initiates USER_PASSWORD_AUTH, returns tokens
  POST /auth/register — creates a new user (SignUp)
  POST /auth/confirm  — confirms email with verification code
  POST /auth/refresh  — refreshes tokens using a refresh token
  POST /auth/logout   — global sign-out (invalidates all tokens)

Environment variables:
  USER_POOL_ID        — Cognito User Pool ID
  USER_POOL_CLIENT_ID — Cognito App Client ID (no secret)
  LOCAL_MOCK          — set to "true" to return stub responses (tests / local dev)
  CORS_ALLOWED_ORIGIN — origin for CORS headers
"""
from __future__ import annotations

import json
import os
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from src.utils.logger import get_logger
from src.utils.response import bad_request, error, ok, unauthorized

log = get_logger("auth")

_BOTO_CONFIG = Config(retries={"max_attempts": 3, "mode": "standard"})

_cognito = None


def _get_cognito():
    global _cognito
    if _cognito is None:
        _cognito = boto3.client(
            "cognito-idp",
            region_name=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            config=_BOTO_CONFIG,
        )
    return _cognito


def _client_id() -> str:
    return os.environ["USER_POOL_CLIENT_ID"]


def _pool_id() -> str:
    return os.environ["USER_POOL_ID"]


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------

def _login(event: dict, _context: Any) -> dict:
    body = _parse_body(event)
    email = body.get("email", "").strip()
    password = body.get("password", "")
    if not email or not password:
        return bad_request("email and password are required")

    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        return ok({
            "idToken": "mock-id-token",
            "accessToken": "mock-access-token",
            "refreshToken": "mock-refresh-token",
            "expiresIn": 3600,
        })

    try:
        resp = _get_cognito().initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            AuthParameters={"USERNAME": email, "PASSWORD": password},
            ClientId=_client_id(),
        )
        result = resp["AuthenticationResult"]
        log.info("login_success", email=email)
        return ok({
            "idToken": result["IdToken"],
            "accessToken": result["AccessToken"],
            "refreshToken": result["RefreshToken"],
            "expiresIn": result["ExpiresIn"],
        })
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        log.warning("login_failed", email=email, code=code)
        if code in ("NotAuthorizedException", "UserNotFoundException"):
            return unauthorized("Invalid email or password")
        if code == "UserNotConfirmedException":
            return error("Email address not verified. Please confirm your account.", 403)
        return error("Authentication failed", 500)


def _register(event: dict, _context: Any) -> dict:
    body = _parse_body(event)
    email = body.get("email", "").strip()
    password = body.get("password", "")
    if not email or not password:
        return bad_request("email and password are required")

    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        return ok({"message": "Registration successful. Check your email for a verification code."}, 201)

    try:
        _get_cognito().sign_up(
            ClientId=_client_id(),
            Username=email,
            Password=password,
            UserAttributes=[{"Name": "email", "Value": email}],
        )
        log.info("register_success", email=email)
        return ok({"message": "Registration successful. Check your email for a verification code."}, 201)
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        log.warning("register_failed", email=email, code=code)
        if code == "UsernameExistsException":
            return error("An account with this email already exists", 409)
        if code == "InvalidPasswordException":
            return bad_request("Password does not meet requirements (min 8 chars, upper, lower, number)")
        return error("Registration failed", 500)


def _confirm(event: dict, _context: Any) -> dict:
    body = _parse_body(event)
    email = body.get("email", "").strip()
    code = body.get("code", "").strip()
    if not email or not code:
        return bad_request("email and code are required")

    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        return ok({"message": "Email confirmed successfully"})

    try:
        _get_cognito().confirm_sign_up(
            ClientId=_client_id(),
            Username=email,
            ConfirmationCode=code,
        )
        log.info("confirm_success", email=email)
        return ok({"message": "Email confirmed successfully"})
    except ClientError as exc:
        code_err = exc.response["Error"]["Code"]
        log.warning("confirm_failed", email=email, code=code_err)
        if code_err == "CodeMismatchException":
            return bad_request("Invalid verification code")
        if code_err == "ExpiredCodeException":
            return bad_request("Verification code has expired. Please request a new one.")
        return error("Confirmation failed", 500)


def _refresh(event: dict, _context: Any) -> dict:
    body = _parse_body(event)
    refresh_token = body.get("refreshToken", "")
    if not refresh_token:
        return bad_request("refreshToken is required")

    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        return ok({
            "idToken": "mock-id-token-refreshed",
            "accessToken": "mock-access-token-refreshed",
            "expiresIn": 3600,
        })

    try:
        resp = _get_cognito().initiate_auth(
            AuthFlow="REFRESH_TOKEN_AUTH",
            AuthParameters={"REFRESH_TOKEN": refresh_token},
            ClientId=_client_id(),
        )
        result = resp["AuthenticationResult"]
        log.info("refresh_success")
        return ok({
            "idToken": result["IdToken"],
            "accessToken": result["AccessToken"],
            "expiresIn": result["ExpiresIn"],
        })
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        log.warning("refresh_failed", code=code)
        if code in ("NotAuthorizedException", "TokenExpiredException"):
            return unauthorized("Refresh token is invalid or expired")
        return error("Token refresh failed", 500)


def _logout(event: dict, _context: Any) -> dict:
    # Requires the access token (not the id token)
    auth_header = (event.get("headers") or {}).get("Authorization", "")
    access_token = auth_header.replace("Bearer ", "").strip()

    if os.environ.get("LOCAL_MOCK", "").lower() == "true":
        return ok({"message": "Signed out successfully"})

    if not access_token:
        return bad_request("Authorization header with access token is required")

    try:
        _get_cognito().global_sign_out(AccessToken=access_token)
        log.info("logout_success")
        return ok({"message": "Signed out successfully"})
    except ClientError as exc:
        code = exc.response["Error"]["Code"]
        log.warning("logout_failed", code=code)
        # If already invalid, treat as success
        if code == "NotAuthorizedException":
            return ok({"message": "Signed out successfully"})
        return error("Sign-out failed", 500)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

ROUTES: dict[str, Any] = {
    "POST /auth/login": _login,
    "POST /auth/register": _register,
    "POST /auth/confirm": _confirm,
    "POST /auth/refresh": _refresh,
    "POST /auth/logout": _logout,
}


def handler(event: dict, context: Any) -> dict:
    method = event.get("httpMethod", "")
    path = event.get("path", "")
    route_key = f"{method} {path}"

    log.info("auth_request", route=route_key)

    if method == "OPTIONS":
        from src.utils.response import ok as _ok
        return _ok({})

    fn = ROUTES.get(route_key)
    if fn is None:
        return error(f"Route not found: {route_key}", 404)

    return fn(event, context)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_body(event: dict) -> dict:
    raw = event.get("body") or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
