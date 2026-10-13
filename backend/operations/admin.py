# =============================================================================
# RestaurantFlow — Operations Admin
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from django.contrib import admin
from operations.models import (
    POSDevice, POSSession,
    MenuModifierGroup, MenuModifierOption, OrderItemModifier,
    OrderFulfillmentStatus, OrderChangeRequest,
    TableFloorPlan, TableOperationalStatus,
    TableTransfer, TableMerge, OrderMergeRequest,
    BillSplit, BillSplitItem,
    ReceiptPrintLog, OperationalShift, ShiftHandoverNote,
    OperationsAuditLog,
)


@admin.register(POSDevice)
class POSDeviceAdmin(admin.ModelAdmin):
    list_display = ["device_name", "device_type", "branch", "is_active", "last_seen_at"]
    list_filter = ["device_type", "is_active", "branch"]
    search_fields = ["device_name", "device_identifier"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(POSSession)
class POSSessionAdmin(admin.ModelAdmin):
    list_display = ["user", "counter", "status", "started_at", "ended_at"]
    list_filter = ["status", "branch"]
    search_fields = ["user__email", "counter__code"]
    readonly_fields = ["started_at", "created_at", "updated_at"]


@admin.register(MenuModifierGroup)
class MenuModifierGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "restaurant", "is_required", "min_selections", "max_selections", "is_active"]
    list_filter = ["is_active", "is_required", "restaurant"]
    search_fields = ["name"]
    filter_horizontal = ["menu_items"]


@admin.register(MenuModifierOption)
class MenuModifierOptionAdmin(admin.ModelAdmin):
    list_display = ["name", "modifier_group", "price_adjustment", "is_active"]
    list_filter = ["is_active", "modifier_group"]
    search_fields = ["name"]


@admin.register(OrderItemModifier)
class OrderItemModifierAdmin(admin.ModelAdmin):
    list_display = ["name", "value", "price_adjustment", "order_item"]
    search_fields = ["name", "value"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(OrderFulfillmentStatus)
class OrderFulfillmentStatusAdmin(admin.ModelAdmin):
    list_display = ["order", "status", "served_by", "served_at"]
    list_filter = ["status"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(OrderChangeRequest)
class OrderChangeRequestAdmin(admin.ModelAdmin):
    list_display = ["order", "change_type", "status", "requested_by", "created_at"]
    list_filter = ["status", "change_type"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TableFloorPlan)
class TableFloorPlanAdmin(admin.ModelAdmin):
    list_display = ["table", "shape", "position_x", "position_y"]


@admin.register(TableOperationalStatus)
class TableOperationalStatusAdmin(admin.ModelAdmin):
    list_display = ["table", "status", "updated_by", "updated_at"]
    list_filter = ["status"]


@admin.register(TableTransfer)
class TableTransferAdmin(admin.ModelAdmin):
    list_display = ["source_table", "destination_table", "order", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TableMerge)
class TableMergeAdmin(admin.ModelAdmin):
    list_display = ["destination_table", "branch", "status", "created_at"]
    list_filter = ["status", "branch"]
    filter_horizontal = ["source_tables"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(OrderMergeRequest)
class OrderMergeRequestAdmin(admin.ModelAdmin):
    list_display = ["destination_order", "status", "requested_by", "created_at"]
    list_filter = ["status"]
    filter_horizontal = ["source_orders"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(BillSplit)
class BillSplitAdmin(admin.ModelAdmin):
    list_display = ["bill", "split_number", "split_type", "amount", "status"]
    list_filter = ["status", "split_type"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(BillSplitItem)
class BillSplitItemAdmin(admin.ModelAdmin):
    list_display = ["bill_split", "bill_item", "quantity", "amount"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ReceiptPrintLog)
class ReceiptPrintLogAdmin(admin.ModelAdmin):
    list_display = ["bill", "print_type", "printed_by", "printed_at"]
    list_filter = ["print_type"]
    readonly_fields = ["printed_at", "created_at", "updated_at"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OperationalShift)
class OperationalShiftAdmin(admin.ModelAdmin):
    list_display = ["branch", "shift_type", "status", "started_at", "ended_at", "opened_by"]
    list_filter = ["status", "shift_type", "branch"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ShiftHandoverNote)
class ShiftHandoverNoteAdmin(admin.ModelAdmin):
    list_display = ["shift", "note_type", "priority", "created_by", "created_at"]
    list_filter = ["note_type", "priority"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(OperationsAuditLog)
class OperationsAuditLogAdmin(admin.ModelAdmin):
    list_display = ["event_type", "actor", "branch", "occurred_at"]
    list_filter = ["event_type"]
    readonly_fields = ["occurred_at", "created_at", "updated_at"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
