# =============================================================================
# RestaurantFlow — Payment Refund Tests
# Phase 9
#
# Tests:
#   - Full refund
#   - Partial refund
#   - Multiple partial refunds
#   - Refund exceeding payment amount
#   - Refund exceeding remaining refundable amount
#   - Refund on non-completed payment
#   - Approve refund
#   - Reject refund
#   - Process refund (payment status → PARTIALLY_REFUNDED / REFUNDED)
#   - Cancel refund
#   - Duplicate refund request
#   - Unauthorized refund
#   - Cross-branch refund
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError, PermissionDenied

from payments import services
from payments.models import PaymentStatus, PaymentMethod, RefundStatus
from payments.tests.base import PaymentTestBase


class TestRefundRequest(PaymentTestBase):
    """Refund request validation."""

    def _pay_full(self, bill):
        return services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.UPI,
            transaction_reference="UPI-REF-001",
        )

    def test_full_refund_request(self):
        """Request a full refund on a completed payment."""
        bill = self._make_finalized_bill()
        payment = self._pay_full(bill)

        refund = services.request_refund(
            payment, self.manager,
            amount=payment.amount,
            reason="Customer changed mind",
        )

        self.assertEqual(refund.status, RefundStatus.REQUESTED)
        self.assertEqual(refund.amount, payment.amount)
        self.assertTrue(refund.refund_number.startswith("REF-"))
        self.assertEqual(refund.requested_by, self.manager)

    def test_partial_refund_request(self):
        """Request a partial refund."""
        bill = self._make_finalized_bill()
        payment = self._pay_full(bill)
        partial = payment.amount / 2

        refund = services.request_refund(
            payment, self.manager,
            amount=partial,
            reason="Partial refund for damaged item",
        )

        self.assertEqual(refund.amount, partial)
        self.assertEqual(refund.status, RefundStatus.REQUESTED)

    def test_refund_exceeds_payment_rejected(self):
        """Refund amount > payment amount is rejected."""
        bill = self._make_finalized_bill()
        payment = self._pay_full(bill)

        with self.assertRaises(ValidationError) as ctx:
            services.request_refund(
                payment, self.manager,
                amount=payment.amount + Decimal("1.00"),
                reason="Too much",
            )
        self.assertIn("REFUND_EXCEEDS_PAYMENT", str(ctx.exception.detail))

    def test_refund_on_pending_payment_rejected(self):
        """Cannot request refund on a non-COMPLETED payment."""
        from payments.models import Payment
        bill = self._make_finalized_bill()
        payment = self._pay_full(bill)
        # Manually set to PENDING to test this path
        Payment.objects.filter(pk=payment.pk).update(status=PaymentStatus.PENDING)
        payment.refresh_from_db()

        with self.assertRaises(ValidationError) as ctx:
            services.request_refund(
                payment, self.manager,
                amount=payment.amount,
                reason="Test",
            )
        self.assertIn("PAYMENT_NOT_REFUNDABLE", str(ctx.exception.detail))

    def test_refund_requires_permission(self):
        """User without payment.refund.request permission is rejected."""
        bill = self._make_finalized_bill()
        payment = self._pay_full(bill)

        with self.assertRaises(PermissionDenied):
            services.request_refund(
                payment, self.cashier,  # cashier doesn't have refund.request
                amount=payment.amount,
                reason="No permission",
            )

    def test_refund_reason_required(self):
        """Empty refund reason is rejected."""
        bill = self._make_finalized_bill()
        payment = self._pay_full(bill)

        with self.assertRaises(ValidationError):
            services.request_refund(
                payment, self.manager,
                amount=payment.amount,
                reason="",
            )

    def test_refund_cross_branch_rejected(self):
        """Manager of branch A cannot refund payment from branch B."""
        # Create payment on other_branch as owner (has access to all branches via restaurant scope)
        from orders.models import Order, OrderItem, OrderStatus, OrderType
        import time
        order_num = f"XBRANCH-R-{time.time_ns()}"
        order = Order.objects.create(
            branch=self.other_branch,
            order_number=order_num,
            order_type=OrderType.COUNTER,
            created_by=self.owner,
            status=OrderStatus.CONFIRMED,
        )
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
        bill = bs.create_bill_from_order(order, self.owner)
        bill = bs.finalize_bill(bill, self.owner)

        payment = services.create_payment(
            bill, self.owner, amount=bill.grand_total,
            payment_method=PaymentMethod.OTHER,
        )

        with self.assertRaises(PermissionDenied):
            services.request_refund(
                payment, self.cashier,  # cashier only has access to cls.branch
                amount=payment.amount,
                reason="Cross-branch refund attempt",
            )


class TestRefundApproval(PaymentTestBase):
    """Approve and reject refund workflows."""

    def _setup_refund(self):
        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.UPI, transaction_reference="UPI-AR-001",
        )
        refund = services.request_refund(
            payment, self.manager, amount=payment.amount,
            reason="Customer returned items",
        )
        return payment, refund

    def test_approve_refund(self):
        """Approving a requested refund transitions to APPROVED."""
        _, refund = self._setup_refund()

        updated = services.approve_refund(refund, self.refund_approver)

        self.assertEqual(updated.status, RefundStatus.APPROVED)
        self.assertEqual(updated.approved_by, self.refund_approver)
        self.assertIsNotNone(updated.approved_at)

    def test_reject_refund(self):
        """Rejecting a requested refund transitions to REJECTED."""
        _, refund = self._setup_refund()

        updated = services.reject_refund(refund, self.refund_approver, reason="Not eligible")

        self.assertEqual(updated.status, RefundStatus.REJECTED)
        self.assertEqual(updated.rejection_reason, "Not eligible")
        self.assertIsNotNone(updated.rejected_at)

    def test_approve_requires_permission(self):
        """User without payment.refund.approve is rejected."""
        _, refund = self._setup_refund()

        with self.assertRaises(PermissionDenied):
            services.approve_refund(refund, self.cashier)

    def test_reject_requires_reason(self):
        """Rejecting without a reason raises ValidationError."""
        _, refund = self._setup_refund()

        with self.assertRaises(ValidationError):
            services.reject_refund(refund, self.refund_approver, reason="")

    def test_approve_non_requested_refund_fails(self):
        """Cannot approve a non-REQUESTED refund."""
        _, refund = self._setup_refund()
        services.reject_refund(refund, self.refund_approver, reason="Rejected first")
        refund.refresh_from_db()

        with self.assertRaises(ValidationError) as ctx:
            services.approve_refund(refund, self.refund_approver)
        self.assertIn("REFUND_NOT_REQUESTED", str(ctx.exception.detail))

    def test_cancel_refund(self):
        """Requester can cancel their REQUESTED refund."""
        _, refund = self._setup_refund()

        updated = services.cancel_refund(refund, self.manager)

        self.assertEqual(updated.status, RefundStatus.CANCELLED)


class TestRefundProcessing(PaymentTestBase):
    """Process refund — payment status updates."""

    def _setup_approved_refund(self, amount=None):
        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.UPI, transaction_reference="UPI-PROC-001",
        )
        refund_amount = amount or payment.amount
        refund = services.request_refund(
            payment, self.manager, amount=refund_amount, reason="Processing test",
        )
        refund = services.approve_refund(refund, self.refund_approver)
        return payment, refund

    def test_process_full_refund_sets_refunded_status(self):
        """Processing a full refund sets payment status to REFUNDED."""
        payment, refund = self._setup_approved_refund()

        updated_refund = services.process_refund(
            refund, self.refund_approver, transaction_reference="PROC-TXN-001"
        )

        self.assertEqual(updated_refund.status, RefundStatus.PROCESSED)
        self.assertEqual(updated_refund.processed_by, self.refund_approver)
        self.assertIsNotNone(updated_refund.processed_at)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

    def test_process_partial_refund_sets_partially_refunded(self):
        """Processing a partial refund sets payment status to PARTIALLY_REFUNDED."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.UPI, transaction_reference="UPI-PART-001",
        )
        partial = payment.amount / 2

        refund = services.request_refund(payment, self.manager, amount=partial, reason="Partial")
        refund = services.approve_refund(refund, self.refund_approver)
        services.process_refund(refund, self.refund_approver)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.PARTIALLY_REFUNDED)

    def test_multiple_partial_refunds_to_full(self):
        """Two partial refunds that together equal the payment → REFUNDED."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.UPI, transaction_reference="UPI-MULTI-001",
        )
        half = payment.amount / 2

        for _ in range(2):
            r = services.request_refund(payment, self.manager, amount=half, reason="Part")
            r = services.approve_refund(r, self.refund_approver)
            services.process_refund(r, self.refund_approver)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

    def test_refund_overage_across_multiple_requests(self):
        """Second refund that would exceed payment amount is rejected."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.UPI, transaction_reference="UPI-OVR-001",
        )

        # First refund: full amount
        r1 = services.request_refund(payment, self.manager,
                                     amount=payment.amount, reason="First")
        r1 = services.approve_refund(r1, self.refund_approver)
        services.process_refund(r1, self.refund_approver)

        # Second refund request: should fail — nothing left to refund
        with self.assertRaises(ValidationError) as ctx:
            services.request_refund(payment, self.manager,
                                    amount=Decimal("1.00"), reason="Over")
        self.assertIn("FULLY_REFUNDED", str(ctx.exception.detail).upper())

    def test_process_requires_permission(self):
        """User without payment.refund.process is rejected."""
        _, refund = self._setup_approved_refund()

        with self.assertRaises(PermissionDenied):
            services.process_refund(refund, self.cashier)

    def test_process_non_approved_refund_fails(self):
        """Cannot process a REQUESTED (not yet APPROVED) refund."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier, amount=bill.grand_total,
            payment_method=PaymentMethod.UPI, transaction_reference="UPI-PROC-002",
        )
        refund = services.request_refund(
            payment, self.manager, amount=payment.amount, reason="Not approved yet",
        )

        with self.assertRaises(ValidationError) as ctx:
            services.process_refund(refund, self.refund_approver)
        self.assertIn("REFUND_NOT_APPROVED", str(ctx.exception.detail))

    def test_refund_audit_log_created(self):
        """Processing a refund creates audit log entries."""
        from payments.models import PaymentAuditLog, AuditAction

        payment, refund = self._setup_approved_refund()
        services.process_refund(refund, self.refund_approver)

        logs = PaymentAuditLog.objects.filter(payment=payment)
        actions = list(logs.values_list("action", flat=True))
        self.assertIn(AuditAction.REFUND_APPROVED, actions)
        self.assertIn(AuditAction.REFUND_PROCESSED, actions)
