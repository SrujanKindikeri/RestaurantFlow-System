# RestaurantFlow — Architecture

## Overview

RestaurantFlow is a multi-restaurant management and POS platform built on a clean,
modular architecture that scales from a single restaurant to a company with many
branches and counters.

---

## Current Architecture (Phase 1)

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│                                                         │
│          React + TypeScript + Vite + Tailwind           │
│          React Router · React Query · Axios             │
└──────────────────────┬──────────────────────────────────┘
                       │
                  HTTP / REST
                       │
┌──────────────────────▼──────────────────────────────────┐
│                  Django REST API                         │
│                                                         │
│    Django 4.2 · DRF · Simple JWT · django-cors-headers  │
│    Django Channels (WebSocket-ready)                     │
└──────────┬───────────────────────┬──────────────────────┘
           │                       │
  ┌────────▼────────┐   ┌──────────▼─────────┐
  │   PostgreSQL    │   │       Redis         │
  │   (primary DB)  │   │  (cache / channels) │
  └─────────────────┘   └────────────────────┘
```

---

## Future Architecture (Phase 15)

```
              CloudFront / CDN
                    │
              Nginx (reverse proxy)
                    │
        ┌───────────┴────────────┐
        │                        │
   React SPA               Django ASGI
   (static)                      │
                    ┌────────────┴────────────┐
                    │                          │
              REST API                  WebSocket (Channels)
                    │                          │
              Gunicorn                   Daphne / ASGI
                    │
         ┌──────────┴────────────┐
         │                       │
    PostgreSQL (RDS)          Redis (ElastiCache)
                                   │
                              Celery Workers
```

---

## Backend Structure

```
backend/
├── config/           ← Django project config (settings, urls, wsgi, asgi)
├── accounts/         ← Custom User model, JWT auth endpoints
├── core/             ← Shared utilities, health endpoint, abstract models
│
│   — Future apps (added per phase) —
├── organizations/    ← Phase 2
├── restaurants/      ← Phase 2
├── branches/         ← Phase 2
├── users/            ← Phase 3
├── menu/             ← Phase 5
├── tables/           ← Phase 6
├── orders/           ← Phase 6
├── kitchen/          ← Phase 7
├── billing/          ← Phase 8
├── payments/         ← Phase 8
├── inventory/        ← Phase 10
├── accounting/       ← Phase 11
├── analytics/        ← Phase 12
└── audit/            ← Phase 9
```

---

## Frontend Structure

```
frontend/src/
├── components/   ← Reusable, stateless UI components
├── layouts/      ← Page shell / navigation wrappers
├── pages/        ← Route-level page components
├── services/     ← All API calls (never raw axios in components)
├── hooks/        ← Custom React hooks (data fetching, state)
├── contexts/     ← React context providers (Auth, etc.)
├── types/        ← Shared TypeScript interfaces & types
└── utils/        ← Pure helper functions (formatters, cn, etc.)
```

---

## Architectural Principles

### 1. Modular Django Apps
Each business domain lives in its own app. No monolithic `models.py`.

### 2. Service / Hook Separation (Frontend)
Business logic lives in `services/` and `hooks/`. Components only render.

### 3. Server-Side Authorization
All access control is enforced on the backend. Frontend never makes
authorization decisions.

### 4. Multi-Tenancy First
The system supports multiple organizations → restaurants → branches → counters
from day one. No single-tenant shortcuts that must be refactored later.

### 5. Immutable Financial Records
Completed financial transactions are never deleted. Audit trails are preserved.

### 6. Environment-Based Config
No secrets in code. All sensitive values come from environment variables.

---

## API Design

- All endpoints live under `/api/`
- Authentication uses JWT Bearer tokens
- Responses use a consistent envelope for errors:

```json
{
  "error": true,
  "message": "Human-readable summary",
  "details": { ... }
}
```

- Pagination follows DRF's `PageNumberPagination` pattern:

```json
{
  "count": 100,
  "next": "http://...",
  "previous": null,
  "results": [...]
}
```

---

## Data Flow (Phase 1)

```
User Action
    │
React Component
    │
  Hook  (useHealth, useQuery, etc.)
    │
  Service  (services/api.ts → services/health.ts)
    │
Axios (with JWT interceptor)
    │
Django View  (DRF APIView / @api_view)
    │
Django ORM
    │
PostgreSQL
```
