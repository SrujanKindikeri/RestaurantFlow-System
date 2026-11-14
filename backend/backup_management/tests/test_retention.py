# =============================================================================
# RestaurantFlow — Backup Retention Tests
# Phase 25
# =============================================================================

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from backup_management.models import BackupRecord
from backup_management.constants import (
    BACKUP_TYPE_DATABASE_FULL,
    BACKUP_TYPE_MEDIA,
    BACKUP_STATUS_COMPLETED,
    BACKUP_STATUS_VERIFIED,
    BACKUP_STATUS_EXPIRED,
    STORAGE_PROVIDER_LOCAL,
    ENCRYPTION_STATUS_ENCRYPTED,
)
from backup_management.tasks import cleanup_expired_backups


def _make_record(backup_type=BACKUP_TYPE_DATABASE_FULL, status=BACKUP_STATUS_COMPLETED, days_ago=35):
    past = timezone.now() - timedelta(days=days_ago)
    return BackupRecord.objects.create(
        backup_type=backup_type,
        storage_provider=STORAGE_PROVIDER_LOCAL,
        storage_location="/backups",
        file_name=f"backup_{backup_type}_{days_ago}d.pgdump",
        status=status,
        started_at=past,
        completed_at=past,
        retention_until=past,  # already past retention
        encryption_status=ENCRYPTION_STATUS_ENCRYPTED,
    )


class CleanupExpiredBackupsTest(TestCase):

    def test_dry_run_does_not_modify_records(self):
        record = _make_record()
        pk = record.pk
        cleanup_expired_backups.apply(kwargs={"dry_run": True})
        record.refresh_from_db()
        # Status must NOT have changed in dry_run mode
        self.assertNotEqual(record.status, BACKUP_STATUS_EXPIRED)

    def test_execute_marks_expired(self):
        record = _make_record()
        pk = record.pk
        cleanup_expired_backups.apply(kwargs={"dry_run": False})
        record.refresh_from_db()
        self.assertEqual(record.status, BACKUP_STATUS_EXPIRED)

    def test_last_verified_backup_never_expired(self):
        """The most recent VERIFIED backup of each type must be preserved."""
        verified_record = _make_record(status=BACKUP_STATUS_VERIFIED)
        # Also create an older completed record that should be expired
        older_record = _make_record(days_ago=60)

        cleanup_expired_backups.apply(kwargs={"dry_run": False})

        verified_record.refresh_from_db()
        older_record.refresh_from_db()

        self.assertNotEqual(verified_record.status, BACKUP_STATUS_EXPIRED, "VERIFIED record must not be expired")
        self.assertEqual(older_record.status, BACKUP_STATUS_EXPIRED, "Old COMPLETED record should be expired")

    def test_multiple_types_protected_independently(self):
        """Each backup_type's last VERIFIED record is independently protected."""
        db_verified = _make_record(backup_type=BACKUP_TYPE_DATABASE_FULL, status=BACKUP_STATUS_VERIFIED)
        media_verified = _make_record(backup_type=BACKUP_TYPE_MEDIA, status=BACKUP_STATUS_VERIFIED)

        cleanup_expired_backups.apply(kwargs={"dry_run": False})

        db_verified.refresh_from_db()
        media_verified.refresh_from_db()

        self.assertNotEqual(db_verified.status, BACKUP_STATUS_EXPIRED)
        self.assertNotEqual(media_verified.status, BACKUP_STATUS_EXPIRED)

    def test_already_expired_records_not_touched(self):
        # Create a record that is already expired
        past = timezone.now() - timedelta(days=40)
        record = BackupRecord.objects.create(
            backup_type=BACKUP_TYPE_DATABASE_FULL,
            storage_provider=STORAGE_PROVIDER_LOCAL,
            storage_location="/backups",
            file_name="old_expired.pgdump",
            status=BACKUP_STATUS_EXPIRED,
            retention_until=past,
            encryption_status=ENCRYPTION_STATUS_ENCRYPTED,
        )
        cleanup_expired_backups.apply(kwargs={"dry_run": False})
        record.refresh_from_db()
        self.assertEqual(record.status, BACKUP_STATUS_EXPIRED)
