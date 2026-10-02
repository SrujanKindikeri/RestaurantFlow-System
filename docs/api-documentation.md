# RestaurantFlow — API Documentation

## Base URL

```
http://localhost:8000/api
```

## Authentication

All Phase 2 endpoints require a valid JWT Bearer token.

```
Authorization: Bearer <access_token>
```

Obtain tokens:
```http
POST /api/auth/login/
Content-Type: application/json

{"email": "user@example.com", "password": "password"}
```

Response:
```json
{"access": "...", "refresh": "..."}
```

---

## Error Format

All errors follow the envelope from `core.exceptions.custom_exception_handler`:

```json
{
  "error": true,
  "message": "A restaurant with code 'SPICE-001' already exists in this organization.",
  "details": {
    "code": ["A restaurant with code 'SPICE-001' already exists in this organization."]
  }
}
```

---

## Health Check

### `GET /api/health/`

No authentication required.

**Response 200:**
```json
{"status": "ok", "service": "RestaurantFlow API"}
```

---

## Authentication Endpoints

### `POST /api/auth/register/`

**Request:**
```json
{
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "password": "secret1234",
  "password_confirm": "secret1234"
}
```

**Response 201:** User object (id, email, first_name, last_name, full_name, is_active, date_joined)

---

### `POST /api/auth/login/`

**Request:**
```json
{"email": "user@example.com", "password": "secret1234"}
```

**Response 200:**
```json
{"access": "<jwt>", "refresh": "<jwt>"}
```

---

### `POST /api/auth/token/refresh/`

**Request:** `{"refresh": "<token>"}`
**Response 200:** `{"access": "<new_token>"}`

---

### `GET /api/auth/me/`

Returns the authenticated user's profile.

---

## Organization Endpoints

### `GET /api/organizations/`

List all organizations.

**Response 200:**
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "name": "RestaurantFlow Foods",
      "legal_name": "RestaurantFlow Foods Pvt Ltd",
      "slug": "restaurantflow-foods",
      "email": "admin@company.com",
      "phone": "+91 9000000001",
      "city": "Bangalore",
      "country": "India",
      "currency": "INR",
      "timezone": "Asia/Kolkata",
      "is_active": true,
      "restaurant_count": 3,
      "active_restaurant_count": 3,
      "created_at": "2026-10-02T12:00:00Z",
      "updated_at": "2026-10-02T12:00:00Z"
    }
  ]
}
```

---

### `POST /api/organizations/`

Create a new organization.

**Request:**
```json
{
  "name": "Acme Foods",
  "legal_name": "Acme Foods Pvt Ltd",
  "email": "admin@acme.com",
  "currency": "INR",
  "timezone": "Asia/Kolkata"
}
```

**Validation errors:**
- `name` is required
- `email` must be valid if provided

**Response 201:** Organization object

---

### `GET /api/organizations/stats/`

Returns aggregate counts for all organizations.

**Response 200:**
```json
{
  "total_organizations": 2,
  "active_organizations": 2,
  "total_restaurants": 5,
  "active_restaurants": 5,
  "total_branches": 12,
  "active_branches": 11
}
```

---

### `GET /api/organizations/<id>/`

Retrieve organization detail with embedded restaurant list.

**Response 200:**
```json
{
  "id": "uuid",
  "name": "RestaurantFlow Foods",
  "...": "...",
  "restaurants": [
    {"id": "uuid", "name": "Spice Garden", "code": "SPICE-001", "...": "..."}
  ]
}
```

---

### `PATCH /api/organizations/<id>/`

Partial update. To soft-disable:

```json
{"is_active": false}
```

To reactivate:
```json
{"is_active": true}
```

**Response 200:** Updated organization object.

---

### `GET /api/organizations/<org_id>/restaurants/`

List restaurants belonging to this organization.

---

### `POST /api/organizations/<org_id>/restaurants/`

Create a restaurant under this organization.

**Request:**
```json
{
  "name": "Spice Garden",
  "code": "SPICE-001",
  "description": "Authentic South Indian cuisine",
  "phone": "+91 9000000002",
  "city": "Bangalore"
}
```

**Validation errors:**
- `name` and `code` are required
- `code` must be unique within the organization
- Organization must be active

**Response 201:** Restaurant object. Settings are auto-created.

---

## Restaurant Endpoints

### `GET /api/restaurants/`

List all restaurants across all organizations.

---

### `GET /api/restaurants/<id>/`

Restaurant detail with embedded branches and settings.

```json
{
  "id": "uuid",
  "name": "Spice Garden",
  "code": "SPICE-001",
  "branch_count": 3,
  "active_branch_count": 3,
  "settings": {
    "currency": "INR",
    "tax_enabled": true,
    "default_tax_rate": "5.00",
    "order_prefix": "SG"
  },
  "branches": [...]
}
```

---

### `PATCH /api/restaurants/<id>/`

Partial update. Soft-disable: `{"is_active": false}`

---

### `GET /api/restaurants/<id>/branches/`

List branches for this restaurant.

---

### `POST /api/restaurants/<id>/branches/`

Create a branch.

**Request:**
```json
{
  "name": "LPU Campus",
  "code": "SG-LPU",
  "address": "LPU Campus, Phagwara",
  "city": "Phagwara",
  "phone": "+91 9000000010"
}
```

**Validation errors:**
- `name` and `code` are required
- `code` must be unique within the restaurant
- Restaurant must be active

**Response 201:** Branch object. Settings are auto-created.

---

### `GET /api/restaurants/<id>/settings/`

Get restaurant settings.

---

### `PATCH /api/restaurants/<id>/settings/`

Update restaurant settings:

```json
{
  "tax_enabled": true,
  "default_tax_rate": "5.00",
  "order_prefix": "SG",
  "allow_negative_stock": false
}
```

---

## Branch Endpoints

### `GET /api/branches/`

List all branches.

---

### `GET /api/branches/<id>/`

Branch detail with embedded settings.

---

### `PATCH /api/branches/<id>/`

Partial update. Soft-disable: `{"is_active": false}`

---

### `GET /api/branches/<id>/settings/`

Get branch settings.

---

### `PATCH /api/branches/<id>/settings/`

```json
{
  "opening_time": "09:00:00",
  "closing_time": "22:00:00",
  "default_order_type": "dine_in"
}
```

`default_order_type` choices: `dine_in`, `takeaway`, `delivery`

---

## Planned Endpoints (future phases)

| Phase | Prefix              | Description               |
|-------|---------------------|---------------------------|
| 3     | `/api/users/`       | User management           |
| 3     | `/api/roles/`       | Role assignments          |
| 4     | `/api/counters/`    | POS counters              |
| 4     | `/api/sessions/`    | Cash sessions             |
| 5     | `/api/menu/`        | Menu categories and items |
| 6     | `/api/orders/`      | Order management          |
| 8     | `/api/billing/`     | Bills and payments        |

---

## Phase 3 — Auth Additions

### `POST /api/auth/logout/`

Blacklists the refresh token. Requires authentication.

**Request:**
```json
{"refresh": "<refresh_token>"}
```

**Response 200:**
```json
{"detail": "Successfully logged out."}
```

---

## Phase 3 — Users

### `GET /api/users/`

List users scoped to the requesting user's authority. Requires `user.view`.

**Query params:** `search`, `page`

**Response 200:**
```json
{
  "count": 9,
  "results": [
    {
      "id": 1,
      "email": "company@restaurantflow.dev",
      "full_name": "Srujan Mehta",
      "phone": "+91-9000000100",
      "is_active": true,
      "profile": {"employee_code": "EMP-0001", "display_name": "..."},
      "scope": {
        "is_superuser": false,
        "permissions": ["organization.view", "restaurant.view", "..."],
        "roles": [{"role_code": "COMPANY_HEAD", "role_name": "Company Head", ...}]
      }
    }
  ]
}
```

### `POST /api/users/`

Create a new user. Requires `user.create`.

**Request:**
```json
{"email": "new@example.com", "first_name": "First", "last_name": "Last", "password": "Secure@123"}
```

### `GET /api/users/{id}/`

Full user detail including all role assignments and effective permissions.

### `PATCH /api/users/{id}/`

Update safe fields: `first_name`, `last_name`, `phone`, `profile`.

### `POST /api/users/{id}/disable/`

Soft-disable a user. Requires `user.disable`.

### `POST /api/users/{id}/reactivate/`

Reactivate a disabled user. Requires `user.disable`.

### `GET /api/users/{id}/roles/`

List active role assignments for a user.

### `POST /api/users/{id}/roles/`

Assign a role. Requires `role.manage`. Subject to privilege-escalation rules.

**Request:**
```json
{
  "role": "<role-uuid>",
  "organization": "<org-uuid>",
  "restaurant": "<restaurant-uuid>",
  "branch": "<branch-uuid>"
}
```

---

## Phase 3 — Role Assignments

### `GET /api/user-role-assignments/{id}/`

Assignment detail.

### `PATCH /api/user-role-assignments/{id}/`

Update scope fields. Requires `role.manage`.

### `POST /api/user-role-assignments/{id}/disable/`

Deactivate an assignment. Requires `role.manage`.

---

## Phase 3 — Roles

### `GET /api/roles/`

List all roles with embedded permissions. Requires `role.view`.

### `GET /api/roles/{id}/`

Role detail including all permission codes.

---

## Phase 3 — Permissions

### `GET /api/permissions/`

List all registered permission codes. Requires `permission.view`.

**Query params:** `module` (filter by module name)

**Response 200:**
```json
{
  "count": 46,
  "results": [
    {"id": "...", "code": "organization.view", "name": "View Organization", "module": "organization", "action": "view", "is_active": true}
  ]
}
```

---

## Phase 3 — Permission Codes Reference

| Module | Codes |
|--------|-------|
| organization | `organization.view` `organization.create` `organization.update` `organization.disable` |
| restaurant | `restaurant.view` `restaurant.create` `restaurant.update` `restaurant.disable` |
| branch | `branch.view` `branch.create` `branch.update` `branch.disable` |
| user | `user.view` `user.create` `user.update` `user.disable` |
| role | `role.view` `role.manage` |
| permission | `permission.view` `permission.manage` |
| order | `order.view` `order.create` `order.update` `order.cancel` |
| bill | `bill.view` `bill.create` `bill.print` `bill.cancel` `bill.edit.request` `bill.edit.approve` |
| payment | `payment.view` `payment.create` `payment.refund.request` `payment.refund.approve` |
| inventory | `inventory.view` `inventory.receive` `inventory.adjust` `inventory.wastage` |
| expense | `expense.view` `expense.create` `expense.approve` |
| report | `report.sales.view` `report.accounts.view` `report.profit.view` |
| kitchen | `kitchen.order.view` `kitchen.order.update` |
| issue | `issue.view` `issue.create` `issue.resolve` |
