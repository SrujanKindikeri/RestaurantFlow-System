# =============================================================================
# RestaurantFlow — Kitchen Admin
# Phase 7
#
# Kitchen records are operational history — use read-only protection on
# timestamps and actor fields to prevent accidental data corruption.
# =============================================================================

from django.contrib import admin
from django.utils.html import format_html

from kitchen.models import KitchenOrder, KitchenOrderItem


# =============================================================================
# KitchenOrderItem inline
# =============================================================================

class KitchenOrderItemInline(admin.TabularInline):
    model = KitchenOrderItem
    extra = 0
    readonly_fields = (
        "id",
        "order_item",
        "menu_item",
        "item_name_snapshot",
        "quantity",
        "notes",
        "food_type",
        "preparation_time_minutes",
        "status",
        "station",
        "started_at",
        "ready_at",
        "cancelled_at",
        "created_at",
        "updated_at",
    )
    can_delete = False
    show_change_link = True
    ordering = ("created_at",)

    def has_add_permission(self, request, obj=None):
        return False


# =============================================================================
# KitchenOrder admin
# =============================================================================

@admin.register(KitchenOrder)
class KitchenOrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number_display",
        "branch",
        "order_type_display",
        "status_colored",
        "priority",
        "received_at",
        "accepted_at",
        "started_at",
        "ready_at",
        "cancelled_at",
    )
    list_filter = (
        "status",
        "priority",
        "branch",
        "order__order_type",
        "received_at",
    )
    search_fields = (
        "order__order_number",
        "branch__name",
        "order__table__table_number",
        "order__counter__code",
        "cancellation_reason",
    )
    readonly_fields = (
        "id",
        "order",
        "branch",
        "received_at",
        "accepted_at",
        "started_at",
        "ready_at",
        "cancelled_at",
        "accepted_by",
        "started_by",
        "completed_by",
        "cancelled_by",
        "created_at",
        "updated_at",
    )
    ordering = ("-received_at",)
    date_hierarchy = "received_at"
    inlines = [KitchenOrderItemInline]
    fieldsets = (
        (
            "Order Reference",
            {
                "fields": (
                    "id",
                    "order",
                    "branch",
                )
            },
        ),
        (
            "Kitchen State",
            {
                "fields": (
                    "status",
                    "priority",
                    "kitchen_note",
                    "cancellation_reason",
                )
            },
        ),
        (
            "Lifecycle Timestamps",
            {
                "fields": (
                    "received_at",
                    "accepted_at",
                    "started_at",
                    "ready_at",
                    "cancelled_at",
                )
            },
        ),
        (
            "Actors",
            {
                "fields": (
                    "accepted_by",
                    "started_by",
                    "completed_by",
                    "cancelled_by",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def order_number_display(self, obj):
        return obj.order.order_number
    order_number_display.short_description = "Order Number"
    order_number_display.admin_order_field = "order__order_number"

    def order_type_display(self, obj):
        return obj.order.order_type
    order_type_display.short_description = "Order Type"
    order_type_display.admin_order_field = "order__order_type"

    def status_colored(self, obj):
        colors = {
            "NEW":       "#2196F3",   # blue
            "ACCEPTED":  "#FF9800",   # orange
            "PREPARING": "#9C27B0",   # purple
            "READY":     "#4CAF50",   # green
            "CANCELLED": "#F44336",   # red
        }
        color = colors.get(obj.status, "#9E9E9E")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status,
        )
    status_colored.short_description = "Status"
    status_colored.admin_order_field = "status"


# =============================================================================
# KitchenOrderItem admin (standalone)
# =============================================================================

@admin.register(KitchenOrderItem)
class KitchenOrderItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_name_snapshot",
        "kitchen_order_number",
        "quantity",
        "food_type",
        "status",
        "station",
        "started_at",
        "ready_at",
    )
    list_filter = (
        "status",
        "food_type",
        "kitchen_order__branch",
        "kitchen_order__received_at",
    )
    search_fields = (
        "item_name_snapshot",
        "kitchen_order__order__order_number",
        "notes",
        "station",
    )
    readonly_fields = (
        "id",
        "kitchen_order",
        "order_item",
        "menu_item",
        "item_name_snapshot",
        "quantity",
        "notes",
        "food_type",
        "preparation_time_minutes",
        "started_at",
        "ready_at",
        "cancelled_at",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    def kitchen_order_number(self, obj):
        return obj.kitchen_order.order.order_number
    kitchen_order_number.short_description = "Order Number"
    kitchen_order_number.admin_order_field = "kitchen_order__order__order_number"
