# Database Restore & Point-in-Time Recovery

---

## 1. What PITR Requires

Point-in-Time Recovery (PITR) allows restoring the database to any moment in time, not just the last backup. It requires:

1. **`wal_level = replica` or `logical`** — PostgreSQL must generate enough WAL to replay transactions
2. **`archive_mode = on`** — WAL archiving must be enabled
3. **`archive_command`** — a command that copies each WAL segment to safe storage before it is recycled
4. **`archive_cleanup_command`** — cleans up old WAL segments after base backup no longer needs them
5. **A base backup** — a consistent full database snapshot taken with `pg_basebackup`
6. **WAL segments stored** from the time of the base backup onward

---

## 2. Current Deployment Gap

**PITR is NOT currently configured.**

The existing `docker-compose.yml` uses `postgres:15-alpine` with no custom `postgresql.conf`. No `archive_mode`, no `archive_command`, no `wal_level` override is set.

This means:
- WAL segments are not archived
- Database can only be restored to the most recent pg_dump backup
- **Effective RPO: 24 hours** (the interval between daily pg_dump runs)
- **Target RPO: 15 minutes** (requires WAL archiving)

This gap is documented in `docs/backup_policy.md`. It must be closed before the platform can claim 15-minute RPO.

---

## 3. Required `postgresql.conf` Settings

```ini
# Enable WAL archiving
wal_level = replica
archive_mode = on
archive_timeout = 60   # Archive WAL segment after 60 seconds of inactivity

# Archive command — copy WAL to local directory (replace with wal-g/pgBackRest in production)
archive_command = 'cp %p /var/lib/postgresql/wal_archive/%f'

# Recovery configuration (used on standby / during PITR)
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'

# Keep enough WAL for replicas and point-in-time recovery
wal_keep_size = 1GB
max_wal_size = 4GB
```

**For production S3 archiving with wal-g:**
```ini
archive_command = 'wal-g wal-push %p'
restore_command = 'wal-g wal-fetch %f %p'
```

---

## 4. Mounting a Custom `postgresql.conf` via Docker Volume

Create `deployment/postgres/postgresql.conf` with the settings above. Add to `docker-compose.yml`:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./deployment/postgres/postgresql.conf:/etc/postgresql/postgresql.conf
      - wal_archive:/var/lib/postgresql/wal_archive
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
```

Add a new volume:
```yaml
volumes:
  wal_archive:
    driver: local
```

---

## 5. WAL Storage Location Options

### Option A: Local Directory
Simple but not offsite. Good for development. Set `archive_command = 'cp %p /wal_archive/%f'`.

### Option B: S3 via wal-g (Recommended for Production)

wal-g is a fast, purpose-built WAL archiving tool.

```bash
# Install wal-g in the postgres container
# Set environment variables:
WALG_S3_PREFIX=s3://my-backup-bucket/restaurantflow/wal
AWS_REGION=us-east-1
# Then in postgresql.conf:
archive_command = 'wal-g wal-push %p'
restore_command = 'wal-g wal-fetch %f %p'
```

### Option C: S3 via pgBackRest

pgBackRest provides full backup + WAL archiving + restore in one tool. Configuration is more complex but supports parallel backup/restore, compression, and encryption natively.

---

## 6. Base Backup Frequency Recommendation

- Take a full base backup (pg_basebackup or pgBackRest full) every 24 hours
- WAL segments fill the gap between base backups
- Keeps restore time manageable (replay WAL from last 24 hours, not weeks)

---

## 7. Recovery Configuration Procedure

After enabling WAL archiving, verify it is working:

```bash
# 1. Connect to postgres container
docker exec -it restaurantflow_postgres psql -U restaurantflow

# 2. Check archiving status
SELECT * FROM pg_stat_archiver;
-- last_archived_wal should show a recent segment
-- failed_count should be 0

# 3. Force WAL switch to test archiving
SELECT pg_switch_wal();

# 4. Confirm the segment appears in your archive location
ls /wal_archive/ | tail -5
```

---

## 8. Recovery to Target Time — Step by Step

This procedure restores the database to a specific timestamp.

### Prerequisites
- Access to the most recent base backup before the target time
- All WAL segments from the base backup to the target time
- A target PostgreSQL instance (must NOT be the production instance)

### Steps

```bash
# 1. Stop the target PostgreSQL instance
docker stop restaurantflow_postgres_restore

# 2. Restore the base backup to the data directory
pg_basebackup -h <backup-host> -U replication_user \
    -D /var/lib/postgresql/restore_data -Fp -Xs -P

# Or restore from wal-g:
# wal-g backup-fetch /var/lib/postgresql/restore_data LATEST

# 3. Create recovery.conf (PostgreSQL 11 and earlier)
# For PostgreSQL 12+, use postgresql.conf and postgresql.auto.conf:
cat >> /var/lib/postgresql/restore_data/postgresql.auto.conf << EOF
restore_command = 'wal-g wal-fetch %f %p'
recovery_target_time = '2025-06-15 14:30:00 UTC'
recovery_target_action = 'promote'
EOF

# 4. Create recovery signal file (PostgreSQL 12+)
touch /var/lib/postgresql/restore_data/recovery.signal

# 5. Start PostgreSQL
docker start restaurantflow_postgres_restore

# 6. Monitor recovery in logs
docker logs -f restaurantflow_postgres_restore

# 7. After recovery, verify data
psql -h localhost -U restaurantflow -c "SELECT COUNT(*) FROM orders;"

# 8. If correct, promote to standalone
# psql -h localhost -U restaurantflow -c "SELECT pg_promote();"
```

---

## 9. PITR Operational Checklist

Before claiming PITR is operational, all of the following must be true:

- [ ] `wal_level = replica` confirmed in `SHOW wal_level;`
- [ ] `archive_mode = on` confirmed in `SHOW archive_mode;`
- [ ] `pg_stat_archiver.last_archived_wal` shows recent segments
- [ ] `pg_stat_archiver.failed_count = 0`
- [ ] WAL segments are appearing in the archive storage location
- [ ] A test restore to a target-time 1 hour ago has been completed successfully
- [ ] The restored database passes application health checks
- [ ] Archive storage has sufficient space (retention policy applied)
- [ ] Monitoring alerts fire when archiving stops (failed_count > 0)
- [ ] The restore procedure is documented and all operators have rehearsed it

---

## 10. Recommended Tool: wal-g

**Install in backup container:**
```bash
# In Dockerfile.backup or postgres container:
curl -L https://github.com/wal-g/wal-g/releases/latest/download/wal-g-pg-ubuntu-20.04-amd64.tar.gz \
    | tar -xz -C /usr/local/bin/
chmod +x /usr/local/bin/wal-g
```

**Configure via environment variables:**
```bash
WALG_S3_PREFIX=s3://my-bucket/restaurantflow/wal
WALG_S3_REGION=us-east-1
# Or use WALG_FILE_PREFIX for local storage
WALG_COMPRESSION_METHOD=lz4
WALG_DELTA_MAX_STEPS=5  # Keep 5 delta backups between fulls
```

**Useful commands:**
```bash
wal-g backup-push /var/lib/postgresql/data   # Take a full base backup
wal-g backup-list                              # List available backups
wal-g backup-fetch /restore LATEST            # Restore latest backup
wal-g delete retain FULL 7                    # Keep 7 full backups, delete older
```

---

## 11. RPO Gap Statement

| State | RPO |
|-------|-----|
| **Current (pg_dump only)** | 24 hours — data since last pg_dump is unrecoverable |
| **Target (WAL archiving)** | 15 minutes — maximum data loss limited to `archive_timeout` |

To achieve the 15-minute RPO target, implement WAL archiving with wal-g or pgBackRest and complete all items in the PITR Operational Checklist above.
