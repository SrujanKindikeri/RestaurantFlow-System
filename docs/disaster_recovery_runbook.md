# Disaster Recovery Runbook — RestaurantFlow

**Audience:** System administrators, operations managers  
**Classification:** Internal — operational use only

---

## Scenario 1: Database Failure (Corruption, Crash, Accidental DROP)

### Symptoms
- Application returns 500 errors referencing database connection failures
- PostgreSQL container exits or restarts continuously
- `pg_stat_activity` shows long-running queries or locks
- `pg_isready` returns non-zero
- CentralAlert: SYSTEM_HEALTH or DATA_INTEGRITY

### Immediate Steps
1. **Do not attempt to restart the database multiple times** — this may worsen corruption
2. Enable maintenance mode if available; otherwise note the outage start time
3. Take a PostgreSQL instance snapshot / Docker volume snapshot before any action
4. Check Docker logs: `docker logs restaurantflow_postgres`
5. Run `pg_isready` to confirm connectivity status

### Recovery Steps

**Case A: Crash (no corruption) — PostgreSQL restarts cleanly**
```bash
docker restart restaurantflow_postgres
docker logs -f restaurantflow_postgres  # Watch for "database system is ready to accept connections"
```

**Case B: Accidental DROP TABLE or data deletion**
```bash
# 1. Stop application to prevent further writes
docker stop restaurantflow_app

# 2. Find the last VERIFIED backup
curl -H "Authorization: Bearer <token>" \
    https://api.restaurantflow.app/api/backup/records/?backup_type=DATABASE_FULL&status=VERIFIED

# 3. Restore to non-production first
export BACKUP_FILE=/backups/db_restaurantflow_<timestamp>.pgdump.gz.gpg
export RESTORE_TARGET_DB=restaurantflow_restore_test
export DB_HOST=localhost DB_PORT=5432 DB_USER=restaurantflow DB_PASSWORD=<secret>
export BACKUP_ENCRYPTION_KEY=<passphrase>

createdb -h localhost -U restaurantflow restaurantflow_restore_test
bash deployment/backup/scripts/restore-database.sh --confirm

# 4. Verify data in restored DB
psql -h localhost -U restaurantflow restaurantflow_restore_test -c "SELECT COUNT(*) FROM orders;"

# 5. If correct, promote to production (destructive — confirm first)
export RESTORE_TARGET_DB=restaurantflow
export RESTORE_ALLOW_PRODUCTION=true
bash deployment/backup/scripts/restore-database.sh --confirm
```

**Case C: Corruption**
- Do not restart — corruption may worsen
- Restore from last VERIFIED backup as above
- After restore: `python manage.py migrate --check` to verify schema

### Verification
- Application returns HTTP 200 on `/health/ready/`
- Database health check passes
- Spot-check 10 recent orders and payments in admin

### Estimated RTO: 1–3 hours

---

## Scenario 2: Server / Host Failure (VM or Container Host Goes Down)

### Symptoms
- All services unreachable
- SSH to host fails
- Monitoring shows host offline

### Immediate Steps
1. Confirm the host is down (check cloud provider console)
2. Identify the last-known-good state from monitoring dashboards
3. Note the time of failure for RPO calculation

### Recovery Steps

```bash
# 1. Provision a new host (cloud provider CLI or console)
# 2. Install Docker and docker-compose

# 3. Clone the repository to the new host
git clone <repo-url> /opt/restaurantflow
cd /opt/restaurantflow

# 4. Create .env file from your secrets management system
# (never copy .env from the old host — it may be compromised)
vault kv get -format=json secret/restaurantflow/production > .env

# 5. Restore database from backup
# ... (see Scenario 1 Case B steps)

# 6. Restore media from backup
# ... (see media_restore.md)

# 7. Start services
docker compose up -d

# 8. Run migrations
docker exec restaurantflow_app python manage.py migrate

# 9. Update DNS/load balancer to point to new host
```

### Estimated RTO: 2–4 hours

---

## Scenario 3: Accidental Data Deletion (Operator Error)

### Symptoms
- Operator reports they deleted a customer record, menu items, or orders
- Data missing from application UI
- No database errors — data was validly deleted

### Immediate Steps
1. Record exactly what was deleted and when
2. Check the audit log in Django admin: `CentralControlAuditLog`
3. Stop application writes if deletion is ongoing

### Recovery Steps

**For soft-deletable data (if the model has `is_active` or `deleted_at`):**
```python
# Restore via Django shell without full DB restore
python manage.py shell
>>> from orders.models import Order
>>> Order.objects.filter(id='<uuid>').update(is_active=True)
```

**For hard-deleted data (requires restore):**
```bash
# 1. Restore to non-production DB (see Scenario 1 Case B)
# 2. Export the missing records as JSON from the restored DB
python manage.py dumpdata orders.Order --pks <uuid1>,<uuid2> > missing_orders.json

# 3. Import into production
python manage.py loaddata missing_orders.json
```

### Verification
- Confirm the restored records appear in the UI
- Confirm related records (payments, billing) are consistent

### Estimated RTO: 1–2 hours for small data loss

---

## Scenario 4: Ransomware / Security Compromise

### Symptoms
- Files encrypted or renamed on host
- Backup files modified or deleted
- Unusual CPU/disk activity
- CentralAlert: UNUSUAL_ACTIVITY

### Immediate Steps
1. **ISOLATE immediately** — disconnect the host from the network (revoke security group/firewall rules)
2. Do NOT pay any ransom
3. Preserve evidence: snapshot all volumes before any action
4. Notify security team and management
5. File a security incident report

### Recovery Steps

```bash
# 1. Provision a CLEAN new host — do not reuse the compromised host
# 2. Retrieve backups ONLY from offsite storage (S3)
#    If local backups are encrypted/deleted, they cannot be used
aws s3 ls s3://my-backup-bucket/restaurantflow/backups/ | sort | tail -10
aws s3 cp s3://my-backup-bucket/restaurantflow/backups/db_<latest>.pgdump.gz.gpg /backups/

# 3. Rotate ALL credentials before restoring:
#    - DB_PASSWORD
#    - SECRET_KEY
#    - BACKUP_ENCRYPTION_KEY
#    - JWT signing key
#    - All API keys
#    - SSL certificates if compromised

# 4. Restore from clean backup (follow Scenario 1 Case B)
# 5. Review access logs to understand breach scope
# 6. Apply security patches before bringing back online
```

### Estimated RTO: 4–8 hours (or longer, depending on breach scope)

---

## Scenario 5: Failed Deployment (Rollback Procedure)

### Symptoms
- After deployment, application returns errors
- `/health/ready/` fails
- Error rate spikes in Prometheus/Grafana

### Immediate Steps
1. Record the deployment commit SHA and time
2. Check application logs: `docker logs restaurantflow_app`

### Recovery Steps

**Fast rollback (previous Docker image):**
```bash
# Roll back to the previous image tag
IMAGE_TAG=<previous_tag>
docker pull ghcr.io/restaurantflow/api:${IMAGE_TAG}
docker stop restaurantflow_app
docker run -d --name restaurantflow_app \
    --env-file /opt/restaurantflow/.env \
    ghcr.io/restaurantflow/api:${IMAGE_TAG}
```

**Database migration rollback:**
```bash
# If the deployment included database migrations that need to be reversed:
python manage.py migrate <app_name> <previous_migration>
# Example: python manage.py migrate orders 0025
```

**Git rollback:**
```bash
git -C /opt/restaurantflow revert HEAD --no-edit
docker compose down && docker compose up -d
```

### Verification
- `/health/ready/` returns 200
- Application creates and processes a test order

### Estimated RTO: 15–60 minutes

---

## Scenario 6: Redis Failure

### Symptoms
- Celery tasks not being processed
- WebSocket connections dropping
- Cache misses causing slow page loads
- CentralAlert: SYSTEM_HEALTH

### Immediate Steps
1. Check Redis container: `docker logs restaurantflow_redis`
2. Run `redis-cli ping` — if no response, Redis is down

### Recovery Steps

**Case A: Redis container crash (no data corruption)**
```bash
# Simply restart — AOF ensures queue state is restored
docker restart restaurantflow_redis
# Confirm: redis-cli ping → PONG
# Confirm: Celery workers reconnect and process pending tasks
```

**Case B: Redis data corruption (AOF file corrupted)**
```bash
# 1. Stop Redis
docker stop restaurantflow_redis

# 2. Retrieve last Redis AOF backup (if BACKUP_REDIS_AOF=true was enabled)
cp /backups/redis_aof_<timestamp>.aof /data/appendonly.aof

# 3. Run AOF repair tool
redis-check-aof --fix /data/appendonly.aof

# 4. Restart Redis
docker start restaurantflow_redis
```

**Case C: Cache-only failure (db 0 used for Django cache)**
```bash
# Cache is entirely rebuildable from PostgreSQL — just flush and restart
redis-cli -a ${REDIS_PASSWORD} FLUSHDB
docker restart restaurantflow_app  # Django rebuilds cache on first requests
```

### Post-Recovery: Cache Rebuild

After any Redis restart, the Django cache (db 0) is empty. This is expected and safe:
- The application functions correctly with empty cache (slower first requests)
- Do NOT restore stale cache over a database that was just restored — always flush cache after DB restore
- Cache warms naturally as requests arrive

### Post-Recovery: Celery Queue

After Redis restart with AOF:
- In-flight tasks that were acknowledged but not completed may be lost
- Tasks that were queued but not yet acknowledged will be replayed
- Check for duplicate processing on idempotent tasks

### WebSocket / Django Channels

Channel layer state (presence, group memberships) is transient and lost on Redis restart. This is expected behavior:
- Clients disconnect and automatically reconnect via the client-side WebSocket reconnect logic
- No data loss; real-time state rebuilds within seconds of client reconnect

### Estimated RTO: 5–30 minutes

---

## Redis Backup Strategy

### Workload Classification

| Redis Use | DB Number | Persistence Needed | Recovery Method |
|-----------|-----------|-------------------|-----------------|
| Django cache | 0 (default) | No — entirely rebuildable | Flush, let warm naturally |
| Celery broker | 0 (via CELERY_BROKER_URL) | Yes — AOF | AOF recovery or accept task loss |
| Django Channels | 0 (channel layer) | No — transient | Clients reconnect automatically |

### Existing AOF Configuration

The `docker-compose.yml` already enables AOF persistence:
```yaml
command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
```

This is the correct configuration. Do not add `save` (RDB) directives unless you specifically want RDB in addition to AOF — mixing both can complicate recovery.

### Safe Shutdown Procedure

```bash
# 1. Tell Redis to do a final BGREWRITEAOF before shutdown
redis-cli -a ${REDIS_PASSWORD} BGREWRITEAOF
# Wait for completion
redis-cli -a ${REDIS_PASSWORD} INFO persistence | grep aof_rewrite_in_progress
# When 0, proceed

# 2. Graceful shutdown
docker stop restaurantflow_redis
# Docker sends SIGTERM which triggers Redis SHUTDOWN SAVE
```

### Copying the AOF File

```bash
# From the redis_data volume mount point
docker exec restaurantflow_redis redis-cli -a ${REDIS_PASSWORD} BGREWRITEAOF
docker cp restaurantflow_redis:/data/appendonly.aof /backups/redis_aof_$(date +%Y%m%d).aof
sha256sum /backups/redis_aof_$(date +%Y%m%d).aof > /backups/redis_aof_$(date +%Y%m%d).aof.sha256
```

### Restoring Queue State

```bash
# 1. Stop Redis
docker stop restaurantflow_redis

# 2. Replace the AOF file
cp /backups/redis_aof_<timestamp>.aof /path/to/redis_data_volume/appendonly.aof

# 3. Repair if needed
redis-check-aof --fix /path/to/redis_data_volume/appendonly.aof

# 4. Start Redis
docker start restaurantflow_redis
```

### Avoiding Stale Cache After DB Restore

**Rule: Always flush the Redis cache after restoring the PostgreSQL database.**

Failing to flush the cache after a DB restore results in serving stale data (e.g., deleted orders appearing valid, old prices in cache while new prices are in DB).

```bash
# After every DB restore, run:
redis-cli -a ${REDIS_PASSWORD} FLUSHDB
# Then restart the application to rebuild session state
docker restart restaurantflow_app
```
