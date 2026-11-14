# =============================================================================
# RestaurantFlow — Backup Management Constants
# Phase 25
#
# All permission codes and choice constants for the backup_management app.
# Never hard-code these values in models, views, or tasks — import from here.
# =============================================================================

# ---------------------------------------------------------------------------
# Backup type choices
# ---------------------------------------------------------------------------
BACKUP_TYPE_DATABASE_FULL        = "DATABASE_FULL"
BACKUP_TYPE_DATABASE_INCREMENTAL = "DATABASE_INCREMENTAL"
BACKUP_TYPE_DATABASE_WAL         = "DATABASE_WAL"
BACKUP_TYPE_MEDIA                = "MEDIA"
BACKUP_TYPE_CONFIGURATION        = "CONFIGURATION"
BACKUP_TYPE_APPLICATION_METADATA = "APPLICATION_METADATA"

BACKUP_TYPE_CHOICES = [
    (BACKUP_TYPE_DATABASE_FULL,        "Database Full"),
    (BACKUP_TYPE_DATABASE_INCREMENTAL, "Database Incremental"),
    (BACKUP_TYPE_DATABASE_WAL,         "Database WAL"),
    (BACKUP_TYPE_MEDIA,                "Media"),
    (BACKUP_TYPE_CONFIGURATION,        "Configuration"),
    (BACKUP_TYPE_APPLICATION_METADATA, "Application Metadata"),
]

# ---------------------------------------------------------------------------
# Backup status choices
# ---------------------------------------------------------------------------
BACKUP_STATUS_PENDING   = "PENDING"
BACKUP_STATUS_RUNNING   = "RUNNING"
BACKUP_STATUS_COMPLETED = "COMPLETED"
BACKUP_STATUS_VERIFIED  = "VERIFIED"
BACKUP_STATUS_FAILED    = "FAILED"
BACKUP_STATUS_EXPIRED   = "EXPIRED"

BACKUP_STATUS_CHOICES = [
    (BACKUP_STATUS_PENDING,   "Pending"),
    (BACKUP_STATUS_RUNNING,   "Running"),
    (BACKUP_STATUS_COMPLETED, "Completed"),
    (BACKUP_STATUS_VERIFIED,  "Verified"),
    (BACKUP_STATUS_FAILED,    "Failed"),
    (BACKUP_STATUS_EXPIRED,   "Expired"),
]

# Statuses considered "healthy" (backup completed successfully)
BACKUP_HEALTHY_STATUSES = {BACKUP_STATUS_COMPLETED, BACKUP_STATUS_VERIFIED}

# ---------------------------------------------------------------------------
# Storage provider choices
# ---------------------------------------------------------------------------
STORAGE_PROVIDER_LOCAL = "LOCAL"
STORAGE_PROVIDER_S3    = "S3"
STORAGE_PROVIDER_GCS   = "GCS"
STORAGE_PROVIDER_AZURE = "AZURE"
STORAGE_PROVIDER_SFTP  = "SFTP"

STORAGE_PROVIDER_CHOICES = [
    (STORAGE_PROVIDER_LOCAL, "Local"),
    (STORAGE_PROVIDER_S3,    "Amazon S3"),
    (STORAGE_PROVIDER_GCS,   "Google Cloud Storage"),
    (STORAGE_PROVIDER_AZURE, "Azure Blob Storage"),
    (STORAGE_PROVIDER_SFTP,  "SFTP"),
]

# ---------------------------------------------------------------------------
# Encryption status choices
# ---------------------------------------------------------------------------
ENCRYPTION_STATUS_ENCRYPTED   = "ENCRYPTED"
ENCRYPTION_STATUS_UNENCRYPTED = "UNENCRYPTED"
ENCRYPTION_STATUS_UNKNOWN     = "UNKNOWN"

ENCRYPTION_STATUS_CHOICES = [
    (ENCRYPTION_STATUS_ENCRYPTED,   "Encrypted"),
    (ENCRYPTION_STATUS_UNENCRYPTED, "Unencrypted"),
    (ENCRYPTION_STATUS_UNKNOWN,     "Unknown"),
]

# ---------------------------------------------------------------------------
# Permission codenames
# ---------------------------------------------------------------------------
PERM_VIEW_BACKUP_STATUS          = "backup_management.view_backup_status"
PERM_VIEW_BACKUP_HISTORY         = "backup_management.view_backup_history"
PERM_CREATE_BACKUP               = "backup_management.create_backup"
PERM_VERIFY_BACKUP               = "backup_management.verify_backup"
PERM_REQUEST_RESTORE             = "backup_management.request_restore"
PERM_APPROVE_RESTORE             = "backup_management.approve_restore"
PERM_MANAGE_RETENTION            = "backup_management.manage_retention"
PERM_MANAGE_BACKUP_CONFIGURATION = "backup_management.manage_backup_configuration"

ALL_BACKUP_PERMISSIONS = [
    (PERM_VIEW_BACKUP_STATUS,          "View Backup Status"),
    (PERM_VIEW_BACKUP_HISTORY,         "View Backup History"),
    (PERM_CREATE_BACKUP,               "Create Backup"),
    (PERM_VERIFY_BACKUP,               "Verify Backup"),
    (PERM_REQUEST_RESTORE,             "Request Restore"),
    (PERM_APPROVE_RESTORE,             "Approve Restore"),
    (PERM_MANAGE_RETENTION,            "Manage Retention Policy"),
    (PERM_MANAGE_BACKUP_CONFIGURATION, "Manage Backup Configuration"),
]

# ---------------------------------------------------------------------------
# Staleness threshold: alert if no healthy backup within this window
# ---------------------------------------------------------------------------
BACKUP_STALENESS_HOURS = 25

# ---------------------------------------------------------------------------
# Storage low threshold (bytes remaining below which an alert fires)
# ---------------------------------------------------------------------------
BACKUP_STORAGE_LOW_BYTES = 5 * 1024 * 1024 * 1024  # 5 GB
