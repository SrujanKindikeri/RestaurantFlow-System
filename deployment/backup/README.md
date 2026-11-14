# RestaurantFlow Backup & Disaster Recovery Scripts

This directory contains all scripts and configuration for backup operations.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| `pg_dump` / `pg_restore` | Database backup/restore | Included in `postgres:15-alpine` |
| `gpg` | Backup encryption | `apk add gnupg` / `apt install gnupg` |
| `aws` CLI | S3 upload | `pip3 install awscli` |
| `bash` 4.x+ | Script runtime | Standard on Linux |
| `sha256sum` | Checksum computation | `coreutils` package |

## Directory Layout

```
deployment/backup/
├── scripts/
│   ├── backup-database.sh      # pg_dump full backup
│   ├── backup-media.sh         # Media directory archive
│   ├── backup-configuration.sh # Non-secret config files
│   ├── verify-backup.sh        # Checksum + structural verify
│   ├── restore-database.sh     # DB restore (requires --confirm)
│   ├── restore-media.sh        # Media restore (requires --confirm)
│   ├── cleanup-retention.sh    # Expire old backup files
│   ├── disaster-recovery-check.sh  # Health probe
│   └── *.ps1                   # PowerShell equivalents of above
├── config/
│   ├── backup-policy.example.yml  # Policy documentation template
│   └── crontab                    # Crontab template for backup container
├── Dockerfile.backup           # Backup container image
└── README.md                   # This file
```

## Environment Variables

All scripts read credentials exclusively from environment variables. Never pass credentials as command-line arguments.

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_HOST` | Yes | PostgreSQL hostname |
| `DB_PORT` | Yes | PostgreSQL port (default: 5432) |
| `DB_NAME` | Yes | Database name |
| `DB_USER` | Yes | Database user |
| `DB_PASSWORD` | Yes | Database password |
| `BACKUP_LOCAL_DIR` | Yes | Local directory to store backups |
| `BACKUP_ENCRYPTION_KEY` | For encrypted backups | GPG symmetric passphrase |
| `BACKUP_S3_BUCKET` | For S3 uploads | S3 bucket name |
| `BACKUP_S3_PREFIX` | No | S3 key prefix (default: `db-backups`) |
| `MEDIA_DIR` | For media backup | Path to Django `mediafiles/` directory |
| `BACKUP_RETENTION_DAYS` | For cleanup | Number of days to retain backup files |
| `RESTORE_TARGET_DB` | For restore | Target database (must not be production unless overridden) |
| `RESTORE_TARGET_DIR` | For media restore | Target directory for media restore |
| `RESTORE_ALLOW_PRODUCTION` | Dangerous | Set `true` only to restore to production DB |

## Running Each Script

### Database Backup

```bash
export DB_HOST=localhost DB_PORT=5432 DB_NAME=restaurantflow
export DB_USER=restaurantflow DB_PASSWORD=<secret>
export BACKUP_LOCAL_DIR=/backups
export BACKUP_ENCRYPTION_KEY=<passphrase>   # optional
export BACKUP_S3_BUCKET=my-backups-bucket   # optional

bash deployment/backup/scripts/backup-database.sh
```

### Media Backup

```bash
export MEDIA_DIR=/app/mediafiles
export BACKUP_LOCAL_DIR=/backups
bash deployment/backup/scripts/backup-media.sh
```

### Configuration Backup

```bash
export BACKUP_LOCAL_DIR=/backups
bash deployment/backup/scripts/backup-configuration.sh
```

### Verify a Backup

```bash
export BACKUP_FILE=/backups/db_restaurantflow_20250101T020000Z.pgdump.gz.gpg
export BACKUP_ENCRYPTION_KEY=<passphrase>   # required for .gpg files
bash deployment/backup/scripts/verify-backup.sh
```

### Restore Database (Always to Non-Production First)

```bash
# Step 1: Create the target database
createdb -h localhost -U restaurantflow restaurantflow_restore_test

# Step 2: Run restore with --confirm
export BACKUP_FILE=/backups/db_restaurantflow_20250101T020000Z.pgdump.gz.gpg
export RESTORE_TARGET_DB=restaurantflow_restore_test   # NOT the production DB
export DB_HOST=localhost DB_PORT=5432
export DB_USER=restaurantflow DB_PASSWORD=<secret>
export BACKUP_ENCRYPTION_KEY=<passphrase>

bash deployment/backup/scripts/restore-database.sh --confirm

# Step 3: Run migrations and verify before serving traffic
python manage.py migrate --check
python manage.py check
```

### Restore Media Files

```bash
export BACKUP_FILE=/backups/media_20250101T030000Z.tar.gz
export RESTORE_TARGET_DIR=/staging/mediafiles
bash deployment/backup/scripts/restore-media.sh --confirm
```

### Cleanup Old Backup Files

```bash
export BACKUP_LOCAL_DIR=/backups
export BACKUP_RETENTION_DAYS=30

# Dry run first (default)
bash deployment/backup/scripts/cleanup-retention.sh

# Execute after reviewing
bash deployment/backup/scripts/cleanup-retention.sh --execute
```

### Disaster Recovery Health Check

```bash
export DB_HOST=localhost DB_PORT=5432 DB_USER=restaurantflow
export BACKUP_LOCAL_DIR=/backups
bash deployment/backup/scripts/disaster-recovery-check.sh
# Exit 0 = all healthy; Exit 1 = one or more checks failed
```

## Cron Schedule Examples

The recommended schedule for the backup container cron:

```
# Full database backup: daily at 02:00 UTC
0 2 * * * /bin/bash /scripts/backup-database.sh

# Media backup: daily at 03:00 UTC
0 3 * * * /bin/bash /scripts/backup-media.sh

# Configuration backup: weekly Sunday at 04:00 UTC
0 4 * * 0 /bin/bash /scripts/backup-configuration.sh

# Retention cleanup: daily at 05:00 UTC
0 5 * * * BACKUP_RETENTION_DAYS=30 /bin/bash /scripts/cleanup-retention.sh --execute
```

## PowerShell (Windows)

PowerShell equivalents are provided for all scripts with `.ps1` extensions. Use the same environment variables. Destructive operations require the `-Confirm` switch:

```powershell
$env:BACKUP_FILE = "C:\backups\db_restaurantflow_20250101T020000Z.pgdump.gz"
$env:RESTORE_TARGET_DB = "restaurantflow_restore_test"
.\deployment\backup\scripts\restore-database.ps1 -Confirm
```

## Security Notes

- Encryption keys are **never** stored in this repository or configuration files.
- `.env` files are explicitly excluded from configuration backups.
- The restore scripts refuse to target the production database unless `RESTORE_ALLOW_PRODUCTION=true` is explicitly set.
- Backup download URLs are not exposed through the application API.
