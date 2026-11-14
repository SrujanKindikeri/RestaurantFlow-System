# =============================================================================
# RestaurantFlow — Health check endpoints
# Phase 23: Liveness and readiness probes for Docker / load balancer
# =============================================================================

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import os
import logging

logger = logging.getLogger("common.health")


def health_live(request):
    """Liveness probe: confirms the process is alive and responding."""
    return JsonResponse({"status": "ok"})

def health_ready(request):
    """Readiness probe: confirms DB and Redis are reachable."""
    checks = {}
    status_code = 200

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        status_code = 503

    # Redis / cache check
    try:
        cache.set("health_check", "1", timeout=5)
        val = cache.get("health_check")
        if val == "1":
            checks["redis"] = "ok"
        else:
            checks["redis"] = "error"
            status_code = 503
    except Exception:
        checks["redis"] = "error"
        status_code = 503

    checks["status"] = "ready" if status_code == 200 else "not_ready"
    return JsonResponse(checks, status=status_code)


# =============================================================================
# Phase 24 — Dependency health (deeper, still cheap, never leaks secrets)
# =============================================================================

def health_dependencies(request):
    """
    Report the reachability of critical dependencies plus process-level config.

    Distinct from the readiness probe: this surface is meant for operators and
    dashboards, not a hot load-balancer probe. It checks PostgreSQL, Redis,
    the Channels layer, Celery worker liveness (where feasible), and required
    application configuration. It never returns secrets or stack traces.
    """
    checks = {}
    status_code = 200

    # --- PostgreSQL -------------------------------------------------------
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        status_code = 503

    # --- Redis (Django cache backend) ------------------------------------
    try:
        cache.set("health_dep_check", "1", timeout=5)
        checks["redis"] = "ok" if cache.get("health_dep_check") == "1" else "error"
        if checks["redis"] == "error":
            status_code = 503
    except Exception:
        checks["redis"] = "error"
        status_code = 503

    # --- Django Channels layer ------------------------------------------
    try:
        from channels.layers import get_channel_layer
        layer = get_channel_layer()
        checks["channels"] = "ok" if layer is not None else "error"
        if layer is None:
            status_code = 503
    except Exception:
        checks["channels"] = "error"
        status_code = 503

    # --- Celery worker liveness (best-effort, never blocks) --------------
    checks["celery"] = _check_celery_liveness()

    # --- Required application configuration ------------------------------
    checks["config"] = _check_required_config()

    overall = "ok" if status_code == 200 else "degraded"
    return JsonResponse({"status": overall, "dependencies": checks}, status=status_code)


def _check_celery_liveness() -> str:
    """
    Best-effort Celery liveness check. Inspecting the broker is cheap and works
    without a running worker process; an active control ping is attempted only
    when a real broker is available. Never raises.
    """
    try:
        from celery import current_app
        from observability.metrics import celery_worker_up
        # If any worker heartbeat has been recorded (worker_ready signal), mark up.
        if celery_worker_up._values:
            return "ok"
        # Fall back to a broker ping (does not require a worker process).
        with current_app.connection_or_acquire() as conn:
            conn.ensure_connection(max_retries=1, timeout=1.0)
            return "ok"
    except Exception:
        # Eager/test environments have no broker; report unknown rather than
        # error so this component does not fail the whole dependency check.
        return "unknown"


def _check_required_config() -> str:
    """Verify required, non-secret application configuration is present.

    Returns a coarse "ok"/"error" so the public endpoint never reveals which
    secret is misconfigured. The specific field is logged for operators.
    """
    try:
        from django.conf import settings
        missing = []
        if not getattr(settings, "DEBUG", False):
            if not os.getenv("SECRET_KEY"):
                missing.append("SECRET_KEY")
            if os.getenv("DB_PASSWORD", "change_me") == "change_me":
                missing.append("DB_PASSWORD")
        if missing:
            logger.warning("health: required config missing: %s", ",".join(missing))
        return "ok" if not missing else "error"
    except Exception:
        return "unknown"
