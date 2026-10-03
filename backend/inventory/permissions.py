# =============================================================================
# RestaurantFlow — Inventory DRF Permission Classes
# Phase 10
#
# All authorization logic delegates to inventory.access and accounts.access.
# Views compose these with IsAuthenticated.
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

# Re-export for convenience — views import from here
from accounts.permissions import HasPermission  # noqa: F401

logger = logging.getLogger("inventory")


class HasInventoryItemAccess(BasePermission):
    """Object-level: user must be able to access this InventoryItem."""

    message = "You do not have access to this inventory item."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from inventory.access import get_accessible_inventory_items
        return get_accessible_inventory_items(request.user).filter(pk=obj.pk).exists()


class HasStorageLocationAccess(BasePermission):
    """Object-level: user must be able to access this StorageLocation."""

    message = "You do not have access to this storage location."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from inventory.access import get_accessible_locations
        return get_accessible_locations(request.user).filter(pk=obj.pk).exists()


class HasPurchaseOrderAccess(BasePermission):
    """Object-level: user must be able to access this PurchaseOrder."""

    message = "You do not have access to this purchase order."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from inventory.access import get_accessible_purchase_orders
        return get_accessible_purchase_orders(request.user).filter(pk=obj.pk).exists()


class HasTransferAccess(BasePermission):
    """Object-level: user must be able to access this StockTransfer."""

    message = "You do not have access to this stock transfer."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from inventory.access import get_accessible_transfers
        return get_accessible_transfers(request.user).filter(pk=obj.pk).exists()


class HasWastageAccess(BasePermission):
    """Object-level: user must be able to access this StockWastage."""

    message = "You do not have access to this wastage record."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from inventory.access import get_accessible_wastages
        return get_accessible_wastages(request.user).filter(pk=obj.pk).exists()
