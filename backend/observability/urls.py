# =============================================================================
# RestaurantFlow — Observability URL Configuration
# Phase 24
# =============================================================================

from django.urls import path, re_path

from observability.views import (
    metrics_view,
    alertmanager_webhook_view,
    FrontendErrorView,
)

urlpatterns = [
    # Prometheus scrape target. Plain Django view (text/plain).
    re_path(r"^metrics/?$", metrics_view, name="observability_metrics"),

    # Alertmanager webhook → Central Control forwarder.
    path(
        "api/observability/alerts/am",
        alertmanager_webhook_view,
        name="observability_alertmanager_webhook",
    ),

    # Frontend runtime error capture (rate-limited, anonymous-safe).
    path(
        "api/observability/frontend-errors",
        FrontendErrorView.as_view(),
        name="observability_frontend_errors",
    ),
]
