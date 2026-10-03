# =============================================================================
# RestaurantFlow — Billing Admin
# Phase 8
#
# Registered models:
#   Bill               — with read-only financial fields for finalized bills
#   BillItem           — inline + standalone
#   BillCorrectionRequest — with status filter
#   BillSequence       — read-only (do not allow manual editing)
#
# Financial fields on finalized bills are read-only to prevent accidental
# modification through the admin interface.
# =============================================================================

from django.contrib import admin
from django.utils.html import format_html

from billing.models import (
    Bill, BillItem, BillCorrectionRequest, BillSequence, BillStatus,
)


# =============================================================================
# BillItem Inline
# =============================================================================

class BillItemInline(admin.TabularInline):
    model = BillItem
    extra = 0
    readonly_fields = (
        "id", "order_item", "menu_item",
        "item_name_snapshot", "sku_snapshot", "quantity",
        "unit_price", "gross_amount", "discount_amount",
        "taxable_amount", "tax_rate", "tax_code",
        "tax_amount", "total_amount", "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# =============================================================================
# Bill Admin
# =============================================================================

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = (
        "bill_number",
        "order_link",
        "branch",
        "status_badge",
        "subtotal",
        "discount_amount",
        "tax_amount",
        "grand_total",
        "created_by",
        "finalized_at",
        "created_at",
    )
    list_filter = (
        "status",
        "discount_type",
        "branch__restaurant",
        "branch",
        ("created_at", admin.DateFieldListFilter),
        ("finalized_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "bill_number",
        "order__order_number",
        "created_by__email",
        "finalized_by__email",
        "branch__name",
    )
    ordering = ("-created_at",)
    readonly_fields = (
        "id",
        "bill_number",
        "order",
        "branch",
        "created_by",
        "created_at",
        "updated_at",
    )
    inlines = [BillItemInline]

    fieldsets = (
        ("Identification", {
            "fields": ("id", "bill_number", "order", "branch", "status"),
        }),
        ("Discount", {
            "fields": ("discount_type", "discount_value"),
        }),
        ("Financial Totals", {
            "fields": (
                "subtotal", "discount_amount", "taxable_amount",
                "tax_amount", "tax_breakdown", "rounding_amount", "grand_total",
            ),
            "classes": ("collapse",),
        }),
        ("Notes", {
            "fields": ("notes",),
        }),
        ("Actors", {
            "fields": (
                "created_by",
                "finalized_by", "finalized_at",
                "cancelled_by", "cancelled_at", "cancellation_reason",
            ),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Make financial fields read-only for finalized/cancelled/voided bills."""
        base = list(self.readonly_fields)
        if obj and obj.status in (BillStatus.FINALIZED, BillStatus.CANCELLED, BillStatus.VOID):
            base += [
                "discount_type", "discount_value",
                "subtotal", "discount_amount", "taxable_amount",
                "tax_amount", "tax_breakdown", "rounding_amount", "grand_total",
                "status", "notes",
                "finalized_by", "finalized_at",
                "cancelled_by", "cancelled_at", "cancellation_reason",
            ]
        return base

    def order_link(self, obj):
        return obj.order.order_number if obj.order_id else "—"
    order_link.short_description = "Order"

    def status_badge(self, obj):
        colors = {
            BillStatus.DRAFT:     "#6c757d",
            BillStatus.FINALIZED: "#28a745",
            BillStatus.CANCELLED: "#dc3545",
            BillStatus.VOID:      "#343a40",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:white;padding:2px 8px;'
            'border-radius:3px;font-size:11px">{}</span>',
            color, obj.status,
        )
    status_badge.short_description = "Status"


# =============================================================================
# BillItem Admin (standalone)
# =============================================================================

@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
    list_display = (
        "bill",
        "item_name_snapshot",
        "quantity",
        "unit_price",
        "gross_amount",
        "tax_rate",
        "tax_amount",
        "total_amount",
    )
    list_filter = (
        "bill__status",
        "bill__branch",
        "tax_code",
    )
    search_fields = (
        "bill__bill_number",
        "item_name_snapshot",
        "sku_snapshot",
        "tax_code",
    )
    readonly_fields = (
        "id", "bill", "order_item", "menu_item",
        "item_name_snapshot", "sku_snapshot", "quantity", "unit_price",
        "gross_amount", "discount_amount", "taxable_amount",
        "tax_rate", "tax_code", "tax_amount", "total_amount",
        "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing but prevent direct edits to line items
        return False


# =============================================================================
# BillCorrectionRequest Admin
# =============================================================================

@admin.register(BillCorrectionRequest)
class BillCorrectionRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "bill_number",
        "correction_type",
        "status",
        "requested_by",
        "reviewed_by",
        "reviewed_at",
        "created_at",
    )
    list_filter = (
        "status",
        "correction_type",
        "bill__branch",
        ("created_at", admin.DateFieldListFilter),
        ("reviewed_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "bill__bill_number",
        "requested_by__email",
        "reviewed_by__email",
        "reason",
        "review_note",
    )
    readonly_fields = (
        "id",
        "bill",
        "requested_by",
        "correction_type",
        "reason",
        "requested_data",
        "created_at",
        "updated_at",
    )
    ordering = ("-created_at",)

    fieldsets = (
        ("Request", {
            "fields": ("id", "bill", "correction_type", "reason", "requested_by"),
        }),
        ("Status", {
            "fields": ("status",),
        }),
        ("Review", {
            "fields": ("reviewed_by", "reviewed_at", "review_note"),
        }),
        ("Snapshot", {
            "fields": ("requested_data",),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    def bill_number(self, obj):
        return obj.bill.bill_number if obj.bill_id else "—"
    bill_number.short_description = "Bill"

    def get_readonly_fields(self, request, obj=None):
        base = list(self.readonly_fields)
        if obj and obj.status != "PENDING":
            # Reviewed corrections should not be re-reviewed
            base += ["status", "reviewed_by", "reviewed_at", "review_note"]
        return base


# =============================================================================
# BillSequence Admin
# =============================================================================

@admin.register(BillSequence)
class BillSequenceAdmin(admin.ModelAdmin):
    list_display = ("branch", "year_key", "last_sequence", "updated_at")
    list_filter = ("year_key", "branch__restaurant")
    search_fields = ("branch__name", "year_key")
    readonly_fields = ("id", "branch", "year_key", "last_sequence", "created_at", "updated_at")

    def has_add_permission(self, request):
        """Sequences are created automatically — do not allow manual creation."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Sequences must never be deleted — bill numbers are immutable."""
        return False
