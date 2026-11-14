# =============================================================================
# RestaurantFlow — Backup Central Control Integration Tests
# Phase 25
# =============================================================================

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings

from backup_management.constants import (
    BACKUP_TYPE_DATABASE_FULL,
    BACKUP_STATUS_COMPLETED,
    STORAGE_PROVIDER_LOCAL,
    ENCRYPTION_STATUS_ENCRYPTED,
)
from backup_management.models import BackupRecord


CELERY_SETTINGS = {
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": True,
}


def _make_failure_result():
    r = MagicMock()
    r.returncode = 1
    r.stdout = ""
    r.stderr = "pg_dump: could not connect to database"
    return r


def _make_success_result():
    r = MagicMock()
    r.returncode = 0
    r.stdout = "BACKUP_FILE=/tmp/backups/db.pgdump.gz.gpg\n"
    r.stderr = ""
    return r


@override_settings(**CELERY_SETTINGS)
class BackupFailureAlertTest(TestCase):

    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._run_backup_script")
    def test_central_alert_raised_on_backup_failure(self, mock_run, mock_alert, mock_notify):
        mock_run.return_value = _make_failure_result()

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        mock_alert.assert_called_once()
        call_kwargs = mock_alert.call_args.kwargs
        self.assertEqual(call_kwargs["alert_type"], "BACKUP_FAILED")

    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._file_size", return_value=1024)
    @patch("backup_management.tasks._compute_sha256", return_value="abc123")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_no_alert_on_backup_success(
        self, mock_run, mock_isfile, mock_sha, mock_size, mock_alert, mock_notify
    ):
        mock_run.return_value = _make_success_result()

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        mock_alert.assert_not_called()


@override_settings(**CELERY_SETTINGS)
class BackupStalenessAlertTest(TestCase):

    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._raise_central_alert")
    def test_staleness_alert_raised_when_no_recent_backup(self, mock_alert, mock_notify):
        # No BackupRecord exists → all types are stale
        from backup_management.tasks import check_backup_staleness
        check_backup_staleness.apply()
        # Should have raised at least one BACKUP_STALE alert
        self.assertTrue(mock_alert.called)
        alert_types = [call.kwargs.get("alert_type") for call in mock_alert.call_args_list]
        self.assertIn("BACKUP_STALE", alert_types)

    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._raise_central_alert")
    def test_no_staleness_alert_when_recent_backup_exists(self, mock_alert, mock_notify):
        from django.utils import timezone
        from datetime import timedelta

        # Create a recent healthy backup for all backup types
        from backup_management.constants import BACKUP_TYPE_CHOICES, BACKUP_STATUS_COMPLETED
        for backup_type, _ in BACKUP_TYPE_CHOICES:
            BackupRecord.objects.create(
                backup_type=backup_type,
                storage_provider=STORAGE_PROVIDER_LOCAL,
                storage_location="/backups",
                file_name=f"{backup_type}_recent.pgdump",
                status=BACKUP_STATUS_COMPLETED,
                completed_at=timezone.now() - timedelta(hours=1),
                started_at=timezone.now() - timedelta(hours=1, minutes=5),
                encryption_status=ENCRYPTION_STATUS_ENCRYPTED,
            )

        from backup_management.tasks import check_backup_staleness
        check_backup_staleness.apply()
        mock_alert.assert_not_called()
