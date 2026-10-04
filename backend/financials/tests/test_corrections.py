# =============================================================================
# RestaurantFlow — Expense Correction Tests
# Phase 12
# =============================================================================

from decimal import Decimal

from financials.services import ExpenseCorrectionService
from financials.tests.base import FinancialTestBase


class CorrectionRequestTests(FinancialTestBase):
    """Correction requests can only be raised against APPROVED expenses."""

    def test_correction_requires_approved_expense(self):
        from rest_framework.exceptions import ValidationError
        expense = self._create_expense(status="DRAFT")
        with self.assertRaises(ValidationError) as ctx:
            ExpenseCorrectionService.request_correction(
                expense=expense,
                user=self.manager,
                correction_type="AMOUNT_CORRECTION",
                requested_data={"amount": "4000.00"},
                reason="The original amount was incorrect due to a typo.",
            )
        self.assertIn("CORRECTION_REQUIRES_APPROVED", str(ctx.exception.detail))

    def test_correction_on_approved_expense_creates_pending_request(self):
        expense = self._create_expense(status="APPROVED")
        correction = ExpenseCorrectionService.request_correction(
            expense=expense,
            user=self.manager,
            correction_type="AMOUNT_CORRECTION",
            requested_data={"amount": "4500.00"},
            reason="The original amount was entered incorrectly in the system.",
        )
        self.assertEqual(correction.status, "PENDING")
        self.assertEqual(correction.expense, expense)

    def test_correction_reason_minimum_length(self):
        from rest_framework.exceptions import ValidationError
        expense = self._create_expense(status="APPROVED")
        with self.assertRaises(ValidationError):
            ExpenseCorrectionService.request_correction(
                expense=expense,
                user=self.manager,
                correction_type="OTHER",
                requested_data={},
                reason="Too short",  # < 10 chars
            )


class CorrectionApprovalTests(FinancialTestBase):
    """Approve and reject correction requests."""

    def _make_correction(self):
        expense = self._create_expense(status="APPROVED")
        return ExpenseCorrectionService.request_correction(
            expense=expense,
            user=self.manager,
            correction_type="AMOUNT_CORRECTION",
            requested_data={"amount": "6000.00"},
            reason="Invoice amount was revised by the vendor, please update.",
        )

    def test_approve_correction_applies_changes(self):
        correction = self._make_correction()
        ExpenseCorrectionService.approve_correction(
            correction, self.accountant, note="Verified against revised invoice."
        )
        correction.expense.refresh_from_db()
        self.assertEqual(correction.expense.amount, Decimal("6000.00"))

    def test_approve_correction_marks_it_approved(self):
        correction = self._make_correction()
        approved = ExpenseCorrectionService.approve_correction(
            correction, self.accountant, note="OK"
        )
        self.assertEqual(approved.status, "APPROVED")
        self.assertEqual(approved.reviewed_by, self.accountant)

    def test_self_approval_of_correction_blocked(self):
        from rest_framework.exceptions import ValidationError
        correction = self._make_correction()
        with self.assertRaises(ValidationError) as ctx:
            # manager requested → manager tries to approve
            ExpenseCorrectionService.approve_correction(
                correction, self.manager, note="Self approve"
            )
        self.assertIn("SELF_APPROVAL_NOT_ALLOWED", str(ctx.exception.detail))

    def test_reject_correction_requires_note(self):
        from rest_framework.exceptions import ValidationError
        correction = self._make_correction()
        with self.assertRaises(ValidationError):
            ExpenseCorrectionService.reject_correction(correction, self.accountant, note="")

    def test_reject_correction_marks_rejected(self):
        correction = self._make_correction()
        rejected = ExpenseCorrectionService.reject_correction(
            correction, self.accountant, note="No supporting evidence provided."
        )
        self.assertEqual(rejected.status, "REJECTED")

    def test_cannot_approve_already_approved_correction(self):
        from rest_framework.exceptions import ValidationError
        correction = self._make_correction()
        ExpenseCorrectionService.approve_correction(correction, self.accountant, note="OK")
        correction.refresh_from_db()
        with self.assertRaises(ValidationError):
            ExpenseCorrectionService.approve_correction(correction, self.accountant, note="Again")

    def test_cancel_pending_correction(self):
        correction = self._make_correction()
        cancelled = ExpenseCorrectionService.cancel_correction(correction, self.manager)
        self.assertEqual(cancelled.status, "CANCELLED")

    def test_cannot_cancel_approved_correction(self):
        from rest_framework.exceptions import ValidationError
        correction = self._make_correction()
        ExpenseCorrectionService.approve_correction(correction, self.accountant, note="OK")
        correction.refresh_from_db()
        with self.assertRaises(ValidationError):
            ExpenseCorrectionService.cancel_correction(correction, self.manager)

    def test_correction_audit_log_recorded(self):
        from financials.models import FinancialAuditLog
        correction = self._make_correction()
        ExpenseCorrectionService.approve_correction(correction, self.accountant, note="All good")
        self.assertTrue(
            FinancialAuditLog.objects.filter(
                action="EXPENSE_CORRECTION_APPROVED",
                entity_id=correction.expense.pk,
            ).exists()
        )


class CorrectionAPITests(FinancialTestBase):
    """Correction request API endpoints."""

    def test_request_correction_via_api(self):
        expense = self._create_expense(status="APPROVED")
        response = self.manager_client.post(
            f"/api/financials/expenses/{expense.pk}/corrections/",
            data={
                "correction_type": "AMOUNT_CORRECTION",
                "requested_data": {"amount": "4500"},
                "reason": "The original invoice amount was mis-entered into the system.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "PENDING")

    def test_other_user_cannot_request_correction_on_foreign_expense(self):
        expense = self._create_expense(status="APPROVED")
        response = self.other_client.post(
            f"/api/financials/expenses/{expense.pk}/corrections/",
            data={
                "correction_type": "OTHER",
                "requested_data": {},
                "reason": "Cross-restaurant injection attempt.",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 404)
