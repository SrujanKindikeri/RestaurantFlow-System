# Monitoring Operations — Phase 24

## Provisioning (one-time)

```bash
# Tokens as secret files (gitignored). Do NOT commit them.
echo -n "$PROMETHEUS_SCRAPE_TOKEN"     > deployment/monitoring/prometheus/secrets/scrape_token
echo -n "$ALERTMANAGER_WEBHOOK_TOKEN" > deployment/monitoring/alertmanager/secrets/webhook_token
chmod 600 deployment/monitoring/prometheus/secrets/scrape_token \
         deployment/monitoring/alertmanager/secrets/webhook_token

# Grafana admin credentials + app tokens in the deployment env file:
#   PROMETHEUS_SCRAPE_TOKEN, ALERTMANAGER_WEBHOOK_TOKEN,
#   OBSERVABILITY_MONITORING_ORG_ID, GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD
```

`OBSERVABILITY_MONITORING_ORG_ID` should be set in multi-tenant deployments so
metric alerts attach to the correct organization. Without it, alerts attach
to the first organization (single-tenant/dev).

## Start / stop / validate

```bash
# Validate config (no containers started)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f deployment/monitoring/docker-compose.monitoring.yml config

# Start app + monitoring
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  -f deployment/monitoring/docker-compose.monitoring.yml up -d

# Status / health
docker compose ps
curl -s localhost/8000/health/ready/
curl -s localhost:8000/health/dependencies/
```

## Verification checklist (on a deployment host)

- [ ] Prometheus target `restaurantflow-api` is `UP` (Prometheus → Status → Targets).
- [ ] `/metrics` returns 200 with a token (403 without).
- [ ] Grafana loads the 6 dashboards from the RestaurantFlow folder.
- [ ] Alertmanager routes a test alert to Central Control (a `CentralAlert`
      with `source_type=MONITORING` appears).
- [ ] A HIGH/CRITICAL alert produces a `Notification` via the existing center.
- [ ] `/health/dependencies/` reports `database`/`redis`/`channels` ok.
- [ ] Host metrics (node-exporter) and container metrics (cAdvisor) appear.
- [ ] postgres-exporter and redis-exporter targets are UP.

## Retention & capacity

- Prometheus retention: `PROMETHEUS_RETENTION` (default 15d). Lower for small
  disks.
- Grafana/Alertmanager data persists in named volumes.
- Application log files rotate at 10 MB × 5 backups. Configure host logrotate
  or Loki retention to bound long-term storage.

## Security

- Only Grafana is host-published, on `127.0.0.1:3000`, with login required.
- `PROMETHEUS_SCRAPE_TOKEN` gates `/metrics`; `ALERTMANAGER_WEBHOOK_TOKEN`
  gates the webhook. Rotate by updating the secret files + app env and
  restarting the affected containers.
- cAdvisor is the only container with the Docker socket, mounted read-only.
- Do not grant monitoring containers additional privileges; do not expose
  exporter ports to the host.

## Failure behavior

- If Prometheus/Alertmanager are down, **business operation is unaffected** —
  metric-based alerts simply stop arriving; the Phase 15 `AlertDetectionService`
  continues to surface business conditions independently.
- If OTel/Sentry are unconfigured, the app runs with local structured logging
  as the error record (documented limitation).
- `/metrics` and the webhook never degrade the request path — instrumentation
  is wrapped so failures are logged and swallowed.
