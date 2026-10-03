# =============================================================================
# RestaurantFlow — Inventory Admin
# Phase 10
# =============================================================================

from django.contrib import admin
from inventory.models import (
    InventoryCategory,
    InventoryItem,
    StorageLocation,
    StockBalance,
    StockMovement,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    StockTransfer,
    StockTransferItem,
    StockWastage,
    StockAdjustment,
)


@admin.register(InventoryCategory)
class InventoryCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "restaurant", "is_active", "created_at"]
    list_filter = ["is_active", "restaurant"]
    search_fields = ["name"]


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ["name", "sku", "restaurant", "category", "default_unit", "average_cost", "is_active"]
    list_filter = ["is_active", "restaurant", "default_unit"]
    search_fields = ["name", "sku"]
    readonly_fields = ["average_cost"]


@admin.register(StorageLocation)
class StorageLocationAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "branch", "location_type", "is_active"]
    list_filter = ["is_active", "location_type"]
    search_fields = ["name", "code"]


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ["inventory_item", "storage_location", "quantity", "reserved_quantity", "average_cost"]
    list_filter = ["storage_location"]
    search_fields = ["inventory_item__name"]
    readonly_fields = ["quantity", "reserved_quantity", "average_cost", "last_movement_at"]


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ["movement_type", "inventory_item", "storage_location", "quantity", "unit_cost", "total_cost", "performed_by", "created_at"]
    list_filter = ["movement_type", "created_at"]
    search_fields = ["inventory_item__name"]
    readonly_fields = [f.name for f in StockMovement._meta.get_fields()]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "restaurant", "contact_person", "phone", "is_active"]
    list_filter = ["is_active", "restaurant"]
    search_fields = ["name", "code"]


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    readonly_fields = ["total_amount", "received_quantity"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ["purchase_number", "supplier", "branch", "status", "total_amount", "created_at"]
    list_filter = ["status", "restaurant"]
    search_fields = ["purchase_number", "supplier__name"]
    readonly_fields = ["purchase_number", "subtotal", "tax_amount", "total_amount"]
    inlines = [PurchaseOrderItemInline]


@admin.register(StockTransfer)
class StockTransferAdmin(admin.ModelAdmin):
    list_display = ["transfer_number", "source_location", "destination_location", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["transfer_number"]
    readonly_fields = ["transfer_number"]


@admin.register(StockWastage)
class StockWastageAdmin(admin.ModelAdmin):
    list_display = ["inventory_item", "storage_location", "quantity", "unit", "wastage_type", "status", "recorded_by"]
    list_filter = ["status", "wastage_type"]
    search_fields = ["inventory_item__name"]


@admin.register(StockAdjustment)
class StockAdjustmentAdmin(admin.ModelAdmin):
    list_display = ["inventory_item", "storage_location", "quantity_before", "quantity_physical", "quantity_difference", "adjusted_by", "created_at"]
    search_fields = ["inventory_item__name"]
    readonly_fields = ["quantity_difference", "stock_movement"]
