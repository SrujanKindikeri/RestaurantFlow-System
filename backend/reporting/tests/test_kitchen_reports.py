# =============================================================================
# RestaurantFlow — Kitchen Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date
from django.utils import timezone

from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from accounts import access as acl
from kitchen.models import KitchenOrder, KitchenOrderItem, KitchenOrderStatus, KitchenItemStatus
from orders.models import OrderStatus


class KitchenPerformanceTests(ReportingTestBase):

    def _make_kitchen_order(self, status=KitchenOrderStatus.READY,
                             started_at=None, ready_at=None):
        order = self._make_order()
        from django.utils import timezone as tz
        ko = KitchenOrder.objects.create(
            order=order,
            branch=self.branch_a1,
            status=status,
            received_at=tz.now(),
            started_at=started_at,
            ready_at=ready_at,
        )
        return ko

    def test_orders_received_counted(self):
        self._make_kitchen_order()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_kitchen_performance(branches, date.today(), date.today())
        self.assertEqual(result["orders_received"], 1)

    def test_ready_orders_counted(self):
        self._make_kitchen_order(status=KitchenOrderStatus.READY)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_kitchen_performance(branches, date.today(), date.today())
        self.assertEqual(result["orders_ready"], 1)

    def test_cancelled_orders_counted(self):
        self._make_kitchen_order(status=KitchenOrderStatus.CANCELLED)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_kitchen_performance(branches, date.today(), date.today())
        self.assertEqual(result["orders_cancelled"], 1)

    def test_pending_orders_counted(self):
        self._make_kitchen_order(status=KitchenOrderStatus.PREPARING)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_kitchen_performance(branches, date.today(), date.today())
        self.assertEqual(result["orders_pending"], 1)

    def test_avg_prep_time_calculated_when_timestamps_present(self):
        from datetime import timedelta
        now = timezone.now()
        self._make_kitchen_order(
            status=KitchenOrderStatus.READY,
            started_at=now - timedelta(minutes=15),
            ready_at=now,
        )
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_kitchen_performance(branches, date.today(), date.today())
        self.assertIsNotNone(result["average_preparation_time_seconds"])
        self.assertAlmostEqual(
            result["average_preparation_time_seconds"], 900.0, delta=60
        )

    def test_avg_prep_time_null_when_no_timestamps(self):
        # Order with no started_at
        self._make_kitchen_order(status=KitchenOrderStatus.READY, started_at=None, ready_at=None)
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_kitchen_performance(branches, date.today(), date.today())
        # No usable timestamps → avg should be None
        self.assertIsNone(result["average_preparation_time_seconds"])

    def test_branch_filter_respected(self):
        self._make_kitchen_order()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_kitchen_performance(
            branches, date.today(), date.today(), branch=self.branch_a1
        )
        self.assertEqual(result["orders_received"], 1)

    def test_isolation_between_orgs(self):
        self._make_kitchen_order()
        branches_b = acl.get_accessible_branches(self.manager_b)
        result = agg.aggregate_kitchen_performance(branches_b, date.today(), date.today())
        self.assertEqual(result["orders_received"], 0)
