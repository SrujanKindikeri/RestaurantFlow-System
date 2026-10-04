# =============================================================================
# RestaurantFlow — Notification Preference Tests
# Phase 16
# =============================================================================

from notifications.tests.base import NotificationTestBase
from notifications.models import NotificationPreference
from notifications.selectors import is_channel_enabled_for_user, get_user_preferences
from notifications.constants import (
    CHANNEL_IN_APP, CHANNEL_EMAIL, CHANNEL_SMS,
    NOTIF_PAYMENT_FAILED, NOTIF_INVENTORY_LOW_STOCK,
    NOTIF_CENTRAL_ALERT_CREATED,
)


class NotificationPreferenceTests(NotificationTestBase):

    def test_default_in_app_enabled_for_payment_failed(self):
        """Without explicit preference, in-app should be enabled by default."""
        enabled = is_channel_enabled_for_user(
            self.user_a, NOTIF_PAYMENT_FAILED, CHANNEL_IN_APP
        )
        self.assertTrue(enabled)

    def test_default_sms_disabled(self):
        """SMS is off by default for most notification types."""
        enabled = is_channel_enabled_for_user(
            self.user_a, NOTIF_INVENTORY_LOW_STOCK, CHANNEL_SMS
        )
        self.assertFalse(enabled)

    def test_explicit_preference_overrides_default(self):
        """Setting enabled=False for in-app should disable it."""
        NotificationPreference.objects.create(
            user=self.user_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            channel=CHANNEL_IN_APP,
            enabled=False,
        )
        enabled = is_channel_enabled_for_user(
            self.user_a, NOTIF_PAYMENT_FAILED, CHANNEL_IN_APP
        )
        self.assertFalse(enabled)

    def test_explicit_preference_enable_email(self):
        """Explicitly enabling email overrides the default (which is off for some types)."""
        NotificationPreference.objects.create(
            user=self.user_a,
            notification_type=NOTIF_INVENTORY_LOW_STOCK,
            channel=CHANNEL_EMAIL,
            enabled=True,
        )
        enabled = is_channel_enabled_for_user(
            self.user_a, NOTIF_INVENTORY_LOW_STOCK, CHANNEL_EMAIL
        )
        self.assertTrue(enabled)

    def test_preference_uniqueness_per_user_type_channel(self):
        """Duplicate (user, type, channel) combination is rejected at DB level."""
        from django.db import IntegrityError
        NotificationPreference.objects.create(
            user=self.user_a,
            notification_type=NOTIF_PAYMENT_FAILED,
            channel=CHANNEL_IN_APP,
            enabled=True,
        )
        with self.assertRaises(IntegrityError):
            NotificationPreference.objects.create(
                user=self.user_a,
                notification_type=NOTIF_PAYMENT_FAILED,
                channel=CHANNEL_IN_APP,
                enabled=False,
            )

    def test_get_user_preferences_returns_only_this_user(self):
        NotificationPreference.objects.create(
            user=self.user_a, notification_type=NOTIF_PAYMENT_FAILED,
            channel=CHANNEL_IN_APP, enabled=True,
        )
        NotificationPreference.objects.create(
            user=self.user_b, notification_type=NOTIF_PAYMENT_FAILED,
            channel=CHANNEL_IN_APP, enabled=False,
        )
        prefs_a = get_user_preferences(self.user_a)
        for pref in prefs_a:
            self.assertEqual(pref.user, self.user_a)

    def test_update_or_create_preference_via_api(self):
        from django.test import RequestFactory
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        resp = client.post(
            "/api/notifications/preferences/",
            {
                "notification_type": NOTIF_PAYMENT_FAILED,
                "channel": CHANNEL_EMAIL,
                "enabled": True,
            },
            format="json",
        )
        self.assertIn(resp.status_code, [200, 201])
        self.assertTrue(
            NotificationPreference.objects.filter(
                user=self.user_a,
                notification_type=NOTIF_PAYMENT_FAILED,
                channel=CHANNEL_EMAIL,
                enabled=True,
            ).exists()
        )

    def test_critical_notifications_always_have_in_app_default(self):
        """Critical notification types should have in-app enabled by default."""
        from notifications.constants import (
            NOTIF_CENTRAL_ALERT_CREATED, NOTIF_ACCOUNTING_POSTING_FAILED,
            DEFAULT_CHANNEL_PREFS,
        )
        for ntype in [NOTIF_CENTRAL_ALERT_CREATED, NOTIF_ACCOUNTING_POSTING_FAILED]:
            prefs = DEFAULT_CHANNEL_PREFS.get(ntype, {})
            self.assertTrue(prefs.get(CHANNEL_IN_APP, False), f"IN_APP should be True for {ntype}")
