# =============================================================================
# RestaurantFlow — WebSocket / Real-time Delivery Tests
# Phase 16
# =============================================================================

from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase, override_settings

from notifications.tests.base import NotificationTestBase


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class WebSocketGroupNameTests(NotificationTestBase):

    def test_ws_group_name_format(self):
        from notifications.constants import WS_GROUP_USER
        group = WS_GROUP_USER.format(user_id=str(self.user_a.pk))
        self.assertEqual(group, f"notifications_user_{self.user_a.pk}")

    def test_ws_group_unique_per_user(self):
        from notifications.constants import WS_GROUP_USER
        group_a = WS_GROUP_USER.format(user_id=str(self.user_a.pk))
        group_b = WS_GROUP_USER.format(user_id=str(self.user_b.pk))
        self.assertNotEqual(group_a, group_b)


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class WebSocketProviderDeliveryTests(NotificationTestBase):

    def test_ws_send_calls_group_send_with_correct_group(self):
        from notifications.delivery.websocket import WebSocketProvider
        from notifications.delivery.base import DeliveryPayload
        from notifications.constants import WS_GROUP_USER

        n = self._make_notification()
        payload = DeliveryPayload(recipient_user=self.user_a, notification=n)

        mock_layer = MagicMock()
        group_send_calls = []

        def fake_group_send(group, msg):
            group_send_calls.append((group, msg))

        with patch("notifications.delivery.websocket.get_channel_layer", return_value=mock_layer):
            with patch("notifications.delivery.websocket.async_to_sync", return_value=lambda f: fake_group_send):
                WebSocketProvider().send(payload)

        expected_group = WS_GROUP_USER.format(user_id=str(self.user_a.pk))
        self.assertTrue(any(g == expected_group for g, _ in group_send_calls))

    def test_ws_send_does_not_send_to_other_user_group(self):
        """WebSocket delivery only targets the recipient's own group."""
        from notifications.delivery.websocket import WebSocketProvider
        from notifications.delivery.base import DeliveryPayload
        from notifications.constants import WS_GROUP_USER

        n = self._make_notification()
        payload = DeliveryPayload(recipient_user=self.user_a, notification=n)

        mock_layer = MagicMock()
        group_send_calls = []

        def fake_group_send(group, msg):
            group_send_calls.append((group, msg))

        with patch("notifications.delivery.websocket.get_channel_layer", return_value=mock_layer):
            with patch("notifications.delivery.websocket.async_to_sync", return_value=lambda f: fake_group_send):
                WebSocketProvider().send(payload)

        wrong_group = WS_GROUP_USER.format(user_id=str(self.user_b.pk))
        self.assertFalse(any(g == wrong_group for g, _ in group_send_calls))

    def test_ws_payload_does_not_include_sensitive_data(self):
        """WebSocket event payload must not include sensitive fields."""
        from notifications.delivery.websocket import WebSocketProvider
        from notifications.delivery.base import DeliveryPayload

        n = self._make_notification(metadata={"secret_key": "should_not_appear"})
        payload = DeliveryPayload(recipient_user=self.user_a, notification=n)

        sent_payloads = []

        def fake_group_send(group, msg):
            sent_payloads.append(msg)

        mock_layer = MagicMock()
        with patch("notifications.delivery.websocket.get_channel_layer", return_value=mock_layer):
            with patch("notifications.delivery.websocket.async_to_sync", return_value=lambda f: fake_group_send):
                WebSocketProvider().send(payload)

        if sent_payloads:
            payload_data = sent_payloads[0].get("payload", {})
            # Must not expose full metadata, DB fields, or secrets
            self.assertNotIn("metadata", payload_data)
            self.assertNotIn("secret_key", str(payload_data))


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class NotificationsConsumerAuthTests(NotificationTestBase):

    def test_consumer_imports_successfully(self):
        from notifications.consumers import NotificationsConsumer
        self.assertIsNotNone(NotificationsConsumer)

    def test_consumer_routing_registered(self):
        from notifications.routing import websocket_urlpatterns
        paths = [str(p.pattern) for p in websocket_urlpatterns]
        self.assertTrue(any("notifications" in p for p in paths))

    def test_ws_read_push_does_not_raise_when_redis_unavailable(self):
        """_push_ws_read_event must never raise even if Redis/Channels is down."""
        with patch("notifications.services.get_channel_layer", side_effect=Exception("Redis down")):
            # Should not raise
            NotificationService = __import__(
                "notifications.services", fromlist=["NotificationService"]
            ).NotificationService
            NotificationService._push_ws_read_event(self.user_a, "fake-notification-id")
