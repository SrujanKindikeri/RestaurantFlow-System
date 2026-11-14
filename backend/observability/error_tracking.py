# =============================================================================
# RestaurantFlow — Centralized Error Tracking
# Phase 24
#
# A single entry point for capturing unhandled backend exceptions:
#   - Writes a structured ERROR log with request_id + safe tenant context +
#     a safe stack trace (no local variables).
#   - Forwards to Sentry IF configured (SENTRY_DSN set + sentry-sdk installed);
#     otherwise local structured logging is the authoritative record and the
#     limitation is documented.
#
# No secrets, passwords, payment data or unnecessary personal data are sent to
# any third-party error monitoring provider. Only request_id, environment,
# service and exception metadata are forwarded.
# =============================================================================

import logging
import os
import traceback

logger = logging.getLogger("observability.errors")

_sentry_initialized = False


def init_sentry(service_name: str = "restaurantflow-api", environment: str = "production"):
    """Initialize Sentry if configured and importable. Idempotent + safe."""
    global _sentry_initialized
    if _sentry_initialized:
        return True
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return False
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
    except Exception as exc:
        logger.warning(
            "SENTRY_DSN set but sentry-sdk not installed (%s). Install "
            "sentry-sdk to enable external error tracking.", exc,
        )
        return False

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            # Send only a controlled sample to control cost/overhead.
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")),
            sample_rate=float(os.getenv("SENTRY_SAMPLE_RATE", "1.0")),
            send_default_pii=False,  # never send PII automatically
            max_breadcrumbs=50,
            before_send=_sentry_before_send,
            integrations=[
                DjangoIntegration(transaction_style="url"),
                CeleryIntegration(),
                RedisIntegration(),
            ],
        )
        _sentry_initialized = True
        logger.info("Sentry error tracking initialized (service=%s, env=%s).",
                    service_name, environment)
        return True
    except Exception as exc:
        logger.error("Sentry initialization failed: %s", exc)
        return False


# Field names stripped from Sentry events before sending.
_SENSITIVE_EVENT_KEYS = {
    "password", "token", "authorization", "api_key", "secret",
    "card_number", "cvv", "pan", "upi_pin", "session_key",
}


def _sentry_before_send(event, hint):
    """Scrub sensitive values before forwarding to Sentry."""
    try:
        _scrub(event)
    except Exception:
        pass
    return event


def _scrub(obj):
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if k.lower() in _SENSITIVE_EVENT_KEYS:
                obj[k] = "[REDACTED]"
            else:
                _scrub(obj[k])
    elif isinstance(obj, list):
        for item in obj:
            _scrub(item)


def capture_exception(exc, request=None, *, error_code: str = "", severity: str = "HIGH"):
    """
    Capture an unhandled exception.

    Always logs a structured record. Forwards to Sentry if initialised.
    `request` is used only to enrich logs/Sentry with request_id + safe scope,
    never to read request bodies or payloads.
    """
    request_id = None
    user_id = None
    if request is not None:
        request_id = getattr(request, "request_id", None)
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            user_id = str(getattr(user, "pk", "") or "")

    logger.error(
        "Unhandled exception: %s",
        exc,
        extra={
            "event": "backend.exception",
            "severity": severity,
            "error_code": error_code or exc.__class__.__name__,
            "request_id": request_id,
            "user_id": user_id,
        },
        exc_info=True,
    )

    if _sentry_initialized:
        try:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                if request_id:
                    scope.set_tag("request_id", request_id)
                if user_id:
                    scope.set_user({"id": user_id})
                scope.set_tag("error_code", error_code or exc.__class__.__name__)
                sentry_sdk.capture_exception(exc)
        except Exception as e:
            logger.debug("Sentry capture failed: %s", e)


def is_sentry_active() -> bool:
    return _sentry_initialized
