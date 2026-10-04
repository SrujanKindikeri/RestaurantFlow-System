# =============================================================================
# RestaurantFlow — Notifications Test Base
# Phase 16
# =============================================================================

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

User = get_user_model()


@override_settings(
    # Use synchronous in-memory channel layer for tests
    CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}},
    # Use in-memory cache so tests don't need Redis
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    # Use console email backend (no actual sends)
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    # Celery runs tasks eagerly in tests
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class NotificationTestBase(TestCase):
    """Base class for all notification tests."""

    @classmethod
    def setUpTestData(cls):
        from organizations.models import Organization, Restaurant, Branch

        # Company A
        cls.company_a = Organization.objects.create(name="Company A")
        cls.restaurant_a = Restaurant.objects.create(
            name="Restaurant A", organization=cls.company_a
        )
        cls.branch_a = Branch.objects.create(
            name="Branch A1", restaurant=cls.restaurant_a
        )

        # Company B — must never see Company A notifications
        cls.company_b = Organization.objects.create(name="Company B")
        cls.restaurant_b = Restaurant.objects.create(
            name="Restaurant B", organization=cls.company_b
        )
        cls.branch_b = Branch.objects.create(
            name="Branch B1", restaurant=cls.restaurant_b
        )

        # Users
        cls.user_a = User.objects.create_user(
            email="user_a@companya.com", password="test", first_name="A", last_name="User"
        )
        cls.user_b = User.objects.create_user(
            email="user_b@companyb.com", password="test", first_name="B", last_name="User"
        )
        cls.admin_a = User.objects.create_user(
            email="admin_a@companya.com", password="test",
            first_name="Admin", last_name="A", is_staff=True
        )

    def _make_notification(
        self,
        company=None,
        notification_type="PAYMENT_FAILED",
        severity="HIGH",
        title="Test",
        message="Test message",
        source_type="PAYMENT",
        source_id="test-001",
        restaurant=None,
        branch=None,
    ):
        from notifications.models import Notification
        return Notification.objects.create(
            company=company or self.company_a,
            restaurant=restaurant,
            branch=branch,
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            source_type=source_type,
            source_id=source_id,
        )

    def _make_recipient(self, notification=None, user=None):
        from notifications.models import NotificationRecipient
        return NotificationRecipient.objects.create(
            notification=notification or self._make_notification(),
            user=user or self.user_a,
        )
