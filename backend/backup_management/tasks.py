# =============================================================================
# RestaurantFlow — Backup Management Celery Tasks
# Phase 25
#
# All backup tasks run as Celery tasks so they can be queued independently
# of the web process.  Primary scheduling in production uses the external
# backup container's cron (see deployment/backup/config/crontab); Celery Beat
# entries here support on-demand triggering and integration with Django admin.
#
# External I/O:
#   - subprocess calls to shell backup scripts in deployment/backup/scripts/
#   - filesystem reads for size/checksum
#   - CentralAlert creation on failure
#   - Notification dispatch on completion/failure
#
# Every task:
#   1. Creates a BackupRecord with status=RUNNING.
#   2. Runs the backup subprocess.
#   3. Updates the record to COMPLETED (or FAILED with failure_reason).
#   4. Records file_size and checksum.
#   5. Publishes Prometheus metrics.
#   6. Raises CentralAlert / sends notification.
# =============================================================================

import hashlib
import logging
import os
import subprocess
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("backup_management")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_sha256(path: str) -> str:
    """Return hex SHA-256 digest for the file at path."""
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            sha.update(chunk)
    return sha.hexdigest()


def _file_size(path: str) -> int:
    """Return file size in bytes."""
    return os.path.getsize(path)


def _raise_central_alert(alert_type: str, title: str, message: str, severity: str = "HIGH"):
    """Create a CentralAlert for backup-related failures.

    Silently logs and skips if no Organization exists (e.g. empty database in tests).
    """
    try:
        from central_control.models import CentralAlert
        from central_control.constants import (
            ALERT_OPEN, SOURCE_TYPE_SYSTEM,
        )
        from organizations.models import Organization

        org = Organization.objects.order_by("created_at").first()
        if org is None:
            logger.warning("_raise_central_alert: no Organization found, skipping alert")
            return

        fingerprint = f"backup:{alert_type}:{org.id}"
        CentralAlert.objects.update_or_create(
            organization=org,
            fingerprint=fingerprint,
            status=ALERT_OPEN,
            defaults={
                "alert_type": alert_type,
                "severity": severity,
                "title": title,
                "message": message,
                "source_type": SOURCE_TYPE_SYSTEM,
                "source_id": "backup_management",
                "detected_at": timezone.now(),
            },
        )
        logger.info("CentralAlert raised: type=%s title=%s", alert_type, title)
    except Exception:
        logger.exception("Failed to raise CentralAlert type=%s", alert_type)


def _send_backup_notification(notif_type: str, title: str, message: str, severity: str):
    """Dispatch a system notification.

    Skips silently if no Organization exists (e.g. during tests).
    """
    try:
        from notifications.services import NotificationService
        from notifications.constants import SOURCE_SYSTEM
        from organizations.models import Organization

        org = Organization.objects.order_by("created_at").first()
        if org is None:
            logger.warning("_send_backup_notification: no Organization found, skipping")
            return

        NotificationService.create_notification(
            company=org,
            notification_type=notif_type,
            severity=severity,
            title=title,
            message=message,
            source_type=SOURCE_SYSTEM,
            source_id="backup_management",
        )
    except Exception:
        logger.exception("Failed to dispatch backup notification type=%s", notif_type)


def _run_backup_script(script_name: str, env_overrides: dict = None) -> subprocess.CompletedProcess:
    """Execute a backup shell script and return the CompletedProcess."""
    scripts_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "deployment", "backup", "scripts",
    )
    script_path = os.path.join(scripts_dir, script_name)
    env = {**os.environ}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", script_path],
        capture_output=True,
        text=True,
        timeout=3600,
        env=env,
    )


def _retention_until(backup_type: str) -> object:
    """Return the retention_until datetime for a given backup type."""
    from backup_management.constants import (
        BACKUP_TYPE_DATABASE_FULL,
        BACKUP_TYPE_DATABASE_INCREMENTAL,
        BACKUP_TYPE_DATABASE_WAL,
        BACKUP_TYPE_MEDIA,
        BACKUP_TYPE_CONFIGURATION,
    )
    days_map = {
        BACKUP_TYPE_DATABASE_FULL:        30,
        BACKUP_TYPE_DATABASE_INCREMENTAL: 7,
        BACKUP_TYPE_DATABASE_WAL:         7,
        BACKUP_TYPE_MEDIA:                14,
        BACKUP_TYPE_CONFIGURATION:        90,
    }
    days = days_map.get(backup_type, 30)
    return timezone.now() + timedelta(days=days)


# ---------------------------------------------------------------------------
# Task: run_database_backup
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="backup_management.run_database_backup",
    max_retries=1,
    default_retry_delay=300,
    ignore_result=True,
)
def run_database_backup(self, backup_type: str = "DATABASE_FULL"):
    """Execute a database backup and record the result."""
    from backup_management.models import BackupRecord
    from backup_management.constants import (
        BACKUP_STATUS_RUNNING, BACKUP_STATUS_COMPLETED, BACKUP_STATUS_FAILED,
        STORAGE_PROVIDER_LOCAL,
        ENCRYPTION_STATUS_ENCRYPTED, ENCRYPTION_STATUS_UNENCRYPTED,
    )
    from backup_management.metrics import (
        BACKUP_DURATION_SECONDS, BACKUP_SIZE_BYTES,
        BACKUP_SUCCESS_TOTAL, BACKUP_FAILURE_TOTAL,
        BACKUP_LAST_SUCCESS_TIMESTAMP,
    )
    from central_control.constants import (
        ALERT_TYPE_SYSTEM_HEALTH, SEVERITY_HIGH, SEVERITY_CRITICAL,
    )

    backup_local_dir = os.getenv("BACKUP_LOCAL_DIR", "/tmp/backups")
    s3_bucket = os.getenv("BACKUP_S3_BUCKET", "")
    storage_provider = STORAGE_PROVIDER_LOCAL if not s3_bucket else "S3"

    record = BackupRecord.objects.create(
        backup_type=backup_type,
        storage_provider=storage_provider,
        storage_location=backup_local_dir,
        file_name="",
        status=BACKUP_STATUS_RUNNING,
        started_at=timezone.now(),
        retention_until=_retention_until(backup_type),
        encryption_status=ENCRYPTION_STATUS_ENCRYPTED if os.getenv("BACKUP_ENCRYPTION_KEY") else ENCRYPTION_STATUS_UNENCRYPTED,
    )

    try:
        result = _run_backup_script("backup-database.sh")

        if result.returncode != 0:
            failure_reason = result.stderr[:2000] if result.stderr else "Script exited non-zero"
            record.status = BACKUP_STATUS_FAILED
            record.failure_reason = failure_reason
            record.completed_at = timezone.now()
            record.save(update_fields=["status", "failure_reason", "completed_at", "updated_at"])

            BACKUP_FAILURE_TOTAL.inc(backup_type=backup_type)
            _raise_central_alert(
                alert_type="BACKUP_FAILED",
                title=f"Database backup failed ({backup_type})",
                message=failure_reason[:500],
                severity=SEVERITY_CRITICAL,
            )
            _send_backup_notification(
                notif_type="BACKUP_FAILED",
                title=f"Database backup failed ({backup_type})",
                message=failure_reason[:200],
                severity="CRITICAL",
            )
            return

        # Parse output for file name: script should emit "BACKUP_FILE=<path>"
        backup_file = None
        for line in result.stdout.splitlines():
            if line.startswith("BACKUP_FILE="):
                backup_file = line.split("=", 1)[1].strip()
                break

        file_size = None
        checksum = ""
        if backup_file and os.path.isfile(backup_file):
            file_size = _file_size(backup_file)
            checksum = _compute_sha256(backup_file)

        completed_at = timezone.now()
        duration = (completed_at - record.started_at).total_seconds()

        record.status = BACKUP_STATUS_COMPLETED
        record.completed_at = completed_at
        record.file_name = os.path.basename(backup_file) if backup_file else ""
        record.storage_location = os.path.dirname(backup_file) if backup_file else backup_local_dir
        record.file_size = file_size
        record.checksum = checksum
        record.save(update_fields=[
            "status", "completed_at", "file_name", "storage_location",
            "file_size", "checksum", "updated_at",
        ])

        BACKUP_SUCCESS_TOTAL.inc(backup_type=backup_type)
        BACKUP_LAST_SUCCESS_TIMESTAMP.set(timezone.now().timestamp(), backup_type=backup_type)
        BACKUP_DURATION_SECONDS.observe(duration, backup_type=backup_type, storage_provider=storage_provider)
        if file_size:
            BACKUP_SIZE_BYTES.set(file_size, backup_type=backup_type)

        _send_backup_notification(
            notif_type="BACKUP_COMPLETED",
            title=f"Database backup completed ({backup_type})",
            message=f"Backup {record.file_name} completed in {duration:.0f}s.",
            severity="INFO",
        )
        logger.info("Database backup completed: type=%s file=%s size=%s", backup_type, record.file_name, file_size)

    except Exception as exc:
        record.status = BACKUP_STATUS_FAILED
        record.failure_reason = str(exc)[:2000]
        record.completed_at = timezone.now()
        record.save(update_fields=["status", "failure_reason", "completed_at", "updated_at"])

        BACKUP_FAILURE_TOTAL.inc(backup_type=backup_type)
        _raise_central_alert(
            alert_type="BACKUP_FAILED",
            title=f"Database backup exception ({backup_type})",
            message=str(exc)[:500],
            severity=SEVERITY_CRITICAL,
        )
        logger.exception("Database backup task exception: type=%s", backup_type)
        raise


# ---------------------------------------------------------------------------
# Task: run_media_backup
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="backup_management.run_media_backup",
    max_retries=1,
    default_retry_delay=300,
    ignore_result=True,
)
def run_media_backup(self):
    """Execute a media files backup and record the result."""
    from backup_management.models import BackupRecord
    from backup_management.constants import (
        BACKUP_TYPE_MEDIA,
        BACKUP_STATUS_RUNNING, BACKUP_STATUS_COMPLETED, BACKUP_STATUS_FAILED,
        STORAGE_PROVIDER_LOCAL, ENCRYPTION_STATUS_ENCRYPTED, ENCRYPTION_STATUS_UNENCRYPTED,
    )
    from backup_management.metrics import (
        BACKUP_DURATION_SECONDS, BACKUP_SIZE_BYTES,
        BACKUP_SUCCESS_TOTAL, BACKUP_FAILURE_TOTAL,
        BACKUP_LAST_SUCCESS_TIMESTAMP,
    )
    from central_control.constants import SEVERITY_CRITICAL

    backup_local_dir = os.getenv("BACKUP_LOCAL_DIR", "/tmp/backups")
    s3_bucket = os.getenv("BACKUP_S3_BUCKET", "")
    storage_provider = STORAGE_PROVIDER_LOCAL if not s3_bucket else "S3"

    record = BackupRecord.objects.create(
        backup_type=BACKUP_TYPE_MEDIA,
        storage_provider=storage_provider,
        storage_location=backup_local_dir,
        file_name="",
        status=BACKUP_STATUS_RUNNING,
        started_at=timezone.now(),
        retention_until=_retention_until(BACKUP_TYPE_MEDIA),
        encryption_status=ENCRYPTION_STATUS_ENCRYPTED if os.getenv("BACKUP_ENCRYPTION_KEY") else ENCRYPTION_STATUS_UNENCRYPTED,
    )

    try:
        result = _run_backup_script("backup-media.sh")

        if result.returncode != 0:
            failure_reason = result.stderr[:2000] if result.stderr else "Script exited non-zero"
            record.status = BACKUP_STATUS_FAILED
            record.failure_reason = failure_reason
            record.completed_at = timezone.now()
            record.save(update_fields=["status", "failure_reason", "completed_at", "updated_at"])

            BACKUP_FAILURE_TOTAL.inc(backup_type=BACKUP_TYPE_MEDIA)
            _raise_central_alert(
                alert_type="BACKUP_FAILED",
                title="Media backup failed",
                message=failure_reason[:500],
                severity=SEVERITY_CRITICAL,
            )
            _send_backup_notification(
                notif_type="BACKUP_FAILED",
                title="Media backup failed",
                message=failure_reason[:200],
                severity="HIGH",
            )
            return

        backup_file = None
        for line in result.stdout.splitlines():
            if line.startswith("BACKUP_FILE="):
                backup_file = line.split("=", 1)[1].strip()
                break

        file_size = None
        checksum = ""
        if backup_file and os.path.isfile(backup_file):
            file_size = _file_size(backup_file)
            checksum = _compute_sha256(backup_file)

        completed_at = timezone.now()
        duration = (completed_at - record.started_at).total_seconds()

        record.status = BACKUP_STATUS_COMPLETED
        record.completed_at = completed_at
        record.file_name = os.path.basename(backup_file) if backup_file else ""
        record.file_size = file_size
        record.checksum = checksum
        record.save(update_fields=[
            "status", "completed_at", "file_name", "file_size", "checksum", "updated_at",
        ])

        BACKUP_SUCCESS_TOTAL.inc(backup_type=BACKUP_TYPE_MEDIA)
        BACKUP_LAST_SUCCESS_TIMESTAMP.set(timezone.now().timestamp(), backup_type=BACKUP_TYPE_MEDIA)
        BACKUP_DURATION_SECONDS.observe(duration, backup_type=BACKUP_TYPE_MEDIA, storage_provider=storage_provider)
        if file_size:
            BACKUP_SIZE_BYTES.set(file_size, backup_type=BACKUP_TYPE_MEDIA)

        _send_backup_notification(
            notif_type="BACKUP_COMPLETED",
            title="Media backup completed",
            message=f"Backup {record.file_name} completed in {duration:.0f}s.",
            severity="INFO",
        )

    except Exception as exc:
        record.status = BACKUP_STATUS_FAILED
        record.failure_reason = str(exc)[:2000]
        record.completed_at = timezone.now()
        record.save(update_fields=["status", "failure_reason", "completed_at", "updated_at"])
        BACKUP_FAILURE_TOTAL.inc(backup_type=BACKUP_TYPE_MEDIA)
        _raise_central_alert(
            alert_type="BACKUP_FAILED",
            title="Media backup exception",
            message=str(exc)[:500],
            severity=SEVERITY_CRITICAL,
        )
        logger.exception("Media backup task exception")
        raise


# ---------------------------------------------------------------------------
# Task: run_configuration_backup
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="backup_management.run_configuration_backup",
    max_retries=1,
    default_retry_delay=300,
    ignore_result=True,
)
def run_configuration_backup(self):
    """Execute a configuration files backup and record the result."""
    from backup_management.models import BackupRecord
    from backup_management.constants import (
        BACKUP_TYPE_CONFIGURATION,
        BACKUP_STATUS_RUNNING, BACKUP_STATUS_COMPLETED, BACKUP_STATUS_FAILED,
        STORAGE_PROVIDER_LOCAL, ENCRYPTION_STATUS_UNENCRYPTED,
    )
    from backup_management.metrics import (
        BACKUP_DURATION_SECONDS, BACKUP_SIZE_BYTES,
        BACKUP_SUCCESS_TOTAL, BACKUP_FAILURE_TOTAL,
        BACKUP_LAST_SUCCESS_TIMESTAMP,
    )
    from central_control.constants import SEVERITY_HIGH

    backup_local_dir = os.getenv("BACKUP_LOCAL_DIR", "/tmp/backups")

    record = BackupRecord.objects.create(
        backup_type=BACKUP_TYPE_CONFIGURATION,
        storage_provider=STORAGE_PROVIDER_LOCAL,
        storage_location=backup_local_dir,
        file_name="",
        status=BACKUP_STATUS_RUNNING,
        started_at=timezone.now(),
        retention_until=_retention_until(BACKUP_TYPE_CONFIGURATION),
        encryption_status=ENCRYPTION_STATUS_UNENCRYPTED,
    )

    try:
        result = _run_backup_script("backup-configuration.sh")

        if result.returncode != 0:
            failure_reason = result.stderr[:2000] if result.stderr else "Script exited non-zero"
            record.status = BACKUP_STATUS_FAILED
            record.failure_reason = failure_reason
            record.completed_at = timezone.now()
            record.save(update_fields=["status", "failure_reason", "completed_at", "updated_at"])

            BACKUP_FAILURE_TOTAL.inc(backup_type=BACKUP_TYPE_CONFIGURATION)
            _raise_central_alert(
                alert_type="BACKUP_FAILED",
                title="Configuration backup failed",
                message=failure_reason[:500],
                severity=SEVERITY_HIGH,
            )
            return

        backup_file = None
        for line in result.stdout.splitlines():
            if line.startswith("BACKUP_FILE="):
                backup_file = line.split("=", 1)[1].strip()
                break

        file_size = None
        checksum = ""
        if backup_file and os.path.isfile(backup_file):
            file_size = _file_size(backup_file)
            checksum = _compute_sha256(backup_file)

        completed_at = timezone.now()
        duration = (completed_at - record.started_at).total_seconds()

        record.status = BACKUP_STATUS_COMPLETED
        record.completed_at = completed_at
        record.file_name = os.path.basename(backup_file) if backup_file else ""
        record.file_size = file_size
        record.checksum = checksum
        record.save(update_fields=[
            "status", "completed_at", "file_name", "file_size", "checksum", "updated_at",
        ])

        BACKUP_SUCCESS_TOTAL.inc(backup_type=BACKUP_TYPE_CONFIGURATION)
        BACKUP_LAST_SUCCESS_TIMESTAMP.set(timezone.now().timestamp(), backup_type=BACKUP_TYPE_CONFIGURATION)
        BACKUP_DURATION_SECONDS.observe(duration, backup_type=BACKUP_TYPE_CONFIGURATION, storage_provider=STORAGE_PROVIDER_LOCAL)
        if file_size:
            BACKUP_SIZE_BYTES.set(file_size, backup_type=BACKUP_TYPE_CONFIGURATION)

    except Exception as exc:
        record.status = BACKUP_STATUS_FAILED
        record.failure_reason = str(exc)[:2000]
        record.completed_at = timezone.now()
        record.save(update_fields=["status", "failure_reason", "completed_at", "updated_at"])
        BACKUP_FAILURE_TOTAL.inc(backup_type=BACKUP_TYPE_CONFIGURATION)
        logger.exception("Configuration backup task exception")
        raise


# ---------------------------------------------------------------------------
# Task: verify_backup
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="backup_management.verify_backup",
    max_retries=0,
    ignore_result=True,
)
def verify_backup(self, backup_record_id: str):
    """Re-verify the checksum of a completed backup and mark it VERIFIED."""
    from backup_management.models import BackupRecord
    from backup_management.constants import (
        BACKUP_STATUS_COMPLETED, BACKUP_STATUS_VERIFIED,
    )
    from central_control.constants import SEVERITY_HIGH

    try:
        record = BackupRecord.objects.get(pk=backup_record_id)
    except BackupRecord.DoesNotExist:
        logger.warning("verify_backup: BackupRecord %s not found", backup_record_id)
        return

    if record.status not in (BACKUP_STATUS_COMPLETED, BACKUP_STATUS_VERIFIED):
        logger.info("verify_backup: record %s has status %s, skipping", backup_record_id, record.status)
        return

    # Build expected file path from storage_location + file_name
    file_path = os.path.join(record.storage_location, record.file_name)

    if not os.path.isfile(file_path):
        logger.warning("verify_backup: file not found at %s", file_path)
        _raise_central_alert(
            alert_type="BACKUP_NOT_VERIFIED",
            title=f"Backup file not found during verification",
            message=f"File {file_path} for record {backup_record_id} does not exist.",
            severity=SEVERITY_HIGH,
        )
        return

    actual_checksum = _compute_sha256(file_path)
    if actual_checksum != record.checksum:
        _raise_central_alert(
            alert_type="BACKUP_NOT_VERIFIED",
            title="Backup checksum mismatch",
            message=(
                f"Record {backup_record_id}: expected {record.checksum[:16]}... "
                f"got {actual_checksum[:16]}..."
            ),
            severity=SEVERITY_HIGH,
        )
        logger.error(
            "Backup checksum mismatch: record=%s expected=%s actual=%s",
            backup_record_id, record.checksum, actual_checksum,
        )
        return

    record.status = BACKUP_STATUS_VERIFIED
    record.verified_at = timezone.now()
    record.save(update_fields=["status", "verified_at", "updated_at"])
    logger.info("Backup verified: record=%s file=%s", backup_record_id, file_path)


# ---------------------------------------------------------------------------
# Task: cleanup_expired_backups
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="backup_management.cleanup_expired_backups",
    max_retries=0,
    ignore_result=True,
)
def cleanup_expired_backups(self, dry_run: bool = True):
    """
    Mark BackupRecords as EXPIRED when their retention_until has passed.

    Dry-run mode (default) only logs what would be expired; it does not
    modify any records.  Pass dry_run=False to execute.

    Safety: the last VERIFIED backup of each type is NEVER expired,
    regardless of its retention_until date.
    """
    from backup_management.models import BackupRecord
    from backup_management.constants import (
        BACKUP_STATUS_EXPIRED, BACKUP_STATUS_VERIFIED,
        BACKUP_TYPE_CHOICES,
    )

    now = timezone.now()
    expired_count = 0

    # Find the last VERIFIED record for each backup_type to protect it.
    protected_ids = set()
    for backup_type, _ in BACKUP_TYPE_CHOICES:
        last_verified = (
            BackupRecord.objects
            .filter(backup_type=backup_type, status=BACKUP_STATUS_VERIFIED)
            .order_by("-created_at")
            .values_list("id", flat=True)
            .first()
        )
        if last_verified:
            protected_ids.add(str(last_verified))

    candidates = BackupRecord.objects.filter(
        retention_until__lt=now,
    ).exclude(
        status=BACKUP_STATUS_EXPIRED,
    ).exclude(
        id__in=protected_ids,
    )

    for record in candidates:
        if dry_run:
            logger.info(
                "cleanup_expired_backups [dry_run]: would expire record=%s type=%s file=%s",
                record.id, record.backup_type, record.file_name,
            )
        else:
            record.status = BACKUP_STATUS_EXPIRED
            record.save(update_fields=["status", "updated_at"])
            logger.info(
                "cleanup_expired_backups: expired record=%s type=%s file=%s",
                record.id, record.backup_type, record.file_name,
            )
        expired_count += 1

    logger.info(
        "cleanup_expired_backups: dry_run=%s expired_count=%d protected_ids=%d",
        dry_run, expired_count, len(protected_ids),
    )


# ---------------------------------------------------------------------------
# Task: check_backup_staleness
# ---------------------------------------------------------------------------

@shared_task(
    bind=True,
    name="backup_management.check_backup_staleness",
    max_retries=0,
    ignore_result=True,
)
def check_backup_staleness(self):
    """
    Check whether any backup type has gone stale (no COMPLETED/VERIFIED
    record in the last BACKUP_STALENESS_HOURS hours).

    Raises a CentralAlert(BACKUP_STALE) for each stale backup type.
    Also sends a notification for operator awareness.
    """
    from backup_management.models import BackupRecord
    from backup_management.constants import (
        BACKUP_TYPE_CHOICES, BACKUP_HEALTHY_STATUSES, BACKUP_STALENESS_HOURS,
    )
    from central_control.constants import SEVERITY_HIGH

    cutoff = timezone.now() - timedelta(hours=BACKUP_STALENESS_HOURS)

    for backup_type, label in BACKUP_TYPE_CHOICES:
        recent = BackupRecord.objects.filter(
            backup_type=backup_type,
            status__in=BACKUP_HEALTHY_STATUSES,
            completed_at__gte=cutoff,
        ).exists()

        if not recent:
            logger.warning("Backup stale: type=%s no healthy backup since %s", backup_type, cutoff)
            _raise_central_alert(
                alert_type="BACKUP_STALE",
                title=f"Backup stale: {label}",
                message=(
                    f"No completed or verified {label} backup in the last "
                    f"{BACKUP_STALENESS_HOURS} hours."
                ),
                severity=SEVERITY_HIGH,
            )
            _send_backup_notification(
                notif_type="BACKUP_STALE",
                title=f"Backup stale: {label}",
                message=f"No healthy {label} backup since {cutoff.isoformat()}.",
                severity="HIGH",
            )
