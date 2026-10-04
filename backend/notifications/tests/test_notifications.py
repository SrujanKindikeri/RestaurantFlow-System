# =============================================================================
# RestaurantFlow — Notification Creation Tests
# Phase 16
# =============================================================================

from unittest.mock import patch
from django.test import override_settings

from notifications.tests.base import NotificationTestBase
from notifications.services import NotificationService, create_and_dispatch
from notifications.models import Notification, NotificationRecipient
from notifications.constants import (
    NOTIF_PAYMENT_FAILED, SEVERITY_HIGH, SOURCE_PAYMENT,
    NOTIF_INVENTORY_LOW_STOCK, SEVERITY_MEDIUM, SOURCE_STOCK_BALANCE,
)


class NotificationCreationTests(NotificationTestBase):

    def test_create_notification_returns_instance(self):
        """Basic notification creation succeeds and returns a Notification."""
        n = NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            severity=SEVERITY_HIGH,
            title="Payment Failed",
            message="Test payment failure.",
            source_type=SOURCE_PAYMENT,
            source_id="pay-001",
        )
        self.assertIsNotNone(n)
        self.assertEqual(str(n.notification_type), NOTIF_PAYMENT_FAILED)
        self.assertEqual(n.company, self.company_a)

    def test_create_notification_persists_to_database(self):
        n = NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            severity=SEVERITY_HIGH,
            title="DB Persist Test",
            message="Should be in DB.",
            source_type=SOURCE_PAYMENT,
            source_id="pay-db-001",
        )
        self.assertTrue(Notification.objects.filter(pk=n.pk).exists())

    def test_notification_has_correct_company_scope(self):
        n = self._make_notification(company=self.company_a)
        self.assertEqual(n.company, self.company_a)

    def test_notification_has_correct_restaurant_scope(self):
        n = self._make_notification(
            company=self.company_a,
            restaurant=self.restaurant_a,
        )
        self.assertEqual(n.restaurant, self.restaurant_a)

    def test_notification_has_correct_branch_scope(self):
        n = self._make_notification(
            company=self.company_a,
            restaurant=self.restaurant_a,
            branch=self.branch_a,
        )
        self.assertEqual(n.branch, self.branch_a)

    def test_idempotency_same_source_id_returns_existing(self):
        """Creating twice with same (company, type, source_type, source_id) returns existing."""
        n1 = NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            severity=SEVERITY_HIGH,
            title="Idempotent",
            message="First.",
            source_type=SOURCE_PAYMENT,
            source_id="idem-001",
        )
        n2 = NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            severity=SEVERITY_HIGH,
            title="Idempotent Duplicate",
            message="Second — should not create.",
            source_type=SOURCE_PAYMENT,
            source_id="idem-001",
        )
        self.assertEqual(n1.pk, n2.pk)
        total = Notification.objects.filter(
            company=self.company_a, source_id="idem-001"
        ).count()
        self.assertEqual(total, 1)

    def test_different_companies_same_source_id_creates_separate_notifications(self):
        n1 = NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            severity=SEVERITY_HIGH,
            title="Company A",
            message=".",
            source_type=SOURCE_PAYMENT,
            source_id="shared-001",
        )
        n2 = NotificationService.create_notification(
            company=self.company_b,
            notification_type=NOTIF_PAYMENT_FAILED,
            severity=SEVERITY_HIGH,
            title="Company B",
            message=".",
            source_type=SOURCE_PAYMENT,
            source_id="shared-001",
        )
        self.assertNotEqual(n1.pk, n2.pk)

    def test_cooldown_suppresses_low_stock_duplicate(self):
        """Low-stock notification is suppressed within the cooldown window."""
        from django.core.cache import cache
        cache.clear()

        n1 = NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_INVENTORY_LOW_STOCK,
            severity=SEVERITY_MEDIUM,
            title="Low Stock",
            message="Item X is low.",
            source_type=SOURCE_STOCK_BALANCE,
            source_id="sb-cool-001",
        )
        # Second call — same type + source — should be suppressed by cooldown
        n2 = NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_INVENTORY_LOW_STOCK,
            severity=SEVERITY_MEDIUM,
            title="Low Stock Again",
            message="Still low.",
            source_type=SOURCE_STOCK_BALANCE,
            source_id="sb-cool-002",  # different source_id to bypass idempotency
        )
        # n2 can be None (suppressed) or a new notification if source_id differs
        # The cooldown key is per notification_type+company_id, so this should be None
        self.assertIsNone(n2)

    def test_bypass_cooldown_creates_notification(self):
        from django.core.cache import cache
        cache.clear()
        # Set cooldown
        NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_INVENTORY_LOW_STOCK,
            severity=SEVERITY_MEDIUM,
            title="Low Stock",
            message=".",
            source_type=SOURCE_STOCK_BALANCE,
            source_id="byp-001",
        )
        # bypass_cooldown should force creation
        n = NotificationService.create_notification(
            company=self.company_a,
            notification_type=NOTIF_INVENTORY_LOW_STOCK,
            severity=SEVERITY_MEDIUM,
            title="Critical Override",
            message=".",
            source_type=SOURCE_STOCK_BALANCE,
            source_id="byp-002",
            bypass_cooldown=True,
        )
        self.assertIsNotNone(n)

    def test_unsafe_action_url_is_rejected(self):
        from notifications.exceptions import NotificationError
        with self.assertRaises(NotificationError):
            NotificationService.create_notification(
                company=self.company_a,
                notification_type=NOTIF_PAYMENT_FAILED,
                severity=SEVERITY_HIGH,
                title="XSS",
                message=".",
                source_type=SOURCE_PAYMENT,
                source_id="xss-001",
                action_url="javascript:alert(1)",
            )

    def test_create_and_dispatch_catches_exceptions(self):
        """create_and_dispatch never raises — returns None on error."""
        with patch(
            "notifications.services.NotificationService.create_notification",
            side_effect=Exception("Unexpected failure"),
        ):
            result = create_and_dispatch(
                company=self.company_a,
                notification_type=NOTIF_PAYMENT_FAILED,
                severity=SEVERITY_HIGH,
                title="Error Test",
                message=".",
                source_type=SOURCE_PAYMENT,
                source_id="err-001",
            )
        self.assertIsNone(result)
