# RestaurantFlow — Production Operations Manual
## Phase 26 — System Operations Guide

---

## 1. System Architecture Overview

```
Internet → Nginx (reverse proxy) → Django (Gunicorn/ASGI)
                                 → Django Channels (WebSocket)
                                 → Celery Workers (background tasks)
PostgreSQL 15 (primary database)
Redis 7 (cache + Celery broker + WebSocket channel layer)
```

---

## 2. Startup Procedure

### Full System Start (Docker Compose)

```bash
# Navigate to project root
cd /srv/restaurantflow

# Pull latest images (if deploying new version)
docker compose pull

# Start all services
docker compose up -d

# Verify all containers are healthy
docker compose ps

# Run migrations (if new deployment)
docker compose exec backend python manage.py migrate --no-input

# Collect static files
docker compose exec backend python manage.py collectstatic --no-input

# Verify application responds
curl -f http://localhost/api/health/ || echo "HEALTH CHECK FAILED"
```

### Expected healthy output from `docker compose ps`:
```
NAME                    STATUS          PORTS
restaurantflow-db       Up (healthy)    5432/tcp
restaurantflow-redis    Up (healthy)    6379/tcp
restaurantflow-backend  Up (healthy)    8000/tcp
restaurantflow-worker   Up              -
restaurantflow-nginx    Up              0.0.0.0:80->80/tcp, 0.0.0.0:443->443/tcp
```

---

## 3. Shutdown Procedure

### Graceful Shutdown
```bash
# Stop all services without removing volumes
docker compose stop

# Full stop and removal of containers (preserves volumes/data)
docker compose down

# CAUTION: This removes all data volumes — only for clean wipe
# docker compose down -v  # NEVER run in production without backup
```

---

## 4. Scaling Workers

### Scale Celery workers up
```bash
docker compose up -d --scale worker=4
```

### Scale back to single worker
```bash
docker compose up -d --scale worker=1
```

### Restart worker after code change
```bash
docker compose restart worker
```

---

## 5. Common Operational Tasks

### Clear Application Cache
```bash
docker compose exec backend python manage.py shell -c "from django.core.cache import cache; cache.clear(); print('Cache cleared')"
```

### Restart Django Backend
```bash
docker compose restart backend
```

### Restart Celery Worker
```bash
docker compose restart worker
```

### Check Application Health
```bash
# HTTP health check
curl -s http://localhost/api/health/

# Database connectivity
docker compose exec backend python manage.py check --database default

# Redis connectivity
docker compose exec redis redis-cli ping
```

### Open Django Shell
```bash
docker compose exec backend python manage.py shell
```

### Run Database Migrations
```bash
docker compose exec backend python manage.py migrate
```

### Create Superuser (first deployment)
```bash
docker compose exec backend python manage.py createsuperuser
```

---

## 6. Log Locations

| Service | Log Location | Access Command |
|---|---|---|
| Django Backend | stdout/stderr → Docker logs | `docker compose logs backend` |
| Celery Worker | stdout/stderr → Docker logs | `docker compose logs worker` |
| Nginx | `/var/log/nginx/access.log`, `error.log` | `docker compose exec nginx cat /var/log/nginx/error.log` |
| PostgreSQL | Docker container logs | `docker compose logs db` |
| Redis | Docker container logs | `docker compose logs redis` |
| Application logs | `backend/logs/*.log` (if file handler configured) | `tail -f backend/logs/app.log` |

### Follow live backend logs
```bash
docker compose logs -f backend --tail=100
```

---

## 7. Database Backup

### Trigger manual PostgreSQL backup
```bash
# Dump database to file
docker compose exec db pg_dump -U $POSTGRES_USER $POSTGRES_DB > backup_$(date +%Y%m%d_%H%M%S).sql

# Compress backup
gzip backup_*.sql
```

### Schedule automated backups (cron example)
```bash
# Add to crontab: daily backup at 2 AM
0 2 * * * cd /srv/restaurantflow && docker compose exec -T db pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > /backups/rf_$(date +\%Y\%m\%d).sql.gz
```

### Restore from backup
```bash
gunzip -c backup_20260101.sql.gz | docker compose exec -T db psql -U $POSTGRES_USER $POSTGRES_DB
```

---

## 8. Environment Variables Reference

| Variable | Description | Example |
|---|---|---|
| `SECRET_KEY` | Django secret key | `50-character random string` |
| `DEBUG` | Django debug mode | `False` (MUST be False in production) |
| `DB_NAME` | PostgreSQL database name | `restaurantflow` |
| `DB_USER` | PostgreSQL username | `rfuser` |
| `DB_PASSWORD` | PostgreSQL password | `secure-password` |
| `DB_HOST` | PostgreSQL host | `db` (Docker) or hostname |
| `DB_PORT` | PostgreSQL port | `5432` |
| `REDIS_URL` | Redis connection URL | `redis://redis:6379/0` |
| `ALLOWED_HOSTS` | Comma-separated allowed hosts | `api.restaurantflow.com` |
| `CORS_ALLOWED_ORIGINS` | Frontend origins | `https://app.restaurantflow.com` |

---

## 9. Emergency Contacts

| Role | Name | Contact |
|---|---|---|
| Technical Lead | [PLACEHOLDER] | [PLACEHOLDER] |
| DevOps Engineer | [PLACEHOLDER] | [PLACEHOLDER] |
| Database Administrator | [PLACEHOLDER] | [PLACEHOLDER] |
| On-call Support | [PLACEHOLDER] | [PLACEHOLDER] |

---

## 10. Quick Diagnostics Checklist

When something goes wrong, check in this order:
1. `docker compose ps` — are all containers running?
2. `docker compose logs backend --tail=50` — any Python errors?
3. `docker compose exec db pg_isready` — database accepting connections?
4. `docker compose exec redis redis-cli ping` — Redis responding?
5. `curl http://localhost/api/health/` — application responding?
6. Check disk space: `df -h /srv/restaurantflow`
7. Check memory: `free -h`
