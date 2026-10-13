# =============================================================================
# RestaurantFlow — Operations Permissions
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from rest_framework.permissions import BasePermission
from operations.constants import (
    PERM_POS_ACCESS, PERM_POS_SESSION_START, PERM_POS_SESSION_PAUSE,
    PERM_POS_SESSION_END, PERM_POS_ORDER_CREATE, PERM_POS_ORDER_HOLD,
    PERM_POS_ORDER_RESUME, PERM_POS_ORDER_PRIORITY,
    PERM_POS_ORDER_PRIORITY_URGENT,
    PERM_ORDER_CHANGE_REQUEST, PERM_ORDER_CHANGE_APPROVE,
    PERM_ORDER_WAITER_ASSIGN,
    PERM_TABLE_VIEW, PERM_TABLE_MANAGE, PERM_TABLE_TRANSFER, PERM_TABLE_MERGE,
    PERM_BILL_SPLIT,
    PERM_RECEIPT_PRINT, PERM_RECEIPT_REPRINT,
    PERM_SHIFT_VIEW, PERM_SHIFT_CREATE, PERM_SHIFT_CLOSE,
    PERM_OPERATIONS_DASHBOARD, PERM_ORDER_MERGE,
    PERM_ORDER_MODIFIER_MANAGE,
)


class HasPOSAccess(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_POS_ACCESS)


class CanStartPOSSession(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_POS_SESSION_START)


class CanPausePOSSession(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_POS_SESSION_PAUSE)


class CanEndPOSSession(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_POS_SESSION_END)


class CanHoldOrder(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_POS_ORDER_HOLD)


class CanSetUrgentPriority(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_POS_ORDER_PRIORITY_URGENT)


class CanManageModifiers(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_ORDER_MODIFIER_MANAGE)


class CanRequestOrderChange(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_ORDER_CHANGE_REQUEST)


class CanApproveOrderChange(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_ORDER_CHANGE_APPROVE)


class CanAssignWaiter(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_ORDER_WAITER_ASSIGN)


class CanTransferTable(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_TABLE_TRANSFER)


class CanMergeTable(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_TABLE_MERGE)


class CanManageTables(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_TABLE_MANAGE)


class CanSplitBill(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_BILL_SPLIT)


class CanPrintReceipt(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_RECEIPT_PRINT)


class CanReprintReceipt(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_RECEIPT_REPRINT)


class CanManageShifts(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_SHIFT_CREATE)


class CanViewOperationsDashboard(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_OPERATIONS_DASHBOARD)


class CanMergeOrders(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.has_perm_code(PERM_ORDER_MERGE)
