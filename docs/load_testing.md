# Load Testing Guide — RestaurantFlow

> **WARNING: NEVER run load tests against the production environment.**

## Overview of scenarios

| Scenario file                     | User class            | Endpoints exercised                                             |
|-----------------------------------|-----------------------|-----------------------------------------------------------------|
| `scenarios/auth.py`               | `AuthOnlyUser`        | POST /api/auth/login/, POST /api/auth/token/refresh/, GET /api/auth/me/ |
| `scenarios/orders.py`             | `RestaurantStaffUser`, `KitchenUser` | GET catalog, POST /api/orders/, PATCH confirm, POST finalize bill |
| `scenarios/payments.py`           | `PaymentUser`         | POST /api/payments/ (concurrent, same bill), GET payment summary |
| `scenarios/reporting.py`          | `ManagerUser`         | GET inventory dashboard, central-control dashboard, sales reports |

The payment scenario is the most critical: multiple `PaymentUser` instances
hit the same bill UUID simultaneously, which directly tests the
`select_for_update()` overpayment guard added in FEAT-001.

---

## Recommended concurrency levels

Start conservative and ramp up. These are baseline recommendations for a
single-server dev or staging environment (4 vCPU, 8 GB RAM, PostgreSQL on
the same host).

| Scenario                   | Starting -u | Max -u before latency degrades | Notes |
|----------------------------|-------------|--------------------------------|-------|
| Staff (order/billing)      | 20          | 80                             | Bounded by DB connection pool |
| Kitchen (status updates)   | 10          | 40                             | Light writes, mostly reads    |
| Manager (reporting)        | 5           | 20                             | Heavy aggregation queries     |
| Payment (concurrent)       | 10          | 30                             | Critical — monitors overpay guard |
| Mixed (all classes)        | 50          | 150                            | Use weighted distribution in locustfile |

For a horizontally scaled deployment (multiple Django workers behind a
load balancer), multiply the Max column by the number of worker instances.

---

## Running a load test

### Install

```bash
pip install locust
```

### Interactive

```bash
locust -f performance/locustfile.py --host http://localhost:8000
# Open http://localhost:8089
```

### Headless (CI)

```bash
locust -f performance/locustfile.py \
    --headless \
    --host http://localhost:8000 \
    -u 50 -r 5 \
    --run-time 60s \
    --csv results/run_$(date +%Y%m%d_%H%M%S)
```

---

## Interpreting Locust results

### Key metrics in the web UI and CSV

| Column / metric           | What it means                                                |
|---------------------------|--------------------------------------------------------------|
| **RPS (requests/sec)**    | Throughput; compare against your target SLA                  |
| **Median (50th pct)**     | The typical response time most users experience              |
| **95th percentile (p95)** | The slowest experience for 1 in 20 users — the SLA target    |
| **99th percentile (p99)** | Worst-case; important for financial operations               |
| **Failure %**             | Any value above 0.1 % warrants investigation                 |
| **Current RPS**           | Watch for a plateau — indicates you've saturated the server  |

### Reading the history chart

The history chart (`_history.csv`) plots RPS and response time over time.
A rising p95 with flat RPS indicates query degradation under load (index
miss or lock contention).  A falling RPS with rising failure % indicates
worker saturation or connection pool exhaustion.

---

## Acceptable performance thresholds

These are the targets for a standard branch-level deployment.  Exceeding
p95 consistently means an endpoint needs profiling.

| Endpoint category                    | p50 target | p95 target | p99 target |
|--------------------------------------|-----------|-----------|-----------|
| Auth (login, token refresh)          | < 100 ms  | < 300 ms  | < 500 ms  |
| Menu catalog (cached)                | < 50 ms   | < 150 ms  | < 300 ms  |
| Order creation                       | < 200 ms  | < 500 ms  | < 800 ms  |
| Bill finalization                    | < 300 ms  | < 700 ms  | < 1200 ms |
| Payment creation (with guard)        | < 300 ms  | < 600 ms  | < 1000 ms |
| Inventory dashboard                  | < 300 ms  | < 800 ms  | < 1500 ms |
| Reporting dashboard (single branch)  | < 500 ms  | < 1200 ms | < 2000 ms |
| Central Control dashboard            | < 800 ms  | < 2000 ms | < 4000 ms |

Failure rate target: **< 0.5 %** for all endpoints under the recommended
concurrency levels above.

---

## Correlating slow endpoints with profiling tools

### Django Debug Toolbar (development only)

Enable in `config/settings.py` with `DEBUG=True` and `INTERNAL_IPS`.
Then navigate to the endpoint in a browser and inspect the SQL panel.
Look for:

- **Duplicate queries**: same SQL appearing multiple times → N+1 regression.
- **Full table scans**: `Seq Scan` in the EXPLAIN output → missing index.
- **High query count**: > 20 queries for a list endpoint → missing prefetch.

### pg_stat_statements (staging / production profiling)

`pg_stat_statements` tracks cumulative stats for every query shape run
against PostgreSQL.  Enable it once and query it after a load test:

```sql
-- Top 10 slowest query shapes by total execution time
SELECT
    left(query, 100)         AS query,
    calls,
    round(total_exec_time::numeric, 2)  AS total_ms,
    round(mean_exec_time::numeric, 2)   AS mean_ms,
    rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;
```

Reset stats before a fresh run:

```sql
SELECT pg_stat_statements_reset();
```

Match the slow query shape back to a Django ORM call by:

1. Searching the query text in model `Meta.indexes` to check for a
   missing composite index.
2. Enabling `LOGGING` with `django.db.backends` to capture the full SQL
   with parameters during a manual request.
3. Using `EXPLAIN ANALYZE` on the slow query to confirm the plan.

### Correlating with Locust results

1. Run the load test with `--csv results/run_X`.
2. In `_stats.csv`, note endpoints with p95 > threshold.
3. Reset `pg_stat_statements`.
4. Replay only those endpoints at moderate load (`-u 10`).
5. Query `pg_stat_statements` for the top offenders.
6. Apply the fix (index, `select_related`, or caching) and rerun.

---

## Common causes and fixes

| Symptom                          | Likely cause                        | Fix                                     |
|----------------------------------|-------------------------------------|-----------------------------------------|
| p95 grows linearly with -u       | Lock contention (payments/billing)  | Confirm `select_for_update()` is used   |
| Reporting dashboard slow         | Missing composite index on date+branch | Add index; consider materialized view |
| Menu catalog not fast            | Cache miss on every request         | Confirm `invalidate_menu_catalog` works |
| DB connections exhausted         | Django worker count > pool size     | Tune `CONN_MAX_AGE` and pool size       |
| Failure % spikes at high -u      | Gunicorn worker timeout             | Increase `--timeout`; add workers       |
