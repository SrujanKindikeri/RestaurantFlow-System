# =============================================================================
# RestaurantFlow — Structured JSON Logging
# Phase 24
#
# Provides:
#   - StructuredJsonFormatter: emits one JSON object per log record with
#     consistent timestamp, level, service, environment, correlation id and
#     safe tenant context, plus exception details.
#   - ContextualLogFilter: injects the active LogContext (request_id + safe
#     tenant scope) into every record so handlers do not need to look it up.
#   - redact(): removes/replaces known-sensitive fields before serialisation.
#
# This module never imports Django models; settings are read lazily so it is
# safe to use in early bootstrap paths.
# =============================================================================

import json
import logging
import os
import re
import traceback
from datetime import datetime, timezone

from observability.context import get_context
from observability.constants import (
    LOG_BASE_FIELDS,
    SENSITIVE_LOG_KEYS,
    SERVICE_NAME,
    ENV_DEVELOPMENT,
    REQUEST_ID_INVALID,
)


# ---------------------------------------------------------------------------
# Settings accessors (lazy, with safe defaults)
# ---------------------------------------------------------------------------

def _service_name() -> str:
    try:
        from django.conf import settings
        return getattr(settings, "OBSERVABILITY_SERVICE_NAME", SERVICE_NAME)
    except Exception:
        return SERVICE_NAME


def _environment() -> str:
    try:
        from django.conf import settings
        return getattr(settings, "OBSERVABILITY_ENVIRONMENT", None) or (
            ENV_DEVELOPMENT if getattr(settings, "DEBUG", False) else "production"
        )
    except Exception:
        return ENV_DEVELOPMENT


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------

_SENSITIVE_RE = re.compile(
    r"(?i)(" + "|".join(re.escape(k) for k in SENSITIVE_LOG_KEYS) + r")"
)


def _is_sensitive_key(key: str) -> bool:
    return key.lower() in SENSITIVE_LOG_KEYS


def redact(value):
    """
    Recursively redact sensitive values in dicts/lists. A sensitive key has
    its value replaced with "[REDACTED]". Strings are scanned for embedded
    secrets (e.g. "Authorization: Bearer xxx") using a denylist of substrings;
    matched substrings are masked.

    Never raise: redaction is defense-in-depth and must never break logging.
    """
    try:
        if isinstance(value, dict):
            return {k: ("[REDACTED]" if _is_sensitive_key(k) else redact(v)) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [redact(v) for v in value]
        if isinstance(value, str):
            return _redact_string(value)
    except Exception:
        return "[redaction-error]"
    return value


def _redact_string(value: str) -> str:
    if not value:
        return value
    # Mask occurrences of "<sensitivekey> <value>" patterns such as header lines.
    masked = _SENSITIVE_RE.sub(lambda m: m.group(1), value)
    # Mask any value that follows a sensitive keyword to the end of the line,
    # so "Authorization: Bearer <token>" is fully redacted (not just "Bearer").
    bearer_re = re.compile(
        r"(?i)(bearer|token|api[_-]?key|authorization|secret|password|cvv|pan)\s*[:=]\s*[^\n]+"
    )
    masked = bearer_re.sub(lambda m: f"{m.group(1)}=[REDACTED]", masked)
    return masked


# ---------------------------------------------------------------------------
# Filter: inject active context
# ---------------------------------------------------------------------------

class ContextualLogFilter(logging.Filter):
    """Attach the active LogContext + service/environment to each record."""

    def filter(self, record):
        ctx = get_context()
        record.request_id = getattr(record, "request_id", None) or ctx.request_id
        record.user_id = getattr(record, "user_id", None) or ctx.user_id
        record.company_id = getattr(record, "company_id", None) or ctx.company_id
        record.restaurant_id = getattr(record, "restaurant_id", None) or ctx.restaurant_id
        record.branch_id = getattr(record, "branch_id", None) or ctx.branch_id
        if not getattr(record, "service", None):
            record.service = _service_name()
        if not getattr(record, "environment", None):
            record.environment = _environment()
        return True


# ---------------------------------------------------------------------------
# Formatter: JSON
# ---------------------------------------------------------------------------

class StructuredJsonFormatter(logging.Formatter):
    """
    Emit a single JSON object per log record.

    Base fields (from LOG_BASE_FIELDS) are always present (as null when not
    set). Arbitrary `extra=...` kwargs are merged in and redacted. Exception
    info is serialised as exception_type / exception_message / stack_trace
    (the formatted traceback string, which excludes local variables).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def format(self, record):
        # Ensure the context filter has run.
        ContextualLogFilter().filter(record)

        payload = {}
        for field in LOG_BASE_FIELDS:
            payload[field] = getattr(record, field, None)

        # Map LogRecord attributes that do not share our field names.
        payload["level"] = record.levelname
        payload["timestamp"] = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat()
        payload["message"] = record.getMessage()

        # Merge non-standard `extra` fields (anything not part of standard LogRecord).
        std_attrs = set(vars(logging.LogRecord(
            name="", level=0, pathname="", lineno=0, msg="", args=None, exc_info=None
        )).keys())
        std_attrs.update({"asctime", "message", "request_id", "user_id",
                          "company_id", "restaurant_id", "branch_id",
                          "service", "environment"})
        for key, value in vars(record).items():
            if key.startswith("_") or key in std_attrs or key in LOG_BASE_FIELDS:
                continue
            payload[key] = redact(value)

        # Exception details (safe: traceback text has no local variables).
        if record.exc_info:
            etype, evalue, tb = record.exc_info
            payload["exception_type"] = etype.__name__ if etype else None
            payload["exception_message"] = str(evalue) if evalue else None
            payload["stack_trace"] = "".join(traceback.format_exception(etype, evalue, tb))

        # Sanitise the request_id (never let an unsafe injected id through).
        if payload.get("request_id") == REQUEST_ID_INVALID:
            payload["request_id"] = None

        # Redact all string leaf values defensively.
        payload = redact(payload)

        return json.dumps(payload, default=str, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Convenience: get a logger that is pre-tagged with an event + module name.
# ---------------------------------------------------------------------------

def get_logger(name: str) -> logging.Logger:
    """Return a logger scoped to the observability naming convention."""
    return logging.getLogger(name)
