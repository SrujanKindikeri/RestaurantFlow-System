# Observability Assessment — Phase 24

**Status:** Completed audit. Phase 24 implements the gaps identified here.
**Auditor notes:** Integrations below are described as *verified* only where
their presence was confirmed by reading the running codebase. Nothing is
claimed to exist that was not inspected.

---

## 1. Existing monitoring infrastructure

| Area | What exists (Phase 1–23) | Verified |
|---|---|---|
| Application logging | Django `LOGGING` config: `RotatingFileHandler` for `general.log`, `errors.log`, `security.log` (10 MB × 5 backups) + console. Per-app loggers (`accounts`, `core`, `orders`, `billing`, `kitchen`, `celery`, `notifications`, …). | Yes — `config/settings.py` |
| Log format | Human-readable text (`verbose`/`simple` formatters). | Yes |
| Health endpoints | `/health/`, `/health/live/` (liveness), `/health/ready/` (DB + Redis). | Yes — `common/views_health.py`, `config/urls.py` |
| Business alerting | Central Control (Phase 15): `CentralAlert` with fingerprint deduplication, severities (INFO/LOW/MEDIUM/HIGH/CRITICAL), lifecycle OPEN→ACKNOWLEDGED→RESOLVED/DISMISSED/EXPIRED, `AlertDetectionService` (kitchen/inventory/payment/financial/counter), `EscalationEngine`, `CentralSystemEvent` timeline, `CentralControlAuditLog`. | Yes — `central_control/` |
| Notification delivery | Notification & Communication Center (Phase 16): `NotificationService` with cooldown + idempotency, channels (in-app, websocket, email, SMS, WhatsApp, Telegram), retries, recipient resolution. | Yes — `notifications/` |
| Error handling | Custom DRF exception handler wrapping errors in a JSON envelope; logs unhandled exceptions. | Yes — `core/exceptions.py` |
| Celery | Broker + result backend via Redis; beat schedule; task routing to named queues; soft/hard time limits. | Yes — `config/settings.py`, `config/celery.py` |
| Django Channels | Redis channel layer; kitchen/central-control/notification WebSocket consumers. | Yes — `config/asgi.py`, `*/routing.py` |
| Deployment | Docker Compose: postgres, redis, backend, celery_worker, celery_beat, nginx. Prod overlay removes host ports for DB/Redis. | Yes — `docker-compose*.yml` |

**Confirmed absent (not present before Phase 24):** Prometheus, Grafana,
Alertmanager, any exporter (node/cAdvisor/postgres/redis/blackbox),
OpenTelemetry, Sentry, AWS CloudWatch. No `/metrics` endpoint. No structured
JSON logging. No request-correlation ID. No `/health/dependencies/`.

## 2. Missing metrics

- API request count, latency, error rate, status distribution — none exposed.
- Database connections, latency, deadlocks, lock waits, size, cache hit ratio.
- Redis memory, clients, hit/miss, evictions, latency.
- Celery worker up/down, queue depth, task success/failure/retry, task duration.
- WebSocket connections, events, errors, channel-layer failures.
- Nginx request/latency/upstream/cert metrics.
- Host/container CPU, memory, disk, network, restarts.
- Business operational event counters (order/payment/inventory/accounting failures).

## 3. Logging gaps

- No structured/JSON format → logs are not machine-parseable and not indexable by request ID.
- No request correlation ID (`X-Request-ID`) — a request and its logs/background tasks cannot be tied together.
- No safe tenant context (company/restaurant/branch) attached to log lines.
- No sensitive-data redaction (passwords, tokens, card data, auth headers).
- No exception structure (type/message/trace) in a parseable field.
- No log aggregation target (Loki etc.) — only local rotating files.

## 4. Monitoring risks

- **Silent failures:** unhandled backend exceptions and background-task failures are invisible until a customer reports them.
- **No SLO signal:** error rate and latency regressions cannot be detected before they affect operations.
- **Cache/broker blind spots:** Redis exhaustion or Celery queue backlogs are not surfaced.
- **Security exposure risk:** without token gating, a `/metrics` endpoint could leak operational data; without redaction, logs could contain secrets.

## 5. Alerting gaps

- Central Control alerts are **business-condition** alerts (kitchen delay, low stock, payment failure…). There was **no path for metric-based infrastructure alerts** (API down, DB down, disk full, cert expiring) to reach Central Control or the notification center.
- No deduplication/cooldown/recovery lifecycle for metric-based alerts.
- No severity-mapped routing from a metric alerting engine.

## 6. Proposed architecture (implemented in Phase 24)

```
RESTAURANTFLOW (Django/Celery/Nginx) — /metrics (token-gated, Prometheus format)
        |
   PROMETHEUS  ── rules ──► ALERTMANAGER ── webhook(token) ──► /api/observability/alerts/am
        |                                                            |
   GRAFANA (dashboards)                          CentralAlert (existing dedup/lifecycle)
                                                                         |
                                                            NotificationService (existing delivery)
```

- **Metrics:** a dependency-free Prometheus-format registry in a new `observability` app (no `prometheus-client` needed), exposed at `/metrics` with low-cardinality labels and a cardinality cap.
- **Logs:** structured JSON formatter + request-correlation contextvar, switched on with `LOG_FORMAT=json`; redaction applied to every record.
- **Tracing:** OpenTelemetry configured but **optional** — activated only when the OTel packages are installed and `OTEL_EXPORTER_OTLP_ENDPOINT` is set.
- **Error tracking:** structured local logging by default; Sentry **optional** (`SENTRY_DSN` + `sentry-sdk`).
- **Alerts:** Alertmanager forwards metric alerts into the **existing** `CentralAlert` model; HIGH/CRITICAL alerts are delivered via the **existing** `NotificationService`. No duplicate alert engine or notification system is created.

## 7. Resource requirements

- App overhead: metrics registry is in-process, ~low; per-request middleware cost is negligible (no extra I/O).
- Monitoring stack (optional): ~1.3 GB memory cap with the limits in `docker-compose.monitoring.yml`; persistent volumes for Prometheus/Grafana/Alertmanager data.
- Tracing/Sentry overhead is controlled by sampling config and is off by default.

## 8. Deployment changes required

- New env vars (documented in `docs/environment_configuration`/settings): `LOG_FORMAT`, `PROMETHEUS_SCRAPE_TOKEN`, `ALERTMANAGER_WEBHOOK_TOKEN`, `OBSERVABILITY_MONITORING_ORG_ID`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `SENTRY_DSN`, `THROTTLE_FRONTEND_ERRORS`.
- Provision token secret files for Prometheus/Alertmanager (see `deployment/monitoring/README.md`).
- Merge the monitoring overlay only when desired (`-f deployment/monitoring/docker-compose.monitoring.yml`).
- Frontend: wire the frontend error capture endpoint (`/api/observability/frontend-errors`) into the app's global error handler.

## Pre-existing test-suite baseline (out of Phase 24 scope)

Before any Phase 24 change, the committed Phase 1–23 suite reported
**163 failures / 733 errors** under the SQLite test settings. The dominant
signature is `AssertionError: 403 != 200` (~145 cases) caused by **cross-test
cache isolation** (the in-process permission cache outlives `TestCase`
transaction rollback) — these tests pass in isolation. A smaller set are
genuine pre-existing app bugs (`Branch() slug kwarg`, `decimal.Decimal`
subtraction, `KeyError: 'categories'`, `'HttpResponseNotFound' has no attribute
'data'`, `NotificationTestBase._make_notification` kwarg, `restaurant_count`
property). None relate to observability.

Phase 24 fixed one trivial, reused-path bug (`NameError:
ALERT_TYPE_PAYMENT_EXCEPTION` in `central_control/alert_rules.py`), reducing
errors to **731** with **no new failures** introduced, and adds **48 passing**
observability tests. Repairing the broader pre-existing suite is out of scope
for the monitoring phase.
