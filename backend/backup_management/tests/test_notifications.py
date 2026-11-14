# =============================================================================
# RestaurantFlow — Backup Notification Tests
# Phase 25
# =============================================================================

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


CELERY_SETTINGS = {
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": True,
}


def _make_success_result():
    r = MagicMock()
    r.returncode = 0
    r.stdout = "BACKUP_FILE=/tmp/backups/db.pgdump.gz.gpg\n"
    r.stderr = ""
    return r


def _make_failure_result():
    r = MagicMock()
    r.returncode = 1
    r.stdout = ""
    r.stderr = "backup failed: connection refused"
    return r


@override_settings(**CELERY_SETTINGS)
class BackupCompletedNotificationTest(TestCase):

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=1024)
    @patch("backup_management.tasks._compute_sha256", return_value="checksum_abc")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_notification_dispatched_on_success(
        self, mock_run, mock_isfile, mock_sha, mock_size, mock_notify, mock_alert
    ):
        mock_run.return_value = _make_success_result()
        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])
        mock_notify.assert_called()
        # The last call should be the COMPLETED notification
        last_call = mock_notify.call_args
        self.assertIn("BACKUP_COMPLETED", last_call.kwargs.get("notif_type", ""))

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._run_backup_script")
    def test_notification_dispatched_on_failure(self, mock_run, mock_notify, mock_alert):
        mock_run.return_value = _make_failure_result()
        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])
        mock_notify.assert_called()
        last_call = mock_notify.call_args
        self.assertIn("BACKUP_FAILED", last_call.kwargs.get("notif_type", ""))


@override_settings(**CELERY_SETTINGS)
class BackupStaleNotificationTest(TestCase):

    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._raise_central_alert")
    def test_notification_dispatched_on_staleness(self, mock_alert, mock_notify):
        from backup_management.tasks import check_backup_staleness
        check_backup_staleness.apply()
        self.assertTrue(mock_notify.called)
        notif_types = [call.kwargs.get("notif_type") for call in mock_notify.call_args_list]
        self.assertTrue(any("BACKUP_STALE" in t for t in notif_types if t))
