# =============================================================================
# RestaurantFlow — Accounting Exceptions
# Phase 13
# =============================================================================

from rest_framework.exceptions import APIException, ValidationError
from rest_framework import status


class AccountingError(APIException):
    """Base exception for all accounting domain errors."""
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "An accounting error occurred."
    default_code = "accounting_error"


class JournalImbalanceError(AccountingError):
    """Raised when total debits ≠ total credits in a journal entry."""
    default_detail = "Journal entry is not balanced: total debits must equal total credits."
    default_code = "journal_imbalance"


class JournalPostingError(AccountingError):
    """Raised when a journal entry cannot be posted."""
    default_detail = "Journal entry cannot be posted in its current state."
    default_code = "journal_posting_error"


class DuplicateAccountingPostError(AccountingError):
    """Raised when attempting to post accounting for an already-posted source."""
    default_detail = "Accounting has already been posted for this source transaction."
    default_code = "duplicate_accounting_post"


class ClosedPeriodError(AccountingError):
    """Raised when attempting to post to a closed accounting period."""
    default_detail = "Cannot post to a closed accounting period."
    default_code = "closed_period"


class NoPeriodFoundError(AccountingError):
    """Raised when no open accounting period is found for the given date."""
    default_detail = "No open accounting period found for the transaction date."
    default_code = "no_period_found"


class AccountInactiveError(AccountingError):
    """Raised when a non-postable or inactive account is used in a journal line."""
    default_detail = "Account is inactive or not postable."
    default_code = "account_inactive"


class CrossRestaurantAccountError(AccountingError):
    """Raised when accounts from different restaurants are used together."""
    default_detail = "All journal lines must reference accounts from the same restaurant."
    default_code = "cross_restaurant_account"


class AccountingSettingsNotConfiguredError(AccountingError):
    """Raised when required AccountingSettings are missing."""
    default_detail = "Accounting settings are not fully configured for this restaurant."
    default_code = "accounting_settings_not_configured"


class PeriodOverlapError(AccountingError):
    """Raised when a new period overlaps with an existing period."""
    default_detail = "Accounting period dates overlap with an existing period."
    default_code = "period_overlap"


class FiscalYearOverlapError(AccountingError):
    """Raised when a new fiscal year overlaps with an existing fiscal year."""
    default_detail = "Fiscal year dates overlap with an existing fiscal year."
    default_code = "fiscal_year_overlap"


class ImmutableJournalError(AccountingError):
    """Raised when attempting to mutate a posted/reversed/void journal entry."""
    default_detail = "Posted journal entries are immutable. Use reversal to correct."
    default_code = "immutable_journal"


class AccountHierarchyCycleError(AccountingError):
    """Raised when a parent-child cycle is detected in chart of accounts."""
    default_detail = "Account hierarchy would create a cycle."
    default_code = "account_hierarchy_cycle"


class NonPostableAccountError(AccountingError):
    """Raised when a group/header account is used for direct posting."""
    default_detail = "Cannot post to a group account (is_postable=False)."
    default_code = "non_postable_account"


class InsufficientPayableError(AccountingError):
    """Raised when payable payment amount exceeds remaining balance."""
    default_detail = "Payment amount exceeds the remaining payable balance."
    default_code = "insufficient_payable"
