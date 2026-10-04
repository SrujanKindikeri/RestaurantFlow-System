# =============================================================================
# RestaurantFlow — Accounting Selectors (Read Layer)
# Phase 13
# =============================================================================

import logging
from decimal import Decimal
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce

from accounting.constants import (
    JE_POSTED,
    NORMAL_BALANCE_DEBIT, NORMAL_BALANCE_CREDIT,
    ACCOUNT_TYPE_ASSET, ACCOUNT_TYPE_LIABILITY,
    ACCOUNT_TYPE_EQUITY, ACCOUNT_TYPE_REVENUE, ACCOUNT_TYPE_EXPENSE,
    SUBTYPE_COST_OF_GOODS_SOLD, SUBTYPE_DISCOUNTS,
)

logger = logging.getLogger("accounting")
ZERO = Decimal("0.00")


def _line_qs(restaurant, account=None, date_from=None, date_to=None, period_id=None):
    """Base queryset for posted journal entry lines scoped to a restaurant."""
    from accounting.models import JournalEntryLine
    qs = JournalEntryLine.objects.filter(
        journal_entry__status=JE_POSTED,
        journal_entry__restaurant=restaurant,
    )
    if account is not None:
        qs = qs.filter(account=account)
    if date_from:
        qs = qs.filter(journal_entry__entry_date__gte=date_from)
    if date_to:
        qs = qs.filter(journal_entry__entry_date__lte=date_to)
    if period_id:
        qs = qs.filter(journal_entry__accounting_period_id=period_id)
    return qs


def _account_net_balance(restaurant, account, date_from=None, date_to=None, period_id=None):
    """Net balance for one account (positive = normal side)."""
    t = _line_qs(restaurant, account, date_from, date_to, period_id).aggregate(
        d=Coalesce(Sum("debit_amount"), ZERO, output_field=DecimalField()),
        c=Coalesce(Sum("credit_amount"), ZERO, output_field=DecimalField()),
    )
    if account.normal_balance == NORMAL_BALANCE_CREDIT:
        return t["c"] - t["d"]
    return t["d"] - t["c"]


def get_account_balance(account, date_from=None, date_to=None):
    """Balance for a single account (positive = normal side)."""
    return _account_net_balance(account.restaurant, account, date_from, date_to)


def get_general_ledger(restaurant, filters=None):
    """
    Return general ledger data with running balance per account.
    filters: account_id, branch_id, date_from, date_to, period_id, source_type
    """
    from accounting.models import JournalEntryLine
    filters = filters or {}

    qs = JournalEntryLine.objects.filter(
        journal_entry__restaurant=restaurant,
        journal_entry__status=JE_POSTED,
    ).select_related(
        "journal_entry", "journal_entry__accounting_period",
        "journal_entry__branch", "account",
    ).order_by("account__code", "journal_entry__entry_date", "journal_entry__entry_number")

    if filters.get("account_id"):
        qs = qs.filter(account_id=filters["account_id"])
    if filters.get("branch_id"):
        qs = qs.filter(journal_entry__branch_id=filters["branch_id"])
    if filters.get("date_from"):
        qs = qs.filter(journal_entry__entry_date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(journal_entry__entry_date__lte=filters["date_to"])
    if filters.get("period_id"):
        qs = qs.filter(journal_entry__accounting_period_id=filters["period_id"])
    if filters.get("source_type"):
        qs = qs.filter(journal_entry__source_type=filters["source_type"])

    rows = []
    current_account_id = None
    running_balance = ZERO

    for line in qs:
        if current_account_id != line.account_id:
            current_account_id = line.account_id
            running_balance = ZERO
        account = line.account
        if account.normal_balance == NORMAL_BALANCE_DEBIT:
            running_balance += line.debit_amount - line.credit_amount
        else:
            running_balance += line.credit_amount - line.debit_amount
        rows.append({
            "date": line.journal_entry.entry_date,
            "journal_number": line.journal_entry.entry_number,
            "description": line.description or line.journal_entry.description,
            "debit": line.debit_amount,
            "credit": line.credit_amount,
            "balance": running_balance,
            "account_code": account.code,
            "account_name": account.name,
            "source_type": line.journal_entry.source_type,
            "source_id": line.journal_entry.source_id,
            "branch": line.journal_entry.branch.name if line.journal_entry.branch else None,
            "journal_entry_id": str(line.journal_entry.pk),
            "line_id": str(line.pk),
        })
    return rows


def get_account_statement(account, date_from=None, date_to=None):
    """Account statement with opening balance, transactions, closing balance."""
    from accounting.models import JournalEntryLine

    opening_balance = ZERO
    if date_from:
        # Opening balance = all movements BEFORE date_from (exclusive boundary).
        # Using date_from - 1 day ensures transactions on date_from are not
        # double-counted in both the opening balance and the transaction list.
        from datetime import timedelta, date as date_type
        if isinstance(date_from, str):
            from datetime import date as _d
            date_from_obj = _d.fromisoformat(date_from)
        else:
            date_from_obj = date_from
        opening_balance = _account_net_balance(
            account.restaurant, account, date_to=date_from_obj - timedelta(days=1)
        )

    qs = JournalEntryLine.objects.filter(
        journal_entry__status=JE_POSTED,
        account=account,
    ).select_related("journal_entry").order_by(
        "journal_entry__entry_date", "journal_entry__entry_number"
    )
    if date_from:
        qs = qs.filter(journal_entry__entry_date__gte=date_from)
    if date_to:
        qs = qs.filter(journal_entry__entry_date__lte=date_to)

    transactions = []
    running = opening_balance
    for line in qs:
        je = line.journal_entry
        if account.normal_balance == NORMAL_BALANCE_DEBIT:
            movement = line.debit_amount - line.credit_amount
        else:
            movement = line.credit_amount - line.debit_amount
        running += movement
        transactions.append({
            "date": je.entry_date,
            "journal_number": je.entry_number,
            "description": line.description or je.description,
            "debit": line.debit_amount,
            "credit": line.credit_amount,
            "balance": running,
        })

    return {
        "account_code": account.code,
        "account_name": account.name,
        "account_type": account.account_type,
        "normal_balance": account.normal_balance,
        "opening_balance": opening_balance,
        "transactions": transactions,
        "closing_balance": running,
        "total_debits": sum(t["debit"] for t in transactions),
        "total_credits": sum(t["credit"] for t in transactions),
    }


def get_trial_balance(restaurant, date_from=None, date_to=None, period_id=None):
    """
    Trial balance: debit/credit totals per account.
    grand_debit MUST equal grand_credit — any variance is flagged.
    """
    from accounting.models import Account

    accounts = Account.objects.filter(
        restaurant=restaurant, is_active=True
    ).order_by("code")

    rows = []
    grand_debit = ZERO
    grand_credit = ZERO

    for account in accounts:
        t = _line_qs(restaurant, account, date_from, date_to, period_id).aggregate(
            d=Coalesce(Sum("debit_amount"), ZERO, output_field=DecimalField()),
            c=Coalesce(Sum("credit_amount"), ZERO, output_field=DecimalField()),
        )
        d, c = t["d"], t["c"]
        if d == ZERO and c == ZERO:
            continue
        rows.append({
            "account_code": account.code,
            "account_name": account.name,
            "account_type": account.account_type,
            "normal_balance": account.normal_balance,
            "debit_total": d,
            "credit_total": c,
        })
        grand_debit += d
        grand_credit += c

    return {
        "accounts": rows,
        "grand_debit": grand_debit,
        "grand_credit": grand_credit,
        "is_balanced": grand_debit == grand_credit,
        "variance": grand_debit - grand_credit,
    }


def get_profit_and_loss(restaurant, date_from=None, date_to=None, period_id=None):
    """P&L from posted journal entries only."""
    from accounting.models import Account

    revenue_accounts = Account.objects.filter(
        restaurant=restaurant, account_type=ACCOUNT_TYPE_REVENUE, is_active=True
    ).order_by("code")
    expense_accounts = Account.objects.filter(
        restaurant=restaurant, account_type=ACCOUNT_TYPE_EXPENSE, is_active=True
    ).order_by("code")

    revenue_rows = []
    total_revenue = ZERO
    for acct in revenue_accounts:
        bal = _account_net_balance(restaurant, acct, date_from, date_to, period_id)
        if bal != ZERO:
            revenue_rows.append({
                "code": acct.code, "name": acct.name,
                "subtype": acct.account_subtype, "balance": bal,
            })
            total_revenue += bal

    cogs_rows = []
    opex_rows = []
    total_cogs = ZERO
    total_opex = ZERO

    for acct in expense_accounts:
        bal = _account_net_balance(restaurant, acct, date_from, date_to, period_id)
        if bal == ZERO:
            continue
        entry = {"code": acct.code, "name": acct.name,
                 "subtype": acct.account_subtype, "balance": bal}
        if acct.account_subtype == SUBTYPE_COST_OF_GOODS_SOLD:
            cogs_rows.append(entry)
            total_cogs += bal
        else:
            opex_rows.append(entry)
            total_opex += bal

    gross_profit = total_revenue - total_cogs
    operating_profit = gross_profit - total_opex

    return {
        "revenue": revenue_rows,
        "total_revenue": total_revenue,
        "cogs": cogs_rows,
        "total_cogs": total_cogs,
        "gross_profit": gross_profit,
        "operating_expenses": opex_rows,
        "total_operating_expenses": total_opex,
        "operating_profit": operating_profit,
    }


def get_balance_sheet(restaurant, as_of_date=None):
    """
    Balance Sheet: Assets = Liabilities + Equity.
    Uses all posted entries up to as_of_date.
    """
    from accounting.models import Account

    kwargs = {"date_to": as_of_date} if as_of_date else {}

    def _section(acct_type):
        accounts = Account.objects.filter(
            restaurant=restaurant, account_type=acct_type, is_active=True
        ).order_by("code")
        rows = []
        total = ZERO
        for acct in accounts:
            bal = _account_net_balance(restaurant, acct, **kwargs)
            if bal != ZERO:
                rows.append({
                    "code": acct.code, "name": acct.name,
                    "subtype": acct.account_subtype, "balance": bal,
                })
                total += bal
        return rows, total

    asset_rows, total_assets = _section(ACCOUNT_TYPE_ASSET)
    liability_rows, total_liabilities = _section(ACCOUNT_TYPE_LIABILITY)
    equity_rows, total_equity = _section(ACCOUNT_TYPE_EQUITY)

    total_liabilities_and_equity = total_liabilities + total_equity
    is_balanced = total_assets == total_liabilities_and_equity

    return {
        "assets": asset_rows,
        "total_assets": total_assets,
        "liabilities": liability_rows,
        "total_liabilities": total_liabilities,
        "equity": equity_rows,
        "total_equity": total_equity,
        "total_liabilities_and_equity": total_liabilities_and_equity,
        "is_balanced": is_balanced,
        "variance": total_assets - total_liabilities_and_equity,
    }


def get_cash_flow_basic(restaurant, date_from=None, date_to=None):
    """
    Basic cash/bank movement report from posted journal entries.
    Aggregates movements through cash and bank accounts.
    """
    from accounting.models import Account
    from accounting.constants import SUBTYPE_CASH, SUBTYPE_BANK

    cash_accounts = Account.objects.filter(
        restaurant=restaurant,
        account_subtype__in=[SUBTYPE_CASH, SUBTYPE_BANK],
        is_active=True,
    )

    inflows = ZERO
    outflows = ZERO
    rows = []

    for acct in cash_accounts:
        qs = _line_qs(restaurant, acct, date_from, date_to)
        t = qs.aggregate(
            d=Coalesce(Sum("debit_amount"), ZERO, output_field=DecimalField()),
            c=Coalesce(Sum("credit_amount"), ZERO, output_field=DecimalField()),
        )
        d, c = t["d"], t["c"]
        # For asset accounts: debit = inflow, credit = outflow
        net = d - c
        inflows += d
        outflows += c
        rows.append({
            "account_code": acct.code,
            "account_name": acct.name,
            "subtype": acct.account_subtype,
            "inflows": d,
            "outflows": c,
            "net": net,
        })

    return {
        "accounts": rows,
        "total_inflows": inflows,
        "total_outflows": outflows,
        "net_cash_movement": inflows - outflows,
    }


def get_accounting_dashboard(restaurant, period_id=None):
    """
    Aggregate key accounting metrics for the dashboard.
    All values come from POSTED journal entries only.
    """
    from accounting.models import AccountingPeriod
    from accounting.constants import PERIOD_OPEN

    pl = get_profit_and_loss(restaurant, period_id=period_id)
    bs = get_balance_sheet(restaurant)
    tb = get_trial_balance(restaurant, period_id=period_id)

    # Open periods count
    open_periods = AccountingPeriod.objects.filter(
        restaurant=restaurant, status=PERIOD_OPEN
    ).count()

    return {
        "total_revenue": pl["total_revenue"],
        "total_cogs": pl["total_cogs"],
        "gross_profit": pl["gross_profit"],
        "operating_profit": pl["operating_profit"],
        "total_assets": bs["total_assets"],
        "total_liabilities": bs["total_liabilities"],
        "total_equity": bs["total_equity"],
        "balance_sheet_balanced": bs["is_balanced"],
        "trial_balance_balanced": tb["is_balanced"],
        "trial_balance_variance": tb["variance"],
        "open_periods_count": open_periods,
    }
