# =============================================================================
# RestaurantFlow — ASGI Configuration
# Phase 7: WebSocket support via Django Channels
# =============================================================================

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django ASGI application early to ensure the AppRegistry is populated
django_asgi_app = get_asgi_application()

# Phase 24 — optional distributed tracing + external error tracking. Both are
# no-ops when their packages/exporters are not configured; see tracing.py and
# error_tracking.py. Never blocks startup.
try:
    from observability.tracing import setup_tracing
    from observability.error_tracking import init_sentry
    from django.conf import settings
    setup_tracing(getattr(settings, "OBSERVABILITY_SERVICE_NAME", "restaurantflow-api"),
                  getattr(settings, "OBSERVABILITY_ENVIRONMENT", "production"))
    init_sentry(getattr(settings, "OBSERVABILITY_SERVICE_NAME", "restaurantflow-api"),
                getattr(settings, "OBSERVABILITY_ENVIRONMENT", "production"))
except Exception:
    # Observability init must never prevent the application from starting.
    pass

# Import WebSocket URL patterns after Django is fully initialized
from kitchen.routing import websocket_urlpatterns as kitchen_ws  # noqa: E402
from central_control.routing import websocket_urlpatterns as cc_ws  # noqa: E402
from notifications.routing import websocket_urlpatterns as notif_ws  # noqa: E402

# Merge all WebSocket URL patterns
all_websocket_urlpatterns = kitchen_ws + cc_ws + notif_ws

application = ProtocolTypeRouter(
    {
        # HTTP → standard Django ASGI handler
        "http": django_asgi_app,
        # WebSocket → Channels + JWT auth
        "websocket": AuthMiddlewareStack(
            URLRouter(all_websocket_urlpatterns)
        ),
    }
)
