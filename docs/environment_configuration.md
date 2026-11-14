# Environment Configuration

All environment-specific values are injected at runtime via environment variables. No secrets are stored in the repository.

The canonical template is `deployment/environment/.env.prod.example`. Copy it to `deployment/environment/.env.prod` and fill in real values before deploying.

---

## Backend variables

### Django core

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | — | 50+ character random string. Generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DEBUG` | No | `False` | Set to `True` only in development. Never `True` in production. |
| `ALLOWED_HOSTS` | Yes | `localhost,127.0.0.1` | Comma-separated list of valid hostnames. Example: `app.example.com,www.app.example.com` |
| `CORS_ALLOWED_ORIGINS` | Yes | `http://localhost:5173` | Comma-separated CORS origins. Example: `https://app.example.com` |
| `CSRF_TRUSTED_ORIGINS` | Yes | — | Comma-separated origins for CSRF. Must match `ALLOWED_HOSTS` scheme. Example: `https://app.example.com` |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_NAME` | No | `restaurantflow` | PostgreSQL database name |
| `DB_USER` | No | `restaurantflow` | PostgreSQL user |
| `DB_PASSWORD` | Yes | — | PostgreSQL password. Must not be `change_me`. |
| `DB_HOST` | No | `localhost` | In Docker Compose: `postgres` |
| `DB_PORT` | No | `5432` | PostgreSQL port |

### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | `redis://localhost:6379/0` | Full Redis URL. In production include password: `redis://:PASSWORD@redis:6379/0` |
| `REDIS_PASSWORD` | Yes | — | Redis AUTH password. Set via `--requirepass` in `docker-compose.yml`. |

Redis serves three workloads on the same instance using database indexes:
- DB 0: Django cache (`CACHES` default backend)
- DB 0: Celery broker (`CELERY_BROKER_URL`)
- DB 0: Django Channels layer

If traffic warrants isolation, separate instances can be introduced by updating `CHANNEL_LAYERS` and `CELERY_BROKER_URL` to point to different Redis URLs.

### JWT

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_ACCESS_TOKEN_LIFETIME` | `60` | Access token lifetime in minutes |
| `JWT_REFRESH_TOKEN_LIFETIME` | `7` | Refresh token lifetime in days |

### Static and media

| Variable | Default | Description |
|----------|---------|-------------|
| `STATIC_URL` | `/static/` | URL prefix for static files |
| `MEDIA_URL` | `/media/` | URL prefix for user-uploaded files |

### Email

| Variable | Default | Description |
|----------|---------|-------------|
| `EMAIL_BACKEND` | `console` (dev) / `smtp` (prod) | Django email backend class |
| `EMAIL_HOST` | `localhost` | SMTP host |
| `EMAIL_PORT` | `587` | SMTP port |
| `EMAIL_USE_TLS` | `True` | Enable STARTTLS |
| `EMAIL_HOST_USER` | — | SMTP username |
| `EMAIL_HOST_PASSWORD` | — | SMTP password |
| `DEFAULT_FROM_EMAIL` | `noreply@restaurantflow.app` | Sender address |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `DEBUG` (dev) / `INFO` (prod) | Minimum log level |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `ADMIN_URL_PREFIX` | `admin` | URL path for Django admin. Change to a non-obvious string in production. |
| `SECURITY_MAX_LOGIN_FAILURES` | `5` | Consecutive failures before lockout |
| `SECURITY_LOGIN_LOCKOUT_MINUTES` | `15` | Lockout duration |
| `AUDIT_RETENTION_DAYS` | `365` | Days to retain audit log entries (0 = never delete) |

### Rate limiting

All throttle rates use Django REST Framework's `count/period` format.

| Variable | Default |
|----------|---------|
| `THROTTLE_AUTH_LOGIN` | `30/hour` |
| `THROTTLE_AUTH_REGISTER` | `5/hour` |
| `THROTTLE_AUTH_PASSWORD` | `10/hour` |
| `THROTTLE_SENSITIVE_OP` | `60/hour` |
| `THROTTLE_EXPORT` | `20/hour` |
| `THROTTLE_SEARCH` | `120/hour` |

### Upload limits

| Variable | Default | Description |
|----------|---------|-------------|
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | `10485760` | 10 MB in bytes |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | `10485760` | 10 MB in bytes |

---

## Frontend build args

These are injected at Docker build time via `ARG` instructions in `frontend/Dockerfile`. They are baked into the JavaScript bundle and are **not** runtime environment variables. Do not put secrets here.

| Arg | Required | Description |
|-----|----------|-------------|
| `VITE_API_URL` | Yes | Backend API base URL. Example: `https://app.example.com/api` |
| `VITE_APP_NAME` | No | Application name shown in the UI. Default: `RestaurantFlow` |
| `VITE_WS_URL` | Yes | WebSocket base URL. Example: `wss://app.example.com` |

---

## Docker Compose variables

These control image registry paths in `docker-compose.prod.yml`.

| Variable | Default | Description |
|----------|---------|-------------|
| `GHCR_OWNER` | `restaurantflow` | GitHub container registry owner/org |
| `IMAGE_TAG` | `latest` | Image tag to pull/run |

---

## Secret management

**Development:** Copy `backend/.env.example` → `backend/.env`. Fill in values locally. Never commit `.env`.

**Production:** Store secrets outside the repository:
- Use GitHub Actions secrets for CI/CD credentials.
- Use a secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.) for server-side secrets.
- Or deploy `deployment/environment/.env.prod` to the server via a secure channel (SCP, Ansible vault, etc.) and exclude it from Git.

**Rotation:** If a secret is ever committed to Git history, rotate it immediately — changing the value in the working tree is not sufficient. Git history retains the old value.

---

## Validation

Before every deployment, `deployment/scripts/validate-environment.sh` (Linux) or `validate-environment.ps1` (Windows) verifies that all required variables are set and that `SECRET_KEY` is not an insecure default.
