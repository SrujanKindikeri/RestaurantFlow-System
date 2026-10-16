# =============================================================================
# RestaurantFlow — Enterprise Admin
# Phase 20
# =============================================================================

from django.contrib import admin
from django.utils.html import format_html

from enterprise.models import (
    BranchOperationalStatus,
    BranchOperatingHour,
    BranchClosure,
    EnterpriseConfiguration,
    ConfigurationChange,
    MenuRollout,
    MenuRolloutBranch,
    StaffBranchAssignment,
    StaffTransfer,
    ApprovalPolicy,
    EnterpriseAuditLog,
)


# ---------------------------------------------------------------------------
# BranchOperationalStatus
# ---------------------------------------------------------------------------

@admin.register(BranchOperationalStatus)
class BranchOperationalStatusAdmin(admin.ModelAdmin):
    list_display  = ["branch", "status", "status_changed_at", "status_changed_by"]
    list_filter   = ["status"]
    search_fields = ["branch__name", "branch__code"]
    raw_id_fields = ["branch", "status_changed_by"]
    readonly_fields = ["created_at", "updated_at"]


# ---------------------------------------------------------------------------
# BranchOperatingHour
# ---------------------------------------------------------------------------

@admin.register(BranchOperatingHour)
class BranchOperatingHourAdmin(admin.ModelAdmin):
    list_display  = ["branch", "day_of_week", "opening_time", "closing_time", "is_closed"]
    list_filter   = ["day_of_week", "is_closed"]
    search_fields = ["branch__name"]
    raw_id_fields = ["branch"]
    readonly_fields = ["created_at", "updated_at"]


# ---------------------------------------------------------------------------
# BranchClosure
# ---------------------------------------------------------------------------

@admin.register(BranchClosure)
class BranchClosureAdmin(admin.ModelAdmin):
    list_display  = [
        "branch", "closure_type", "start_datetime", "end_datetime", "status"
    ]
    list_filter   = ["closure_type", "status"]
    search_fields = ["branch__name", "reason"]
    raw_id_fields = ["branch", "created_by", "approved_by"]
    readonly_fields = ["created_at", "updated_at"]


# ---------------------------------------------------------------------------
# EnterpriseConfiguration
# ---------------------------------------------------------------------------

@admin.register(EnterpriseConfiguration)
class EnterpriseConfigurationAdmin(admin.ModelAdmin):
    list_display  = [
        "configuration_key", "configuration_value", "value_type",
        "scope", "is_active", "version", "company",
    ]
    list_filter   = ["is_active", "value_type"]
    search_fields = ["configuration_key", "configuration_value"]
    raw_id_fields = ["company", "restaurant", "branch", "created_by", "updated_by"]
    readonly_fields = ["scope", "version", "created_at", "updated_at"]

    def scope(self, obj):
        return obj.scope
    scope.short_description = "Scope"


# ---------------------------------------------------------------------------
# ConfigurationChange  (immutable — no add/change/delete in admin)
# ---------------------------------------------------------------------------

@admin.register(ConfigurationChange)
class ConfigurationChangeAdmin(admin.ModelAdmin):
    list_display  = [
        "configuration_key", "old_value", "new_value",
        "version", "changed_by", "scope", "created_at",
    ]
    list_filter   = ["scope"]
    search_fields = ["configuration_key", "change_reason"]
    raw_id_fields = ["company", "restaurant", "branch", "changed_by"]
    readonly_fields = [
        "company", "restaurant", "branch", "configuration_key",
        "old_value", "new_value", "version",
        "changed_by", "change_reason", "scope", "created_at", "updated_at",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ---------------------------------------------------------------------------
# MenuRollout
# ---------------------------------------------------------------------------

class MenuRolloutBranchInline(admin.TabularInline):
    model  = MenuRolloutBranch
    extra  = 0
    readonly_fields = ["branch", "result", "old_value", "new_value", "failure_reason", "created_at"]
    can_delete = False


@admin.register(MenuRollout)
class MenuRolloutAdmin(admin.ModelAdmin):
    list_display  = [
        "menu_item", "restaurant", "rollout_type",
        "target_scope", "status", "created_by", "created_at",
    ]
    list_filter   = ["status", "rollout_type", "target_scope"]
    search_fields = ["menu_item__name", "restaurant__name"]
    raw_id_fields = [
        "restaurant", "menu_item", "source_branch",
        "created_by", "approved_by",
    ]
    readonly_fields = ["created_at", "updated_at", "completed_at", "approved_at"]
    inlines = [MenuRolloutBranchInline]


# ---------------------------------------------------------------------------
# StaffBranchAssignment
# ---------------------------------------------------------------------------

@admin.register(StaffBranchAssignment)
class StaffBranchAssignmentAdmin(admin.ModelAdmin):
    list_display  = [
        "user", "branch", "restaurant", "role",
        "is_primary", "is_active", "assigned_at",
    ]
    list_filter   = ["is_primary", "is_active"]
    search_fields = ["user__email", "branch__name"]
    raw_id_fields = ["user", "restaurant", "branch", "role", "assigned_by"]
    readonly_fields = ["assigned_at", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# StaffTransfer
# ---------------------------------------------------------------------------

@admin.register(StaffTransfer)
class StaffTransferAdmin(admin.ModelAdmin):
    list_display  = [
        "user", "source_branch", "destination_branch",
        "status", "requested_by", "requested_at",
    ]
    list_filter   = ["status"]
    search_fields = ["user__email", "source_branch__name", "destination_branch__name"]
    raw_id_fields = [
        "user", "restaurant", "source_branch", "destination_branch",
        "requested_by", "approved_by",
    ]
    readonly_fields = [
        "requested_at", "approved_at", "completed_at",
        "rejected_at", "created_at", "updated_at",
    ]


# ---------------------------------------------------------------------------
# ApprovalPolicy
# ---------------------------------------------------------------------------

@admin.register(ApprovalPolicy)
class ApprovalPolicyAdmin(admin.ModelAdmin):
    list_display  = [
        "policy_type", "company", "restaurant", "branch",
        "threshold_amount", "threshold_percentage",
        "required_permission", "is_active",
    ]
    list_filter   = ["policy_type", "is_active"]
    search_fields = ["policy_type", "required_permission"]
    raw_id_fields = ["company", "restaurant", "branch", "required_role", "created_by", "updated_by"]
    readonly_fields = ["created_at", "updated_at"]


# ---------------------------------------------------------------------------
# EnterpriseAuditLog  (immutable — no add/change/delete in admin)
# ---------------------------------------------------------------------------

@admin.register(EnterpriseAuditLog)
class EnterpriseAuditLogAdmin(admin.ModelAdmin):
    list_display  = [
        "action", "description_short", "company",
        "restaurant", "branch", "performed_by", "created_at",
    ]
    list_filter   = ["action"]
    search_fields = ["action", "description", "source_id"]
    raw_id_fields = ["company", "restaurant", "branch", "performed_by"]
    readonly_fields = [
        "action", "description", "company", "restaurant", "branch",
        "performed_by", "source_type", "source_id", "metadata",
        "created_at", "updated_at",
    ]

    def description_short(self, obj):
        return obj.description[:80]
    description_short.short_description = "Description"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
