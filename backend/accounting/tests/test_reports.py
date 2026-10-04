# =============================================================================
# RestaurantFlow — Accounting Reports Tests
# Phase 13
# =============================================================================

from decimal import Decimal
from datetime import date

from accounting.tests.base import AccountingTestBase, ZERO
from accounting.selectors import (
    get_trial_balance, get_profit_and_loss,
    get_balance_sheet, get_account_statement,
    get_general_ledger, get_cash_flow_basic,
)
from accounting.services import JournalService


class TrialBalanceTests(AccountingTestBase):

    def _post_balanced_entry(self, debit_acct, credit_acct, amount):
        entry = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(),
            description=f"TB Test {amount}", user=self.user,
        )
        JournalService.add_line(entry, debit_acct, debit_amount=amount, credit_amount=ZERO, user=self.user)
        JournalService.add_line(entry, credit_acct, debit_amount=ZERO, credit_amount=amount, user=self.user)
        return JournalService.post_entry(entry, self.user)

    def test_trial_balance_is_balanced(self):
        """Total debits MUST equal total credits in a correct trial balance."""
        self._post_balanced_entry(self.acct_cash, self.acct_sales, Decimal("500.00"))
        self._post_balanced_entry(self.acct_receivable, self.acct_sales, Decimal("300.00"))

        tb = get_trial_balance(self.restaurant)
        self.assertTrue(tb["is_balanced"],
                         f"Trial balance not balanced! Variance: {tb['variance']}")
        self.assertEqual(tb["variance"], ZERO)
        self.assertEqual(tb["grand_debit"], tb["grand_credit"])

    def test_trial_balance_identifies_imbalance(self):
        """
        Simulate an imbalanced state by directly writing a bad line.
        The trial balance must surface the variance, not hide it.
        """
        from accounting.models import JournalEntry, JournalEntryLine
        # Create a posted entry first
        entry = self._post_balanced_entry(self.acct_cash, self.acct_sales, Decimal("100.00"))

        # Forcefully add an extra debit-only line to the posted entry (bypass service)
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=self.acct_cash,
            debit_amount=Decimal("50.00"),
            credit_amount=ZERO,
            description="Forced imbalance for testing",
        )

        tb = get_trial_balance(self.restaurant)
        self.assertFalse(tb["is_balanced"])
        self.assertNotEqual(tb["variance"], ZERO)

    def test_trial_balance_excludes_draft_entries(self):
        """DRAFT and VOID entries must not appear in trial balance."""
        # Post a balanced entry
        self._post_balanced_entry(self.acct_cash, self.acct_sales, Decimal("200.00"))
        tb_before = get_trial_balance(self.restaurant)

        # Add a draft entry — should not change totals
        draft = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Draft", user=self.user,
        )
        JournalService.add_line(draft, self.acct_cash, debit_amount=Decimal("999.00"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(draft, self.acct_sales, debit_amount=ZERO, credit_amount=Decimal("999.00"), user=self.user)
        # Don't post it

        tb_after = get_trial_balance(self.restaurant)
        self.assertEqual(tb_before["grand_debit"], tb_after["grand_debit"])


class ProfitLossTests(AccountingTestBase):

    def test_profit_loss_revenue_and_cogs(self):
        # Post: Dr Receivable 1000, Cr Sales 1000
        e1 = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Sales", user=self.user,
        )
        JournalService.add_line(e1, self.acct_receivable, debit_amount=Decimal("1000"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(e1, self.acct_sales, debit_amount=ZERO, credit_amount=Decimal("1000"), user=self.user)
        JournalService.post_entry(e1, self.user)

        # Post: Dr COGS 300, Cr Inventory 300
        e2 = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="COGS", user=self.user,
        )
        JournalService.add_line(e2, self.acct_cogs, debit_amount=Decimal("300"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(e2, self.acct_inventory, debit_amount=ZERO, credit_amount=Decimal("300"), user=self.user)
        JournalService.post_entry(e2, self.user)

        pl = get_profit_and_loss(self.restaurant)
        self.assertEqual(pl["total_revenue"], Decimal("1000"))
        self.assertEqual(pl["total_cogs"], Decimal("300"))
        self.assertEqual(pl["gross_profit"], Decimal("700"))


class BalanceSheetTests(AccountingTestBase):

    def test_balance_sheet_assets_equals_liabilities_plus_equity(self):
        # Post: Dr Cash 5000, Cr Retained Earnings 5000
        e = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Initial capital", user=self.user,
        )
        JournalService.add_line(e, self.acct_cash, debit_amount=Decimal("5000"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(e, self.acct_retained, debit_amount=ZERO, credit_amount=Decimal("5000"), user=self.user)
        JournalService.post_entry(e, self.user)

        bs = get_balance_sheet(self.restaurant)
        self.assertTrue(bs["is_balanced"],
                         f"Balance sheet not balanced! Variance: {bs['variance']}")
        self.assertEqual(bs["variance"], ZERO)
        self.assertEqual(bs["total_assets"], bs["total_liabilities_and_equity"])

    def test_balance_sheet_with_payable(self):
        # Dr Inventory 1000, Cr Accounts Payable 1000
        e = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Purchase on credit", user=self.user,
        )
        JournalService.add_line(e, self.acct_inventory, debit_amount=Decimal("1000"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(e, self.acct_payable, debit_amount=ZERO, credit_amount=Decimal("1000"), user=self.user)
        JournalService.post_entry(e, self.user)

        bs = get_balance_sheet(self.restaurant)
        self.assertTrue(bs["is_balanced"])


class AccountStatementTests(AccountingTestBase):

    def test_account_statement_opening_balance(self):
        # Post a transaction for cash
        e = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Cash received", user=self.user,
        )
        JournalService.add_line(e, self.acct_cash, debit_amount=Decimal("2000"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(e, self.acct_sales, debit_amount=ZERO, credit_amount=Decimal("2000"), user=self.user)
        JournalService.post_entry(e, self.user)

        stmt = get_account_statement(self.acct_cash)
        self.assertEqual(len(stmt["transactions"]), 1)
        self.assertEqual(stmt["closing_balance"], Decimal("2000"))
        self.assertEqual(stmt["total_debits"], Decimal("2000"))

    def test_normal_balance_calculation(self):
        """
        For a DEBIT-normal account (Cash): balance = debits - credits.
        For a CREDIT-normal account (Sales): balance = credits - debits.
        """
        e = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Balance test", user=self.user,
        )
        JournalService.add_line(e, self.acct_cash, debit_amount=Decimal("500"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(e, self.acct_sales, debit_amount=ZERO, credit_amount=Decimal("500"), user=self.user)
        JournalService.post_entry(e, self.user)

        cash_stmt = get_account_statement(self.acct_cash)
        sales_stmt = get_account_statement(self.acct_sales)

        # Cash (debit normal): +500 debit = +500 balance
        self.assertEqual(cash_stmt["closing_balance"], Decimal("500"))
        # Sales (credit normal): +500 credit = +500 balance
        self.assertEqual(sales_stmt["closing_balance"], Decimal("500"))


class GeneralLedgerTests(AccountingTestBase):

    def test_general_ledger_returns_posted_entries(self):
        e = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="GL test", user=self.user,
        )
        JournalService.add_line(e, self.acct_cash, debit_amount=Decimal("100"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(e, self.acct_sales, debit_amount=ZERO, credit_amount=Decimal("100"), user=self.user)
        JournalService.post_entry(e, self.user)

        rows = get_general_ledger(self.restaurant)
        cash_rows = [r for r in rows if r["account_code"] == self.acct_cash.code]
        self.assertGreaterEqual(len(cash_rows), 1)

    def test_general_ledger_excludes_draft(self):
        draft = JournalService.create_draft(
            restaurant=self.restaurant, period=self.period,
            entry_date=date.today(), description="Draft GL", user=self.user,
        )
        JournalService.add_line(draft, self.acct_cash, debit_amount=Decimal("777"), credit_amount=ZERO, user=self.user)
        JournalService.add_line(draft, self.acct_sales, debit_amount=ZERO, credit_amount=Decimal("777"), user=self.user)
        # Do NOT post

        rows = get_general_ledger(self.restaurant)
        draft_rows = [r for r in rows if r["debit"] == Decimal("777")]
        self.assertEqual(len(draft_rows), 0)


class AccountingInvariantTests(AccountingTestBase):
    """
    Central accounting invariants verified across all posted entries.
    """

    def test_all_posted_entries_are_balanced(self):
        """For every POSTED journal entry: total debits == total credits."""
        from accounting.models import JournalEntry
        from accounting.constants import JE_POSTED

        # Create several entries
        amounts = [Decimal("100"), Decimal("500"), Decimal("2500"), Decimal("10000")]
        for amt in amounts:
            e = JournalService.create_draft(
                restaurant=self.restaurant, period=self.period,
                entry_date=date.today(), description=f"Invariant test {amt}",
                user=self.user,
            )
            JournalService.add_line(e, self.acct_cash, debit_amount=amt, credit_amount=ZERO, user=self.user)
            JournalService.add_line(e, self.acct_sales, debit_amount=ZERO, credit_amount=amt, user=self.user)
            JournalService.post_entry(e, self.user)

        posted_entries = JournalEntry.objects.filter(
            restaurant=self.restaurant, status=JE_POSTED
        )
        for entry in posted_entries:
            self.assertTrue(
                entry.is_balanced(),
                f"Entry {entry.entry_number} is NOT balanced! "
                f"Dr={entry.get_total_debits()} Cr={entry.get_total_credits()}"
            )

    def test_trial_balance_grand_totals_match(self):
        """grand_debit == grand_credit in trial balance for clean data."""
        tb = get_trial_balance(self.restaurant)
        self.assertEqual(
            tb["grand_debit"], tb["grand_credit"],
            f"Trial balance imbalanced: Dr={tb['grand_debit']} Cr={tb['grand_credit']}"
        )
