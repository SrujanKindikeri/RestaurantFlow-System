# =============================================================================
# RestaurantFlow — Backup Management Prometheus Metrics
# Phase 25
#
# Uses the same custom metrics registry as the observability app (Phase 24).
# All metric instances are module-level singletons.  Labels are intentionally
# low-cardinality: backup_type, storage_provider, restore_type.
#
# NEVER use user IDs, file names, or free-text strings as label values.
# =============================================================================

from observability.metrics import Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# Backup duration (seconds)
# ---------------------------------------------------------------------------
BACKUP_DURATION_SECONDS = Histogram(
    name="restaurantflow_backup_duration_seconds",
    help="Time taken to complete a backup operation in seconds.",
    buckets=[30, 60, 120, 300, 600, 1200, 1800, 3600],
    label_names=["backup_type", "storage_provider"],
)

# ---------------------------------------------------------------------------
# Backup file size (bytes)
# ---------------------------------------------------------------------------
BACKUP_SIZE_BYTES = Gauge(
    name="restaurantflow_backup_size_bytes",
    help="Size of the most recent successful backup in bytes.",
    label_names=["backup_type"],
)

# ---------------------------------------------------------------------------
# Backup success/failure counters
# ---------------------------------------------------------------------------
BACKUP_SUCCESS_TOTAL = Counter(
    name="restaurantflow_backup_success_total",
    help="Total number of successful backup operations.",
    label_names=["backup_type"],
)

BACKUP_FAILURE_TOTAL = Counter(
    name="restaurantflow_backup_failure_total",
    help="Total number of failed backup operations.",
    label_names=["backup_type"],
)

# ---------------------------------------------------------------------------
# Last successful backup timestamp (Unix epoch seconds)
# ---------------------------------------------------------------------------
BACKUP_LAST_SUCCESS_TIMESTAMP = Gauge(
    name="restaurantflow_backup_last_success_timestamp",
    help="Unix timestamp of the last successful backup for each backup_type.",
    label_names=["backup_type"],
)

# ---------------------------------------------------------------------------
# Restore duration (seconds)
# ---------------------------------------------------------------------------
RESTORE_DURATION_SECONDS = Histogram(
    name="restaurantflow_restore_duration_seconds",
    help="Time taken to complete a restore operation in seconds.",
    buckets=[30, 60, 120, 300, 600, 1200, 1800, 7200],
    label_names=["restore_type"],
)

# ---------------------------------------------------------------------------
# Restore test success (1 = pass, 0 = fail/not tested)
# ---------------------------------------------------------------------------
RESTORE_TEST_SUCCESS = Gauge(
    name="restaurantflow_restore_test_success",
    help="1 if the most recent restore test passed, 0 otherwise.",
    label_names=["restore_type"],
)

# ---------------------------------------------------------------------------
# Backup storage available bytes
# ---------------------------------------------------------------------------
BACKUP_STORAGE_BYTES = Gauge(
    name="restaurantflow_backup_storage_bytes",
    help="Available storage bytes on the backup storage backend.",
    label_names=["storage_provider"],
)
