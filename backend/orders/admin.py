# =============================================================================
# RestaurantFlow — Orders Admin
# Phase 6
# =============================================================================

from django.contrib import admin
from django.utils.html import format_html

from .models import DiningTable, TableSession, OrderSequence, Order, OrderItem


# =============================================================================
# DiningTable
# =============================================================================

@admin.register(DiningTable)
class DiningTableAdmin(admin.ModelAdmin):
    list_display = [
        "table_number", "name", "branch", "section",
        "capacity", "status", "display_order", "is_occupied_display",
        "created_at",
    ]
    list_filter = ["status", "section", "branch__restaurant"]
    search_fields = ["table_number", "name", "branch__name", "section"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["branch", "display_order", "table_number"]

    fieldsets = [
        ("Identity", {
            "fields": ["id", "branch", "table_number", "name", "section"],
        }),
        ("Configuration", {
            "fields": ["capacity", "status", "display_order"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def is_occupied_display(self, obj):
        occupied = obj.sessions.filter(status="OPEN").exists()
        color = "red" if occupied else "green"
        text = "Occupied" if occupied else "Available"
        return format_html('<span style="color: {};">{}</span>', color, text)

    is_occupied_display.short_description = "Occupancy"


# =============================================================================
# TableSession
# =============================================================================

@admin.register(TableSession)
class TableSessionAdmin(admin.ModelAdmin):
    list_display = [
        "id", "table", "status", "guest_count",
        "opened_by", "opened_at", "closed_by", "closed_at",
    ]
    list_filter = ["status", "table__branch__restaurant"]
    search_fields = ["table__table_number", "opened_by__email"]
    readonly_fields = [
        "id", "table", "opened_by", "opened_at",
        "created_at", "updated_at",
    ]
    ordering = ["-opened_at"]

    def has_delete_permission(self, request, obj=None):
        # Historical sessions must not be deleted
        return False

    def has_change_permission(self, request, obj=None):
        if obj and obj.status == "CLOSED":
            return False  # Closed sessions are immutable
        return super().has_change_permission(request, obj)


# =============================================================================
# OrderSequence
# =============================================================================

@admin.register(OrderSequence)
class OrderSequenceAdmin(admin.ModelAdmin):
    list_display = ["scope_type", "scope_id", "date_key", "last_sequence", "updated_at"]
    list_filter = ["scope_type", "date_key"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-date_key", "scope_type", "scope_id"]


# =============================================================================
# OrderItem Inline
# =============================================================================

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = [
        "menu_item", "item_name_snapshot", "sku_snapshot",
        "quantity", "unit_price_snapshot", "tax_rate_snapshot", "notes",
    ]
    readonly_fields = [
        "item_name_snapshot", "sku_snapshot",
        "unit_price_snapshot", "tax_rate_snapshot", "tax_code_snapshot",
    ]

    def has_delete_permission(self, request, obj=None):
        # Prevent deleting items from confirmed/cancelled orders via admin
        if obj and obj.status in ("CONFIRMED", "CANCELLED"):
            return False
        return super().has_delete_permission(request, obj)


# =============================================================================
# Order
# =============================================================================

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number", "order_type", "status",
        "branch", "table", "counter",
        "created_by", "assigned_waiter",
        "created_at",
    ]
    list_filter = ["status", "order_type", "branch__restaurant"]
    search_fields = [
        "order_number", "branch__name",
        "created_by__email", "assigned_waiter__email",
    ]
    readonly_fields = [
        "id", "order_number", "created_by",
        "confirmed_at", "cancelled_at", "cancelled_by",
        "created_at", "updated_at",
    ]
    inlines = [OrderItemInline]
    ordering = ["-created_at"]

    fieldsets = [
        ("Identity", {
            "fields": ["id", "order_number", "branch", "order_type"],
        }),
        ("Table (DINE_IN)", {
            "fields": ["table", "table_session", "guest_count"],
            "classes": ["collapse"],
        }),
        ("Counter (COUNTER/TAKEAWAY)", {
            "fields": ["counter", "counter_session"],
            "classes": ["collapse"],
        }),
        ("Actors", {
            "fields": ["created_by", "assigned_waiter"],
        }),
        ("Status", {
            "fields": [
                "status", "notes",
                "confirmed_at",
                "cancelled_at", "cancelled_by", "cancellation_reason",
            ],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    def has_delete_permission(self, request, obj=None):
        # Never allow hard deletion of orders
        return False


# =============================================================================
# OrderItem
# =============================================================================

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "id", "order", "item_name_snapshot",
        "quantity", "unit_price_snapshot", "tax_rate_snapshot",
        "created_at",
    ]
    list_filter = ["order__status", "order__branch__restaurant"]
    search_fields = [
        "item_name_snapshot", "sku_snapshot",
        "order__order_number",
    ]
    readonly_fields = [
        "id",
        "item_name_snapshot", "sku_snapshot",
        "unit_price_snapshot", "tax_rate_snapshot", "tax_code_snapshot",
        "created_at", "updated_at",
    ]
    ordering = ["-created_at"]

    def has_delete_permission(self, request, obj=None):
        # Do not allow deletion of historical order items
        if obj and obj.order.status in ("CONFIRMED", "CANCELLED"):
            return False
        return super().has_delete_permission(request, obj)
