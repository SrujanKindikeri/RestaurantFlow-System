# =============================================================================
# RestaurantFlow — Observability Middleware
# Phase 24
#
#   RequestCorrelationMiddleware
#       - Validate/generate X-Request-ID
#       - Bind a LogContext (request_id + user_id) for the request lifetime
#       - Echo X-Request-ID on the response
#
#   MetricsMiddleware
#       - Per-request API metrics (count, latency, errors, sizes)
#       - Low-cardinality labels only (route view-name, method, status class)
#       - Never records user IDs / order IDs / URLs / raw exceptions as labels
#
# Both middlewares are defensive: a failure inside instrumentation must never
# change the HTTP response or break the request.
# =============================================================================

import re
import time
import uuid

from observability.context import LogContext, set_context, reset_context, get_context
from observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_errors_total,
    http_request_size_bytes,
    http_response_size_bytes,
)
from observability.constants import (
    REQUEST_ID_HEADER,
    REQUEST_ID_PATTERN,
    REQUEST_ID_INVALID,
)

import logging

logger = logging.getLogger("observability.middleware")

_REQUEST_ID_RE = re.compile(REQUEST_ID_PATTERN)

# Paths excluded from metrics to avoid scrape/self-noise and admin static.
_METRICS_SKIP_PREFIXES = ("/metrics", "/static/", "/media/")


def _normalise_route(request) -> str:
    """Return a low-cardinality route identifier for the request."""
    try:
        match = getattr(request, "resolver_match", None)
        if match is not None:
            name = getattr(match, "view_name", None)
            if name:
                return name
            # Fall back to the route pattern (contains <pk> placeholders, not ids).
            route = getattr(match, "route", "")
            if route:
                return route or "unnamed"
        return "not_resolved"
    except Exception:
        return "not_resolved"


def _status_class(status_code: int) -> str:
    return f"{status_code // 100}xx"


class RequestCorrelationMiddleware:
    """Validate/generate a request ID and bind structured-log context."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = self._extract_request_id(request)
        # Bind context for the lifetime of this request.
        ctx = LogContext(request_id=request_id)
        token = set_context(ctx)
        request.request_id = request_id
        try:
            response = self.get_response(request)
        finally:
            reset_context(token)

        # Always echo the request id on the response.
        try:
            response[REQUEST_ID_HEADER] = request_id
        except Exception:
            pass
        return response

    @staticmethod
    def _extract_request_id(request) -> str:
        incoming = ""
        try:
            incoming = request.headers.get(REQUEST_ID_HEADER, "") or request.META.get(
                "HTTP_X_REQUEST_ID", ""
            ) or ""
        except Exception:
            incoming = ""
        incoming = (incoming or "").strip()
        if incoming and _REQUEST_ID_RE.match(incoming):
            return incoming
        # Generate a fresh, safe id. We never trust a client id for auth.
        return uuid.uuid4().hex


class MetricsMiddleware:
    """Record API request metrics. Never raises into the request path."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.perf_counter()
        # Pre-read request size (content-length) before the body is consumed.
        request_size = 0
        try:
            cl = request.META.get("CONTENT_LENGTH") or request.META.get("HTTP_CONTENT_LENGTH")
            if cl:
                request_size = int(cl)
        except Exception:
            request_size = 0

        response = self.get_response(request)

        try:
            self._record(request, response, start, request_size)
        except Exception as exc:
            logger.debug("MetricsMiddleware recording failed: %s", exc)
        return response

    def _record(self, request, response, start, request_size):
        path = request.path or ""
        if any(path.startswith(p) for p in _METRICS_SKIP_PREFIXES):
            return

        duration = max(time.perf_counter() - start, 0.0)
        method = request.method or "UNKNOWN"
        status_code = getattr(response, "status_code", 200) or 200
        route = _normalise_route(request)

        http_requests_total.inc(
            route=route, method=method, status_class=_status_class(status_code),
        )
        http_request_duration_seconds.observe(duration, route=route, method=method)

        if request_size and request_size > 0:
            http_request_size_bytes.observe(request_size, route=route, method=method)

        response_size = 0
        try:
            content = getattr(response, "content", b"") or b""
            response_size = len(content)
        except Exception:
            response_size = 0
        if response_size and response_size > 0:
            http_response_size_bytes.observe(response_size, route=route, method=method)

        if status_code >= 500:
            http_errors_total.inc(route=route, method=method)
