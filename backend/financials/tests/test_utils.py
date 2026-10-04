# =============================================================================
# RestaurantFlow — Financials Utility / Validator Tests
# Phase 12
# =============================================================================

from decimal import Decimal
from datetime import date

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from financials.validators import (
    validate_non_negative_amount,
    validate_positive_amount,
    validate_rejection_reason,
    validate_correction_reason,
    validate_payable_payment,
)
from financials.exceptions import (
    InvalidStatusTransition,
    DuplicatePayable,
    SelfApprovalNotAllowed,
    AttachmentTooLarge,
    AttachmentTypeNotAllowed,
)
from financials.validators import validate_expense_transition, validate_sinv_transition
from financials.tests.base import FinancialTestBase


class AmountValidatorTests(TestCase):

    def test_non_negative_allows_zero(self):
        result = validate_non_negative_amount(Decimal("0.00"))
        self.assertEqual(result, Decimal("0.00"))

    def test_non_negative_allows_positive(self):
        result = validate_non_negative_amount(Decimal("100.00"))
        self.assertEqual(result, Decimal("100.00"))

    def test_non_negative_rejects_negative(self):
        with self.assertRaises(ValidationError):
            validate_non_negative_amount(Decimal("-1.00"))

    def test_positive_rejects_zero(self):
        with self.assertRaises(ValidationError):
            validate_positive_amount(Decimal("0.00"))

    def test_positive_allows_positive(self):
        result = validate_positive_amount(Decimal("0.01"))
        self.assertEqual(result, Decimal("0.01"))

    def test_invalid_string_raises(self):
        with self.assertRaises(ValidationError):
            validate_non_negative_amount("not_a_number")


class RejectionReasonTests(TestCase):

    def test_empty_reason_raises(self):
        with self.assertRaises(ValidationError):
            validate_rejection_reason("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValidationError):
            validate_rejection_reason("   ")

    def test_too_short_raises(self):
        with self.assertRaises(ValidationError):
            validate_rejection_reason("Bad")  # < 5 chars

    def test_valid_reason(self):
        result = validate_rejection_reason("This is a valid reason.")
        self.assertEqual(result, "This is a valid reason.")

    def test_reason_is_stripped(self):
        result = validate_rejection_reason("  Valid reason  ")
        self.assertEqual(result, "Valid reason")


class CorrectionReasonTests(TestCase):

    def test_too_short_raises(self):
        with self.assertRaises(ValidationError):
            validate_correction_reason("Short")  # < 10 chars

    def test_valid_reason(self):
        result = validate_correction_reason("This correction is needed because the vendor changed the price.")
        self.assertIn("correction", result)


class StatusTransitionTests(TestCase):

    def test_valid_expense_draft_to_submitted(self):
        # Should not raise
        validate_expense_transition("DRAFT", "SUBMITTED")

    def test_invalid_expense_transition_raises(self):
        with self.assertRaises(Exception):
            validate_expense_transition("APPROVED", "DRAFT")

    def test_valid_sinv_draft_to_submitted(self):
        validate_sinv_transition("DRAFT", "SUBMITTED")

    def test_invalid_sinv_terminal_to_anything(self):
        with self.assertRaises(Exception):
            validate_sinv_transition("PAID", "DRAFT")


class PayablePaymentValidatorTests(TestCase):

    def test_valid_payment(self):
        # Should not raise
        validate_payable_payment(
            paid_amount=Decimal("1000.00"),
            new_payment=Decimal("2000.00"),
            total=Decimal("5000.00"),
        )

    def test_overpayment_raises(self):
        with self.assertRaises(ValidationError):
            validate_payable_payment(
                paid_amount=Decimal("4000.00"),
                new_payment=Decimal("2000.00"),
                total=Decimal("5000.00"),
            )

    def test_exact_payment_allowed(self):
        validate_payable_payment(
            paid_amount=Decimal("0.00"),
            new_payment=Decimal("5000.00"),
            total=Decimal("5000.00"),
        )


class CustomExceptionTests(TestCase):

    def test_invalid_status_transition_detail(self):
        exc = InvalidStatusTransition("DRAFT", "APPROVED", ["SUBMITTED"])
        self.assertEqual(exc.detail["code"], "INVALID_STATUS_TRANSITION")
        self.assertIn("DRAFT", exc.detail["message"])

    def test_duplicate_payable_detail(self):
        exc = DuplicatePayable("Expense")
        self.assertEqual(exc.detail["code"], "DUPLICATE_PAYABLE")

    def test_self_approval_detail(self):
        exc = SelfApprovalNotAllowed()
        self.assertEqual(exc.detail["code"], "SELF_APPROVAL_NOT_ALLOWED")

    def test_attachment_too_large_detail(self):
        exc = AttachmentTooLarge(15 * 1024 * 1024, 10 * 1024 * 1024)
        self.assertEqual(exc.detail["code"], "ATTACHMENT_TOO_LARGE")

    def test_attachment_type_not_allowed_detail(self):
        exc = AttachmentTypeNotAllowed(".exe")
        self.assertEqual(exc.detail["code"], "ATTACHMENT_TYPE_NOT_ALLOWED")


class ExpenseCategoryAPITests(FinancialTestBase):
    """Category API tests using the standard FinancialTestBase."""

    def test_category_list_returns_200(self):
        response = self.owner_client.get("/api/financials/expense-categories/")
        self.assertEqual(response.status_code, 200)

    def test_duplicate_category_code_rejected(self):
        # RENT already exists from fixture (same restaurant, same code)
        response = self.owner_client.post(
            "/api/financials/expense-categories/",
            data={
                "restaurant": str(self.restaurant.pk),
                "name": "Duplicate Rent",
                "code": "RENT",  # already exists
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
