# =============================================================================
# RestaurantFlow — Sales Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone

from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from reporting.selectors import select_sales_summary, select_sales_trend, select_hourly_sales
from accounts import access as acl


class SalesSummaryTests(ReportingTestBase):
    """
    Tests for sales summary aggregation.
    FINALIZED bills → included.
    DRAFT / CANCELLED / VOID bills → excluded.
    """

    def test_finalized_bill_included_in_sales(self):
        bill = self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_summary(branches, date.today(), date.today())
        self.assertEqual(result["number_of_bills"], 1)
        self.assertGreater(result["net_sales"], Decimal("0"))

    def test_draft_bill_excluded_from_sales(self):
        self._make_draft_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_summary(branches, date.today(), date.today())
        self.assertEqual(result["number_of_bills"], 0)
        self.assertEqual(result["net_sales"], Decimal("0.00"))

    def test_cancelled_bill_excluded_from_sales(self):
        self._make_cancelled_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_summary(branches, date.today(), date.today())
        self.assertEqual(result["number_of_bills"], 0)

    def test_correct_totals_from_multiple_bills(self):
        self._make_finalized_bill(grand_total=Decimal("525.00"))
        self._make_finalized_bill(grand_total=Decimal("300.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_summary(branches, date.today(), date.today())
        self.assertEqual(result["number_of_bills"], 2)
        self.assertEqual(result["net_sales"], Decimal("825.00"))

    def test_average_bill_value_calculated(self):
        self._make_finalized_bill(grand_total=Decimal("600.00"))
        self._make_finalized_bill(grand_total=Decimal("400.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_summary(branches, date.today(), date.today())
        self.assertEqual(result["average_bill_value"], Decimal("500.00"))

    def test_date_filter_excludes_old_bills(self):
        yesterday = date.today() - timedelta(days=1)
        from django.utils import timezone as tz
        old_finalized_at = tz.now() - timedelta(days=2)
        bill = self._make_finalized_bill(finalized_at=old_finalized_at)
        branches = acl.get_accessible_branches(self.manager_a)
        # Query only today
        result = agg.aggregate_sales_summary(branches, date.today(), date.today())
        self.assertEqual(result["number_of_bills"], 0)

    def test_branch_filter_respected(self):
        # Bill in A1 — should be counted
        self._make_finalized_bill()
        # Query scoped to A1 only
        branches = acl.get_accessible_branches(self.manager_a)  # only A1
        result = agg.aggregate_sales_summary(
            branches, date.today(), date.today(), branch=self.branch_a1
        )
        self.assertEqual(result["number_of_bills"], 1)

    def test_discount_fields_present_in_result(self):
        self._make_finalized_bill(discount_amount=Decimal("50.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_summary(branches, date.today(), date.today())
        self.assertIn("discount_amount", result)
        self.assertEqual(result["discount_amount"], Decimal("50.00"))

    def test_empty_result_returns_zeros(self):
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_summary(branches, date.today(), date.today())
        self.assertEqual(result["net_sales"], Decimal("0.00"))
        self.assertEqual(result["number_of_bills"], 0)
        self.assertIsNone(result["average_bill_value"])

    def test_selector_respects_user_scope(self):
        self._make_finalized_bill()
        # manager_a can see Branch A1
        result = select_sales_summary(self.manager_a, date.today(), date.today())
        self.assertEqual(result["number_of_bills"], 1)

    def test_selector_isolation_between_restaurants(self):
        # Bill in Restaurant A, Branch A1
        self._make_finalized_bill()
        # manager_b should see ZERO (different org)
        result = select_sales_summary(self.manager_b, date.today(), date.today())
        self.assertEqual(result["number_of_bills"], 0)


class SalesTrendTests(ReportingTestBase):

    def test_trend_daily_returns_one_row_per_day(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_trend(branches, date.today(), date.today(), "daily")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["bill_count"], 1)

    def test_trend_row_has_required_keys(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_trend(branches, date.today(), date.today(), "daily")
        row = result[0]
        for key in ["date", "gross_sales", "discounts", "tax", "net_sales", "bill_count"]:
            self.assertIn(key, row)

    def test_trend_empty_period_returns_empty_list(self):
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_sales_trend(
            branches,
            date.today() - timedelta(days=5),
            date.today() - timedelta(days=1),
            "daily",
        )
        self.assertEqual(result, [])


class HourlySalesTests(ReportingTestBase):

    def test_hourly_returns_24_hours(self):
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_hourly_sales(branches, date.today(), date.today())
        self.assertEqual(len(result), 24)
        hours = [r["hour"] for r in result]
        self.assertEqual(hours, list(range(24)))

    def test_hourly_empty_hours_return_zero(self):
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_hourly_sales(branches, date.today(), date.today())
        for row in result:
            self.assertIn("sales", row)
            self.assertIn("bill_count", row)
            self.assertEqual(row["bill_count"], 0)
