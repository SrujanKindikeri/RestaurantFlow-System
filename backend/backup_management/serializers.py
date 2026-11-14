# =============================================================================
# RestaurantFlow — Backup Management Serializers
# Phase 25
# =============================================================================

from rest_framework import serializers

from backup_management.models import BackupRecord


class BackupRecordSerializer(serializers.ModelSerializer):
    """
    Read-only serializer for BackupRecord.

    All fields are read-only — backup records are created by Celery tasks,
    never by API consumers. The computed `duration_seconds` field is added
    via SerializerMethodField.

    Raw backup file paths (storage_location) ARE included because operators
    with view_backup_history need to know where backups reside.
    Download access is not provided through this API.
    """

    duration_seconds = serializers.SerializerMethodField()

    class Meta:
        model = BackupRecord
        fields = [
            "id",
            "backup_type",
            "storage_provider",
            "storage_location",
            "file_name",
            "file_size",
            "checksum",
            "encryption_status",
            "status",
            "started_at",
            "completed_at",
            "verified_at",
            "retention_until",
            "failure_reason",
            "duration_seconds",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_duration_seconds(self, obj) -> float | None:
        return obj.duration_seconds
