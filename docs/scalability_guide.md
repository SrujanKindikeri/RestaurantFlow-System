# Scalability Guide — Phase 22

**Purpose**: Operational guide for scaling RestaurantFlow horizontally across Gunicorn workers,
Celery workers, and an optional PgBouncer connection pooler.

---

## 1. Database Connection Pooling

### 1.1 CONN_MAX_AGE (Django Persistent Connections)

**Setting**: `DATABASES['default']['CONN_MAX_AGE'] = 60`

Gunicorn with sync workers assigns one worker process to one HTTP request at a time. Without
persistent connections, every request pays the cost of opening and authenticating a new PostgreSQL
connection (typically 5–20 ms of overhead).

With `CONN_MAX_AGE = 60`, each Gunicorn worker keeps its database connection alive for up to 60
seconds of idle time. This means:

- Number of DB connections at peak ≈ number of Gunicorn workers
- No connection surge on restart — connections re-established gradually
- Idle connections are recycled after 60 seconds, preventing PostgreSQL from accumulating stale
  connections from crashed or redeployed workers

**Recommended Gunicorn worker count**: `2 × CPU_cores + 1`

```bash
gunicorn config.wsgi:application \
    --workers $(( 2 * $(nproc) + 1 )) \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 5
```

**PostgreSQL `max_connections`**: Set to at least `(gunicorn_workers × instances) + 20` for overhead.

---

### 1.2 PgBouncer — Optional External Connection Pooler

PgBouncer sits between Django and PostgreSQL and multiplexes many client connections to a smaller
pool of server connections. It is optional but recommended for deployments with:
- More than 4 Gunicorn instances running simultaneously
- PostgreSQL `max_connections` pressure
- Short-lived connection overhead on high-traffic endpoints

**Important**: When using PgBouncer in **transaction pooling** mode, set `CONN_MAX_AGE = 0` in
Django settings. Persistent connections conflict with transaction-level pooling.

#### PgBouncer Installation

```bash
# Ubuntu/Debian
apt-get install pgbouncer

# Docker
docker run -d --name pgbouncer \
    -e DATABASE_URL="postgres://user:pass@postgres:5432/restaurantflow" \
    -e POOL_MODE=transaction \
    -p 6432:6432 \
    edoburu/pgbouncer
```

#### pgbouncer.ini Example

```ini
[databases]
restaurantflow = host=localhost port=5432 dbname=restaurantflow

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 6432
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt

; Transaction pooling — compatible with Django
pool_mode = transaction

; Pool size per database/user combination
default_pool_size = 20
max_client_conn = 500
reserve_pool_size = 5

; Connection timeouts
connect_timeout = 10
server_idle_timeout = 600
client_idle_timeout = 300

; Logging
log_connections = 0
log_disconnections = 0
log_pooler_errors = 1
```

#### Django settings when using PgBouncer

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "restaurantflow",
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": "pgbouncer_host",   # point to PgBouncer, not Postgres
        "PORT": "6432",
        "CONN_MAX_AGE": 0,          # let PgBouncer manage pooling
    }
}
```

---

## 2. Celery Queue Layout

### 2.1 Queue Design

RestaurantFlow uses four Celery queues to separate tasks by priority and resource requirements:

| Queue | Tasks Routed | Priority | Use Case |
|---|---|---|---|
| `default` | All other tasks | Medium | Order events, billing, misc |
| `notifications` | `notifications.*` | High | Real-time user notifications — keep latency low |
| `maintenance` | `crm.*`, `marketing.*` | Low | Background analytics, campaign delivery |
| `reports` | `reports.*` (future) | Medium | Report generation, CSV exports |

### 2.2 CELERY_TASK_ROUTES

Configured in `backend/config/settings.py`:

```python
CELERY_TASK_ROUTES = {
    "notifications.*": {"queue": "notifications"},
    "crm.*":           {"queue": "maintenance"},
    "marketing.*":     {"queue": "maintenance"},
}
```

Tasks not matching any pattern go to the `default` queue.

### 2.3 Starting Workers

Start a separate Celery worker process for each queue to control concurrency independently:

```bash
# Default queue — handles orders, billing, misc events
celery -A config worker \
    --queues=default \
    --concurrency=4 \
    --hostname=worker-default@%h \
    --loglevel=info

# Notifications queue — keep latency low with higher concurrency
celery -A config worker \
    --queues=notifications \
    --concurrency=4 \
    --hostname=worker-notifications@%h \
    --loglevel=info

# Maintenance queue — background work, lower concurrency to avoid DB saturation
celery -A config worker \
    --queues=maintenance \
    --concurrency=2 \
    --hostname=worker-maintenance@%h \
    --loglevel=info

# Celery Beat — only one instance must run at a time
celery -A config beat \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --loglevel=info
```

### 2.4 Celery Concurrency Guidance

| Queue | Recommended Concurrency | Reason |
|---|---|---|
| `default` | `2 × CPU + 1` per instance | Mixed I/O + CPU workload |
| `notifications` | 4–8 per instance | I/O-bound (HTTP calls, Redis writes) |
| `maintenance` | 1–2 per instance | Avoid bulk DB query saturation |
| `reports` | 1 per instance | CPU + DB intensive; run on a dedicated worker |

### 2.5 Task Time Limits

Global limits set in settings (Phase 22):

```python
CELERY_TASK_TIME_LIMIT = 300       # hard kill at 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # SoftTimeLimitExceeded at 4 minutes
```

Individual tasks may override these with smaller values using `@shared_task(time_limit=X)`.

---

## 3. Horizontal Scaling

### 3.1 Gunicorn Instances

RestaurantFlow's Django application is stateless — each Gunicorn worker reads from the same
PostgreSQL database and writes to the same Redis cache. Multiple instances can run behind a
load balancer (Nginx, AWS ALB, GCP Cloud Load Balancing) with no changes to the application.

**Recommended configuration per instance**:

```
CPU:     2–4 cores
RAM:     1–2 GB
Workers: 2 × CPU + 1  (e.g., 5 workers on a 2-core instance)
```

**Nginx upstream example**:

```nginx
upstream restaurantflow_backend {
    least_conn;
    server app1:8000 max_fails=3 fail_timeout=30s;
    server app2:8000 max_fails=3 fail_timeout=30s;
    server app3:8000 max_fails=3 fail_timeout=30s;
}
```

### 3.2 Django Channels (WebSocket)

The WebSocket layer uses Redis as the channel layer backend. Multiple Django Channels instances
(ASGI server via Daphne or Uvicorn) connect to the same Redis and fan-out messages correctly.

Scale WebSocket workers independently from HTTP workers if the kitchen display or notifications
traffic is significantly higher than REST API traffic.

```bash
# ASGI server — start multiple instances behind a WebSocket-capable load balancer
daphne -b 0.0.0.0 -p 8001 config.asgi:application
```

### 3.3 Database

PostgreSQL scaling options (in order of complexity):

1. **Vertical scaling** — increase CPU and RAM on the primary. Most cost-effective first step.
2. **Read replicas** — route reporting and dashboard queries to a replica using Django's database
   router. Write operations (orders, payments) always go to primary.
3. **PgBouncer** — connection pooler (see Section 1.2) to handle connection surge from many workers.
4. **Table partitioning** — partition `orders_order`, `billing_bill`, and `notifications_notification`
   by `created_at` (monthly or quarterly) once rows exceed 10M. Requires careful migration.

### 3.4 Redis

Redis is used for:
- Django cache (dashboard KPIs, reporting summaries, unread counts)
- Celery broker and result backend
- Django Channels layer

For high availability, deploy Redis Sentinel or Redis Cluster. The application configuration
requires only a URL change (`REDIS_URL`).

---

## 4. Performance Targets

| Operation | Target p95 Latency | Notes |
|---|---|---|
| Menu catalog GET | < 100 ms | Cache-first after Phase 22 caching wired in |
| Order list GET | < 200 ms | With select_related applied |
| Dashboard KPIs GET | < 500 ms | Cached 120 s; cold cache ≤ 2 s |
| Payment create POST | < 300 ms | Transactional with select_for_update |
| Notification delivery | < 2 s end-to-end | Via Celery notifications queue |

Measure these with Locust (`performance/locustfile.py`) against staging before each release.

---

## 5. Pre-Deployment Checklist

Before scaling out:

- [ ] `DEBUG = False` in production settings
- [ ] `SECRET_KEY` set via environment variable (not default)
- [ ] `DB_PASSWORD` set via environment variable
- [ ] Redis running and reachable
- [ ] `python manage.py migrate` applied
- [ ] `python manage.py collectstatic` run
- [ ] Celery workers started for all queues
- [ ] Celery Beat started (exactly one instance)
- [ ] PgBouncer configured if `max_connections` pressure expected
- [ ] Load balancer health check pointing to `/api/health/` or similar
