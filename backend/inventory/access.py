# =============================================================================
# RestaurantFlow — Inventory Access Control
# Phase 10
#
# Single source of truth for inventory authorization decisions.
# Views and serializers delegate here — never duplicate access logic.
#
# Public API:
#   get_accessible_inventory_items(user)         → QuerySet[InventoryItem]
#   get_accessible_categories(user)              → QuerySet[InventoryCategory]
#   get_accessible_locations(user)               → QuerySet[StorageLocation]
#   get_accessible_stock_balances(user)          → QuerySet[StockBalance]
#   get_accessible_movements(user)               → QuerySet[StockMovement]
#   get_accessible_suppliers(user)               → QuerySet[Supplier]
#   get_accessible_purchase_orders(user)         → QuerySet[PurchaseOrder]
#   get_accessible_transfers(user)               → QuerySet[StockTransfer]
#   get_accessible_wastages(user)                → QuerySet[StockWastage]
#   get_accessible_adjustments(user)             → QuerySet[StockAdjustment]
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("inventory")


def get_accessible_inventory_items(user):
    from inventory.models import InventoryItem
    if not user or not user.is_authenticated or not user.is_active:
        return InventoryItem.objects.none()
    if user.is_superuser or user.is_staff:
        return InventoryItem.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return InventoryItem.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_categories(user):
    from inventory.models import InventoryCategory
    if not user or not user.is_authenticated or not user.is_active:
        return InventoryCategory.objects.none()
    if user.is_superuser or user.is_staff:
        return InventoryCategory.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return InventoryCategory.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_locations(user):
    from inventory.models import StorageLocation
    if not user or not user.is_authenticated or not user.is_active:
        return StorageLocation.objects.none()
    if user.is_superuser or user.is_staff:
        return StorageLocation.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return StorageLocation.objects.filter(branch__in=accessible_branches)


def get_accessible_stock_balances(user):
    from inventory.models import StockBalance
    if not user or not user.is_authenticated or not user.is_active:
        return StockBalance.objects.none()
    if user.is_superuser or user.is_staff:
        return StockBalance.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return StockBalance.objects.filter(storage_location__branch__in=accessible_branches)


def get_accessible_movements(user):
    from inventory.models import StockMovement
    if not user or not user.is_authenticated or not user.is_active:
        return StockMovement.objects.none()
    if user.is_superuser or user.is_staff:
        return StockMovement.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return StockMovement.objects.filter(storage_location__branch__in=accessible_branches)


def get_accessible_suppliers(user):
    from inventory.models import Supplier
    if not user or not user.is_authenticated or not user.is_active:
        return Supplier.objects.none()
    if user.is_superuser or user.is_staff:
        return Supplier.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return Supplier.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_purchase_orders(user):
    from inventory.models import PurchaseOrder
    if not user or not user.is_authenticated or not user.is_active:
        return PurchaseOrder.objects.none()
    if user.is_superuser or user.is_staff:
        return PurchaseOrder.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return PurchaseOrder.objects.filter(branch__in=accessible_branches)


def get_accessible_transfers(user):
    from inventory.models import StockTransfer
    if not user or not user.is_authenticated or not user.is_active:
        return StockTransfer.objects.none()
    if user.is_superuser or user.is_staff:
        return StockTransfer.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return StockTransfer.objects.filter(
        source_location__branch__in=accessible_branches
    )


def get_accessible_wastages(user):
    from inventory.models import StockWastage
    if not user or not user.is_authenticated or not user.is_active:
        return StockWastage.objects.none()
    if user.is_superuser or user.is_staff:
        return StockWastage.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return StockWastage.objects.filter(storage_location__branch__in=accessible_branches)


def get_accessible_adjustments(user):
    from inventory.models import StockAdjustment
    if not user or not user.is_authenticated or not user.is_active:
        return StockAdjustment.objects.none()
    if user.is_superuser or user.is_staff:
        return StockAdjustment.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return StockAdjustment.objects.filter(storage_location__branch__in=accessible_branches)
