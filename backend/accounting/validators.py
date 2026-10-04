# =============================================================================
# RestaurantFlow — Accounting Validators
# Phase 13
# =============================================================================

from decimal import Decimal
from django.utils import timezone

from accounting.constants import (
    ZERO, PERIOD_OPEN, JE_DRAFT, JE_POSTED,
    ACCOUNT_TYPE_ASSET, ACCOUNT_TYPE_LIABILITY,
    ACCOUNT_TYPE_EQUITY, ACCOUNT_TYPE_REVENUE, ACCOUNT_TYPE_EXPENSE,
)
from accounting.exceptions import (
    JournalImbalanceError, ClosedPeriodError, AccountInactiveError,
    CrossRestaurantAccountError, NonPostableAccountError,
    JournalPostingError, ImmutableJournalError,
)


def validate_period_is_open(period):
    """Raise ClosedPeriodError if period is not OPEN."""
    if period.status != PERIOD_OPEN:
        raise ClosedPeriodError(
            f"Accounting period '{period.name}' is {period.status}. "
            "Cannot post to a closed period."
        )


def validate_entry_date_in_period(entry_date, period):
    """Raise ValidationError if entry_date does not fall within the period."""
    from rest_framework.exceptions import ValidationError
    if not period.contains_date(entry_date):
        raise ValidationError(
            f"Entry date {entry_date} does not fall within period "
            f"'{period.name}' ({period.start_date} – {period.end_date})."
        )


def validate_account_postable(account):
    """Raise errors if account cannot receive journal line entries."""
    if not account.is_active:
        raise AccountInactiveError(
            f"Account [{account.code}] {account.name} is inactive."
        )
    if not account.is_postable:
        raise NonPostableAccountError(
            f"Account [{account.code}] {account.name} is a group account (not postable)."
        )


def validate_accounts_same_restaurant(restaurant, accounts):
    """Raise CrossRestaurantAccountError if any account belongs to a different restaurant."""
    for account in accounts:
        if str(account.restaurant_id) != str(restaurant.pk):
            raise CrossRestaurantAccountError(
                f"Account [{account.code}] belongs to a different restaurant."
            )


def validate_line_debit_xor_credit(debit_amount, credit_amount):
    """Raise ValidationError if both or neither of debit/credit are positive."""
    from rest_framework.exceptions import ValidationError
    if debit_amount < ZERO or credit_amount < ZERO:
        raise ValidationError("Debit and credit amounts must be >= 0.")
    both_zero = (debit_amount == ZERO and credit_amount == ZERO)
    both_nonzero = (debit_amount > ZERO and credit_amount > ZERO)
    if both_zero or both_nonzero:
        raise ValidationError(
            "Exactly one of debit_amount or credit_amount must be > 0 per line."
        )


def validate_journal_entry_balanced(journal_entry):
    """
    Validate that total debits == total credits for a journal entry.
    Raises JournalImbalanceError if not balanced.
    """
    lines = list(journal_entry.lines.all())
    if len(lines) < 2:
        raise JournalImbalanceError(
            f"Journal entry {journal_entry.entry_number} must have at least 2 lines."
        )
    total_debit = sum((l.debit_amount for l in lines), Decimal("0.00"))
    total_credit = sum((l.credit_amount for l in lines), Decimal("0.00"))
    if total_debit != total_credit:
        raise JournalImbalanceError(
            f"Journal entry {journal_entry.entry_number} is not balanced: "
            f"debits={total_debit}, credits={total_credit}."
        )


def validate_journal_is_draft(journal_entry):
    """Raise ImmutableJournalError if the entry is not in DRAFT status."""
    if journal_entry.status != JE_DRAFT:
        raise ImmutableJournalError(
            f"Journal entry {journal_entry.entry_number} is {journal_entry.status} "
            "and cannot be modified. Use reversal to correct posted entries."
        )


def validate_journal_is_posted(journal_entry):
    """Raise JournalPostingError if the entry is not POSTED (for reversal)."""
    if journal_entry.status != JE_POSTED:
        raise JournalPostingError(
            f"Journal entry {journal_entry.entry_number} is {journal_entry.status}. "
            "Only POSTED entries can be reversed."
        )


def validate_no_existing_reversal(journal_entry):
    """Raise JournalPostingError if the entry already has a reversal."""
    if hasattr(journal_entry, 'reversal_entry') and journal_entry.reversal_entry is not None:
        raise JournalPostingError(
            f"Journal entry {journal_entry.entry_number} already has a reversal entry."
        )


def validate_account_type_for_role(account, expected_types, role_description):
    """Raise ValidationError if account type is not in expected_types."""
    from rest_framework.exceptions import ValidationError
    if account.account_type not in expected_types:
        raise ValidationError(
            f"Account [{account.code}] {account.name} has type {account.account_type}, "
            f"but {role_description} requires one of: {expected_types}."
        )


def validate_no_duplicate_posting(source_type, source_id):
    """
    Raise DuplicateAccountingPostError if a POSTED journal entry already
    exists for this source_type + source_id combination.
    """
    from accounting.models import JournalEntry
    from accounting.constants import JE_POSTED
    from accounting.exceptions import DuplicateAccountingPostError

    if source_id is None:
        return  # Manual entries don't need uniqueness check

    exists = JournalEntry.objects.filter(
        source_type=source_type,
        source_id=source_id,
        status=JE_POSTED,
    ).exists()
    if exists:
        raise DuplicateAccountingPostError(
            f"A posted journal entry already exists for {source_type} {source_id}."
        )
