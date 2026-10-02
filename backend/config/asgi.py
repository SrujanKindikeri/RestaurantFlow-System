# =============================================================================
# RestaurantFlow — ASGI Configuration
# WebSocket-ready via Django Channels
# =============================================================================

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django ASGI application early to ensure the AppRegistry is populated
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        # HTTP requests → standard Django ASGI handler
        "http": django_asgi_app,
        # WebSocket requests — routes will be added in future phases
        # "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
