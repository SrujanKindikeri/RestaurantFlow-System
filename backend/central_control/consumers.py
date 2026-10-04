# =============================================================================
# RestaurantFlow — Central Control Center WebSocket Consumer
# Phase 15
#
# WebSocket URL pattern:
#   ws://host/ws/central-control/<organization_id>/
#
# Group naming convention:
#   company_{organization_id}_central_control
#
# Authentication flow on connect:
#   1. Extract JWT from query string (?token=<jwt>) or AuthMiddlewareStack
#   2. Authenticate and verify user is active
#   3. Verify user has central_control.dashboard.view permission
#   4. Verify user has access to the requested organization
#   5. Join the organization central-control group
#   6. Send initial state sync
#
# Security guarantees:
#   - Users can only join groups for organizations they are authorized to access.
#   - Cross-company data leakage is prevented by server-side group assignment.
#   - The group name is derived SERVER-SIDE from the validated organization.
#   - Never trust the client-supplied organization_id for authorization alone.
#
# Event format (server → client):
#   {"type": "central.event", "payload": {"type": "<event_type>", ...}}
# =============================================================================

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from central_control.constants import (
    PERM_DASHBOARD_VIEW,
    WS_GROUP_COMPANY,
)

logger = logging.getLogger("central_control")


class CentralControlConsumer(AsyncWebsocketConsumer):
    """
    Async WebSocket consumer for the Central Control Center.

    Clients receive real-time events:
      - central.alert.created / updated / resolved
      - central.issue.created / updated / resolved
      - central.health.updated
      - central.restaurant.status_changed
      - central.branch.status_changed
    """

    # -------------------------------------------------------------------------
    # connect
    # -------------------------------------------------------------------------

    async def connect(self):
        """
        Authenticate user, validate organization access, join group.
        Rejects unauthorized connections immediately.
        """
        org_id = self.scope["url_route"]["kwargs"].get("organization_id")

        # Step 1: Authenticate
        user = await self._get_authenticated_user()
        if user is None:
            logger.warning(
                "CentralControlConsumer.connect: rejected unauthenticated connection "
                "for org=%s", org_id,
            )
            await self.close(code=4001)
            return

        # Step 2: Check central_control.dashboard.view permission
        has_perm = await self._check_permission(user, PERM_DASHBOARD_VIEW)
        if not has_perm:
            logger.warning(
                "CentralControlConsumer.connect: rejected user=%s (no %s) org=%s",
                user.email, PERM_DASHBOARD_VIEW, org_id,
            )
            await self.close(code=4003)
            return

        # Step 3: Verify organization access
        organization = await self._get_authorized_organization(user, org_id)
        if organization is None:
            logger.warning(
                "CentralControlConsumer.connect: rejected user=%s no access to org=%s",
                user.email, org_id,
            )
            await self.close(code=4004)
            return

        # Step 4: Store context
        self.user = user
        self.organization = organization
        self.organization_id = str(organization.pk)
        self.group_name = WS_GROUP_COMPANY.format(company_id=self.organization_id)

        # Step 5: Join group
        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name,
            )
        except Exception as exc:
            logger.error(
                "CentralControlConsumer.connect: failed to join group=%s error=%s",
                self.group_name, exc,
            )
            await self.close(code=4005)
            return

        await self.accept()

        logger.info(
            "CentralControlConsumer.connect: user=%s joined group=%s",
            user.email, self.group_name,
        )

        # Step 6: Send initial state sync
        await self._send_initial_sync()

    # -------------------------------------------------------------------------
    # disconnect
    # -------------------------------------------------------------------------

    async def disconnect(self, close_code):
        """Leave the organization group on disconnect."""
        group_name = getattr(self, "group_name", None)
        if group_name:
            try:
                await self.channel_layer.group_discard(
                    group_name,
                    self.channel_name,
                )
            except Exception as exc:
                logger.error(
                    "CentralControlConsumer.disconnect: error leaving group=%s error=%s",
                    group_name, exc,
                )
            logger.info(
                "CentralControlConsumer.disconnect: user=%s left group=%s code=%s",
                getattr(self, "user", {}).email if hasattr(self, "user") else "?",
                group_name,
                close_code,
            )

    # -------------------------------------------------------------------------
    # receive (client → server)
    # -------------------------------------------------------------------------

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle messages from the Central Control client.
        Supports: ping/pong, sync request.
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
            await self._send_initial_sync()
        else:
            logger.debug(
                "CentralControlConsumer.receive: unknown type=%s from user=%s",
                msg_type,
                getattr(self, "user", {}).email if hasattr(self, "user") else "?",
            )

    # -------------------------------------------------------------------------
    # central_event — group message handler
    # -------------------------------------------------------------------------

    async def central_event(self, event):
        """
        Forward a central control event from the channel group to the WebSocket client.

        Called by Django Channels when channel_layer.group_send() is called with
        {"type": "central_event", "payload": {...}}.
        """
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps({
            "type": "central.event",
            "payload": payload,
        }))

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    async def _get_authenticated_user(self):
        """
        Extract and validate JWT from query string or scope user.
        Returns the User instance or None.

        Follows the exact same pattern as KitchenConsumer._get_authenticated_user().
        """
        query_string = self.scope.get("query_string", b"").decode("utf-8")
        token_str = None
        for part in query_string.split("&"):
            if part.startswith("token="):
                token_str = part[6:]
                break

        # Fall back to AuthMiddlewareStack scope user
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
            logger.warning(
                "CentralControlConsumer._get_authenticated_user: JWT error=%s", exc
            )
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
    def _get_authorized_organization(self, user, org_id: str):
        """
        Return Organization if user is authorized to access it, else None.
        Always validates server-side — never trusts client-supplied org_id.
        """
        from accounts import access as acl
        from organizations.models import Organization

        if not org_id:
            return None

        try:
            org = Organization.objects.get(pk=org_id)
        except (Organization.DoesNotExist, Exception):
            return None

        if not acl.can_access_organization(user, org):
            return None

        return org

    async def _send_initial_sync(self):
        """
        Send current alert/issue/health summary to the client on connect or resync request.
        This reconciles any events missed during a disconnection.
        """
        try:
            sync_data = await database_sync_to_async(self._build_sync_payload)()
            await self.send(text_data=json.dumps({
                "type": "central.sync",
                "organization_id": self.organization_id,
                **sync_data,
            }))
        except Exception as exc:
            logger.error(
                "CentralControlConsumer._send_initial_sync: error=%s org=%s",
                exc, getattr(self, "organization_id", "?"),
            )

    def _build_sync_payload(self) -> dict:
        """
        Build a minimal sync payload: active alert counts, active issue counts,
        overall health. Intentionally lightweight — not the full detail lists.
        """
        from central_control.models import CentralAlert, CentralIssue
        from central_control.constants import (
            ALERT_ACTIVE_STATUSES, ISSUE_ACTIVE_STATUSES,
            SEVERITY_CRITICAL, SEVERITY_HIGH,
        )
        from django.db.models import Count

        org = self.organization

        # Alert summary
        alert_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for row in CentralAlert.objects.filter(
            organization=org,
            status__in=list(ALERT_ACTIVE_STATUSES),
        ).values("severity").annotate(c=Count("id")):
            k = row["severity"].lower()
            if k in alert_counts:
                alert_counts[k] = row["c"]

        # Issue summary
        issue_open = CentralIssue.objects.filter(
            organization=org,
            status__in=list(ISSUE_ACTIVE_STATUSES),
        ).count()

        issue_critical = CentralIssue.objects.filter(
            organization=org,
            status__in=list(ISSUE_ACTIVE_STATUSES),
            severity=SEVERITY_CRITICAL,
        ).count()

        return {
            "alerts": alert_counts,
            "issues": {"open": issue_open, "critical": issue_critical},
        }

    async def _send_error(self, code: str, message: str):
        """Send an error message to the client."""
        await self.send(text_data=json.dumps({
            "type": "error",
            "code": code,
            "message": message,
        }))
