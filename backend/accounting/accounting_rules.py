# =============================================================================
# RestaurantFlow — Accounting Rules
# Phase 13
#
# This module contains the business accounting rules that determine
# which accounts are debited/credited for each source transaction type.
#
# Every rule function returns a list of (account, debit_amount, credit_amount, description)
# tuples. The calling service constructs JournalEntryLine objects from these.
#
# Rules are pure functions — they receive the source document and the
# AccountingSettings for the restaurant, and return line specifications.
# They do NOT touch the database directly.
# =============================================================================

from decimal import Decimal
from accounting.exceptions import AccountingSettingsNotConfiguredError

ZERO = Decimal("0.00")


def _require_account(settings_obj, attr_name, description):
    """Get a required account from settings, raising an error if not configured."""
    account = getattr(settings_obj, attr_name, None)
    if account is None:
        raise AccountingSettingsNotConfiguredError(
            f"Accounting setting '{description}' is not configured for this restaurant. "
            f"Configure it in Accounting Settings ({attr_name})."
        )
    return account


def build_bill_lines(bill, settings):
    """
    Build journal entry lines for a finalized Bill.

    Net revenue accounting method (discounts absorbed into taxable_amount):
        Dr  Accounts Receivable          (grand_total)
        Cr  Sales Revenue                (taxable_amount = subtotal - discount)
        Cr  Tax Payable                  (tax_amount)
        Dr/Cr Rounding Adjustment        (rounding_amount, if non-zero)

    Accounting policy note:
        Discounts are absorbed into taxable_amount by the billing layer
        (taxable_amount = subtotal - discount_amount). This means the discount
        is not posted as a separate debit to a discount expense account —
        it reduces the recognised revenue directly.
        This is the NET REVENUE method. If gross revenue accounting is required
        (posting discount as a separate Dr to default_discount_account), a
        future configuration flag can switch accounting_rules to the gross method.
    """
    receivable = _require_account(settings, "default_accounts_receivable", "Accounts Receivable")
    sales = _require_account(settings, "default_sales_account", "Sales Revenue")
    tax_payable = _require_account(settings, "default_tax_payable", "Tax Payable")

    grand_total = bill.grand_total
    tax_amount = bill.tax_amount
    discount_amount = bill.discount_amount
    rounding_amount = bill.rounding_amount
    taxable_amount = bill.taxable_amount

    lines = []

    # Dr Accounts Receivable (full amount owed by customer)
    lines.append({
        "account": receivable,
        "debit_amount": grand_total,
        "credit_amount": ZERO,
        "description": f"Sales receivable — {bill.bill_number}",
    })

    # Cr Sales Revenue (taxable amount = subtotal - discount)
    lines.append({
        "account": sales,
        "debit_amount": ZERO,
        "credit_amount": taxable_amount,
        "description": f"Sales revenue — {bill.bill_number}",
    })

    # Cr Tax Payable (if tax exists)
    if tax_amount > ZERO:
        lines.append({
            "account": tax_payable,
            "debit_amount": ZERO,
            "credit_amount": tax_amount,
            "description": f"Tax payable — {bill.bill_number}",
        })

    # Rounding adjustment (Dr or Cr depending on sign)
    if rounding_amount != ZERO and settings.default_rounding_account:
        rounding_acct = settings.default_rounding_account
        if rounding_amount > ZERO:
            # Positive rounding: customer pays a bit more → extra credit to rounding
            lines.append({
                "account": rounding_acct,
                "debit_amount": ZERO,
                "credit_amount": rounding_amount,
                "description": f"Rounding — {bill.bill_number}",
            })
        else:
            # Negative rounding: customer pays a bit less → debit rounding
            lines.append({
                "account": rounding_acct,
                "debit_amount": abs(rounding_amount),
                "credit_amount": ZERO,
                "description": f"Rounding — {bill.bill_number}",
            })

    return lines


def build_payment_lines(payment, settings):
    """
    Build journal entry lines for a completed customer Payment.

    Cash:
        Dr  Cash                         (payment.amount)
        Cr  Accounts Receivable          (payment.amount)

    UPI / Bank Transfer:
        Dr  UPI Clearing / Bank          (payment.amount)
        Cr  Accounts Receivable          (payment.amount)

    Card:
        Dr  Card Clearing                (payment.amount)
        Cr  Accounts Receivable          (payment.amount)

    Wallet / Net Banking / Other → default_bank_account
    """
    from payments.models import PaymentMethod

    receivable = _require_account(settings, "default_accounts_receivable", "Accounts Receivable")
    amount = payment.amount

    # Determine the debit (cash/clearing) account based on payment method
    method = payment.payment_method
    if method == PaymentMethod.CASH:
        debit_account = _require_account(settings, "default_cash_account", "Cash Account")
        debit_desc = "Cash received"
    elif method in (PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER):
        debit_account = (
            settings.default_upi_clearing_account
            or _require_account(settings, "default_bank_account", "Bank Account")
        )
        debit_desc = "UPI/Bank received"
    elif method == PaymentMethod.CARD:
        debit_account = (
            settings.default_card_clearing_account
            or _require_account(settings, "default_bank_account", "Bank Account")
        )
        debit_desc = "Card payment clearing"
    else:
        # WALLET, NET_BANKING, CHEQUE, CREDIT, OTHER → bank
        debit_account = _require_account(settings, "default_bank_account", "Bank Account")
        debit_desc = f"{method} received"

    return [
        {
            "account": debit_account,
            "debit_amount": amount,
            "credit_amount": ZERO,
            "description": f"{debit_desc} — {payment.payment_number}",
        },
        {
            "account": receivable,
            "debit_amount": ZERO,
            "credit_amount": amount,
            "description": f"Clear receivable — {payment.payment_number}",
        },
    ]


def build_refund_lines(refund, settings):
    """
    Build journal entry lines for a processed PaymentRefund.

    Reverses the payment entry:
        Dr  Accounts Receivable          (refund.amount)
        Cr  Cash / UPI / Card Clearing   (refund.amount)
    """
    from payments.models import PaymentMethod

    receivable = _require_account(settings, "default_accounts_receivable", "Accounts Receivable")
    payment = refund.payment
    amount = refund.amount
    method = payment.payment_method

    if method == PaymentMethod.CASH:
        credit_account = _require_account(settings, "default_cash_account", "Cash Account")
        credit_desc = "Cash refunded"
    elif method in (PaymentMethod.UPI, PaymentMethod.BANK_TRANSFER):
        credit_account = (
            settings.default_upi_clearing_account
            or _require_account(settings, "default_bank_account", "Bank Account")
        )
        credit_desc = "UPI/Bank refunded"
    elif method == PaymentMethod.CARD:
        credit_account = (
            settings.default_card_clearing_account
            or _require_account(settings, "default_bank_account", "Bank Account")
        )
        credit_desc = "Card refunded"
    else:
        credit_account = _require_account(settings, "default_bank_account", "Bank Account")
        credit_desc = f"{method} refunded"

    return [
        {
            "account": receivable,
            "debit_amount": amount,
            "credit_amount": ZERO,
            "description": f"Refund receivable — {refund.refund_number}",
        },
        {
            "account": credit_account,
            "debit_amount": ZERO,
            "credit_amount": amount,
            "description": f"{credit_desc} — {refund.refund_number}",
        },
    ]


def build_supplier_invoice_lines(invoice, settings):
    """
    Build journal entry lines for an approved SupplierInvoice.

    Inventory purchase:
        Dr  Inventory                    (invoice.subtotal)
        Dr  Input Tax / Tax Asset        (invoice.tax_amount)  [if any]
        Cr  Accounts Payable             (invoice.total_amount)
    """
    inventory = _require_account(settings, "default_inventory_account", "Inventory Account")
    payable = _require_account(settings, "default_accounts_payable", "Accounts Payable")

    subtotal = invoice.subtotal
    tax_amount = invoice.tax_amount
    total_amount = invoice.total_amount

    lines = [
        {
            "account": inventory,
            "debit_amount": subtotal,
            "credit_amount": ZERO,
            "description": f"Inventory purchase — {invoice.invoice_number}",
        },
    ]

    if tax_amount > ZERO:
        # Input tax treated as additional inventory cost (simple approach)
        # Future phases can separate input tax credit into a dedicated account
        lines.append({
            "account": inventory,
            "debit_amount": tax_amount,
            "credit_amount": ZERO,
            "description": f"Input tax on purchase — {invoice.invoice_number}",
        })

    lines.append({
        "account": payable,
        "debit_amount": ZERO,
        "credit_amount": total_amount,
        "description": f"Accounts payable — {invoice.invoice_number}",
    })

    return lines


def build_expense_lines(expense, settings):
    """
    Build journal entry lines for an approved Expense.

    Uses the expense category's mapped account if configured,
    otherwise falls back to a generic expense account from settings.

    Expense accrual:
        Dr  [Expense Account]            (expense.total_amount)
        Cr  Accounts Payable             (expense.total_amount)
    """
    payable = _require_account(settings, "default_accounts_payable", "Accounts Payable")
    total = expense.total_amount

    # Use category's expense_account if configured
    expense_account = None
    category = expense.category
    if hasattr(category, 'expense_account') and category.expense_account is not None:
        expense_account = category.expense_account

    if expense_account is None:
        raise AccountingSettingsNotConfiguredError(
            f"Expense category '{category.name}' has no expense_account mapped. "
            "Configure the expense account mapping in the expense category settings."
        )

    return [
        {
            "account": expense_account,
            "debit_amount": total,
            "credit_amount": ZERO,
            "description": f"Expense — {expense.expense_number} — {expense.title}",
        },
        {
            "account": payable,
            "debit_amount": ZERO,
            "credit_amount": total,
            "description": f"Payable for expense — {expense.expense_number}",
        },
    ]


def build_consumption_lines(consumption_batch, consumptions, settings):
    """
    Build journal entry lines for an inventory consumption (COGS).

    Uses the authoritative cost captured in StockConsumption records:
        Dr  Cost of Goods Sold           (total consumed cost)
        Cr  Inventory                    (total consumed cost)
    """
    cogs = _require_account(settings, "default_cogs_account", "Cost of Goods Sold")
    inventory = _require_account(settings, "default_inventory_account", "Inventory Account")

    total_cost = sum((c.total_cost for c in consumptions), ZERO)

    if total_cost == ZERO:
        return []

    return [
        {
            "account": cogs,
            "debit_amount": total_cost,
            "credit_amount": ZERO,
            "description": f"COGS — consumption batch {str(consumption_batch.pk)[:8]}",
        },
        {
            "account": inventory,
            "debit_amount": ZERO,
            "credit_amount": total_cost,
            "description": f"Inventory consumed — batch {str(consumption_batch.pk)[:8]}",
        },
    ]


def build_consumption_reversal_lines(original_entry_lines, settings):
    """
    Build reversal lines for a consumption reversal.
    Swaps debits/credits from the original consumption lines.

        Dr  Inventory                    (total consumed cost)
        Cr  Cost of Goods Sold           (total consumed cost)
    """
    reversal_lines = []
    for line in original_entry_lines:
        reversal_lines.append({
            "account": line.account,
            "debit_amount": line.credit_amount,   # swap
            "credit_amount": line.debit_amount,   # swap
            "description": f"Reversal: {line.description}",
        })
    return [l for l in reversal_lines if l["debit_amount"] > ZERO or l["credit_amount"] > ZERO]


def build_payable_payment_lines(payable, amount, payment_method, settings):
    """
    Build journal entry lines for settling a payable.

    Partial or full payable settlement:
        Dr  Accounts Payable             (amount paid)
        Cr  Cash / Bank                  (amount paid)
    """
    from payments.models import PaymentMethod as PM

    payable_account = _require_account(settings, "default_accounts_payable", "Accounts Payable")

    if payment_method == PM.CASH:
        credit_account = _require_account(settings, "default_cash_account", "Cash Account")
        desc = "Cash payment"
    else:
        credit_account = _require_account(settings, "default_bank_account", "Bank Account")
        desc = f"{payment_method} payment"

    return [
        {
            "account": payable_account,
            "debit_amount": amount,
            "credit_amount": ZERO,
            "description": f"{desc} — payable {payable.reference_number}",
        },
        {
            "account": credit_account,
            "debit_amount": ZERO,
            "credit_amount": amount,
            "description": f"Payable settled — {payable.reference_number}",
        },
    ]
