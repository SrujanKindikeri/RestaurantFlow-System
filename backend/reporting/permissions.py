# =============================================================================
# RestaurantFlow — Reporting DRF Permissions
# Phase 14
#
# Each permission class maps to one reporting.*.view permission code.
# Views combine these using IsAuthenticated + the specific permission.
# =============================================================================

from rest_framework.permissions import BasePermission
from accounts import access as acl
from reporting.constants import (
    PERM_DASHBOARD_VIEW,
    PERM_SALES_VIEW,
    PERM_ORDERS_VIEW,
    PERM_MENU_VIEW,
    PERM_BRANCH_VIEW,
    PERM_COUNTER_VIEW,
    PERM_PAYMENT_VIEW,
    PERM_REFUND_VIEW,
    PERM_DISCOUNT_VIEW,
    PERM_KITCHEN_VIEW,
    PERM_STAFF_VIEW,
    PERM_INVENTORY_VIEW,
    PERM_PURCHASE_VIEW,
    PERM_SUPPLIER_VIEW,
    PERM_EXPENSE_VIEW,
    PERM_PAYABLE_VIEW,
    PERM_PROFITABILITY_VIEW,
    PERM_FINANCIAL_VIEW,
    PERM_EXPORT_CSV,
    PERM_EXPORT_EXCEL,
    PERM_EXPORT_PDF,
)


class CanViewDashboard(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_DASHBOARD_VIEW)


class CanViewSalesReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_SALES_VIEW)


class CanViewOrdersReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_ORDERS_VIEW)


class CanViewMenuReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_MENU_VIEW)


class CanViewBranchReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_BRANCH_VIEW)


class CanViewCounterReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_COUNTER_VIEW)


class CanViewPaymentReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_PAYMENT_VIEW)


class CanViewRefundReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_REFUND_VIEW)


class CanViewDiscountReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_DISCOUNT_VIEW)


class CanViewKitchenReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_KITCHEN_VIEW)


class CanViewStaffReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_STAFF_VIEW)


class CanViewInventoryReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_INVENTORY_VIEW)


class CanViewPurchaseReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_PURCHASE_VIEW)


class CanViewSupplierReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_SUPPLIER_VIEW)


class CanViewExpenseReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_EXPENSE_VIEW)


class CanViewPayableReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_PAYABLE_VIEW)


class CanViewProfitabilityReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_PROFITABILITY_VIEW)


class CanViewFinancialReport(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_FINANCIAL_VIEW)


class CanExportCSV(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_EXPORT_CSV)


class CanExportExcel(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_EXPORT_EXCEL)


class CanExportPDF(BasePermission):
    def has_permission(self, request, view):
        return acl.has_permission(request.user, PERM_EXPORT_PDF)
