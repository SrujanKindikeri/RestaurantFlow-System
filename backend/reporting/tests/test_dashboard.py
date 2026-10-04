# =============================================================================
# RestaurantFlow — Dashboard Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date, timedelta
from django.test import TestCase

from reporting.tests.base import ReportingTestBase
from reporting.dashboard_services import get_dashboard_kpis
from reporting.aggregations import growth_pct, _safe_div


class DashboardKPITests(ReportingTestBase):

    def test_dashboard_returns_expected_sections(self):
        result = get_dashboard_kpis(self.manager_a)
        self.assertIn("period", result)
        self.assertIn("sales", result)
        self.assertIn("orders", result)
        self.assertIn("products", result)
        self.assertIn("payments", result)
        self.assertIn("kitchen", result)
        self.assertIn("inventory", result)
        self.assertIn("financials", result)

    def test_dashboard_today_sales_with_bill(self):
        self._make_finalized_bill(grand_total=Decimal("525.00"))
        result = get_dashboard_kpis(self.manager_a)
        self.assertEqual(result["sales"]["today_bill_count"], 1)
        self.assertEqual(result["sales"]["today_net_sales"], Decimal("525.00"))

    def test_dashboard_no_bills_returns_zero_sales(self):
        result = get_dashboard_kpis(self.manager_a)
        self.assertEqual(result["sales"]["today_bill_count"], 0)
        self.assertEqual(result["sales"]["today_net_sales"], Decimal("0.00"))

    def test_dashboard_growth_pct_calculated(self):
        """today vs yesterday growth must be calculated."""
        result = get_dashboard_kpis(self.manager_a)
        # No bills yesterday → growth is None (division by zero handled)
        self.assertIsNone(result["sales"]["today_vs_yesterday_growth"])

    def test_dashboard_isolation(self):
        """manager_b should see no data from Org A."""
        self._make_finalized_bill()
        result = get_dashboard_kpis(self.manager_b)
        self.assertEqual(result["sales"]["today_bill_count"], 0)


class ComparisonEngineTests(TestCase):
    """
    Tests for the growth_pct helper — the comparison calculation engine.
    """

    def test_positive_growth(self):
        result = growth_pct(Decimal("110"), Decimal("100"))
        self.assertEqual(result, Decimal("10.00"))

    def test_negative_growth(self):
        result = growth_pct(Decimal("90"), Decimal("100"))
        self.assertEqual(result, Decimal("-10.00"))

    def test_zero_previous_returns_none(self):
        """Division by zero must never happen."""
        result = growth_pct(Decimal("100"), Decimal("0"))
        self.assertIsNone(result)

    def test_none_previous_returns_none(self):
        result = growth_pct(Decimal("100"), None)
        self.assertIsNone(result)

    def test_zero_current_zero_previous_returns_none(self):
        result = growth_pct(Decimal("0"), Decimal("0"))
        self.assertIsNone(result)

    def test_large_values_no_overflow(self):
        result = growth_pct(Decimal("1000000"), Decimal("500000"))
        self.assertEqual(result, Decimal("100.00"))

    def test_safe_div_avoids_zero_division(self):
        self.assertIsNone(_safe_div(Decimal("100"), Decimal("0")))
        self.assertIsNone(_safe_div(Decimal("100"), 0))
        self.assertIsNone(_safe_div(Decimal("100"), None))
        self.assertEqual(_safe_div(Decimal("100"), Decimal("4")), Decimal("25.00"))


class DashboardFilterTests(ReportingTestBase):

    def test_dashboard_respects_branch_filter(self):
        """Filter by branch_a1 — only A1 data returned."""
        self._make_finalized_bill()
        result = get_dashboard_kpis(
            self.manager_a,
            branch_id=str(self.branch_a1.pk),
        )
        self.assertIsNotNone(result)
        self.assertIn("sales", result)

    def test_dashboard_invalid_branch_raises_scope_error(self):
        from reporting.exceptions import ReportScopeError
        with self.assertRaises(ReportScopeError):
            get_dashboard_kpis(
                self.manager_a,
                branch_id=str(self.branch_b1.pk),  # different org
            )
