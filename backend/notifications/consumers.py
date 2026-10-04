# =============================================================================
# RestaurantFlow — Notifications WebSocket Consumer
# Phase 16
#
# WebSocket URL: ws://host/ws/notifications/
#
# Group naming: notifications_user_{user_id}
#
# Authentication:
#   JWT from query string (?token=<jwt>) or AuthMiddlewareStack.
#   User ID is always derived server-side — never trusted from client.
#
# Security:
#   - Each user joins ONLY their own group.
#   - Cross-user delivery is structurally impossible.
#   - Unauthenticated connections are closed with code 4001.
#
# Reconnect / resync:
#   WebSocket is NOT the source of truth.
#   After reconnect the frontend must call:
#       GET /api/notifications/?unread=true
#   to resync missed notifications.
#
# Server → client events:
#   notification.created  — new notification for this user
#   notification.updated  — notification state changed
#   notification.read     — notification marked read
#
# Client → server messages:
#   {"type": "ping"}    → {"type": "pong"}
#   {"type": "sync"}    → sends unread_count
# =============================================================================

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from notifications.constants import WS_GROUP_USER

logger = logging.getLogger("notifications")


class NotificationsConsumer(AsyncWebsocketConsumer):
    """
    Per-user WebSocket consumer for real-time notification delivery.
    """

    # -------------------------------------------------------------------------
    # connect
    # -------------------------------------------------------------------------

    async def connect(self):
        """Authenticate user and join personal notification group."""
        user = await self._get_authenticated_user()
        if user is None:
            logger.warning(
                "NotificationsConsumer.connect: rejected unauthenticated connection"
            )
            await self.close(code=4001)
            return

        self.user       = user
        self.user_id    = str(user.pk)
        self.group_name = WS_GROUP_USER.format(user_id=self.user_id)

        # Join personal group — always the user's own group derived server-side
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Send initial unread count
        await self._send_unread_count()

        logger.info(
            "NotificationsConsumer.connect: user=%s group=%s",
            self.user_id, self.group_name,
        )

    # -------------------------------------------------------------------------
    # disconnect
    # -------------------------------------------------------------------------

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug(
            "NotificationsConsumer.disconnect: user=%s code=%s",
            getattr(self, "user_id", "?"), close_code,
        )

    # -------------------------------------------------------------------------
    # receive — messages from the client
    # -------------------------------------------------------------------------

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, ValueError):
            await self.send(text_data=json.dumps({"type": "error", "code": "INVALID_JSON"}))
            return

        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))

        elif msg_type == "sync":
            await self._send_unread_count()

        else:
            logger.debug(
                "NotificationsConsumer.receive: unknown type=%s user=%s",
                msg_type, self.user_id,
            )

    # -------------------------------------------------------------------------
    # notification_event — group message handler (called by channel_layer.group_send)
    # -------------------------------------------------------------------------

    async def notification_event(self, event):
        """
        Forward a notification event from the channel group to this client.

        Called by Django Channels when group_send() is used with
        {"type": "notification_event", "payload": {...}}.
        """
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps({
            "type":    "notification.event",
            "payload": payload,
        }))

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _send_unread_count(self):
        """Send the current unread notification count to this client."""
        try:
            count = await database_sync_to_async(self._get_unread_count)()
            await self.send(text_data=json.dumps({
                "type":  "notification.unread_count",
                "count": count,
            }))
        except Exception as exc:
            logger.debug("_send_unread_count failed: %s", exc)

    def _get_unread_count(self) -> int:
        from notifications.selectors import get_unread_count_for_user
        return get_unread_count_for_user(self.user)

    async def _get_authenticated_user(self):
        """
        Extract and validate JWT from query string or scope user.
        Mirrors the exact pattern used by CentralControlConsumer and KitchenConsumer.
        """
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        token_str    = None
        for part in query_string.split("&"):
            if part.startswith("token="):
                token_str = part[6:]
                break

        # Fallback to AuthMiddlewareStack scope user
        if not token_str:
            scope_user = self.scope.get("user")
            if scope_user and scope_user.is_authenticated and scope_user.is_active:
                return scope_user
            return None

        # Validate the JWT
        try:
            user = await database_sync_to_async(self._validate_jwt_token)(token_str)
            return user
        except Exception as exc:
            logger.warning("NotificationsConsumer._get_authenticated_user: JWT error=%s", exc)
            return None

    def _validate_jwt_token(self, token_str: str):
        """Synchronous JWT validation (called via database_sync_to_async)."""
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        from accounts.models import User

        try:
            token   = AccessToken(token_str)
            user_id = token.get("user_id")
            return User.objects.get(pk=user_id, is_active=True)
        except (TokenError, User.DoesNotExist):
            return None
