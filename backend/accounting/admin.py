# =============================================================================
# RestaurantFlow — Accounting Admin
# Phase 13
# =============================================================================

from django.contrib import admin
from accounting.models import (
    FiscalYear, AccountingPeriod, Account, AccountingSettings,
    JournalSequence, JournalEntry, JournalEntryLine, AccountingAuditLog,
)


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ["name", "restaurant", "start_date", "end_date", "status"]
    list_filter = ["status", "restaurant"]
    search_fields = ["name", "restaurant__name"]
    ordering = ["-start_date"]
    readonly_fields = ["closed_at", "closed_by", "created_at", "updated_at"]


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ["name", "restaurant", "start_date", "end_date", "status"]
    list_filter = ["status", "restaurant"]
    search_fields = ["name", "restaurant__name"]
    ordering = ["-start_date"]
    readonly_fields = ["closed_at", "closed_by", "created_at", "updated_at"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "account_type", "account_subtype",
        "normal_balance", "is_group", "is_postable", "is_active",
        "is_system_account", "restaurant",
    ]
    list_filter = [
        "account_type", "is_active", "is_group", "is_postable",
        "is_system_account", "restaurant",
    ]
    search_fields = ["code", "name", "restaurant__name"]
    ordering = ["restaurant", "code"]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["parent_account"]


@admin.register(AccountingSettings)
class AccountingSettingsAdmin(admin.ModelAdmin):
    list_display = ["restaurant"]
    raw_id_fields = [
        "default_sales_account", "default_discount_account",
        "default_cash_account", "default_bank_account",
        "default_accounts_receivable", "default_inventory_account",
        "default_card_clearing_account", "default_upi_clearing_account",
        "default_accounts_payable", "default_tax_payable",
        "default_cogs_account", "default_rounding_account",
        "retained_earnings_account",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(JournalSequence)
class JournalSequenceAdmin(admin.ModelAdmin):
    list_display = ["restaurant", "last_sequence"]
    readonly_fields = ["created_at", "updated_at"]


class JournalEntryLineInline(admin.TabularInline):
    model = JournalEntryLine
    extra = 0
    readonly_fields = ["created_at"]
    fields = ["account", "description", "debit_amount", "credit_amount", "reference_type"]


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = [
        "entry_number", "entry_date", "restaurant", "branch",
        "source_type", "status", "created_by",
    ]
    list_filter = ["status", "source_type", "restaurant"]
    search_fields = ["entry_number", "description", "restaurant__name"]
    ordering = ["-entry_date", "-created_at"]
    readonly_fields = [
        "entry_number", "posted_by", "posted_at",
        "reversed_by", "reversed_at", "created_at", "updated_at",
    ]
    inlines = [JournalEntryLineInline]

    def has_change_permission(self, request, obj=None):
        """Posted journal entries should not be editable in admin."""
        if obj and obj.status in ("POSTED", "REVERSED"):
            return False
        return super().has_change_permission(request, obj)


@admin.register(JournalEntryLine)
class JournalEntryLineAdmin(admin.ModelAdmin):
    list_display = [
        "journal_entry", "account", "debit_amount", "credit_amount",
        "description", "created_at",
    ]
    list_filter = ["account__account_type", "account__restaurant"]
    search_fields = ["journal_entry__entry_number", "account__code", "account__name"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(AccountingAuditLog)
class AccountingAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "action", "entity_type", "entity_id", "actor",
        "restaurant", "created_at",
    ]
    list_filter = ["action", "entity_type", "restaurant"]
    search_fields = ["actor__email", "entity_type", "action"]
    ordering = ["-created_at"]
    readonly_fields = [field.name for field in AccountingAuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
