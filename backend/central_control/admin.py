# =============================================================================
# RestaurantFlow — Central Control Center Admin
# Phase 15
# =============================================================================

from django.contrib import admin

from central_control.models import (
    CentralControlSettings,
    CentralAlert,
    EscalationRule,
    CentralIssue,
    CentralSystemEvent,
    CentralControlAuditLog,
)


@admin.register(CentralControlSettings)
class CentralControlSettingsAdmin(admin.ModelAdmin):
    list_display = [
        "organization", "kitchen_delay_minutes", "kitchen_backlog_threshold",
        "payment_failure_threshold", "alert_escalation_enabled",
    ]
    search_fields = ["organization__name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CentralAlert)
class CentralAlertAdmin(admin.ModelAdmin):
    list_display = [
        "alert_type", "severity", "status", "title", "organization",
        "restaurant", "branch", "detected_at",
    ]
    list_filter = ["severity", "status", "alert_type"]
    search_fields = ["title", "message", "fingerprint"]
    readonly_fields = ["id", "fingerprint", "detected_at", "created_at", "updated_at"]


@admin.register(EscalationRule)
class EscalationRuleAdmin(admin.ModelAdmin):
    list_display = [
        "organization", "alert_type", "severity", "threshold_minutes",
        "auto_create_issue", "escalation_target_role", "is_active",
    ]
    list_filter = ["alert_type", "severity", "is_active"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CentralIssue)
class CentralIssueAdmin(admin.ModelAdmin):
    list_display = [
        "category", "severity", "status", "title", "organization",
        "restaurant", "assigned_to", "created_at",
    ]
    list_filter = ["category", "severity", "status"]
    search_fields = ["title", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CentralSystemEvent)
class CentralSystemEventAdmin(admin.ModelAdmin):
    list_display = [
        "event_type", "severity", "title", "organization",
        "restaurant", "branch", "occurred_at",
    ]
    list_filter = ["event_type", "severity"]
    search_fields = ["title", "description"]
    readonly_fields = ["id", "occurred_at", "created_at", "updated_at"]


@admin.register(CentralControlAuditLog)
class CentralControlAuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "action", "entity_type", "entity_id", "actor", "organization", "created_at",
    ]
    list_filter = ["action", "entity_type"]
    search_fields = ["entity_id", "actor__email"]
    readonly_fields = [
        "id", "actor", "action", "entity_type", "entity_id",
        "organization", "restaurant", "branch",
        "old_status", "new_status", "metadata", "created_at", "updated_at",
    ]

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable

    def has_delete_permission(self, request, obj=None):
        return False  # Never delete audit history
