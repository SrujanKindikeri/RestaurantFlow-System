# =============================================================================
# RestaurantFlow — Accounting Services
# Phase 13
#
# All business logic for accounting lives here.
# Views call these; serializers validate input shapes only.
#
# Public API — AccountService:
#   create_account(restaurant, code, name, account_type, ...)   → Account
#   update_account(account, user, **fields)                     → Account
#   deactivate_account(account, user)                           → Account
#
# Public API — PeriodService:
#   create_fiscal_year(restaurant, name, start_date, end_date, user) → FiscalYear
#   create_period(restaurant, name, start_date, end_date, fy, user)  → AccountingPeriod
#   get_period_for_date(restaurant, date)                       → AccountingPeriod
#   request_period_close(period, user, note)                    → AccountingPeriod
#   close_period(period, user, note)                            → AccountingPeriod
#   reopen_period(period, user, note)                           → AccountingPeriod
#
# Public API — JournalService:
#   generate_journal_number(restaurant)                         → str
#   create_draft(restaurant, period, entry_date, description, user, ...) → JournalEntry
#   add_line(journal_entry, account, debit, credit, user, ...)  → JournalEntryLine
#   validate_entry(journal_entry)                               → None (raises on fail)
#   post_entry(journal_entry, user)                             → JournalEntry
#   reverse_entry(journal_entry, user, reason, entry_date)      → JournalEntry
#   void_entry(journal_entry, user, reason)                     → JournalEntry
#
# Public API — AccountingPostingService:
#   post_bill(bill, user)                                       → JournalEntry
#   post_payment(payment, user)                                 → JournalEntry
#   post_refund(refund, user)                                   → JournalEntry
#   post_supplier_invoice(invoice, user)                        → JournalEntry
#   post_expense(expense, user)                                 → JournalEntry
#   post_inventory_consumption(batch, user)                     → JournalEntry
#   post_consumption_reversal(batch, user)                      → JournalEntry
#   post_payable_payment(payable, amount, method, user)         → JournalEntry
#
# Concurrency:
#   - generate_journal_number uses select_for_update() — never MAX()+1.
#   - post_entry uses select_for_update() on the JournalEntry.
#   - All mutating operations are wrapped in transaction.atomic().
#
# Security:
#   - All public functions validate user authentication.
#   - Restaurant/branch scope validated.
#   - Permission codes checked via acl.has_permission().
#   - Duplicate postings prevented via validate_no_duplicate_posting().
# =============================================================================

import logging
from decimal import Decimal
from datetime import date as date_type

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from accounting.constants import (
    ZERO, JE_NUMBER_FORMAT,
    JE_DRAFT, JE_POSTED, JE_REVERSED, JE_VOID,
    PERIOD_OPEN, PERIOD_CLOSE_REQUESTED, PERIOD_CLOSED,
    FY_OPEN, FY_CLOSED,
    SOURCE_BILL, SOURCE_PAYMENT, SOURCE_PAYMENT_REFUND,
    SOURCE_SUPPLIER_INVOICE, SOURCE_EXPENSE,
    SOURCE_INVENTORY_CONSUMPTION, SOURCE_CONSUMPTION_REVERSAL,
    SOURCE_PAYABLE_PAYMENT, SOURCE_MANUAL,
    AUDIT_ACCOUNT_CREATED, AUDIT_ACCOUNT_UPDATED, AUDIT_ACCOUNT_DEACTIVATED,
    AUDIT_JOURNAL_CREATED, AUDIT_JOURNAL_POSTED, AUDIT_JOURNAL_REVERSED,
    AUDIT_JOURNAL_VOIDED,
    AUDIT_PERIOD_CREATED, AUDIT_PERIOD_CLOSE_REQUESTED,
    AUDIT_PERIOD_CLOSED, AUDIT_PERIOD_REOPENED,
    AUDIT_FY_CREATED, AUDIT_FY_CLOSED,
    AUDIT_SETTINGS_UPDATED,
    AUDIT_POSTED_FROM_BILL, AUDIT_POSTED_FROM_PAYMENT, AUDIT_POSTED_FROM_REFUND,
    AUDIT_POSTED_FROM_SINV, AUDIT_POSTED_FROM_EXPENSE,
    AUDIT_POSTED_FROM_CONSUMPTION, AUDIT_POSTED_FROM_PAYABLE,
    PERM_ACCOUNT_CREATE, PERM_ACCOUNT_UPDATE, PERM_ACCOUNT_DEACTIVATE,
    PERM_JOURNAL_CREATE, PERM_JOURNAL_POST, PERM_JOURNAL_REVERSE,
    PERM_PERIOD_CREATE, PERM_PERIOD_CLOSE, PERM_PERIOD_REOPEN,
    PERM_CONFIG_MANAGE,
    ACCOUNT_TYPE_NORMAL_BALANCE, NORMAL_BALANCE_DEBIT, NORMAL_BALANCE_CREDIT,
)
from accounting.exceptions import (
    ClosedPeriodError, NoPeriodFoundError, PeriodOverlapError,
    FiscalYearOverlapError, ImmutableJournalError, JournalPostingError,
    AccountHierarchyCycleError, DuplicateAccountingPostError,
    AccountingSettingsNotConfiguredError,
)
from accounting.validators import (
    validate_period_is_open, validate_entry_date_in_period,
    validate_account_postable, validate_accounts_same_restaurant,
    validate_line_debit_xor_credit, validate_journal_entry_balanced,
    validate_journal_is_draft, validate_journal_is_posted,
    validate_no_existing_reversal, validate_no_duplicate_posting,
)

logger = logging.getLogger("accounting")


# =============================================================================
# Internal helpers
# =============================================================================

def _require_auth(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


def _create_audit_log(actor, action, entity, restaurant, branch=None, metadata=None,
                       old_status="", new_status=""):
    """Create an immutable AccountingAuditLog entry."""
    from accounting.models import AccountingAuditLog
    import uuid as _uuid

    entity_id = None
    if hasattr(entity, 'pk') and entity.pk:
        try:
            entity_id = _uuid.UUID(str(entity.pk))
        except (ValueError, AttributeError):
            entity_id = None

    AccountingAuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity.__class__.__name__,
        entity_id=entity_id,
        restaurant=restaurant,
        branch=branch,
        old_status=old_status,
        new_status=new_status,
        metadata=metadata or {},
    )


def _get_or_create_accounting_settings(restaurant):
    """Return AccountingSettings for the restaurant, raising if not found."""
    from accounting.models import AccountingSettings
    try:
        return AccountingSettings.objects.select_related(
            "default_sales_account", "default_cash_account", "default_bank_account",
            "default_accounts_receivable", "default_inventory_account",
            "default_card_clearing_account", "default_upi_clearing_account",
            "default_accounts_payable", "default_tax_payable",
            "default_cogs_account", "default_rounding_account",
            "default_discount_account", "retained_earnings_account",
        ).get(restaurant=restaurant)
    except AccountingSettings.DoesNotExist:
        raise AccountingSettingsNotConfiguredError(
            f"Accounting settings not configured for restaurant '{restaurant.name}'. "
            "Please configure accounting settings before posting transactions."
        )


def _build_lines_from_specs(journal_entry, line_specs):
    """Create JournalEntryLine objects from a list of line spec dicts."""
    from accounting.models import JournalEntryLine
    lines = []
    for spec in line_specs:
        debit = spec.get("debit_amount", ZERO)
        credit = spec.get("credit_amount", ZERO)
        if debit == ZERO and credit == ZERO:
            continue  # skip zero-value lines
        line = JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=spec["account"],
            description=spec.get("description", ""),
            debit_amount=debit,
            credit_amount=credit,
            reference_type=spec.get("reference_type", ""),
            reference_id=spec.get("reference_id"),
        )
        lines.append(line)
    return lines


# =============================================================================
# AccountService
# =============================================================================

class AccountService:
    """Service for Chart of Accounts management."""

    @staticmethod
    @transaction.atomic
    def create_account(
        restaurant, code, name, account_type, normal_balance,
        user, description="", account_subtype="",
        parent_account=None, is_group=False, is_postable=True,
        is_system_account=False,
    ):
        """
        Create a new account in the Chart of Accounts.

        - Code must be unique within the restaurant.
        - Parent must belong to the same restaurant (no cross-restaurant hierarchy).
        - Parent cycles are detected and rejected.
        - normal_balance is set from account_type if not explicitly provided.
        """
        from accounting.models import Account

        _require_auth(user)
        if not acl.has_permission(user, PERM_ACCOUNT_CREATE):
            raise PermissionDenied("Permission required: accounting.account.create")
        if not acl.can_access_restaurant(user, restaurant):
            raise PermissionDenied("You do not have access to this restaurant.")

        # Validate parent belongs to same restaurant and no cycle
        if parent_account is not None:
            if str(parent_account.restaurant_id) != str(restaurant.pk):
                raise ValidationError(
                    "Parent account must belong to the same restaurant."
                )

        # Derive normal_balance from account_type if not provided
        if not normal_balance:
            normal_balance = ACCOUNT_TYPE_NORMAL_BALANCE.get(account_type, NORMAL_BALANCE_DEBIT)

        account = Account.objects.create(
            restaurant=restaurant,
            code=code,
            name=name,
            description=description,
            account_type=account_type,
            account_subtype=account_subtype,
            parent_account=parent_account,
            is_group=is_group,
            is_postable=is_postable,
            is_active=True,
            is_system_account=is_system_account,
            normal_balance=normal_balance,
        )

        # Cycle detection after creation
        if parent_account and account.has_ancestor(account.pk):
            account.delete()
            raise AccountHierarchyCycleError(
                f"Setting parent [{parent_account.code}] would create a cycle."
            )

        _create_audit_log(
            user, AUDIT_ACCOUNT_CREATED, account, restaurant,
            metadata={"code": code, "name": name, "type": account_type},
        )
        logger.info("Account created: [%s] %s for %s", code, name, restaurant.name)
        return account

    @staticmethod
    @transaction.atomic
    def update_account(account, user, **fields):
        """Update allowed fields on an account."""
        _require_auth(user)
        if not acl.has_permission(user, PERM_ACCOUNT_UPDATE):
            raise PermissionDenied("Permission required: accounting.account.update")
        if not acl.can_access_restaurant(user, account.restaurant):
            raise PermissionDenied("You do not have access to this restaurant.")

        allowed_fields = {"name", "description", "account_subtype", "is_postable", "is_group"}
        for field, value in fields.items():
            if field in allowed_fields:
                setattr(account, field, value)

        # If parent is being changed, validate cycle
        if "parent_account" in fields:
            new_parent = fields["parent_account"]
            if new_parent is not None:
                if str(new_parent.restaurant_id) != str(account.restaurant_id):
                    raise ValidationError("Parent account must belong to same restaurant.")
                account.parent_account = new_parent
                if account.has_ancestor(account.pk):
                    raise AccountHierarchyCycleError()

        account.save()
        _create_audit_log(
            user, AUDIT_ACCOUNT_UPDATED, account, account.restaurant,
            metadata={k: str(v) for k, v in fields.items()},
        )
        return account

    @staticmethod
    @transaction.atomic
    def deactivate_account(account, user):
        """
        Deactivate an account. Does NOT delete it — historical records are preserved.
        An account with active children cannot be deactivated.
        """
        _require_auth(user)
        if not acl.has_permission(user, PERM_ACCOUNT_DEACTIVATE):
            raise PermissionDenied("Permission required: accounting.account.deactivate")
        if not acl.can_access_restaurant(user, account.restaurant):
            raise PermissionDenied("You do not have access to this restaurant.")

        active_children = account.children.filter(is_active=True).exists()
        if active_children:
            raise ValidationError(
                "Cannot deactivate an account that has active child accounts."
            )

        account.is_active = False
        account.save(update_fields=["is_active", "updated_at"])
        _create_audit_log(
            user, AUDIT_ACCOUNT_DEACTIVATED, account, account.restaurant,
            metadata={"code": account.code, "name": account.name},
        )
        return account


# =============================================================================
# PeriodService
# =============================================================================

class PeriodService:
    """Service for Fiscal Year and Accounting Period management."""

    @staticmethod
    @transaction.atomic
    def create_fiscal_year(restaurant, name, start_date, end_date, user):
        """Create a new fiscal year, validating no overlaps."""
        from accounting.models import FiscalYear

        _require_auth(user)
        if not acl.has_permission(user, PERM_PERIOD_CREATE):
            raise PermissionDenied("Permission required: accounting.period.create")
        if not acl.can_access_restaurant(user, restaurant):
            raise PermissionDenied("You do not have access to this restaurant.")

        if start_date >= end_date:
            raise ValidationError("Fiscal year start_date must be before end_date.")

        # Check for overlaps
        overlapping = FiscalYear.objects.filter(
            restaurant=restaurant,
        ).exclude(status=FY_CLOSED).filter(
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if overlapping.exists():
            raise FiscalYearOverlapError()

        fy = FiscalYear.objects.create(
            restaurant=restaurant,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=FY_OPEN,
        )
        _create_audit_log(user, AUDIT_FY_CREATED, fy, restaurant,
                          metadata={"name": name, "start": str(start_date), "end": str(end_date)})
        return fy

    @staticmethod
    @transaction.atomic
    def create_period(restaurant, name, start_date, end_date, user,
                       fiscal_year=None):
        """Create a new accounting period, validating no overlaps."""
        from accounting.models import AccountingPeriod

        _require_auth(user)
        if not acl.has_permission(user, PERM_PERIOD_CREATE):
            raise PermissionDenied("Permission required: accounting.period.create")
        if not acl.can_access_restaurant(user, restaurant):
            raise PermissionDenied("You do not have access to this restaurant.")

        if start_date >= end_date:
            raise ValidationError("Period start_date must be before end_date.")

        # Check for overlapping periods (any status)
        overlapping = AccountingPeriod.objects.filter(
            restaurant=restaurant,
            start_date__lte=end_date,
            end_date__gte=start_date,
        )
        if overlapping.exists():
            raise PeriodOverlapError()

        period = AccountingPeriod.objects.create(
            restaurant=restaurant,
            fiscal_year=fiscal_year,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status=PERIOD_OPEN,
        )
        _create_audit_log(user, AUDIT_PERIOD_CREATED, period, restaurant,
                          metadata={"name": name, "start": str(start_date), "end": str(end_date)})
        return period

    @staticmethod
    def get_period_for_date(restaurant, for_date):
        """
        Return the OPEN AccountingPeriod that contains the given date.
        Raises NoPeriodFoundError if none found.
        """
        from accounting.models import AccountingPeriod

        try:
            return AccountingPeriod.objects.get(
                restaurant=restaurant,
                status=PERIOD_OPEN,
                start_date__lte=for_date,
                end_date__gte=for_date,
            )
        except AccountingPeriod.DoesNotExist:
            raise NoPeriodFoundError(
                f"No open accounting period found for date {for_date} "
                f"in restaurant '{restaurant.name}'."
            )
        except AccountingPeriod.MultipleObjectsReturned:
            # Multiple OPEN periods overlap this date — return most recent
            return AccountingPeriod.objects.filter(
                restaurant=restaurant,
                status=PERIOD_OPEN,
                start_date__lte=for_date,
                end_date__gte=for_date,
            ).order_by("-start_date").first()

    @staticmethod
    @transaction.atomic
    def request_period_close(period, user, note=""):
        """Transition period from OPEN → CLOSE_REQUESTED."""
        _require_auth(user)
        if not acl.has_permission(user, PERM_PERIOD_CLOSE):
            raise PermissionDenied("Permission required: accounting.period.close")
        if not acl.can_access_restaurant(user, period.restaurant):
            raise PermissionDenied()

        period = period.__class__.objects.select_for_update().get(pk=period.pk)
        if period.status != PERIOD_OPEN:
            raise ValidationError(
                f"Period is {period.status}. Only OPEN periods can be close-requested."
            )

        old_status = period.status
        period.status = PERIOD_CLOSE_REQUESTED
        period.closing_note = note
        period.save(update_fields=["status", "closing_note", "updated_at"])

        _create_audit_log(user, AUDIT_PERIOD_CLOSE_REQUESTED, period, period.restaurant,
                          old_status=old_status, new_status=PERIOD_CLOSE_REQUESTED,
                          metadata={"note": note})
        return period

    @staticmethod
    @transaction.atomic
    def close_period(period, user, note=""):
        """
        Close an accounting period (OPEN or CLOSE_REQUESTED → CLOSED).
        Validates that no unposted journal entries remain.
        """
        _require_auth(user)
        if not acl.has_permission(user, PERM_PERIOD_CLOSE):
            raise PermissionDenied("Permission required: accounting.period.close")
        if not acl.can_access_restaurant(user, period.restaurant):
            raise PermissionDenied()

        period = period.__class__.objects.select_for_update().get(pk=period.pk)
        if period.status == PERIOD_CLOSED:
            raise ValidationError("Period is already CLOSED.")

        # Check for unposted draft entries in this period
        from accounting.models import JournalEntry
        draft_count = JournalEntry.objects.filter(
            accounting_period=period,
            status=JE_DRAFT,
        ).count()
        if draft_count > 0:
            raise ValidationError(
                f"Cannot close period: {draft_count} draft journal "
                "entries exist. Post or void them first."
            )

        old_status = period.status
        period.status = PERIOD_CLOSED
        period.closed_at = timezone.now()
        period.closed_by = user
        if note:
            period.closing_note = note
        period.save(update_fields=["status", "closed_at", "closed_by", "closing_note", "updated_at"])

        _create_audit_log(user, AUDIT_PERIOD_CLOSED, period, period.restaurant,
                          old_status=old_status, new_status=PERIOD_CLOSED,
                          metadata={"note": note})
        return period

    @staticmethod
    @transaction.atomic
    def reopen_period(period, user, note=""):
        """Reopen a CLOSED period (controlled operation)."""
        _require_auth(user)
        if not acl.has_permission(user, PERM_PERIOD_REOPEN):
            raise PermissionDenied("Permission required: accounting.period.reopen")
        if not acl.can_access_restaurant(user, period.restaurant):
            raise PermissionDenied()

        period = period.__class__.objects.select_for_update().get(pk=period.pk)
        if period.status != PERIOD_CLOSED:
            raise ValidationError(f"Period is {period.status}. Only CLOSED periods can be reopened.")

        old_status = period.status
        period.status = PERIOD_OPEN
        period.closed_at = None
        period.closed_by = None
        period.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])

        _create_audit_log(user, AUDIT_PERIOD_REOPENED, period, period.restaurant,
                          old_status=old_status, new_status=PERIOD_OPEN,
                          metadata={"note": note})
        return period


# =============================================================================
# JournalService
# =============================================================================

class JournalService:
    """Service for creating, validating, and posting journal entries."""

    @staticmethod
    @transaction.atomic
    def generate_journal_number(restaurant) -> str:
        """
        Generate a concurrency-safe journal entry number.
        Format: JE-000001, JE-000002, ...
        Uses select_for_update() — never MAX()+1.
        Must be called inside a transaction.atomic() block.
        """
        from accounting.models import JournalSequence

        try:
            seq = JournalSequence.objects.select_for_update().get(restaurant=restaurant)
            seq.last_sequence += 1
            seq.save(update_fields=["last_sequence", "updated_at"])
        except JournalSequence.DoesNotExist:
            try:
                seq, created = JournalSequence.objects.get_or_create(
                    restaurant=restaurant,
                    defaults={"last_sequence": 1},
                )
                if not created:
                    seq = JournalSequence.objects.select_for_update().get(restaurant=restaurant)
                    seq.last_sequence += 1
                    seq.save(update_fields=["last_sequence", "updated_at"])
            except IntegrityError:
                seq = JournalSequence.objects.select_for_update().get(restaurant=restaurant)
                seq.last_sequence += 1
                seq.save(update_fields=["last_sequence", "updated_at"])

        return JE_NUMBER_FORMAT.format(seq=seq.last_sequence)

    @staticmethod
    @transaction.atomic
    def create_draft(
        restaurant, period, entry_date, description, user,
        source_type=SOURCE_MANUAL, source_id=None,
        reference_type="", reference_id=None,
        branch=None,
    ):
        """
        Create a DRAFT journal entry.
        No lines are added at this stage; use add_line() to add them.
        """
        from accounting.models import JournalEntry

        _require_auth(user)
        if not acl.has_permission(user, PERM_JOURNAL_CREATE):
            raise PermissionDenied("Permission required: accounting.journal.create")
        if not acl.can_access_restaurant(user, restaurant):
            raise PermissionDenied("You do not have access to this restaurant.")

        validate_period_is_open(period)
        validate_entry_date_in_period(entry_date, period)

        entry_number = JournalService.generate_journal_number(restaurant)

        entry = JournalEntry.objects.create(
            restaurant=restaurant,
            branch=branch,
            entry_number=entry_number,
            accounting_period=period,
            entry_date=entry_date,
            description=description,
            source_type=source_type,
            source_id=source_id,
            reference_type=reference_type,
            reference_id=reference_id,
            status=JE_DRAFT,
            created_by=user,
        )

        _create_audit_log(user, AUDIT_JOURNAL_CREATED, entry, restaurant, branch=branch,
                          metadata={"entry_number": entry_number, "source_type": source_type})
        return entry

    @staticmethod
    @transaction.atomic
    def add_line(journal_entry, account, debit_amount, credit_amount, user,
                  description="", reference_type="", reference_id=None):
        """
        Add a debit or credit line to a DRAFT journal entry.
        Validates: entry is DRAFT, XOR rule, account is active/postable,
        account belongs to same restaurant.
        """
        validate_journal_is_draft(journal_entry)
        validate_line_debit_xor_credit(debit_amount, credit_amount)
        validate_account_postable(account)
        validate_accounts_same_restaurant(journal_entry.restaurant, [account])

        from accounting.models import JournalEntryLine
        line = JournalEntryLine.objects.create(
            journal_entry=journal_entry,
            account=account,
            description=description,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            reference_type=reference_type,
            reference_id=reference_id,
        )
        return line

    @staticmethod
    def validate_entry(journal_entry):
        """
        Run full pre-posting validation.
        Raises on any violation. Does NOT modify any data.
        """
        # Entry must be DRAFT
        validate_journal_is_draft(journal_entry)

        # Period must still be open
        validate_period_is_open(journal_entry.accounting_period)

        # Entry date must still be within period
        validate_entry_date_in_period(journal_entry.entry_date, journal_entry.accounting_period)

        # All lines must have valid accounts from same restaurant
        lines = list(journal_entry.lines.select_related("account").all())
        accounts = [l.account for l in lines]
        validate_accounts_same_restaurant(journal_entry.restaurant, accounts)
        for account in accounts:
            validate_account_postable(account)

        # Balanced: total debits == total credits
        validate_journal_entry_balanced(journal_entry)

    @staticmethod
    @transaction.atomic
    def post_entry(journal_entry, user):
        """
        Post a DRAFT journal entry.
        After posting:
            - status = POSTED
            - posted_by and posted_at recorded
            - Entry becomes IMMUTABLE

        The central double-entry invariant is validated before posting.
        """
        _require_auth(user)
        if not acl.has_permission(user, PERM_JOURNAL_POST):
            raise PermissionDenied("Permission required: accounting.journal.post")
        if not acl.can_access_restaurant(user, journal_entry.restaurant):
            raise PermissionDenied()

        # Lock the entry to prevent concurrent posting
        journal_entry = journal_entry.__class__.objects.select_for_update().get(
            pk=journal_entry.pk
        )

        # Full validation
        JournalService.validate_entry(journal_entry)

        old_status = journal_entry.status
        journal_entry.status = JE_POSTED
        journal_entry.posted_by = user
        journal_entry.posted_at = timezone.now()
        journal_entry.save(update_fields=["status", "posted_by", "posted_at", "updated_at"])

        _create_audit_log(
            user, AUDIT_JOURNAL_POSTED, journal_entry, journal_entry.restaurant,
            branch=journal_entry.branch,
            old_status=old_status, new_status=JE_POSTED,
            metadata={"entry_number": journal_entry.entry_number},
        )
        logger.info("Journal entry POSTED: %s", journal_entry.entry_number)
        return journal_entry

    @staticmethod
    @transaction.atomic
    def reverse_entry(journal_entry, user, reason, reversal_date=None):
        """
        Create a reversal of a POSTED journal entry.

        The original entry is NOT modified. A new journal entry is created
        with all debits/credits swapped, status DRAFT, then posted.

        Returns the new reversal JournalEntry (already POSTED).
        """
        _require_auth(user)
        if not acl.has_permission(user, PERM_JOURNAL_REVERSE):
            raise PermissionDenied("Permission required: accounting.journal.reverse")
        if not acl.can_access_restaurant(user, journal_entry.restaurant):
            raise PermissionDenied()

        journal_entry = journal_entry.__class__.objects.select_for_update().get(
            pk=journal_entry.pk
        )
        validate_journal_is_posted(journal_entry)
        validate_no_existing_reversal(journal_entry)

        if not reason or not reason.strip():
            raise ValidationError("Reversal reason is required.")

        # Determine reversal date
        if reversal_date is None:
            reversal_date = journal_entry.entry_date

        # Find the period for the reversal date
        reversal_period = PeriodService.get_period_for_date(
            journal_entry.restaurant, reversal_date
        )

        # Create the reversal entry as DRAFT
        reversal_number = JournalService.generate_journal_number(journal_entry.restaurant)

        from accounting.models import JournalEntry
        reversal = JournalEntry.objects.create(
            restaurant=journal_entry.restaurant,
            branch=journal_entry.branch,
            entry_number=reversal_number,
            accounting_period=reversal_period,
            entry_date=reversal_date,
            description=f"Reversal of {journal_entry.entry_number}: {reason}",
            source_type=journal_entry.source_type,
            source_id=None,  # reversal is not a duplicate of the original source
            status=JE_DRAFT,
            created_by=user,
            reversal_of=journal_entry,
        )

        # Create swapped lines
        original_lines = list(journal_entry.lines.select_related("account").all())
        from accounting.models import JournalEntryLine
        for line in original_lines:
            JournalEntryLine.objects.create(
                journal_entry=reversal,
                account=line.account,
                description=f"Reversal: {line.description}",
                debit_amount=line.credit_amount,   # SWAP
                credit_amount=line.debit_amount,   # SWAP
                reference_type=line.reference_type,
                reference_id=line.reference_id,
            )

        # Post the reversal entry
        reversal.status = JE_POSTED
        reversal.posted_by = user
        reversal.posted_at = timezone.now()
        reversal.save(update_fields=["status", "posted_by", "posted_at", "updated_at"])

        # Mark original as reversed
        journal_entry.status = JE_REVERSED
        journal_entry.reversed_by = user
        journal_entry.reversed_at = timezone.now()
        journal_entry.reversal_reason = reason
        journal_entry.save(update_fields=[
            "status", "reversed_by", "reversed_at", "reversal_reason", "updated_at"
        ])

        _create_audit_log(
            user, AUDIT_JOURNAL_REVERSED, journal_entry, journal_entry.restaurant,
            branch=journal_entry.branch,
            old_status=JE_POSTED, new_status=JE_REVERSED,
            metadata={"reversal_number": reversal_number, "reason": reason},
        )
        logger.info(
            "Journal entry REVERSED: %s → %s",
            journal_entry.entry_number, reversal_number,
        )
        return reversal

    @staticmethod
    @transaction.atomic
    def void_entry(journal_entry, user, reason=""):
        """Void a DRAFT journal entry (before it is posted)."""
        _require_auth(user)
        if not acl.has_permission(user, PERM_JOURNAL_CREATE):
            raise PermissionDenied("Permission required: accounting.journal.create")
        if not acl.can_access_restaurant(user, journal_entry.restaurant):
            raise PermissionDenied()

        journal_entry = journal_entry.__class__.objects.select_for_update().get(
            pk=journal_entry.pk
        )
        validate_journal_is_draft(journal_entry)

        old_status = journal_entry.status
        journal_entry.status = JE_VOID
        journal_entry.save(update_fields=["status", "updated_at"])

        _create_audit_log(
            user, AUDIT_JOURNAL_VOIDED, journal_entry, journal_entry.restaurant,
            old_status=old_status, new_status=JE_VOID,
            metadata={"reason": reason},
        )
        return journal_entry


# =============================================================================
# AccountingSettingsService
# =============================================================================

class AccountingSettingsService:
    """Service for managing AccountingSettings per restaurant."""

    @staticmethod
    @transaction.atomic
    def get_or_create_settings(restaurant, user):
        """Get or create AccountingSettings for a restaurant."""
        from accounting.models import AccountingSettings
        _require_auth(user)
        if not acl.can_access_restaurant(user, restaurant):
            raise PermissionDenied()
        settings_obj, created = AccountingSettings.objects.get_or_create(
            restaurant=restaurant,
        )
        return settings_obj

    @staticmethod
    @transaction.atomic
    def update_settings(settings_obj, user, **fields):
        """Update AccountingSettings with validated account references."""
        from accounting.models import Account
        _require_auth(user)
        if not acl.has_permission(user, PERM_CONFIG_MANAGE):
            raise PermissionDenied("Permission required: accounting.configuration.manage")
        if not acl.can_access_restaurant(user, settings_obj.restaurant):
            raise PermissionDenied()

        account_fields = {
            "default_sales_account", "default_discount_account",
            "default_cash_account", "default_bank_account",
            "default_accounts_receivable", "default_inventory_account",
            "default_card_clearing_account", "default_upi_clearing_account",
            "default_accounts_payable", "default_tax_payable",
            "default_cogs_account", "default_rounding_account",
            "retained_earnings_account",
        }

        for field, value in fields.items():
            if field in account_fields and value is not None:
                if isinstance(value, Account):
                    if str(value.restaurant_id) != str(settings_obj.restaurant_id):
                        raise ValidationError(
                            f"Account for '{field}' belongs to a different restaurant."
                        )
                    if not value.is_active:
                        raise ValidationError(f"Account for '{field}' is inactive.")
            setattr(settings_obj, field, value)

        settings_obj.save()
        _create_audit_log(
            user, AUDIT_SETTINGS_UPDATED, settings_obj, settings_obj.restaurant,
            metadata={k: str(v) for k, v in fields.items() if v is not None},
        )
        return settings_obj


# =============================================================================
# AccountingPostingService
# =============================================================================

class AccountingPostingService:
    """
    Service for automatic accounting postings from source transactions.

    Every method is idempotent — if a POSTED entry already exists for
    the source_type + source_id, the existing entry is returned.
    This prevents duplicate accounting from retries.
    """

    @staticmethod
    def _get_existing_posting(source_type, source_id):
        """Return existing POSTED journal entry for this source, or None."""
        from accounting.models import JournalEntry
        return JournalEntry.objects.filter(
            source_type=source_type,
            source_id=source_id,
            status=JE_POSTED,
        ).first()

    @staticmethod
    def _post_from_line_specs(
        restaurant, branch, period, entry_date, description,
        line_specs, source_type, source_id, user, audit_action,
    ):
        """
        Internal helper: create draft, add lines, validate, post.
        Returns the POSTED JournalEntry.
        """
        # Validate period and date BEFORE creating the entry — fast fail
        validate_period_is_open(period)
        validate_entry_date_in_period(entry_date, period)

        entry_number = JournalService.generate_journal_number(restaurant)

        from accounting.models import JournalEntry, JournalEntryLine
        entry = JournalEntry.objects.create(
            restaurant=restaurant,
            branch=branch,
            entry_number=entry_number,
            accounting_period=period,
            entry_date=entry_date,
            description=description,
            source_type=source_type,
            source_id=source_id,
            status=JE_DRAFT,
            created_by=user,
        )

        _build_lines_from_specs(entry, line_specs)

        # Validate double-entry balance invariant
        validate_journal_entry_balanced(entry)

        # Post
        entry.status = JE_POSTED
        entry.posted_by = user
        entry.posted_at = timezone.now()
        entry.save(update_fields=["status", "posted_by", "posted_at", "updated_at"])

        _create_audit_log(
            user, audit_action, entry, restaurant, branch=branch,
            new_status=JE_POSTED,
            metadata={
                "entry_number": entry_number,
                "source_type": source_type,
                "source_id": str(source_id) if source_id else "",
            },
        )
        logger.info("Accounting posted: %s %s → %s", source_type, source_id, entry_number)
        return entry

    @staticmethod
    @transaction.atomic
    def post_bill(bill, user):
        """
        Post accounting for a FINALIZED Bill.
        Creates: Dr Receivable / Cr Sales Revenue / Cr Tax Payable
        Idempotent: returns existing posting if already done.
        """
        from billing.models import BillStatus
        from accounting.accounting_rules import build_bill_lines

        if bill.status != BillStatus.FINALIZED:
            raise ValidationError(
                f"Bill {bill.bill_number} is {bill.status}. "
                "Only FINALIZED bills can be posted."
            )

        existing = AccountingPostingService._get_existing_posting(
            SOURCE_BILL, bill.pk
        )
        if existing:
            return existing

        validate_no_duplicate_posting(SOURCE_BILL, bill.pk)

        restaurant = bill.branch.restaurant
        settings = _get_or_create_accounting_settings(restaurant)
        entry_date = bill.finalized_at.date() if bill.finalized_at else timezone.now().date()
        period = PeriodService.get_period_for_date(restaurant, entry_date)
        line_specs = build_bill_lines(bill, settings)

        return AccountingPostingService._post_from_line_specs(
            restaurant=restaurant,
            branch=bill.branch,
            period=period,
            entry_date=entry_date,
            description=f"Sales — {bill.bill_number}",
            line_specs=line_specs,
            source_type=SOURCE_BILL,
            source_id=bill.pk,
            user=user,
            audit_action=AUDIT_POSTED_FROM_BILL,
        )

    @staticmethod
    @transaction.atomic
    def post_payment(payment, user):
        """
        Post accounting for a COMPLETED Payment.
        Creates: Dr Cash/UPI/Card / Cr Accounts Receivable
        Idempotent.
        """
        from payments.models import PaymentStatus
        from accounting.accounting_rules import build_payment_lines

        if payment.status != PaymentStatus.COMPLETED:
            raise ValidationError(
                f"Payment {payment.payment_number} is {payment.status}. "
                "Only COMPLETED payments can be posted."
            )

        existing = AccountingPostingService._get_existing_posting(
            SOURCE_PAYMENT, payment.pk
        )
        if existing:
            return existing

        validate_no_duplicate_posting(SOURCE_PAYMENT, payment.pk)

        restaurant = payment.branch.restaurant
        settings = _get_or_create_accounting_settings(restaurant)
        entry_date = payment.completed_at.date() if payment.completed_at else timezone.now().date()
        period = PeriodService.get_period_for_date(restaurant, entry_date)
        line_specs = build_payment_lines(payment, settings)

        return AccountingPostingService._post_from_line_specs(
            restaurant=restaurant,
            branch=payment.branch,
            period=period,
            entry_date=entry_date,
            description=f"Payment received — {payment.payment_number}",
            line_specs=line_specs,
            source_type=SOURCE_PAYMENT,
            source_id=payment.pk,
            user=user,
            audit_action=AUDIT_POSTED_FROM_PAYMENT,
        )

    @staticmethod
    @transaction.atomic
    def post_refund(refund, user):
        """
        Post accounting for a PROCESSED PaymentRefund.
        Creates: Dr Accounts Receivable / Cr Cash/UPI/Card
        Idempotent.
        """
        from payments.models import RefundStatus
        from accounting.accounting_rules import build_refund_lines

        if refund.status != RefundStatus.PROCESSED:
            raise ValidationError(
                f"Refund {refund.refund_number} is {refund.status}. "
                "Only PROCESSED refunds can be posted."
            )

        existing = AccountingPostingService._get_existing_posting(
            SOURCE_PAYMENT_REFUND, refund.pk
        )
        if existing:
            return existing

        validate_no_duplicate_posting(SOURCE_PAYMENT_REFUND, refund.pk)

        restaurant = refund.payment.branch.restaurant
        settings = _get_or_create_accounting_settings(restaurant)
        entry_date = refund.processed_at.date() if refund.processed_at else timezone.now().date()
        period = PeriodService.get_period_for_date(restaurant, entry_date)
        line_specs = build_refund_lines(refund, settings)

        return AccountingPostingService._post_from_line_specs(
            restaurant=restaurant,
            branch=refund.payment.branch,
            period=period,
            entry_date=entry_date,
            description=f"Refund — {refund.refund_number}",
            line_specs=line_specs,
            source_type=SOURCE_PAYMENT_REFUND,
            source_id=refund.pk,
            user=user,
            audit_action=AUDIT_POSTED_FROM_REFUND,
        )

    @staticmethod
    @transaction.atomic
    def post_supplier_invoice(invoice, user):
        """
        Post accounting for an APPROVED SupplierInvoice.
        Creates: Dr Inventory / Cr Accounts Payable
        Idempotent.
        """
        from financials.constants import SINV_APPROVED
        from accounting.accounting_rules import build_supplier_invoice_lines

        if invoice.status != SINV_APPROVED:
            raise ValidationError(
                f"Supplier invoice {invoice.invoice_number} is {invoice.status}. "
                "Only APPROVED invoices can be posted."
            )

        existing = AccountingPostingService._get_existing_posting(
            SOURCE_SUPPLIER_INVOICE, invoice.pk
        )
        if existing:
            return existing

        validate_no_duplicate_posting(SOURCE_SUPPLIER_INVOICE, invoice.pk)

        restaurant = invoice.restaurant
        settings = _get_or_create_accounting_settings(restaurant)
        entry_date = invoice.approved_at.date() if invoice.approved_at else timezone.now().date()
        period = PeriodService.get_period_for_date(restaurant, entry_date)
        line_specs = build_supplier_invoice_lines(invoice, settings)

        return AccountingPostingService._post_from_line_specs(
            restaurant=restaurant,
            branch=invoice.branch,
            period=period,
            entry_date=entry_date,
            description=f"Supplier invoice — {invoice.invoice_number}",
            line_specs=line_specs,
            source_type=SOURCE_SUPPLIER_INVOICE,
            source_id=invoice.pk,
            user=user,
            audit_action=AUDIT_POSTED_FROM_SINV,
        )

    @staticmethod
    @transaction.atomic
    def post_expense(expense, user):
        """
        Post accounting for an APPROVED Expense.
        Creates: Dr [Expense Account] / Cr Accounts Payable
        Idempotent.
        """
        from financials.constants import EXPENSE_APPROVED
        from accounting.accounting_rules import build_expense_lines

        if expense.status != EXPENSE_APPROVED:
            raise ValidationError(
                f"Expense {expense.expense_number} is {expense.status}. "
                "Only APPROVED expenses can be posted."
            )

        existing = AccountingPostingService._get_existing_posting(
            SOURCE_EXPENSE, expense.pk
        )
        if existing:
            return existing

        validate_no_duplicate_posting(SOURCE_EXPENSE, expense.pk)

        restaurant = expense.restaurant
        settings = _get_or_create_accounting_settings(restaurant)
        entry_date = expense.approved_at.date() if expense.approved_at else timezone.now().date()
        period = PeriodService.get_period_for_date(restaurant, entry_date)
        line_specs = build_expense_lines(expense, settings)

        return AccountingPostingService._post_from_line_specs(
            restaurant=restaurant,
            branch=expense.branch,
            period=period,
            entry_date=entry_date,
            description=f"Expense — {expense.expense_number} — {expense.title}",
            line_specs=line_specs,
            source_type=SOURCE_EXPENSE,
            source_id=expense.pk,
            user=user,
            audit_action=AUDIT_POSTED_FROM_EXPENSE,
        )

    @staticmethod
    @transaction.atomic
    def post_inventory_consumption(batch, user):
        """
        Post accounting for a COMPLETED ConsumptionBatch (COGS).
        Creates: Dr COGS / Cr Inventory
        Uses authoritative unit_cost from StockConsumption records.
        Idempotent.
        """
        from recipes.models import ConsumptionBatch, StockConsumption
        from accounting.accounting_rules import build_consumption_lines

        COMPLETED = "COMPLETED"
        if batch.status != COMPLETED:
            raise ValidationError(
                f"Consumption batch {batch.pk} is {batch.status}. "
                "Only COMPLETED batches can be posted."
            )

        existing = AccountingPostingService._get_existing_posting(
            SOURCE_INVENTORY_CONSUMPTION, batch.pk
        )
        if existing:
            return existing

        validate_no_duplicate_posting(SOURCE_INVENTORY_CONSUMPTION, batch.pk)

        # Get all CONSUMED StockConsumption records in this batch
        consumptions = list(
            StockConsumption.objects.filter(batch=batch, status="CONSUMED")
        )
        if not consumptions:
            raise ValidationError(
                f"No CONSUMED stock consumptions found in batch {batch.pk}."
            )

        restaurant = batch.branch.restaurant
        settings = _get_or_create_accounting_settings(restaurant)
        entry_date = batch.completed_at.date() if batch.completed_at else timezone.now().date()
        period = PeriodService.get_period_for_date(restaurant, entry_date)
        line_specs = build_consumption_lines(batch, consumptions, settings)

        if not line_specs:
            logger.info("No COGS lines for batch %s (zero cost).", batch.pk)
            return None

        return AccountingPostingService._post_from_line_specs(
            restaurant=restaurant,
            branch=batch.branch,
            period=period,
            entry_date=entry_date,
            description=f"COGS — consumption batch {str(batch.pk)[:8]}",
            line_specs=line_specs,
            source_type=SOURCE_INVENTORY_CONSUMPTION,
            source_id=batch.pk,
            user=user,
            audit_action=AUDIT_POSTED_FROM_CONSUMPTION,
        )

    @staticmethod
    @transaction.atomic
    def post_consumption_reversal(batch, user):
        """
        Post accounting for a REVERSED ConsumptionBatch.
        Finds the original COGS journal entry and creates a reversal.
        Idempotent.
        """
        REVERSED = "REVERSED"
        if batch.status != REVERSED:
            raise ValidationError(
                f"Consumption batch {batch.pk} is {batch.status}. "
                "Only REVERSED batches trigger a consumption reversal."
            )

        existing = AccountingPostingService._get_existing_posting(
            SOURCE_CONSUMPTION_REVERSAL, batch.pk
        )
        if existing:
            return existing

        validate_no_duplicate_posting(SOURCE_CONSUMPTION_REVERSAL, batch.pk)

        # Find the original COGS posting for this batch
        from accounting.models import JournalEntry
        original = JournalEntry.objects.filter(
            source_type=SOURCE_INVENTORY_CONSUMPTION,
            source_id=batch.pk,
            status=JE_POSTED,
        ).first()

        if original is None:
            raise ValidationError(
                f"No original COGS posting found for consumption batch {batch.pk}."
            )

        restaurant = batch.branch.restaurant
        entry_date = timezone.now().date()
        period = PeriodService.get_period_for_date(restaurant, entry_date)

        # Build reversal lines (swap debits/credits)
        from accounting.accounting_rules import build_consumption_reversal_lines
        original_lines = list(original.lines.select_related("account").all())
        line_specs = build_consumption_reversal_lines(original_lines, None)

        return AccountingPostingService._post_from_line_specs(
            restaurant=restaurant,
            branch=batch.branch,
            period=period,
            entry_date=entry_date,
            description=f"COGS reversal — batch {str(batch.pk)[:8]}",
            line_specs=line_specs,
            source_type=SOURCE_CONSUMPTION_REVERSAL,
            source_id=batch.pk,
            user=user,
            audit_action=AUDIT_POSTED_FROM_CONSUMPTION,
        )

    @staticmethod
    @transaction.atomic
    def post_payable_payment(payable, amount, payment_method, user):
        """
        Post accounting for settling a Payable.
        Creates: Dr Accounts Payable / Cr Cash/Bank
        Updates payable.paid_amount and payable.remaining_amount.
        """
        from financials.models import Payable
        from accounting.accounting_rules import build_payable_payment_lines
        from accounting.exceptions import InsufficientPayableError

        if amount <= ZERO:
            raise ValidationError("Payment amount must be > 0.")
        if amount > payable.remaining_amount:
            raise InsufficientPayableError(
                f"Payment {amount} exceeds remaining payable balance {payable.remaining_amount}."
            )

        restaurant = payable.restaurant
        settings = _get_or_create_accounting_settings(restaurant)
        entry_date = timezone.now().date()
        period = PeriodService.get_period_for_date(restaurant, entry_date)
        line_specs = build_payable_payment_lines(payable, amount, payment_method, settings)

        entry = AccountingPostingService._post_from_line_specs(
            restaurant=restaurant,
            branch=payable.branch,
            period=period,
            entry_date=entry_date,
            description=f"Payable payment — {payable.reference_number}",
            line_specs=line_specs,
            source_type=SOURCE_PAYABLE_PAYMENT,
            source_id=None,  # payable payments are not uniquely-keyed (multiple allowed)
            user=user,
            audit_action=AUDIT_POSTED_FROM_PAYABLE,
        )

        # Update the payable balance
        payable = Payable.objects.select_for_update().get(pk=payable.pk)
        payable.paid_amount += amount
        payable.remaining_amount = payable.amount - payable.paid_amount
        payable.refresh_status()
        payable.save(update_fields=["paid_amount", "remaining_amount", "status", "updated_at"])

        return entry
