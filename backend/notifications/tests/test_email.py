# =============================================================================
# RestaurantFlow — Email Delivery Tests
# Phase 16
# =============================================================================

from unittest.mock import patch
from django.test import override_settings
from django.core import mail

from notifications.tests.base import NotificationTestBase
from notifications.delivery.email import EmailProvider
from notifications.delivery.base import DeliveryPayload
from notifications.constants import DELIVERY_SENT, DELIVERY_FAILED


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="test@restaurantflow.app",
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class EmailProviderTests(NotificationTestBase):

    def setUp(self):
        mail.outbox = []  # Clear locmem outbox

    def _make_payload(self, subject="Test Subject", body="Test body."):
        n = self._make_notification()
        return DeliveryPayload(
            recipient_user=self.user_a,
            notification=n,
            subject=subject,
            body=body,
        )

    def test_email_sent_to_correct_recipient(self):
        provider = EmailProvider()
        result = provider.send(self._make_payload())
        self.assertTrue(result.success)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user_a.email, mail.outbox[0].to)

    def test_email_has_correct_subject(self):
        provider = EmailProvider()
        provider.send(self._make_payload(subject="Payment Failed Alert"))
        self.assertEqual(mail.outbox[0].subject, "Payment Failed Alert")

    def test_email_has_correct_body(self):
        provider = EmailProvider()
        provider.send(self._make_payload(body="Your payment of 500 failed."))
        self.assertIn("Your payment of 500 failed.", mail.outbox[0].body)

    def test_email_uses_default_from_email(self):
        provider = EmailProvider()
        provider.send(self._make_payload())
        self.assertEqual(mail.outbox[0].from_email, "test@restaurantflow.app")

    def test_email_fails_gracefully_on_smtp_error(self):
        with patch("notifications.delivery.email.send_mail", side_effect=Exception("SMTP fail")):
            provider = EmailProvider()
            result = provider.send(self._make_payload())
        self.assertFalse(result.success)
        self.assertEqual(result.status, DELIVERY_FAILED)
        self.assertIn("SMTP", result.failure_reason)

    def test_email_rejected_for_invalid_address(self):
        """Invalid email address should fail before attempting send."""
        original = self.user_a.email
        self.user_a.email = "not-an-email-address"
        provider = EmailProvider()
        result = provider.send(self._make_payload())
        self.assertFalse(result.success)
        self.assertEqual(result.status, DELIVERY_FAILED)
        self.user_a.email = original

    def test_email_not_sent_twice_for_same_delivery(self):
        """Delivering twice should not result in two emails (idempotency check at service level)."""
        from notifications.models import NotificationDelivery, NotificationRecipient
        from notifications.services import NotificationService
        from notifications.constants import CHANNEL_EMAIL

        n = self._make_notification(source_id="email-idem-001")
        recipient = NotificationRecipient.objects.create(notification=n, user=self.user_a)
        delivery = NotificationDelivery.objects.create(
            notification=n, recipient=recipient, channel=CHANNEL_EMAIL
        )
        # Deliver once
        NotificationService.deliver_channel(str(delivery.pk))
        first_count = len(mail.outbox)
        # Second call — delivery is now SENT/DELIVERED, should be noop
        NotificationService.deliver_channel(str(delivery.pk))
        second_count = len(mail.outbox)
        self.assertEqual(first_count, second_count)
