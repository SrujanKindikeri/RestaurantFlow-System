# =============================================================================
# RestaurantFlow — Financials Access Control
# Phase 12
#
# Single source of truth for financial authorization decisions.
# Views and serializers delegate here — never duplicate access logic.
#
# Public API:
#   get_accessible_expense_categories(user)  → QuerySet[ExpenseCategory]
#   get_accessible_expenses(user)            → QuerySet[Expense]
#   get_accessible_approvals(user)           → QuerySet[ExpenseApproval]
#   get_accessible_corrections(user)         → QuerySet[ExpenseCorrectionRequest]
#   get_accessible_attachments(user)         → QuerySet[ExpenseAttachment]
#   get_accessible_recurring_expenses(user)  → QuerySet[RecurringExpense]
#   get_accessible_supplier_invoices(user)   → QuerySet[SupplierInvoice]
#   get_accessible_payables(user)            → QuerySet[Payable]
#   get_accessible_audit_logs(user)          → QuerySet[FinancialAuditLog]
#
# Security principle:
#   All querysets are scoped to what the user's role permits.
#   A user from Restaurant A must never see Restaurant B's financials
#   even if they guess a valid UUID.
#   Views call get_queryset().get(pk=pk) → 404 on miss (IDOR prevention).
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("financials")


def get_accessible_expense_categories(user):
    from financials.models import ExpenseCategory
    if not user or not user.is_authenticated or not user.is_active:
        return ExpenseCategory.objects.none()
    if user.is_superuser or user.is_staff:
        return ExpenseCategory.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return ExpenseCategory.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_expenses(user):
    from financials.models import Expense
    if not user or not user.is_authenticated or not user.is_active:
        return Expense.objects.none()
    if user.is_superuser or user.is_staff:
        return Expense.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return Expense.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_approvals(user):
    from financials.models import ExpenseApproval
    if not user or not user.is_authenticated or not user.is_active:
        return ExpenseApproval.objects.none()
    if user.is_superuser or user.is_staff:
        return ExpenseApproval.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return ExpenseApproval.objects.filter(
        expense__restaurant__in=accessible_restaurants
    )


def get_accessible_corrections(user):
    from financials.models import ExpenseCorrectionRequest
    if not user or not user.is_authenticated or not user.is_active:
        return ExpenseCorrectionRequest.objects.none()
    if user.is_superuser or user.is_staff:
        return ExpenseCorrectionRequest.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return ExpenseCorrectionRequest.objects.filter(
        expense__restaurant__in=accessible_restaurants
    )


def get_accessible_attachments(user):
    from financials.models import ExpenseAttachment
    if not user or not user.is_authenticated or not user.is_active:
        return ExpenseAttachment.objects.none()
    if user.is_superuser or user.is_staff:
        return ExpenseAttachment.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return ExpenseAttachment.objects.filter(
        expense__restaurant__in=accessible_restaurants
    )


def get_accessible_recurring_expenses(user):
    from financials.models import RecurringExpense
    if not user or not user.is_authenticated or not user.is_active:
        return RecurringExpense.objects.none()
    if user.is_superuser or user.is_staff:
        return RecurringExpense.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return RecurringExpense.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_supplier_invoices(user):
    from financials.models import SupplierInvoice
    if not user or not user.is_authenticated or not user.is_active:
        return SupplierInvoice.objects.none()
    if user.is_superuser or user.is_staff:
        return SupplierInvoice.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return SupplierInvoice.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_payables(user):
    from financials.models import Payable
    if not user or not user.is_authenticated or not user.is_active:
        return Payable.objects.none()
    if user.is_superuser or user.is_staff:
        return Payable.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return Payable.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_audit_logs(user):
    from financials.models import FinancialAuditLog
    if not user or not user.is_authenticated or not user.is_active:
        return FinancialAuditLog.objects.none()
    if user.is_superuser or user.is_staff:
        return FinancialAuditLog.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return FinancialAuditLog.objects.filter(restaurant__in=accessible_restaurants)
