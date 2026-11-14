# =============================================================================
# RestaurantFlow — WSGI Configuration
# =============================================================================

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Phase 24 — optional tracing + error tracking init (no-op unless configured).
try:
    from observability.tracing import setup_tracing
    from observability.error_tracking import init_sentry
    from django.conf import settings
    setup_tracing(getattr(settings, "OBSERVABILITY_SERVICE_NAME", "restaurantflow-api"),
                  getattr(settings, "OBSERVABILITY_ENVIRONMENT", "production"))
    init_sentry(getattr(settings, "OBSERVABILITY_SERVICE_NAME", "restaurantflow-api"),
                getattr(settings, "OBSERVABILITY_ENVIRONMENT", "production"))
except Exception:
    pass
