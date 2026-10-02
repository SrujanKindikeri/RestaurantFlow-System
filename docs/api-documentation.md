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

---

## Phase 4 — Counter API

All counter endpoints require authentication (`Authorization: Bearer <token>`).
All responses follow the standard error envelope on failure:
```json
{ "error": { "code": "ERROR_CODE", "message": "Human-readable message." } }
```

### GET /api/counters/

List counters scoped to the authenticated user's branches.

**Query params:** `branch=<uuid>`, `status=ACTIVE|INACTIVE|MAINTENANCE`

**Response 200:**
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "uuid",
      "branch": "uuid",
      "branch_name": "LPU Campus",
      "restaurant_id": "uuid",
      "restaurant_name": "Spice Garden",
      "name": "Main Billing",
      "code": "C01",
      "counter_type": "MAIN_BILLING",
      "status": "ACTIVE",
      "is_active": true
    }
  ]
}
```

---

### POST /api/counters/

Create a counter. Requires `counter.create`.

**Request:**
```json
{
  "branch": "uuid",
  "name": "Main Billing",
  "code": "C01",
  "counter_type": "MAIN_BILLING",
  "description": "",
  "location": "Near entrance"
}
```

---

### GET /api/counters/{id}/

Retrieve counter detail including current session summary and active assignments.

---

### PATCH /api/counters/{id}/

Partial update. Requires `counter.update`. Accepts same fields as POST except `branch`.

---

### POST /api/counters/{id}/disable/

Set counter status to `INACTIVE`. Requires `counter.disable`.

---

### POST /api/counters/{id}/reactivate/

Set counter status to `ACTIVE`. Requires `counter.update`.

---

### POST /api/counters/{id}/sessions/open/

Open a new cash session. Requires `counter.session.open`.

**Request:**
```json
{
  "opening_cash": "5000.00",
  "shift": "uuid"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "counter": "uuid",
  "counter_code": "C01",
  "status": "OPEN",
  "opening_cash": "5000.00",
  "expected_cash": "5000.00",
  "opened_at": "2026-10-02T08:03:00Z",
  "opened_by_email": "cashier@spicegarden.dev"
}
```

**Error codes:** `COUNTER_INACTIVE`, `COUNTER_MAINTENANCE`, `COUNTER_SESSION_ALREADY_OPEN`, `INVALID_OPENING_CASH`

---

### GET /api/counter-sessions/

List sessions. Requires `counter.session.view`.

**Query params:** `counter=<uuid>`, `status=OPEN|CLOSED|FORCE_CLOSED`, `branch=<uuid>`

---

### GET /api/counter-sessions/{id}/

Retrieve session detail.

---

### POST /api/counter-sessions/{id}/close/

Close an open session. Requires `counter.session.close`.

**Request:**
```json
{
  "actual_cash": "9850.00",
  "closing_note": "Normal closing. All clear."
}
```

**Response 200:** Full session with `cash_difference` calculated by backend.

**Error codes:** `COUNTER_SESSION_NOT_OPEN`, `INVALID_ACTUAL_CASH`

---

### POST /api/counter-sessions/{id}/force-close/

Force-close an open session. Requires `counter.session.force_close`.

**Request:**
```json
{
  "reason": "Cashier left unexpectedly",
  "actual_cash": "4800.00"
}
```

**Error codes:** `FORCE_CLOSE_NOT_ALLOWED`, `COUNTER_SESSION_NOT_OPEN`

---

### GET /api/counter-assignments/

List assignments. Requires `counter.view`.
**Query params:** `counter=<uuid>`, `is_active=true|false`

---

### POST /api/counter-assignments/

Assign a user to a counter. Requires `counter.assign`.

**Request:**
```json
{
  "counter": "uuid",
  "user": 42,
  "expires_at": "2026-12-31T23:59:00Z"
}
```

---

### POST /api/counter-assignments/{id}/deactivate/

Deactivate an assignment. Requires `counter.unassign`. Historical record is preserved.

---

### GET /api/shifts/

List shifts. Requires `shift.view`.
**Query params:** `branch=<uuid>`

---

### POST /api/shifts/

Create a shift. Requires `shift.manage`.

**Request:**
```json
{
  "branch": "uuid",
  "name": "Morning",
  "start_time": "08:00:00",
  "end_time": "16:00:00"
}
```

---

### GET /api/counter-dashboard/

Branch-level counter status overview. Requires `counter.view`.
**Query params:** `branch=<uuid>` (optional — returns all accessible if omitted)

**Response 200:**
```json
{
  "branch_id": "uuid",
  "counters": [
    {
      "id": "uuid",
      "code": "C01",
      "name": "Main Billing",
      "status": "ACTIVE",
      "current_session": {
        "id": "uuid",
        "opened_by_name": "Rohit Verma",
        "opened_at": "2026-10-02T08:03:00Z",
        "opening_cash": "5000.00",
        "status": "OPEN"
      },
      "assigned_cashier": {
        "user_id": 5,
        "user_name": "Rohit Verma",
        "user_email": "cashier@spicegarden.dev"
      }
    }
  ],
  "summary": {
    "total": 3,
    "active": 2,
    "sessions_open": 1,
    "inactive": 0,
    "maintenance": 1
  }
}
```

---

## Phase 5 — Menu API

All endpoints require `Authorization: Bearer <access_token>` and the corresponding permission.
Results are scoped to the requesting user's accessible restaurants and branches — cross-tenant access returns 404.

### Tax Rates

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/menu/tax-rates/` | `tax.view` |
| POST | `/api/menu/tax-rates/` | `tax.create` |
| GET | `/api/menu/tax-rates/{id}/` | `tax.view` |
| PATCH | `/api/menu/tax-rates/{id}/` | `tax.update` |
| POST | `/api/menu/tax-rates/{id}/disable/` | `tax.update` |
| POST | `/api/menu/tax-rates/{id}/enable/` | `tax.update` |

### Categories

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/menu/categories/` | `category.view` |
| POST | `/api/menu/categories/` | `category.create` |
| GET | `/api/menu/categories/{id}/` | `category.view` |
| PATCH | `/api/menu/categories/{id}/` | `category.update` |
| POST | `/api/menu/categories/{id}/disable/` | `category.disable` |
| POST | `/api/menu/categories/{id}/enable/` | `category.create` |

### Menu Items

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/menu/items/` | `menu.view` |
| POST | `/api/menu/items/` | `menu.create` |
| GET | `/api/menu/items/{id}/` | `menu.view` |
| PATCH | `/api/menu/items/{id}/` | `menu.update` |
| POST | `/api/menu/items/{id}/disable/` | `menu.disable` |
| POST | `/api/menu/items/{id}/enable/` | `menu.create` |

**Query parameters (items):** `restaurant`, `category`, `food_type`, `is_active`, `is_available`, `search`

### Prices

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/menu/prices/` | `menu.price.view` |
| POST | `/api/menu/prices/` | `menu.price.create` |
| GET | `/api/menu/prices/{id}/` | `menu.price.view` |
| PATCH | `/api/menu/prices/{id}/` | `menu.price.update` |
| POST | `/api/menu/prices/{id}/deactivate/` | `menu.price.update` |

### Availability

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/menu/availability/` | `menu.availability.view` |
| POST | `/api/menu/availability/` | `menu.availability.update` |
| GET | `/api/menu/availability/{id}/` | `menu.availability.view` |
| PATCH | `/api/menu/availability/{id}/` | `menu.availability.update` |

### Branch Catalog (POS)

```http
GET /api/menu/branches/{branch_id}/catalog/
```

Permission: `menu.view`. Returns only active categories, active items, and items available at this branch. Includes branch-specific price and tax data.

**Response structure:**
```json
{
  "branch": { "id": "...", "name": "LPU Campus", "restaurant_id": "...", "restaurant_name": "..." },
  "categories": [
    {
      "id": "...", "name": "Non-Veg", "slug": "non-veg", "display_order": 2,
      "items": [
        {
          "id": "...", "name": "Chicken Biryani", "slug": "chicken-biryani",
          "sku": "SG-CB-001", "short_description": "...",
          "food_type": "NON_VEG", "image": null,
          "display_order": 1, "preparation_time_minutes": 20,
          "price": "220.00",
          "tax_rate_code": "GST_STANDARD", "tax_rate_name": "GST Standard", "tax_rate": "5.000"
        }
      ]
    }
  ]
}
```

### Menu Dashboard

```http
GET /api/menu/dashboard/
```

Permission: `menu.view`. Returns summary counts for categories, items, and per-branch availability stats.
