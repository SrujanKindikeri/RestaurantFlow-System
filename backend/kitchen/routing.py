# =============================================================================
# RestaurantFlow — Kitchen WebSocket URL Routing
# Phase 7
#
# WebSocket URL:
#   ws://host/ws/kitchen/<branch_id>/
#
# Group name (server-side):
#   kitchen_{branch_id}
#
# Security:
#   branch_id in the URL is ALWAYS re-validated server-side in the consumer.
#   A client cannot impersonate another branch by supplying a different UUID.
#
# Future extension:
#   ws://host/ws/kitchen/<branch_id>/station/<station_id>/
#   Add a new URL pattern here and a corresponding consumer.
# =============================================================================

from django.urls import re_path
from kitchen.consumers import KitchenConsumer

websocket_urlpatterns = [
    re_path(
        r"^ws/kitchen/(?P<branch_id>[0-9a-f-]{36})/$",
        KitchenConsumer.as_asgi(),
    ),
]
