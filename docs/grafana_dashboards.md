# Grafana Dashboards — Phase 24

Dashboards are provisioned from `deployment/monitoring/grafana/dashboards/`
and loaded by the provider in
`grafana/provisioning/dashboards/dashboards.yml` into the **RestaurantFlow**
folder. The datasource is auto-provisioned from
`grafana/provisioning/datasources/datasources.yml` (Prometheus default).

## Access

- Grafana is bound to `127.0.0.1:3000` only; anonymous access disabled;
  admin credentials required from `GRAFANA_ADMIN_USER` /
  `GRAFANA_ADMIN_PASSWORD`.
- For remote access, front Grafana with Nginx + auth (do **not** expose it
  publicly without access controls).

## Dashboards

| Dashboard (UID) | Panels |
|---|---|
| Application Overview (`rf-app-overview`) | API availability, request rate by route, p95/p99 latency, error rate, status-class breakdown |
| PostgreSQL (`rf-postgres`) | up, active connections, connection utilisation, deadlocks, cache hit ratio, DB size |
| Redis (`rf-redis`) | up, memory used vs max, connected clients, commands/s, evictions/s, hit/miss |
| Celery (`rf-celery`) | workers up, queue depth, tasks started/s, task failures/s, task duration p95 |
| Infrastructure (`rf-infra`) | CPU per core, memory, disk usage gauge, network, container memory |
| Business Operations (`rf-business`) | business events by type, payment/bill/accounting failure counts, critical business events |

Business dashboards read `restaurantflow_business_events_total`, populated by
`observability.record_business_event()` from business-module failure paths.
For business **analytics** (revenue, sales trends) use the existing Reporting
services — dashboards are for operational event counts, not recomputed KPIs.

## Adding/modifying dashboards

- Drop a JSON file into `grafana/dashboards/`; the provider reloads every 30s.
- `allowUiUpdates: false` keeps the file as the source of truth.
- Use datasource name `Prometheus` in panel JSON (resolved by the
  auto-provisioned datasource).
