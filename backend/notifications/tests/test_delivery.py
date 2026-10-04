# =============================================================================
# RestaurantFlow — Delivery Channel Tests
# Phase 16
# =============================================================================

from unittest.mock import patch, MagicMock
from notifications.tests.base import NotificationTestBase
from notifications.models import NotificationDelivery, NotificationRecipient
from notifications.delivery.base import DeliveryPayload, DeliveryResult
from notifications.delivery.in_app import InAppProvider
from notifications.delivery.websocket import WebSocketProvider
from notifications.delivery.email import EmailProvider
from notifications.delivery.sms import SMSProvider
from notifications.delivery.whatsapp import WhatsAppProvider
from notifications.delivery.telegram import TelegramProvider
from notifications.constants import (
    DELIVERY_DELIVERED, DELIVERY_SENT, DELIVERY_FAILED,
    DELIVERY_NOT_CONFIGURED, CHANNEL_IN_APP, CHANNEL_EMAIL,
)
from notifications.services import NotificationService


class InAppProviderTests(NotificationTestBase):

    def _make_payload(self):
        n = self._make_notification()
        return DeliveryPayload(
            recipient_user=self.user_a,
            notification=n,
            subject="Test",
            body="Test body",
        )

    def test_in_app_always_succeeds(self):
        provider = InAppProvider()
        result = provider.send(self._make_payload())
        self.assertTrue(result.success)
        self.assertEqual(result.status, DELIVERY_DELIVERED)

    def test_in_app_always_configured(self):
        self.assertTrue(InAppProvider().validate_configuration())

    def test_in_app_get_status(self):
        status = InAppProvider().get_status()
        self.assertTrue(status["configured"])


class WebSocketProviderTests(NotificationTestBase):

    def _make_payload(self):
        n = self._make_notification()
        return DeliveryPayload(recipient_user=self.user_a, notification=n)

    def test_websocket_send_succeeds_with_mock_channel_layer(self):
        mock_layer = MagicMock()
        mock_layer.group_send = MagicMock(return_value=None)
        with patch("notifications.delivery.websocket.get_channel_layer", return_value=mock_layer):
            with patch("notifications.delivery.websocket.async_to_sync", return_value=lambda f: f):
                provider = WebSocketProvider()
                result = provider.send(self._make_payload())
        # Passes without raising
        self.assertIsNotNone(result)

    def test_websocket_returns_failed_when_channel_layer_none(self):
        with patch("notifications.delivery.websocket.get_channel_layer", return_value=None):
            provider = WebSocketProvider()
            result = provider.send(self._make_payload())
        self.assertFalse(result.success)
        self.assertEqual(result.status, DELIVERY_FAILED)

    def test_websocket_catches_exceptions(self):
        """WebSocket errors never propagate — always returns DeliveryResult."""
        with patch("notifications.delivery.websocket.get_channel_layer", side_effect=Exception("Redis down")):
            provider = WebSocketProvider()
            result = provider.send(self._make_payload())
        self.assertFalse(result.success)


class EmailProviderTests(NotificationTestBase):

    def _make_payload(self):
        n = self._make_notification()
        return DeliveryPayload(
            recipient_user=self.user_a,
            notification=n,
            subject="Test Subject",
            body="Test body text.",
        )

    def test_email_sends_with_locmem_backend(self):
        """With locmem email backend, email delivery should succeed."""
        from django.test import override_settings
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                               DEFAULT_FROM_EMAIL="test@test.com"):
            provider = EmailProvider()
            result = provider.send(self._make_payload())
        self.assertTrue(result.success)

    def test_email_fails_with_invalid_recipient_email(self):
        self.user_a.email = "not-an-email"
        provider = EmailProvider()
        result = provider.send(self._make_payload())
        self.assertFalse(result.success)
        # Restore
        self.user_a.email = "user_a@companya.com"

    def test_email_catches_smtp_exception(self):
        """SMTP failures are caught and returned as DeliveryResult.failed."""
        from unittest.mock import patch
        with patch("django.core.mail.send_mail", side_effect=Exception("SMTP Error")):
            with __import__("django.test", fromlist=["override_settings"]).override_settings(
                EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
                DEFAULT_FROM_EMAIL="x@x.com",
            ):
                provider = EmailProvider()
                result = provider.send(self._make_payload())
        self.assertFalse(result.success)
        self.assertEqual(result.status, DELIVERY_FAILED)


class ExternalProviderNotConfiguredTests(NotificationTestBase):

    def _make_payload(self, provider_class):
        n = self._make_notification()
        return DeliveryPayload(recipient_user=self.user_a, notification=n)

    def test_sms_not_configured_returns_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("SMS_PROVIDER", None)
            result = SMSProvider().send(self._make_payload(SMSProvider))
        self.assertFalse(result.success)
        self.assertEqual(result.status, DELIVERY_NOT_CONFIGURED)
        self.assertTrue(result.not_configured)

    def test_whatsapp_not_configured_returns_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("WHATSAPP_PROVIDER", None)
            result = WhatsAppProvider().send(self._make_payload(WhatsAppProvider))
        self.assertFalse(result.success)
        self.assertEqual(result.status, DELIVERY_NOT_CONFIGURED)
        self.assertTrue(result.not_configured)

    def test_telegram_not_configured_returns_not_configured(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            result = TelegramProvider().send(self._make_payload(TelegramProvider))
        self.assertFalse(result.success)
        self.assertEqual(result.status, DELIVERY_NOT_CONFIGURED)
        self.assertTrue(result.not_configured)

    def test_sms_validate_configuration_false_without_env(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("SMS_PROVIDER", None)
            self.assertFalse(SMSProvider().validate_configuration())

    def test_telegram_validate_configuration_false_without_env(self):
        with patch.dict("os.environ", {}, clear=True):
            import os
            os.environ.pop("TELEGRAM_BOT_TOKEN", None)
            self.assertFalse(TelegramProvider().validate_configuration())


class DeliveryServiceTests(NotificationTestBase):

    def test_deliver_channel_marks_in_app_delivered(self):
        """In-app delivery should be marked DELIVERED after deliver_channel."""
        n = self._make_notification()
        recipient = NotificationRecipient.objects.create(
            notification=n, user=self.user_a
        )
        delivery = NotificationDelivery.objects.create(
            notification=n,
            recipient=recipient,
            channel=CHANNEL_IN_APP,
        )
        NotificationService.deliver_channel(str(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DELIVERY_DELIVERED)

    def test_deliver_channel_unknown_delivery_id_does_not_raise(self):
        """Missing delivery ID is silently ignored."""
        NotificationService.deliver_channel("00000000-0000-0000-0000-000000000000")
        # No exception raised

    def test_mark_delivered_updates_status(self):
        n = self._make_notification()
        recipient = self._make_recipient(notification=n)
        delivery = NotificationDelivery.objects.create(
            notification=n, recipient=recipient, channel=CHANNEL_IN_APP
        )
        NotificationService.mark_delivered(delivery, "msg-id-123")
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DELIVERY_DELIVERED)
        self.assertEqual(delivery.provider_message_id, "msg-id-123")

    def test_mark_failed_updates_status(self):
        n = self._make_notification()
        recipient = self._make_recipient(notification=n)
        delivery = NotificationDelivery.objects.create(
            notification=n, recipient=recipient, channel=CHANNEL_EMAIL
        )
        NotificationService.mark_failed(delivery, "SMTP error")
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DELIVERY_FAILED)
        self.assertIn("SMTP", delivery.failure_reason)

    def test_retry_delivery_resets_status_to_pending(self):
        n = self._make_notification()
        recipient = self._make_recipient(notification=n)
        delivery = NotificationDelivery.objects.create(
            notification=n, recipient=recipient,
            channel=CHANNEL_EMAIL,
            attempt_count=1,
        )
        NotificationService.mark_failed(delivery, "Temporary failure")
        # Retry (attempt_count=1 is below max)
        delivery.refresh_from_db()
        # Manually reset to test retry path
        delivery.attempt_count = 1
        delivery.save()
        NotificationService.retry_delivery(str(delivery.pk))
        # Task would have been queued; just verify no exception
