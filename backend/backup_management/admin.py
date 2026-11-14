# =============================================================================
# RestaurantFlow — Backup Management Admin
# Phase 25
# =============================================================================

from django.contrib import admin

from backup_management.models import BackupRecord


@admin.register(BackupRecord)
class BackupRecordAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "backup_type",
        "status",
        "storage_provider",
        "file_name",
        "file_size",
        "encryption_status",
        "started_at",
        "completed_at",
        "verified_at",
        "retention_until",
        "created_at",
    ]
    list_filter = ["status", "backup_type", "storage_provider", "encryption_status"]
    search_fields = ["file_name", "storage_location"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "completed_at",
        "verified_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        # Backup records are created programmatically only.
        return False

    def has_delete_permission(self, request, obj=None):
        return False
