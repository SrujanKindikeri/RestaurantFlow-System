# RestaurantFlow

**A production-oriented, multi-restaurant management and POS platform built with Django, React, PostgreSQL, and Redis.**

RestaurantFlow is designed to manage multiple organizations, restaurants, branches, counters, employees, menus, orders, kitchen operations, billing, inventory, and business analytics through a centralized platform.

---

## Current Development Status

**Current Phase: Phase 5 — Menu Management**

The Phase 5 menu catalog system is implemented and operational.

It supports restaurant-level menu management, configurable categories, branch-specific pricing, menu availability, and tax configuration.

### Current Architecture

```text
Organization
    │
    └── Restaurant
          │
          ├── Restaurant Settings
          │
          ├── Branch
          │     ├── Branch Settings
          │     ├── Counters
          │     └── Counter Sessions
          │
          └── Menu Management
                │
                ├── Categories
                ├── Tax Rates
                └── Menu Items
                      │
                      ├── Branch Pricing
                      │     └── Price History
                      │
                      └── Branch Availability
                            └── Availability Windows
```

### Phase 5 Features

- Restaurant-specific menu categories.
- Menu item creation and management.
- Veg, Non-Veg, Snacks, Beverages, Desserts and configurable categories.
- Branch-specific menu pricing.
- Historical price records.
- Branch-specific item availability.
- Availability time windows.
- Restaurant-scoped tax configuration.
- Backend-controlled pricing and tax resolution.
- API-based menu catalog access.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python, Django 4.2 |
| API | Django REST Framework 3.15 |
| Authentication | JWT, Simple JWT |
| Database | PostgreSQL 15 |
| Cache | Redis 7 |
| Real-time | Django Channels |
| Frontend | React 18, TypeScript |
| Build Tool | Vite |
| Styling | Tailwind CSS |
| Server State | TanStack Query v5 |
| HTTP Client | Axios |
| Infrastructure | Docker, Docker Compose |

### Architecture Principles

- Modular Django applications.
- REST API-based frontend/backend communication.
- PostgreSQL as the primary source of truth.
- Redis for caching and real-time infrastructure.
- JWT-based authentication.
- Role-based and permission-based authorization.
- Organization, restaurant and branch data isolation.
- Backend-authoritative business rules.
- Decimal-based financial calculations.
- Historical records for important business transactions.

---

## Quick Start

### Prerequisites

Install:

- Python 3.11 or compatible version.
- Node.js and npm.
- Docker Desktop.
- Git.

### 1. Start Infrastructure

From the project root:

```powershell
docker compose up -d
```

This starts the configured infrastructure services, including PostgreSQL and Redis.

Check their status:

```powershell
docker compose ps
```

### 2. Configure the Backend

```powershell
cd backend
```

Create your environment file:

```powershell
Copy-Item .env.example .env
```

Configure the required database, Redis, Django secret key, and other environment variables.

Install dependencies:

```powershell
pip install -r requirements.txt
```

Apply database migrations:

```powershell
python manage.py migrate
```

Create an administrative account:

```powershell
python manage.py createsuperuser
```

Start the Django development server:

```powershell
python manage.py runserver
```

Backend:

```text
http://localhost:8000
```

Django Admin:

```text
http://localhost:8000/admin/
```

### 3. Optional Demo Data

Load the initial organization, restaurant, and branch data:

```powershell
python manage.py seed_demo_data
```

Load the Phase 5 menu demonstration data:

```powershell
python manage.py seed_menu_data
```

**Important:** These commands are optional. Inspect their implementation before using `--reset` or running them against a database containing real business data.

### 4. Configure the Frontend

Open another terminal:

```powershell
cd frontend
```

Create the environment file:

```powershell
Copy-Item .env.example .env
```

Configure the API URL:

```env
VITE_API_URL=http://localhost:8000/api
```

Install dependencies:

```powershell
npm install
```

Start the frontend:

```powershell
npm run dev
```

Frontend:

```text
http://localhost:5173
```

### 5. Verify Backend Connectivity

Open:

```text
http://localhost:8000/api/health/
```

Expected response:

```json
{
  "status": "ok",
  "service": "RestaurantFlow API"
}
```

The actual response must be verified against the implemented health endpoint.

---

## Project Structure

The following is the intended high-level structure. Some applications are introduced in later development phases.

```text
RestaurantFlow-System/
│
├── backend/
│   ├── config/
│   │   └── Django project configuration
│   │
│   ├── accounts/
│   │   └── Custom user and authentication
│   │
│   ├── core/
│   │   ├── Common models
│   │   ├── Health endpoint
│   │   └── Shared utilities
│   │
│   ├── organizations/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   └── management/
│   │       └── commands/
│   │           └── seed_demo_data.py
│   │
│   ├── menu/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── services.py
│   │   ├── tests.py
│   │   └── management/
│   │       └── commands/
│   │           └── seed_menu_data.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── types/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── organization/
│   │   │   ├── restaurant/
│   │   │   ├── branch/
│   │   │   └── menu/
│   │   ├── pages/
│   │   │   ├── organizations/
│   │   │   ├── restaurants/
│   │   │   ├── branches/
│   │   │   └── menu/
│   │   └── layouts/
│   │
│   └── package.json
│
├── docs/
│   ├── architecture.md
│   ├── database-design.md
│   ├── api-documentation.md
│   ├── development-setup.md
│   ├── roadmap.md
│   └── phases/
│
├── deployment/
│
├── docker-compose.yml
├── README.md
└── .gitignore
```

The actual repository structure should be treated as authoritative. Do not create empty applications merely to match this documentation.

---

## API Endpoints

### Core

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health/` | Backend health check |

### Organizations — Phase 2

| Method | Endpoint | Description |
|---|---|---|
| GET, POST | `/api/organizations/` | List and create organizations |
| GET | `/api/organizations/stats/` | Organization dashboard statistics |
| GET, PATCH | `/api/organizations/{id}/` | Retrieve and update organization |
| GET, POST | `/api/organizations/{id}/restaurants/` | List and create restaurants |

### Restaurants

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/restaurants/` | List accessible restaurants |
| GET, PATCH | `/api/restaurants/{id}/` | Retrieve and update restaurant |
| GET, POST | `/api/restaurants/{id}/branches/` | List and create branches |
| GET, PATCH | `/api/restaurants/{id}/settings/` | Restaurant settings |

### Branches

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/branches/` | List accessible branches |
| GET, PATCH | `/api/branches/{id}/` | Retrieve and update branch |
| GET, PATCH | `/api/branches/{id}/settings/` | Branch settings |

### Menu — Phase 5

The menu API supports:

- Menu categories.
- Menu items.
- Branch-specific pricing.
- Price history.
- Branch availability.
- Tax rate configuration.
- Branch-specific catalog retrieval.

**Note:** Exact menu endpoint paths should be documented from the implemented Django URL configuration rather than assumed.

### Authentication

Protected API endpoints use:

```http
Authorization: Bearer <access_token>
```

Authentication verifies the user's identity. Authorization determines what the user can do and which organization, restaurant, branch, or resource they can access.

A valid JWT alone must not grant unrestricted administrative access.

---

## Django Administration

Django Admin is available at:

```text
http://localhost:8000/admin/
```

Create an administrative user:

```powershell
cd backend
python manage.py createsuperuser
```

Registered models should reflect the actual implementation, including:

- Organization
- Restaurant
- Branch
- RestaurantSettings
- BranchSettings
- User
- Menu-related models

---

## Development and Validation Commands

### Backend

```powershell
cd backend

python manage.py check
python manage.py migrate
python manage.py test
```

### Frontend

```powershell
cd frontend

npm install
npm run type-check
npm run build
```

Keep automated tests in the repository. They protect authentication, tenant isolation, pricing, tax calculations, and transaction workflows.

---

## Development Roadmap

RestaurantFlow follows a 26-phase development roadmap.

| Phase | Status | Description |
|---|---|---|
| 1 | ✅ Completed | Foundation — Django, React, PostgreSQL and Docker |
| 2 | ✅ Completed | Organizations, Restaurants and Branches |
| 3 | ✅ Completed | Authentication, Users, Roles and Permissions |
| 4 | ✅ Completed | Counters and Cash Sessions |
| 5 | ✅ Completed | Menu, Categories, Branch Pricing, Availability and Tax |
| 6 | ✅ Completed | Tables, Orders and POS |
| 7 | ✅ Completed | Kitchen Display System |
| 8 | ✅ Completed | Billing and Invoice Management |
| 9 | ✅ Completed | Payments and Refunds |
| 10 | 🔜 ✅ Completed | Inventory and Stock Management |
| 11 | 🔜 ✅ Completed | Recipes and Inventory Consumption |
| 12 | 🔜 ✅ Completed | Expenses and Financial Operations |
| 13 | 🔜 ✅ Completed | Accounting and Double-Entry Bookkeeping |
| 14 | 🔜 ✅ Completed | Reports, Analytics and Business Intelligence |
| 15 | 🔜 ✅ Completed | Central Control Center |
| 16 | 🔜 ✅ Completed | Notifications and Communication |
| 17 | 🔜 ✅ Completed | Customer CRM, Loyalty and Feedback |
| 18 | 🔜 ✅ Completed | Marketing and Campaign Management |
| 19 | 🔜 ✅ Completed | Advanced POS and Restaurant Operations |
| 20 | 🔜 ✅ Completed | Multi-Branch Enterprise Operations |
| 21 | 🔜 ✅ Completed | Security, Audit and Compliance Hardening |
| 22 | 🔜 ✅ Completed | Performance and Scalability |
| 23 | 🔜 ✅ Completed | DevOps and Production Deployment |
| 24 | 🔜 ✅ Completed | Monitoring and Observability |
| 25 | 🔜 ✅ Completed | Backup and Disaster Recovery |
| 26 | 🔜 ✅ Completed | Final Integration, QA and Production Release |

**Status definitions:**

- Completed: Implemented and validated.
- In Progress: Currently being implemented.
- Planned: Not yet completed.

Do not mark a phase complete simply because its files or initial models exist. Validate its workflows, permissions, APIs, frontend integration, and tests.

---

## Documentation

| Document | Description |
|---|---|
| `docs/architecture.md` | System architecture and design decisions |
| `docs/database-design.md` | Database schema and relationships |
| `docs/api-documentation.md` | API reference |
| `docs/development-setup.md` | Local development setup |
| `docs/roadmap.md` | Complete 26-phase development roadmap |
| `docs/phases/` | Phase-specific implementation documentation |
| `deployment/README.md` | Deployment documentation |

---

## Security and Data Integrity

RestaurantFlow is designed around the following principles:

- JWT-based authentication.
- Role- and permission-based authorization.
- Organization, restaurant and branch-level access control.
- Backend-enforced tenant isolation.
- Server-side validation of business operations.
- Historical pricing and tax snapshots.
- Decimal-based monetary calculations.
- Protected administrative operations.
- Audit trails for sensitive operations as introduced in their respective phases.
- Environment-based secret management.

Production security and compliance must be validated before deployment.

---

## Project Goals

The long-term goal is to provide a centralized platform where restaurant businesses can manage:

1. Multiple companies and restaurants.
2. Multiple branches and counters.
3. Employees, roles and permissions.
4. Menus, pricing and taxes.
5. Orders and POS operations.
6. Kitchen workflows.
7. Billing and payments.
8. Inventory and procurement.
9. Expenses and accounting.
10. Customer relationships and loyalty.
11. Marketing and promotions.
12. Analytics and enterprise operations.

RestaurantFlow is being developed incrementally, with each phase building on the previous architecture.

---

**RestaurantFlow — One platform to manage restaurant operations.**
