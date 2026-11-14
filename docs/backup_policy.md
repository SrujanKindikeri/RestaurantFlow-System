# Backup Policy — RestaurantFlow

**Version:** 1.0  
**Effective from:** Phase 25  
**Review cadence:** Annually, or after any DR exercise reveals gaps

---

## 1. Scope

This policy covers all data stored and processed by the RestaurantFlow platform:
- PostgreSQL database (`restaurantflow` schema and all application data)
- Django media files (uploaded images, receipts, documents)
- System configuration files (docker-compose, nginx, deployment scripts)
- Application metadata (Celery results, session data)

Excluded from this policy (managed separately or intentionally not backed up):
- `.env` files and secrets (must NEVER be backed up to shared storage)
- Private keys and TLS certificates (managed by secrets management system)
- Ephemeral Redis cache data (database 0: entirely rebuildable from PostgreSQL)

---

## 2. Recovery Objectives

| Metric | Target | Current Status |
|--------|--------|---------------|
| **RPO (Recovery Point Objective)** | 15 minutes | **GAP: 24 hours** — pg_dump full backups only; WAL archiving required for 15-min RPO. See `docs/database_restore.md`. |
| **RTO (Recovery Time Objective)** | 4 hours | Achievable with documented restore procedures |

**RPO Gap Statement:** The current deployment uses pg_dump full backups on a daily schedule. To achieve the 15-minute RPO target, WAL archiving (using pgBackRest or wal-g) must be implemented and verified. This is documented as a gap in `docs/database_restore.md`. Until WAL archiving is operational, the effective RPO is 24 hours.

---

## 3. Backup Types and Schedules

| Backup Type | Schedule | Method | Encryption |
|-------------|----------|--------|-----------|
| Database full | Daily at 02:00 UTC | pg_dump -Fc + gzip + GPG | Required |
| Database incremental | Every 6 hours | pg_dump (differential via script) | Required |
| Database WAL | Continuous (gap — not yet configured) | pgBackRest / wal-g | Required |
| Media files | Daily at 03:00 UTC | tar + gzip | Optional |
| Configuration | Weekly Sunday 04:00 UTC | tar/zip | Not required (no secrets) |

---

## 4. Retention Periods

| Backup Type | Retention |
|-------------|-----------|
| Database full | 30 days |
| Database incremental | 7 days |
| WAL segments | 7 days |
| Media files | 14 days |
| Configuration | 90 days |

**Safety rule:** The most recent VERIFIED backup of each type is never deleted, regardless of its retention date. This ensures there is always at least one valid restore point.

---

## 5. Encryption Requirements

- All database backups MUST be encrypted using GPG AES-256 symmetric encryption
- The encryption key MUST be stored in the `BACKUP_ENCRYPTION_KEY` environment variable only
- The key MUST NOT be committed to any repository or configuration file
- Key rotation: annually or upon any suspected compromise
- Key storage: use a secrets management system (HashiCorp Vault, AWS Secrets Manager, or equivalent)

---

## 6. Storage Requirements

### Primary Storage
- Local: `backup_data` Docker volume on the backup container host
- Minimum free space: 5 GB at all times
- Alert threshold: CentralAlert raised when free space drops below 5 GB

### Offsite Storage (Recommended)
- Amazon S3 (or equivalent) with `STANDARD_IA` storage class for cost efficiency
- Bucket lifecycle policy: archive to Glacier after 30 days
- S3 bucket versioning: enabled
- S3 bucket MFA delete: enabled for production buckets

### Geographic Distribution
- Primary: same region as the application
- Secondary: different AWS region (disaster recovery)

---

## 7. Verification Requirements

- Every backup MUST have a SHA-256 checksum sidecar file (`.sha256`)
- Checksums MUST be verified before marking a backup as VERIFIED
- Monthly restore test: restore database to a non-production target and verify data integrity
- Quarterly restore drill: full DR exercise including application startup
- All verification results MUST be recorded in `BackupRecord.verified_at` and `BackupRecord.status`

---

## 8. Roles and Responsibilities

| Role | Responsibility |
|------|---------------|
| System Administrator | Configure backup environment variables, monitor CentralAlerts |
| Operations Manager | Approve restore requests, sign off on quarterly DR drills |
| Developer Lead | Maintain backup scripts and backup_management app |
| All Engineers | Understand restore procedures; never commit credentials |

### Django Permissions

| Permission | Who Should Have It |
|------------|-------------------|
| `view_backup_status` | All operations staff |
| `view_backup_history` | Operations managers, system admins |
| `create_backup` | System admins only |
| `verify_backup` | System admins only |
| `request_restore` | Operations managers |
| `approve_restore` | Senior operations managers |
| `manage_retention` | System admins only |
| `manage_backup_configuration` | System admins only |

---

## 9. Review Cadence

| Review Type | Frequency | Owner |
|-------------|-----------|-------|
| Policy review | Annual | Operations Manager |
| Backup schedule review | Quarterly | System Administrator |
| Restore test | Monthly | System Administrator |
| Full DR exercise | Annual | All stakeholders |
| RPO/RTO target review | After any incident | Operations Manager |
