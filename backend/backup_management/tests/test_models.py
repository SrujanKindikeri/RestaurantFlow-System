# =============================================================================
# RestaurantFlow — Backup Management Model Tests
# Phase 25
# =============================================================================

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from backup_management.models import BackupRecord
from backup_management.constants import (
    BACKUP_TYPE_DATABASE_FULL,
    BACKUP_TYPE_MEDIA,
    BACKUP_STATUS_PENDING,
    BACKUP_STATUS_RUNNING,
    BACKUP_STATUS_COMPLETED,
    BACKUP_STATUS_VERIFIED,
    BACKUP_STATUS_FAILED,
    BACKUP_STATUS_EXPIRED,
    STORAGE_PROVIDER_LOCAL,
    ENCRYPTION_STATUS_ENCRYPTED,
)


def _make_record(**kwargs):
    defaults = {
        "backup_type": BACKUP_TYPE_DATABASE_FULL,
        "storage_provider": STORAGE_PROVIDER_LOCAL,
        "storage_location": "/backups",
        "file_name": "test_backup.pgdump.gz.gpg",
        "status": BACKUP_STATUS_PENDING,
        "encryption_status": ENCRYPTION_STATUS_ENCRYPTED,
    }
    defaults.update(kwargs)
    return BackupRecord.objects.create(**defaults)


class BackupRecordCreationTest(TestCase):

    def test_create_with_required_fields(self):
        record = _make_record()
        self.assertIsNotNone(record.id)
        self.assertEqual(record.backup_type, BACKUP_TYPE_DATABASE_FULL)
        self.assertEqual(record.status, BACKUP_STATUS_PENDING)
        self.assertIsNotNone(record.created_at)
        self.assertIsNotNone(record.updated_at)

    def test_file_size_nullable(self):
        record = _make_record(file_size=None)
        self.assertIsNone(record.file_size)

    def test_file_size_set(self):
        record = _make_record(file_size=1024 * 1024 * 50)
        self.assertEqual(record.file_size, 52428800)

    def test_checksum_blank_by_default(self):
        record = _make_record()
        self.assertEqual(record.checksum, "")

    def test_str_representation(self):
        record = _make_record()
        s = str(record)
        self.assertIn("DATABASE_FULL", s)
        self.assertIn("PENDING", s)


class BackupRecordStatusTransitionTest(TestCase):

    def test_pending_to_running(self):
        record = _make_record(status=BACKUP_STATUS_PENDING)
        record.started_at = timezone.now()
        record.status = BACKUP_STATUS_RUNNING
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.status, BACKUP_STATUS_RUNNING)

    def test_running_to_completed(self):
        record = _make_record(status=BACKUP_STATUS_RUNNING, started_at=timezone.now())
        record.status = BACKUP_STATUS_COMPLETED
        record.completed_at = timezone.now()
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.status, BACKUP_STATUS_COMPLETED)

    def test_completed_to_verified(self):
        record = _make_record(status=BACKUP_STATUS_COMPLETED, completed_at=timezone.now())
        record.status = BACKUP_STATUS_VERIFIED
        record.verified_at = timezone.now()
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.status, BACKUP_STATUS_VERIFIED)

    def test_running_to_failed(self):
        record = _make_record(status=BACKUP_STATUS_RUNNING)
        record.status = BACKUP_STATUS_FAILED
        record.failure_reason = "pg_dump returned exit code 1"
        record.save()
        record.refresh_from_db()
        self.assertEqual(record.status, BACKUP_STATUS_FAILED)
        self.assertIn("pg_dump", record.failure_reason)


class BackupRecordRetentionTest(TestCase):

    def test_retention_until_in_past(self):
        past = timezone.now() - timedelta(days=1)
        record = _make_record(
            status=BACKUP_STATUS_COMPLETED,
            retention_until=past,
        )
        self.assertLess(record.retention_until, timezone.now())

    def test_retention_until_in_future(self):
        future = timezone.now() + timedelta(days=30)
        record = _make_record(
            status=BACKUP_STATUS_COMPLETED,
            retention_until=future,
        )
        self.assertGreater(record.retention_until, timezone.now())


class BackupRecordDurationTest(TestCase):

    def test_duration_seconds_with_both_timestamps(self):
        started = timezone.now()
        completed = started + timedelta(seconds=120)
        record = _make_record(
            status=BACKUP_STATUS_COMPLETED,
            started_at=started,
            completed_at=completed,
        )
        self.assertAlmostEqual(record.duration_seconds, 120.0, places=0)

    def test_duration_seconds_missing_completed(self):
        record = _make_record(started_at=timezone.now())
        self.assertIsNone(record.duration_seconds)

    def test_duration_seconds_no_timestamps(self):
        record = _make_record()
        self.assertIsNone(record.duration_seconds)
