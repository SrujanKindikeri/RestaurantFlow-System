# RestaurantFlow — Development Setup

## Prerequisites

- Python 3.11+
- Node.js 20 LTS+
- Docker Desktop (for PostgreSQL + Redis)
- Git

---

## 1 — Clone and Setup

```bash
git clone <repo-url>
cd RestaurantFlow-System
```

---

## 2 — Start Infrastructure

```bash
docker compose up -d
```

Verify:
```bash
docker compose ps
# postgres: healthy
# redis:    healthy
```

---

## 3 — Backend Setup

```bash
cd backend
cp .env.example .env
```

Edit `.env` with real values (at minimum, confirm `DB_PASSWORD` matches `docker-compose.yml`).

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Verify:
```bash
curl http://localhost:8000/api/health/
# {"status": "ok", "service": "RestaurantFlow API"}
```

---

## 4 — Seed Demo Data (optional)

```bash
python manage.py seed_demo_data
```

Creates:
- Organization: RestaurantFlow Foods
- Restaurants: Spice Garden, Urban Bites, Royal Kitchen
- Branches: 7 locations across 3 restaurants

Reset and reseed:
```bash
python manage.py seed_demo_data --reset
```

---

## 5 — Frontend Setup

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Visit: http://localhost:5173

---

## 6 — Run Tests

```bash
cd backend
python manage.py test organizations
python manage.py test accounts
python manage.py test core
```

---

## 7 — TypeScript Check

```bash
cd frontend
npm run type-check
```

---

## 8 — Production Build

```bash
cd frontend
npm run build
# Output in frontend/dist/
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable                    | Default              | Description                          |
|-----------------------------|----------------------|--------------------------------------|
| `SECRET_KEY`                | (required)           | Django secret key                    |
| `DEBUG`                     | `True`               | Debug mode                           |
| `ALLOWED_HOSTS`             | `localhost,127.0.0.1`| Comma-separated allowed hosts        |
| `DB_NAME`                   | `restaurantflow`     | PostgreSQL database name             |
| `DB_USER`                   | `restaurantflow`     | PostgreSQL username                  |
| `DB_PASSWORD`               | `change_me`          | PostgreSQL password                  |
| `DB_HOST`                   | `localhost`          | PostgreSQL host                      |
| `DB_PORT`                   | `5432`               | PostgreSQL port                      |
| `REDIS_URL`                 | `redis://localhost:6379/0` | Redis connection URL           |
| `CORS_ALLOWED_ORIGINS`      | `http://localhost:5173` | Allowed frontend origins (prod)   |
| `JWT_ACCESS_TOKEN_LIFETIME` | `60`                 | Access token lifetime (minutes)      |
| `JWT_REFRESH_TOKEN_LIFETIME`| `7`                  | Refresh token lifetime (days)        |
| `LOG_LEVEL`                 | `DEBUG`              | Logging level                        |

### Frontend (`frontend/.env`)

| Variable        | Default                        | Description          |
|-----------------|--------------------------------|----------------------|
| `VITE_API_URL`  | `http://localhost:8000/api`    | Backend API base URL |
| `VITE_APP_NAME` | `RestaurantFlow`               | App display name     |

---

## Django Admin

1. Create superuser: `python manage.py createsuperuser`
2. Visit: http://localhost:8000/admin/
3. Available: Organization, Restaurant, Branch, RestaurantSettings, BranchSettings, User

---

## Common Issues

**Port already in use (5432):**
```bash
docker compose down && docker compose up -d
```

**Migration errors after pulling new code:**
```bash
python manage.py migrate --run-syncdb
```

**Frontend can't reach backend:**
Check `VITE_API_URL` in `frontend/.env` matches the backend port.

**CORS errors:**
In development, `DEBUG=True` allows all origins. In production, set `CORS_ALLOWED_ORIGINS`.
