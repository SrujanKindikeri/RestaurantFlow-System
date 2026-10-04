# =============================================================================
# RestaurantFlow — Accounting DRF Permissions
# Phase 13
# =============================================================================

from rest_framework.permissions import BasePermission
from accounts import access as acl
from accounting.constants import (
    PERM_ACCOUNT_VIEW, PERM_ACCOUNT_CREATE, PERM_ACCOUNT_UPDATE, PERM_ACCOUNT_DEACTIVATE,
    PERM_JOURNAL_VIEW, PERM_JOURNAL_CREATE, PERM_JOURNAL_POST, PERM_JOURNAL_REVERSE,
    PERM_PERIOD_VIEW, PERM_PERIOD_CREATE, PERM_PERIOD_CLOSE, PERM_PERIOD_REOPEN,
    PERM_LEDGER_VIEW, PERM_TRIAL_BALANCE_VIEW, PERM_PROFIT_LOSS_VIEW,
    PERM_BALANCE_SHEET_VIEW, PERM_CASH_FLOW_VIEW,
    PERM_CONFIG_VIEW, PERM_CONFIG_MANAGE,
)


class CanViewAccount(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_ACCOUNT_VIEW)


class CanCreateAccount(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_ACCOUNT_CREATE)


class CanUpdateAccount(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_ACCOUNT_UPDATE)


class CanDeactivateAccount(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_ACCOUNT_DEACTIVATE)


class CanViewJournal(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_JOURNAL_VIEW)


class CanCreateJournal(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_JOURNAL_CREATE)


class CanPostJournal(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_JOURNAL_POST)


class CanReverseJournal(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_JOURNAL_REVERSE)


class CanViewPeriod(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_PERIOD_VIEW)


class CanCreatePeriod(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_PERIOD_CREATE)


class CanClosePeriod(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_PERIOD_CLOSE)


class CanViewLedger(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_LEDGER_VIEW)


class CanViewTrialBalance(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_TRIAL_BALANCE_VIEW)


class CanViewProfitLoss(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_PROFIT_LOSS_VIEW)


class CanViewBalanceSheet(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_BALANCE_SHEET_VIEW)


class CanViewCashFlow(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_CASH_FLOW_VIEW)


class CanViewConfig(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_CONFIG_VIEW)


class CanManageConfig(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_CONFIG_MANAGE)
