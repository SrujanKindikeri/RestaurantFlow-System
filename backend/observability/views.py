# =============================================================================
# RestaurantFlow — Observability Views
# Phase 24
#
#   GET  /metrics                       — Prometheus text exposition (token-gated)
#   POST /api/observability/alerts/am   — Alertmanager webhook (token-gated)
#   POST /api/observability/frontend-errors — Frontend error capture (rate-limited)
#
# No new models are introduced; business events and frontend errors are
# emitted as structured logs + metrics, not stored rows. The authoritative
# audit trail remains the existing audit system.
# =============================================================================

import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle

from observability.metrics import REGISTRY

logger = logging.getLogger("observability.views")


# ---------------------------------------------------------------------------
# Prometheus metrics endpoint
# ---------------------------------------------------------------------------

def metrics_view(request):
    """Expose all registered metrics in Prometheus text exposition format."""
    if not _metrics_allowed(request):
        return HttpResponse(status=403)
    body = REGISTRY.render()
    return HttpResponse(body, content_type="text/plain; version=0.0.4; charset=utf-8")


def _metrics_allowed(request) -> bool:
    # In development, allow unauthenticated scraping for convenience.
    if getattr(settings, "DEBUG", False):
        return True
    token = getattr(settings, "PROMETHEUS_SCRAPE_TOKEN", "") or ""
    if not token:
        # No token configured in production → refuse (no public metrics).
        return False
    # Accept either a custom header (X-Prometheus-Token) or the standard
    # "Authorization: Bearer <token>" that Prometheus sends via bearer_token.
    supplied = request.headers.get("X-Prometheus-Token", "") or request.META.get(
        "HTTP_X_PROMETHEUS_TOKEN", ""
    ) or ""
    if not supplied:
        auth = request.headers.get("Authorization", "") or request.META.get(
            "HTTP_AUTHORIZATION", ""
        ) or ""
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
    return _constant_time_eq(supplied, token)


def _constant_time_eq(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(str(a), str(b))


# ---------------------------------------------------------------------------
# Alertmanager webhook
# ---------------------------------------------------------------------------

@csrf_exempt
@require_POST
def alertmanager_webhook_view(request):
    """Receive Alertmanager alerts and forward them to Central Control."""
    if not _webhook_allowed(request):
        return JsonResponse({"error": "forbidden"}, status=403)

    import json
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "invalid_json"}, status=400)

    organization = _resolve_monitoring_organization()
    from observability.alert_forwarder import handle_alertmanager_webhook
    result = handle_alertmanager_webhook(payload, organization=organization)
    return JsonResponse({"ok": True, **result})


def _webhook_allowed(request) -> bool:
    token = getattr(settings, "ALERTMANAGER_WEBHOOK_TOKEN", "") or ""
    if not token:
        return False
    supplied = request.headers.get("X-Alertmanager-Token", "") or request.META.get(
        "HTTP_X_ALERTMANAGER_TOKEN", ""
    ) or ""
    if not supplied:
        auth = request.headers.get("Authorization", "") or request.META.get(
            "HTTP_AUTHORIZATION", ""
        ) or ""
        if auth.lower().startswith("bearer "):
            supplied = auth[7:].strip()
    return _constant_time_eq(supplied, token)


def _resolve_monitoring_organization():
    """
    Resolve the organization that owns monitoring alerts.

    In multi-tenant production set OBSERVABILITY_MONITORING_ORG_ID. Without
    it, alerts are attached to the first organization (single-tenant dev).
    """
    from organizations.models import Organization
    org_id = getattr(settings, "OBSERVABILITY_MONITORING_ORG_ID", "") or ""
    if org_id:
        return Organization.objects.filter(pk=org_id).first()
    return Organization.objects.order_by("created_at").first()


# ---------------------------------------------------------------------------
# Frontend error capture
# ---------------------------------------------------------------------------

class FrontendErrorThrottle(AnonRateThrottle):
    scope = "frontend_errors"


@method_decorator(csrf_exempt, name="dispatch")
class FrontendErrorView(APIView):
    """
    Capture a frontend runtime error. Accepts only safe diagnostic fields;
    request bodies/payloads are never recorded. Errors are written as
    structured logs and counted by a metric.
    """
    permission_classes = [AllowAny]
    throttle_classes = [FrontendErrorThrottle]
    MAX_MESSAGE_LEN = 1000

    def post(self, request):
        data = request.data or {}
        event_type = _clean(data.get("type", "javascript_error"), 80)
        message = _clean(data.get("message", ""), self.MAX_MESSAGE_LEN)
        url = _clean(data.get("url", ""), 500)
        line = _int_or_none(data.get("line"))
        col = _int_or_none(data.get("column"))
        severity = _clean(data.get("severity", "MEDIUM"), 10).upper() or "MEDIUM"
        app_version = _clean(data.get("app_version", ""), 60)
        request_id = _clean(data.get("request_id", ""), 128)

        # Never store user/customer identifiers here; frontend may send a
        # hashed user reference but we do not persist payloads.
        logger.warning(
            "Frontend error: type=%s severity=%s url=%s line=%s col=%s app_version=%s "
            "request_id=%s message=%s",
            event_type, severity, url, line, col, app_version, request_id, message,
            extra={
                "event": "frontend.error",
                "severity": severity,
                "error_code": event_type,
            },
        )
        from observability.metrics import business_events_total
        business_events_total.inc(event="frontend.error", severity=severity)
        return Response({"ok": True}, status=200)


def _clean(value, max_len: int) -> str:
    if value is None:
        return ""
    s = str(value)
    return s[:max_len]


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
