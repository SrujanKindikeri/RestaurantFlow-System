# Deployment Rollback

RestaurantFlow uses immutable Docker image tags (git SHA) to enable reliable rollbacks. Every production deployment pushes images tagged with the full commit SHA, making it straightforward to return to any previous state.

---

## Rollback strategy overview

| Layer | Rollback method |
|-------|----------------|
| Application (backend + frontend) | Pull previous SHA tag, restart services |
| Database migrations | Manual — requires pre-deploy backup |
| Configuration | Restore previous `.env.prod` |
| Static assets | Re-built into the image — rolls back automatically with the image |
| Media files (uploads) | Persistent volume — not affected by application rollback |

---

## Automated rollback script

```bash
bash deployment/scripts/rollback.sh <previous-git-sha>
```

or on Windows:

```powershell
.\deployment\scripts\rollback.ps1 -PrevTag <previous-git-sha>
```

The script:
1. Sets `IMAGE_TAG=<previous-git-sha>`
2. Pulls the previously-tagged backend and frontend images from GHCR
3. Restarts all services using `docker compose up -d --no-build`
4. Runs the health check (`/health/ready/`) and fails loudly if services do not recover

---

## Finding the previous image tag

```bash
# View recent git commit SHAs (full SHA is used as the image tag)
git log --oneline -20

# Or look up the previous successful CD workflow run in GitHub Actions
# Actions → CD → (previous run) → build-and-push → image tag output
```

---

## Manual rollback steps

If the rollback script is unavailable, run these commands directly on the server:

```bash
export IMAGE_TAG=<previous-sha>
cd ~/restaurantflow

docker compose -f docker-compose.yml -f docker-compose.prod.yml pull backend nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build

# Verify
curl -f http://localhost/health/ready/
```

---

## Database rollback

**Application rollback does not automatically reverse database migrations.**

Migrations are forward-only by default. Rolling back the application image while leaving the database at its current migration state is safe as long as the previous application version is compatible with the current schema.

### When rollback is safe (no DB action needed)

- The rolled-back version was written with backward-compatible migrations.
- No columns, tables, or constraints were removed in the failed deployment.
- The expand-and-contract pattern was followed (see below).

### When manual database recovery is needed

If a destructive migration ran (column drop, table rename, constraint change), restoring the database requires:

1. Stop all application services immediately.

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml stop backend celery_worker celery_beat
   ```

2. Restore from the pre-deploy backup.

   ```bash
   # Find the backup created by backup-before-deploy.sh
   ls -lt ~/restaurantflow-backups/
   
   # Restore
   BACKUP_FILE=~/restaurantflow-backups/restaurantflow_<timestamp>.sql
   docker compose exec -T postgres psql -U restaurantflow restaurantflow < "$BACKUP_FILE"
   ```

3. Roll back the application image using the script above.

4. Verify health and resume traffic.

### Expand-and-contract pattern

For destructive schema changes, use two separate deployments:

1. **Expand**: Add new columns/tables alongside old ones. Deploy application that writes to both.
2. **Migrate data**: Backfill if needed.
3. **Contract**: Remove old columns/tables in a later deployment once all code uses the new schema.

This ensures any single deployment can be safely rolled back without data loss.

---

## Rollback for failed health checks

If the deployment script's health check fails:

1. The script exits non-zero — services are in an indeterminate state.
2. Run the rollback script immediately with the previous SHA.
3. Investigate logs before attempting another deploy.

```bash
# View logs from the failed backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 backend
```

---

## Configuration rollback

If the problem is a bad environment variable (not code or migration):

1. Edit `deployment/environment/.env.prod` on the server.
2. Restart affected services without pulling new images:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build backend celery_worker celery_beat
   ```

---

## Verifying a rollback succeeded

```bash
# Health check
curl https://yourdomain.com/health/ready/
# Expected: {"status": "ready", "database": "ok", "redis": "ok"}

# Confirm running image SHA
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker inspect restaurantflow_backend | grep -i image
```

---

## Cases requiring manual intervention

| Scenario | Manual step required |
|----------|---------------------|
| Destructive migration ran | Restore database from backup |
| Redis data cleared unexpectedly | Celery queues may need replaying; Channels groups reconnect automatically |
| `celery_beat` duplicated schedules | Stop extra instances; check `django_celery_beat` periodic task table for duplicates |
| SSL certificate expired | Renew certificate, restart Nginx |
| Docker volume corrupted | Restore from backup; volumes do not roll back with images |
