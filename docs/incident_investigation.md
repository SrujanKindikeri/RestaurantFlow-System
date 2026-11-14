# Incident Investigation — Phase 24

## 1. Detect

- **Grafana** Application Overview → check API availability, error rate, latency.
- **Central Control** (in-app) → open `CentralAlert`s by severity/type.
- **Alertmanager** UI (`:9093` internal) → firing vs resolved alerts.

## 2. Correlate by request ID

Every response carries `X-Request-ID`. Search logs by that id:

```bash
# JSON logs (stdout) — grep the request_id field
docker compose logs backend | jq -c "select(.request_id==\"<id>\")"

# rotating files
grep "<id>" backend/logs/errors.log
```

The same `request_id` propagates into Celery task logs where present, so a
request and its background work share a correlation id.

## 3. Trace (if OTel enabled)

Open the trace in your OTel backend using the `request_id` span attribute, or
query by the affected service. Sampling is configurable via
`OTEL_TRACES_SAMPLER_ARG`.

## 4. Inspect the failing component

| Symptom | Where to look |
|---|---|
| High API error rate | `restaurantflow_http_errors_total` by route; `errors.log`; Sentry (if enabled) |
| DB deadlocks / slow queries | PostgreSQL dashboard; `pg_stat_activity`; check long-running transactions |
| Redis evictions / memory | Redis dashboard; check cache TTLs / large keys |
| Celery backlog / failures | Celery dashboard; `celery_task_failures_total`; inspect task logs (no args) |
| WebSocket failures | `restaurantflow_websocket_errors_total`; channel-layer (Redis) health |
| Disk full / CPU saturation | Infrastructure dashboard; `node-exporter` |
| Cert expiry | `RestaurantFlowCertNearingExpiry`; blackbox `probe_ssl_earliest_cert_expiry` |

## 5. Resolve & confirm

- Acknowledge the `CentralAlert` (OPEN → ACKNOWLEDGED); resolve with a note
  when fixed (CRITICAL requires a note). The lifecycle and audit trail are
  preserved (Phase 15 `CentralControlAuditLog`).
- For metric alerts, once Prometheus stops firing, Alertmanager sends
  `resolved` and the matching alert auto-resolves.

## Safe-handling rules

- Never paste secrets, tokens, card data, or customer PII into tickets or
  external trackers. Logs redact sensitive keys, but treat any raw output as
  potentially sensitive.
- Stack traces in logs contain no local-variable values (traceback only), but
  still review before sharing externally.
- The audit trail (`CentralControlAuditLog`, accounting/payment audit logs) is
  authoritative for business history — application logs are diagnostic only.
