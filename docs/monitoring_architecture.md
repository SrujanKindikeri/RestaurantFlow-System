# Monitoring Architecture — Phase 24

RestaurantFlow observability has three signals — **metrics**, **logs**, and
**traces** — and reuses the existing Central Control alert engine and
Notification delivery center rather than introducing a parallel system.

## Signal model

| Signal | Source | Transport | Storage | Consumption |
|---|---|---|---|---|
| Metrics | `observability` app (in-process registry) | `/metrics` (Prometheus text) | Prometheus TSDB | Grafana dashboards + alert rules |
| Logs | Django `LOGGING` (JSON formatter) | stdout | rotating files + (optional) Loki | Grafana log panel / log search |
| Traces | OpenTelemetry (optional) | OTLP | OTel collector / backend | OTel-compatible UI |

## Request flow (metrics + correlation)

1. `RequestCorrelationMiddleware` validates/generates `X-Request-ID`, binds a
   `LogContext` (request_id, user_id) for the request lifetime, echoes the id
   on the response.
2. `MetricsMiddleware` records `restaurantflow_http_requests_total`,
   `restaurantflow_http_request_duration_seconds`, `restaurantflow_http_errors_total`
   using low-cardinality labels (`route` = resolved view name, `method`,
   `status_class`). It skips `/metrics` and static paths, never breaks a
   request, and never uses user IDs / order IDs / raw URLs as labels.
3. Business modules call `observability.record_business_event(event, ...)`
   from failure paths, incrementing `restaurantflow_business_events_total`
   with low-cardinality `event`/`severity` labels and emitting a structured log.
4. Unhandled exceptions route through `core/exceptions.py` to
   `observability.error_tracking.capture_exception`, which logs a structured
   error with request_id + safe scope and optionally forwards to Sentry.

## Alert flow (metric-based)

```
Prometheus rule fires ─► Alertmanager (group/inhibit/dedupe/repeat)
   ─► POST /api/observability/alerts/am  (Authorization: Bearer token)
        ─► observability.alert_forwarder.handle_alertmanager_webhook
             ─► CentralAlert (existing fingerprint dedup + lifecycle)
                  ─► NotificationService (HIGH/CRITICAL only, existing delivery)
```

Recovery: Alertmanager sends `status=resolved`, which resolves the matching
active `CentralAlert` (no duplicate alert created).

## Components

- **Backend (`observability` app):** metrics registry, middleware, JSON
  logging, business events, Celery signals, alert forwarder, frontend error
  endpoint, optional tracing + Sentry init.
- **Stack (`deployment/monitoring/`):** Prometheus, Grafana, Alertmanager,
  node-exporter, cAdvisor, postgres-exporter, redis-exporter, blackbox-exporter.

## What is verified vs configured

| Item | Status |
|---|---|
| `/metrics` exposition + token gating | Verified (tests) |
| Alertmanager webhook → CentralAlert dedup/resolve | Verified (tests) |
| Central Control → Notification integration | Verified (tests) |
| Structured JSON logging + redaction | Verified (tests) |
| Request correlation propagation | Verified (tests) |
| Health `/health/dependencies/` | Verified (tests) |
| Live Prometheus scrape / exporters / Grafana rendering | Configured; runtime-verified on a deployment host |
| OpenTelemetry tracing | Configured; activates only with OTel packages + endpoint |
| Sentry error tracking | Configured; activates only with sentry-sdk + DSN |
