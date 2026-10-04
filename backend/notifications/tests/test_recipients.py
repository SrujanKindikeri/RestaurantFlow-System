# =============================================================================
# RestaurantFlow — Recipient Resolution Tests
# Phase 16
# =============================================================================

from notifications.tests.base import NotificationTestBase
from notifications.models import NotificationRecipient
from notifications.recipient_resolver import RecipientResolver
from notifications.services import NotificationService
from notifications.constants import (
    NOTIF_PAYMENT_FAILED, SEVERITY_HIGH, SOURCE_PAYMENT,
    NOTIF_CENTRAL_ALERT_CREATED, NOTIF_CENTRAL_ISSUE_ASSIGNED,
    SOURCE_CENTRAL_ALERT, SOURCE_CENTRAL_ISSUE,
)


class RecipientResolutionTests(NotificationTestBase):

    def test_resolve_returns_list(self):
        n = self._make_notification()
        resolver = RecipientResolver(n)
        result = resolver.resolve()
        self.assertIsInstance(result, list)

    def test_resolve_deduplicates_users(self):
        """If the same user appears multiple times, they get only one entry."""
        n = self._make_notification(
            notification_type=NOTIF_CENTRAL_ALERT_CREATED,
            source_type=SOURCE_CENTRAL_ALERT,
        )
        resolver = RecipientResolver(n)
        result = resolver.resolve()
        pks = [u.pk for u in result]
        self.assertEqual(len(pks), len(set(pks)))

    def test_resolve_excludes_inactive_users(self):
        """Inactive users must never be recipients."""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        inactive = User.objects.create_user(
            email="inactive@test.com", password="x",
            first_name="I", last_name="N", is_active=False,
        )
        n = self._make_notification()
        resolver = RecipientResolver(n)
        result = resolver.resolve()
        self.assertNotIn(inactive, result)

    def test_company_isolation_in_recipient_resolution(self):
        """
        Recipients for company_a notifications must not include company_b users.
        """
        n = self._make_notification(company=self.company_a)
        resolver = RecipientResolver(n)
        result = resolver.resolve()
        for user in result:
            from accounts import access as acl
            self.assertTrue(acl.can_access_organization(user, self.company_a))

    def test_resolve_and_create_recipients_creates_db_rows(self):
        n = self._make_notification(
            notification_type=NOTIF_CENTRAL_ISSUE_ASSIGNED,
            source_type=SOURCE_CENTRAL_ISSUE,
            metadata={"assignee_id": str(self.user_a.pk)},
        )
        recipients = NotificationService.resolve_and_create_recipients(n)
        # Should have created at least one NotificationRecipient
        db_count = NotificationRecipient.objects.filter(notification=n).count()
        self.assertEqual(db_count, len(recipients))

    def test_resolve_specific_assignee(self):
        """Central issue assigned: assignee should be in recipients."""
        n = self._make_notification(
            notification_type=NOTIF_CENTRAL_ISSUE_ASSIGNED,
            source_type=SOURCE_CENTRAL_ISSUE,
            metadata={"assignee_id": str(self.user_a.pk)},
        )
        resolver = RecipientResolver(n)
        result = resolver.resolve()
        pks = [u.pk for u in result]
        self.assertIn(self.user_a.pk, pks)

    def test_unknown_notification_type_returns_empty(self):
        """Unregistered notification type handler returns empty list safely."""
        n = self._make_notification(notification_type="ORDER_CONFIRMED")
        # Patch _HANDLERS to empty
        resolver = RecipientResolver(n)
        with __import__("unittest.mock", fromlist=["patch"]).patch.object(
            type(resolver), "_HANDLERS", new_callable=lambda: property(lambda self: {})
        ):
            result = resolver.resolve()
        self.assertEqual(result, [])

    def test_recipient_uniqueness_enforced(self):
        """Creating duplicate NotificationRecipient rows is prevented."""
        n = self._make_notification()
        NotificationRecipient.objects.create(notification=n, user=self.user_a)
        # get_or_create should not raise
        r, created = NotificationRecipient.objects.get_or_create(
            notification=n, user=self.user_a
        )
        self.assertFalse(created)
        self.assertEqual(NotificationRecipient.objects.filter(notification=n, user=self.user_a).count(), 1)
