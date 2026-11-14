# =============================================================================
# RestaurantFlow — Observability App Config
# Phase 24
#
# Connects Celery signals for task metrics on app ready. Tracing/error-tracking
# initialization is triggered from ASGI/WSGI entrypoints, not here, so that
# `manage.py` commands and tests are never coupled to optional exporters.
# =============================================================================

from django.apps import AppConfig


class ObservabilityConfig(AppConfig):
    name = "observability"
    verbose_name = "Observability & Monitoring"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        # Import to register signal receivers. Guarded internally so the
        # absence of a running Celery worker never breaks app load.
        try:
            from observability import celery_signals  # noqa: F401
        except Exception:
            # Signal wiring must never block application startup.
            pass
