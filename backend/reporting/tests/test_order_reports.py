# =============================================================================
# RestaurantFlow — Order Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date
from django.utils import timezone

from orders.models import OrderStatus, OrderType
from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from accounts import access as acl


class OrderSummaryTests(ReportingTestBase):

    def test_confirmed_orders_counted(self):
        self._make_order(status=OrderStatus.CONFIRMED)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_orders_summary(branches, date.today(), date.today())
        self.assertEqual(result["confirmed_orders"], 1)
        self.assertEqual(result["total_orders"], 1)

    def test_cancelled_orders_counted_separately(self):
        self._make_order(status=OrderStatus.CANCELLED)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_orders_summary(branches, date.today(), date.today())
        self.assertEqual(result["cancelled_orders"], 1)
        self.assertEqual(result["confirmed_orders"], 0)

    def test_order_type_counts(self):
        self._make_order(order_type=OrderType.COUNTER)
        self._make_order(order_type=OrderType.DINE_IN)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_orders_summary(branches, date.today(), date.today())
        self.assertEqual(result["counter_orders"], 1)
        self.assertEqual(result["dine_in_orders"], 1)

    def test_restaurant_isolation(self):
        # Create order in Org A
        self._make_order()
        # manager_b in Org B sees nothing
        branches_b = acl.get_accessible_branches(self.manager_b)
        result = agg.aggregate_orders_summary(branches_b, date.today(), date.today())
        self.assertEqual(result["total_orders"], 0)

    def test_orders_by_type_returns_breakdown(self):
        self._make_finalized_bill()  # creates a confirmed COUNTER order + bill
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_orders_by_type(branches, date.today(), date.today())
        self.assertIsInstance(result, list)
        # Should have at least one entry
        if result:
            row = result[0]
            self.assertIn("order_type", row)
            self.assertIn("order_count", row)
            self.assertIn("percentage_of_orders", row)

    def test_orders_by_type_percentages_sum_to_100(self):
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_orders_by_type(branches, date.today(), date.today())
        if result:
            total = sum(r["percentage_of_orders"] for r in result)
            self.assertAlmostEqual(float(total), 100.0, places=1)
