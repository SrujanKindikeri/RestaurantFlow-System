# RestaurantFlow — Order Types

Phase 6

---

## The three order types

Phase 6 supports three order types. A fourth type (DELIVERY) is reserved for a future phase.

### DINE_IN

A customer sits at a physical table inside the restaurant.

**Required fields:**
- `table` — must be an ACTIVE DiningTable belonging to the order's branch
- `table_session` — must be an OPEN TableSession for that table

**Prohibited fields:**
- `counter` must be `null`
- `counter_session` must be `null`

**Flow:**
```
Waiter selects branch
  → Selects available table
  → Opens TableSession (guest_count)
  → Creates DINE_IN DRAFT order
  → Adds items
  → Confirms order
  → (Future: Kitchen processes → Bill generated → Payment taken)
  → TableSession closed
```

**Sequence prefix:** `D-` (branch-scoped daily sequence)

---

### COUNTER

A customer orders directly at a POS billing counter — typically quick-service, dine-in counter seating, or in-person pickup.

**Required fields:**
- `counter` — must be an ACTIVE Counter belonging to the order's branch
- `counter_session` — must be an OPEN CounterSession on that counter

**Prohibited fields:**
- `table` must be `null`
- `table_session` must be `null`

**Flow:**
```
Cashier opens counter session
  → Creates COUNTER DRAFT order
  → Adds items
  → Confirms order
  → (Future: Kitchen processes → Bill generated → Payment taken)
```

**Sequence prefix:** counter code (e.g. `C01-`, `C02-`) — counter-scoped daily sequence

---

### TAKEAWAY

A customer orders food for collection (not dine-in). Operationally similar to COUNTER but distinct for reporting and future workflow purposes.

**Required fields:**
- `counter` — must be an ACTIVE Counter
- `counter_session` — must be OPEN

**Prohibited fields:**
- `table` must be `null`
- `table_session` must be `null`

**Why keep TAKEAWAY and COUNTER separate?**

Future reporting needs to distinguish walk-in counter sales from takeaway/collection orders. Merging them into one type would require a reclassification migration later. The distinction is cheap now and valuable later.

**Sequence prefix:** counter code (same as COUNTER)

---

## Type-field matrix

| Field | DINE_IN | COUNTER | TAKEAWAY |
|---|---|---|---|
| `table` | Required | Null | Null |
| `table_session` | Required | Null | Null |
| `counter` | Null | Required | Required |
| `counter_session` | Null | Required | Required |
| `guest_count` | Recommended | Optional | Optional |

---

## Backend enforcement

The backend validates the type-field matrix on every order create request. The frontend sending `{"order_type": "DINE_IN", "counter": "<uuid>"}` will receive a 400 validation error — not a silent accept.

Cross-branch integrity is also enforced:

- `table.branch` must equal `order.branch`
- `counter.branch` must equal `order.branch`
- `counter_session.counter.branch` must equal `order.branch`
- `table_session.table.branch` must equal `order.branch`
- Menu items must belong to the same restaurant as the branch

---

## Permissions by type

| Permission | Controls |
|---|---|
| `order.create.dine_in` | DINE_IN order creation |
| `order.create.counter` | COUNTER order creation |
| `order.create.takeaway` | TAKEAWAY order creation |

A Cashier typically holds `order.create.counter` and `order.create.takeaway`.
A Waiter typically holds `order.create.dine_in`.
A Manager holds all three.

These are permissions on the `Permission` model — they are never hard-coded role checks.

---

## Future: DELIVERY

`DELIVERY` is intentionally excluded from Phase 6. It will require additional fields (delivery address, rider assignment, delivery tracking) that are out of scope here. The `OrderType` TextChoices enum is ready to accept `DELIVERY = "DELIVERY"` when that phase arrives.
