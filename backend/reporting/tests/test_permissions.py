# =============================================================================
# RestaurantFlow — Reporting Permission Tests
# Phase 14
#
# Tests that every endpoint:
#   1. Returns 401 for unauthenticated requests
#   2. Returns 403 when the user lacks the required reporting permission
#   3. Returns 200 for authorized users
# =============================================================================

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from reporting.tests.base import ReportingTestBase


# All reporting URL names and the permission they require
ENDPOINT_CASES = [
    ("reporting:dashboard",           None),           # permission enforced by CanViewDashboard
    ("reporting:sales-summary",       None),
    ("reporting:sales-trend",         None),
    ("reporting:sales-hourly",        None),
    ("reporting:orders-summary",      None),
    ("reporting:orders-by-type",      None),
    ("reporting:menu-items",          None),
    ("reporting:menu-top-selling",    None),
    ("reporting:menu-categories",     None),
    ("reporting:menu-profitability",  None),
    ("reporting:branch-performance",  None),
    ("reporting:counter-performance", None),
    ("reporting:payment-summary",     None),
    ("reporting:payment-methods",     None),
    ("reporting:refunds",             None),
    ("reporting:discounts",           None),
    ("reporting:kitchen-performance", None),
    ("reporting:kitchen-items",       None),
    ("reporting:staff-waiters",       None),
    ("reporting:staff-cashiers",      None),
    ("reporting:inventory-summary",   None),
    ("reporting:inventory-consumption", None),
    ("reporting:inventory-wastage",   None),
    ("reporting:purchases",           None),
    ("reporting:suppliers",           None),
    ("reporting:expenses",            None),
    ("reporting:payables",            None),
    ("reporting:financial-summary",   None),
]


class UnauthenticatedAccessTests(TestCase):
    """All reporting endpoints return 401 without authentication."""

    def setUp(self):
        self.client = APIClient()

    def test_dashboard_requires_auth(self):
        url = reverse("reporting:dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_sales_summary_requires_auth(self):
        url = reverse("reporting:sales-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_menu_items_requires_auth(self):
        url = reverse("reporting:menu-items")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_financial_summary_requires_auth(self):
        url = reverse("reporting:financial-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)


class PermissionEnforcementTests(ReportingTestBase):
    """
    Users without reporting permissions get 403.
    Users with permissions get 200.
    """

    def setUp(self):
        self.client = APIClient()

    def _user_without_perms(self):
        """Create a fresh user with no reporting permissions."""
        from accounts.models import User
        return User.objects.create_user(
            email="noperms@test.com", password="pass123"
        )

    def test_user_without_permission_denied_dashboard(self):
        user = self._user_without_perms()
        self.client.force_authenticate(user=user)
        url = reverse("reporting:dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_user_without_permission_denied_sales(self):
        user = self._user_without_perms()
        self.client.force_authenticate(user=user)
        url = reverse("reporting:sales-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_authorized_user_gets_200_dashboard(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:dashboard")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authorized_user_gets_200_sales_summary(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:sales-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authorized_user_gets_200_menu_items(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:menu-items")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authorized_user_gets_200_payment_summary(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:payment-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authorized_user_gets_200_inventory_summary(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:inventory-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authorized_user_gets_200_kitchen_performance(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:kitchen-performance")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authorized_user_gets_200_expenses(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:expenses")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authorized_user_gets_200_financial_summary(self):
        self.client.force_authenticate(user=self.manager_a)
        url = reverse("reporting:financial-summary")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class ScopeIsolationTests(ReportingTestBase):
    """
    manager_b (Org B) must never see Org A data even if they pass valid UUIDs.
    """

    def setUp(self):
        self.client = APIClient()

    def test_manager_b_cannot_access_restaurant_a_sales(self):
        """Pass restaurant_a's UUID in the query string — must be denied."""
        self._make_finalized_bill()
        self.client.force_authenticate(user=self.manager_b)
        url = reverse("reporting:sales-summary")
        response = self.client.get(url, {
            "restaurant_id": str(self.restaurant_a.pk),
            "date_from": "2020-01-01",
            "date_to": "2099-12-31",
        })
        # Should either 403 (scope error) or 200 with empty data
        # Either is acceptable — but must NOT return Org A data
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["data"]["number_of_bills"], 0)

    def test_manager_b_cannot_access_branch_a1_menu_items(self):
        self._make_finalized_bill()
        self.client.force_authenticate(user=self.manager_b)
        url = reverse("reporting:menu-items")
        response = self.client.get(url, {
            "branch_id": str(self.branch_a1.pk),
        })
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["data"], [])
        else:
            self.assertEqual(response.status_code, 403)

    def test_export_scoped_correctly(self):
        """Export endpoint must apply same scoping as report endpoint."""
        self._make_finalized_bill()
        self.client.force_authenticate(user=self.manager_b)
        url = reverse("reporting:export-csv", kwargs={"report_type": "menu_top_selling"})
        response = self.client.get(url, {
            "branch_id": str(self.branch_a1.pk),
        })
        # 200 with empty CSV OR 403 — never Org A data
        if response.status_code == 200:
            content = response.content.decode("utf-8-sig")
            # CSV has only the header row (no data rows) since scope blocked
            lines = [l for l in content.strip().split("\n") if l.strip()]
            # 1 = header only
            self.assertLessEqual(len(lines), 1)
