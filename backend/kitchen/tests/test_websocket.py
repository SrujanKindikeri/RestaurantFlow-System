# =============================================================================
# RestaurantFlow — Kitchen WebSocket Tests
# Phase 7
#
# Tests:
#   - authenticated connection accepted
#   - unauthenticated connection rejected (close code 4001)
#   - user without kitchen.view rejected (close code 4003)
#   - user from different branch rejected (close code 4004)
#   - initial sync message sent on connect
#   - kitchen.order.created event delivered to group
#   - kitchen.order.accepted event delivered
#   - branch isolation: Branch A events not received by Branch B consumer
#   - reconnect sync delivers current state
#   - ping/pong heartbeat works
#
# Uses Django Channels test helpers (WebsocketCommunicator).
# Note: These tests require channels[daphne] and an in-memory layer.
# =============================================================================

from decimal import Decimal
from unittest.mock import patch, AsyncMock

from django.test import TestCase, override_settings
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch
from kitchen.models import KitchenOrderStatus
from kitchen.services import send_order_to_kitchen
from kitchen.consumers import KitchenConsumer
from kitchen.routing import websocket_urlpatterns

from kitchen.tests.test_kitchen import KitchenTestBase

# Use in-memory channel layer for tests
TEST_CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}


def _get_jwt_token(user):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(user)
    return str(refresh.access_token)


@override_settings(CHANNEL_LAYERS=TEST_CHANNEL_LAYERS)
class TestKitchenWebSocket(KitchenTestBase):

    async def _connect(self, branch_id, token):
        """Helper: create a communicator for the kitchen WS endpoint."""
        from channels.routing import URLRouter
        application = URLRouter(websocket_urlpatterns)
        url = f"/ws/kitchen/{branch_id}/?token={token}"
        communicator = WebsocketCommunicator(application, url)
        return communicator

    async def test_authenticated_connection_accepted(self):
        token = _get_jwt_token(self.kitchen_user)
        communicator = await self._connect(str(self.branch.id), token)
        connected, code = await communicator.connect()
        self.assertTrue(connected)
        # Initial sync message received
        msg = await communicator.receive_json_from()
        self.assertEqual(msg["type"], "kitchen.sync")
        await communicator.disconnect()

    async def test_unauthenticated_connection_rejected(self):
        communicator = await self._connect(str(self.branch.id), "invalid-token-xyz")
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4001)

    async def test_no_token_rejected(self):
        from channels.routing import URLRouter
        application = URLRouter(websocket_urlpatterns)
        url = f"/ws/kitchen/{self.branch.id}/"
        communicator = WebsocketCommunicator(application, url)
        connected, code = await communicator.connect()
        self.assertFalse(connected)

    async def test_user_without_kitchen_view_rejected(self):
        """other_user has no kitchen.view — should be rejected with 4003."""
        token = _get_jwt_token(self.other_user)
        communicator = await self._connect(str(self.branch.id), token)
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4003)

    async def test_wrong_branch_rejected(self):
        """kitchen_user from branch A cannot connect to branch B's KDS."""
        # kitchen_user has access only to self.branch, not branch2
        from asgiref.sync import sync_to_async

        org2 = await sync_to_async(Organization.objects.create)(name="Org2WS", slug="org2-ws")
        rest2 = await sync_to_async(Restaurant.objects.create)(
            organization=org2, name="Rest2WS", slug="rest2-ws"
        )
        branch2 = await sync_to_async(Branch.objects.create)(
            restaurant=rest2, name="Branch2WS", slug="branch2-ws"
        )

        token = _get_jwt_token(self.kitchen_user)
        communicator = await self._connect(str(branch2.id), token)
        connected, code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(code, 4004)

    async def test_initial_sync_contains_orders(self):
        """On connect, the consumer sends current kitchen state."""
        from asgiref.sync import sync_to_async

        order = await sync_to_async(self._make_confirmed_order)()
        await sync_to_async(send_order_to_kitchen)(order)

        token = _get_jwt_token(self.kitchen_user)
        communicator = await self._connect(str(self.branch.id), token)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        msg = await communicator.receive_json_from()
        self.assertEqual(msg["type"], "kitchen.sync")
        self.assertIn("orders", msg)
        self.assertIsInstance(msg["orders"], list)
        await communicator.disconnect()

    async def test_ping_pong(self):
        """Consumer responds to ping with pong."""
        token = _get_jwt_token(self.kitchen_user)
        communicator = await self._connect(str(self.branch.id), token)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume the initial sync
        await communicator.receive_json_from()

        await communicator.send_json_to({"type": "ping"})
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "pong")
        await communicator.disconnect()

    async def test_kitchen_event_delivered_to_group(self):
        """
        An event published to the kitchen_{branch_id} group must be
        received by the connected consumer.
        """
        from asgiref.sync import sync_to_async

        token = _get_jwt_token(self.kitchen_user)
        communicator = await self._connect(str(self.branch.id), token)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume the initial sync
        await communicator.receive_json_from()

        # Publish an event via channel layer
        channel_layer = get_channel_layer()
        group_name = f"kitchen_{self.branch.id}"
        await channel_layer.group_send(
            group_name,
            {
                "type": "kitchen.event",
                "payload": {
                    "event": "kitchen.order.created",
                    "order_number": "C01-TEST-0001",
                    "status": "NEW",
                },
            },
        )

        msg = await communicator.receive_json_from()
        self.assertEqual(msg["type"], "kitchen.event")
        self.assertEqual(msg["payload"]["event"], "kitchen.order.created")
        await communicator.disconnect()

    async def test_branch_isolation_branch_a_cannot_receive_branch_b_events(self):
        """
        A consumer subscribed to branch A must NOT receive events for branch B.
        """
        from asgiref.sync import sync_to_async

        org2 = await sync_to_async(Organization.objects.create)(name="OrgIso", slug="org-iso")
        rest2 = await sync_to_async(Restaurant.objects.create)(
            organization=org2, name="RestIso", slug="rest-iso"
        )
        branch2 = await sync_to_async(Branch.objects.create)(
            restaurant=rest2, name="BranchIso", slug="branch-iso"
        )

        token = _get_jwt_token(self.kitchen_user)
        communicator = await self._connect(str(self.branch.id), token)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        # Consume initial sync
        await communicator.receive_json_from()

        # Send event to branch2 group — should NOT arrive on branch1 consumer
        channel_layer = get_channel_layer()
        group_name_b2 = f"kitchen_{branch2.id}"
        await channel_layer.group_send(
            group_name_b2,
            {
                "type": "kitchen.event",
                "payload": {
                    "event": "kitchen.order.created",
                    "order_number": "BRANCH-B-ORDER",
                },
            },
        )

        # Consumer should not receive any message (timeout)
        with self.assertRaises(Exception):
            await communicator.receive_json_from(timeout=0.1)

        await communicator.disconnect()

    async def test_sync_request_delivers_current_state(self):
        """Client can send {type: sync} to request a fresh state dump."""
        token = _get_jwt_token(self.kitchen_user)
        communicator = await self._connect(str(self.branch.id), token)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume initial sync
        await communicator.receive_json_from()

        # Request manual sync
        await communicator.send_json_to({"type": "sync"})
        msg = await communicator.receive_json_from()
        self.assertEqual(msg["type"], "kitchen.sync")
        self.assertIn("orders", msg)
        await communicator.disconnect()

    async def test_event_payload_has_no_financial_data(self):
        """Event payloads must not contain price, tax, cash, discount fields."""
        token = _get_jwt_token(self.kitchen_user)
        communicator = await self._connect(str(self.branch.id), token)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_json_from()

        channel_layer = get_channel_layer()
        group_name = f"kitchen_{self.branch.id}"
        await channel_layer.group_send(
            group_name,
            {
                "type": "kitchen.event",
                "payload": {
                    "event": "kitchen.order.ready",
                    "order_number": "D-TEST-001",
                    "status": "READY",
                },
            },
        )
        msg = await communicator.receive_json_from()
        payload = msg["payload"]

        # Must not expose financial data
        financial_keys = {
            "unit_price", "unit_price_snapshot", "tax_rate", "tax_rate_snapshot",
            "tax_code", "line_total", "cash_amount", "discount", "profit",
            "opening_cash", "actual_cash", "expected_cash",
        }
        for key in financial_keys:
            self.assertNotIn(key, payload, f"Financial key '{key}' found in event payload")

        await communicator.disconnect()
