# =============================================================================
# RestaurantFlow — Backup Task Tests
# Phase 25
# =============================================================================

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from backup_management.models import BackupRecord
from backup_management.constants import (
    BACKUP_TYPE_DATABASE_FULL,
    BACKUP_TYPE_MEDIA,
    BACKUP_TYPE_CONFIGURATION,
    BACKUP_STATUS_COMPLETED,
    BACKUP_STATUS_FAILED,
    STORAGE_PROVIDER_LOCAL,
)


CELERY_SETTINGS = {
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": True,
}


def _make_success_result(backup_file="/tmp/backups/db.pgdump.gz.gpg"):
    result = MagicMock()
    result.returncode = 0
    result.stdout = f"BACKUP_FILE={backup_file}\n"
    result.stderr = ""
    return result


def _make_failure_result():
    result = MagicMock()
    result.returncode = 1
    result.stdout = ""
    result.stderr = "pg_dump: error: connection failed"
    return result


@override_settings(**CELERY_SETTINGS)
class RunDatabaseBackupTaskTest(TestCase):

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=1024 * 1024)
    @patch("backup_management.tasks._compute_sha256", return_value="abc123def456")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_success_path_creates_completed_record(
        self, mock_run, mock_isfile, mock_sha256, mock_size, mock_notify, mock_alert
    ):
        mock_run.return_value = _make_success_result()

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        record = BackupRecord.objects.order_by("-created_at").first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status, BACKUP_STATUS_COMPLETED)
        self.assertEqual(record.backup_type, BACKUP_TYPE_DATABASE_FULL)
        self.assertEqual(record.checksum, "abc123def456")
        self.assertIsNotNone(record.completed_at)
        mock_alert.assert_not_called()

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._run_backup_script")
    def test_failure_path_creates_failed_record(self, mock_run, mock_notify, mock_alert):
        mock_run.return_value = _make_failure_result()

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        record = BackupRecord.objects.order_by("-created_at").first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status, BACKUP_STATUS_FAILED)
        self.assertIn("pg_dump", record.failure_reason)
        mock_alert.assert_called_once()

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=1024 * 1024)
    @patch("backup_management.tasks._compute_sha256", return_value="abc123def456")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_metrics_updated_on_success(
        self, mock_run, mock_isfile, mock_sha256, mock_size, mock_notify, mock_alert
    ):
        mock_run.return_value = _make_success_result()

        from backup_management.tasks import run_database_backup
        from backup_management.metrics import BACKUP_SUCCESS_TOTAL, BACKUP_FAILURE_TOTAL

        before_success = BACKUP_SUCCESS_TOTAL.get(backup_type=BACKUP_TYPE_DATABASE_FULL)
        before_failure = BACKUP_FAILURE_TOTAL.get(backup_type=BACKUP_TYPE_DATABASE_FULL)

        run_database_backup.apply(args=["DATABASE_FULL"])

        self.assertGreater(
            BACKUP_SUCCESS_TOTAL.get(backup_type=BACKUP_TYPE_DATABASE_FULL),
            before_success,
        )
        self.assertEqual(
            BACKUP_FAILURE_TOTAL.get(backup_type=BACKUP_TYPE_DATABASE_FULL),
            before_failure,
        )

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._run_backup_script")
    def test_metrics_updated_on_failure(self, mock_run, mock_notify, mock_alert):
        mock_run.return_value = _make_failure_result()

        from backup_management.tasks import run_database_backup
        from backup_management.metrics import BACKUP_FAILURE_TOTAL

        before = BACKUP_FAILURE_TOTAL.get(backup_type=BACKUP_TYPE_DATABASE_FULL)
        run_database_backup.apply(args=["DATABASE_FULL"])
        self.assertGreater(BACKUP_FAILURE_TOTAL.get(backup_type=BACKUP_TYPE_DATABASE_FULL), before)


@override_settings(**CELERY_SETTINGS)
class RunMediaBackupTaskTest(TestCase):

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=512 * 1024 * 1024)
    @patch("backup_management.tasks._compute_sha256", return_value="feedbeef1234")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_success_path(self, mock_run, mock_isfile, mock_sha, mock_size, mock_notify, mock_alert):
        mock_run.return_value = _make_success_result("/tmp/backups/media.tar.gz")
        from backup_management.tasks import run_media_backup
        run_media_backup.apply()
        record = BackupRecord.objects.order_by("-created_at").first()
        self.assertEqual(record.status, BACKUP_STATUS_COMPLETED)
        self.assertEqual(record.backup_type, BACKUP_TYPE_MEDIA)

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._run_backup_script")
    def test_failure_path(self, mock_run, mock_notify, mock_alert):
        mock_run.return_value = _make_failure_result()
        from backup_management.tasks import run_media_backup
        run_media_backup.apply()
        record = BackupRecord.objects.order_by("-created_at").first()
        self.assertEqual(record.status, BACKUP_STATUS_FAILED)


@override_settings(**CELERY_SETTINGS)
class RunConfigurationBackupTaskTest(TestCase):

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=1024)
    @patch("backup_management.tasks._compute_sha256", return_value="configchecksum")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_success_path(self, mock_run, mock_isfile, mock_sha, mock_size, mock_notify, mock_alert):
        mock_run.return_value = _make_success_result("/tmp/backups/config.tar.gz")
        from backup_management.tasks import run_configuration_backup
        run_configuration_backup.apply()
        record = BackupRecord.objects.order_by("-created_at").first()
        self.assertEqual(record.status, BACKUP_STATUS_COMPLETED)
        self.assertEqual(record.backup_type, BACKUP_TYPE_CONFIGURATION)
