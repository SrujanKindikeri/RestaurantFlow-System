# =============================================================================
# RestaurantFlow — Notifications Django Admin
# Phase 16
# =============================================================================

from django.contrib import admin
from django.utils.html import format_html

from notifications.models import (
    Notification,
    NotificationRecipient,
    NotificationDelivery,
    NotificationPreference,
    NotificationTemplate,
    NotificationProviderConfig,
)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ["notification_type", "severity", "title", "company", "restaurant", "branch", "created_at"]
    list_filter   = ["notification_type", "severity", "source_type", "company"]
    search_fields = ["title", "message", "source_id"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering      = ["-created_at"]

    def has_add_permission(self, request):
        return False  # Notifications are created programmatically only


@admin.register(NotificationRecipient)
class NotificationRecipientAdmin(admin.ModelAdmin):
    list_display  = ["user", "notification", "delivery_status", "read_at", "created_at"]
    list_filter   = ["delivery_status"]
    search_fields = ["user__email", "notification__title"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering      = ["-created_at"]

    def has_add_permission(self, request):
        return False


@admin.register(NotificationDelivery)
class NotificationDeliveryAdmin(admin.ModelAdmin):
    list_display  = ["channel", "status", "attempt_count", "provider", "queued_at", "sent_at", "failed_at"]
    list_filter   = ["channel", "status", "provider"]
    search_fields = ["provider_message_id", "failure_reason"]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering      = ["-created_at"]

    def has_add_permission(self, request):
        return False


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ["user", "notification_type", "channel", "enabled", "updated_at"]
    list_filter  = ["channel", "enabled", "notification_type"]
    search_fields = ["user__email"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display  = ["notification_type", "channel", "company", "is_active", "updated_at"]
    list_filter   = ["notification_type", "channel", "is_active"]
    search_fields = ["subject_template", "body_template"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(NotificationProviderConfig)
class NotificationProviderConfigAdmin(admin.ModelAdmin):
    list_display  = ["company", "channel", "provider", "is_enabled", "updated_at"]
    list_filter   = ["channel", "is_enabled"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        # Never show configuration_metadata in a way that suggests secrets are stored there
        return fields
