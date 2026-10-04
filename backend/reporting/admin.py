# =============================================================================
# RestaurantFlow — Reporting Admin
# Phase 14
# =============================================================================

from django.contrib import admin
from reporting.models import ReportExportAudit


@admin.register(ReportExportAudit)
class ReportExportAuditAdmin(admin.ModelAdmin):
    list_display = [
        "report_type", "export_format", "actor", "restaurant",
        "branch", "status", "row_count", "created_at",
    ]
    list_filter = ["report_type", "export_format", "status", "created_at"]
    search_fields = ["actor__email", "report_type"]
    readonly_fields = [
        "id", "actor", "organization", "restaurant", "branch",
        "report_type", "export_format", "filters_applied",
        "status", "row_count", "failure_reason", "created_at", "updated_at",
    ]
    ordering = ["-created_at"]

    def has_add_permission(self, request):
        return False  # Audit records are created programmatically only

    def has_delete_permission(self, request, obj=None):
        return False  # Immutable
