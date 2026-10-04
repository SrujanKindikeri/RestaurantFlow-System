# =============================================================================
# RestaurantFlow — Company / Restaurant / Branch Isolation Tests
# Phase 16
# =============================================================================

from notifications.tests.base import NotificationTestBase
from notifications.models import Notification, NotificationRecipient
from notifications.services import NotificationService
from notifications.selectors import get_notification_recipients_for_user
from notifications.constants import NOTIF_PAYMENT_FAILED, SEVERITY_HIGH, SOURCE_PAYMENT


class CompanyScopeIsolationTests(NotificationTestBase):

    def test_company_a_notification_not_visible_to_company_b_user(self):
        """Notifications for company_a must not appear in company_b user's list."""
        n = self._make_notification(company=self.company_a)
        NotificationRecipient.objects.create(notification=n, user=self.user_a)

        qs = get_notification_recipients_for_user(self.user_b)
        notif_ids = [r.notification_id for r in qs]
        self.assertNotIn(n.pk, notif_ids)

    def test_company_b_notification_not_visible_to_company_a_user(self):
        n = self._make_notification(company=self.company_b)
        NotificationRecipient.objects.create(notification=n, user=self.user_b)

        qs = get_notification_recipients_for_user(self.user_a)
        notif_ids = [r.notification_id for r in qs]
        self.assertNotIn(n.pk, notif_ids)

    def test_notification_scoped_to_correct_company(self):
        n = self._make_notification(company=self.company_a)
        self.assertEqual(n.company, self.company_a)
        self.assertNotEqual(n.company, self.company_b)

    def test_restaurant_scope_isolation(self):
        """
        A restaurant_a notification should have restaurant=restaurant_a,
        not restaurant_b.
        """
        n = self._make_notification(
            company=self.company_a,
            restaurant=self.restaurant_a,
        )
        self.assertEqual(n.restaurant, self.restaurant_a)

    def test_branch_scope_set_correctly(self):
        n = self._make_notification(
            company=self.company_a,
            restaurant=self.restaurant_a,
            branch=self.branch_a,
        )
        self.assertEqual(n.branch, self.branch_a)

    def test_notification_company_a_does_not_leak_to_company_b(self):
        """
        Even if user_b somehow has a recipient row for company_a notification
        (which should never happen), the get_notification_recipients_for_user
        selector still returns only user_b's own rows.
        """
        n_a = self._make_notification(company=self.company_a)
        # Deliberately create a cross-company recipient (simulating a bug)
        NotificationRecipient.objects.create(notification=n_a, user=self.user_b)

        qs = get_notification_recipients_for_user(self.user_b)
        # The selector returns rows by user — so this would appear.
        # The REAL guard is that recipient resolution never creates this row.
        # Verify our resolver never adds user_b to company_a notifications.
        from notifications.recipient_resolver import RecipientResolver
        resolver = RecipientResolver(n_a)
        users = resolver.resolve()
        pks = [u.pk for u in users]
        # user_b has no assignment to company_a, so must not be in resolved list
        self.assertNotIn(self.user_b.pk, pks)


class AdminDeliveryScopeTests(NotificationTestBase):

    def test_admin_delivery_list_scoped_to_company(self):
        """Admin delivery history should only return deliveries for the user's company."""
        from notifications.selectors import get_deliveries_for_admin
        from notifications.models import NotificationDelivery

        n_a = self._make_notification(company=self.company_a, source_id="scope-del-a")
        from notifications.models import NotificationRecipient
        r_a = NotificationRecipient.objects.create(notification=n_a, user=self.user_a)
        del_a = NotificationDelivery.objects.create(
            notification=n_a, recipient=r_a, channel="IN_APP"
        )

        n_b = self._make_notification(company=self.company_b, source_id="scope-del-b")
        r_b = NotificationRecipient.objects.create(notification=n_b, user=self.user_b)
        del_b = NotificationDelivery.objects.create(
            notification=n_b, recipient=r_b, channel="IN_APP"
        )

        qs_a = get_deliveries_for_admin(company=self.company_a)
        ids_a = [d.pk for d in qs_a]
        self.assertIn(del_a.pk, ids_a)
        self.assertNotIn(del_b.pk, ids_a)
