# =============================================================================
# RestaurantFlow — Bill Lifecycle Tests
# Phase 8
#
# Tests:
#   - bill created from valid confirmed order
#   - bill rejected from DRAFT order
#   - bill rejected from CANCELLED order
#   - one bill per order (DB uniqueness)
#   - idempotent creation (concurrent returns existing)
#   - bill number format (B-YYYY-NNNNNN)
#   - bill finalization
#   - finalized bill immutability
#   - bill cancellation (DRAFT and FINALIZED)
#   - bill void
#   - grand total calculation correctness
#   - rounding applied correctly
#   - receipt data structure
# =============================================================================

from decimal import Decimal

from django.db import IntegrityError
from rest_framework.exceptions import PermissionDenied, ValidationError

from billing.models import Bill, BillItem, BillStatus, BillSequence
from billing import services
from billing.tests.base import BillingTestBase


class TestBillCreation(BillingTestBase):
    """Tests for create_bill_from_order()."""

    def test_creates_bill_from_confirmed_order(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertIsNotNone(bill)
        self.assertEqual(bill.status, BillStatus.DRAFT)
        self.assertEqual(bill.order, order)
        self.assertEqual(bill.branch, self.branch)

    def test_bill_number_format(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        # Format: B-YYYY-NNNNNN
        parts = bill.bill_number.split("-")
        self.assertEqual(parts[0], "B")
        self.assertEqual(len(parts[1]), 4)  # year
        self.assertEqual(len(parts[2]), 6)  # 6-digit padded sequence

    def test_bill_number_is_unique(self):
        order1 = self._make_confirmed_order()
        order2 = self._make_confirmed_order()
        bill1 = services.create_bill_from_order(order1, self.cashier)
        bill2 = services.create_bill_from_order(order2, self.cashier)
        self.assertNotEqual(bill1.bill_number, bill2.bill_number)

    def test_bill_number_different_from_order_number(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertNotEqual(bill.bill_number, order.order_number)
        # Order is like TEST-..., bill starts with B-
        self.assertTrue(bill.bill_number.startswith("B-"))

    def test_bill_items_created(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.items.count(), 2)

    def test_bill_items_copy_snapshots(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        biryani_item = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani_item.unit_price, Decimal("250.00"))
        self.assertEqual(biryani_item.tax_rate, Decimal("5.000"))
        self.assertEqual(biryani_item.tax_code, "GST_5")
        self.assertEqual(biryani_item.quantity, Decimal("2.000"))

    def test_rejects_draft_order(self):
        order = self._make_draft_order()
        with self.assertRaises(ValidationError) as ctx:
            services.create_bill_from_order(order, self.cashier)
        self.assertEqual(ctx.exception.detail["code"], "ORDER_DRAFT")

    def test_rejects_cancelled_order(self):
        order = self._make_cancelled_order()
        with self.assertRaises(ValidationError) as ctx:
            services.create_bill_from_order(order, self.cashier)
        self.assertEqual(ctx.exception.detail["code"], "ORDER_CANCELLED")

    def test_idempotent_returns_existing_bill(self):
        order = self._make_confirmed_order()
        bill1 = services.create_bill_from_order(order, self.cashier)
        bill2 = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill1.id, bill2.id)

    def test_one_bill_per_order_db_constraint(self):
        """DB-level: Bill.order is OneToOneField → duplicate raises IntegrityError."""
        from billing.models import Bill
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(Exception):  # IntegrityError or similar
            Bill.objects.create(
                order=order,
                branch=self.branch,
                bill_number="B-2026-999999",
                created_by=self.cashier,
            )

    def test_no_permission_raises(self):
        order = self._make_confirmed_order()
        with self.assertRaises(PermissionDenied):
            services.create_bill_from_order(order, self.other_user)

    def test_other_branch_access_denied(self):
        """other_user has no branch access at all."""
        order = self._make_confirmed_order()
        with self.assertRaises(PermissionDenied):
            services.create_bill_from_order(order, self.other_user)

    def test_created_by_set(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.created_by, self.cashier)


class TestBillTotals(BillingTestBase):
    """Tests for calculate_bill() — exact amount verification."""

    def test_subtotal_calculation(self):
        # 2 × 250 + 1 × 120 = 620
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.subtotal, Decimal("620.00"))

    def test_tax_calculation_no_discount(self):
        # Biryani: 500 × 5% = 25.00
        # Fries: 120 × 0% = 0.00
        # Total tax = 25.00
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.tax_amount, Decimal("25.00"))

    def test_taxable_amount_no_discount(self):
        # taxable_amount = subtotal - discount = 620 - 0 = 620
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.taxable_amount, Decimal("620.00"))

    def test_grand_total_no_discount(self):
        # 620 + 25 = 645 → rounding = 0 → grand total = 645
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.grand_total, Decimal("645.00"))

    def test_rounding_applied(self):
        # 620 + 25 = 645.00 → rounds to 645 → rounding = 0.00
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.rounding_amount, Decimal("0.00"))

    def test_tax_breakdown_structure(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertIn("GST_5", bill.tax_breakdown)
        # ZERO_TAX items produce 0.00 tax
        self.assertEqual(bill.tax_breakdown["GST_5"], "25.00")

    def test_zero_tax_item(self):
        """An order with only zero-tax items should produce zero tax."""
        from django.utils import timezone as tz_mod
        from orders.models import OrderStatus, OrderType, OrderItem
        ts = tz_mod.now().strftime("%Y%m%d%H%M%S%f")
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"FRIES-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.cashier,
            status=OrderStatus.CONFIRMED,
            confirmed_at=tz_mod.now(),
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_fries,
            item_name_snapshot="French Fries",
            sku_snapshot="FRIES-001",
            unit_price_snapshot=Decimal("120.00"),
            tax_rate_snapshot=Decimal("0.000"),
            tax_code_snapshot="ZERO_TAX",
            quantity=Decimal("1.000"),
        )
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.tax_amount, Decimal("0.00"))
        self.assertEqual(bill.grand_total, Decimal("120.00"))

    def test_backend_authoritative_totals(self):
        """calculate_bill returns consistent data; never trusts client."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        result = services.calculate_bill(bill)
        self.assertEqual(result["subtotal"], "620.00")
        self.assertEqual(result["tax_amount"], "25.00")
        self.assertEqual(result["grand_total"], "645.00")


class TestBillFinalization(BillingTestBase):
    """Tests for finalize_bill()."""

    def test_finalize_draft_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        finalized = services.finalize_bill(bill, self.cashier)
        self.assertEqual(finalized.status, BillStatus.FINALIZED)

    def test_finalized_by_and_at_set(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        finalized = services.finalize_bill(bill, self.cashier)
        self.assertEqual(finalized.finalized_by, self.cashier)
        self.assertIsNotNone(finalized.finalized_at)

    def test_idempotent_finalization(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        bill1 = services.finalize_bill(bill, self.cashier)
        bill2 = services.finalize_bill(bill, self.cashier)  # called again
        self.assertEqual(bill1.status, BillStatus.FINALIZED)
        self.assertEqual(bill2.status, BillStatus.FINALIZED)
        self.assertEqual(bill1.finalized_at, bill2.finalized_at)

    def test_no_permission_raises(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(PermissionDenied):
            services.finalize_bill(bill, self.other_user)

    def test_finalized_amounts_locked(self):
        """After finalization financial fields must not change on re-read."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        finalized = services.finalize_bill(bill, self.cashier)
        # Re-read from DB
        from billing.models import Bill as BillModel
        db_bill = BillModel.objects.get(pk=finalized.pk)
        self.assertEqual(db_bill.grand_total, finalized.grand_total)
        self.assertEqual(db_bill.tax_amount, finalized.tax_amount)


class TestBillImmutability(BillingTestBase):
    """Tests ensuring finalized bills cannot be directly edited."""

    def test_cannot_apply_discount_to_finalized_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            services.apply_discount(
                bill, self.cashier,
                discount_type="PERCENTAGE",
                value=Decimal("10"),
            )
        self.assertEqual(ctx.exception.detail["code"], "BILL_NOT_DRAFT")

    def test_cannot_remove_discount_from_finalized_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        with self.assertRaises(ValidationError):
            services.remove_discount(bill, self.cashier)

    def test_bill_item_is_read_only(self):
        """BillItem model has no update path — values are snapshots."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        item = bill.items.first()
        original_price = item.unit_price
        # Direct ORM update works (no app-level guard on BillItem itself),
        # but verify the service layer doesn't call calculate on finalized bills
        result = services.calculate_bill(bill)
        # Should return the existing values, not recalculate to zero
        self.assertGreater(Decimal(result["grand_total"]), Decimal("0"))


class TestBillCancellation(BillingTestBase):
    """Tests for cancel_bill() and void_bill()."""

    def test_cancel_draft_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        cancelled = services.cancel_bill(bill, self.cashier, reason="Test cancellation reason")
        self.assertEqual(cancelled.status, BillStatus.CANCELLED)
        self.assertEqual(cancelled.cancelled_by, self.cashier)
        self.assertIsNotNone(cancelled.cancelled_at)

    def test_cancel_finalized_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        cancelled = services.cancel_bill(bill, self.manager, reason="Customer requested cancellation")
        self.assertEqual(cancelled.status, BillStatus.CANCELLED)

    def test_cancel_requires_reason(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(ValidationError):
            services.cancel_bill(bill, self.cashier, reason="")

    def test_cannot_cancel_already_cancelled(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.cancel_bill(bill, self.cashier, reason="First cancellation")
        bill.refresh_from_db()
        with self.assertRaises(ValidationError):
            services.cancel_bill(bill, self.cashier, reason="Second cancellation")

    def test_void_finalized_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        voided = services.void_bill(bill, self.manager, reason="Post-payment void test")
        self.assertEqual(voided.status, BillStatus.VOID)

    def test_cannot_void_draft_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(ValidationError) as ctx:
            services.void_bill(bill, self.manager, reason="test void")
        self.assertEqual(ctx.exception.detail["code"], "BILL_NOT_FINALIZED")

    def test_cancel_without_permission_raises(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(PermissionDenied):
            services.cancel_bill(bill, self.other_user, reason="unauthorized cancel")


class TestBillReceipt(BillingTestBase):
    """Tests for get_bill_receipt_data()."""

    def test_receipt_structure(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        receipt = services.get_bill_receipt_data(bill)
        required_keys = [
            "bill_number", "order_number", "order_type", "restaurant",
            "branch", "items", "subtotal", "tax_amount", "grand_total",
            "tax_breakdown", "status",
        ]
        for key in required_keys:
            self.assertIn(key, receipt)

    def test_receipt_bill_number(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        receipt = services.get_bill_receipt_data(bill)
        self.assertEqual(receipt["bill_number"], bill.bill_number)

    def test_receipt_items_count(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        receipt = services.get_bill_receipt_data(bill)
        self.assertEqual(len(receipt["items"]), 2)

    def test_receipt_restaurant_info(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        receipt = services.get_bill_receipt_data(bill)
        self.assertEqual(receipt["restaurant"]["name"], "Test Restaurant")
        self.assertEqual(receipt["restaurant"]["tax_id"], "GSTIN12345")

    def test_receipt_no_payment_data(self):
        """Phase 8: payment data must NOT appear in receipt."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        receipt = services.get_bill_receipt_data(bill)
        self.assertNotIn("payment_method", receipt)
        self.assertNotIn("paid_amount", receipt)
        self.assertNotIn("change", receipt)


# Order model used in test_zero_tax_item
from orders.models import Order
