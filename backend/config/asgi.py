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
