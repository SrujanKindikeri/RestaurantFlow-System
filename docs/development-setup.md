# RestaurantFlow — Development Setup

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | Use pyenv for version management |
| Node.js | 20 LTS+ | Use nvm for version management |
| Docker Desktop | Latest | Required for PostgreSQL and Redis |
| Git | Latest | |

---

## 1. Clone / Open the Repository

```bash
cd RestaurantFlow-System
```

---

## 2. Start Infrastructure (PostgreSQL + Redis)

Docker Compose manages the database and cache.

```bash
docker compose up -d
```

Verify services are healthy:

```bash
docker compose ps
```

Both `restaurantflow_postgres` and `restaurantflow_redis` should show `healthy`.

To stop services:

```bash
docker compose down
```

To stop and remove volumes (full reset):

```bash
docker compose down -v
```

---

## 3. Backend Setup

### 3.1 Create a Virtual Environment

```bash
cd backend
python -m venv venv
```

Activate it:

- **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
- **macOS / Linux:** `source venv/bin/activate`

### 3.2 Install Dependencies

```bash
pip install -r requirements.txt
```

### 3.3 Configure Environment Variables

```bash
# Copy the example file
cp .env.example .env
```

Open `backend/.env` and set:

```env
SECRET_KEY=generate-a-random-key-here
DEBUG=True
DB_NAME=restaurantflow
DB_USER=restaurantflow
DB_PASSWORD=change_me
DB_HOST=localhost
DB_PORT=5432
REDIS_URL=redis://localhost:6379/0
```

> The PostgreSQL credentials must match what you set in `docker-compose.yml`.
> The defaults work out of the box with the included Docker Compose config.

### 3.4 Run Migrations

```bash
python manage.py migrate
```

### 3.5 Create a Superuser (optional)

```bash
python manage.py createsuperuser
```

### 3.6 Start the Backend

```bash
python manage.py runserver
```

The API is now available at `http://localhost:8000/api/`.

Test the health endpoint:

```bash
curl http://localhost:8000/api/health/
# → {"status": "ok", "service": "RestaurantFlow API"}
```

Django admin is available at `http://localhost:8000/admin/`.

---

## 4. Frontend Setup

### 4.1 Install Dependencies

```bash
cd frontend
npm install
```

### 4.2 Configure Environment Variables

```bash
cp .env.example .env
```

The default `.env` works as-is for local development:

```env
VITE_API_URL=http://localhost:8000/api
VITE_APP_NAME=RestaurantFlow
```

### 4.3 Start the Frontend

```bash
npm run dev
```

The app is now available at `http://localhost:5173`.

---

## 5. Verify Everything Works

With both backend and frontend running, open `http://localhost:5173`.

You should see:

```
RestaurantFlow
Restaurant Management & POS Platform

System Status
─────────────────────
Backend   ● Connected
API       ● Healthy
```

---

## 6. Running Tests

### Backend Tests

```bash
cd backend
python manage.py test
```

Run a specific app:

```bash
python manage.py test core
python manage.py test accounts
```

### Frontend Type Check

```bash
cd frontend
npm run type-check
```

---

## 7. Project Structure Overview

```
RestaurantFlow-System/
├── backend/          ← Django REST API
│   ├── config/       ← Django settings, urls, wsgi, asgi
│   ├── accounts/     ← Custom User model + JWT auth
│   ├── core/         ← Health endpoint, shared utilities
│   └── requirements.txt
│
├── frontend/         ← React + TypeScript + Vite
│   └── src/
│       ├── components/
│       ├── layouts/
│       ├── pages/
│       ├── services/
│       ├── hooks/
│       ├── contexts/
│       ├── types/
│       └── utils/
│
├── docs/             ← Project documentation
├── tests/            ← Cross-system test structure
├── deployment/       ← Deployment configs (future phases)
└── docker-compose.yml
```

---

## 8. Common Issues

### Port already in use

```bash
# Check what's using port 5432
netstat -ano | findstr :5432

# Or change the port in docker-compose.yml:
ports:
  - "5433:5432"
# And update DB_PORT=5433 in backend/.env
```

### Django can't connect to PostgreSQL

1. Make sure Docker is running: `docker compose ps`
2. Wait for the health check to pass (can take ~10s on first boot)
3. Confirm `DB_HOST=localhost` in `backend/.env`

### Module not found (backend)

Make sure your virtual environment is activated before running any `python` commands.

### CORS errors in browser

In development, `CORS_ALLOW_ALL_ORIGINS = True` is set when `DEBUG=True`.
If you see CORS errors, confirm `DEBUG=True` in `backend/.env`.
