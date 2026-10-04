# =============================================================================
# RestaurantFlow — Notification Permission / Security Tests
# Phase 16
# =============================================================================

from rest_framework.test import APIClient
from django.test import override_settings

from notifications.tests.base import NotificationTestBase
from notifications.models import NotificationRecipient
from notifications.constants import NOTIF_PAYMENT_FAILED, SEVERITY_HIGH, SOURCE_PAYMENT


@override_settings(
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
)
class NotificationPermissionTests(NotificationTestBase):

    def setUp(self):
        self.client = APIClient()

    def test_unauthenticated_user_cannot_list_notifications(self):
        resp = self.client.get("/api/notifications/")
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_user_cannot_get_unread_count(self):
        resp = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(resp.status_code, 401)

    def test_authenticated_user_can_list_own_notifications(self):
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get("/api/notifications/")
        self.assertEqual(resp.status_code, 200)

    def test_user_cannot_see_another_users_notification(self):
        """User B cannot access User A's NotificationRecipient via the detail endpoint."""
        n = self._make_notification(company=self.company_a)
        NotificationRecipient.objects.create(notification=n, user=self.user_a)

        self.client.force_authenticate(user=self.user_b)
        resp = self.client.get(f"/api/notifications/{n.pk}/")
        # Should 404 because user_b has no recipient row for this notification
        self.assertEqual(resp.status_code, 404)

    def test_user_can_only_mark_own_notification_as_read(self):
        """User B cannot mark User A's notification as read."""
        n = self._make_notification(company=self.company_a)
        NotificationRecipient.objects.create(notification=n, user=self.user_a)

        self.client.force_authenticate(user=self.user_b)
        resp = self.client.post(f"/api/notifications/{n.pk}/read/")
        self.assertEqual(resp.status_code, 404)

    def test_user_a_mark_read_does_not_affect_user_b_state(self):
        """Marking read for user_a should not change user_b's recipient row."""
        n = self._make_notification(company=self.company_a)
        r_a = NotificationRecipient.objects.create(notification=n, user=self.user_a)
        r_b = NotificationRecipient.objects.create(notification=n, user=self.user_b)

        self.client.force_authenticate(user=self.user_a)
        self.client.post(f"/api/notifications/{n.pk}/read/")

        r_b.refresh_from_db()
        self.assertIsNone(r_b.read_at)

    def test_unread_count_is_user_scoped(self):
        """Unread count only counts this user's own unread notifications."""
        n = self._make_notification(company=self.company_a)
        NotificationRecipient.objects.create(notification=n, user=self.user_a)
        # user_b has no notifications

        self.client.force_authenticate(user=self.user_a)
        resp_a = self.client.get("/api/notifications/unread-count/")
        self.assertEqual(resp_a.status_code, 200)
        count_a = resp_a.data["count"]
        self.assertGreaterEqual(count_a, 1)

        self.client.force_authenticate(user=self.user_b)
        resp_b = self.client.get("/api/notifications/unread-count/")
        count_b = resp_b.data["count"]
        self.assertEqual(count_b, 0)

    def test_admin_templates_endpoint_requires_permission(self):
        """Ordinary user cannot access admin template endpoint."""
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get("/api/notifications/admin/templates/")
        self.assertEqual(resp.status_code, 403)

    def test_provider_config_endpoint_requires_permission(self):
        """Ordinary user cannot access provider config."""
        self.client.force_authenticate(user=self.user_a)
        resp = self.client.get("/api/notifications/admin/providers/")
        self.assertEqual(resp.status_code, 403)

    def test_provider_config_metadata_cannot_store_secrets(self):
        """Serializer must reject api_key in configuration_metadata."""
        from notifications.serializers import NotificationProviderConfigSerializer
        from notifications.constants import CHANNEL_EMAIL

        s = NotificationProviderConfigSerializer(data={
            "channel": CHANNEL_EMAIL,
            "provider": "SENDGRID",
            "is_enabled": True,
            "configuration_metadata": {"api_key": "sk-secret-123"},
        })
        self.assertFalse(s.is_valid())
        self.assertIn("configuration_metadata", s.errors)
