# =============================================================================
# RestaurantFlow — Reporting Performance Tests
# Phase 14
#
# Verify that key endpoints don't have obvious N+1 query problems.
# Uses assertNumQueries to set upper bounds.
# =============================================================================

from decimal import Decimal
from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse

from reporting.tests.base import ReportingTestBase


class QueryCountTests(ReportingTestBase):
    """
    These tests set UPPER BOUNDS on query counts, not exact counts.
    If a query count exceeds the bound, it signals a potential N+1 problem.

    Note: assertNumQueries counts DB queries, not cache lookups.
    Cache is disabled in tests (Django test runner uses dummy cache by default).
    """

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_a)
        # Create some test data
        for _ in range(5):
            self._make_finalized_bill()

    def test_sales_summary_query_count_bounded(self):
        """Sales summary should use at most ~5 queries (not N queries per bill)."""
        url = reverse("reporting:sales-summary")
        with self.assertNumQueries(5):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_top_selling_query_count_bounded(self):
        """Top selling should use at most ~5 queries regardless of item count."""
        url = reverse("reporting:menu-top-selling")
        with self.assertNumQueries(5):
            response = self.client.get(url, {"limit": "10"})
        self.assertEqual(response.status_code, 200)

    def test_orders_summary_query_count_bounded(self):
        url = reverse("reporting:orders-summary")
        with self.assertNumQueries(6):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_payment_summary_query_count_bounded(self):
        url = reverse("reporting:payment-summary")
        with self.assertNumQueries(5):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_branch_performance_query_count_bounded(self):
        url = reverse("reporting:branch-performance")
        with self.assertNumQueries(8):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_menu_items_query_count_bounded(self):
        url = reverse("reporting:menu-items")
        with self.assertNumQueries(5):
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class PaginationTests(ReportingTestBase):
    """Verify that list responses are bounded / paginated."""

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.manager_a)

    def test_top_selling_limit_respected(self):
        for _ in range(10):
            self._make_finalized_bill()
        url = reverse("reporting:menu-top-selling")
        response = self.client.get(url, {"limit": "3"})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertLessEqual(len(data), 3)

    def test_default_limit_applied_when_not_specified(self):
        for _ in range(15):
            self._make_finalized_bill()
        url = reverse("reporting:menu-top-selling")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        # Default limit is 10
        self.assertLessEqual(len(data), 10)
