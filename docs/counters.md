# Counters — Architecture & Reference

## Overview

A **Counter** is a physical POS (Point of Sale) billing station at a Branch. Phase 4 introduces the full counter infrastructure: counter management, staff assignment, and cash session lifecycle.

```
Organization
    └── Restaurant
          └── Branch
                ├── Counter 01 (C01 — Main Billing)
                ├── Counter 02 (C02 — Takeaway)
                └── Counter 03 (C03 — Snacks)
```

Each counter is independently identifiable and operates its own cash sessions.

---

## Data Models

### Counter

| Field          | Type         | Notes                                          |
|----------------|--------------|------------------------------------------------|
| `id`           | UUID         | Primary key                                    |
| `branch`       | FK → Branch  | PROTECT — never cascade-deletes                |
| `name`         | CharField    | Human-readable name, e.g. "Main Billing"       |
| `code`         | CharField    | Short identifier, e.g. "C01". Auto-uppercased. |
| `description`  | TextField    | Optional                                       |
| `counter_type` | TextChoices  | MAIN_BILLING / TAKEAWAY / SNACKS / DRIVE_THROUGH / OTHER |
| `location`     | CharField    | Physical location hint                         |
| `status`       | TextChoices  | ACTIVE / INACTIVE / MAINTENANCE                |
| `is_active`    | Boolean      | Derived from `status == ACTIVE`. Not editable directly. |
| `created_at`   | DateTimeField| Auto                                           |
| `updated_at`   | DateTimeField| Auto                                           |

**Uniqueness constraint:** `(branch, code)` — two different branches may each have a counter coded `C01`. The same code cannot exist twice within the same branch.

### Counter Status vs Session Status

These are **distinct concepts** and must not be confused:

| Concept        | Values                           | Meaning                          |
|----------------|----------------------------------|----------------------------------|
| Counter status | ACTIVE / INACTIVE / MAINTENANCE  | Operational state of the hardware POS station |
| Session status | OPEN / CLOSED / FORCE_CLOSED     | State of a cash session running on that counter |

A counter with status `MAINTENANCE` cannot open a new session. A counter with status `ACTIVE` and session status `CLOSED` is ready for a new session.

### CounterAssignment

Links a user (cashier, manager) to a specific counter. Multiple assignments over time are kept for historical audit.

| Field        | Type               | Notes                                   |
|--------------|--------------------|-----------------------------------------|
| `id`         | UUID               | Primary key                             |
| `counter`    | FK → Counter       | PROTECT                                 |
| `user`       | FK → User          | PROTECT                                 |
| `assigned_by`| FK → User (nullable) | Who created this assignment           |
| `assigned_at`| DateTimeField      | Auto on creation                        |
| `expires_at` | DateTimeField      | Optional expiry                         |
| `is_active`  | Boolean            | `false` = deactivated, record preserved |

Assignments are **never deleted**. Use `is_active = false` to end an assignment. History is preserved.

### Shift

A named shift schedule for a branch. Shifts are configuration — not permanently tied to any one employee.

| Field        | Type         | Notes            |
|--------------|--------------|------------------|
| `id`         | UUID         | Primary key      |
| `branch`     | FK → Branch  | PROTECT          |
| `name`       | CharField    | e.g. "Morning"   |
| `start_time` | TimeField    | e.g. 08:00       |
| `end_time`   | TimeField    | e.g. 16:00       |
| `is_active`  | Boolean      |                  |

### CounterSession

One operational cash session at a counter.

| Field           | Type          | Notes                                              |
|-----------------|---------------|----------------------------------------------------|
| `id`            | UUID          | Primary key                                        |
| `counter`       | FK → Counter  | PROTECT                                            |
| `shift`         | FK → Shift    | Optional, SET_NULL on delete                       |
| `opened_by`     | FK → User     | PROTECT                                            |
| `closed_by`     | FK → User     | Nullable. PROTECT                                  |
| `opened_at`     | DateTimeField | Auto on creation                                   |
| `closed_at`     | DateTimeField | Nullable — set on close                            |
| `opening_cash`  | DecimalField  | Physical cash at session start. Never float.       |
| `expected_cash` | DecimalField  | Phase 4: equals `opening_cash`. Future: includes sales. |
| `actual_cash`   | DecimalField  | Nullable — entered at close                        |
| `cash_difference` | DecimalField | `actual_cash − expected_cash`. Backend-calculated. |
| `status`        | TextChoices   | OPEN / CLOSED / FORCE_CLOSED                       |
| `closing_note`  | TextField     | Optional closing note or force-close reason        |

**Critical:** All monetary fields use `DecimalField`. Never float.

**Partial unique constraint:** Only ONE open session per counter at a time — enforced at the database level via a PostgreSQL partial unique index on `(counter) WHERE status = 'OPEN'`.

---

## Counter Type Choices

| Value          | Label         |
|----------------|---------------|
| `MAIN_BILLING` | Main Billing  |
| `TAKEAWAY`     | Takeaway      |
| `SNACKS`       | Snacks        |
| `DRIVE_THROUGH`| Drive Through |
| `OTHER`        | Other         |

---

## Counter Status Choices

| Value         | Label       | Can open session? |
|---------------|-------------|-------------------|
| `ACTIVE`      | Active      | Yes               |
| `INACTIVE`    | Inactive    | No                |
| `MAINTENANCE` | Maintenance | No                |

---

## Scope Validation

Counter assignments enforce the full scope chain:

```
User
 → has active role assignment
 → role assignment scoped to the correct organization
 → role assignment scoped to the correct restaurant
 → role assignment scoped to the branch that owns this counter
```

A cashier assigned to Branch A **cannot** be assigned to a counter in Branch B unless they also hold a valid Branch B assignment.

---

## Permissions

| Permission Code                  | Description                     |
|----------------------------------|---------------------------------|
| `counter.view`                   | View counters                   |
| `counter.create`                 | Create new counters             |
| `counter.update`                 | Edit counter details            |
| `counter.disable`                | Disable (set INACTIVE) a counter|
| `counter.assign`                 | Assign a user to a counter      |
| `counter.unassign`               | Deactivate an assignment        |
| `counter.session.view`           | View sessions                   |
| `counter.session.open`           | Open a session                  |
| `counter.session.close`          | Close a session                 |
| `counter.session.force_close`    | Force-close (manager only)      |
| `counter.reconcile`              | Review reconciliation           |
| `shift.view`                     | View shifts                     |
| `shift.manage`                   | Create/edit shifts              |

### Default Role Assignments

| Role               | Counter Permissions                                                          |
|--------------------|------------------------------------------------------------------------------|
| Company Head       | All counter permissions                                                      |
| Central Admin      | All counter permissions                                                      |
| Restaurant Owner   | All counter permissions                                                      |
| Restaurant Manager | All except `counter.disable` (cannot permanently disable hardware)           |
| Cashier            | `counter.view`, `counter.session.view`, `counter.session.open`, `counter.session.close` |

---

## Scoped Querysets

Counters are **never** exposed globally to non-superusers. The `counters.access` module scopes all querysets:

| Role / Scope        | Visible Counters                          |
|---------------------|-------------------------------------------|
| Superuser / Staff   | All counters                              |
| Company Head        | All counters in their organization(s)     |
| Central Admin       | All counters in their organization(s)     |
| Restaurant Owner    | All counters in their restaurant(s)       |
| Manager             | Counters in their assigned branch(es)     |
| Cashier             | Counters in their assigned branch(es)     |

Requesting a counter UUID that is outside the user's scope returns **404 Not Found** — never 403. This prevents UUID enumeration (IDOR protection).

---

## Files

```
backend/counters/
├── __init__.py
├── apps.py
├── models.py          # Counter, CounterAssignment, Shift, CounterSession
├── admin.py
├── access.py          # Scoped querysets (mirrors accounts/access.py pattern)
├── permissions.py     # DRF permission classes
├── serializers.py     # Read/write serializers + action serializers
├── services.py        # Business logic (open/close/assign/disable)
├── views.py           # All API views
├── urls.py            # URL patterns
├── tests.py           # Comprehensive test suite
└── migrations/
    └── 0001_initial.py

frontend/src/
├── types/index.ts         # Counter, Session, Assignment, Shift types added
├── services/counters.ts   # API calls
├── hooks/useCounters.ts   # TanStack Query hooks
├── utils/money.ts         # formatCurrency, formatDifference
├── components/counter/
│   ├── CounterStatusBadge.tsx
│   ├── CounterForm.tsx
│   ├── OpenSessionForm.tsx
│   ├── CloseSessionForm.tsx
│   ├── ForceCloseForm.tsx
│   └── AssignCounterForm.tsx
└── pages/counters/
    ├── CountersListPage.tsx
    ├── CounterDetailPage.tsx
    ├── CounterSessionsPage.tsx
    └── CounterDashboardPage.tsx
```
