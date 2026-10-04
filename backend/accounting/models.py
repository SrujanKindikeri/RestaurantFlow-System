# =============================================================================
# RestaurantFlow — Accounting Models
# Phase 13: Accounting Ledger, Double-Entry Bookkeeping, Financial Statements
#
# Model hierarchy:
#   FiscalYear                — restaurant-scoped fiscal year boundaries
#   AccountingPeriod          — monthly/quarterly periods within a fiscal year
#   Account                   — Chart of Accounts (hierarchical)
#   AccountingSettings        — per-restaurant system account configuration
#   JournalSequence           — concurrency-safe JE number generation
#   JournalEntry              — double-entry accounting document
#   JournalEntryLine          — individual debit/credit line on a journal entry
#   AccountingAuditLog        — immutable append-only audit trail
#
# Design principles:
#   - UUID primary keys on all models.
#   - All monetary values use DecimalField — NEVER float.
#   - Posted journal entries are IMMUTABLE (service-enforced).
#   - Every posted JournalEntry must satisfy: total debits == total credits.
#   - Account code unique per restaurant.
#   - JournalEntry number unique per restaurant (concurrency-safe).
#   - Source uniqueness: one primary posting per source transaction.
#   - Audit log rows cannot be updated after creation.
#   - Organization isolation enforced via restaurant FK scoping.
#
# Double-entry invariant (CENTRAL RULE):
#   For every POSTED JournalEntry:
#       sum(line.debit_amount for all lines) == sum(line.credit_amount for all lines)
#
# Normal balance rules:
#   Asset / Expense accounts   → DEBIT normal balance
#   Liability / Equity / Revenue → CREDIT normal balance
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel
from accounting.constants import (
    FISCAL_YEAR_STATUS_CHOICES, FY_OPEN,
    PERIOD_STATUS_CHOICES, PERIOD_OPEN,
    ACCOUNT_TYPE_CHOICES,
    ACCOUNT_SUBTYPE_CHOICES,
    NORMAL_BALANCE_CHOICES,
    JOURNAL_ENTRY_STATUS_CHOICES, JE_DRAFT,
    SOURCE_TYPE_CHOICES, SOURCE_MANUAL,
    REFERENCE_TYPE_CHOICES,
    AUDIT_ACTION_CHOICES,
)

logger = logging.getLogger("accounting")


# =============================================================================
# FiscalYear
# =============================================================================

class FiscalYear(TimestampedModel):
    """
    A fiscal year boundary for a restaurant.

    Each restaurant configures their own fiscal year independently —
    not all companies use the same fiscal calendar.

    Rules:
        - No overlapping fiscal years within the same restaurant.
        - A closed fiscal year cannot receive normal postings.
        - Fiscal years provide the outer container for AccountingPeriods.

    Example: FY 2026-27  (April 2026 – March 2027 for Indian restaurants)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="fiscal_years",
        db_index=True,
    )

    name = models.CharField(
        max_length=100,
        help_text="Human-readable name, e.g. 'FY 2026-27'.",
    )
    start_date = models.DateField(
        help_text="First day of the fiscal year.",
    )
    end_date = models.DateField(
        help_text="Last day of the fiscal year.",
    )
    status = models.CharField(
        max_length=10,
        choices=FISCAL_YEAR_STATUS_CHOICES,
        default=FY_OPEN,
        db_index=True,
    )

    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_fiscal_years",
    )

    class Meta:
        verbose_name = "Fiscal Year"
        verbose_name_plural = "Fiscal Years"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "start_date"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.status}] — {self.restaurant.name}"

    @property
    def is_open(self) -> bool:
        from accounting.constants import FY_OPEN
        return self.status == FY_OPEN


# =============================================================================
# AccountingPeriod
# =============================================================================

class AccountingPeriod(TimestampedModel):
    """
    A discrete accounting period (typically monthly) within a fiscal year.

    Rules:
        - Period belongs to a restaurant.
        - Only one open period should exist at a time for a restaurant
          (business rule; validated in service layer).
        - Period dates cannot overlap with other periods for the same restaurant.
        - Period dates must fall within the parent fiscal year's range.
        - CLOSED periods cannot accept new posted journal entries.
        - Historical records remain immutable after closure.
        - CLOSED periods can be reopened by authorized users.

    Status transitions:
        OPEN → CLOSE_REQUESTED → CLOSED → OPEN (controlled reopen)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="accounting_periods",
        db_index=True,
    )
    fiscal_year = models.ForeignKey(
        FiscalYear,
        on_delete=models.PROTECT,
        related_name="periods",
        db_index=True,
        null=True,
        blank=True,
        help_text="The fiscal year this period belongs to. Optional for flexibility.",
    )

    name = models.CharField(
        max_length=100,
        help_text="Human-readable name, e.g. 'January 2026'.",
    )
    start_date = models.DateField(
        db_index=True,
        help_text="First day of the period (inclusive).",
    )
    end_date = models.DateField(
        db_index=True,
        help_text="Last day of the period (inclusive).",
    )
    status = models.CharField(
        max_length=20,
        choices=PERIOD_STATUS_CHOICES,
        default=PERIOD_OPEN,
        db_index=True,
    )

    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_accounting_periods",
    )
    closing_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Accounting Period"
        verbose_name_plural = "Accounting Periods"
        ordering = ["-start_date"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "start_date"]),
            models.Index(fields=["restaurant", "end_date"]),
            models.Index(fields=["fiscal_year", "status"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.status}] — {self.restaurant.name}"

    @property
    def is_open(self) -> bool:
        from accounting.constants import PERIOD_OPEN
        return self.status == PERIOD_OPEN

    def contains_date(self, d) -> bool:
        """Return True if the given date falls within this period."""
        return self.start_date <= d <= self.end_date


# =============================================================================
# Account (Chart of Accounts)
# =============================================================================

class Account(TimestampedModel):
    """
    A single account in the Chart of Accounts.

    Hierarchical structure via self-referential parent_account FK.
    Parent-child cycles are prevented in the service layer.

    Group accounts (is_group=True) are header/parent accounts and should
    not normally be used for direct posting (is_postable=False).
    Leaf accounts should have is_postable=True.

    System accounts (is_system_account=True) are created by the system setup
    and are referenced by AccountingSettings for automatic posting.
    Their codes are stable and used for lookup, never hard-coded IDs.

    Normal balance follows accounting standards:
        Asset / Expense        → DEBIT
        Liability / Equity / Revenue → CREDIT

    Account code uniqueness enforced at DB level per restaurant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="accounts",
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    code = models.CharField(
        max_length=20,
        db_index=True,
        help_text=(
            "Unique account code within the restaurant. "
            "Example: 1100 for Cash, 2100 for Accounts Payable. "
            "Never auto-generated using MAX()+1."
        ),
    )
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Type classification
    # -------------------------------------------------------------------------
    account_type = models.CharField(
        max_length=15,
        choices=ACCOUNT_TYPE_CHOICES,
        db_index=True,
        help_text="One of: ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE.",
    )
    account_subtype = models.CharField(
        max_length=30,
        choices=ACCOUNT_SUBTYPE_CHOICES,
        blank=True,
        db_index=True,
        help_text="Optional detailed subtype, e.g. CASH, BANK, ACCOUNTS_RECEIVABLE.",
    )

    # -------------------------------------------------------------------------
    # Hierarchy
    # -------------------------------------------------------------------------
    parent_account = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        db_index=True,
        help_text=(
            "Parent account for hierarchical grouping. "
            "Null for top-level accounts. "
            "Cycles are prevented by the service layer."
        ),
    )

    # -------------------------------------------------------------------------
    # Behaviour flags
    # -------------------------------------------------------------------------
    is_group = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "True for header/group accounts that contain sub-accounts. "
            "Group accounts are normally not postable."
        ),
    )
    is_postable = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "True if this account can receive direct debit/credit entries. "
            "Group accounts should have is_postable=False."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=(
            "Inactive accounts cannot be used in new journal entries. "
            "Use deactivate instead of delete to preserve historical records."
        ),
    )
    is_system_account = models.BooleanField(
        default=False,
        db_index=True,
        help_text=(
            "True for accounts required by the automatic posting system. "
            "System accounts are identified by stable codes, never hard-coded IDs."
        ),
    )

    # -------------------------------------------------------------------------
    # Accounting standard
    # -------------------------------------------------------------------------
    normal_balance = models.CharField(
        max_length=6,
        choices=NORMAL_BALANCE_CHOICES,
        help_text=(
            "DEBIT for Asset/Expense accounts; "
            "CREDIT for Liability/Equity/Revenue accounts. "
            "Determines how balance increases/decreases."
        ),
    )

    class Meta:
        verbose_name = "Account"
        verbose_name_plural = "Accounts"
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_account_code_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "account_type"]),
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "is_system_account"]),
            models.Index(fields=["restaurant", "code"]),
            models.Index(fields=["parent_account"]),
            models.Index(fields=["account_type", "account_subtype"]),
        ]

    def __str__(self):
        return f"[{self.code}] {self.name} ({self.account_type})"

    def get_ancestors(self):
        """Return a list of ancestors (parent, grandparent, ...) in root-first order."""
        ancestors = []
        current = self.parent_account
        seen = set()
        while current is not None:
            if current.pk in seen:
                break  # cycle guard
            seen.add(current.pk)
            ancestors.insert(0, current)
            current = current.parent_account
        return ancestors

    def has_ancestor(self, candidate_pk) -> bool:
        """Check if candidate_pk is an ancestor of this account (cycle detection)."""
        seen = set()
        current = self.parent_account
        while current is not None:
            if current.pk in seen:
                return False
            if current.pk == candidate_pk:
                return True
            seen.add(current.pk)
            current = current.parent_account
        return False


# =============================================================================
# AccountingSettings
# =============================================================================

class AccountingSettings(TimestampedModel):
    """
    Restaurant-specific accounting configuration.

    Maps system-level posting roles to concrete Account instances.
    This is the single source of truth for automatic posting account selection.

    Validation (enforced in service/serializer):
        - All referenced accounts must belong to the same restaurant.
        - All referenced accounts must be active.
        - All referenced accounts must be postable (is_postable=True).
        - Accounts must have the correct account_type for their role:
            cash/bank/clearing → ASSET
            payable → LIABILITY
            sales → REVENUE
            cogs/discount/expense → EXPENSE
            tax_payable → LIABILITY

    Each restaurant configures these independently; there is no global default.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.OneToOneField(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="accounting_settings",
    )

    # Revenue / Sales
    default_sales_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Default sales revenue account (REVENUE type).",
    )
    default_discount_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Sales discount account (REVENUE/EXPENSE type).",
    )

    # Asset accounts
    default_cash_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Cash on hand account (ASSET type).",
    )
    default_bank_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Bank account (ASSET type).",
    )
    default_accounts_receivable = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Accounts receivable / POS clearing account (ASSET type).",
    )
    default_inventory_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Inventory asset account (ASSET type).",
    )
    default_card_clearing_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Card payment clearing account (ASSET type).",
    )
    default_upi_clearing_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="UPI / bank transfer clearing account (ASSET type).",
    )

    # Liability accounts
    default_accounts_payable = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Accounts payable account (LIABILITY type).",
    )
    default_tax_payable = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Tax payable / GST payable account (LIABILITY type).",
    )

    # Expense accounts
    default_cogs_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Cost of Goods Sold account (EXPENSE type).",
    )
    default_rounding_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Rounding adjustment account.",
    )

    # Equity
    retained_earnings_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="+",
        help_text="Retained earnings equity account.",
    )

    class Meta:
        verbose_name = "Accounting Settings"
        verbose_name_plural = "Accounting Settings"

    def __str__(self):
        return f"AccountingSettings — {self.restaurant.name}"


# =============================================================================
# JournalSequence
# =============================================================================

class JournalSequence(TimestampedModel):
    """
    Concurrency-safe journal entry number sequence per restaurant.

    One row per restaurant. select_for_update() is used in the service.
    Format: JE-{seq:06d}  e.g. JE-000001

    Never uses MAX()+1 — always uses DB-level locking.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.OneToOneField(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="journal_sequence",
    )
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Journal Sequence"
        verbose_name_plural = "Journal Sequences"

    def __str__(self):
        return f"JournalSeq restaurant={self.restaurant.name} seq={self.last_sequence}"


# =============================================================================
# JournalEntry
# =============================================================================

class JournalEntry(TimestampedModel):
    """
    A double-entry accounting transaction.

    Every financial event in RestaurantFlow generates (or should generate)
    a JournalEntry with at least two JournalEntryLines that balance:

        TOTAL DEBITS == TOTAL CREDITS  (the central accounting invariant)

    Status lifecycle:
        DRAFT   → POSTED   (immutable after this point)
        POSTED  → REVERSED (original entry preserved; reversal entry created)
        DRAFT   → VOID     (discarded before posting)

    Immutability:
        Once POSTED, the entry and its lines CANNOT be modified.
        Corrections are handled by:
            1. Creating a reversal entry (swaps debits/credits)
            2. Creating a new corrected entry

    Source tracking:
        source_type + source_id identify the business transaction that
        triggered this journal entry. These prevent duplicate postings.
        Use SOURCE_MANUAL for manually created entries.

    Reference tracking (additional context):
        reference_type + reference_id provide additional context about
        the specific document or event within the source.

    Entry number format: JE-000001, JE-000002, ...
    Generated using select_for_update() on JournalSequence — never MAX()+1.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="journal_entries",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journal_entries",
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Entry identification
    # -------------------------------------------------------------------------
    entry_number = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Human-readable entry number. Format: JE-NNNNNN. Immutable.",
    )
    accounting_period = models.ForeignKey(
        AccountingPeriod,
        on_delete=models.PROTECT,
        related_name="journal_entries",
        db_index=True,
    )
    entry_date = models.DateField(
        db_index=True,
        help_text="The accounting date of this entry (falls within accounting_period).",
    )
    description = models.TextField(
        help_text="Human-readable description of the accounting event.",
    )

    # -------------------------------------------------------------------------
    # Source tracking — identifies the originating business transaction
    # -------------------------------------------------------------------------
    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_TYPE_CHOICES,
        default=SOURCE_MANUAL,
        db_index=True,
        help_text=(
            "Type of the originating business transaction. "
            "BILL, PAYMENT, EXPENSE, SUPPLIER_INVOICE, etc."
        ),
    )
    source_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the originating source document.",
    )

    # -------------------------------------------------------------------------
    # Additional reference context
    # -------------------------------------------------------------------------
    reference_type = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text="Additional context type (e.g. BILL_ITEM, PAYMENT).",
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the additional context document.",
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=10,
        choices=JOURNAL_ENTRY_STATUS_CHOICES,
        default=JE_DRAFT,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Actors
    # -------------------------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_journal_entries",
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="posted_journal_entries",
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversed_journal_entries",
    )
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversal_reason = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Reversal linkage
    # -------------------------------------------------------------------------
    reversal_of = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal_entry",
        help_text="If this is a reversal entry, points to the original entry.",
    )

    class Meta:
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"
        ordering = ["-entry_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "entry_number"],
                name="unique_journal_entry_number_per_restaurant",
            ),
            # Prevent duplicate primary postings from the same source
            models.UniqueConstraint(
                fields=["source_type", "source_id"],
                condition=models.Q(
                    status__in=["POSTED"],
                    source_type__in=[
                        "BILL", "PAYMENT", "PAYMENT_REFUND",
                        "SUPPLIER_INVOICE", "EXPENSE",
                        "INVENTORY_CONSUMPTION", "CONSUMPTION_REVERSAL",
                    ]
                ),
                name="unique_primary_posting_per_source",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "entry_date"]),
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "accounting_period"]),
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["entry_date", "status"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["branch", "entry_date"]),
        ]

    def __str__(self):
        return f"{self.entry_number} [{self.status}] {self.entry_date} — {self.description[:50]}"

    @property
    def is_posted(self) -> bool:
        from accounting.constants import JE_POSTED
        return self.status == JE_POSTED

    @property
    def is_editable(self) -> bool:
        """Only DRAFT entries can be modified."""
        from accounting.constants import JE_DRAFT
        return self.status == JE_DRAFT

    def get_total_debits(self):
        from decimal import Decimal
        return sum(
            (line.debit_amount for line in self.lines.all()),
            Decimal("0.00")
        )

    def get_total_credits(self):
        from decimal import Decimal
        return sum(
            (line.credit_amount for line in self.lines.all()),
            Decimal("0.00")
        )

    def is_balanced(self) -> bool:
        return self.get_total_debits() == self.get_total_credits()


# =============================================================================
# JournalEntryLine
# =============================================================================

class JournalEntryLine(TimestampedModel):
    """
    A single debit or credit line in a JournalEntry.

    Rules enforced at model and service level:
        1. Exactly ONE of debit_amount or credit_amount must be > 0.
        2. Both debit_amount and credit_amount cannot be non-zero simultaneously.
        3. Both values are >= 0 (no negative amounts).
        4. A journal entry requires at least 2 lines.
        5. The account must belong to the same restaurant as the journal entry.
        6. The account must be active.
        7. The account must be postable (is_postable=True).
        8. Across all lines in one entry: sum(debits) == sum(credits).

    All monetary amounts use DecimalField — NEVER float.

    Reference fields (optional):
        reference_type + reference_id provide line-level context to the
        specific sub-document (e.g. a BillItem, a StockConsumption).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="lines",
        db_index=True,
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="journal_lines",
        db_index=True,
        help_text="The account being debited or credited.",
    )
    description = models.CharField(
        max_length=300,
        blank=True,
        help_text="Optional line-level description.",
    )

    # -------------------------------------------------------------------------
    # Debit / Credit amounts — exactly one must be > 0; both >= 0
    # -------------------------------------------------------------------------
    debit_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text=(
            "Debit amount for this line. "
            "Must be >= 0. "
            "Exactly one of debit_amount or credit_amount must be > 0."
        ),
    )
    credit_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text=(
            "Credit amount for this line. "
            "Must be >= 0. "
            "Exactly one of debit_amount or credit_amount must be > 0."
        ),
    )

    # -------------------------------------------------------------------------
    # Optional line-level reference
    # -------------------------------------------------------------------------
    reference_type = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text="Type of the source sub-document for this line.",
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the source sub-document.",
    )

    class Meta:
        verbose_name = "Journal Entry Line"
        verbose_name_plural = "Journal Entry Lines"
        ordering = ["created_at"]
        constraints = [
            # debit_amount >= 0
            models.CheckConstraint(
                check=models.Q(debit_amount__gte=0),
                name="je_line_debit_non_negative",
            ),
            # credit_amount >= 0
            models.CheckConstraint(
                check=models.Q(credit_amount__gte=0),
                name="je_line_credit_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["journal_entry", "account"]),
            models.Index(fields=["account", "created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]

    def __str__(self):
        if self.debit_amount > 0:
            return f"Dr {self.account.code} {self.debit_amount} — {self.journal_entry.entry_number}"
        return f"Cr {self.account.code} {self.credit_amount} — {self.journal_entry.entry_number}"

    @property
    def is_debit(self) -> bool:
        return self.debit_amount > 0

    @property
    def is_credit(self) -> bool:
        return self.credit_amount > 0

    def clean(self):
        """
        Validate the debit XOR credit rule.
        Called by full_clean(); also validated in the service layer.
        """
        from decimal import Decimal
        from django.core.exceptions import ValidationError as DjangoValidationError

        ZERO = Decimal("0.00")

        if self.debit_amount < ZERO or self.credit_amount < ZERO:
            raise DjangoValidationError("Debit and credit amounts must be >= 0.")

        both_zero = (self.debit_amount == ZERO and self.credit_amount == ZERO)
        both_nonzero = (self.debit_amount > ZERO and self.credit_amount > ZERO)

        if both_zero or both_nonzero:
            raise DjangoValidationError(
                "Exactly one of debit_amount or credit_amount must be > 0."
            )


# =============================================================================
# AccountingAuditLog
# =============================================================================

class AccountingAuditLog(TimestampedModel):
    """
    Immutable audit trail for all accounting actions.

    Every accounting state transition and configuration change creates one record.
    Records are never updated or deleted — append only.

    Uses a generic entity_type + entity_id pattern (same as FinancialAuditLog)
    to avoid tight coupling with individual model FKs.

    Multi-tenant scoping via restaurant FK.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="accounting_audit_logs",
        db_index=True,
    )
    action = models.CharField(
        max_length=60,
        choices=AUDIT_ACTION_CHOICES,
        db_index=True,
    )
    entity_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Model name, e.g. 'Account', 'JournalEntry', 'AccountingPeriod'.",
    )
    entity_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the affected entity.",
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="accounting_audit_logs",
        db_index=True,
        help_text="Restaurant scope for multi-tenant filtering.",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accounting_audit_logs",
        db_index=True,
    )
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context for the audit event.",
    )

    class Meta:
        verbose_name = "Accounting Audit Log"
        verbose_name_plural = "Accounting Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "action"]),
            models.Index(fields=["restaurant", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self):
        return f"{self.action} — {self.entity_type} {self.entity_id} by {self.actor}"

    def save(self, *args, **kwargs):
        """Enforce immutability: audit log rows cannot be updated."""
        if not self._state.adding:
            raise ValueError("AccountingAuditLog records are immutable.")
        super().save(*args, **kwargs)
