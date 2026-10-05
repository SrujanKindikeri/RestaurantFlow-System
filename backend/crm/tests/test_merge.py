# =============================================================================
# RestaurantFlow — CRM Customer Merge Tests
# Phase 17
# =============================================================================

from crm.customer_services import CustomerMergeService
from crm.exceptions import CustomerMergeConflict, CustomerMergeNotAllowed
from crm.tests.base import CRMTestBase


class CustomerMergeTests(CRMTestBase):

    def test_request_merge(self):
        from crm.constants import MERGE_REQUESTED
        source = self.make_customer(phone="+910007000001")
        target = self.make_customer(phone="+910007000002")
        req = CustomerMergeService.request_merge(
            source, target, reason="Duplicate customer", actor=self.manager_user
        )
        self.assertEqual(req.status, MERGE_REQUESTED)
        self.assertEqual(req.source_customer, source)
        self.assertEqual(req.target_customer, target)

    def test_same_customer_raises(self):
        c = self.make_customer(phone="+910007000003")
        with self.assertRaises(CustomerMergeConflict):
            CustomerMergeService.request_merge(c, c, reason="Test", actor=self.manager_user)

    def test_cross_restaurant_merge_raises(self):
        source = self.make_customer(restaurant=self.restaurant, phone="+910007000004")
        target = self.make_customer(restaurant=self.other_restaurant, phone="+910007000005")
        with self.assertRaises(CustomerMergeConflict):
            CustomerMergeService.request_merge(
                source, target, reason="Cross-restaurant", actor=self.manager_user
            )

    def test_duplicate_request_raises(self):
        source = self.make_customer(phone="+910007000006")
        target = self.make_customer(phone="+910007000007")
        CustomerMergeService.request_merge(source, target, reason="First", actor=self.manager_user)
        with self.assertRaises(CustomerMergeConflict):
            CustomerMergeService.request_merge(source, target, reason="Second", actor=self.manager_user)

    def test_approve_merge_deactivates_source(self):
        source = self.make_customer(phone="+910007000008")
        target = self.make_customer(phone="+910007000009")
        req = CustomerMergeService.request_merge(
            source, target, reason="Test approve", actor=self.manager_user
        )
        CustomerMergeService.approve_merge(req, actor=self.manager_user)

        source.refresh_from_db()
        self.assertFalse(source.is_active)
        self.assertEqual(source.merged_into, target)
        req.refresh_from_db()
        self.assertEqual(req.status, "APPROVED")

    def test_approve_transfers_orders(self):
        from orders.models import Order, OrderType, OrderStatus
        source = self.make_customer(phone="+910007000010")
        target = self.make_customer(phone="+910007000011")

        order = Order.objects.create(
            branch=self.branch, order_number="ORD-MERGE-001",
            order_type=OrderType.COUNTER, status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user, customer=source,
        )
        req = CustomerMergeService.request_merge(
            source, target, reason="Merge orders", actor=self.manager_user
        )
        CustomerMergeService.approve_merge(req, actor=self.manager_user)

        order.refresh_from_db()
        self.assertEqual(order.customer, target)

    def test_reject_merge(self):
        source = self.make_customer(phone="+910007000012")
        target = self.make_customer(phone="+910007000013")
        req = CustomerMergeService.request_merge(
            source, target, reason="Test reject", actor=self.manager_user
        )
        CustomerMergeService.reject_merge(req, actor=self.manager_user)
        req.refresh_from_db()
        self.assertEqual(req.status, "REJECTED")

        # Source still active
        source.refresh_from_db()
        self.assertTrue(source.is_active)

    def test_cannot_approve_already_rejected(self):
        source = self.make_customer(phone="+910007000014")
        target = self.make_customer(phone="+910007000015")
        req = CustomerMergeService.request_merge(
            source, target, reason="Test double", actor=self.manager_user
        )
        CustomerMergeService.reject_merge(req, actor=self.manager_user)
        with self.assertRaises(CustomerMergeNotAllowed):
            CustomerMergeService.approve_merge(req, actor=self.manager_user)
