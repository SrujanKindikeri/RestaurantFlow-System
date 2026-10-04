# =============================================================================
# RestaurantFlow — Accounting Access Control
# Phase 13
#
# All IDOR-safe queryset scoping for accounting models.
# Views must use these functions — never trust IDs from the frontend directly.
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("accounting")


# ---------------------------------------------------------------------------
# Fiscal Years
# ---------------------------------------------------------------------------

def get_accessible_fiscal_years(user):
    """Return FiscalYears scoped to the user's accessible restaurants."""
    from accounting.models import FiscalYear
    if not user or not user.is_authenticated or not user.is_active:
        return FiscalYear.objects.none()
    if user.is_superuser or user.is_staff:
        return FiscalYear.objects.all()
    restaurants = acl.get_accessible_restaurants(user)
    return FiscalYear.objects.filter(restaurant__in=restaurants)


def can_access_fiscal_year(user, fiscal_year) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_restaurant(user, fiscal_year.restaurant)


# ---------------------------------------------------------------------------
# Accounting Periods
# ---------------------------------------------------------------------------

def get_accessible_periods(user):
    from accounting.models import AccountingPeriod
    if not user or not user.is_authenticated or not user.is_active:
        return AccountingPeriod.objects.none()
    if user.is_superuser or user.is_staff:
        return AccountingPeriod.objects.all()
    restaurants = acl.get_accessible_restaurants(user)
    return AccountingPeriod.objects.filter(restaurant__in=restaurants)


def can_access_period(user, period) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_restaurant(user, period.restaurant)


# ---------------------------------------------------------------------------
# Accounts (Chart of Accounts)
# ---------------------------------------------------------------------------

def get_accessible_accounts(user):
    from accounting.models import Account
    if not user or not user.is_authenticated or not user.is_active:
        return Account.objects.none()
    if user.is_superuser or user.is_staff:
        return Account.objects.all()
    restaurants = acl.get_accessible_restaurants(user)
    return Account.objects.filter(restaurant__in=restaurants)


def can_access_account(user, account) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_restaurant(user, account.restaurant)


# ---------------------------------------------------------------------------
# Accounting Settings
# ---------------------------------------------------------------------------

def get_accessible_settings(user):
    from accounting.models import AccountingSettings
    if not user or not user.is_authenticated or not user.is_active:
        return AccountingSettings.objects.none()
    if user.is_superuser or user.is_staff:
        return AccountingSettings.objects.all()
    restaurants = acl.get_accessible_restaurants(user)
    return AccountingSettings.objects.filter(restaurant__in=restaurants)


# ---------------------------------------------------------------------------
# Journal Entries
# ---------------------------------------------------------------------------

def get_accessible_journal_entries(user):
    from accounting.models import JournalEntry
    if not user or not user.is_authenticated or not user.is_active:
        return JournalEntry.objects.none()
    if user.is_superuser or user.is_staff:
        return JournalEntry.objects.all()
    restaurants = acl.get_accessible_restaurants(user)
    return JournalEntry.objects.filter(restaurant__in=restaurants)


def can_access_journal_entry(user, entry) -> bool:
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_restaurant(user, entry.restaurant)


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

def get_accessible_audit_logs(user):
    from accounting.models import AccountingAuditLog
    if not user or not user.is_authenticated or not user.is_active:
        return AccountingAuditLog.objects.none()
    if user.is_superuser or user.is_staff:
        return AccountingAuditLog.objects.all()
    restaurants = acl.get_accessible_restaurants(user)
    return AccountingAuditLog.objects.filter(restaurant__in=restaurants)
