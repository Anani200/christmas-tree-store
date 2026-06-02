"""Tests for the structured logger."""
from __future__ import annotations

import json
import os


def test_logger_emits_json(capsys):
    os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test-fn"
    os.environ["LOG_LEVEL"] = "INFO"
    from src.utils.logger import get_logger

    log = get_logger("test-service")
    log.info("test_event", order_id="ord-1", user_id="u-1")

    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if l.strip().startswith("{")]
    assert lines, "Expected at least one JSON line"
    entry = json.loads(lines[-1])
    assert entry["eventType"] == "test_event"
    assert entry["service"] == "test-service"
    assert entry["order_id"] == "ord-1"


def test_logger_redacts_sensitive_keys(capsys):
    from src.utils.logger import get_logger

    log = get_logger("test-service")
    log.info("test_event", token="should-be-redacted", password="also-redacted", order_id="safe")

    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if l.strip().startswith("{")]
    assert lines
    entry = json.loads(lines[-1])
    assert entry["token"] == "[REDACTED]"
    assert entry["password"] == "[REDACTED]"
    assert entry["order_id"] == "safe"


def test_logger_does_not_log_authorization_header(capsys):
    from src.utils.logger import get_logger

    log = get_logger("test-service")
    log.info("test_event", authorization="Bearer eyJhbGc...")

    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if l.strip().startswith("{")]
    assert lines
    entry = json.loads(lines[-1])
    assert entry["authorization"] == "[REDACTED]"
    assert "eyJhbGc" not in captured.out
