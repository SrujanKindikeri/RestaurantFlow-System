# RestaurantFlow — Access Control

Phase 3 establishes the complete security foundation for multi-tenant, role-based access control across the Organization → Restaurant → Branch hierarchy.

---

## Core Principle

The backend **always** determines authorization. Frontend permission checks are UI hints only.

```
Request
  ↓
JWT Authentication
  ↓
User (authenticated, active)
  ↓
Role (via UserRoleAssignment)
  ↓
Permission code check
  ↓
Scope check (org / restaurant / branch)
  ↓
Resource returned or 403/404
```

Resource IDs supplied by the frontend are never trusted. The backend resolves scope from stored role assignments.

---

## Models

### User
Standard Django custom user model. Email-based authentication. BigAutoField PK (integer). No role or org FK directly on the user — scope is handled entirely via `UserRoleAssignment`.

### UserProfile
One-to-one extension. Stores `employee_code`, `display_name`, `profile_photo`. Auto-created on user registration.

### Permission
Granular permission codes. `code` is unique (e.g. `restaurant.view`). Grouped by `module` + `action`.

### Role
Named role with a `scope` (organization / restaurant / branch). `is_system_role=True` records are seeded and protected from deletion. M2M relationship to `Permission`.

### UserRoleAssignment
Links a `User` to a `Role` within a specific scope (organization, optional restaurant, optional branch). The model's `clean()` enforces the hierarchy: branch belongs to restaurant, restaurant belongs to organization, role scope is respected.

---

## System Roles

| Code | Scope | Description |
|------|-------|-------------|
| `COMPANY_HEAD` | organization | Full organizational access including financials and user management |
| `CENTRAL_ADMIN` | organization | Technical/admin oversight; no financial ownership |
| `RESTAURANT_OWNER` | restaurant | Full control over a single restaurant and its branches |
| `RESTAURANT_MANAGER` | branch | Day-to-day operations for a restaurant or branch |
| `CASHIER` | branch | POS operations — orders, bills, payments |
| `WAITER` | branch | Table service — order creation and viewing |
| `KITCHEN_STAFF` | branch | Kitchen display and order status updates |
| `INVENTORY_STAFF` | branch | Stock receiving, adjustments, wastage |
| `ACCOUNTANT` | branch | Expenses and financial reporting |

---

## Scope Examples

### Company Head
```
user = Srujan
role = COMPANY_HEAD
organization = RestaurantFlow Foods
restaurant = NULL
branch = NULL
```
Can see all organizations, restaurants, branches, and users within the organization.

### Restaurant Owner
```
user = Arjun
role = RESTAURANT_OWNER
organization = RestaurantFlow Foods
restaurant = Spice Garden
branch = NULL
```
Can see all branches of Spice Garden. Cannot access Urban Bites or Royal Kitchen.

### Branch Manager
```
user = Kavya
role = RESTAURANT_MANAGER
organization = RestaurantFlow Foods
restaurant = Spice Garden
branch = LPU Campus
```
Can see LPU Campus branch. Cannot see Main Market or City Center.

### Cashier
```
user = Rohit
role = CASHIER
organization = RestaurantFlow Foods
restaurant = Spice Garden
branch = LPU Campus
```
Has `order.create`, `bill.create`, `bill.view`, `bill.print`, `payment.create`. No access to inventory, financials, or user management.

---

## Backend Access Control Layer

### `accounts/access.py`

| Function | Description |
|----------|-------------|
| `has_permission(user, code)` | Check a permission code against user's active role assignments |
| `get_accessible_organizations(user)` | QuerySet of orgs the user can access |
| `get_accessible_restaurants(user)` | QuerySet of restaurants the user can access |
| `get_accessible_branches(user)` | QuerySet of branches the user can access |
| `can_access_organization(user, org)` | Object-level check |
| `can_access_restaurant(user, restaurant)` | Object-level check |
| `can_access_branch(user, branch)` | Object-level check |
| `get_user_scope_summary(user)` | Structured dict: permissions list + role assignments |
| `can_manage_user(actor, target)` | Whether actor can manage a specific user |
| `can_assign_role(actor, role, ...)` | Privilege-escalation check for role assignment |

### `accounts/permissions.py` — DRF Permission Classes

| Class | Description |
|-------|-------------|
| `HasPermission(code)` | Factory returning a permission class for a specific code |
| `HasOrganizationAccess` | Object-level: user must have access to the Organization |
| `HasRestaurantAccess` | Object-level: user must have access to the Restaurant |
| `HasBranchAccess` | Object-level: user must have access to the Branch |
| `IsOrganizationAdmin` | Request-level: user holds COMPANY_HEAD or CENTRAL_ADMIN |
| `IsRestaurantAdmin` | Request-level: user holds COMPANY_HEAD, CENTRAL_ADMIN, or RESTAURANT_OWNER |
| `IsSelfOrAdmin` | Object-level: user is themselves or an authorized manager |

Usage:
```python
# In a view
permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]

# In get_permissions()
def get_permissions(self):
    if self.request.method == "PATCH":
        return [IsAuthenticated(), HasPermission("restaurant.update")(), HasRestaurantAccess()]
    return [IsAuthenticated(), HasRestaurantAccess()]
```

### `accounts/services.py`

Business-logic operations that span multiple models. Views call these instead of duplicating logic.

| Function | Description |
|----------|-------------|
| `create_user(actor, ...)` | Create user — enforces escalation rules, strips is_superuser/is_staff |
| `disable_user(actor, user)` | Soft-disable — cannot disable yourself or a superuser |
| `reactivate_user(actor, user)` | Reactivate a disabled user |
| `assign_role(actor, ...)` | Create assignment — checks can_assign_role before saving |
| `remove_role_assignment(actor, assignment)` | Soft-deactivate an assignment |

---

## Queryset Scoping

Organization views always scope to the requesting user's accessible resources:

```python
# organizations/views.py
def get_organization_queryset(request):
    if user.is_superuser or user.is_staff:
        return Organization.objects.all()
    accessible_ids = acl.get_accessible_organizations(user).values_list("pk", flat=True)
    return Organization.objects.filter(pk__in=accessible_ids)
```

The same pattern applies to restaurants and branches. A user who knows a UUID for a resource they cannot access receives **404**, not 403. This prevents existence leakage (IDOR protection).

---

## Privilege Escalation Rules

| Actor | Can assign |
|-------|-----------|
| Superuser | Any role |
| COMPANY_HEAD / CENTRAL_ADMIN | Any role within their org except COMPANY_HEAD / CENTRAL_ADMIN |
| RESTAURANT_OWNER | Branch-level roles within their restaurant |
| Manager and below | No role assignment permitted |

Nobody can grant a role with greater scope than their own.

---

## Frontend Permission Checks

The `AuthContext` provides `hasPermission(code)` and `hasRole(code)` helpers. These are used to show/hide UI elements only. The backend always enforces authorization.

```tsx
const { hasPermission } = useAuth()

// Show create button only if permitted
{hasPermission('user.create') && <Button>Add User</Button>}

// Filter nav items
const visible = NAV_ITEMS.filter(item => !item.permission || hasPermission(item.permission))
```

The sidebar automatically hides navigation items the current user lacks permission to access.

---

## Security Events (Audit-Ready)

The following events are logged to `logs/security.log` and `logs/general.log` in preparation for a future audit module:

- `login` — successful token issuance
- `failed_login` — invalid credentials
- `user_created` — new user created
- `user_disabled` — user soft-disabled
- `user_reactivated` — user reactivated
- `role_assigned` — role assignment created
- `role_removed` — role assignment deactivated
- `access_denied` — permission check failure (403/404)

---

## HTTP Status Code Conventions

| Status | Meaning |
|--------|---------|
| 401 | Not authenticated — token missing or expired |
| 403 | Authenticated but lacks the required permission |
| 404 | Resource does not exist **or** exists but is outside user's scope |
| 400 | Validation failure (scope hierarchy, password rules, etc.) |

404 is intentionally returned in some 403 scenarios to avoid leaking resource existence to unauthorized callers.
