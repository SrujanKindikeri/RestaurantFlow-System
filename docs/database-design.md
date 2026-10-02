# RestaurantFlow — Database Design

## Phase 2 Schema

### Entity Relationship Overview

```
accounts_user
    │  (Phase 3 will add org/restaurant/branch FK)
    │
organizations_organization
    │ id (UUID PK)          slug (unique)
    │ name                  legal_name
    │ currency              timezone
    │ is_active             created_at / updated_at
    │
    └── organizations_restaurant
            │ id (UUID PK)
            │ organization_id (FK → PROTECT)
            │ name              slug (unique per org)
            │ code (unique per org)
            │ is_active         created_at / updated_at
            │
            ├── organizations_restaurantsettings
            │       id (UUID PK)
            │       restaurant_id (OneToOne → CASCADE)
            │       currency      timezone
            │       tax_enabled   default_tax_rate
            │       order_prefix  allow_negative_stock
            │
            └── organizations_branch
                    │ id (UUID PK)
                    │ restaurant_id (FK → PROTECT)
                    │ name          code (unique per restaurant)
                    │ latitude      longitude
                    │ is_active     created_at / updated_at
                    │
                    └── organizations_branchsettings
                            id (UUID PK)
                            branch_id (OneToOne → CASCADE)
                            opening_time    closing_time
                            default_order_type
```

---

## Tables

### `organizations_organization`

| Column       | Type         | Constraints            |
|--------------|--------------|------------------------|
| id           | UUID         | PK, default=uuid4      |
| name         | VARCHAR(255) | NOT NULL, index        |
| legal_name   | VARCHAR(255) |                        |
| slug         | SLUG(255)    | UNIQUE, index          |
| email        | EMAIL        |                        |
| phone        | VARCHAR(30)  |                        |
| address      | TEXT         |                        |
| city         | VARCHAR(100) |                        |
| state        | VARCHAR(100) |                        |
| country      | VARCHAR(100) | default 'India'        |
| postal_code  | VARCHAR(20)  |                        |
| tax_id       | VARCHAR(100) |                        |
| currency     | VARCHAR(10)  | default 'INR'          |
| timezone     | VARCHAR(50)  | default 'Asia/Kolkata' |
| is_active    | BOOLEAN      | default True, index    |
| created_at   | TIMESTAMPTZ  | auto                   |
| updated_at   | TIMESTAMPTZ  | auto                   |

Indexes: `slug`, `is_active`

### `organizations_restaurant`

| Column          | Type         | Constraints                             |
|-----------------|--------------|-----------------------------------------|
| id              | UUID         | PK                                      |
| organization_id | UUID         | FK → Organization (PROTECT)             |
| name            | VARCHAR(255) | NOT NULL, index                         |
| slug            | SLUG(255)    | unique per org (UniqueConstraint)       |
| code            | VARCHAR(50)  | unique per org (UniqueConstraint), index|
| description     | TEXT         |                                         |
| email           | EMAIL        |                                         |
| phone           | VARCHAR(30)  |                                         |
| address         | TEXT         |                                         |
| city            | VARCHAR(100) |                                         |
| state           | VARCHAR(100) |                                         |
| country         | VARCHAR(100) |                                         |
| postal_code     | VARCHAR(20)  |                                         |
| is_active       | BOOLEAN      | default True, index                     |
| created_at      | TIMESTAMPTZ  | auto                                    |
| updated_at      | TIMESTAMPTZ  | auto                                    |

Constraints:
- `unique_restaurant_code_per_org` — `(organization_id, code)`
- `unique_restaurant_slug_per_org` — `(organization_id, slug)`

Indexes: `(organization_id, is_active)`, `(organization_id, code)`, `(organization_id, slug)`

### `organizations_branch`

| Column        | Type           | Constraints                                  |
|---------------|----------------|----------------------------------------------|
| id            | UUID           | PK                                           |
| restaurant_id | UUID           | FK → Restaurant (PROTECT)                   |
| name          | VARCHAR(255)   | NOT NULL, index                              |
| code          | VARCHAR(50)    | unique per restaurant (UniqueConstraint)     |
| address       | TEXT           |                                              |
| city          | VARCHAR(100)   |                                              |
| state         | VARCHAR(100)   |                                              |
| country       | VARCHAR(100)   |                                              |
| postal_code   | VARCHAR(20)    |                                              |
| phone         | VARCHAR(30)    |                                              |
| email         | EMAIL          |                                              |
| latitude      | DECIMAL(9,6)   | nullable                                     |
| longitude     | DECIMAL(9,6)   | nullable                                     |
| is_active     | BOOLEAN        | default True, index                          |
| created_at    | TIMESTAMPTZ    | auto                                         |
| updated_at    | TIMESTAMPTZ    | auto                                         |

Constraints:
- `unique_branch_code_per_restaurant` — `(restaurant_id, code)`

Indexes: `(restaurant_id, is_active)`, `(restaurant_id, code)`

### `organizations_restaurantsettings`

| Column              | Type          | Constraints                        |
|---------------------|---------------|------------------------------------|
| id                  | UUID          | PK                                 |
| restaurant_id       | UUID          | OneToOne → Restaurant (CASCADE)    |
| currency            | VARCHAR(10)   | blank (inherits from org if empty) |
| timezone            | VARCHAR(50)   | blank                              |
| tax_enabled         | BOOLEAN       | default True                       |
| default_tax_rate    | DECIMAL(5,2)  | default 0.00                       |
| receipt_header      | TEXT          |                                    |
| receipt_footer      | TEXT          |                                    |
| allow_negative_stock| BOOLEAN       | default False                      |
| order_prefix        | VARCHAR(20)   | default 'ORD'                      |
| is_active           | BOOLEAN       | default True                       |
| created_at          | TIMESTAMPTZ   | auto                               |
| updated_at          | TIMESTAMPTZ   | auto                               |

### `organizations_branchsettings`

| Column              | Type          | Constraints                        |
|---------------------|---------------|------------------------------------|
| id                  | UUID          | PK                                 |
| branch_id           | UUID          | OneToOne → Branch (CASCADE)        |
| opening_time        | TIME          | nullable                           |
| closing_time        | TIME          | nullable                           |
| default_order_type  | VARCHAR(20)   | choices: dine_in/takeaway/delivery |
| receipt_footer      | TEXT          |                                    |
| is_active           | BOOLEAN       | default True                       |
| created_at          | TIMESTAMPTZ   | auto                               |
| updated_at          | TIMESTAMPTZ   | auto                               |

---

## Design Principles

### UUID Primary Keys

All business entities use `UUID` primary keys (`default=uuid.uuid4`).
This prevents enumeration attacks (`/api/organizations/1/`, `2/`, `3/`) and makes IDs safe to expose publicly.

### Soft Delete via `is_active`

No business record is ever hard-deleted through the normal API. Setting `is_active = False` preserves the record and all FK relationships while preventing new operational data from being created beneath it. Administrators can reactivate records via the API or Django Admin.

### PROTECT Foreign Keys

`ForeignKey(on_delete=PROTECT)` is used for all parent→child org relationships:
- `Restaurant.organization` → PROTECT
- `Branch.restaurant` → PROTECT

This ensures that attempting to delete an organization with restaurants, or a restaurant with branches, raises an explicit database error instead of silently cascading.

Settings use `CASCADE` because they are subordinate configuration records that have no independent meaning without their parent.

### TimestampedModel

All models inherit `core.models.TimestampedModel` which provides `created_at` (auto on create) and `updated_at` (auto on every save). This is the audit trail foundation. Phase 9 will add a full `AuditLog` model.

### Slug Auto-Generation

`Organization.save()` and `Restaurant.save()` auto-generate slugs from `name` using `django.utils.text.slugify`. Collisions are resolved by appending a counter (`-1`, `-2`, etc.). Slugs are unique globally for organizations, and unique per-organization for restaurants.

---

## Future Schema (upcoming phases)

```
Phase 3:
    accounts_user
        ├── organization_id (FK)
        ├── restaurant_id (FK, nullable)
        ├── branch_id (FK, nullable)
        └── role (CharField)

Phase 4:
    organizations_counter
        └── branch_id (FK)
    organizations_cashsession
        └── counter_id (FK)

Phase 5:
    menu_category
        └── restaurant_id (FK)
    menu_item
        └── category_id (FK)

Phase 6+:
    orders_order, orders_orderitem
    billing_bill, billing_payment
    inventory_*, accounting_*
```

---

## Phase 3 Schema

### New Tables

#### `accounts_permission`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| code | varchar(100) unique | e.g. `restaurant.view` |
| name | varchar(150) | Human-readable |
| module | varchar(50) | e.g. `restaurant` |
| action | varchar(50) | e.g. `view` |
| is_active | bool | default True |
| created_at | timestamptz | auto |
| updated_at | timestamptz | auto |

#### `accounts_role`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| code | varchar(50) unique | e.g. `COMPANY_HEAD` |
| name | varchar(100) | |
| description | text | |
| scope | varchar(20) | organization / restaurant / branch |
| is_system_role | bool | protected from deletion |
| is_active | bool | |
| created_at | timestamptz | auto |
| updated_at | timestamptz | auto |

#### `accounts_role_permissions` (M2M)

| Column | Type |
|--------|------|
| role_id | UUID FK → accounts_role |
| permission_id | UUID FK → accounts_permission |

#### `accounts_userprofile`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | bigint FK → accounts_user (CASCADE) | OneToOne |
| display_name | varchar(150) | |
| employee_code | varchar(50) indexed | |
| profile_photo | image path | nullable |
| is_active | bool | |
| created_at | timestamptz | auto |
| updated_at | timestamptz | auto |

#### `accounts_userroleassignment`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| user_id | bigint FK → accounts_user (CASCADE) | |
| role_id | UUID FK → accounts_role (PROTECT) | |
| organization_id | UUID FK → organizations_organization (PROTECT) | nullable |
| restaurant_id | UUID FK → organizations_restaurant (PROTECT) | nullable |
| branch_id | UUID FK → organizations_branch (PROTECT) | nullable |
| is_active | bool indexed | |
| created_at | timestamptz | auto |
| updated_at | timestamptz | auto |

### `accounts_user` — Phase 3 additions

| Column | Type | Notes |
|--------|------|-------|
| phone | varchar(30) | new in Phase 3 |

All other User fields are unchanged from Phase 1.

### Design Notes

- `UserRoleAssignment.clean()` validates: branch belongs to restaurant, restaurant belongs to organization, role scope is respected.
- `PROTECT` FKs on organization/restaurant/branch prevent orphaned assignments.
- `CASCADE` on user ensures assignments are deleted when a user is deleted.
- Employee codes are not unique globally — uniqueness within an organization is enforced at the application level (not yet a DB constraint).
- All UUID fields use `uuid.uuid4` as default — never sequential.
