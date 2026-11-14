# =============================================================================
# RestaurantFlow — Health check endpoints
# Phase 23: Liveness and readiness probes for Docker / load balancer
# =============================================================================

from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import os


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
