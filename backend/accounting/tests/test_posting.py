# =============================================================================
# RestaurantFlow — Accounting Posting Tests
# Phase 13
#
# Tests for AccountingPostingService: bill, payment, refund, expense,
# supplier invoice, inventory consumption.
# =============================================================================

import uuid
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from accounting.tests.base import AccountingTestBase, ZERO
from accounting.services import AccountingPostingService
from accounting.exceptions import DuplicateAccountingPostError
from accounting.constants import JE_POSTED, SOURCE_BILL, SOURCE_PAYMENT


# =============================================================================
# Bill Posting
# =============================================================================

class BillPostingTests(AccountingTestBase):

    def _make_finalized_bill(self, grand_total=None, tax_amount=None,
                              taxable_amount=None, subtotal=None,
                              discount_amount=None, rounding_amount=None):
        """Create a minimal mock Bill object."""
        from billing.models import Bill, BillStatus
        from orders.models import Order, OrderItem
        from menu.models import MenuItem, Category, TaxRate

        # Tax rate
        tax_rate_obj, _ = TaxRate.objects.get_or_create(
            restaurant=self.restaurant,
            code="GST5",
            defaults={"name": "GST 5%", "rate": Decimal("5.000")},
        )
        # Category
        cat, _ = Category.objects.get_or_create(
            restaurant=self.restaurant,
            slug=f"cat-{uuid.uuid4().hex[:4]}",
            defaults={"name": "Main", "display_order": 1},
        )
        # Menu item
        item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=cat,
            name=f"Item {uuid.uuid4().hex[:4]}",
            slug=f"item-{uuid.uuid4().hex[:6]}",
            sku=f"SKU{uuid.uuid4().hex[:6]}",
            tax_rate=tax_rate_obj,
        )
        # Order
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ORD-{uuid.uuid4().hex[:8].upper()}",
            order_type="COUNTER",
            status="CONFIRMED",
            created_by=self.user,
        )
        # Bill (FINALIZED)
        subtotal = subtotal or Decimal("1000.00")
        tax_amount = tax_amount or Decimal("180.00")
        taxable_amount = taxable_amount or subtotal
        discount_amount = discount_amount or ZERO
        rounding_amount = rounding_amount or ZERO
        grand_total = grand_total or (taxable_amount + tax_amount + rounding_amount)

        bill = Bill.objects.create(
            order=order,
            branch=self.branch,
            bill_number=f"B-2026-{uuid.uuid4().hex[:6].upper()}",
            status=BillStatus.FINALIZED,
            subtotal=subtotal,
            discount_amount=discount_amount,
            taxable_amount=taxable_amount,
            tax_amount=tax_amount,
            rounding_amount=rounding_amount,
            grand_total=grand_total,
            created_by=self.user,
            finalized_by=self.user,
            finalized_at=timezone.now(),
        )
        return bill

    def test_post_bill_creates_journal_entry(self):
        bill = self._make_finalized_bill()
        entry = AccountingPostingService.post_bill(bill, self.user)

        self.assertEqual(entry.status, JE_POSTED)
        self.assertEqual(entry.source_type, SOURCE_BILL)
        self.assertEqual(entry.source_id, bill.pk)

    def test_post_bill_is_balanced(self):
        bill = self._make_finalized_bill()
        entry = AccountingPostingService.post_bill(bill, self.user)
        self.assertTrue(entry.is_balanced())

    def test_post_bill_debits_receivable(self):
        bill = self._make_finalized_bill(
            grand_total=Decimal("1180.00"),
            taxable_amount=Decimal("1000.00"),
            tax_amount=Decimal("180.00"),
        )
        entry = AccountingPostingService.post_bill(bill, self.user)
        debit_lines = [l for l in entry.lines.all() if l.debit_amount > ZERO]
        receivable_line = next(
            (l for l in debit_lines if l.account == self.acct_receivable), None
        )
        self.assertIsNotNone(receivable_line)
        self.assertEqual(receivable_line.debit_amount, Decimal("1180.00"))

    def test_post_bill_credits_sales_and_tax(self):
        bill = self._make_finalized_bill(
            grand_total=Decimal("1180.00"),
            taxable_amount=Decimal("1000.00"),
            tax_amount=Decimal("180.00"),
        )
        entry = AccountingPostingService.post_bill(bill, self.user)
        credit_lines = {l.account_id: l for l in entry.lines.all() if l.credit_amount > ZERO}

        sales_line = credit_lines.get(self.acct_sales.pk)
        tax_line = credit_lines.get(self.acct_tax_payable.pk)

        self.assertIsNotNone(sales_line)
        self.assertEqual(sales_line.credit_amount, Decimal("1000.00"))
        self.assertIsNotNone(tax_line)
        self.assertEqual(tax_line.credit_amount, Decimal("180.00"))

    def test_draft_bill_not_posted(self):
        from billing.models import Bill, BillStatus
        from orders.models import Order
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ORD-DRAFT-{uuid.uuid4().hex[:6]}",
            order_type="COUNTER",
            status="CONFIRMED",
            created_by=self.user,
        )
        bill = Bill.objects.create(
            order=order,
            branch=self.branch,
            bill_number=f"B-DRAFT-{uuid.uuid4().hex[:6]}",
            status=BillStatus.DRAFT,
            subtotal=Decimal("100.00"),
            taxable_amount=Decimal("100.00"),
            grand_total=Decimal("100.00"),
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            AccountingPostingService.post_bill(bill, self.user)

    def test_duplicate_bill_posting_prevented(self):
        bill = self._make_finalized_bill()
        entry1 = AccountingPostingService.post_bill(bill, self.user)
        entry2 = AccountingPostingService.post_bill(bill, self.user)  # idempotent
        self.assertEqual(entry1.pk, entry2.pk)  # same entry returned

    def test_cancelled_bill_not_posted(self):
        from billing.models import Bill, BillStatus
        from orders.models import Order
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ORD-CANC-{uuid.uuid4().hex[:6]}",
            order_type="COUNTER",
            status="CONFIRMED",
            created_by=self.user,
        )
        bill = Bill.objects.create(
            order=order,
            branch=self.branch,
            bill_number=f"B-CANC-{uuid.uuid4().hex[:6]}",
            status=BillStatus.CANCELLED,
            subtotal=Decimal("100.00"),
            taxable_amount=Decimal("100.00"),
            grand_total=Decimal("100.00"),
            created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            AccountingPostingService.post_bill(bill, self.user)


# =============================================================================
# Payment Posting
# =============================================================================

class PaymentPostingTests(AccountingTestBase):

    def _make_completed_payment(self, method="CASH", amount=Decimal("1180.00")):
        from payments.models import Payment, PaymentStatus, PaymentMethod

        payment_method = getattr(PaymentMethod, method, PaymentMethod.CASH)
        from billing.models import Bill, BillStatus
        from orders.models import Order
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ORD-PAY-{uuid.uuid4().hex[:6]}",
            order_type="COUNTER",
            status="CONFIRMED",
            created_by=self.user,
        )
        bill = Bill.objects.create(
            order=order, branch=self.branch,
            bill_number=f"B-PAY-{uuid.uuid4().hex[:6]}",
            status=BillStatus.FINALIZED,
            subtotal=amount, taxable_amount=amount, grand_total=amount,
            created_by=self.user, finalized_by=self.user,
            finalized_at=timezone.now(),
        )
        payment = Payment.objects.create(
            bill=bill, branch=self.branch,
            payment_number=f"PAY-{uuid.uuid4().hex[:6].upper()}",
            amount=amount,
            payment_method=method,
            status=PaymentStatus.COMPLETED,
            initiated_by=self.user,
            completed_by=self.user,
            completed_at=timezone.now(),
        )
        return payment

    def test_post_cash_payment(self):
        payment = self._make_completed_payment("CASH")
        entry = AccountingPostingService.post_payment(payment, self.user)
        self.assertEqual(entry.status, JE_POSTED)
        self.assertTrue(entry.is_balanced())

        dr_lines = [l for l in entry.lines.all() if l.debit_amount > ZERO]
        cash_debit = next((l for l in dr_lines if l.account == self.acct_cash), None)
        self.assertIsNotNone(cash_debit)

    def test_post_upi_payment(self):
        payment = self._make_completed_payment("UPI")
        entry = AccountingPostingService.post_payment(payment, self.user)
        self.assertTrue(entry.is_balanced())
        dr_lines = [l for l in entry.lines.all() if l.debit_amount > ZERO]
        upi_debit = next((l for l in dr_lines if l.account == self.acct_upi), None)
        self.assertIsNotNone(upi_debit)

    def test_post_card_payment(self):
        payment = self._make_completed_payment("CARD")
        entry = AccountingPostingService.post_payment(payment, self.user)
        self.assertTrue(entry.is_balanced())
        dr_lines = [l for l in entry.lines.all() if l.debit_amount > ZERO]
        card_debit = next((l for l in dr_lines if l.account == self.acct_card), None)
        self.assertIsNotNone(card_debit)

    def test_pending_payment_not_posted(self):
        from payments.models import Payment, PaymentStatus, PaymentMethod
        from billing.models import Bill, BillStatus
        from orders.models import Order
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ORD-PEND-{uuid.uuid4().hex[:6]}",
            order_type="COUNTER", status="CONFIRMED", created_by=self.user,
        )
        bill = Bill.objects.create(
            order=order, branch=self.branch,
            bill_number=f"B-PEND-{uuid.uuid4().hex[:6]}",
            status=BillStatus.FINALIZED,
            subtotal=Decimal("100"), taxable_amount=Decimal("100"),
            grand_total=Decimal("100"), created_by=self.user,
            finalized_by=self.user, finalized_at=timezone.now(),
        )
        payment = Payment.objects.create(
            bill=bill, branch=self.branch,
            payment_number=f"PAY-PEND-{uuid.uuid4().hex[:6]}",
            amount=Decimal("100"), payment_method=PaymentMethod.CASH,
            status=PaymentStatus.PENDING, initiated_by=self.user,
        )
        with self.assertRaises(ValidationError):
            AccountingPostingService.post_payment(payment, self.user)

    def test_duplicate_payment_posting_idempotent(self):
        payment = self._make_completed_payment("CASH")
        e1 = AccountingPostingService.post_payment(payment, self.user)
        e2 = AccountingPostingService.post_payment(payment, self.user)
        self.assertEqual(e1.pk, e2.pk)


# =============================================================================
# Expense Posting
# =============================================================================

class ExpensePostingTests(AccountingTestBase):

    def _make_approved_expense(self, amount=Decimal("5000.00")):
        from financials.models import ExpenseCategory, Expense
        from financials.constants import EXPENSE_APPROVED

        cat, _ = ExpenseCategory.objects.get_or_create(
            restaurant=self.restaurant,
            code="RENT_TEST",
            defaults={"name": "Rent", "expense_account": self.acct_rent},
        )
        # Ensure expense_account is set
        if not cat.expense_account:
            cat.expense_account = self.acct_rent
            cat.save()

        expense = Expense.objects.create(
            restaurant=self.restaurant,
            expense_number=f"EXP-{uuid.uuid4().hex[:6].upper()}",
            category=cat,
            title="Monthly Rent",
            amount=amount,
            tax_amount=ZERO,
            total_amount=amount,
            expense_date=date.today(),
            status=EXPENSE_APPROVED,
            created_by=self.user,
            approved_by=self.user,
            approved_at=timezone.now(),
        )
        return expense

    def test_post_approved_expense(self):
        expense = self._make_approved_expense()
        entry = AccountingPostingService.post_expense(expense, self.user)
        self.assertEqual(entry.status, JE_POSTED)
        self.assertTrue(entry.is_balanced())

    def test_expense_debits_expense_account(self):
        expense = self._make_approved_expense(Decimal("20000.00"))
        entry = AccountingPostingService.post_expense(expense, self.user)
        dr_lines = [l for l in entry.lines.all() if l.debit_amount > ZERO]
        rent_debit = next((l for l in dr_lines if l.account == self.acct_rent), None)
        self.assertIsNotNone(rent_debit)
        self.assertEqual(rent_debit.debit_amount, Decimal("20000.00"))

    def test_expense_credits_accounts_payable(self):
        expense = self._make_approved_expense(Decimal("20000.00"))
        entry = AccountingPostingService.post_expense(expense, self.user)
        cr_lines = [l for l in entry.lines.all() if l.credit_amount > ZERO]
        payable_line = next((l for l in cr_lines if l.account == self.acct_payable), None)
        self.assertIsNotNone(payable_line)
        self.assertEqual(payable_line.credit_amount, Decimal("20000.00"))

    def test_draft_expense_not_posted(self):
        from financials.models import ExpenseCategory, Expense
        cat, _ = ExpenseCategory.objects.get_or_create(
            restaurant=self.restaurant, code="RENT_DFT",
            defaults={"name": "Rent Draft", "expense_account": self.acct_rent},
        )
        expense = Expense.objects.create(
            restaurant=self.restaurant,
            expense_number=f"EXP-DFT-{uuid.uuid4().hex[:6]}",
            category=cat, title="Draft Expense",
            amount=Decimal("1000"), tax_amount=ZERO, total_amount=Decimal("1000"),
            expense_date=date.today(), status="DRAFT", created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            AccountingPostingService.post_expense(expense, self.user)

    def test_duplicate_expense_posting_idempotent(self):
        expense = self._make_approved_expense()
        e1 = AccountingPostingService.post_expense(expense, self.user)
        e2 = AccountingPostingService.post_expense(expense, self.user)
        self.assertEqual(e1.pk, e2.pk)


# =============================================================================
# Supplier Invoice Posting
# =============================================================================

class SupplierInvoicePostingTests(AccountingTestBase):

    def _make_approved_invoice(self, subtotal=Decimal("10000.00"),
                                tax_amount=Decimal("1800.00")):
        from inventory.models import Supplier
        from financials.models import SupplierInvoice
        from financials.constants import SINV_APPROVED

        supplier, _ = Supplier.objects.get_or_create(
            restaurant=self.restaurant,
            code="SUPP001",
            defaults={"name": "Test Supplier"},
        )
        invoice = SupplierInvoice.objects.create(
            restaurant=self.restaurant,
            supplier=supplier,
            invoice_number=f"SINV-{uuid.uuid4().hex[:6].upper()}",
            invoice_date=date.today(),
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=ZERO,
            total_amount=subtotal + tax_amount,
            status=SINV_APPROVED,
            created_by=self.user,
            approved_by=self.user,
            approved_at=timezone.now(),
        )
        return invoice

    def test_post_approved_supplier_invoice(self):
        invoice = self._make_approved_invoice()
        entry = AccountingPostingService.post_supplier_invoice(invoice, self.user)
        self.assertEqual(entry.status, JE_POSTED)
        self.assertTrue(entry.is_balanced())

    def test_invoice_credits_accounts_payable(self):
        invoice = self._make_approved_invoice(Decimal("10000"), Decimal("1800"))
        entry = AccountingPostingService.post_supplier_invoice(invoice, self.user)
        cr_lines = [l for l in entry.lines.all() if l.credit_amount > ZERO]
        payable_line = next((l for l in cr_lines if l.account == self.acct_payable), None)
        self.assertIsNotNone(payable_line)
        self.assertEqual(payable_line.credit_amount, Decimal("11800.00"))

    def test_draft_invoice_not_posted(self):
        from inventory.models import Supplier
        from financials.models import SupplierInvoice
        supplier, _ = Supplier.objects.get_or_create(
            restaurant=self.restaurant, code="SUPP002",
            defaults={"name": "Supplier2"},
        )
        invoice = SupplierInvoice.objects.create(
            restaurant=self.restaurant, supplier=supplier,
            invoice_number=f"SINV-DFT-{uuid.uuid4().hex[:6]}",
            invoice_date=date.today(),
            subtotal=Decimal("1000"), tax_amount=ZERO,
            discount_amount=ZERO, total_amount=Decimal("1000"),
            status="DRAFT", created_by=self.user,
        )
        with self.assertRaises(ValidationError):
            AccountingPostingService.post_supplier_invoice(invoice, self.user)

    def test_duplicate_invoice_posting_idempotent(self):
        invoice = self._make_approved_invoice()
        e1 = AccountingPostingService.post_supplier_invoice(invoice, self.user)
        e2 = AccountingPostingService.post_supplier_invoice(invoice, self.user)
        self.assertEqual(e1.pk, e2.pk)
