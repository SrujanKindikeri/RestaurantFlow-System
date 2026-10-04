# =============================================================================
# RestaurantFlow — WebSocket Notification Provider
# Phase 16
#
# Pushes a lightweight notification.created event to the per-user
# WebSocket group using Django Channels + Redis.
#
# Group name: notifications_user_{user_id}
#
# The WebSocket is NOT the source of truth. If delivery fails here,
# the in-app notification is still available via the REST API.
# =============================================================================

import json
import logging

from notifications.delivery.base import BaseNotificationProvider, DeliveryPayload, DeliveryResult
from notifications.constants import (
    CHANNEL_WEBSOCKET,
    DELIVERY_SENT,
    DELIVERY_FAILED,
    WS_NOTIFICATION_CREATED,
    WS_GROUP_USER,
)

logger = logging.getLogger("notifications")


class WebSocketProvider(BaseNotificationProvider):
    """
    WebSocket delivery via Django Channels channel layer (Redis-backed).

    Fires a lightweight event — full data is fetched by the frontend
    via REST GET /api/notifications/ after receiving the event.

    Authorization:
        Users are subscribed to their own group only
        (notifications_user_{user_id}). Cross-user delivery is impossible
        because the group name is derived server-side.

    Failure handling:
        Channels/Redis unavailability is caught and logged. The method
        returns FAILED (not DELIVERED) in that case — the in-app record
        already exists, so the user will see the notification on next load.
    """

    provider_code = "WEBSOCKET"
    channel_code  = CHANNEL_WEBSOCKET

    def send(self, payload: DeliveryPayload) -> DeliveryResult:
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer

            channel_layer = get_channel_layer()
            if channel_layer is None:
                return DeliveryResult.failed("Channel layer not configured.")

            notif = payload.notification
            group_name = WS_GROUP_USER.format(user_id=str(payload.recipient_user.pk))

            event_payload = {
                "notification_id": str(notif.pk),
                "type":            notif.notification_type,
                "severity":        notif.severity,
                "title":           notif.title,
                "created_at":      notif.created_at.isoformat(),
            }

            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type":    "notification_event",   # → consumer handler method
                    "payload": {
                        "type":    WS_NOTIFICATION_CREATED,
                        **event_payload,
                    },
                },
            )

            logger.debug(
                "WebSocketProvider.send: group=%s notification=%s",
                group_name, notif.pk,
            )
            return DeliveryResult(success=True, status=DELIVERY_SENT)

        except Exception as exc:
            logger.warning(
                "WebSocketProvider.send failed: notification=%s user=%s error=%s",
                getattr(payload.notification, "pk", "?"),
                getattr(payload.recipient_user, "pk", "?"),
                exc,
            )
            return DeliveryResult.failed(str(exc))

    def validate_configuration(self) -> bool:
        try:
            from channels.layers import get_channel_layer
            return get_channel_layer() is not None
        except Exception:
            return False

    def get_status(self) -> dict:
        configured = self.validate_configuration()
        return {
            "channel": CHANNEL_WEBSOCKET,
            "provider": self.provider_code,
            "configured": configured,
            "status": "available" if configured else "unavailable — channel layer not configured",
        }
