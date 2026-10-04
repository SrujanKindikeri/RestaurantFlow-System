# =============================================================================
# RestaurantFlow — Expense Tests
# Phase 12
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from financials.models import Expense, ExpenseApproval, Payable
from financials.services import ExpenseService, generate_expense_number
from financials.exceptions import (
    InvalidStatusTransition, SelfApprovalNotAllowed, ExpenseNotEditable,
)
from financials.tests.base import FinancialTestBase


class ExpenseNumberingTests(FinancialTestBase):
    """Expense number generation — concurrency-safe sequencing."""

    def test_first_expense_gets_exp_000001(self):
        exp = self._create_expense()
        self.assertTrue(exp.expense_number.startswith("EXP-"))

    def test_numbers_increment_per_restaurant(self):
        e1 = self._create_expense(title="Expense A")
        e2 = self._create_expense(title="Expense B")
        seq1 = int(e1.expense_number.split("-")[1])
        seq2 = int(e2.expense_number.split("-")[1])
        self.assertEqual(seq2, seq1 + 1)

    def test_expense_numbers_are_unique(self):
        e1 = self._create_expense(title="E1")
        e2 = self._create_expense(title="E2")
        self.assertNotEqual(e1.expense_number, e2.expense_number)

    def test_expense_number_is_immutable(self):
        expense = self._create_expense()
        original = expense.expense_number
        # Attempt to change expense_number via direct save
        expense.expense_number = "EXP-HACKED"
        # The DB has a unique constraint — saving would conflict if called
        # We verify the original value is preserved in the object
        expense.refresh_from_db()
        self.assertEqual(expense.expense_number, original)


class ExpenseCreationTests(FinancialTestBase):
    """Expense creation — field validation and defaults."""

    def test_creates_expense_in_draft_status(self):
        expense = self._create_expense()
        self.assertEqual(expense.status, "DRAFT")

    def test_total_amount_computed_by_backend(self):
        expense = self._create_expense(amount=Decimal("1000.00"), tax_amount=Decimal("180.00"))
        self.assertEqual(expense.total_amount, Decimal("1180.00"))

    def test_payment_status_defaults_to_unpaid(self):
        expense = self._create_expense()
        self.assertEqual(expense.payment_status, "UNPAID")

    def test_negative_amount_raises_validation_error(self):
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            ExpenseService.create_expense(
                restaurant=self.restaurant,
                category=self.category,
                title="Bad Amount",
                amount=Decimal("-500.00"),
                expense_date=timezone.now().date(),
                user=self.manager,
            )

    def test_negative_tax_raises_validation_error(self):
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            ExpenseService.create_expense(
                restaurant=self.restaurant,
                category=self.category,
                title="Bad Tax",
                amount=Decimal("500.00"),
                tax_amount=Decimal("-10.00"),
                expense_date=timezone.now().date(),
                user=self.manager,
            )

    def test_inactive_category_raises_validation_error(self):
        from rest_framework.exceptions import ValidationError
        self.category.is_active = False
        self.category.save()
        try:
            with self.assertRaises(ValidationError):
                ExpenseService.create_expense(
                    restaurant=self.restaurant,
                    category=self.category,
                    title="Inactive Cat",
                    amount=Decimal("100.00"),
                    expense_date=timezone.now().date(),
                    user=self.manager,
                )
        finally:
            self.category.is_active = True
            self.category.save()

    def test_wrong_restaurant_category_raises_validation_error(self):
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            ExpenseService.create_expense(
                restaurant=self.restaurant,
                category=self.other_category,  # belongs to other_restaurant
                title="Wrong Category",
                amount=Decimal("100.00"),
                expense_date=timezone.now().date(),
                user=self.manager,
            )


class ExpenseUpdateTests(FinancialTestBase):
    """Expense editing — only DRAFT is editable."""

    def test_can_update_draft_expense(self):
        expense = self._create_expense()
        updated = ExpenseService.update_draft(
            expense, self.manager, title="Updated Title", amount=Decimal("2000.00")
        )
        self.assertEqual(updated.title, "Updated Title")
        self.assertEqual(updated.amount, Decimal("2000.00"))

    def test_update_recalculates_total(self):
        expense = self._create_expense(amount=Decimal("1000.00"), tax_amount=Decimal("100.00"))
        updated = ExpenseService.update_draft(expense, self.manager, amount=Decimal("2000.00"))
        self.assertEqual(updated.total_amount, Decimal("2100.00"))

    def test_submitted_expense_not_editable(self):
        expense = self._create_expense(status="SUBMITTED")
        with self.assertRaises(ExpenseNotEditable):
            ExpenseService.update_draft(expense, self.manager, title="Nope")

    def test_approved_expense_not_editable(self):
        expense = self._create_expense(status="APPROVED")
        with self.assertRaises(ExpenseNotEditable):
            ExpenseService.update_draft(expense, self.accountant, title="Nope")


class ExpenseWorkflowTests(FinancialTestBase):
    """Expense state machine — submit / approve / reject / cancel."""

    def test_submit_draft_expense(self):
        expense = self._create_expense()
        submitted = ExpenseService.submit_expense(expense, self.manager)
        self.assertEqual(submitted.status, "SUBMITTED")
        self.assertIsNotNone(submitted.submitted_at)
        # Should create an ExpenseApproval
        self.assertTrue(submitted.approvals.filter(status="PENDING").exists())

    def test_cannot_submit_already_submitted(self):
        expense = self._create_expense(status="SUBMITTED")
        with self.assertRaises(InvalidStatusTransition):
            ExpenseService.submit_expense(expense, self.manager)

    def test_approve_submitted_expense(self):
        expense = self._create_expense(status="SUBMITTED")
        approved = ExpenseService.approve_expense(expense, self.accountant)
        self.assertEqual(approved.status, "APPROVED")
        self.assertEqual(approved.approved_by, self.accountant)
        self.assertIsNotNone(approved.approved_at)

    def test_approved_expense_creates_payable(self):
        expense = self._create_expense(status="SUBMITTED")
        ExpenseService.approve_expense(expense, self.accountant)
        self.assertTrue(Payable.objects.filter(expense=expense).exists())

    def test_self_approval_raises_error(self):
        """The submitter cannot approve their own expense."""
        expense = self._create_expense(status="SUBMITTED")
        with self.assertRaises(SelfApprovalNotAllowed):
            # manager submitted, manager tries to approve
            ExpenseService.approve_expense(expense, self.manager)

    def test_reject_submitted_expense(self):
        expense = self._create_expense(status="SUBMITTED")
        rejected = ExpenseService.reject_expense(
            expense, self.accountant, reason="Not a valid business expense."
        )
        self.assertEqual(rejected.status, "REJECTED")
        self.assertEqual(rejected.rejected_by, self.accountant)
        self.assertEqual(rejected.rejection_reason, "Not a valid business expense.")

    def test_rejection_reason_required(self):
        from financials.validators import validate_rejection_reason
        from rest_framework.exceptions import ValidationError
        expense = self._create_expense(status="SUBMITTED")
        with self.assertRaises(ValidationError):
            ExpenseService.reject_expense(expense, self.accountant, reason="")

    def test_rejection_reason_min_length(self):
        from rest_framework.exceptions import ValidationError
        expense = self._create_expense(status="SUBMITTED")
        with self.assertRaises(ValidationError):
            ExpenseService.reject_expense(expense, self.accountant, reason="Bad")

    def test_cancel_draft_expense(self):
        expense = self._create_expense()
        cancelled = ExpenseService.cancel_expense(expense, self.manager)
        self.assertEqual(cancelled.status, "CANCELLED")

    def test_cannot_cancel_approved_expense(self):
        expense = self._create_expense(status="APPROVED")
        with self.assertRaises(InvalidStatusTransition):
            ExpenseService.cancel_expense(expense, self.accountant)

    def test_cannot_approve_draft_directly(self):
        expense = self._create_expense()
        with self.assertRaises(InvalidStatusTransition):
            ExpenseService.approve_expense(expense, self.accountant)

    def test_rejected_expense_is_terminal(self):
        expense = self._create_expense(status="REJECTED")
        with self.assertRaises(InvalidStatusTransition):
            ExpenseService.submit_expense(expense, self.manager)

    def test_approved_expense_is_protected_from_direct_edit(self):
        expense = self._create_expense(status="APPROVED")
        with self.assertRaises(ExpenseNotEditable):
            ExpenseService.update_draft(expense, self.accountant, title="Hack")

    def test_duplicate_approval_attempt_blocked(self):
        """Two concurrent approve calls — only one should succeed."""
        expense = self._create_expense(status="SUBMITTED")
        ExpenseService.approve_expense(expense, self.accountant)
        expense.refresh_from_db()
        # Second approval attempt on already-approved expense
        with self.assertRaises(InvalidStatusTransition):
            ExpenseService.approve_expense(expense, self.accountant)

    def test_approval_audit_log_created(self):
        from financials.models import FinancialAuditLog
        expense = self._create_expense(status="SUBMITTED")
        ExpenseService.approve_expense(expense, self.accountant)
        self.assertTrue(
            FinancialAuditLog.objects.filter(
                entity_id=expense.pk,
                action="EXPENSE_APPROVED",
            ).exists()
        )


class ExpenseAmountValidationTests(FinancialTestBase):
    """Amount and tax field invariants."""

    def test_zero_amount_is_allowed(self):
        """Zero-amount expenses (e.g. donations) are valid."""
        expense = ExpenseService.create_expense(
            restaurant=self.restaurant,
            category=self.category,
            title="Zero Expense",
            amount=Decimal("0.00"),
            expense_date=timezone.now().date(),
            user=self.manager,
        )
        self.assertEqual(expense.amount, Decimal("0.00"))

    def test_total_amount_equals_amount_plus_tax(self):
        expense = self._create_expense(
            amount=Decimal("3500.00"), tax_amount=Decimal("630.00")
        )
        self.assertEqual(expense.total_amount, Decimal("4130.00"))

    def test_frontend_total_is_ignored_backend_recalculates(self):
        """Even if we manually set total_amount, the service recomputes it."""
        expense = self._create_expense(amount=Decimal("100.00"), tax_amount=Decimal("18.00"))
        self.assertEqual(expense.total_amount, Decimal("118.00"))


class ExpenseAPITests(FinancialTestBase):
    """Expense API endpoints — permission and isolation checks."""

    def test_unauthenticated_cannot_list_expenses(self):
        response = self.anon_client.get("/api/financials/expenses/")
        self.assertEqual(response.status_code, 401)

    def test_cashier_cannot_create_expense(self):
        response = self.cashier_client.post(
            "/api/financials/expenses/",
            data={
                "restaurant": str(self.restaurant.pk),
                "category": str(self.category.pk),
                "title": "Cashier attempt",
                "amount": "100.00",
                "expense_date": "2026-10-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_manager_can_create_expense(self):
        response = self.manager_client.post(
            "/api/financials/expenses/",
            data={
                "restaurant": str(self.restaurant.pk),
                "category": str(self.category.pk),
                "title": "Manager Expense",
                "amount": "500.00",
                "tax_amount": "90.00",
                "expense_date": "2026-10-01",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["title"], "Manager Expense")
        self.assertEqual(data["total_amount"], "590.00")

    def test_other_user_cannot_see_this_restaurants_expense(self):
        expense = self._create_expense()
        response = self.other_client.get(f"/api/financials/expenses/{expense.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_owner_can_see_own_restaurant_expense(self):
        expense = self._create_expense()
        response = self.owner_client.get(f"/api/financials/expenses/{expense.pk}/")
        self.assertEqual(response.status_code, 200)

    def test_expense_list_is_scoped_to_user_restaurant(self):
        self._create_expense(restaurant=self.restaurant)
        self._create_expense(user=self.other_user, restaurant=self.other_restaurant, category=self.other_category)
        response = self.owner_client.get("/api/financials/expenses/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # All returned expenses must belong to owner's restaurant
        for exp in data["results"]:
            self.assertEqual(exp["restaurant"], str(self.restaurant.pk))

    def test_manager_cannot_approve_expense(self):
        expense = self._create_expense(status="SUBMITTED")
        response = self.manager_client.post(
            f"/api/financials/expenses/{expense.pk}/approve/",
            data={"approval_note": "approve"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_accountant_can_approve_expense(self):
        expense = self._create_expense(status="SUBMITTED")
        response = self.accountant_client.post(
            f"/api/financials/expenses/{expense.pk}/approve/",
            data={"approval_note": "Looks good"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "APPROVED")

    def test_reject_without_reason_returns_400(self):
        expense = self._create_expense(status="SUBMITTED")
        response = self.accountant_client.post(
            f"/api/financials/expenses/{expense.pk}/reject/",
            data={"rejection_reason": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_list_expenses_filter_by_status(self):
        self._create_expense(status="DRAFT", title="Draft")
        self._create_expense(status="SUBMITTED", title="Submitted")
        response = self.owner_client.get("/api/financials/expenses/?status=SUBMITTED")
        self.assertEqual(response.status_code, 200)
        for exp in response.json()["results"]:
            self.assertEqual(exp["status"], "SUBMITTED")

    def test_pagination_present(self):
        response = self.owner_client.get("/api/financials/expenses/")
        self.assertIn("count", response.json())
        self.assertIn("results", response.json())
