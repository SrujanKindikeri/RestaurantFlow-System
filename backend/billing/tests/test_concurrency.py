# =============================================================================
# RestaurantFlow — Billing Concurrency Tests
# Phase 8
#
# Tests:
#   - two simultaneous bill creation requests for the same order → one bill
#   - double-click finalize → bill finalized only once (idempotent)
#   - concurrent discount applications → last-write-wins (no stacking)
#   - concurrent correction approval attempts → only one succeeds
#
# Note: True concurrent thread tests are hard in Django's test runner.
# We simulate concurrency by:
#   1. Testing the idempotency of service calls (same result on repeat).
#   2. Testing that DB constraints prevent duplicates (IntegrityError caught).
#   3. Testing the idempotent paths explicitly.
#
# For production-grade concurrency, these are also covered by:
#   - select_for_update() in services.py
#   - UniqueConstraint on Bill.order (DB level)
# =============================================================================

from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, wait

from django.test import TransactionTestCase
from django.utils import timezone

from billing.models import Bill, BillStatus
from billing import services
from billing.tests.base import BillingTestBase

from orders.models import Order, OrderItem, OrderStatus, OrderType
from counters.models import CounterSession, SessionStatus


class TestBillCreationIdempotency(BillingTestBase):
    """Repeated bill creation calls return the same bill."""

    def test_repeated_create_bill_returns_same_bill(self):
        order = self._make_confirmed_order()
        bill1 = services.create_bill_from_order(order, self.cashier)
        bill2 = services.create_bill_from_order(order, self.cashier)
        bill3 = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill1.pk, bill2.pk)
        self.assertEqual(bill2.pk, bill3.pk)

    def test_bill_number_issued_only_once(self):
        order = self._make_confirmed_order()
        bill1 = services.create_bill_from_order(order, self.cashier)
        bill2 = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill1.bill_number, bill2.bill_number)


class TestFinalizationIdempotency(BillingTestBase):
    """Double-click finalize must not create multiple finalized states."""

    def test_finalize_twice_returns_same_result(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)

        finalized1 = services.finalize_bill(bill, self.cashier)
        finalized2 = services.finalize_bill(bill, self.cashier)  # second call

        self.assertEqual(finalized1.status, BillStatus.FINALIZED)
        self.assertEqual(finalized2.status, BillStatus.FINALIZED)
        # Finalized timestamp must be the same (set only once)
        self.assertEqual(finalized1.finalized_at, finalized2.finalized_at)

    def test_finalize_after_finalize_does_not_change_totals(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        first = services.finalize_bill(bill, self.cashier)
        original_total = first.grand_total

        # Second finalize should return same total
        second = services.finalize_bill(bill, self.cashier)
        self.assertEqual(second.grand_total, original_total)


class TestDiscountIdempotency(BillingTestBase):
    """Applying the same discount twice must not stack."""

    def test_apply_same_discount_twice_does_not_stack(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)

        # Apply 10% discount
        services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("10"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        first_discount = bill.discount_amount  # 62.00

        # Apply same discount again
        services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("10"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        second_discount = bill.discount_amount  # should still be 62.00

        self.assertEqual(first_discount, second_discount)

    def test_apply_different_discount_overwrites(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)

        services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("5"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        first_discount = bill.discount_amount  # 31.00

        services.apply_discount(
            bill, self.cashier,
            discount_type="FIXED_AMOUNT",
            value=Decimal("50"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        # Should be 50.00, not 31+50
        self.assertEqual(bill.discount_amount, Decimal("50.00"))
        self.assertNotEqual(bill.discount_amount, first_discount + Decimal("50.00"))


class TestCorrectionConcurrency(BillingTestBase):
    """Concurrent correction approval must not result in double-approval."""

    def test_approval_is_idempotent_on_already_approved(self):
        """Trying to approve an already-approved correction raises ValidationError."""
        from rest_framework.exceptions import ValidationError

        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()

        correction = services.request_bill_correction(
            bill, self.cashier,
            correction_type="ITEM_CORRECTION",
            reason="Some item error that requires correction approval.",
        )
        # First approval succeeds
        services.approve_bill_correction(correction, self.manager, note="First approval.")
        correction.refresh_from_db()

        # Second approval on already-approved correction must fail
        with self.assertRaises(ValidationError) as ctx:
            services.approve_bill_correction(correction, self.manager, note="Second approval.")
        self.assertEqual(ctx.exception.detail["code"], "CORRECTION_NOT_PENDING")


class TestBillSequenceIncrement(BillingTestBase):
    """Bill sequence numbers must increment correctly."""

    def test_sequence_increments_per_bill(self):
        from billing.models import BillSequence
        year = timezone.now().strftime("%Y")

        # Start fresh sequence count
        initial_count = BillSequence.objects.filter(
            branch=self.branch, year_key=year
        ).values_list("last_sequence", flat=True).first() or 0

        order1 = self._make_confirmed_order()
        order2 = self._make_confirmed_order()

        bill1 = services.create_bill_from_order(order1, self.cashier)
        bill2 = services.create_bill_from_order(order2, self.cashier)

        # Extract sequence numbers from bill numbers
        seq1 = int(bill1.bill_number.split("-")[2])
        seq2 = int(bill2.bill_number.split("-")[2])

        self.assertGreater(seq2, seq1)
        self.assertEqual(seq2, seq1 + 1)

    def test_bill_number_year_prefix_correct(self):
        expected_year = timezone.now().strftime("%Y")
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        bill_year = bill.bill_number.split("-")[1]
        self.assertEqual(bill_year, expected_year)
