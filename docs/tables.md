# RestaurantFlow — Dining Tables

Phase 6

---

## Overview

A `DiningTable` is a physical seating surface at a Branch.  Table configuration (number, capacity, section) is stored here.  **Occupancy is never stored as a flag on the table itself** — it is derived from whether an active `TableSession` exists for that table.

```
Branch
  └── DiningTable (T01, T02 …)
          └── TableSession (OPEN / CLOSED history)
```

---

## DiningTable

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | Immutable |
| `branch` | FK → Branch | PROTECT |
| `table_number` | CharField(20) | Unique within branch |
| `name` | CharField(150) | Optional label e.g. "Window Table" |
| `capacity` | PositiveInt | Must be ≥ 1 |
| `section` | CharField(100) | e.g. Indoor, Outdoor, Terrace |
| `status` | ACTIVE / INACTIVE | Config status only |
| `display_order` | PositiveInt | UI ordering |
| `created_at / updated_at` | DateTimeField | Auto |

**Key design rules:**
- `table_number` is unique per branch — two different branches may both have `T01`.
- `status = INACTIVE` archives the table without deleting it. Historical sessions and orders remain intact.
- Do **not** add `is_occupied` to this model. Occupancy = active `TableSession` exists.
- Hard deletion is blocked when orders reference this table.

### Computed properties

| Property | Description |
|---|---|
| `is_active` | `status == ACTIVE` |
| `is_occupied` | `sessions.filter(status=OPEN).exists()` |
| `current_session` | The OPEN `TableSession` or `None` |

---

## TableSession

One session represents a group of guests occupying a table from arrival to departure.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | Immutable |
| `table` | FK → DiningTable | PROTECT |
| `opened_by` | FK → User | PROTECT |
| `closed_by` | FK → User (nullable) | PROTECT |
| `opened_at` | DateTimeField | auto_now_add |
| `closed_at` | DateTimeField (nullable) | Set on close |
| `status` | OPEN / CLOSED | |
| `guest_count` | PositiveInt | Min 1 |
| `notes` | TextField | Optional |

### Concurrency protection

A partial unique constraint enforces **exactly one OPEN session per table** at the DB level:

```sql
UNIQUE (table_id) WHERE status = 'OPEN'
```

The service layer additionally uses `select_for_update()` inside `transaction.atomic()` to prevent race conditions on concurrent open requests.

### Session lifecycle

```
open_table_session()  →  status = OPEN
close_table_session() →  status = CLOSED  (requires no active orders)
```

Closed sessions are **never deleted** — they form the historical audit trail.

---

## API Endpoints

| Method | URL | Permission | Description |
|---|---|---|---|
| GET | `/api/tables/` | `table.view` | List (scoped, filterable) |
| POST | `/api/tables/` | `table.create` | Create table |
| GET | `/api/tables/{id}/` | `table.view` | Retrieve |
| PATCH | `/api/tables/{id}/` | `table.update` | Update |
| POST | `/api/tables/{id}/disable/` | `table.disable` | Soft disable |
| POST | `/api/tables/{id}/enable/` | `table.update` | Re-enable |
| POST | `/api/tables/{id}/sessions/open/` | `table.session.open` | Open session |
| GET | `/api/table-sessions/` | `table.session.view` | List sessions |
| GET | `/api/table-sessions/{id}/` | `table.session.view` | Retrieve session |
| POST | `/api/table-sessions/{id}/close/` | `table.session.close` | Close session |

### Query filters (tables)

| Param | Example | Description |
|---|---|---|
| `branch` | `?branch=<uuid>` | Filter by branch |
| `section` | `?section=Indoor` | Filter by section (contains) |
| `status` | `?status=ACTIVE` | ACTIVE / INACTIVE |
| `occupied` | `?occupied=true` | true / false |

---

## Scope rules

Every API response is **scoped to the requesting user's accessible branches**. A user from Restaurant A will receive a 404 (not 403) when accessing a table belonging to Restaurant B — this prevents UUID enumeration (IDOR protection).

---

## Frontend components

| Component | Location | Purpose |
|---|---|---|
| `TableCard` | `components/orders/TableCard.tsx` | Single table tile with occupancy dot |
| `TableGrid` | `components/orders/TableGrid.tsx` | Section-grouped grid |
| `TablesDashboard` | `pages/tables/TablesDashboard.tsx` | Full page with filters and stats |
