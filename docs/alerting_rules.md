# Alerting Rules — Phase 24

Metric-based alerts live in
`deployment/monitoring/prometheus/rules/alerting_rules.yml`. Alertmanager
routes them to `POST /api/observability/alerts/am`, which forwards them into
the existing `CentralAlert` model. Business-condition alerts (kitchen, stock,
payments, …) continue to be detected by the Phase 15 `AlertDetectionService`
and are unchanged.

## Severities (map to CentralControl)

`critical → CRITICAL`, `high → HIGH`, `warning → MEDIUM`, `info → INFO`.

## Rules

| Alert | Condition | For | Severity |
|---|---|---|---|
| RestaurantFlowApiDown | `up{job="restaurantflow-api"} == 0` | 2m | critical |
| RestaurantFlowHighErrorRate | 5xx ratio > 5% per route | 5m | high |
| RestaurantFlowHighLatency | p95 latency > 2s per route | 10m | warning |
| RestaurantFlowCeleryWorkersDown | `celery_worker_up == 0` | 3m | high |
| RestaurantFlowCeleryQueueBacklog | queue depth > 500 | 10m | warning |
| RestaurantFlowCeleryTaskFailures | failures > 0.5/s | 5m | high |
| RestaurantFlowPostgresDown | `pg_up == 0` | 2m | critical |
| RestaurantFlowPostgresConnectionSaturation | connections/max > 0.8 | 5m | high |
| RestaurantFlowPostgresDeadlocks | deadlocks increasing | 5m | high |
| RestaurantFlowRedisDown | `redis_up == 0` | 2m | critical |
| RestaurantFlowRedisMemoryNearLimit | used/max > 0.9 | 5m | high |
| RestaurantFlowRedisHighEvictions | evictions > 10/s | 5m | warning |
| RestaurantFlowHostDiskNearlyFull | free space < 10% | 10m | high |
| RestaurantFlowHostCpuSaturation | CPU > 85% | 10m | warning |
| RestaurantFlowContainerRestarting | repeated restarts | 5m | warning |
| RestaurantFlowCertNearingExpiry | cert < 14 days | 1h | high |

All thresholds are tunable defaults; edit the rule file per deployment.

## Lifecycle (reused from Phase 15)

```
DETECTED → OPEN → ACKNOWLEDGED → RESOLVED
```

- **Deduplication:** `CentralAlert.fingerprint` (alert_type + source + scope).
  A re-firing alert increments `detection_count` and `last_detected_at` rather
  than creating a duplicate; severity escalates if the new detection is worse.
- **Cooldown / repeat:** Alertmanager `repeat_interval` (critical 1h,
  high 2h, default 4h) prevents indefinite repeats; `inhibit_rules` suppress
  warnings while a critical parent is firing.
- **Recovery:** Alertmanager `status=resolved` resolves the matching active
  alert (no duplicate).
- **Notification:** only HIGH/CRITICAL monitoring alerts are pushed via
  `NotificationService` (which applies its own cooldown); lower severities
  remain visible in Central Control dashboards.

## Forwarding contract (webhook)

- Endpoint: `POST /api/observability/alerts/am`
- Auth: `Authorization: Bearer <ALERTMANAGER_WEBHOOK_TOKEN>` (or
  `X-Alertmanager-Token`).
- Body: Alertmanager webhook payload (`{"alerts":[...]}`).
- Secret labels (values matching `password|token|secret|key|auth|cvv|pan`)
  are redacted before persistence.
- Without a configured token the webhook returns 403.
