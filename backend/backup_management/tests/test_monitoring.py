# =============================================================================
# RestaurantFlow — Backup Prometheus Metrics Tests
# Phase 25
# =============================================================================

from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings


CELERY_SETTINGS = {
    "CELERY_TASK_ALWAYS_EAGER": True,
    "CELERY_TASK_EAGER_PROPAGATES": True,
}


def _make_success_result(path="/tmp/backups/db.pgdump.gz.gpg"):
    r = MagicMock()
    r.returncode = 0
    r.stdout = f"BACKUP_FILE={path}\n"
    r.stderr = ""
    return r


def _make_failure_result():
    r = MagicMock()
    r.returncode = 1
    r.stdout = ""
    r.stderr = "backup failed"
    return r


@override_settings(**CELERY_SETTINGS)
class BackupMetricsTest(TestCase):
    """
    Tests that Prometheus counters and gauges are updated correctly.
    Uses the module-level metric singletons from backup_management.metrics.
    """

    def _get_metrics(self):
        from backup_management import metrics as m
        return m

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=1024 * 1024)
    @patch("backup_management.tasks._compute_sha256", return_value="deadbeef")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_success_increments_success_counter(
        self, mock_run, mock_isfile, mock_sha, mock_size, mock_notify, mock_alert
    ):
        mock_run.return_value = _make_success_result()
        m = self._get_metrics()
        before = m.BACKUP_SUCCESS_TOTAL.get(backup_type="DATABASE_FULL")

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        after = m.BACKUP_SUCCESS_TOTAL.get(backup_type="DATABASE_FULL")
        self.assertGreater(after, before)

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=1024 * 1024)
    @patch("backup_management.tasks._compute_sha256", return_value="deadbeef")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_success_does_not_increment_failure_counter(
        self, mock_run, mock_isfile, mock_sha, mock_size, mock_notify, mock_alert
    ):
        mock_run.return_value = _make_success_result()
        m = self._get_metrics()
        before = m.BACKUP_FAILURE_TOTAL.get(backup_type="DATABASE_FULL")

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        after = m.BACKUP_FAILURE_TOTAL.get(backup_type="DATABASE_FULL")
        self.assertEqual(after, before)

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._run_backup_script")
    def test_failure_increments_failure_counter(self, mock_run, mock_notify, mock_alert):
        mock_run.return_value = _make_failure_result()
        m = self._get_metrics()
        before = m.BACKUP_FAILURE_TOTAL.get(backup_type="DATABASE_FULL")

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        after = m.BACKUP_FAILURE_TOTAL.get(backup_type="DATABASE_FULL")
        self.assertGreater(after, before)

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=52428800)
    @patch("backup_management.tasks._compute_sha256", return_value="sizechecksum")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_success_sets_size_gauge(
        self, mock_run, mock_isfile, mock_sha, mock_size, mock_notify, mock_alert
    ):
        mock_run.return_value = _make_success_result()
        m = self._get_metrics()

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        value = m.BACKUP_SIZE_BYTES.get(backup_type="DATABASE_FULL")
        self.assertEqual(value, 52428800.0)

    @patch("backup_management.tasks._raise_central_alert")
    @patch("backup_management.tasks._send_backup_notification")
    @patch("backup_management.tasks._file_size", return_value=1024)
    @patch("backup_management.tasks._compute_sha256", return_value="ts_check")
    @patch("os.path.isfile", return_value=True)
    @patch("backup_management.tasks._run_backup_script")
    def test_success_sets_last_success_timestamp(
        self, mock_run, mock_isfile, mock_sha, mock_size, mock_notify, mock_alert
    ):
        mock_run.return_value = _make_success_result()
        m = self._get_metrics()

        from backup_management.tasks import run_database_backup
        run_database_backup.apply(args=["DATABASE_FULL"])

        ts = m.BACKUP_LAST_SUCCESS_TIMESTAMP.get(backup_type="DATABASE_FULL")
        self.assertGreater(ts, 0)
