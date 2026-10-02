# RestaurantFlow — API Documentation

## Overview

- Base URL: `http://localhost:8000/api/` (development)
- All requests and responses use **JSON**
- Authentication: **JWT Bearer Token**
- API versioning will be introduced in Phase 2 under `/api/v1/`

---

## Authentication

Include the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Tokens are obtained via the login endpoint and refreshed using the refresh endpoint.

---

## Error Response Envelope

All errors return a consistent shape:

```json
{
  "error": true,
  "message": "Human-readable description of the error",
  "details": {
    "field_name": ["Validation message"]
  }
}
```

---

## Phase 1 Endpoints

### Health Check

#### `GET /api/health/`

Check backend availability. No authentication required.

**Response `200 OK`:**

```json
{
  "status": "ok",
  "service": "RestaurantFlow API"
}
```

---

### Authentication

#### `POST /api/auth/register/`

Register a new user account.

**Request:**

```json
{
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "password": "securepassword123",
  "password_confirm": "securepassword123"
}
```

**Response `201 Created`:**

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "full_name": "Jane Doe",
  "is_active": true,
  "date_joined": "2026-10-02T10:00:00Z"
}
```

---

#### `POST /api/auth/login/`

Obtain JWT access and refresh tokens.

**Request:**

```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response `200 OK`:**

```json
{
  "access": "<jwt_access_token>",
  "refresh": "<jwt_refresh_token>"
}
```

---

#### `POST /api/auth/token/refresh/`

Exchange a refresh token for a new access token.

**Request:**

```json
{
  "refresh": "<jwt_refresh_token>"
}
```

**Response `200 OK`:**

```json
{
  "access": "<new_jwt_access_token>"
}
```

---

#### `POST /api/auth/token/verify/`

Verify that an access token is valid.

**Request:**

```json
{
  "token": "<jwt_access_token>"
}
```

**Response `200 OK`:** (empty body on success)

---

#### `GET /api/auth/me/`

Return the authenticated user's profile.

**Headers:** `Authorization: Bearer <access_token>`

**Response `200 OK`:**

```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "full_name": "Jane Doe",
  "is_active": true,
  "date_joined": "2026-10-02T10:00:00Z"
}
```

---

## Future Endpoints (Phase 2+)

The following endpoint groups will be added in later phases:

| Phase | Prefix | Description |
|-------|--------|-------------|
| 2 | `/api/organizations/` | Company management |
| 2 | `/api/restaurants/` | Restaurant management |
| 2 | `/api/branches/` | Branch management |
| 3 | `/api/users/` | User & role management |
| 4 | `/api/counters/` | Counter & cash session management |
| 5 | `/api/menu/` | Menu categories & items |
| 6 | `/api/tables/` | Table management |
| 6 | `/api/orders/` | Order creation & management |
| 7 | `/api/kitchen/` | Kitchen display & ticket management |
| 8 | `/api/billing/` | Bill generation & payment |
| 9 | `/api/approvals/` | Discount & void approvals |
| 10 | `/api/inventory/` | Inventory management |
| 11 | `/api/accounting/` | Accounting & journal entries |
| 12 | `/api/analytics/` | Reporting & analytics |

---

## Pagination

All list endpoints return paginated results:

```json
{
  "count": 150,
  "next": "http://localhost:8000/api/restaurants/?page=2",
  "previous": null,
  "results": [...]
}
```

Default page size: **20**. Override with `?page_size=50` (max: 100).

---

## Filtering & Search

List endpoints support:

- `?search=keyword` — full-text search on searchable fields
- `?ordering=field` — sort ascending (`field`) or descending (`-field`)
- Field-specific filters vary by endpoint (documented per endpoint in later phases)

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK — successful GET / PUT / PATCH |
| 201 | Created — successful POST |
| 204 | No Content — successful DELETE |
| 400 | Bad Request — validation error |
| 401 | Unauthorized — missing or expired token |
| 403 | Forbidden — authenticated but not authorized |
| 404 | Not Found |
| 405 | Method Not Allowed |
| 500 | Internal Server Error |
