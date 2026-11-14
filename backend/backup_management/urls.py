# =============================================================================
# RestaurantFlow — Backup Management URL Configuration
# Phase 25
# =============================================================================

from django.urls import path

from backup_management.views import (
    BackupRecordListView,
    BackupRecordDetailView,
    BackupTriggerView,
)

urlpatterns = [
    path("backup/records/", BackupRecordListView.as_view(), name="backup-record-list"),
    path("backup/records/<uuid:pk>/", BackupRecordDetailView.as_view(), name="backup-record-detail"),
    path("backup/trigger/", BackupTriggerView.as_view(), name="backup-trigger"),
]
