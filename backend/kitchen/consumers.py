# =============================================================================
# RestaurantFlow — Kitchen WebSocket Consumer
# Phase 7
#
# WebSocket URL pattern:
#   ws://host/ws/kitchen/<branch_id>/
#
# Group naming convention:
#   kitchen_{branch_id}
#
# Authentication flow on connect:
#   1. Extract JWT from query string (?token=<jwt>) or Authorization header
#   2. Authenticate user
#   3. Verify user is active
#   4. Verify user has kitchen.view permission
#   5. Verify user has access to the requested branch
#   6. Join the branch kitchen group
#   7. Send current kitchen state (REST sync)
#
# Security guarantees:
#   - Users can only join groups for branches they are authorized to access.
#   - Cross-branch data leakage is prevented by server-side group assignment.
#   - Disabled users are rejected at connect time.
#   - Branch ID from URL is always re-validated against user's accessible branches.
#
# Event flow:
#   Server → Client:  { "type": "kitchen.event", "payload": {...} }
#   Client → Server:  (currently receive-only; future: ack/ping)
#
# Reconnection support:
#   - On (re)connect, current kitchen state is sent as a bulk sync message.
#   - This reconciles any events missed during disconnection.
#
# Redis failure:
#   - group_add/group_send failures are caught and logged.
#   - The consumer falls back gracefully — no silent data loss.
# =============================================================================

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger("kitchen")


class KitchenConsumer(AsyncWebsocketConsumer):
    """
    Async WebSocket consumer for the Kitchen Display System.

    Handles:
        - JWT authentication on connect
        - Branch access validation
        - Group join/leave
        - Real-time kitchen event forwarding to connected KDS clients
        - Initial state sync on connect
    """

    # -------------------------------------------------------------------------
    # connect
    # -------------------------------------------------------------------------

    async def connect(self):
        """
        Authenticate user and join branch kitchen group.
        Rejects unauthorized connections immediately.
        """
        branch_id = self.scope["url_route"]["kwargs"].get("branch_id")

        # Step 1: Authenticate
        user = await self._get_authenticated_user()
        if user is None:
            logger.warning(
                "KitchenConsumer.connect: rejected unauthenticated connection "
                "for branch=%s", branch_id,
            )
            await self.close(code=4001)
            return

        # Step 2: Verify kitchen.view permission
        has_perm = await self._check_permission(user, "kitchen.view")
        if not has_perm:
            logger.warning(
                "KitchenConsumer.connect: rejected user=%s (no kitchen.view) branch=%s",
                user.email, branch_id,
            )
            await self.close(code=4003)
            return

        # Step 3: Verify branch access
        branch = await self._get_authorized_branch(user, branch_id)
        if branch is None:
            logger.warning(
                "KitchenConsumer.connect: rejected user=%s no access to branch=%s",
                user.email, branch_id,
            )
            await self.close(code=4004)
            return

        # Step 4: Store context
        self.user = user
        self.branch = branch
        self.branch_id = str(branch.pk)
        self.group_name = f"kitchen_{self.branch_id}"

        # Step 5: Join group
        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name,
            )
        except Exception as exc:
            logger.error(
                "KitchenConsumer.connect: failed to join group=%s error=%s",
                self.group_name, exc,
            )
            await self.close(code=4005)
            return

        await self.accept()

        logger.info(
            "KitchenConsumer.connect: user=%s joined group=%s",
            user.email, self.group_name,
        )

        # Step 6: Send initial state sync
        await self._send_initial_sync()

    # -------------------------------------------------------------------------
    # disconnect
    # -------------------------------------------------------------------------

    async def disconnect(self, close_code):
        """Leave the branch group on disconnect."""
        group_name = getattr(self, "group_name", None)
        if group_name:
            try:
                await self.channel_layer.group_discard(
                    group_name,
                    self.channel_name,
                )
            except Exception as exc:
                logger.error(
                    "KitchenConsumer.disconnect: error leaving group=%s error=%s",
                    group_name, exc,
                )
            logger.info(
                "KitchenConsumer.disconnect: user=%s left group=%s code=%s",
                getattr(self, "user", {}).email if hasattr(self, "user") else "?",
                group_name,
                close_code,
            )

    # -------------------------------------------------------------------------
    # receive (client → server)
    # -------------------------------------------------------------------------

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle messages from the KDS client.
        Currently receive-only for heartbeat/ping support.
        Future: client-initiated actions (ack, etc.)
        """
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except (json.JSONDecodeError, ValueError):
            await self._send_error("INVALID_JSON", "Message must be valid JSON.")
            return

        msg_type = data.get("type")

        if msg_type == "ping":
            await self.send(text_data=json.dumps({"type": "pong"}))
        elif msg_type == "sync":
            # Client requests a full state sync (e.g. after reconnect)
            await self._send_initial_sync()
        else:
            # Unknown message type — ignore gracefully
            logger.debug(
                "KitchenConsumer.receive: unknown type=%s from user=%s",
                msg_type, getattr(self, "user", {}).email
                if hasattr(self, "user") else "?",
            )

    # -------------------------------------------------------------------------
    # kitchen.event — group message handler
    # -------------------------------------------------------------------------

    async def kitchen_event(self, event):
        """
        Forward a kitchen event from the channel group to the WebSocket client.

        Called by Django Channels when a message is sent to this consumer's group
        via channel_layer.group_send(..., {"type": "kitchen.event", ...}).
        """
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps({
            "type": "kitchen.event",
            "payload": payload,
        }))

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _get_authenticated_user(self):
        """
        Extract and validate JWT from query string or scope headers.
        Returns the User instance or None.
        """
        # Try query string token first: ws://host/ws/kitchen/.../?token=<jwt>
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        token_str = None
        for part in query_string.split("&"):
            if part.startswith("token="):
                token_str = part[6:]
                break

        # Fall back to scope user (set by AuthMiddlewareStack / JWTAuthMiddleware)
        if not token_str:
            scope_user = self.scope.get("user")
            if scope_user and scope_user.is_authenticated and scope_user.is_active:
                return scope_user
            return None

        # Validate the JWT token
        try:
            user = await database_sync_to_async(self._validate_jwt_token)(token_str)
            return user
        except Exception as exc:
            logger.warning("KitchenConsumer._get_authenticated_user: JWT error=%s", exc)
            return None

    def _validate_jwt_token(self, token_str: str):
        """Synchronous JWT validation (called via database_sync_to_async)."""
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        from accounts.models import User

        try:
            token = AccessToken(token_str)
            user_id = token.get("user_id")
            user = User.objects.get(pk=user_id, is_active=True)
            return user
        except (TokenError, User.DoesNotExist):
            return None

    @database_sync_to_async
    def _check_permission(self, user, code: str) -> bool:
        """Check if user has the given permission code."""
        from accounts import access as acl
        return acl.has_permission(user, code)

    @database_sync_to_async
    def _get_authorized_branch(self, user, branch_id: str):
        """
        Return Branch if user is authorized to access it, else None.
        Always validates server-side — never trusts client-supplied branch_id.
        """
        from accounts import access as acl
        from organizations.models import Branch

        if not branch_id:
            return None

        try:
            branch = Branch.objects.get(pk=branch_id)
        except (Branch.DoesNotExist, Exception):
            return None

        if not acl.can_access_branch(user, branch):
            return None

        return branch

    async def _send_initial_sync(self):
        """
        Send the current kitchen state to the client immediately on connect.
        This reconciles any events missed during a disconnection.
        """
        try:
            orders_data = await database_sync_to_async(self._get_current_state)()
            await self.send(text_data=json.dumps({
                "type": "kitchen.sync",
                "branch_id": self.branch_id,
                "orders": orders_data,
            }))
        except Exception as exc:
            logger.error(
                "KitchenConsumer._send_initial_sync: error=%s branch=%s",
                exc, getattr(self, "branch_id", "?"),
            )

    def _get_current_state(self):
        """
        Synchronously fetch today's active kitchen orders for the branch.
        Returns a list of serializable dicts (minimal — not the full serializer).
        """
        from django.utils import timezone
        from kitchen.models import KitchenOrder, KitchenOrderStatus
        from kitchen.serializers import KitchenOrderListSerializer

        branch = self.branch
        qs = (
            KitchenOrder.objects
            .filter(
                branch=branch,
                received_at__date=timezone.now().date(),
            )
            .exclude(status=KitchenOrderStatus.CANCELLED)
            .select_related(
                "order__table",
                "order__counter",
                "order__assigned_waiter",
            )
            .prefetch_related("items__menu_item")
            .order_by("-priority", "received_at")
        )
        serializer = KitchenOrderListSerializer(qs, many=True)
        return serializer.data

    async def _send_error(self, code: str, message: str):
        """Send an error message to the WebSocket client."""
        await self.send(text_data=json.dumps({
            "type": "error",
            "code": code,
            "message": message,
        }))
