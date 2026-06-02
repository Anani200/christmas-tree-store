"""
Structured JSON logger for all Lambda functions.

Usage:
    from src.utils.logger import get_logger
    log = get_logger("order-api")
    log.info("order_created", order_id="abc123", user_id="sub-xyz")

NEVER pass JWT tokens, passwords, or secret values to any log method.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any


class _StructuredLogger:
    """Thin wrapper that emits structured JSON lines to stdout."""

    _SENSITIVE_KEYS = frozenset(
        {"token", "jwt", "password", "secret", "authorization", "auth", "credential"}
    )

    def __init__(self, service: str, function_name: str, level: int) -> None:
        self._service = service
        self._function_name = function_name
        self._level = level
        # Underlying stdlib logger to honour Lambda's log-stream routing.
        self._stdlib = logging.getLogger(service)
        self._stdlib.setLevel(level)
        if not self._stdlib.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(level)
            self._stdlib.addHandler(handler)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def info(self, event_type: str, **kwargs: Any) -> None:
        self._emit("INFO", event_type, **kwargs)

    def warning(self, event_type: str, **kwargs: Any) -> None:
        self._emit("WARNING", event_type, **kwargs)

    def error(self, event_type: str, **kwargs: Any) -> None:
        self._emit("ERROR", event_type, **kwargs)

    def debug(self, event_type: str, **kwargs: Any) -> None:
        if self._level <= logging.DEBUG:
            self._emit("DEBUG", event_type, **kwargs)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _sanitize(self, data: dict[str, Any]) -> dict[str, Any]:
        """Remove any key whose name looks sensitive."""
        return {
            k: "[REDACTED]" if k.lower() in self._SENSITIVE_KEYS else v
            for k, v in data.items()
        }

    def _emit(self, level: str, event_type: str, **kwargs: Any) -> None:
        entry: dict[str, Any] = {
            "level": level,
            "service": self._service,
            "function": self._function_name,
            "eventType": event_type,
        }
        entry.update(self._sanitize(kwargs))
        line = json.dumps(entry, default=str)
        # Write directly to stdout so output is always capturable in tests.
        print(line, file=sys.stdout, flush=True)


def get_logger(service: str | None = None) -> _StructuredLogger:
    """Return a logger bound to the current Lambda context."""
    svc = service or os.environ.get("SERVICE_NAME", "unknown-service")
    fn = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "local")
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    return _StructuredLogger(svc, fn, level)
