# RestaurantFlow

**Restaurant Management & POS Platform**

A production-oriented, multi-restaurant management and point-of-sale platform
built with Django and React. Designed to scale from a single restaurant to a
company with many branches and counters.

---

## Current Status — Phase 1: Foundation ✅

The technical foundation is in place. Business features will be built on top
in subsequent phases.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| State / Data | TanStack React Query, Axios |
| Routing | React Router v6 |
| Backend | Django 4.2, Django REST Framework |
| Auth | Simple JWT |
| Database | PostgreSQL 15 |
| Cache / WS | Redis 7 |
| Infrastructure | Docker Compose |

---

## Quick Start

### 1. Start infrastructure

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv

# Windows
.\venv\Scripts\Activate.ps1
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env   # edit as needed
python manage.py migrate
python manage.py runserver
```

Backend: `http://localhost:8000`
Health check: `http://localhost:8000/api/health/`

### 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend: `http://localhost:5173`

---

## Project Structure

```
RestaurantFlow-System/
├── backend/
│   ├── config/          ← Django project config
│   ├── accounts/        ← Custom User model, JWT auth
│   ├── core/            ← Health endpoint, shared utilities
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── components/
│       ├── layouts/
│       ├── pages/
│       ├── services/    ← All API calls go here
│       ├── hooks/
│       ├── contexts/
│       ├── types/
│       └── utils/
│
├── docs/
│   ├── architecture.md
│   ├── development-setup.md
│   ├── database-design.md
│   ├── api-documentation.md
│   └── roadmap.md
│
├── tests/               ← Cross-system test structure
├── deployment/          ← Deployment configs (Phase 15)
├── docker-compose.yml
├── .gitignore
└── README.md
```

---

## API Endpoints (Phase 1)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | `/api/health/` | None | Backend health check |
| POST | `/api/auth/register/` | None | Register user |
| POST | `/api/auth/login/` | None | Obtain JWT tokens |
| POST | `/api/auth/token/refresh/` | None | Refresh access token |
| GET | `/api/auth/me/` | Bearer | Current user profile |

---

## Running Tests

```bash
cd backend
python manage.py test
```

---

## Documentation

- [Architecture](docs/architecture.md)
- [Development Setup](docs/development-setup.md)
- [Database Design](docs/database-design.md)
- [API Documentation](docs/api-documentation.md)
- [Roadmap](docs/roadmap.md)

---

## Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation | ✅ Complete |
| 2 | Companies, Restaurants & Branches | Planned |
| 3 | Users, Roles & Permissions | Planned |
| 4 | Counters & Cash Sessions | Planned |
| 5 | Menu | Planned |
| 6 | Tables, Orders & POS | Planned |
| 7 | Kitchen Display System | Planned |
| 8 | Billing & Payments | Planned |
| 9 | Approvals, Audit & Issues | Planned |
| 10 | Inventory | Planned |
| 11 | Accounts | Planned |
| 12 | Restaurant Analytics | Planned |
| 13 | Central Control Center | Planned |
| 14 | Security & Monitoring | Planned |
| 15 | Production Deployment | Planned |

---

## License

MIT — see [LICENSE](LICENSE).
