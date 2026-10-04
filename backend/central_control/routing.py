# =============================================================================
# RestaurantFlow — Central Control Center WebSocket URL Routing
# Phase 15
#
# Registered in config/asgi.py alongside kitchen.routing.
# URL: ws://host/ws/central-control/<organization_id>/
# =============================================================================

from django.urls import re_path

from central_control.consumers import CentralControlConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/central-control/(?P<organization_id>[0-9a-f-]{36})/$",
        CentralControlConsumer.as_asgi(),
    ),
]
