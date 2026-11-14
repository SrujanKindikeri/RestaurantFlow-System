# =============================================================================
# RestaurantFlow — Backup Management Models
# Phase 25
#
# Models:
#   BackupRecord — tracks every backup operation and its lifecycle
#
# Design:
#   - UUID primary key; TimestampedModel base.
#   - All choice fields use constants from backup_management.constants.
#   - Custom permissions declared in Meta.permissions.
#   - No FK to any restaurant/branch — backup records are system-global.
# =============================================================================

import uuid

from django.db import models

from core.models import TimestampedModel
from backup_management.constants import (
    BACKUP_TYPE_CHOICES,
    STORAGE_PROVIDER_CHOICES,
    ENCRYPTION_STATUS_CHOICES, ENCRYPTION_STATUS_UNKNOWN,
    BACKUP_STATUS_CHOICES, BACKUP_STATUS_PENDING,
)


class BackupRecord(TimestampedModel):
    """
    Records a single backup operation from inception through verification.

    Lifecycle: PENDING → RUNNING → COMPLETED → VERIFIED
                                 → FAILED
                       → EXPIRED  (after retention_until passes)

    file_size is in bytes. checksum is a hex SHA-256 digest.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    backup_type = models.CharField(
        max_length=40,
        choices=BACKUP_TYPE_CHOICES,
        db_index=True,
    )
    storage_provider = models.CharField(
        max_length=40,
        choices=STORAGE_PROVIDER_CHOICES,
        default="LOCAL",
        db_index=True,
    )
    storage_location = models.CharField(
        max_length=500,
        help_text="Path or URI where the backup file is stored.",
    )
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Backup file size in bytes.",
    )
    checksum = models.CharField(
        max_length=128,
        blank=True,
        help_text="Hex-encoded SHA-256 digest of the backup file.",
    )
    encryption_status = models.CharField(
        max_length=20,
        choices=ENCRYPTION_STATUS_CHOICES,
        default=ENCRYPTION_STATUS_UNKNOWN,
    )
    status = models.CharField(
        max_length=20,
        choices=BACKUP_STATUS_CHOICES,
        default=BACKUP_STATUS_PENDING,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    retention_until = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this backup record may be expired and its file deleted.",
    )
    failure_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Backup Record"
        verbose_name_plural = "Backup Records"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["backup_type", "status"]),
            models.Index(fields=["backup_type", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["retention_until"]),
        ]
        permissions = [
            ("view_backup_status",          "Can view backup status"),
            ("view_backup_history",         "Can view backup history"),
            ("create_backup",               "Can create/trigger backup"),
            ("verify_backup",               "Can verify backup integrity"),
            ("request_restore",             "Can request a restore"),
            ("approve_restore",             "Can approve a restore"),
            ("manage_retention",            "Can manage retention policy"),
            ("manage_backup_configuration", "Can manage backup configuration"),
        ]

    def __str__(self):
        return (
            f"BackupRecord({self.backup_type}, {self.status}, "
            f"{self.file_name or 'pending'}, {self.created_at.date() if self.created_at else '?'})"
        )

    @property
    def duration_seconds(self):
        """Return backup duration in seconds, or None if not yet complete."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
