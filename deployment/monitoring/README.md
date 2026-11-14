# RestaurantFlow — Monitoring Stack (Phase 24)

An **optional** overlay that adds a Prometheus + Grafana + Alertmanager +
exporters monitoring stack. It is merged on top of the production stack only
when you want monitoring; it is not required to run RestaurantFlow.

## Components

| Service | Image | Purpose | Port (internal) |
|---|---|---|---|
| prometheus | prom/prometheus:v2.54.1 | Scrape + store metrics, evaluate alert rules | 9090 |
| alertmanager | prom/alertmanager:v0.27.1 | Route metric alerts → Central Control webhook | 9093 |
| grafana | grafana/grafana:11.2.2 | Dashboards | 127.0.0.1:3000 (host loopback only) |
| node-exporter | prom/node-exporter:v1.8.2 | Host CPU/mem/disk/net | 9100 |
| cadvisor | cadvisor:v0.49.1 | Per-container metrics | 8080 |
| postgres-exporter | postgres-exporter:v0.15.0 | PostgreSQL metrics | 9187 |
| redis-exporter | redis_exporter:v1.66.0 | Redis metrics | 9121 |
| blackbox-exporter | blackbox-exporter:v0.25.0 | Endpoint/TLS probing | 9115 |

**Nothing except Grafana is published to the host**, and Grafana is bound to
`127.0.0.1:3000` with anonymous access disabled and admin credentials required
from the environment. Front it with Nginx + auth for remote access.

## Resource envelope

Total memory cap of the stack is roughly **1.3 GB** with the limits in
`docker-compose.monitoring.yml`. Tune the `deploy.resources.limits` down for
very small servers, or drop `cadvisor`/`blackbox-exporter` first.

## Usage

```bash
# 1. Provision tokens as secret files (never commit them):
echo -n "$PROMETHEUS_SCRAPE_TOKEN"  > prometheus/secrets/scrape_token
echo -n "$ALERTMANAGER_WEBHOOK_TOKEN" > alertmanager/secrets/webhook_token
chmod 600 prometheus/secrets/scrape_token alertmanager/secrets/webhook_token

# 2. Validate the merged configuration:
docker compose -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f deployment/monitoring/docker-compose.monitoring.yml config

# 3. Start everything (app + monitoring):
docker compose -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f deployment/monitoring/docker-compose.monitoring.yml up -d
```

## Security notes

- Prometheus/Alertmanager and all exporters are internal-only (no host ports).
- The Docker socket is mounted **read-only** into cAdvisor only; no other
  monitoring container gets it. cAdvisor is given no special privileges beyond
  the read-only socket + filesystem mounts.
- `PROMETHEUS_SCRAPE_TOKEN` gates `/metrics` (sent as `Authorization: Bearer`).
- `ALERTMANAGER_WEBHOOK_TOKEN` gates the webhook into Central Control.
- Grafana admin password is required (`GRAFANA_ADMIN_PASSWORD`); sign-up and
  anonymous access are disabled.

## What is verified vs configured

- **Verified by tests:** the `/metrics` exposition format, token gating,
  Alertmanager webhook → CentralAlert dedup/resolve, and Central Control
  notification integration (`backend/manage.py test observability`).
- **Configured, not runtime-verified here:** live Prometheus scraping, the
  exporters, Grafana dashboard rendering, and Alertmanager routing require a
  running deployment host. Validate with the steps in `docs/monitoring_operations.md`.
