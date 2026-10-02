# RestaurantFlow — Architecture

## Current Architecture (Phase 2)

```
Browser (React + Vite, port 5173)
    │
    │  REST API (JSON over HTTP)
    │  Authorization: Bearer <JWT>
    ▼
Django REST Framework (port 8000)
    │
    ├── /api/health/
    ├── /api/auth/          (accounts app)
    ├── /api/organizations/ (organizations app)
    ├── /api/restaurants/   (organizations app)
    └── /api/branches/      (organizations app)
    │
    ├── PostgreSQL 15 (port 5432)
    │       accounts_user
    │       organizations_organization
    │       organizations_restaurant
    │       organizations_restaurantsettings
    │       organizations_branch
    │       organizations_branchsettings
    │
    └── Redis 7 (port 6379)
            Django Channels (WebSocket-ready)
            Celery broker (foundation)
            Django cache backend
```

---

## Request / Response Flow

```
React Component
    │  (e.g. OrganizationsListPage)
    │
    ▼
React Query Hook
    │  (e.g. useOrganizations)
    │
    ▼
Service Function
    │  (e.g. listOrganizations())
    │
    ▼
Axios Instance (services/api.ts)
    │  Attaches Bearer token (request interceptor)
    │  Handles 401 → token refresh (response interceptor)
    │
    ▼
Django REST Framework View
    │  (e.g. OrganizationListCreateView)
    │  Authentication: JWTAuthentication
    │  Permissions: IsAuthenticated
    │
    ▼
Queryset Helper
    │  (e.g. get_organization_queryset())
    │  Phase 3 will add ownership filter here
    │
    ▼
Django ORM
    │
    ▼
PostgreSQL
```

---

## Django App Structure

```
config/         Project settings, URL routing, WSGI/ASGI
accounts/       Custom User model (email-based), JWT auth endpoints
core/           TimestampedModel, health endpoint, custom exception handler
organizations/  Phase 2 business hierarchy (Organization → Restaurant → Branch)
```

### Dependency graph

```
organizations → core (TimestampedModel)
accounts      → (standalone, no internal deps)
core          → (standalone base)
```

---

## Frontend Architecture

```
pages/
    Uses hooks → which call services → which call api.ts
    Renders components → which receive props typed from types/index.ts

components/ui/       Reusable primitives (no domain knowledge)
components/          Domain components (know about Organization, Restaurant, Branch)
hooks/               React Query data layer (cache management, mutations)
services/            API call functions (thin wrappers around api.ts helpers)
types/               Shared TypeScript interfaces (mirrors backend serializer output)
utils/               Pure utilities (cn, formatters)
```

---

## Security Architecture

### Authentication
- JWT Bearer tokens via `djangorestframework-simplejwt`
- Access token: 60 minutes (configurable via `JWT_ACCESS_TOKEN_LIFETIME`)
- Refresh token: 7 days (configurable via `JWT_REFRESH_TOKEN_LIFETIME`)
- Token rotation enabled — each refresh yields a new refresh token
- Frontend automatically retries with a fresh access token on 401

### Authorization (Phase 2)
All Phase 2 endpoints require `IsAuthenticated`. Full RBAC arrives in Phase 3.

The queryset helper pattern means adding ownership checks in Phase 3 requires changing only 3 functions, not 11 views:

```python
# Phase 2 (current):
def get_organization_queryset(request=None):
    return Organization.objects.annotate(...)

# Phase 3 (planned):
def get_organization_queryset(request=None):
    qs = Organization.objects.annotate(...)
    if request and not request.user.is_staff:
        qs = qs.filter(memberships__user=request.user)
    return qs
```

### IDOR Prevention
- All resource IDs are UUIDs — not guessable
- Nested URL parameters are typed as `<uuid:pk>` — non-UUID strings return 404
- Future Phase 3 ownership filter will ensure users only see their own orgs

### CORS
- `DEBUG=True` (development): all origins allowed
- `DEBUG=False` (production): `CORS_ALLOWED_ORIGINS` from environment variable

### Input Validation
- Serializer-level validation on all write endpoints
- Unique constraints enforced at both serializer and database level
- Custom exception handler wraps all errors — raw Django/DB errors never reach the client

---

## Data Integrity

| Concern                  | Mechanism                                              |
|--------------------------|--------------------------------------------------------|
| Soft delete              | `is_active` flag — no hard deletes on business records |
| Cascade prevention       | `PROTECT` FK on all org hierarchy relationships        |
| Duplicate codes          | `UniqueConstraint` at DB + serializer validation       |
| UUID-only public IDs     | `UUIDField(primary_key=True, default=uuid.uuid4)`      |
| Audit timestamps         | `TimestampedModel` on all models                       |
| Settings auto-creation   | Views call `get_or_create` after parent is saved       |

---

## Future Architecture Changes

### Phase 3 — RBAC
The User model will gain `organization`, `restaurant`, `branch`, and `role` fields. Queryset helpers will enforce scoped access.

### Phase 7 — WebSocket (Django Channels)
Django Channels is already installed and Redis is configured as the channel layer. Phase 7 adds the Kitchen Display System over WebSocket.

### Phase 15 — Production Deployment
```
CloudFront → ALB → Nginx → Gunicorn (REST)
                         → Daphne    (WebSocket/ASGI)
                   → RDS PostgreSQL
                   → ElastiCache Redis
                   → Celery Workers
```

---

## Phase 3 Architecture

```
Browser (React + Vite, port 5173)
    │  JWT Bearer token (stored in localStorage)
    ▼
Django REST Framework (port 8000)
    │
    ├── /api/health/
    ├── /api/auth/          login / logout / register / me / token refresh
    ├── /api/users/         user management
    ├── /api/roles/         role listing
    ├── /api/permissions/   permission registry
    ├── /api/user-role-assignments/   scope assignment management
    ├── /api/organizations/ (scoped to user's accessible orgs)
    ├── /api/restaurants/   (scoped to user's accessible restaurants)
    └── /api/branches/      (scoped to user's accessible branches)
    │
    ├── PostgreSQL 15 (port 5432)
    │       accounts_user
    │       accounts_userprofile
    │       accounts_permission
    │       accounts_role
    │       accounts_role_permissions
    │       accounts_userroleassignment
    │       organizations_organization
    │       organizations_restaurant
    │       organizations_restaurantsettings
    │       organizations_branch
    │       organizations_branchsettings
    │       token_blacklist_*  (simplejwt)
    │
    └── Redis 7 (port 6379)
            Django Channels
            Celery broker
            Django cache

```

### Authorization Flow (Phase 3)

```
Request with Bearer token
    ↓
JWTAuthentication (simplejwt)
    ↓
request.user resolved
    ↓
DRF permission classes evaluated left-to-right:
    IsAuthenticated → HasPermission(code) → [HasOrganizationAccess | HasRestaurantAccess | HasBranchAccess]
    ↓
get_queryset() calls acl.get_accessible_*() — scoped to user's assignments
    ↓
get_object() fetches from scoped queryset — outside-scope → 404
    ↓
Response (or 401 / 403 / 404)
```

### Django App Dependency Graph

```
organizations  →  core
accounts       →  core
organizations  →  accounts  (UserRoleAssignment FKs)
```

### Phase 3 Security Properties

- UUID PKs on all business models prevent sequential enumeration
- Soft delete (`is_active`) on Users, Roles, Assignments — never hard-delete operational records
- `PROTECT` FKs on org/restaurant/branch in UserRoleAssignment
- `UserRoleAssignment.clean()` enforces hierarchy at model level
- `get_queryset()` always scoped — no `Model.objects.all()` in business endpoints
- Resources outside scope return 404 (no existence leakage)
- `is_superuser` and `is_staff` cannot be set via the public API
- JWT refresh tokens are blacklisted on logout
