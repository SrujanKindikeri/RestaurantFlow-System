# Phase 2 — Organizations, Restaurants & Branches

## Overview

Phase 2 establishes the organizational foundation of RestaurantFlow.
It introduces the three-level hierarchy that all future phases depend on:

```
Organization
    │
    ├── Restaurant
    │      ├── Branch
    │      ├── Branch
    │      └── Branch
    │
    └── Restaurant
           └── Branch
```

---

## What Was Built

### Backend

**New Django app:** `organizations`

**Models (5):**
- `Organization` — company / legal entity operating restaurants
- `Restaurant` — a restaurant brand belonging to an organization
- `Branch` — a physical location belonging to a restaurant
- `RestaurantSettings` — OneToOne per-restaurant configuration
- `BranchSettings` — OneToOne per-branch operational settings

**API (17 URL patterns):**
- Full CRUD via `GET`, `POST`, `PATCH` (no destructive `DELETE`)
- Nested endpoints: orgs → restaurants, restaurants → branches
- Stats endpoint for dashboard aggregate counts
- Settings endpoints per restaurant and branch

**Business rules enforced:**
- All primary keys are UUIDs
- `slug` is auto-generated and unique (with counter disambiguation)
- `code` is unique within parent scope (org → restaurant, restaurant → branch)
- Disabled organizations cannot receive new restaurants
- Disabled restaurants cannot receive new branches
- Soft-disable via `is_active` — no hard deletes on business records
- Foreign keys use `PROTECT` to prevent accidental cascade deletion
- `TimestampedModel` provides `created_at` / `updated_at` on all models

**Security preparation:**
- `get_organization_queryset()`, `get_restaurant_queryset()`, `get_branch_queryset()` are extracted as queryset helpers so Phase 3 can inject ownership filters without rewriting views
- All endpoints require authentication (`IsAuthenticated`)
- Nested URL parameters use UUID type converters (no integer enumeration)

**Admin:** All 5 models registered with `list_display`, `search_fields`, `list_filter`, inline relationships, and readonly timestamps.

**Seed data command:**
```bash
python manage.py seed_demo_data
python manage.py seed_demo_data --reset
```

Creates: 1 organization · 3 restaurants · 7 branches with settings.

**Tests (~50 test cases):**
- `OrganizationCRUDTests`
- `RestaurantTests`
- `BranchTests`
- `CrossOrganizationSecurityTests`
- `StatsEndpointTests`

---

### Frontend

**New TypeScript types:** `Organization`, `Restaurant`, `Branch`, `RestaurantSettings`, `BranchSettings`, all payload types, `OrganizationStats`

**Services (3 files):** `organizations.ts`, `restaurants.ts`, `branches.ts`
All use the existing centralised Axios client from `services/api.ts`.

**Hooks (3 files):** `useOrganizations.ts`, `useRestaurants.ts`, `useBranches.ts`
All use React Query v5 with full cache invalidation chains.

**UI primitives (9 components):**
`Badge`, `Button`, `Input/Textarea/Select`, `Modal/ConfirmDialog`, `Toast/ToastProvider`, `EmptyState`, `Breadcrumbs`, `PageHeader`, `StatCard`

**Domain components (6):**
`OrganizationCard`, `OrganizationForm`, `RestaurantCard`, `RestaurantForm`, `BranchCard`, `BranchForm`

**Pages (6):**
- `OrganizationsListPage` — list with create modal
- `OrganizationDetailPage` — detail with inline restaurant management
- `RestaurantsListPage` — all restaurants, admin view
- `RestaurantDetailPage` — detail with inline branch management
- `BranchesListPage` — all branches, admin view
- `BranchDetailPage` — detail with settings summary

**Navigation:** Sidebar rebuilt with icons for Dashboard / Organizations / Restaurants / Branches.

**Dashboard:** Updated with live organization stats (6 stat cards) and quick-link navigation tiles.

---

## Design Decisions

### Why soft-disable instead of delete?

Restaurant and POS data has historical and audit value. Orders, bills, payments, and cash sessions will eventually reference organizations, restaurants, and branches by foreign key. Hard-deleting a branch would either:
1. Cascade-delete all historical orders at that branch (catastrophic), or
2. Leave orphaned FK references (corrupt data).

Soft-disable (`is_active = False`) preserves the record and all relationships while preventing new operational data from being created under it.

### Why PROTECT on foreign keys?

`PROTECT` raises an error if you attempt to delete a parent that still has children. This is an explicit safety net: an organization cannot be deleted while it has restaurants, and a restaurant cannot be deleted while it has branches. This forces deliberate, explicit data management rather than silent cascade deletion.

### Why UUID primary keys?

Sequential integer IDs (`1`, `2`, `3`) can be enumerated in URLs. A user could iterate `GET /api/organizations/1/`, `GET /api/organizations/2/` to discover records they shouldn't access. UUIDs prevent this pattern. They also make IDs safe to include in logs and API responses without leaking business-sensitive information about record counts.

### Why scoped queryset helpers?

```python
def get_organization_queryset(request=None):
    return Organization.objects.annotate(...)
```

All views use these helpers rather than calling `Organization.objects` directly. This single-point-of-access pattern means Phase 3 can add:
```python
if not request.user.is_staff:
    return qs.filter(memberships__user=request.user)
```
in one place, and every view automatically respects it.

---

## File Map

### Backend

```
backend/organizations/
├── __init__.py
├── apps.py
├── models.py               Organization, Restaurant, Branch, Settings models
├── serializers.py          5 serializers + OrganizationStatsSerializer
├── views.py                11 class-based views + queryset helpers
├── urls.py                 17 URL patterns
├── admin.py                5 model registrations with inlines
├── tests.py                50 test cases
├── migrations/
│   └── 0001_initial.py     Initial migration (manually written)
└── management/
    └── commands/
        └── seed_demo_data.py
```

### Frontend

```
frontend/src/
├── types/index.ts                         +Phase 2 types
├── services/organizations.ts
├── services/restaurants.ts
├── services/branches.ts
├── hooks/useOrganizations.ts
├── hooks/useRestaurants.ts
├── hooks/useBranches.ts
├── components/ui/
│   ├── Badge.tsx
│   ├── Button.tsx
│   ├── Input.tsx            (+ Textarea, Select)
│   ├── Modal.tsx            (+ ConfirmDialog)
│   ├── Toast.tsx            (+ ToastProvider)
│   ├── EmptyState.tsx
│   ├── Breadcrumbs.tsx
│   ├── PageHeader.tsx
│   └── StatCard.tsx
├── components/organization/
│   ├── OrganizationCard.tsx
│   └── OrganizationForm.tsx
├── components/restaurant/
│   ├── RestaurantCard.tsx
│   └── RestaurantForm.tsx
├── components/branch/
│   ├── BranchCard.tsx
│   └── BranchForm.tsx
├── pages/organizations/
│   ├── OrganizationsListPage.tsx
│   └── OrganizationDetailPage.tsx
├── pages/restaurants/
│   ├── RestaurantsListPage.tsx
│   └── RestaurantDetailPage.tsx
├── pages/branches/
│   ├── BranchesListPage.tsx
│   └── BranchDetailPage.tsx
├── layouts/MainLayout.tsx   (rebuilt with sidebar)
├── pages/DashboardPage.tsx  (updated with stats)
├── App.tsx                  (Phase 2 routes added)
└── main.tsx                 (ToastProvider added)
```

---

## What Comes Next (Phase 3)

Phase 3 will introduce:
- Extend `User` model with role and organization/restaurant/branch assignment
- Roles: Company Head, Restaurant Owner, Branch Manager, Cashier, Waiter, Kitchen Staff, etc.
- The `get_*_queryset()` helpers will be narrowed to filter by the authenticated user's assigned scope
- Invitation and onboarding flow
- Frontend user management screens
