# Scalability Guide — RestaurantFlow (Phase 22)

**Purpose**: Operational guide for scaling RestaurantFlow horizontally across Gunicorn workers,
Celery workers, and an optional PgBouncer connection pooler. Updated in Phase 22 to include
Redis memory configuration, Nginx connection handling, PostgreSQL autovacuum tuning,
container resource guidance, and scaling milestones.

---

## 1. Database Connection Management

### 1.1 CONN_MAX_AGE (Django Persistent Connections)

**Recommended setting**: `DATABASES['default']['CONN_MAX_AGE'] = 60`

Gunicorn sync workers handle one HTTP request at a time per process. Without persistent
connections, every request pays the cost of opening and authenticating a new PostgreSQL
connection — typically 5–20 ms of overhead. With `CONN_MAX_AGE = 60`, each Gunicorn worker
keeps its database connection alive for up to 60 seconds of idle time.

Effects:
- Peak DB connections ≈ number of Gunicorn workers (predictable, bounded)
- No connection surge on restart — connections re-establish gradually
- Connections idle for 60 seconds are recycled automatically, preventing accumulation from
  crashed or redeployed workers

**PostgreSQL `max_connections`**: set to at least `(gunicorn_workers × instances) + 20`
to account for migrations, management commands, and monitoring overhead.

> **Important**: if you deploy PgBouncer in **transaction pooling** mode, set
> `CONN_MAX_AGE = 0` in Django. Persistent connections conflict with transaction-level pooling.

---

### 1.2 PgBouncer — Optional External Connection Pooler

PgBouncer sits between Django and PostgreSQL and multiplexes many client connections to a
smaller pool of server connections. It is optional but recommended when:
- More than four Gunicorn instances run simultaneously
- PostgreSQL `max_connections` pressure appears in monitoring
- Short-lived connection overhead is measurable on high-traffic endpoints

#### Installation

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

; Transaction pooling — compatible with Django (requires CONN_MAX_AGE = 0)
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
        "HOST": "pgbouncer_host",   # point to PgBouncer, not Postgres directly
        "PORT": "6432",
        "CONN_MAX_AGE": 0,          # let PgBouncer manage pooling
    }
}
```

---

## 2. Gunicorn Worker Formula

### 2.1 Formula

```
workers = 2 × CPU_COUNT + 1
```

This formula balances CPU-bound processing with I/O wait (database queries, Redis lookups,
network calls). Most Django views are I/O-bound, so the extra worker per core allows the
OS to context-switch while one worker waits for the database.

### 2.2 Development

```bash
gunicorn config.wsgi:application \
    --workers 1 \
    --reload \
    --bind 0.0.0.0:8000 \
    --timeout 120
```

One worker with `--reload` enables code reloading without restarts. Never use `--reload`
in production.

### 2.3 Small Production (example: 4-core host)

```bash
# 4-core host → 2×4+1 = 9 workers
gunicorn config.wsgi:application \
    --workers 9 \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 5 \
    --worker-class sync
```

### 2.4 Growing Deployment

As traffic grows, scale in this order:

1. Add Gunicorn workers to the formula limit (`2 × CPU + 1`)
2. Add Celery workers for background task throughput (see Section 3)
3. Add a second application instance behind a load balancer
4. Add read replicas for reporting and dashboard queries (see Section 9)

---

## 3. Celery Concurrency by Queue

### 3.1 Queue Design

RestaurantFlow uses four Celery queues:

| Queue | Tasks Routed | Priority |
|---|---|---|
| `default` | Orders, billing, miscellaneous | Medium |
| `notifications` | `notifications.*` | High |
| `maintenance` | `crm.*`, `marketing.*` | Low |
| `reports` | `reports.*` (future) | Medium |

### 3.2 Recommended Worker Concurrency

| Queue | Concurrency | Reason |
|---|---|---|
| `default` | `2 × CPU + 1` per worker instance | Mixed I/O + CPU |
| `notifications` | 4–8 per instance | I/O-bound: HTTP calls, Redis writes |
| `maintenance` | 1–2 per instance | Avoid bulk DB query saturation |
| `reports` | 1 per instance | CPU + DB intensive; use a dedicated worker |

### 3.3 Starting Workers

```bash
# Default queue
celery -A config worker \
    --queues=default \
    --concurrency=4 \
    --hostname=worker-default@%h \
    --loglevel=info

# Notifications queue — higher concurrency for low-latency delivery
celery -A config worker \
    --queues=notifications \
    --concurrency=4 \
    --hostname=worker-notifications@%h \
    --loglevel=info

# Maintenance queue — lower concurrency to protect DB
celery -A config worker \
    --queues=maintenance \
    --concurrency=2 \
    --hostname=worker-maintenance@%h \
    --loglevel=info

# Celery Beat — exactly one instance must run
celery -A config beat \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler \
    --loglevel=info
```

### 3.4 Task Time Limits

```python
CELERY_TASK_TIME_LIMIT = 300       # hard kill at 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # SoftTimeLimitExceeded at 4 minutes
```

Individual tasks may override these with `@shared_task(time_limit=X)`.

---

## 4. Redis Memory Configuration

### 4.1 maxmemory

Set `maxmemory` to 20–25% of the host's available RAM. This leaves memory for the OS, Django
processes, and Celery workers sharing the same host, while giving Redis enough headroom to
absorb burst traffic without swapping.

Example for a host with 8 GB RAM:

```
# redis.conf
maxmemory 2gb
```

For a 16 GB host, 3–4 GB is appropriate.

### 4.2 maxmemory-policy

```
maxmemory-policy allkeys-lru
```

`allkeys-lru` evicts the least-recently-used key across all keys (not just those with a TTL)
when memory reaches `maxmemory`. For RestaurantFlow's cache workload — where keys have TTLs
of 60–600 seconds — this policy means stale cache entries are the first to go, which is the
desired behaviour.

**Do not use** `noeviction` in a shared Redis instance: it causes writes to fail when memory
is full, which breaks Celery task queuing.

### 4.3 Separating Cache and Channel Layer

The Django cache and the Django Channels channel layer both use Redis. Under high notification
traffic, channel layer writes can consume cache memory and trigger unexpected evictions.
Use separate Redis databases (or separate Redis instances) for each:

```python
# settings.py
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": "redis://redis:6379/1",   # DB 1 for cache
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [("redis", 6379, {"db": 2})]},  # DB 2 for channels
    }
}
```

---

## 5. Container Resource Limits

Container limits should be tuned from observed usage (use `docker stats` or Prometheus + cAdvisor).
The ranges below are starting points, not hard targets.

| Service | CPU request | CPU limit | Memory request | Memory limit |
|---|---|---|---|---|
| Django (Gunicorn) | 0.25 CPU | 1–2 CPU | 256 MB | 512 MB–1 GB |
| Celery worker (default/notifications) | 0.25 CPU | 1 CPU | 256 MB | 512 MB |
| Celery worker (maintenance) | 0.1 CPU | 0.5 CPU | 128 MB | 256 MB |
| Celery Beat | 0.05 CPU | 0.1 CPU | 64 MB | 128 MB |
| Redis | 0.1 CPU | 0.5 CPU | 256 MB | Matches `maxmemory` + 15% overhead |
| Nginx | 0.1 CPU | 0.25 CPU | 32 MB | 64 MB |

Increase Django memory limits if you observe OOM kills on large reporting requests.
CPU limits above 2 per Gunicorn container rarely help — add more container replicas instead.

---

## 6. Nginx Connection Handling

### 6.1 Minimal nginx.conf

```nginx
worker_processes auto;          # one worker per CPU core

events {
    worker_connections 1024;    # max simultaneous connections per worker
}

http {
    keepalive_timeout 65;       # keep client connections alive 65 seconds

    upstream restaurantflow_backend {
        least_conn;
        server app1:8000 max_fails=3 fail_timeout=30s;
        server app2:8000 max_fails=3 fail_timeout=30s;
        keepalive 32;           # pool of 32 keepalive connections to upstream
    }

    server {
        listen 80;
        server_name _;

        location / {
            proxy_pass http://restaurantflow_backend;
            proxy_http_version 1.1;
            proxy_set_header Connection "";          # required for upstream keepalive
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 10s;
            proxy_read_timeout 120s;
        }

        location /ws/ {
            proxy_pass http://daphne_backend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "Upgrade";
            proxy_set_header Host $host;
            proxy_read_timeout 86400s;              # keep WebSocket open for up to 24 h
        }

        location /static/ {
            alias /app/static/;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
```

**`worker_processes auto`** scales Nginx worker count to CPU core count automatically.

**`worker_connections 1024`** sets the maximum simultaneous connections per Nginx worker.
Total concurrent connections = `worker_processes × worker_connections`.

**`keepalive_timeout 65`** matches the typical browser keepalive timeout, reducing TCP
handshake overhead for repeat requests from the same client.

**`keepalive 32`** in the upstream block maintains a pool of persistent connections from
Nginx to Gunicorn, avoiding a new TCP handshake per proxied request.

---

## 7. Autovacuum and PostgreSQL Maintenance

### 7.1 Why Autovacuum Matters

RestaurantFlow is a write-heavy OLTP workload. Tables like `orders_order`,
`billing_bill`, `payments_payment`, and `notifications_notificationrecipient`
accumulate dead tuples from updates and deletes. Without timely vacuuming, table
bloat increases I/O and query times; without timely analysis, the query planner
uses stale statistics.

### 7.2 Recommended autovacuum Settings

PostgreSQL's default scale factors target infrequently updated tables. For
high-write tables, reduce them so autovacuum triggers more often:

```sql
-- Set per-table on high-write tables
ALTER TABLE orders_order SET (
    autovacuum_vacuum_scale_factor = 0.01,    -- trigger VACUUM when 1% of rows are dead
    autovacuum_analyze_scale_factor = 0.005   -- trigger ANALYZE when 0.5% of rows changed
);

ALTER TABLE billing_bill SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);

ALTER TABLE payments_payment SET (
    autovacuum_vacuum_scale_factor = 0.01,
    autovacuum_analyze_scale_factor = 0.005
);

ALTER TABLE notifications_notificationrecipient SET (
    autovacuum_vacuum_scale_factor = 0.02,
    autovacuum_analyze_scale_factor = 0.01
);
```

The PostgreSQL global defaults (`autovacuum_vacuum_scale_factor = 0.2`,
`autovacuum_analyze_scale_factor = 0.1`) are suitable for small or rarely-updated tables.
Lowering them on specific large tables avoids over-vacuuming the entire database.

### 7.3 After Bulk Loads

Always run `VACUUM ANALYZE` manually after any bulk import, data migration, or large batch
delete. The autovacuum daemon may not trigger quickly enough after a bulk operation, leaving
the query planner with stale row estimates.

```sql
VACUUM ANALYZE orders_order;
VACUUM ANALYZE billing_bill;
VACUUM ANALYZE inventory_stockmovement;
```

---

## 8. Known Remaining Bottlenecks

For the full baseline assessment, see `docs/performance_assessment_phase22.md`.

The following items were identified during Phase 22 and deferred:

| Priority | Bottleneck | Location | Deferred Reason |
|---|---|---|---|
| Medium | N+1 on `is_occupied` / `active_session_id` | `orders/serializers.py` — `DiningTableSerializer` | Requires annotation + prefetch refactor |
| Medium | N+1 on `item_count` per Order | `orders/serializers.py` | Replace `self.items.count()` with `annotate(item_count=Count('items'))` |
| Medium | N+1 on `active_prices` / `branch_availability` | `menu/serializers.py` | Requires `prefetch_related` on `prices` and `MenuItemBranch` |
| Medium | Unbounded Kitchen WS payload on connect | `kitchen/consumers.py` | Full KO list sent on connect; should filter to `PENDING/ACCEPTED/PREPARING` |
| Low | No `react-window` list virtualisation | `InventoryItemsPage`, `MenuItems` | Below threshold at current row counts (<200); add if rows exceed 500 |
| Low | Missing composite index `(branch, status, created_at)` on `orders_order` | `orders/models.py` | Added in FEAT-001 as `(branch, status)` and `(branch, created_at)` separately |
| Low | Missing composite index `(branch, status, expense_date)` on `financials_expense` | `financials/models.py` | Not addressed in Phase 22 |
| Low | Cache invalidation hooks not wired into all write paths | `common/caching/invalidation.py` | Infrastructure complete; wiring partially done in FEAT-002 |
| Low | No `maxmemory` / `maxmemory-policy` in Redis container config | `docker-compose.yml` | Documented here; docker-compose update deferred |

---

## 9. Scaling Milestones

These are the operational triggers to watch for and act on:

### Add Read Replicas
**Trigger**: sustained read load above 70% of the primary's query throughput for more than
15 minutes. Observable via `pg_stat_activity` or a monitoring tool (Prometheus + postgres_exporter).

**Action**: provision a PostgreSQL streaming replica; add a database router in
`config/db_router.py` to send reporting, dashboard, and analytics queries to the replica.
Write operations (orders, payments, billing, inventory deductions) always go to primary.

### Add Celery Workers
**Trigger**: queue depth above 1 000 tasks in any single queue for more than 5 consecutive
minutes. Monitor with `celery -A config inspect active` or Flower.

**Action**: add worker containers/processes for the saturated queue. Scale `notifications`
and `default` queues independently — do not let notification backlog block order processing.

### Consider Table Sharding or Partitioning
**Trigger**: a single-tenant table exceeds 50 million rows (check with
`SELECT reltuples FROM pg_class WHERE relname = 'orders_order'`).

**Action**: implement PostgreSQL declarative partitioning by `created_at` (monthly or
quarterly) for `orders_order`, `billing_bill`, and `notifications_notification`. This is
a significant migration; plan for a maintenance window and test on a copy of production data
first.

### Upgrade from Vertical to Horizontal Scaling
**Trigger**: a single Gunicorn instance consistently runs at > 80% CPU under normal load.

**Action**: place two or more Gunicorn instances behind Nginx (`least_conn` upstream). The
application is stateless — no code changes are required. Ensure Redis and PostgreSQL are
reachable from all instances.

---

## 10. Horizontal Scaling

### 10.1 Gunicorn Instances

RestaurantFlow's Django application is stateless — each worker reads from the same PostgreSQL
database and the same Redis cache. Multiple instances run behind a load balancer (Nginx, AWS ALB,
GCP Cloud Load Balancing) with no application changes.

**Recommended configuration per instance**:
```
CPU:     2–4 cores
RAM:     1–2 GB
Workers: 2 × CPU + 1  (5 workers on a 2-core instance)
```

### 10.2 Django Channels (WebSocket)

The WebSocket layer uses Redis as the channel layer backend. Multiple Daphne/Uvicorn instances
connect to the same Redis and fan-out messages correctly.

Scale WebSocket workers independently from HTTP workers if kitchen display or notification
traffic significantly exceeds REST API traffic.

```bash
daphne -b 0.0.0.0 -p 8001 config.asgi:application
```

### 10.3 Database

PostgreSQL scaling options in order of complexity:

1. **Vertical scaling** — increase CPU and RAM on the primary. Most cost-effective first step.
2. **Read replicas** — route reporting and dashboard queries to a replica (see Section 9).
3. **PgBouncer** — connection pooler for connection surge from many workers (see Section 1.2).
4. **Table partitioning** — partition `orders_order`, `billing_bill`, `notifications_notification`
   by `created_at` once rows exceed 10M per tenant.

---

## 11. Performance Targets

| Operation | Target p95 Latency | Notes |
|---|---|---|
| Menu catalog GET | < 100 ms | Cache-first after Phase 22 caching wired in |
| Order list GET | < 200 ms | With `select_related` applied |
| Dashboard KPIs GET | < 500 ms | Cached 120 s; cold cache ≤ 2 s |
| Payment create POST | < 300 ms | Transactional with `select_for_update` |
| Notification delivery | < 2 s end-to-end | Via Celery notifications queue |

Measure with Locust (`performance/locustfile.py`) against staging before each release.
See `docs/load_testing.md` for instructions and thresholds.

---

## 12. Pre-Deployment Checklist

Before scaling out:

- [ ] `DEBUG = False` in production settings
- [ ] `SECRET_KEY` set via environment variable
- [ ] `DB_PASSWORD` set via environment variable
- [ ] Redis running with `maxmemory` and `allkeys-lru` configured
- [ ] `python manage.py migrate` applied
- [ ] `python manage.py collectstatic` run
- [ ] Celery workers started for all queues (`default`, `notifications`, `maintenance`)
- [ ] Celery Beat started (exactly one instance)
- [ ] PgBouncer configured if `max_connections` pressure expected (set `CONN_MAX_AGE = 0`)
- [ ] Nginx configured with `worker_processes auto` and upstream keepalive
- [ ] Container resource limits set and verified against observed usage
- [ ] Load balancer health check pointing to `/api/health/` or similar
- [ ] `autovacuum_vacuum_scale_factor` tuned on high-write tables

---

## Frontend Performance

*Added in Phase 22 — FEAT-003.*

### Optimisations Applied

#### 1. Route-level lazy loading (`src/App.tsx`)

All page-level components except `LoginPage`, `RegisterPage`, `DashboardPage`, and `NotFoundPage`
are imported with `React.lazy`. Auth pages are eager because they are the first view on a cold
load. The `Suspense` fallback was updated from a plain text string to a `RouteLoadingSkeleton`
component (animated spinner + pulse bars) for a better perceived loading experience.

**Files changed**: `frontend/src/App.tsx`

---

#### 2. `React.memo` on expensive pure components

Components that receive stable props but sit inside a parent that re-renders frequently were
wrapped with `React.memo`. On the kitchen board, each status column re-renders every time an
order in *any* column changes status; `React.memo` prevents the unchanged columns from diffing
their subtrees.

| Component | File | Reason |
|---|---|---|
| `TableCard` | `components/orders/TableCard.tsx` | Rendered in a grid; only the clicked/changed card should update |
| `TableGrid` | `components/orders/TableGrid.tsx` | Contains 10–50 `TableCard` elements; re-mounts are expensive |
| `KitchenStatusColumn` | `components/kitchen/KitchenStatusColumn.tsx` | Five columns on the KDS board; each should be independent |
| `KitchenOrderCard` | `components/kitchen/KitchenOrderCard.tsx` | Already memoized in a prior phase |
| `MenuItemCard` | `components/orders/MenuItemCard.tsx` | Already memoized in a prior phase |
| `StatCard` | `components/ui/StatCard.tsx` | Already memoized in a prior phase |

---

#### 3. Debounced search inputs (300 ms)

Search inputs that immediately triggered an API call on every keystroke were updated to route
through the existing `useDebounce(value, 300)` hook before the value is passed to the data-
fetching hook or callback.

| Page | File | Change |
|---|---|---|
| Users list | `pages/users/UsersListPage.tsx` | Added `useDebounce` before `useUsers({ search: debouncedSearch })` |
| Bill list | `pages/billing/BillListPage.tsx` | Added `useDebounce` for `bill_number` and `order_number` text inputs |
| Menu items | `pages/menu/MenuItems.tsx` | Already debounced (no change) |
| Inventory items | `pages/inventory/InventoryItemsPage.tsx` | Already debounced (no change) |
| Customer list | `pages/crm/CustomerListPage.tsx` | Already debounced (no change) |

---

#### 4. Virtualisation

**Finding**: Neither `react-window` nor `react-virtual` is in `package.json`. All paginated
tables use server-side pagination with a default page size of 20. The largest in-memory list
is the inventory items table, which renders whatever the server returns. Under normal operating
conditions (<200 items per restaurant) this is below the threshold where virtualisation provides
a measurable benefit.

**Decision**: No virtualisation added. If a deployment grows to restaurants with >500 inventory
items and the page starts showing visible jank, add `react-window` to `package.json` and wire
`FixedSizeList` into `InventoryItemsPage` and `MenuItems`.

---

#### 5. `AbortController`-based request cancellation

`useEffect` hooks that issue fetch/axios calls now create an `AbortController` and pass its
`signal` to the service function. The cleanup function calls `controller.abort()` so that if the
component unmounts or its dependency changes before the request resolves, the in-flight request
is cancelled and stale state updates are skipped.

| File | Signal passed via |
|---|---|
| `pages/billing/BillListPage.tsx` | `listBills(params, controller.signal)` |
| `pages/billing/BillingDashboard.tsx` | `listBills({ page: 1 }, controller.signal)` |
| `pages/crm/CustomerListPage.tsx` | `crmApi.listCustomers(params, controller.signal)` |
| `pages/inventory/InventoryItemsPage.tsx` | `listInventoryItems(params, signal)` + `listCategories(params, signal)` |
| `pages/central-control/SystemHealthPage.tsx` | `centralControlApi.getSystemHealth(signal)` — also cancels interval fetches |
| `pages/central-control/RestaurantHealthPage.tsx` | `centralControlApi.getRestaurantHealth(undefined, signal)` |

Service functions updated to accept `signal?: AbortSignal`:
- `services/billing.ts` — `listBills`
- `services/crm.ts` — `listCustomers`
- `services/inventory.ts` — `listInventoryItems`, `listCategories`
- `services/centralControl.ts` — `getSystemHealth`, `getRestaurantHealth`

---

#### 6. Vite chunk splitting (`vite.config.ts`)

`manualChunks` was already present. The configuration was updated to separate `react` / `react-dom`
into a `vendor` chunk and `react-router-dom` into a `router` chunk. This allows the browser to
cache them independently — the router chunk changes on React Router upgrades while the React core
chunk stays stable across releases.

| Chunk | Libraries |
|---|---|
| `vendor` | `react`, `react-dom` |
| `router` | `react-router-dom` |
| `vendor-query` | `@tanstack/react-query` |
| `vendor-charts` | `recharts` |

**File changed**: `frontend/vite.config.ts`

---

#### 7. Loading skeletons

| Location | Before | After |
|---|---|---|
| Route `Suspense` fallback (`App.tsx`) | Plain `"Loading..."` text | `RouteLoadingSkeleton` — spinner + two pulse bars |
| Billing Dashboard recent bills list | `"Loading…"` text string | Four `Skeleton` rows (`h-14`) |
| `StatCard` | Already had `animate-pulse` placeholder | No change |
| Order list / Bill list / Inventory items | Already used `Skeleton` rows | No change |
