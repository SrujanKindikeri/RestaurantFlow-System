# RestaurantFlow — Rollback Procedure
## Phase 26 — Emergency Rollback Guide

---

## Overview

This document describes the step-by-step procedure to roll back a failed deployment of RestaurantFlow. The rollback procedure covers:
1. Docker image reversion
2. Database migration rollback
3. Cache flush
4. Nginx config restore
5. Verification

---

## Prerequisites

Before starting a rollback:
- Identify the previous stable Docker image tag (e.g., `v0.9.0`)
- Confirm the last migration state before the failed deployment
- Ensure you have database backup from before deployment
- Alert the team that a rollback is in progress

---

## Step 1: Stop the Current Deployment

```bash
cd /srv/restaurantflow

# Stop the failing deployment
docker compose stop backend worker

# Verify stopped
docker compose ps
```

---

## Step 2: Identify the Previous Stable Image Tag

```bash
# List available backend images
docker images restaurantflow-backend

# Example output:
# restaurantflow-backend   v1.0.0   abc123   10 minutes ago   ...
# restaurantflow-backend   v0.9.0   def456   2 days ago       ...

# Record the previous stable tag (e.g., v0.9.0)
ROLLBACK_TAG="v0.9.0"
```

---

## Step 3: Revert Docker Image Tag

```bash
# Edit docker-compose.yml to use the previous image tag
# Option A: Edit the image tag directly
sed -i "s/restaurantflow-backend:latest/restaurantflow-backend:${ROLLBACK_TAG}/" docker-compose.yml

# Option B: Manually edit docker-compose.yml and change:
#   image: restaurantflow-backend:v1.0.0
# to:
#   image: restaurantflow-backend:v0.9.0

# Verify the change
grep "image:" docker-compose.yml
```

---

## Step 4: Roll Back Database Migrations

**IMPORTANT:** Only roll back migrations if the new deployment added migrations that need to be undone. Skip this step if the deployment failed before migrations ran.

```bash
# First, identify which migrations the new deployment added
# (compare with the migration list from before deployment)

# Check current migration state
docker compose run --rm backend python manage.py showmigrations | grep "\[X\]" | tail -20

# Roll back to a specific migration
# Replace <app_name> and <migration_name> with the last KNOWN GOOD state
# Example: roll back billing to 0003_add_vat_field
docker compose run --rm backend python manage.py migrate billing 0003_add_vat_field

# Roll back multiple apps if needed
docker compose run --rm backend python manage.py migrate notifications 0004_notification_channels
docker compose run --rm backend python manage.py migrate central_control 0002_rate_limit_policy
docker compose run --rm backend python manage.py migrate backup_management 0001_initial

# Verify migration state
docker compose run --rm backend python manage.py showmigrations
```

**WARNING:** Rolling back migrations that modify or drop columns will cause data loss. Always have a database backup before rolling back migrations.

---

## Step 5: Restore Database from Backup (if migration rollback is risky)

If the migration changes are destructive (column drops, data transformations), restore from the pre-deployment backup instead of rolling back migrations:

```bash
# Stop all services accessing the database
docker compose stop backend worker

# Restore from backup
gunzip -c /backups/rf_pre_deployment_YYYYMMDD.sql.gz | \
  docker compose exec -T db psql -U $POSTGRES_USER $POSTGRES_DB

# Verify restore
docker compose exec db psql -U $POSTGRES_USER $POSTGRES_DB -c "\dt" | head -20
```

---

## Step 6: Flush Application Cache

```bash
# Start the previous version first
docker compose up -d backend

# Flush Redis cache (clears all cached data)
docker compose exec redis redis-cli FLUSHDB

# Or flush specific namespaces:
docker compose exec backend python manage.py shell -c "
from django.core.cache import cache
cache.clear()
print('Cache flushed')
"
```

---

## Step 7: Restore Nginx Configuration (if changed)

```bash
# If Nginx config was updated as part of the deployment:

# Check git for the previous Nginx config
git show HEAD~1:nginx/nginx.conf > /tmp/previous_nginx.conf

# Replace current Nginx config
cp /tmp/previous_nginx.conf /srv/restaurantflow/nginx/nginx.conf

# Restart Nginx
docker compose restart nginx

# Test Nginx config
docker compose exec nginx nginx -t
```

---

## Step 8: Start Rolled-Back Services

```bash
# Start backend with the previous image
docker compose up -d backend worker

# Monitor startup logs
docker compose logs -f backend --tail=50
```

---

## Step 9: Verification

```bash
# 1. Health check
curl -f http://localhost/api/health/ && echo "HEALTH CHECK PASSED"

# 2. Check Django system
docker compose exec backend python manage.py check

# 3. Verify migration state
docker compose exec backend python manage.py showmigrations | grep "\[X\]" | tail -10

# 4. Quick smoke test — login should work
curl -X POST http://localhost/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass"}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK' if 'access' in d else 'FAIL')"

# 5. Check error logs
docker compose logs backend --tail=100 | grep -i "error\|exception\|critical"
```

---

## Step 10: Post-Rollback Actions

1. **Notify the team** that rollback is complete and system is stable
2. **Create a post-incident report** documenting what failed and why
3. **Preserve failed deployment artifacts** (Docker images, migration files) for investigation
4. **Update monitoring** to reflect the rolled-back version
5. **Plan the fix** before attempting re-deployment

---

## Quick Reference: Common Rollback Commands

```bash
# Roll back one migration in an app
python manage.py migrate <app> <migration_number>

# Roll back ALL migrations in an app (removes all tables for that app)
python manage.py migrate <app> zero

# See migration history
python manage.py showmigrations

# Check what SQL a rollback would execute (dry run)
python manage.py sqlmigrate <app> <migration> --backwards

# Flush cache
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Restart services
docker compose restart backend worker nginx
```
