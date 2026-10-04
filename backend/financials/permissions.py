# =============================================================================
# RestaurantFlow — Financials DRF Permission Classes
# Phase 12
#
# All authorization logic delegates to accounts.access and financials.access.
# Never check role names directly — always use permission codes.
#
# Permission codes registered in this module:
#
#   expense.view               expense.create
#   expense.update             expense.submit
#   expense.approve            expense.reject
#   expense.cancel
#   expense.category.view      expense.category.create
#   expense.category.update
#   expense.attachment.view    expense.attachment.create
#   expense.attachment.delete
#   expense.correction.request expense.correction.approve
#   expense.correction.reject
#   recurring_expense.view     recurring_expense.create
#   recurring_expense.update   recurring_expense.disable
#   supplier_invoice.view      supplier_invoice.create
#   supplier_invoice.update    supplier_invoice.submit
#   supplier_invoice.approve   supplier_invoice.cancel
#   payable.view               payable.manage
#   financial.dashboard.view
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

# Re-export HasPermission factory from accounts for convenience
from accounts.permissions import HasPermission  # noqa: F401

logger = logging.getLogger("financials")


class HasExpenseAccess(BasePermission):
    """Object-level: user must be able to access this Expense's restaurant."""

    message = "You do not have access to this expense."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from financials.access import get_accessible_expenses
        return get_accessible_expenses(request.user).filter(pk=obj.pk).exists()


class HasSupplierInvoiceAccess(BasePermission):
    """Object-level: user must be able to access this SupplierInvoice."""

    message = "You do not have access to this supplier invoice."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from financials.access import get_accessible_supplier_invoices
        return get_accessible_supplier_invoices(request.user).filter(pk=obj.pk).exists()


class HasPayableAccess(BasePermission):
    """Object-level: user must be able to access this Payable."""

    message = "You do not have access to this payable."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from financials.access import get_accessible_payables
        return get_accessible_payables(request.user).filter(pk=obj.pk).exists()


class HasCorrectionAccess(BasePermission):
    """Object-level: user must be able to access this ExpenseCorrectionRequest."""

    message = "You do not have access to this correction request."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from financials.access import get_accessible_corrections
        return get_accessible_corrections(request.user).filter(pk=obj.pk).exists()


# ---------------------------------------------------------------------------
# Permission code constants — used in views
# ---------------------------------------------------------------------------

PERM_EXPENSE_VIEW               = "expense.view"
PERM_EXPENSE_CREATE             = "expense.create"
PERM_EXPENSE_UPDATE             = "expense.update"
PERM_EXPENSE_SUBMIT             = "expense.submit"
PERM_EXPENSE_APPROVE            = "expense.approve"
PERM_EXPENSE_REJECT             = "expense.reject"
PERM_EXPENSE_CANCEL             = "expense.cancel"

PERM_CATEGORY_VIEW              = "expense.category.view"
PERM_CATEGORY_CREATE            = "expense.category.create"
PERM_CATEGORY_UPDATE            = "expense.category.update"

PERM_ATTACHMENT_VIEW            = "expense.attachment.view"
PERM_ATTACHMENT_CREATE          = "expense.attachment.create"
PERM_ATTACHMENT_DELETE          = "expense.attachment.delete"

PERM_CORRECTION_REQUEST         = "expense.correction.request"
PERM_CORRECTION_APPROVE         = "expense.correction.approve"
PERM_CORRECTION_REJECT          = "expense.correction.reject"

PERM_RECURRING_VIEW             = "recurring_expense.view"
PERM_RECURRING_CREATE           = "recurring_expense.create"
PERM_RECURRING_UPDATE           = "recurring_expense.update"
PERM_RECURRING_DISABLE          = "recurring_expense.disable"

PERM_SINV_VIEW                  = "supplier_invoice.view"
PERM_SINV_CREATE                = "supplier_invoice.create"
PERM_SINV_UPDATE                = "supplier_invoice.update"
PERM_SINV_SUBMIT                = "supplier_invoice.submit"
PERM_SINV_APPROVE               = "supplier_invoice.approve"
PERM_SINV_CANCEL                = "supplier_invoice.cancel"

PERM_PAYABLE_VIEW               = "payable.view"
PERM_PAYABLE_MANAGE             = "payable.manage"

PERM_FINANCIAL_DASHBOARD        = "financial.dashboard.view"

# Full list used by seed command
ALL_FINANCIAL_PERMISSIONS = [
    (PERM_EXPENSE_VIEW,        "expense",          "view",    "View expenses"),
    (PERM_EXPENSE_CREATE,      "expense",          "create",  "Create expenses"),
    (PERM_EXPENSE_UPDATE,      "expense",          "update",  "Update draft expenses"),
    (PERM_EXPENSE_SUBMIT,      "expense",          "submit",  "Submit expenses for approval"),
    (PERM_EXPENSE_APPROVE,     "expense",          "approve", "Approve expenses"),
    (PERM_EXPENSE_REJECT,      "expense",          "reject",  "Reject expenses"),
    (PERM_EXPENSE_CANCEL,      "expense",          "cancel",  "Cancel expenses"),
    (PERM_CATEGORY_VIEW,       "expense_category", "view",    "View expense categories"),
    (PERM_CATEGORY_CREATE,     "expense_category", "create",  "Create expense categories"),
    (PERM_CATEGORY_UPDATE,     "expense_category", "update",  "Update expense categories"),
    (PERM_ATTACHMENT_VIEW,     "expense_attachment","view",   "View expense attachments"),
    (PERM_ATTACHMENT_CREATE,   "expense_attachment","create", "Upload expense attachments"),
    (PERM_ATTACHMENT_DELETE,   "expense_attachment","delete", "Delete expense attachments"),
    (PERM_CORRECTION_REQUEST,  "expense_correction","request","Request expense corrections"),
    (PERM_CORRECTION_APPROVE,  "expense_correction","approve","Approve expense corrections"),
    (PERM_CORRECTION_REJECT,   "expense_correction","reject", "Reject expense corrections"),
    (PERM_RECURRING_VIEW,      "recurring_expense","view",    "View recurring expenses"),
    (PERM_RECURRING_CREATE,    "recurring_expense","create",  "Create recurring expenses"),
    (PERM_RECURRING_UPDATE,    "recurring_expense","update",  "Update recurring expenses"),
    (PERM_RECURRING_DISABLE,   "recurring_expense","disable", "Disable recurring expenses"),
    (PERM_SINV_VIEW,           "supplier_invoice", "view",    "View supplier invoices"),
    (PERM_SINV_CREATE,         "supplier_invoice", "create",  "Create supplier invoices"),
    (PERM_SINV_UPDATE,         "supplier_invoice", "update",  "Update supplier invoices"),
    (PERM_SINV_SUBMIT,         "supplier_invoice", "submit",  "Submit supplier invoices"),
    (PERM_SINV_APPROVE,        "supplier_invoice", "approve", "Approve supplier invoices"),
    (PERM_SINV_CANCEL,         "supplier_invoice", "cancel",  "Cancel supplier invoices"),
    (PERM_PAYABLE_VIEW,        "payable",          "view",    "View payables"),
    (PERM_PAYABLE_MANAGE,      "payable",          "manage",  "Manage payables (record payments)"),
    (PERM_FINANCIAL_DASHBOARD, "financial",        "dashboard_view", "View financial dashboard"),
]
