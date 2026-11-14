# Docker Architecture

## Service Overview

RestaurantFlow's production stack runs as six Docker services orchestrated by Docker Compose. The base `docker-compose.yml` provides development-only infrastructure (PostgreSQL and Redis). The production overlay `docker-compose.prod.yml` adds the application services and removes host-exposed database ports.

### Full production command

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Service Diagram

```
                        INTERNET
                           |
                     :80 / :443
                           |
                   ┌───────────────┐
                   │     nginx     │  Nginx:alpine
                   │  (frontend +  │  Serves React SPA
                   │  TLS proxy)   │  Proxies /api/, /ws/, /admin/
                   └───────┬───────┘
                           |
              ┌────────────┴────────────┐
              |                         |
         /api/, /ws/              / (static SPA)
         /admin/, /health/
              |
     ┌────────────────┐
     │    backend     │  python:3.11-slim
     │ Uvicorn ASGI   │  :8000 (internal only)
     │ 2 workers      │  HTTP + WebSocket
     └────┬──────┬────┘
          │      │
   ┌──────┘      └──────┐
   │                     │
┌──────┐          ┌──────────────┐
│redis │          │   postgres   │  postgres:15-alpine
│  7   │          │              │  persistent volume
└──┬───┘          └──────────────┘
   │
   ├── Channel Layer (WebSocket groups)
   ├── Celery Broker
   └── Django Cache
   │
┌──┴──────────────────┐
│   celery_worker     │  Same backend image
│   celery_beat       │  Different CMD
└─────────────────────┘
  (1 beat instance only)
```

---

## Images

### `restaurantflow-backend`

Multi-stage build defined in `backend/Dockerfile`.

| Stage | Base | Purpose |
|-------|------|---------|
| `builder` | `python:3.11-slim` | Installs gcc, libpq-dev; compiles Python packages into `/install` |
| `runtime` | `python:3.11-slim` | Copies compiled packages; runs collectstatic; creates non-root `appuser` |

Key properties:
- Non-root user `appuser` (UID 1000)
- Whitenoise serves static files from `/app/staticfiles`
- `PYTHONUNBUFFERED=1` — logs stream directly without buffering
- `DEBUG=False` baked in; real `SECRET_KEY` injected at runtime only
- Health check: `curl -f http://localhost:8000/health/`
- Shared by `backend`, `celery_worker`, and `celery_beat` services (different CMD per service)

### `restaurantflow-frontend`

Multi-stage build defined in `frontend/Dockerfile`.

| Stage | Base | Purpose |
|-------|------|---------|
| `builder` | `node:20-alpine` | `npm ci` + `npm run build` (TypeScript compile + Vite bundle) |
| `runtime` | `nginx:alpine` | Copies `/app/dist`; serves static bundle |

Key properties:
- Build args `VITE_API_URL`, `VITE_WS_URL`, `VITE_APP_NAME` are baked in at build time
- Nginx serves index.html for all SPA routes (React Router fallback)
- No backend secrets in the frontend image
- The outer Nginx container (same image) also handles TLS termination and reverse proxying

---

## Volumes

| Volume | Used by | Contents |
|--------|---------|----------|
| `postgres_data` | postgres | PostgreSQL data directory — persistent, never ephemeral |
| `redis_data` | redis | Redis AOF persistence file |
| `static_files` | backend, nginx | Django collectstatic output |
| `media_files` | backend, nginx | User-uploaded files |

---

## Networks

All services run on Docker Compose's default bridge network. No service exposes a port to the host except `nginx` (:80, :443). PostgreSQL and Redis ports are removed in the production overlay (`ports: []`).

---

## Service Commands

| Service | Command |
|---------|---------|
| `backend` | `uvicorn config.asgi:application --host 0.0.0.0 --port 8000 --workers 2 --worker-class uvicorn.workers.UvicornWorker` |
| `celery_worker` | `celery -A config worker --loglevel=info --queues=default,notifications,maintenance` |
| `celery_beat` | `celery -A config beat --scheduler django_celery_beat.schedulers:DatabaseScheduler --loglevel=info` |
| `nginx` | `nginx -g 'daemon off;'` |

---

## Celery Beat: single-instance requirement

**Never scale `celery_beat` beyond 1 replica.** Multiple Beat instances running simultaneously will produce duplicate periodic task executions. The `docker-compose.prod.yml` does not set a `deploy.replicas` count for `celery_beat`; leave it at the default of 1.

---

## WebSocket flow

```
Browser → wss://domain.com/ws/kitchen/123/
  → Nginx (TLS termination, Upgrade headers)
  → backend:8000 (Uvicorn ASGI)
  → Django Channels
  → channels_redis channel layer
  → Redis pub/sub
```

Uvicorn handles both HTTP and WebSocket connections over the same port via ASGI protocol routing. No separate Daphne process is needed.

---

## Registry

Images are pushed to GitHub Container Registry (GHCR) during CD:

```
ghcr.io/<owner>/restaurantflow-backend:<git-sha>
ghcr.io/<owner>/restaurantflow-backend:latest
ghcr.io/<owner>/restaurantflow-frontend:<git-sha>
ghcr.io/<owner>/restaurantflow-frontend:latest
```

The `latest` tag is updated only on pushes to `main`. The SHA tag is used for rollbacks.
