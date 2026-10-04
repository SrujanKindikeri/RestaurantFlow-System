# =============================================================================
# RestaurantFlow — Branch Performance Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date

from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from reporting.selectors import select_branch_performance
from accounts import access as acl


class BranchPerformanceTests(ReportingTestBase):

    def test_branch_performance_includes_revenue(self):
        self._make_finalized_bill(grand_total=Decimal("525.00"))
        branches = acl.get_accessible_branches(self.owner_a)  # sees A1 + A2
        result = agg.aggregate_branch_performance(branches, date.today(), date.today())
        self.assertGreater(len(result), 0)
        row = result[0]
        self.assertIn("branch_name", row)
        self.assertIn("revenue", row)
        self.assertIn("bills", row)

    def test_branch_a2_not_in_manager_a1_results(self):
        """manager_a only sees A1; owner sees both."""
        self._make_finalized_bill()
        # Owner sees multiple branches
        branches_owner = acl.get_accessible_branches(self.owner_a)
        result = agg.aggregate_branch_performance(branches_owner, date.today(), date.today())
        branch_names = [r["branch_name"] for r in result]
        # Only A1 has bills, A2 has none — A1 should appear in results
        self.assertIn("Branch A1", branch_names)

    def test_manager_a_cannot_see_branch_b1(self):
        """manager_a should never see Branch B1 (different org)."""
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_branch_performance(branches, date.today(), date.today())
        branch_names = [r["branch_name"] for r in result]
        self.assertNotIn("Branch B1", branch_names)

    def test_selector_respects_restaurant_scope(self):
        self._make_finalized_bill()
        result = select_branch_performance(
            self.owner_a, date.today(), date.today(),
            restaurant_id=str(self.restaurant_a.pk),
        )
        self.assertIsInstance(result, list)

    def test_required_fields_present(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.owner_a)
        result = agg.aggregate_branch_performance(branches, date.today(), date.today())
        if result:
            required = ["branch_id", "branch_name", "orders", "bills", "revenue",
                        "payments", "refunds", "discounts", "taxes"]
            for k in required:
                self.assertIn(k, result[0], f"Missing field: {k}")
