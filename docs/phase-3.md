# RestaurantFlow — Phase 3

## Users, Roles, Permissions & Multi-Level Access Control

Phase 3 builds the complete security foundation on top of the Phase 2 Organization → Restaurant → Branch hierarchy. Every future module (POS, orders, billing, inventory) depends on this access-control layer.

---

## What Was Built

### Backend

#### New Models (`accounts/`)
- **User** — extended with `phone` field
- **UserProfile** — `employee_code`, `display_name`, `profile_photo`; one-to-one with User; auto-created on registration
- **Permission** — granular permission codes (`restaurant.view`, `bill.create`, etc.); 46 permissions registered across 13 modules
- **Role** — 9 system roles with scope (`organization` / `restaurant` / `branch`); M2M relationship to Permission
- **UserRoleAssignment** — scoped assignment of a role to a user; `clean()` enforces hierarchy integrity at the model level

#### Access Control Layer
- `accounts/access.py` — queryset scoping and object-level access checks; no role names hard-coded in views
- `accounts/permissions.py` — reusable DRF permission classes including `HasPermission(code)` factory
- `accounts/services.py` — privilege-escalation-aware user/role management operations

#### APIs
- `POST /api/auth/logout/` — JWT refresh token blacklist
- `GET /api/auth/me/` — current user with full scope summary and effective permissions
- `GET /api/users/` — user list (scoped to actor's authority)
- `POST /api/users/` — create user (requires `user.create`)
- `GET /api/users/{id}/` — user detail with roles and permissions
- `PATCH /api/users/{id}/` — update safe fields
- `POST /api/users/{id}/disable/` — soft-disable
- `POST /api/users/{id}/reactivate/` — reactivate
- `GET /api/users/{id}/roles/` — list role assignments
- `POST /api/users/{id}/roles/` — create role assignment
- `GET /api/user-role-assignments/{id}/` — assignment detail
- `PATCH /api/user-role-assignments/{id}/` — update assignment
- `POST /api/user-role-assignments/{id}/disable/` — deactivate assignment
- `GET /api/roles/` — list roles with permissions
- `GET /api/roles/{id}/` — role detail
- `GET /api/permissions/` — list all registered permissions

#### Organizations API — Phase 3 changes
All queryset helpers now enforce user scope. Stats endpoint returns scoped counts. Resources outside the user's scope return 404.

#### Admin
Registered: `User`, `UserProfile`, `Permission`, `Role`, `UserRoleAssignment`. System roles protected from deletion in admin. Role permissions editable via filter_horizontal widget.

#### Seed Command
`python manage.py seed_demo_data` now seeds:
- 46 permissions across all modules
- 9 system roles with permission assignments
- 9 demo users (company head through accountant)
- Role assignments with correct scope chains

Demo credentials:

| Email | Role |
|-------|------|
| company@restaurantflow.dev | COMPANY_HEAD |
| admin@restaurantflow.dev | CENTRAL_ADMIN |
| owner@spicegarden.dev | RESTAURANT_OWNER |
| manager@spicegarden.dev | RESTAURANT_MANAGER |
| cashier@spicegarden.dev | CASHIER |
| waiter@spicegarden.dev | WAITER |
| kitchen@spicegarden.dev | KITCHEN_STAFF |
| inventory@spicegarden.dev | INVENTORY_STAFF |
| accounts@spicegarden.dev | ACCOUNTANT |

Default password: `Demo@1234` (set via `DEMO_PASSWORD` env var)

#### Tests
30+ tests covering:
- Authentication (valid/invalid login, unauthenticated rejection, password not exposed)
- Permission checks (with/without required permission)
- Organization scope (cross-tenant access blocked with 404)
- Restaurant scope (cross-restaurant access blocked)
- Branch scope (cross-branch access blocked)
- Privilege escalation prevention (cashier/manager cannot assign company head, cannot create users)
- Role assignment scope validation (hierarchy enforced at model level)
- User disable/reactivate (actor authority enforced)

---

### Frontend

#### New Files
- `src/contexts/AuthContext.tsx` — full implementation: user population on mount, `setTokens` fetches `/api/auth/me/`, JWT blacklist on logout, `hasPermission(code)` and `hasRole(code)` helpers
- `src/components/ProtectedRoute.tsx` — redirects unauthenticated users to `/login`
- `src/pages/auth/LoginPage.tsx` — email/password login form
- `src/pages/auth/RegisterPage.tsx` — registration form
- `src/pages/users/UsersListPage.tsx` — searchable table with roles, employee codes, disable/reactivate
- `src/pages/users/UserDetailPage.tsx` — full user view: identity, active role assignments, effective permissions grid
- `src/pages/roles/RolesListPage.tsx` — role cards with scope, permissions count, click-to-detail modal
- `src/components/users/RoleAssignmentModal.tsx` — cascading dropdowns (role → org → restaurant → branch)
- `src/services/auth.ts` — login, logout, register, fetchCurrentUser
- `src/services/users.ts` — CRUD + disable/reactivate + role assignments
- `src/services/roles.ts` — list roles, list permissions
- `src/hooks/useUsers.ts` — React Query hooks for all user operations
- `src/hooks/useRoles.ts` — React Query hooks for roles and permissions

#### Modified Files
- `src/main.tsx` — `AuthProvider` added to provider stack
- `src/App.tsx` — `ProtectedRoute` wraps all authenticated routes; `/login`, `/register` are public; `/users`, `/users/:id`, `/roles` added
- `src/layouts/MainLayout.tsx` — permission-filtered nav items, user info + primary role in sidebar, logout button
- `src/types/index.ts` — Phase 3 types: `User`, `UserDetail`, `UserProfile`, `UserScope`, `Permission`, `Role`, `UserRoleAssignment` and all payloads

---

## Architecture After Phase 3

```
Organization
    │
    ├── Users
    │     └── UserRoleAssignment
    │               ├── Role
    │               │     └── Permissions
    │               ├── Organization scope
    │               ├── Restaurant scope
    │               └── Branch scope
    │
    └── Restaurants
          └── Branches
```

Every API request is evaluated:
```
Authentication → User → Role → Permission → Scope → Resource
```

---

## Security Properties

- **IDOR protection** — resources outside user's scope return 404
- **Cross-tenant isolation** — Org A users cannot access Org B resources
- **Privilege escalation prevention** — no actor can grant a role beyond their own authority
- **No password exposure** — passwords never appear in API responses or logs
- **JWT blacklist** — logout invalidates the refresh token server-side
- **Scope hierarchy validated at DB level** — `UserRoleAssignment.clean()` enforces relationships

---

## Next Phase

Phase 4 will add:
- `Counter` model
- Counter assignment to users (Cashier → Counter)
- Cash sessions (opening/closing cash)
- Shift management
- Cash reconciliation

The `UserRoleAssignment` model is designed to support counter-level scope in Phase 4 without schema changes to existing models.
