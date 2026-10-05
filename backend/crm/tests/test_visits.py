# =============================================================================
# RestaurantFlow — CRM Visit Tests
# Phase 17
# =============================================================================

from crm.customer_services import CustomerVisitService
from crm.tests.base import CRMTestBase


class CustomerVisitTests(CRMTestBase):

    def _make_confirmed_order(self, customer=None, order_type="COUNTER"):
        from orders.models import Order, OrderType, OrderStatus
        from django.utils import timezone
        return Order.objects.create(
            branch=self.branch,
            order_number=f"ORD-V-{Order.objects.count():06d}",
            order_type=order_type,
            status=OrderStatus.CONFIRMED,
            created_by=self.cashier_user,
            customer=customer,
            confirmed_at=timezone.now(),
        )

    def test_visit_created_for_confirmed_order_with_customer(self):
        c = self.make_customer(phone="+910006000001")
        order = self._make_confirmed_order(customer=c)
        visit = CustomerVisitService.record_visit_for_order(order)
        self.assertIsNotNone(visit)
        self.assertEqual(visit.customer, c)
        self.assertEqual(visit.status, "COMPLETED")

    def test_no_visit_for_anonymous_order(self):
        order = self._make_confirmed_order(customer=None)
        visit = CustomerVisitService.record_visit_for_order(order)
        self.assertIsNone(visit)

    def test_visit_creation_idempotent(self):
        c = self.make_customer(phone="+910006000002")
        order = self._make_confirmed_order(customer=c)
        visit1 = CustomerVisitService.record_visit_for_order(order)
        visit2 = CustomerVisitService.record_visit_for_order(order)
        self.assertEqual(visit1.pk, visit2.pk)

    def test_no_visit_for_draft_order(self):
        from orders.models import Order, OrderType, OrderStatus
        c = self.make_customer(phone="+910006000003")
        order = Order.objects.create(
            branch=self.branch,
            order_number="ORD-DRAFT-V",
            order_type=OrderType.COUNTER,
            status=OrderStatus.DRAFT,
            created_by=self.cashier_user,
            customer=c,
        )
        visit = CustomerVisitService.record_visit_for_order(order)
        self.assertIsNone(visit)

    def test_no_visit_for_cancelled_order(self):
        from orders.models import Order, OrderType, OrderStatus
        c = self.make_customer(phone="+910006000004")
        order = Order.objects.create(
            branch=self.branch,
            order_number="ORD-CANC-V",
            order_type=OrderType.COUNTER,
            status=OrderStatus.CANCELLED,
            created_by=self.cashier_user,
            customer=c,
        )
        visit = CustomerVisitService.record_visit_for_order(order)
        self.assertIsNone(visit)

    def test_visit_type_matches_order_type(self):
        from crm.constants import VISIT_DINE_IN, VISIT_TAKEAWAY, VISIT_COUNTER
        from orders.models import OrderType as OT
        c = self.make_customer(phone="+910006000005")

        order = self._make_confirmed_order(customer=c, order_type=OT.COUNTER)
        visit = CustomerVisitService.record_visit_for_order(order)
        self.assertEqual(visit.visit_type, VISIT_COUNTER)

    def test_sequential_visit_numbers(self):
        c = self.make_customer(phone="+910006000006")
        o1 = self._make_confirmed_order(customer=c)
        o2 = self._make_confirmed_order(customer=c)
        # Need distinct order ids — patch order_number
        o2.order_number = "ORD-V-SEQ2"
        o2.save(update_fields=["order_number"])

        v1 = CustomerVisitService.record_visit_for_order(o1)
        v2 = CustomerVisitService.record_visit_for_order(o2)
        self.assertIsNotNone(v1)
        self.assertIsNotNone(v2)
        self.assertNotEqual(v1.pk, v2.pk)
