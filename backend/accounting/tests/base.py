# =============================================================================
# RestaurantFlow — Accounting Test Base
# Phase 13
#
# Shared fixtures and helpers for all accounting tests.
# Uses Django TestCase (no external DB required for unit tests).
# =============================================================================

import uuid
from decimal import Decimal
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone


ZERO = Decimal("0.00")


class AccountingTestBase(TestCase):
    """
    Base class for all accounting tests.

    Creates a minimal fixture tree:
        Organization → Restaurant → Branch
        User (superuser — bypasses all permission checks)
        FiscalYear + AccountingPeriod (OPEN, covers today)
        Chart of Accounts (standard set)
        AccountingSettings (all accounts wired up)
    """

    @classmethod
    def setUpTestData(cls):
        """Create shared fixtures once per TestCase class."""
        cls._create_org_tree()
        cls._create_user()
        cls._create_chart_of_accounts()
        cls._create_period()
        cls._create_accounting_settings()

    # -------------------------------------------------------------------------
    # Org tree
    # -------------------------------------------------------------------------

    @classmethod
    def _create_org_tree(cls):
        from organizations.models import Organization, Restaurant, Branch

        cls.org = Organization.objects.create(
            name="Test Org",
            slug=f"test-org-{uuid.uuid4().hex[:6]}",
            currency="INR",
        )
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Test Restaurant",
            slug=f"test-rest-{uuid.uuid4().hex[:6]}",
            code=f"TR{uuid.uuid4().hex[:4].upper()}",
        )
        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Main Branch",
            code=f"MB{uuid.uuid4().hex[:4].upper()}",
        )

    # -------------------------------------------------------------------------
    # User
    # -------------------------------------------------------------------------

    @classmethod
    def _create_user(cls):
        from accounts.models import User

        cls.user = User.objects.create_superuser(
            email=f"test-{uuid.uuid4().hex[:6]}@test.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    # -------------------------------------------------------------------------
    # Chart of accounts
    # -------------------------------------------------------------------------

    @classmethod
    def _create_chart_of_accounts(cls):
        from accounting.models import Account
        from accounting.constants import (
            ACCOUNT_TYPE_ASSET, ACCOUNT_TYPE_LIABILITY,
            ACCOUNT_TYPE_EQUITY, ACCOUNT_TYPE_REVENUE, ACCOUNT_TYPE_EXPENSE,
            NORMAL_BALANCE_DEBIT, NORMAL_BALANCE_CREDIT,
            SUBTYPE_CASH, SUBTYPE_BANK, SUBTYPE_ACCOUNTS_RECEIVABLE,
            SUBTYPE_INVENTORY, SUBTYPE_ACCOUNTS_PAYABLE, SUBTYPE_TAX_PAYABLE,
            SUBTYPE_FOOD_SALES, SUBTYPE_COST_OF_GOODS_SOLD,
            SUBTYPE_RENT, SUBTYPE_OTHER_EXPENSE,
            SUBTYPE_RETAINED_EARNINGS, SUBTYPE_DISCOUNTS,
            SUBTYPE_OTHER_LIABILITY,
        )

        def _acct(code, name, acct_type, normal, subtype="", group=False, postable=True):
            return Account.objects.create(
                restaurant=cls.restaurant,
                code=code,
                name=name,
                account_type=acct_type,
                normal_balance=normal,
                account_subtype=subtype,
                is_group=group,
                is_postable=postable,
                is_active=True,
            )

        D = NORMAL_BALANCE_DEBIT
        C = NORMAL_BALANCE_CREDIT
        A = ACCOUNT_TYPE_ASSET
        L = ACCOUNT_TYPE_LIABILITY
        E = ACCOUNT_TYPE_EQUITY
        R = ACCOUNT_TYPE_REVENUE
        X = ACCOUNT_TYPE_EXPENSE

        cls.acct_cash          = _acct("1100", "Cash",                A, D, SUBTYPE_CASH)
        cls.acct_bank          = _acct("1200", "Bank",                A, D, SUBTYPE_BANK)
        cls.acct_receivable    = _acct("1300", "Accounts Receivable", A, D, SUBTYPE_ACCOUNTS_RECEIVABLE)
        cls.acct_inventory     = _acct("1400", "Inventory",           A, D, SUBTYPE_INVENTORY)
        cls.acct_card          = _acct("1500", "Card Clearing",       A, D, SUBTYPE_ACCOUNTS_RECEIVABLE)
        cls.acct_upi           = _acct("1600", "UPI Clearing",        A, D, SUBTYPE_BANK)
        cls.acct_payable       = _acct("2100", "Accounts Payable",    L, C, SUBTYPE_ACCOUNTS_PAYABLE)
        cls.acct_tax_payable   = _acct("2200", "Tax Payable",         L, C, SUBTYPE_TAX_PAYABLE)
        cls.acct_retained      = _acct("3100", "Retained Earnings",   E, C, SUBTYPE_RETAINED_EARNINGS)
        cls.acct_sales         = _acct("4100", "Food Sales",          R, C, SUBTYPE_FOOD_SALES)
        cls.acct_discount      = _acct("4900", "Sales Discounts",     R, C, SUBTYPE_DISCOUNTS)
        cls.acct_cogs          = _acct("5100", "Cost of Goods Sold",  X, D, SUBTYPE_COST_OF_GOODS_SOLD)
        cls.acct_rent          = _acct("6100", "Rent Expense",        X, D, SUBTYPE_RENT)
        cls.acct_other_expense = _acct("6900", "Other Expense",       X, D, SUBTYPE_OTHER_EXPENSE)
        cls.acct_rounding      = _acct("7100", "Rounding Adj",        X, D, SUBTYPE_OTHER_EXPENSE)

        # Group (header) account — not postable
        cls.acct_assets_header = _acct("1000", "Assets", A, D, group=True, postable=False)

    # -------------------------------------------------------------------------
    # Accounting period
    # -------------------------------------------------------------------------

    @classmethod
    def _create_period(cls):
        from accounting.models import FiscalYear, AccountingPeriod

        today = date.today()
        cls.fiscal_year = FiscalYear.objects.create(
            restaurant=cls.restaurant,
            name="FY Test",
            start_date=date(today.year, 1, 1),
            end_date=date(today.year, 12, 31),
            status="OPEN",
        )
        cls.period = AccountingPeriod.objects.create(
            restaurant=cls.restaurant,
            fiscal_year=cls.fiscal_year,
            name=f"Period {today.month}/{today.year}",
            start_date=date(today.year, today.month, 1),
            end_date=date(today.year, today.month, 28) + timedelta(days=3),
            status="OPEN",
        )

    # -------------------------------------------------------------------------
    # Accounting settings
    # -------------------------------------------------------------------------

    @classmethod
    def _create_accounting_settings(cls):
        from accounting.models import AccountingSettings

        cls.settings = AccountingSettings.objects.create(
            restaurant=cls.restaurant,
            default_sales_account=cls.acct_sales,
            default_discount_account=cls.acct_discount,
            default_cash_account=cls.acct_cash,
            default_bank_account=cls.acct_bank,
            default_accounts_receivable=cls.acct_receivable,
            default_inventory_account=cls.acct_inventory,
            default_card_clearing_account=cls.acct_card,
            default_upi_clearing_account=cls.acct_upi,
            default_accounts_payable=cls.acct_payable,
            default_tax_payable=cls.acct_tax_payable,
            default_cogs_account=cls.acct_cogs,
            default_rounding_account=cls.acct_rounding,
            retained_earnings_account=cls.acct_retained,
        )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _make_journal_entry(self, description="Test JE", source_type="MANUAL",
                             source_id=None):
        """Create a balanced DRAFT journal entry with two lines."""
        from accounting.services import JournalService
        entry = JournalService.create_draft(
            restaurant=self.restaurant,
            period=self.period,
            entry_date=date.today(),
            description=description,
            user=self.user,
            source_type=source_type,
            source_id=source_id,
        )
        JournalService.add_line(
            entry, self.acct_cash,
            debit_amount=Decimal("100.00"), credit_amount=ZERO,
            user=self.user, description="Test debit",
        )
        JournalService.add_line(
            entry, self.acct_sales,
            debit_amount=ZERO, credit_amount=Decimal("100.00"),
            user=self.user, description="Test credit",
        )
        return entry

    def _post_journal_entry(self, entry=None):
        from accounting.services import JournalService
        if entry is None:
            entry = self._make_journal_entry()
        return JournalService.post_entry(entry, self.user)
