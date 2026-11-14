# =============================================================================
# RestaurantFlow — Backup Verification Tests
# Phase 25
# =============================================================================

import hashlib
import os
import tempfile
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from backup_management.models import BackupRecord
from backup_management.constants import (
    BACKUP_TYPE_DATABASE_FULL,
    BACKUP_STATUS_COMPLETED,
    BACKUP_STATUS_VERIFIED,
    STORAGE_PROVIDER_LOCAL,
    ENCRYPTION_STATUS_ENCRYPTED,
)
from backup_management.tasks import _compute_sha256, verify_backup


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _make_completed_record(file_path: str, checksum: str):
    return BackupRecord.objects.create(
        backup_type=BACKUP_TYPE_DATABASE_FULL,
        storage_provider=STORAGE_PROVIDER_LOCAL,
        storage_location=os.path.dirname(file_path),
        file_name=os.path.basename(file_path),
        status=BACKUP_STATUS_COMPLETED,
        started_at=timezone.now(),
        completed_at=timezone.now(),
        checksum=checksum,
        encryption_status=ENCRYPTION_STATUS_ENCRYPTED,
    )


class ChecksumVerificationTest(TestCase):

    def test_valid_checksum_passes(self):
        data = b"database backup content"
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(data)
            path = f.name
        try:
            expected = _sha256(data)
            actual = _compute_sha256(path)
            self.assertEqual(expected, actual)
        finally:
            os.unlink(path)

    def test_tampered_file_gives_different_checksum(self):
        original_data = b"original backup content"
        tampered_data = b"tampered content XXXXXXX"
        self.assertNotEqual(_sha256(original_data), _sha256(tampered_data))


class VerifyBackupTaskTest(TestCase):

    def test_valid_backup_marked_verified(self):
        data = b"valid backup file content"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pgdump") as f:
            f.write(data)
            path = f.name
        try:
            checksum = _sha256(data)
            record = _make_completed_record(path, checksum)
            verify_backup.apply(args=[str(record.id)])
            record.refresh_from_db()
            self.assertEqual(record.status, BACKUP_STATUS_VERIFIED)
            self.assertIsNotNone(record.verified_at)
        finally:
            os.unlink(path)

    @patch("backup_management.tasks._raise_central_alert")
    def test_checksum_mismatch_raises_alert(self, mock_alert):
        data = b"real backup content"
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pgdump") as f:
            f.write(data)
            path = f.name
        try:
            wrong_checksum = _sha256(b"different content entirely")
            record = _make_completed_record(path, wrong_checksum)
            verify_backup.apply(args=[str(record.id)])
            # Status should NOT be VERIFIED
            record.refresh_from_db()
            self.assertNotEqual(record.status, BACKUP_STATUS_VERIFIED)
            mock_alert.assert_called_once()
        finally:
            os.unlink(path)

    @patch("backup_management.tasks._raise_central_alert")
    def test_missing_file_raises_alert(self, mock_alert):
        record = _make_completed_record(
            file_path="/tmp/nonexistent_backup_file.pgdump",
            checksum="doesnotmatter",
        )
        verify_backup.apply(args=[str(record.id)])
        mock_alert.assert_called_once()

    def test_nonexistent_record_does_not_raise(self):
        import uuid
        # Should log and return without error
        verify_backup.apply(args=[str(uuid.uuid4())])
