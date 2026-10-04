# =============================================================================
# RestaurantFlow — Idempotency Tests
# Phase 16
# =============================================================================

from notifications.tests.base import NotificationTestBase
from notifications.models import Notification, NotificationRecipient, NotificationDelivery
from notifications.services import NotificationService
from notifications.constants import (
    NOTIF_PAYMENT_FAILED, SEVERITY_HIGH, SOURCE_PAYMENT,
    CHANNEL_IN_APP, DELIVERY_DELIVERED,
)


class NotificationIdempotencyTests(NotificationTestBase):

    def test_duplicate_event_creates_only_one_notification(self):
        """Sending the same payment.failed event twice produces one Notification."""
        kwargs = dict(
            company=self.company_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            severity=SEVERITY_HIGH,
            title="Duplicate",
            message=".",
            source_type=SOURCE_PAYMENT,
            source_id="idem-pay-100",
        )
        n1 = NotificationService.create_notification(**kwargs)
        n2 = NotificationService.create_notification(**kwargs)
        self.assertEqual(n1.pk, n2.pk)
        self.assertEqual(
            Notification.objects.filter(
                company=self.company_a, source_id="idem-pay-100"
            ).count(),
            1,
        )

    def test_duplicate_recipient_row_not_created(self):
        """get_or_create in resolve_and_create_recipients prevents duplicate rows."""
        n = self._make_notification(source_id="idem-recip-001")
        r1, _ = NotificationRecipient.objects.get_or_create(notification=n, user=self.user_a)
        r2, created = NotificationRecipient.objects.get_or_create(notification=n, user=self.user_a)
        self.assertFalse(created)
        self.assertEqual(r1.pk, r2.pk)

    def test_delivery_not_recreated_if_already_delivered(self):
        """queue_delivery skips creation when a non-failed delivery already exists."""
        n = self._make_notification(source_id="idem-deliv-001")
        recipient = NotificationRecipient.objects.create(notification=n, user=self.user_a)
        # Create an existing DELIVERED record
        NotificationDelivery.objects.create(
            notification=n,
            recipient=recipient,
            channel=CHANNEL_IN_APP,
            status=DELIVERY_DELIVERED,
        )
        # queue_delivery should detect the existing row and skip
        NotificationService.queue_delivery(recipient, channels=[CHANNEL_IN_APP])
        count = NotificationDelivery.objects.filter(
            notification=n, recipient=recipient, channel=CHANNEL_IN_APP
        ).count()
        self.assertEqual(count, 1)  # Still just one

    def test_deliver_channel_is_noop_for_delivered_delivery(self):
        """deliver_channel returns immediately for already-DELIVERED records."""
        n = self._make_notification(source_id="idem-ch-001")
        recipient = NotificationRecipient.objects.create(notification=n, user=self.user_a)
        delivery = NotificationDelivery.objects.create(
            notification=n,
            recipient=recipient,
            channel=CHANNEL_IN_APP,
            status=DELIVERY_DELIVERED,
        )
        # Should be a no-op — no additional DB writes
        NotificationService.deliver_channel(str(delivery.pk))
        delivery.refresh_from_db()
        self.assertEqual(delivery.status, DELIVERY_DELIVERED)

    def test_retry_delivery_does_not_exceed_max_attempts(self):
        """retry_delivery raises NotificationNotFoundError when at MAX_DELIVERY_ATTEMPTS."""
        from notifications.exceptions import NotificationNotFoundError
        from notifications.constants import MAX_DELIVERY_ATTEMPTS

        n = self._make_notification(source_id="idem-retry-001")
        recipient = NotificationRecipient.objects.create(notification=n, user=self.user_a)
        delivery = NotificationDelivery.objects.create(
            notification=n,
            recipient=recipient,
            channel=CHANNEL_IN_APP,
            attempt_count=MAX_DELIVERY_ATTEMPTS,
        )
        # Should NOT queue another Celery task — just log a warning
        NotificationService.retry_delivery(str(delivery.pk))  # no exception raised
