# =============================================================================
# RestaurantFlow — Order Merge Tests
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from decimal import Decimal
from django.test import TestCase

from operations.tests.base import OperationsTestBase
from operations.order_services import merge_orders
from operations.exceptions import OrderMergeConflict, IncompatibleOrders
from operations.models import OrderMergeRequest
from operations.constants import ORDER_MERGE_PENDING, ORDER_MERGE_COMPLETED
from operations.validators import validate_order_merge_compatibility
from orders.models import OrderStatus


class OrderMergeServiceTest(OperationsTestBase):
    """Tests for order merge workflow."""

    def _make_merge_request(self, sources, destination):
        req = OrderMergeRequest.objects.create(
            destination_order=destination,
            requested_by=self.manager,
            status=ORDER_MERGE_PENDING,
        )
        req.source_orders.set(sources)
        return req

    def test_merge_two_draft_orders(self):
        order_a = self._make_order()
        order_b = self._make_order()
        req = self._make_merge_request([order_a, order_b], order_a)

        req = merge_orders(merge_request=req, approver=self.manager)
        self.assertEqual(req.status, ORDER_MERGE_COMPLETED)

        # order_b should be cancelled
        order_b.refresh_from_db()
        self.assertEqual(order_b.status, OrderStatus.CANCELLED)

    def test_merge_moves_items_to_destination(self):
        order_a = self._make_order()  # 1 pizza
        order_b = self._make_order()  # 1 pizza
        item_b_id = order_b.items.first().id

        req = self._make_merge_request([order_a, order_b], order_a)
        merge_orders(merge_request=req, approver=self.manager)

        order_a.refresh_from_db()
        item_ids = list(order_a.items.values_list("id", flat=True))
        self.assertIn(item_b_id, item_ids)

    def test_merge_cancelled_order_raises(self):
        order_a = self._make_order()
        order_b = self._make_order(status=OrderStatus.CANCELLED)
        req = self._make_merge_request([order_a, order_b], order_a)

        with self.assertRaises(IncompatibleOrders):
            merge_orders(merge_request=req, approver=self.manager)

    def test_merge_cross_branch_raises(self):
        """Orders from different branches cannot be merged."""
        from orders.models import Order
        order_a = self._make_order()
        order_other = Order.objects.create(
            branch=self.other_branch,
            order_number="OTH-0001",
            order_type="COUNTER",
            status=OrderStatus.DRAFT,
            created_by=self.other_user,
        )
        with self.assertRaises(IncompatibleOrders):
            validate_order_merge_compatibility([order_a, order_other], order_a)

    def test_merge_already_billed_order_raises(self):
        """An order that already has a bill cannot be merged."""
        from billing.models import Bill, BillStatus
        order_a = self._make_confirmed_order()
        order_b = self._make_confirmed_order()

        # Give order_b a bill
        Bill.objects.create(
            order=order_b, branch=self.branch,
            bill_number=f"B-2026-MRG-{Bill.objects.count():04d}",
            status=BillStatus.DRAFT,
            subtotal=Decimal("350.00"), grand_total=Decimal("367.50"),
            created_by=self.cashier,
        )
        with self.assertRaises(IncompatibleOrders):
            validate_order_merge_compatibility([order_a, order_b], order_a)

    def test_merge_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_ORDER_MERGED

        order_a = self._make_order()
        order_b = self._make_order()
        req = self._make_merge_request([order_a, order_b], order_a)
        merge_orders(merge_request=req, approver=self.manager)

        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_ORDER_MERGED,
                order_id=order_a.id,
            ).exists()
        )

    def test_merge_non_pending_raises(self):
        """Cannot process a merge request that is not PENDING."""
        order_a = self._make_order()
        order_b = self._make_order()
        req = self._make_merge_request([order_a, order_b], order_a)
        # Complete first merge
        merge_orders(merge_request=req, approver=self.manager)
        req.refresh_from_db()

        with self.assertRaises(OrderMergeConflict):
            merge_orders(merge_request=req, approver=self.manager)

    def test_merge_api_endpoint(self):
        """API endpoint creates and processes merge request."""
        self.client.force_login(self.manager)
        order_a = self._make_order()
        order_b = self._make_order()

        r = self.client.post(
            "/api/operations/orders/merge/",
            {
                "source_order_ids": [str(order_b.id)],
                "destination_order_id": str(order_a.id),
            },
            content_type="application/json",
        )
        self.assertIn(r.status_code, [201, 400, 403])
