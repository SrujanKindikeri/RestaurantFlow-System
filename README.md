# RestaurantFlow

A production-oriented restaurant management and POS platform built with Django, React, and PostgreSQL.

---

## Current Phase

**Phase 5 — Menu, Categories, Branch Pricing, Availability & Tax**

The full menu catalog system is operational:

```
Organization
    └── Restaurant
          ├── Branch
          │    └── Counters / Sessions
          └── Menu
               ├── TaxRate (restaurant-scoped tax configuration)
               ├── Category (Veg, Non-Veg, Snacks, Beverages, Desserts)
               └── MenuItem
                     ├── MenuItemPrice  (branch-specific pricing + history)
                     └── MenuItemBranch (branch availability + time windows)
```

---

## Technology Stack

| Layer      | Technology                                      |
|------------|-------------------------------------------------|
| Backend    | Django 4.2 · DRF 3.15 · Simple JWT             |
| Database   | PostgreSQL 15                                   |
| Cache/WS   | Redis 7 · Django Channels                       |
| Frontend   | React 18 · TypeScript · Vite · Tailwind CSS     |
| State      | TanStack Query v5 · Axios                       |
| Auth       | JWT (Bearer token) — Phase 3 adds full RBAC     |

---

## Quick Start

### 1 — Infrastructure (Docker)

```bash
docker compose up -d
```

Starts PostgreSQL (port 5432) and Redis (port 6379).

### 2 — Backend

```bash
cd backend
cp .env.example .env          # fill in real values
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Optional — load demo data:

```bash
python manage.py seed_demo_data   # Phase 1-4 orgs, restaurants, branches
python manage.py seed_menu_data   # Phase 5 permissions + demo menu
```

### 3 — Frontend

```bash
cd frontend
cp .env.example .env          # set VITE_API_URL
npm install
npm run dev
```

Visit: http://localhost:5173

### 4 — Verify

```bash
curl http://localhost:8000/api/health/
# {"status": "ok", "service": "RestaurantFlow API"}
```

---

## Project Structure

```
RestaurantFlow-System/
├── backend/
│   ├── config/               Django project config
│   ├── accounts/             Custom User model (email-based)
│   ├── core/                 TimestampedModel, health endpoint, exception handler
│   ├── organizations/        Phase 2 — Organization / Restaurant / Branch
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   └── management/commands/seed_demo_data.py
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── types/            Shared TypeScript interfaces
│       ├── services/         Axios API service layer
│       ├── hooks/            React Query data hooks
│       ├── components/
│       │   ├── ui/           Shared UI primitives
│       │   ├── organization/
│       │   ├── restaurant/
│       │   └── branch/
│       ├── pages/
│       │   ├── organizations/
│       │   ├── restaurants/
│       │   └── branches/
│       └── layouts/
│
├── docs/
├── docker-compose.yml
└── README.md
```

---

## API Endpoints (Phase 2)

| Method   | Endpoint                                         | Description                    |
|----------|--------------------------------------------------|--------------------------------|
| GET      | `/api/health/`                                   | Health check                   |
| GET/POST | `/api/organizations/`                            | List / create organizations    |
| GET      | `/api/organizations/stats/`                      | Dashboard aggregate counts     |
| GET/PATCH| `/api/organizations/<id>/`                       | Detail / update organization   |
| GET/POST | `/api/organizations/<id>/restaurants/`           | List / create restaurants      |
| GET      | `/api/restaurants/`                              | All restaurants (admin)        |
| GET/PATCH| `/api/restaurants/<id>/`                         | Detail / update restaurant     |
| GET/POST | `/api/restaurants/<id>/branches/`                | List / create branches         |
| GET/PATCH| `/api/restaurants/<id>/settings/`                | Restaurant settings            |
| GET      | `/api/branches/`                                 | All branches (admin)           |
| GET/PATCH| `/api/branches/<id>/`                            | Detail / update branch         |
| GET/PATCH| `/api/branches/<id>/settings/`                   | Branch settings                |

All endpoints require `Authorization: Bearer <token>`.

---

## Django Admin

Available at `/admin/` after creating a superuser:

```bash
python manage.py createsuperuser
```

Registered models: `Organization`, `Restaurant`, `Branch`, `RestaurantSettings`, `BranchSettings`, `User`.

---

## Development Commands

```bash
# Run tests
python manage.py test organizations

# Seed demo data
python manage.py seed_demo_data

# Reset and re-seed
python manage.py seed_demo_data --reset

# Frontend type check
cd frontend && npm run type-check

# Frontend build
cd frontend && npm run build
```

---

## Documentation

| Document                         | Description                              |
|----------------------------------|------------------------------------------|
| `docs/architecture.md`           | System architecture and design decisions |
| `docs/database-design.md`        | Database schema and relationships        |
| `docs/api-documentation.md`      | Full API reference                       |
| `docs/phase-2.md`                | Phase 2 implementation details           |
| `docs/development-setup.md`      | Local development setup guide            |
| `docs/roadmap.md`                | Full 15-phase development roadmap        |
| `deployment/README.md`           | Production deployment (Phase 15)         |

---

## Development Phases

| Phase | Status | Description                          |
|-------|--------|--------------------------------------|
| 1     | ✅ Done | Foundation — Django + React + Docker |
| 2     | ✅ Done | Organizations, Restaurants, Branches |
| 3     | 🔜     | Users, Roles & Permissions           |
| 4     | 🔜     | Counters & Cash Sessions             |
| 5     | 🔜     | Menu                                 |
| 6     | 🔜     | Tables, Orders & POS                 |
| 7     | 🔜     | Kitchen Display System               |
| 8     | 🔜     | Billing & Payments                   |
| 9+    | 🔜     | Audit, Inventory, Analytics, Deployment |
