# =============================================================================
# RestaurantFlow — Counter Session Validation Tests
# Phase 9
#
# Tests:
#   - Cash payment requires OPEN counter session
#   - Closed session is rejected
#   - Force-closed session is rejected
#   - Counter from different branch is rejected
#   - Cash payments are linked to counter_session correctly
#   - Non-cash payments don't require counter_session
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from counters.models import CounterSession, SessionStatus, Counter, CounterStatus
from payments import services
from payments.models import PaymentMethod
from payments.tests.base import PaymentTestBase


class TestCounterSessionValidation(PaymentTestBase):

    def test_open_session_allows_cash_payment(self):
        """OPEN counter session: cash payment succeeds."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier,
            amount=bill.grand_total,
            payment_method=PaymentMethod.CASH,
            cash_received=bill.grand_total + Decimal("50.00"),
            counter_session=self.counter_session,
        )
        self.assertEqual(payment.counter_session, self.counter_session)
        self.assertEqual(payment.counter, self.counter)

    def test_closed_session_rejects_cash_payment(self):
        """CLOSED counter session → ValidationError."""
        bill = self._make_finalized_bill()

        self.counter_session.status = SessionStatus.CLOSED
        self.counter_session.save(update_fields=["status"])
        try:
            with self.assertRaises(ValidationError) as ctx:
                services.create_payment(
                    bill, self.cashier,
                    amount=bill.grand_total,
                    payment_method=PaymentMethod.CASH,
                    cash_received=bill.grand_total,
                    counter_session=self.counter_session,
                )
            detail = str(ctx.exception.detail)
            self.assertIn("COUNTER_SESSION_NOT_OPEN", detail)
        finally:
            self.counter_session.status = SessionStatus.OPEN
            self.counter_session.save(update_fields=["status"])

    def test_force_closed_session_rejects_cash_payment(self):
        """FORCE_CLOSED counter session → ValidationError."""
        bill = self._make_finalized_bill()

        self.counter_session.status = SessionStatus.FORCE_CLOSED
        self.counter_session.save(update_fields=["status"])
        try:
            with self.assertRaises(ValidationError):
                services.create_payment(
                    bill, self.cashier,
                    amount=bill.grand_total,
                    payment_method=PaymentMethod.CASH,
                    cash_received=bill.grand_total,
                    counter_session=self.counter_session,
                )
        finally:
            self.counter_session.status = SessionStatus.OPEN
            self.counter_session.save(update_fields=["status"])

    def test_different_branch_counter_session_rejected(self):
        """Counter session belonging to other_branch is rejected for bill from cls.branch."""
        # Create a counter + session for the other_branch
        other_counter = Counter.objects.create(
            branch=self.other_branch,
            name="Other Counter",
            code="OC01",
            status=CounterStatus.ACTIVE,
        )
        other_session = CounterSession.objects.create(
            counter=other_counter,
            opened_by=self.cashier,
            opening_cash=Decimal("500.00"),
            status=SessionStatus.OPEN,
        )

        bill = self._make_finalized_bill()  # bill is for cls.branch

        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill, self.cashier,
                amount=bill.grand_total,
                payment_method=PaymentMethod.CASH,
                cash_received=bill.grand_total,
                counter_session=other_session,  # ← wrong branch
            )
        self.assertIn("COUNTER_BRANCH_MISMATCH", str(ctx.exception.detail))

    def test_upi_does_not_require_counter_session(self):
        """Non-cash payment works without a counter session."""
        bill = self._make_finalized_bill()
        payment = services.create_payment(
            bill, self.cashier,
            amount=bill.grand_total,
            payment_method=PaymentMethod.UPI,
            transaction_reference="UPI-CS-001",
            counter_session=None,
        )
        self.assertIsNone(payment.counter_session)
        self.assertIsNone(payment.counter)

    def test_cash_payment_no_session_rejected(self):
        """CASH payment with counter_session=None is rejected."""
        bill = self._make_finalized_bill()
        with self.assertRaises(ValidationError) as ctx:
            services.create_payment(
                bill, self.cashier,
                amount=bill.grand_total,
                payment_method=PaymentMethod.CASH,
                cash_received=bill.grand_total,
                counter_session=None,
            )
        self.assertIn("SESSION", str(ctx.exception.detail).upper())
