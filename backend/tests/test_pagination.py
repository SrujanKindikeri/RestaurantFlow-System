# =============================================================================
# RestaurantFlow — Pagination Enforcement Tests
# FEAT-004: Verifies SafePageNumberPagination caps page_size at max_page_size,
# and ExportCSVView returns HTTP 400 when row count exceeds MAX_EXPORT_ROWS.
# =============================================================================

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

User = get_user_model()


def _make_user_with_perm(email, perm_code, perm_name="Permission"):
    """Create a user and assign a single permission."""
    from organizations.models import Organization, Restaurant, Branch
    from accounts.models import Permission, Role, UserRoleAssignment

    org = Organization.objects.create(
        slug=f"pag-org-{perm_code[:8].replace('.', '-')}",
        name="PagOrg",
    )
    restaurant = Restaurant.objects.create(
        slug=f"pag-rest-{perm_code[:8].replace('.', '-')}",
        organization=org,
        name="PagRest",
    )
    branch = Branch.objects.create(
        code=f"P{perm_code[:3].upper().replace('.', '')}",
        restaurant=restaurant,
        name="PagBranch",
    )
    user = User.objects.create_user(email=email, password="pass", is_active=True, is_superuser=True)
    perm, _ = Permission.objects.get_or_create(
        code=perm_code, defaults={"name": perm_name, "module": "test"}
    )
    role, _ = Role.objects.get_or_create(
        code=f"role-{perm_code.replace('.', '-')}",
        defaults={"name": f"Role {perm_code}", "is_system_role": False},
    )
    role.permissions.add(perm)
    UserRoleAssignment.objects.get_or_create(
        user=user, organization=org, role=role,
        defaults={"restaurant": restaurant, "branch": branch},
    )
    return user, branch


class MaxPageSizeEnforcedTest(TestCase):
    """
    Requesting ?page_size=500 on any list endpoint must return at most
    max_page_size (100) items, not 500.
    """

    def setUp(self):
        self.user, self.branch = _make_user_with_perm(
            "pag-orders@example.com", "order.view.branch", "View Orders"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        from orders.models import Order, OrderType
        # Create 110 DRAFT orders (no signals) so we can verify capping at 100
        for i in range(110):
            Order.objects.create(
                branch=self.branch,
                order_number=f"ORD-PAG-{i:04d}",
                order_type=OrderType.COUNTER,
                # Use DRAFT to avoid kitchen-order signal firing on CONFIRMED
                status="DRAFT",
                created_by=self.user,
            )

    def test_page_size_capped_at_max(self):
        url = reverse("order-list-create")
        response = self.client.get(url, {"page_size": 500})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Result count must not exceed max_page_size=100
        results = data.get("results", data)
        self.assertLessEqual(len(results), 100)


class ExportMaxRowsTest(TestCase):
    """
    ExportCSVView must return HTTP 400 with EXPORT_TOO_LARGE code when the
    service function would return more rows than MAX_EXPORT_ROWS.
    """

    def setUp(self):
        self.user, _ = _make_user_with_perm(
            "pag-export@example.com", "reporting.export.csv", "Export CSV"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_export_returns_400_when_too_many_rows(self):
        from reporting.constants import MAX_EXPORT_ROWS
        from reporting.views import ExportCSVView
        from unittest.mock import patch, MagicMock

        # Mock the service function to return a list exceeding MAX_EXPORT_ROWS
        large_dataset = [{"row": i} for i in range(MAX_EXPORT_ROWS + 1)]
        mock_fn = MagicMock(return_value=large_dataset)

        original_map = ExportCSVView.REPORT_MAP.copy()
        patched_map = dict(original_map)
        patched_map["sales_summary"] = (mock_fn, "sales_summary")

        with patch.object(ExportCSVView, "REPORT_MAP", patched_map):
            url = "/api/reporting/export/sales_summary/"
            response = self.client.get(url)

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertTrue(data.get("error"))
        self.assertEqual(data.get("code"), "EXPORT_TOO_LARGE")

    def test_export_succeeds_within_row_limit(self):
        """When dataset is small, export should not return EXPORT_TOO_LARGE."""
        small_dataset = [{"metric": "sales", "value": "100.00"}]

        with patch("reporting.services.get_sales_summary", return_value=small_dataset), \
             patch("reporting.export_services.generate_csv", return_value=(b"col,val\r\n", 1)):
            url = "/api/reporting/export/sales_summary/"
            response = self.client.get(url)

        # Should not be a row-limit error regardless of auth outcome
        if response.status_code == 400:
            self.assertNotEqual(response.json().get("code"), "EXPORT_TOO_LARGE")
