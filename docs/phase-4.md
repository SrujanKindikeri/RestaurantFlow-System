# Phase 4 — Counters, Sessions & Cash Reconciliation

## Summary

Phase 4 adds the physical billing-counter infrastructure to RestaurantFlow. It builds directly on the Organization → Restaurant → Branch hierarchy from Phase 2 and the access-control system from Phase 3.

**What was built:**

- Physical POS counter model with status management
- Counter assignments (cashier ↔ counter links with history)
- Shift schedule configuration
- Counter sessions with full cash lifecycle (open → close → reconcile)
- Force-close by managers
- Full permission-scoped API
- Complete frontend with dashboard, list, detail, session, and form UIs

---

## Architecture After Phase 4

```
Organization
    │
    ├── Users
    │     └── Roles
    │           └── Permissions
    │
    └── Restaurants
          │
          └── Branches
                │
                ├── Shifts (schedule config)
                │
                └── Counters
                      │
                      ├── CounterAssignments  (cashier ↔ counter, with history)
                      │
                      └── CounterSessions
                              │
                              └── Cash Reconciliation
                                  (opening_cash → actual_cash → difference)
```

---

## What Was NOT Built (Future Phases)

Phase 4 explicitly excludes:

| Feature              | Planned Phase |
|----------------------|---------------|
| Menu / Categories    | Phase 5       |
| Orders               | Phase 6       |
| Kitchen Display      | Phase 6       |
| Bills                | Phase 6       |
| Payments             | Phase 6       |
| Cash adjustments     | Phase 6       |
| Inventory            | Phase 7+      |
| Accounting / Reports | Phase 7+      |
| Analytics            | Phase 7+      |

The `expected_cash` field in `CounterSession` is intentionally designed to be updated by future transaction aggregations (Phase 6+) without any schema migration.

---

## New Django App

```
backend/counters/
├── __init__.py
├── apps.py
├── admin.py
├── models.py          Counter, CounterAssignment, Shift, CounterSession
├── access.py          get_accessible_counters/sessions/assignments/shifts
├── permissions.py     HasCounterAccess, HasCounterSessionAccess
├── serializers.py     CounterSerializer, CounterDetailSerializer,
│                      CounterAssignmentSerializer, CounterSessionSerializer,
│                      ShiftSerializer, OpenSessionSerializer,
│                      CloseSessionSerializer, ForceCloseSessionSerializer
├── services.py        open_session, close_session, force_close_session,
│                      assign_counter, deactivate_assignment,
│                      disable_counter, reactivate_counter
├── views.py           CounterListCreateView, CounterDetailView,
│                      CounterDisableView, CounterReactivateView,
│                      CounterOpenSessionView, CounterSessionListView,
│                      CounterSessionDetailView, CounterSessionCloseView,
│                      CounterSessionForceCloseView,
│                      CounterAssignmentListCreateView,
│                      CounterAssignmentDetailView,
│                      CounterAssignmentDeactivateView,
│                      ShiftListCreateView, ShiftDetailView,
│                      CounterDashboardView
├── urls.py
├── tests.py           ~35 tests covering all acceptance criteria
└── migrations/
    └── 0001_initial.py
```

---

## New API Endpoints

### Counters

| Method | URL                                    | Description              | Permission       |
|--------|----------------------------------------|--------------------------|------------------|
| GET    | `/api/counters/`                       | List counters (scoped)   | counter.view     |
| POST   | `/api/counters/`                       | Create counter           | counter.create   |
| GET    | `/api/counters/{id}/`                  | Retrieve detail          | counter.view     |
| PATCH  | `/api/counters/{id}/`                  | Update                   | counter.update   |
| POST   | `/api/counters/{id}/disable/`          | Set INACTIVE             | counter.disable  |
| POST   | `/api/counters/{id}/reactivate/`       | Set ACTIVE               | counter.update   |
| POST   | `/api/counters/{id}/sessions/open/`    | Open session             | counter.session.open |

### Sessions

| Method | URL                                        | Description        | Permission                   |
|--------|--------------------------------------------|--------------------|------------------------------|
| GET    | `/api/counter-sessions/`                   | List sessions      | counter.session.view         |
| GET    | `/api/counter-sessions/{id}/`              | Retrieve           | counter.session.view         |
| POST   | `/api/counter-sessions/{id}/close/`        | Close session      | counter.session.close        |
| POST   | `/api/counter-sessions/{id}/force-close/`  | Force close        | counter.session.force_close  |

### Assignments

| Method | URL                                           | Description       | Permission         |
|--------|-----------------------------------------------|-------------------|--------------------|
| GET    | `/api/counter-assignments/`                   | List              | counter.view       |
| POST   | `/api/counter-assignments/`                   | Create            | counter.assign     |
| GET    | `/api/counter-assignments/{id}/`              | Retrieve          | counter.view       |
| PATCH  | `/api/counter-assignments/{id}/`              | Update            | counter.assign     |
| POST   | `/api/counter-assignments/{id}/deactivate/`   | Deactivate        | counter.unassign   |

### Shifts

| Method | URL                | Description | Permission    |
|--------|--------------------|-------------|---------------|
| GET    | `/api/shifts/`     | List        | shift.view    |
| POST   | `/api/shifts/`     | Create      | shift.manage  |
| GET    | `/api/shifts/{id}/`| Retrieve    | shift.view    |
| PATCH  | `/api/shifts/{id}/`| Update      | shift.manage  |

### Dashboard

| Method | URL                           | Description                  | Permission    |
|--------|-------------------------------|------------------------------|---------------|
| GET    | `/api/counter-dashboard/`     | Branch counter status overview| counter.view |

Optional filter: `?branch={uuid}`

---

## New Frontend Pages

| Route                 | Page                     | Description                          |
|-----------------------|--------------------------|--------------------------------------|
| `/counter-dashboard`  | CounterDashboardPage     | Live card grid of all counters       |
| `/counters`           | CountersListPage         | Table list with filters and actions  |
| `/counters/:id`       | CounterDetailPage        | Full detail with session + assignments |
| `/counter-sessions`   | CounterSessionsPage      | Tabular session list with close/force actions |

---

## New Frontend Components

| Component              | Purpose                                           |
|------------------------|---------------------------------------------------|
| `CounterStatusBadge`   | ACTIVE / INACTIVE / MAINTENANCE coloured badge    |
| `SessionStatusBadge`   | OPEN / CLOSED / FORCE_CLOSED coloured badge       |
| `CounterStatusDot`     | Small inline status dot for table rows            |
| `CounterForm`          | Create / edit counter form                        |
| `OpenSessionForm`      | Opening cash entry with shift selector            |
| `CloseSessionForm`     | Actual cash entry with live difference preview    |
| `ForceCloseForm`       | Force-close form with warning banner              |
| `AssignCounterForm`    | Assign cashier to counter                         |

---

## Key Security Decisions

### IDOR Protection
All views use scoped querysets. A request for a counter UUID that exists but is outside the user's scope returns **404 Not Found**, not 403. This prevents UUID enumeration.

### No Client-Submitted Differences
`cash_difference` is always calculated server-side: `actual_cash − expected_cash`. Any client-submitted value is ignored.

### Concurrency Protection
`open_session` uses `select_for_update()` inside `transaction.atomic()` plus a database-level partial unique constraint. Two simultaneous open-session requests will never create two OPEN sessions.

### Privilege Escalation
`force_close` requires `counter.session.force_close`. Cashiers cannot force-close their own session or another cashier's session. This is enforced in the service layer, not only in the frontend.

### Money as Decimal
All monetary fields use `DecimalField(max_digits=12, decimal_places=2)`. No `float` anywhere in the financial path.

---

## Running Phase 4 After Pulling

### Prerequisites
- Docker Desktop running with WSL2
- Existing Phase 1–3 database intact

### Steps

```bash
# Start services
docker compose up -d

# Apply Phase 4 migration
docker compose exec backend python manage.py migrate

# Seed counter permissions into existing roles
docker compose exec backend python manage.py seed_demo_data

# Run test suite
docker compose exec backend python manage.py test counters

# Verify health endpoint still works
curl http://localhost:8000/api/health/
# → {"status": "ok", "service": "RestaurantFlow API"}

# Frontend (development)
cd frontend && npm run dev
```

---

## Test Coverage

Tests in `backend/counters/tests.py` cover:

### Counter model
- Code uniqueness within branch enforced
- Same code in different branches allowed
- `is_active` syncs with `status`
- `can_open_session` property

### Counter Assignment
- Assign authorized user
- Cross-branch assignment rejected
- Unauthorized user cannot assign
- Historical assignments preserved on deactivation

### Counter Session
- Open session success
- Negative opening cash rejected
- Cannot open on inactive/maintenance counter
- Cannot open second session (service + DB constraint)
- Close with correct difference calculation (negative, positive, zero)
- Cannot close already-closed session
- Negative actual cash rejected
- Force close requires `force_close` permission
- Force close by manager succeeds
- Force close without actual_cash allowed
- New session can open after closing

### Concurrency
- DB partial unique constraint prevents two OPEN sessions

### API Security (APITestCase)
- Cashier sees only their branch counters
- Company Head sees all counters
- Cashier gets 404 (not 403) for other-branch counter
- Unauthenticated request returns 401
- API open session, duplicate rejected
- API close with correct difference
- Force close by cashier → 403
- Force close by manager → 200
- Negative cash → 400
- Counter create by cashier → 403
- Dashboard returns correct structure
- Health endpoint still works (regression)

---

## Future Operational Flow (Phase 6+)

```
Counter Session (Phase 4)
      ↓
Order Created (Phase 6)
      ↓
Kitchen Display (Phase 6)
      ↓
Bill Generated (Phase 6)
      ↓
Payment Received (Phase 6)
      ↓
expected_cash updated (Phase 6)
      ↓
Close Session → Cash Reconciliation (Phase 4 + Phase 6)
```
