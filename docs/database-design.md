# RestaurantFlow — Database Design

## Overview

RestaurantFlow uses PostgreSQL as its primary database.

The schema is designed for multi-tenancy from day one:

```
Organization (Company)
    └── Restaurant
            └── Branch
                    └── Counter
                             └── Cash Session
                                      └── Orders / Bills
```

---

## Phase 1 — Current Schema

Only the custom `User` table exists in Phase 1.

### accounts_user

| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | Auto-increment |
| email | varchar (unique) | Login identifier |
| first_name | varchar(150) | |
| last_name | varchar(150) | |
| password | varchar | Hashed (Django PBKDF2) |
| is_active | boolean | Default: true |
| is_staff | boolean | Admin site access |
| is_superuser | boolean | Full permissions |
| date_joined | timestamptz | Auto-set on create |
| last_login | timestamptz | Updated by Django auth |
| updated_at | timestamptz | Auto-updated |

---

## Future Schema (Phases 2–15)

### organizations (Phase 2)

| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| name | varchar | Company name |
| slug | varchar (unique) | URL-safe identifier |
| is_active | boolean | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### restaurants (Phase 2)

| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| organization | FK → organizations | |
| name | varchar | |
| slug | varchar | Unique within org |
| is_active | boolean | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### branches (Phase 2)

| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| restaurant | FK → restaurants | |
| name | varchar | |
| address | text | |
| is_active | boolean | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

### counters (Phase 4)

| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| branch | FK → branches | |
| name | varchar | |
| is_active | boolean | |
| created_at | timestamptz | |

### users (Phase 3)

Extends `accounts_user` with role and multi-tenant assignment:

| Column | Type | Notes |
|--------|------|-------|
| user | FK → accounts_user | |
| role | varchar / FK | Company Head, Manager, Cashier, etc. |
| organization | FK → organizations | nullable |
| restaurant | FK → restaurants | nullable |
| branch | FK → branches | nullable |
| counter | FK → counters | nullable |

### orders (Phase 6)

| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| counter | FK → counters | |
| table | FK → tables (nullable) | Dine-in only |
| status | varchar | pending, in_kitchen, ready, served, billed |
| order_type | varchar | dine_in, takeaway, delivery |
| created_by | FK → users | |
| created_at | timestamptz | Immutable once set |
| updated_at | timestamptz | |

### bills (Phase 8)

| Column | Type | Notes |
|--------|------|-------|
| id | bigint (PK) | |
| order | FK → orders | |
| total_amount | decimal(12,2) | |
| tax_amount | decimal(12,2) | |
| discount_amount | decimal(12,2) | |
| status | varchar | draft, issued, paid, refunded |
| created_at | timestamptz | **Immutable** |

> **Rule:** Financial records are never deleted. Corrections use reversal entries.

---

## Design Principles

### UUIDs vs BigInt PKs
Phase 1 uses `BigAutoField` (bigint). If public-facing UUIDs are needed for
security (hiding record counts), they can be added as a separate `uuid` field
in Phase 2+.

### Soft Deletes
Business entities (restaurants, branches, menu items) use `is_active` flags
rather than hard deletes. This preserves referential integrity for historical
orders and financial data.

### Timestamps
All models inherit from `core.models.TimestampedModel` which provides:
- `created_at` — set once on creation
- `updated_at` — updated on every save

### Financial Immutability
Once a `Bill` or `Payment` is finalized, it must not be mutated.
Corrections are handled by reversal records (credit notes, refunds).
This ensures a complete audit trail.

### Multi-Tenancy Strategy
All queries for business data must be scoped through the tenant hierarchy:

```
Request User
    → verify Organization membership
    → verify Restaurant access
    → verify Branch access
    → verify Counter access (where applicable)
    → execute query
```

This is enforced server-side on every API request.
Frontend IDs are never trusted for authorization.
