# Staging Deployment

The staging environment is a production-equivalent deployment used to validate every release before it reaches production. It runs the same Docker images, the same Compose configuration, and the same environment variable structure as production, with different credential values and domain.

---

## Purpose

- Catch deployment-specific failures (image build errors, migration issues, misconfigured env vars) before they affect real users.
- Verify cross-service integration (WebSocket, Celery, database, Redis) in a Docker environment.
- Run acceptance tests against a live application without touching production data.

---

## Staging vs production

| Aspect | Staging | Production |
|--------|---------|------------|
| Docker images | Same tags | Same tags |
| Compose config | Same files | Same files |
| Domain | `staging.example.com` or IP | `app.example.com` |
| TLS | Self-signed or Let's Encrypt staging cert | Let's Encrypt production cert |
| Data | Synthetic / anonymized | Real customer data |
| Auto-deploy | Yes — every push to `main` | Manual approval required |
| Resource limits | May be relaxed | Full spec |

---

## Setup

### 1. Provision a server

A single VM or EC2 instance with Docker installed is sufficient. Minimum recommended: 2 vCPU, 4 GB RAM.

Install Docker and the Compose plugin:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
```

### 2. Clone the repository

```bash
git clone https://github.com/your-org/restaurantflow.git ~/restaurantflow
cd ~/restaurantflow
```

### 3. Create the staging env file

```bash
cp deployment/environment/.env.prod.example deployment/environment/.env.prod
# Edit the file with staging-specific values:
#   ALLOWED_HOSTS=staging.example.com
#   CORS_ALLOWED_ORIGINS=https://staging.example.com
#   CSRF_TRUSTED_ORIGINS=https://staging.example.com
#   DB_PASSWORD=<staging-db-password>
#   REDIS_PASSWORD=<staging-redis-password>
#   SECRET_KEY=<staging-secret-key>
nano deployment/environment/.env.prod
```

Validate the env file:

```bash
bash deployment/scripts/validate-environment.sh
```

### 4. Obtain a TLS certificate (or use self-signed)

For a real staging domain with Let's Encrypt:

```bash
sudo certbot certonly --standalone -d staging.example.com
sudo cp /etc/letsencrypt/live/staging.example.com/fullchain.pem deployment/nginx/ssl/
sudo cp /etc/letsencrypt/live/staging.example.com/privkey.pem deployment/nginx/ssl/
sudo chmod 600 deployment/nginx/ssl/privkey.pem
```

For a self-signed certificate (IP-only or quick testing):

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout deployment/nginx/ssl/privkey.pem \
  -out    deployment/nginx/ssl/fullchain.pem \
  -subj "/CN=staging.example.com"
```

### 5. First deploy

```bash
export IMAGE_TAG=latest
bash deployment/scripts/deploy.sh latest
```

This runs: environment validation → database backup → image pull → migrations → service restart → health check.

---

## Automated staging deploys via CI/CD

The CD workflow (`.github/workflows/deploy.yml`) deploys to staging automatically on every push to `main`. No manual step is needed.

Add these secrets to the `staging` GitHub environment:

| Secret | Value |
|--------|-------|
| `SSH_HOST` | Staging server IP/hostname |
| `SSH_USER` | SSH username |
| `SSH_PRIVATE_KEY` | Private key for SSH |
| `GHCR_TOKEN` | GHCR read token (for pulling images) |

---

## Staging verification checklist

Run through these scenarios after each staging deployment before approving a production release.

### Authentication
- [ ] Register a new user account
- [ ] Log in and receive a JWT access token
- [ ] Token refresh works
- [ ] Log out invalidates the refresh token
- [ ] Failed login lockout triggers after configured threshold

### Multi-tenancy
- [ ] Create two companies; each can only see its own data
- [ ] Create multiple restaurants under a company
- [ ] Staff from restaurant A cannot access restaurant B data

### POS operations
- [ ] Open a POS session / cash session
- [ ] Create and complete an order
- [ ] Apply a discount
- [ ] Process a payment
- [ ] Issue a refund
- [ ] Close the session

### Order and kitchen workflows
- [ ] Order placed → appears on KDS
- [ ] KDS item marked ready → updates order status
- [ ] Kitchen display WebSocket connection stays alive (> 60 seconds)

### Billing
- [ ] Subscription plan assigned to a company
- [ ] Invoice generated
- [ ] Payment recorded against invoice

### Inventory
- [ ] Stock adjustment recorded
- [ ] Low-stock alert fires (Celery notification task)

### Accounting
- [ ] Journal entry created
- [ ] Financial reports generate without error

### Reporting
- [ ] Sales report returns data for a date range
- [ ] Export triggers a Celery task (check worker logs)

### Central Control
- [ ] WebSocket connection to central control dashboard established
- [ ] Real-time alert appears on dashboard

### Notifications
- [ ] In-app notification delivered via WebSocket
- [ ] Celery beat retry task visible in `django_celery_results`

### Enterprise configuration
- [ ] Branch-level configuration override applied
- [ ] Cross-branch report aggregates correctly

### Background tasks
- [ ] Celery worker is running (`docker compose ps celery_worker`)
- [ ] Celery beat is running (`docker compose ps celery_beat`)
- [ ] Check `django_celery_results` for recent task executions
- [ ] No duplicate periodic task executions (verify Beat is a single instance)

### WebSocket stability
- [ ] Connect to `/ws/kitchen/<id>/`, send a message, receive a broadcast
- [ ] Connect to `/ws/notifications/`, receive a push notification

### Infrastructure
- [ ] `GET /health/` → `{"status": "ok"}`
- [ ] `GET /health/ready/` → `{"status": "ready", "database": "ok", "redis": "ok"}`
- [ ] `GET /health/live/` → `{"status": "ok"}`
- [ ] HTTPS redirect works (HTTP → HTTPS)
- [ ] TLS certificate is valid
- [ ] Django admin accessible at the configured `ADMIN_URL_PREFIX`
- [ ] No database or Redis ports accessible from outside the Docker network

---

## Data policy

- Use synthetic data only. Never copy production customer records, payment data, or personal information into staging.
- If anonymized production data is needed for a specific test, run it through an approved anonymization process and document the procedure.
- Staging databases are dropped and rebuilt freely; they contain no real data.

---

## Teardown

To stop staging without destroying data:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

To destroy everything including volumes (data will be lost):

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```
