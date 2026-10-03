# =============================================================================
# RestaurantFlow — Payment Core Tests
# Phase 9
#
# Tests:
#   - Payment creation (CASH, UPI, CARD, OTHER)
#   - Cash change calculation
#   - Insufficient cash rejection
#   - Overpayment prevention
#   - Duplicate payment prevention
#   - Idempotency (same key returns same payment)
#   - Partial payments
#   - Split payments (CASH + UPI)
#   - Bill already paid rejection
#   - Bill not finalized rejection
#   - Bill cancelled rejection
#   - Counter session validation
#   - Cross-branch access rejection
#   - Permission checks
# =============================================================================

from decimal import Decimal
import uuid

from django.test import TestCase

from payments import services
from payments.models import Payment, PaymentStatus, PaymentMethod
from payments.utils import compute_remaining_amount, compute_bill_payment_status
from payments.tests.base import PaymentTestBase


class TestCreateCashPayment(PaymentTestBase):
    """CASH payment creation — core functionality."""

    def test_cash_payment_full_bill(self):
        """Full cash payment against a finalized bill succeeds."""
        bill = self._make_finalized_bill()
        amount = bill.grand_total

        payment = services.create_payment(
            bill,
            self.cashier,
            amount=amount,
            payment_method=PaymentMethod.CASH,
            cash_received=amount + Decimal("50.00"),
            counter_session=self.counter_session,
        )

        self.assertEqual(payment.status, PaymentStatus.COMPLETED)
        self.assertEqual(payment.amount, amount)
        self.assertEqual(payment.payment_method, PaymentMethod.CASH)
        self.assertIsNotNone(payment.payment_number)
        self.assertTrue(payment.payment_number.startswith("PAY-"))
        self.assertIsNotNone(payment.cash_received)
        self.assertIsNotNone(payment.change_amount)
        # change = cash_received - amount
        expected_change = payment.cash_received - amount
        self.assertEqual(payment.change_amount, expected_change)
        self.assertEqual(payment.counter_session, self.counter_session)
        self.assertEqual(payment.counter, self.counter)

    def test_cash_change_calculated_by_backend(self):
        """Change amount is always calculated by backend, never trusted from client."""
        bill = self._make_finalized_bill()
        amount = bill.grand_total

        payment = services.create_payment(
            bill,
            self.cashier,
            amount=amount,
            payment_method=PaymentMethod.CASH,
            cash_received=Decimal("1000.00"),
            counter_session=self.counter_session,
        )

        # Backend calculates: change = 1000 - amount
        expected_change = Decimal("1000.00") - amount
        self.assertEqual(payment.change_amount, expected_change)

    def test_cash_exact_amount(self):
        """Exact cash — change should be zero."""
        bill = self._make_finalized_bill()
        amount = bill.grand_total

        payment = services.create_payment(
            bill,
            self.cashier,
            amount=amount,
            payment_method=PaymentMethod.CASH,
            cash_received=amount,
            counter_session=self.counter_session,
        )

        self.assertEqual(payment.change_amount, Decimal("0.00"))

    def test_cash_insufficient_rejected(self):
        """Cash received less than amount is rejected."""
        bill = self._make_finalized_bill()
        amount = bill.grand_total

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill,
                self.cashier,
                amount=amount,
                payment_method=PaymentMethod.CASH,
                cash_received=amount - Decimal("1.00"),
                counter_session=self.counter_session,
            )
        self.assertIn("INSUFFICIENT_CASH", str(ctx.exception.detail))

    def test_cash_requires_counter_session(self):
        """CASH payment without counter_session is rejected."""
        bill = self._make_finalized_bill()

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill,
                self.cashier,
                amount=bill.grand_total,
                payment_method=PaymentMethod.CASH,
                cash_received=bill.grand_total,
                counter_session=None,
            )
        self.assertIn("SESSION", str(ctx.exception.detail).upper())

    def test_cash_closed_session_rejected(self):
        """CASH payment with a closed counter session is rejected."""
        from counters.models import SessionStatus
        from rest_framework.exceptions import ValidationError

        self.counter_session.status = SessionStatus.CLOSED
        self.counter_session.save(update_fields=["status"])

        bill = self._make_finalized_bill()

        try:
            with self.assertRaises(ValidationError) as ctx:
                services.create_payment(
                    bill,
                    self.cashier,
                    amount=bill.grand_total,
                    payment_method=PaymentMethod.CASH,
                    cash_received=bill.grand_total,
                    counter_session=self.counter_session,
                )
            self.assertIn("SESSION", str(ctx.exception.detail).upper())
        finally:
            # Restore for other tests
            self.counter_session.status = SessionStatus.OPEN
            self.counter_session.save(update_fields=["status"])


class TestCreateDigitalPayments(PaymentTestBase):
    """UPI, CARD, and OTHER payment creation."""

    def test_upi_payment_with_reference(self):
        """UPI payment with transaction reference succeeds."""
        bill = self._make_finalized_bill()

        payment = services.create_payment(
            bill,
            self.cashier,
            amount=bill.grand_total,
            payment_method=PaymentMethod.UPI,
            transaction_reference="UPI-TXN-123456",
        )

        self.assertEqual(payment.status, PaymentStatus.COMPLETED)
        self.assertEqual(payment.payment_method, PaymentMethod.UPI)
        self.assertEqual(payment.transaction_reference, "UPI-TXN-123456")
        self.assertIsNone(payment.cash_received)
        self.assertIsNone(payment.change_amount)

    def test_card_payment_with_reference(self):
        """CARD payment with transaction reference succeeds."""
        bill = self._make_finalized_bill()

        payment = services.create_payment(
            bill,
            self.cashier,
            amount=bill.grand_total,
            payment_method=PaymentMethod.CARD,
            transaction_reference="CARD-REF-789",
        )

        self.assertEqual(payment.status, PaymentStatus.COMPLETED)
        self.assertEqual(payment.payment_method, PaymentMethod.CARD)

    def test_upi_requires_transaction_reference(self):
        """UPI payment without transaction_reference is rejected."""
        bill = self._make_finalized_bill()

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill,
                self.cashier,
                amount=bill.grand_total,
                payment_method=PaymentMethod.UPI,
                transaction_reference="",
            )
        self.assertIn("TRANSACTION_REFERENCE", str(ctx.exception.detail).upper())

    def test_other_payment_no_reference_required(self):
        """OTHER payment succeeds without transaction_reference."""
        bill = self._make_finalized_bill()

        payment = services.create_payment(
            bill,
            self.cashier,
            amount=bill.grand_total,
            payment_method=PaymentMethod.OTHER,
        )

        self.assertEqual(payment.status, PaymentStatus.COMPLETED)


class TestPaymentValidation(PaymentTestBase):
    """Validation rules: bill status, amount, overpayment."""

    def test_draft_bill_rejected(self):
        """Cannot pay a DRAFT bill."""
        bill = self._make_draft_bill()

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill,
                self.cashier,
                amount=bill.grand_total or Decimal("100.00"),
                payment_method=PaymentMethod.OTHER,
            )
        self.assertIn("BILL_NOT_FINALIZED", str(ctx.exception.detail))

    def test_cancelled_bill_rejected(self):
        """Cannot pay a CANCELLED bill."""
        bill = self._make_cancelled_bill()

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill,
                self.cashier,
                amount=Decimal("100.00"),
                payment_method=PaymentMethod.OTHER,
            )
        self.assertIn("BILL_CANCELLED", str(ctx.exception.detail))

    def test_overpayment_rejected(self):
        """Payment exceeding remaining balance is rejected."""
        bill = self._make_finalized_bill()
        # Pay half first
        half = bill.grand_total / 2
        services.create_payment(
            bill,
            self.cashier,
            amount=half,
            payment_method=PaymentMethod.OTHER,
        )
        # Try to pay the full amount again (exceeds remaining)
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill,
                self.cashier,
                amount=bill.grand_total,
                payment_method=PaymentMethod.OTHER,
            )
        self.assertIn("OVERPAYMENT", str(ctx.exception.detail))

    def test_bill_already_paid_rejected(self):
        """Cannot pay a fully paid bill."""
        bill = self._make_finalized_bill()
        # Pay the full amount
        services.create_payment(
            bill,
            self.cashier,
            amount=bill.grand_total,
            payment_method=PaymentMethod.OTHER,
        )
        # Try to pay again
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill,
                self.cashier,
                amount=Decimal("1.00"),
                payment_method=PaymentMethod.OTHER,
            )
        self.assertIn("PAID", str(ctx.exception.detail).upper())

    def test_zero_amount_rejected(self):
        """Payment of ₹0 is rejected."""
        bill = self._make_finalized_bill()

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            services.create_payment(
                bill,
                self.cashier,
                amount=Decimal("0.00"),
                payment_method=PaymentMethod.OTHER,
            )

    def test_permission_required(self):
        """User without payment.create permission is rejected."""
        bill = self._make_finalized_bill()

        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.create_payment(
                bill,
                self.other_user,
                amount=bill.grand_total,
                payment_method=PaymentMethod.OTHER,
            )

    def test_cross_branch_rejected(self):
        """User cannot pay a bill from a branch they don't have access to."""
        # Make a bill for other_branch
        from organizations.models import Branch
        from orders.models import Order, OrderItem, OrderStatus, OrderType

        import time
        order_num = f"XBRANCH-{time.time_ns()}"
        order = Order.objects.create(
            branch=self.other_branch,
            order_number=order_num,
            order_type=OrderType.COUNTER,
            created_by=self.manager,
            status=OrderStatus.CONFIRMED,
        )
        from orders.models import OrderItem
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_biryani,
            item_name_snapshot="Biryani",
            sku_snapshot="BIRYA-001",
            unit_price_snapshot=Decimal("250.00"),
            tax_rate_snapshot=Decimal("5.000"),
            tax_code_snapshot="GST_5",
            quantity=Decimal("1.000"),
        )

        from billing import services as bs
        bill = bs.create_bill_from_order(order, self.manager)
        bill = bs.finalize_bill(bill, self.manager)

        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.create_payment(
                bill,
                self.cashier,  # cashier only has access to cls.branch
                amount=bill.grand_total,
                payment_method=PaymentMethod.OTHER,
            )


class TestPartialAndSplitPayments(PaymentTestBase):
    """Partial payments and split-method payments."""

    def test_partial_payment(self):
        """Partial payment: remaining amount is correctly reduced."""
        bill = self._make_finalized_bill()
        total = bill.grand_total
        half = (total / 2).quantize(Decimal("0.01"))

        payment = services.create_payment(
            bill,
            self.cashier,
            amount=half,
            payment_method=PaymentMethod.UPI,
            transaction_reference="UPI-PARTIAL-001",
        )

        remaining = compute_remaining_amount(bill)
        self.assertEqual(remaining, total - half)

    def test_split_payment_cash_and_upi(self):
        """Split payment: CASH + UPI covering the full bill amount."""
        bill = self._make_finalized_bill()
        total = bill.grand_total
        cash_part = Decimal("200.00")
        upi_part = total - cash_part

        # First: cash payment
        services.create_payment(
            bill,
            self.cashier,
            amount=cash_part,
            payment_method=PaymentMethod.CASH,
            cash_received=Decimal("300.00"),
            counter_session=self.counter_session,
        )

        # Second: UPI payment
        services.create_payment(
            bill,
            self.cashier,
            amount=upi_part,
            payment_method=PaymentMethod.UPI,
            transaction_reference="UPI-SPLIT-002",
        )

        remaining = compute_remaining_amount(bill)
        self.assertEqual(remaining, Decimal("0.00"))

        # Bill payment status should now be PAID
        from payments.utils import compute_bill_payment_status
        from payments.utils import compute_successful_payments_total
        paid = compute_successful_payments_total(bill)
        status = compute_bill_payment_status(total, paid)
        self.assertEqual(status, "PAID")

    def test_multiple_partial_then_full(self):
        """Multiple partial payments that cumulatively cover the full bill."""
        bill = self._make_finalized_bill()
        total = bill.grand_total
        third = (total / 3).quantize(Decimal("0.01"))
        # Small rounding: pay two thirds as two payments, rest as third
        remainder = total - third - third

        services.create_payment(bill, self.cashier, amount=third,
                                payment_method=PaymentMethod.OTHER)
        services.create_payment(bill, self.cashier, amount=third,
                                payment_method=PaymentMethod.OTHER)
        services.create_payment(bill, self.cashier, amount=remainder,
                                payment_method=PaymentMethod.OTHER)

        remaining = compute_remaining_amount(bill)
        self.assertEqual(remaining, Decimal("0.00"))

    def test_payment_number_is_unique(self):
        """Each payment gets a unique, sequentially incrementing number."""
        bill1 = self._make_finalized_bill()
        bill2 = self._make_finalized_bill()

        p1 = services.create_payment(bill1, self.cashier,
                                     amount=bill1.grand_total,
                                     payment_method=PaymentMethod.OTHER)
        p2 = services.create_payment(bill2, self.cashier,
                                     amount=bill2.grand_total,
                                     payment_method=PaymentMethod.OTHER)

        self.assertNotEqual(p1.payment_number, p2.payment_number)
        # Numbers should be sequential
        seq1 = int(p1.payment_number.replace("PAY-", ""))
        seq2 = int(p2.payment_number.replace("PAY-", ""))
        self.assertEqual(seq2, seq1 + 1)


class TestIdempotency(PaymentTestBase):
    """Idempotency key prevents duplicate payments on retry."""

    def test_same_idempotency_key_returns_same_payment(self):
        """Submitting the same (bill, idempotency_key) twice returns the same payment."""
        bill = self._make_finalized_bill()
        key = str(uuid.uuid4())

        p1 = services.create_payment(
            bill,
            self.cashier,
            amount=bill.grand_total,
            payment_method=PaymentMethod.UPI,
            transaction_reference="UPI-IDEM-001",
            idempotency_key=key,
        )
        p2 = services.create_payment(
            bill,
            self.cashier,
            amount=bill.grand_total,
            payment_method=PaymentMethod.UPI,
            transaction_reference="UPI-IDEM-001",
            idempotency_key=key,
        )

        # Same payment returned
        self.assertEqual(p1.pk, p2.pk)
        self.assertEqual(p1.payment_number, p2.payment_number)

        # Only ONE payment in the DB
        count = Payment.objects.filter(bill=bill).count()
        self.assertEqual(count, 1)

    def test_different_idempotency_keys_create_different_payments(self):
        """Two different idempotency keys on the same bill (split) create two payments."""
        bill = self._make_finalized_bill()
        total = bill.grand_total
        half = (total / 2).quantize(Decimal("0.01"))

        p1 = services.create_payment(
            bill, self.cashier, amount=half,
            payment_method=PaymentMethod.OTHER,
            idempotency_key=str(uuid.uuid4()),
        )
        p2 = services.create_payment(
            bill, self.cashier, amount=total - half,
            payment_method=PaymentMethod.OTHER,
            idempotency_key=str(uuid.uuid4()),
        )

        self.assertNotEqual(p1.pk, p2.pk)
        self.assertEqual(Payment.objects.filter(bill=bill).count(), 2)

    def test_empty_idempotency_key_not_deduplicated(self):
        """Empty idempotency key is not used for deduplication."""
        bill = self._make_finalized_bill()
        half = (bill.grand_total / 2).quantize(Decimal("0.01"))

        # Two payments with empty key are independent
        services.create_payment(
            bill, self.cashier, amount=half,
            payment_method=PaymentMethod.OTHER, idempotency_key="",
        )
        services.create_payment(
            bill, self.cashier, amount=bill.grand_total - half,
            payment_method=PaymentMethod.OTHER, idempotency_key="",
        )

        self.assertEqual(Payment.objects.filter(bill=bill).count(), 2)


class TestBillPaymentStatus(PaymentTestBase):
    """Bill payment status derives correctly from successful payments."""

    def test_unpaid_status(self):
        """Bill with no payments → UNPAID."""
        bill = self._make_finalized_bill()
        summary = services.get_bill_payment_summary(bill)
        self.assertEqual(summary["payment_status"], "UNPAID")
        self.assertEqual(summary["remaining"], str(bill.grand_total))

    def test_partially_paid_status(self):
        """Bill with partial payments → PARTIALLY_PAID."""
        bill = self._make_finalized_bill()
        partial = (bill.grand_total / 2).quantize(Decimal("0.01"))
        services.create_payment(bill, self.cashier, amount=partial,
                                payment_method=PaymentMethod.OTHER)

        summary = services.get_bill_payment_summary(bill)
        self.assertEqual(summary["payment_status"], "PARTIALLY_PAID")

    def test_fully_paid_status(self):
        """Bill fully paid → PAID."""
        bill = self._make_finalized_bill()
        services.create_payment(bill, self.cashier, amount=bill.grand_total,
                                payment_method=PaymentMethod.OTHER)

        summary = services.get_bill_payment_summary(bill)
        self.assertEqual(summary["payment_status"], "PAID")
        self.assertEqual(summary["remaining"], "0.00")

    def test_payment_summary_structure(self):
        """Summary has all expected keys."""
        bill = self._make_finalized_bill()
        summary = services.get_bill_payment_summary(bill)

        required_keys = [
            "bill_id", "bill_number", "bill_total", "total_paid",
            "total_refunded", "remaining", "payment_status", "payments",
        ]
        for key in required_keys:
            self.assertIn(key, summary, f"Missing key: {key}")

    def test_audit_log_created_on_payment(self):
        """Creating a payment writes audit log entries."""
        from payments.models import PaymentAuditLog, AuditAction

        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.OTHER,
        )

        logs = PaymentAuditLog.objects.filter(payment=payment)
        self.assertTrue(logs.exists())
        # At minimum: PAYMENT_CREATED + PAYMENT_COMPLETED
        actions = list(logs.values_list("action", flat=True))
        self.assertIn(AuditAction.PAYMENT_CREATED, actions)
        self.assertIn(AuditAction.PAYMENT_COMPLETED, actions)

    def test_audit_log_is_immutable(self):
        """PaymentAuditLog raises ValueError on update."""
        from payments.models import PaymentAuditLog, AuditAction

        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.OTHER,
        )
        log = PaymentAuditLog.objects.filter(payment=payment).first()
        log.reason = "mutated"
        with self.assertRaises(ValueError):
            log.save()
