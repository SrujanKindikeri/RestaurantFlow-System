# Backup Architecture — RestaurantFlow

## System Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        RestaurantFlow Infrastructure                     │
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌────────────────────────────┐ │
│  │   Django App  │    │  PostgreSQL  │    │        Redis               │ │
│  │  (Gunicorn)  │    │  postgres_   │    │  redis_data volume         │ │
│  │              │    │  data volume │    │  AOF: appendonly.aof       │ │
│  └──────┬───────┘    └──────┬───────┘    └────────────────────────────┘ │
│         │                   │                                            │
│         │ Celery tasks       │ pg_dump (TCP)                             │
│         ▼                   ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                    Backup Container                               │   │
│  │  (postgres:15-alpine + gpg + aws-cli + supercrond)               │   │
│  │                                                                   │   │
│  │  Cron schedule:                                                   │   │
│  │    02:00 → backup-database.sh                                     │   │
│  │    03:00 → backup-media.sh                                        │   │
│  │    04:00 Sun → backup-configuration.sh                            │   │
│  │    */15 min → disaster-recovery-check.sh                         │   │
│  │                                                                   │   │
│  │  Output: /backups volume (backup_data)                            │   │
│  └───────────────────────────┬──────────────────────────────────────┘   │
│                              │                                           │
│         ┌────────────────────┼────────────────────┐                     │
│         ▼                    ▼                    ▼                     │
│  ┌──────────────┐  ┌───────────────────┐  ┌─────────────┐              │
│  │  Local Volume │  │   Amazon S3       │  │   GCS/Azure │              │
│  │  (backup_data)│  │  (optional)       │  │  (optional) │              │
│  └──────────────┘  └───────────────────┘  └─────────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     Django backup_management App                         │
│                                                                          │
│  BackupRecord model  ──► API views (list, detail, trigger)              │
│         │                                                                │
│         │ Celery tasks (run_database_backup, run_media_backup, etc.)    │
│         │                                                                │
│         ├──► CentralAlert (BACKUP_FAILED, BACKUP_STALE, etc.)           │
│         │                                                                │
│         ├──► NotificationService (operators with backup permissions)    │
│         │                                                                │
│         └──► Prometheus metrics (success_total, failure_total, etc.)    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components

### backup_management Django App

| Component | Purpose |
|-----------|---------|
| `BackupRecord` model | Records every backup operation with status, file info, checksum, timing |
| Celery tasks | `run_database_backup`, `run_media_backup`, `run_configuration_backup`, `verify_backup`, `cleanup_expired_backups`, `check_backup_staleness` |
| API views | Read-only list/detail; trigger endpoint requires `create_backup` permission |
| `metrics.py` | Prometheus counters/gauges/histograms for backup operations |

### Backup Container

An independent Docker container (`docker-compose.backup.yml`) that:
- Uses `postgres:15-alpine` base with `gpg`, `aws-cli`, `supercrond`
- Runs scheduled backup scripts via cron
- Operates independently of the application container
- Mounts `postgres_data` read-only and `media_files` read-only
- Writes output to `backup_data` volume

### Storage Backends

| Backend | Use Case | Configuration |
|---------|----------|---------------|
| Local (`backup_data` volume) | Primary, fast, same host | `BACKUP_LOCAL_DIR=/backups` |
| Amazon S3 | Offsite, durable | `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX` |
| GCS / Azure | Alternative offsite | Not yet scripted; add to scripts |
| SFTP | Air-gapped sites | Not yet scripted |

## Data Flow

```
1. Cron fires  →  backup-database.sh
2. Script calls pg_dump, compresses with gzip
3. If BACKUP_ENCRYPTION_KEY set: encrypts with GPG AES256
4. Writes backup file to BACKUP_LOCAL_DIR
5. Computes SHA-256, writes .sha256 sidecar
6. If BACKUP_S3_BUCKET set: uploads both files to S3
7. Emits BACKUP_FILE=<path> to stdout
8. Celery task (or separate invocation) reads output, updates BackupRecord
9. Verification task re-computes SHA-256, marks record VERIFIED
```

## Encryption Approach

- **Algorithm:** GPG symmetric AES-256
- **Key source:** `BACKUP_ENCRYPTION_KEY` environment variable only
- **Never committed:** Keys are never written to files or committed to git
- **Scope:** Database backups are encrypted by default when key is provided
- **Media/config:** Optional encryption (configure in `backup-policy.example.yml`)

## Metric Collection

Metrics are published via the same custom Prometheus registry used by the `observability` app (Phase 24). No external Prometheus client library is required.

| Metric | Type | Labels |
|--------|------|--------|
| `restaurantflow_backup_success_total` | Counter | `backup_type` |
| `restaurantflow_backup_failure_total` | Counter | `backup_type` |
| `restaurantflow_backup_duration_seconds` | Histogram | `backup_type`, `storage_provider` |
| `restaurantflow_backup_size_bytes` | Gauge | `backup_type` |
| `restaurantflow_backup_last_success_timestamp` | Gauge | `backup_type` |
| `restaurantflow_restore_duration_seconds` | Histogram | `restore_type` |
| `restaurantflow_restore_test_success` | Gauge | `restore_type` |
| `restaurantflow_backup_storage_bytes` | Gauge | `storage_provider` |

## Alert Integration

CentralAlert types added to `central_control/constants.py`:

| Alert Type | Trigger | Severity |
|------------|---------|----------|
| `BACKUP_FAILED` | Backup script exits non-zero | CRITICAL |
| `BACKUP_NOT_VERIFIED` | Checksum mismatch or missing file | HIGH |
| `BACKUP_STALE` | No healthy backup in 25 hours | HIGH |
| `BACKUP_STORAGE_LOW` | Storage below threshold | HIGH |
| `BACKUP_RESTORE_TEST_FAILED` | Monthly restore drill failed | CRITICAL |
| `DISASTER_RECOVERY_FAILURE` | Multiple DR checks failing | CRITICAL |
| `RECOVERY_OBJECTIVE_BREACH` | RTO/RPO target breached | CRITICAL |

## Retention Policy Diagram

```
Day 0  ──────────────────────────────────────────────────────► Day 90+
│
├── DB Full Backups: retained 30 days, last VERIFIED never expired
├── DB Incremental: retained 7 days
├── Media Backups:  retained 14 days, last VERIFIED never expired
└── Config Backups: retained 90 days

Rule: cleanup_expired_backups() marks records EXPIRED after retention_until.
      The last VERIFIED backup of each type is ALWAYS preserved regardless of date.
```
