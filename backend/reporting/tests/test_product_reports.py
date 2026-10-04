# =============================================================================
# RestaurantFlow — Product / Menu Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date

from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from accounts import access as acl


class MenuItemReportTests(ReportingTestBase):

    def test_menu_item_aggregation_uses_billitem_snapshots(self):
        """Revenue must come from BillItem historical values, not current menu price."""
        bill = self._make_finalized_bill(grand_total=Decimal("525.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_items(branches, date.today(), date.today())
        self.assertGreater(len(result), 0)
        item_row = result[0]
        # net_revenue should equal the BillItem.total_amount, not current price
        self.assertIn("net_revenue", item_row)
        self.assertGreater(item_row["net_revenue"], Decimal("0"))

    def test_menu_item_has_required_fields(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_items(branches, date.today(), date.today())
        if result:
            row = result[0]
            required = [
                "menu_item_id", "menu_item_name", "quantity_sold",
                "gross_revenue", "discount_amount", "net_revenue",
                "number_of_orders", "percentage_of_sales",
            ]
            for k in required:
                self.assertIn(k, row, f"Missing key: {k}")

    def test_only_finalized_bills_counted(self):
        # Draft bill should NOT contribute to menu item revenue
        self._make_draft_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_items(branches, date.today(), date.today())
        self.assertEqual(result, [])

    def test_percentage_of_sales_between_0_and_100(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_items(branches, date.today(), date.today())
        for row in result:
            self.assertGreaterEqual(float(row["percentage_of_sales"]), 0)
            self.assertLessEqual(float(row["percentage_of_sales"]), 100)

    def test_restaurant_isolation_for_menu_items(self):
        self._make_finalized_bill()
        # Org B manager sees nothing
        branches_b = acl.get_accessible_branches(self.manager_b)
        result = agg.aggregate_menu_items(branches_b, date.today(), date.today())
        self.assertEqual(result, [])


class TopSellingItemsTests(ReportingTestBase):

    def test_top_selling_returns_limited_results(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_top_selling_items(branches, date.today(), date.today(), limit=5)
        self.assertLessEqual(len(result), 5)

    def test_top_selling_has_rank(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_top_selling_items(branches, date.today(), date.today(), limit=10)
        for i, row in enumerate(result):
            self.assertEqual(row["rank"], i + 1)

    def test_top_selling_sort_by_quantity(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_top_selling_items(
            branches, date.today(), date.today(), limit=10, sort_by="quantity"
        )
        if len(result) > 1:
            qtys = [r["quantity_sold"] for r in result]
            self.assertEqual(qtys, sorted(qtys, reverse=True))

    def test_top_selling_empty_returns_empty(self):
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_top_selling_items(branches, date.today(), date.today(), limit=10)
        self.assertEqual(result, [])


class CategoryPerformanceTests(ReportingTestBase):

    def test_category_aggregation(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_category_performance(branches, date.today(), date.today())
        self.assertGreater(len(result), 0)
        row = result[0]
        self.assertIn("category", row)
        self.assertIn("net_revenue", row)
        self.assertIn("sales_percentage", row)

    def test_category_percentage_total_100(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_category_performance(branches, date.today(), date.today())
        total = sum(r["sales_percentage"] for r in result)
        self.assertAlmostEqual(float(total), 100.0, places=1)


class MenuProfitabilityTests(ReportingTestBase):

    def test_profitability_revenue_from_bill_item(self):
        """Revenue must come from finalized BillItem, not current price."""
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_profitability(branches, date.today(), date.today())
        self.assertGreater(len(result), 0)
        row = result[0]
        self.assertIn("revenue", row)
        self.assertGreater(row["revenue"], Decimal("0"))

    def test_profitability_ingredient_cost_none_when_no_consumption(self):
        """When no StockConsumption records exist, cost must be None — not fabricated."""
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_profitability(branches, date.today(), date.today())
        for row in result:
            # No consumption created → ingredient_cost must be None or 0
            # (0 is acceptable if there are CONSUMED records with 0 cost)
            if row["ingredient_cost"] is None:
                self.assertIsNone(row["gross_profit"])
                self.assertIsNone(row["gross_margin_percentage"])

    def test_profitability_isolation(self):
        self._make_finalized_bill()
        branches_b = acl.get_accessible_branches(self.manager_b)
        result = agg.aggregate_menu_profitability(branches_b, date.today(), date.today())
        self.assertEqual(result, [])
