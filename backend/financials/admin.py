# =============================================================================
# RestaurantFlow — Financials Admin
# Phase 12
# =============================================================================

from django.contrib import admin
from django.utils.html import format_html

from financials.models import (
    ExpenseCategory,
    ExpenseSequence,
    Expense,
    ExpenseApproval,
    ExpenseCorrectionRequest,
    ExpenseAttachment,
    RecurringExpense,
    SupplierInvoiceSequence,
    SupplierInvoice,
    Payable,
    FinancialAuditLog,
)


# ---------------------------------------------------------------------------
# ExpenseCategory
# ---------------------------------------------------------------------------

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "restaurant", "is_active", "created_at")
    list_filter = ("is_active", "restaurant")
    search_fields = ("name", "code")
    ordering = ("restaurant", "name")


# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------

class ExpenseAttachmentInline(admin.TabularInline):
    model = ExpenseAttachment
    extra = 0
    readonly_fields = ("id", "file_name", "file_type", "file_size", "uploaded_by", "uploaded_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ExpenseApprovalInline(admin.TabularInline):
    model = ExpenseApproval
    extra = 0
    readonly_fields = (
        "id", "requested_by", "reviewed_by", "status",
        "reviewed_at", "approval_note", "rejection_reason", "created_at",
    )
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "expense_number", "title", "restaurant", "branch",
        "category", "amount", "total_amount",
        "status", "payment_status",
        "expense_date", "created_by", "created_at",
    )
    list_filter = ("status", "payment_status", "restaurant", "category")
    search_fields = ("expense_number", "title", "vendor_name")
    ordering = ("-created_at",)
    inlines = [ExpenseApprovalInline, ExpenseAttachmentInline]
    readonly_fields = (
        "id", "expense_number", "total_amount",
        "submitted_at", "approved_at", "rejected_at",
        "created_at", "updated_at",
    )

    def get_readonly_fields(self, request, obj=None):
        """Make approved expenses fully read-only in admin."""
        base = list(self.readonly_fields)
        if obj and obj.status in ("APPROVED", "REJECTED", "CANCELLED"):
            return base + [
                "restaurant", "branch", "category", "title", "description",
                "amount", "tax_amount", "expense_date", "due_date",
                "vendor_name", "vendor_reference", "notes",
                "status", "payment_status",
            ]
        return base


# ---------------------------------------------------------------------------
# ExpenseCorrectionRequest
# ---------------------------------------------------------------------------

@admin.register(ExpenseCorrectionRequest)
class ExpenseCorrectionRequestAdmin(admin.ModelAdmin):
    list_display = (
        "expense", "correction_type", "requested_by", "status", "created_at"
    )
    list_filter = ("status", "correction_type")
    search_fields = ("expense__expense_number",)
    readonly_fields = (
        "id", "expense", "requested_by", "requested_data",
        "reviewed_at", "created_at", "updated_at",
    )


# ---------------------------------------------------------------------------
# RecurringExpense
# ---------------------------------------------------------------------------

@admin.register(RecurringExpense)
class RecurringExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "title", "restaurant", "frequency", "amount",
        "next_run_date", "is_active", "created_at",
    )
    list_filter = ("frequency", "is_active", "restaurant")
    search_fields = ("title",)
    readonly_fields = ("id", "created_at", "updated_at")


# ---------------------------------------------------------------------------
# SupplierInvoice
# ---------------------------------------------------------------------------

@admin.register(SupplierInvoice)
class SupplierInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number", "supplier", "restaurant", "branch",
        "total_amount", "status", "invoice_date", "due_date", "created_at",
    )
    list_filter = ("status", "restaurant", "supplier")
    search_fields = ("invoice_number", "external_invoice_number", "supplier__name")
    ordering = ("-created_at",)
    readonly_fields = (
        "id", "invoice_number", "approved_at",
        "created_at", "updated_at",
    )


# ---------------------------------------------------------------------------
# Payable
# ---------------------------------------------------------------------------

@admin.register(Payable)
class PayableAdmin(admin.ModelAdmin):
    list_display = (
        "reference_number", "payable_type", "restaurant",
        "amount", "paid_amount", "remaining_amount",
        "status", "due_date", "created_at",
    )
    list_filter = ("status", "payable_type", "restaurant")
    search_fields = ("reference_number",)
    readonly_fields = (
        "id", "remaining_amount", "created_at", "updated_at",
    )


# ---------------------------------------------------------------------------
# FinancialAuditLog — read-only, no add/change/delete
# ---------------------------------------------------------------------------

@admin.register(FinancialAuditLog)
class FinancialAuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "action", "entity_type", "entity_id",
        "actor", "restaurant", "old_status", "new_status", "created_at",
    )
    list_filter = ("action", "entity_type", "restaurant")
    search_fields = ("entity_id", "actor__email")
    ordering = ("-created_at",)
    readonly_fields = (
        "id", "actor", "action", "entity_type", "entity_id",
        "restaurant", "old_status", "new_status", "metadata", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# Sequences — read-only
# ---------------------------------------------------------------------------

@admin.register(ExpenseSequence)
class ExpenseSequenceAdmin(admin.ModelAdmin):
    list_display = ("restaurant", "last_sequence", "updated_at")
    readonly_fields = ("id", "restaurant", "last_sequence", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SupplierInvoiceSequence)
class SupplierInvoiceSequenceAdmin(admin.ModelAdmin):
    list_display = ("restaurant", "last_sequence", "updated_at")
    readonly_fields = ("id", "restaurant", "last_sequence", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
