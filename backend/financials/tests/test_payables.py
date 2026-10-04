# =============================================================================
# RestaurantFlow — Payable Tests
# Phase 12
# =============================================================================

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from financials.models import Payable
from financials.services import PayableService, ExpenseService, SupplierInvoiceService
from financials.exceptions import DuplicatePayable
from financials.tests.base import FinancialTestBase


class PayableCreationTests(FinancialTestBase):
    """Payable creation from expenses and supplier invoices."""

    def test_payable_created_from_approved_expense(self):
        expense = self._create_expense(
            amount=Decimal("5000.00"), tax_amount=Decimal("900.00"), status="APPROVED"
        )
        payable = Payable.objects.get(expense=expense)
        self.assertEqual(payable.amount, Decimal("5900.00"))
        self.assertEqual(payable.paid_amount, Decimal("0.00"))
        self.assertEqual(payable.remaining_amount, Decimal("5900.00"))
        self.assertEqual(payable.status, "OPEN")
        self.assertEqual(payable.payable_type, "EXPENSE")

    def test_payable_created_from_approved_invoice(self):
        invoice = self._create_supplier_invoice(subtotal=Decimal("20000.00"))
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        SupplierInvoiceService.approve_invoice(invoice, self.accountant)
        payable = Payable.objects.get(supplier_invoice=invoice)
        self.assertEqual(payable.amount, Decimal("20000.00"))
        self.assertEqual(payable.payable_type, "SUPPLIER_INVOICE")

    def test_payable_reference_number_matches_expense_number(self):
        expense = self._create_expense(status="APPROVED")
        payable = Payable.objects.get(expense=expense)
        self.assertEqual(payable.reference_number, expense.expense_number)

    def test_duplicate_payable_from_same_expense_raises(self):
        expense = self._create_expense(status="APPROVED")
        # The approval workflow already created one payable — try to create another
        with self.assertRaises(DuplicatePayable):
            PayableService.create_payable_from_expense(expense, self.accountant)

    def test_duplicate_payable_from_same_invoice_raises(self):
        invoice = self._create_supplier_invoice()
        SupplierInvoiceService.submit_invoice(invoice, self.owner)
        invoice.refresh_from_db()
        SupplierInvoiceService.approve_invoice(invoice, self.accountant)
        with self.assertRaises(DuplicatePayable):
            PayableService.create_payable_from_invoice(invoice, self.accountant)


class PayablePaymentTests(FinancialTestBase):
    """Recording payments and status transitions."""

    def _get_expense_payable(self, amount=Decimal("5000.00")):
        expense = self._create_expense(amount=amount, status="APPROVED")
        return Payable.objects.get(expense=expense)

    def test_partial_payment_sets_partially_paid(self):
        payable = self._get_expense_payable()
        updated = PayableService.record_payment(payable, Decimal("2000.00"), self.accountant)
        self.assertEqual(updated.status, "PARTIALLY_PAID")
        self.assertEqual(updated.paid_amount, Decimal("2000.00"))
        self.assertEqual(updated.remaining_amount, Decimal("3000.00"))

    def test_full_payment_sets_paid(self):
        payable = self._get_expense_payable()
        updated = PayableService.record_payment(payable, Decimal("5000.00"), self.accountant)
        self.assertEqual(updated.status, "PAID")
        self.assertEqual(updated.remaining_amount, Decimal("0.00"))

    def test_overpayment_raises_validation_error(self):
        from rest_framework.exceptions import ValidationError
        payable = self._get_expense_payable()
        with self.assertRaises(ValidationError) as ctx:
            PayableService.record_payment(payable, Decimal("6000.00"), self.accountant)
        self.assertIn("OVERPAYMENT", str(ctx.exception.detail))

    def test_payment_on_cancelled_payable_raises(self):
        from rest_framework.exceptions import ValidationError
        expense = self._create_expense(status="APPROVED")
        payable = Payable.objects.get(expense=expense)
        payable.status = "CANCELLED"
        payable.save()
        with self.assertRaises(ValidationError):
            PayableService.record_payment(payable, Decimal("100.00"), self.accountant)

    def test_payment_on_paid_payable_raises(self):
        from rest_framework.exceptions import ValidationError
        payable = self._get_expense_payable()
        PayableService.record_payment(payable, Decimal("5000.00"), self.accountant)
        payable.refresh_from_db()
        with self.assertRaises(ValidationError):
            PayableService.record_payment(payable, Decimal("1.00"), self.accountant)

    def test_remaining_amount_is_correctly_updated(self):
        payable = self._get_expense_payable(amount=Decimal("10000.00"))
        PayableService.record_payment(payable, Decimal("3000.00"), self.accountant)
        payable.refresh_from_db()
        self.assertEqual(payable.remaining_amount, Decimal("7000.00"))

    def test_payment_audit_log_recorded(self):
        from financials.models import FinancialAuditLog
        payable = self._get_expense_payable()
        PayableService.record_payment(payable, Decimal("1000.00"), self.accountant)
        self.assertTrue(
            FinancialAuditLog.objects.filter(
                action="PAYABLE_STATUS_CHANGED",
                entity_id=payable.pk,
            ).exists()
        )


class OverdueStatusTests(FinancialTestBase):
    """Overdue status detection and bulk refresh."""

    def test_payable_becomes_overdue_after_due_date(self):
        expense = self._create_expense(status="SUBMITTED")
        # Manually set due_date in the past
        expense.due_date = timezone.now().date() - timedelta(days=5)
        expense.save()
        ExpenseService.approve_expense(expense, self.accountant)
        payable = Payable.objects.get(expense=expense)
        # Initially OPEN (just created)
        PayableService.refresh_overdue_statuses()
        payable.refresh_from_db()
        self.assertEqual(payable.status, "OVERDUE")

    def test_paid_payable_not_marked_overdue(self):
        expense = self._create_expense(
            amount=Decimal("1000.00"), status="SUBMITTED"
        )
        expense.due_date = timezone.now().date() - timedelta(days=5)
        expense.save()
        ExpenseService.approve_expense(expense, self.accountant)
        payable = Payable.objects.get(expense=expense)
        PayableService.record_payment(payable, Decimal("1000.00"), self.accountant)
        payable.refresh_from_db()
        PayableService.refresh_overdue_statuses()
        payable.refresh_from_db()
        self.assertEqual(payable.status, "PAID")

    def test_get_overdue_payables_returns_correct_records(self):
        expense = self._create_expense(status="SUBMITTED")
        expense.due_date = timezone.now().date() - timedelta(days=3)
        expense.save()
        ExpenseService.approve_expense(expense, self.accountant)
        PayableService.refresh_overdue_statuses()
        overdue = PayableService.get_overdue_payables(self.restaurant)
        self.assertTrue(overdue.filter(expense=expense).exists())

    def test_refresh_returns_count(self):
        expense = self._create_expense(status="SUBMITTED")
        expense.due_date = timezone.now().date() - timedelta(days=1)
        expense.save()
        ExpenseService.approve_expense(expense, self.accountant)
        count = PayableService.refresh_overdue_statuses()
        self.assertGreaterEqual(count, 1)


class PayableAPITests(FinancialTestBase):
    """Payable API isolation and permission tests."""

    def test_unauthenticated_cannot_list_payables(self):
        response = self.anon_client.get("/api/financials/payables/")
        self.assertEqual(response.status_code, 401)

    def test_cashier_cannot_view_payables(self):
        response = self.cashier_client.get("/api/financials/payables/")
        self.assertEqual(response.status_code, 403)

    def test_accountant_can_view_payables(self):
        self._create_expense(status="APPROVED")
        response = self.accountant_client.get("/api/financials/payables/")
        self.assertEqual(response.status_code, 200)

    def test_other_user_cannot_see_foreign_payable(self):
        expense = self._create_expense(status="APPROVED")
        payable = Payable.objects.get(expense=expense)
        response = self.other_client.get(f"/api/financials/payables/{payable.pk}/")
        self.assertEqual(response.status_code, 404)

    def test_owner_can_record_payment_via_api(self):
        expense = self._create_expense(amount=Decimal("5000.00"), status="APPROVED")
        payable = Payable.objects.get(expense=expense)
        response = self.owner_client.post(
            f"/api/financials/payables/{payable.pk}/record-payment/",
            data={"payment_amount": "2500.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["paid_amount"], "2500.00")

    def test_payable_dashboard_returns_summary(self):
        self._create_expense(status="APPROVED")
        response = self.owner_client.get("/api/financials/payables/dashboard/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("total_payables", data)
        self.assertIn("open_payables", data)
        self.assertIn("remaining_amount", data)
