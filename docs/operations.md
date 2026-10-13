# RestaurantFlow — Phase 19: Advanced POS & Restaurant Operations

## Overview

Phase 19 adds the `operations` Django app — the operational layer that sits between the POS interface and the core domain models (Order, Bill, Payment, KitchenOrder). It provides fast POS workflows, table management, order modifications, bill splitting, shift handover, and receipt printing without duplicating any existing domain model.

---

## Architecture

```
Company
 └── Restaurant
      └── Branch
           ├── Counter ──────────────────── CounterSession (Phase 4)
           │                                     └── POSSession (Phase 19)
           │
           ├── DiningTable ──────────────── TableSession (Phase 6)
           │    └── TableOperationalStatus (Phase 19, derived runtime state)
           │    └── TableFloorPlan (Phase 19, layout metadata)
           │
           └── OperationalShift (Phase 19, shift-level grouping)
                └── ShiftHandoverNote
```

### Key separation of concerns

| Domain model | Owned by | Phase 19 extends with |
|---|---|---|
| `Order` | `orders` | `ON_HOLD` status, `OrderFulfillmentStatus`, `OrderChangeRequest`, `OrderItemModifier` |
| `DiningTable` | `orders` | `TableOperationalStatus` (OneToOne), `TableFloorPlan` (OneToOne) |
| `Bill` | `billing` | `BillSplit`, `BillSplitItem` |
| `Payment` | `payments` | `ReceiptPrintLog` |
| `CounterSession` | `counters` | `POSSession` (child session) |
| `KitchenOrder.priority` | `kitchen` | Exposed via `set_order_priority` service |

Phase 19 **never** re-implements any of these models — it only extends them with separate models that reference them via FK/OneToOne.

---

## POS Session Workflow

### Hierarchy

```
Counter
 └── CounterSession  (cash session — Phase 4)
      └── POSSession  (POS app session — Phase 19)
```

A `POSSession` belongs to an open `CounterSession`. One shift can have multiple POSSessions (break resumptions, shift changes).

### Lifecycle

```
[Start] → ACTIVE → [Pause] → PAUSED → [Resume] → ACTIVE → [End] → ENDED
```

### Security invariants

- Backend verifies `counter.branch == user's authorized branch` — never trusts `counter_id` from frontend.
- `device_identifier` is metadata only — never used for authorization.
- Only ONE `ACTIVE` POSSession per `(counter, user)` enforced by partial unique constraint.
- Every state change creates an `OperationsAuditLog` entry.

### API

| Method | Endpoint | Permission |
|---|---|---|
| GET | `/api/operations/pos/session/` | `pos.access` |
| POST | `/api/operations/pos/session/start/` | `pos.session.start` |
| POST | `/api/operations/pos/session/{id}/pause/` | `pos.session.pause` |
| POST | `/api/operations/pos/session/{id}/resume/` | `pos.session.start` |
| POST | `/api/operations/pos/session/{id}/end/` | `pos.session.end` |
| GET | `/api/operations/pos/recovery/?counter_id=` | `pos.access` |

---

## Counter Integration

```
Counter (Phase 4)
 └── CounterSession  OPEN
      └── POSSession  ACTIVE  ←  required to use POS
```

Rules enforced in `pos_services.start_pos_session()`:
1. `counter.branch` must match the user's authorized branch.
2. `Counter.status` must be `ACTIVE`.
3. An `OPEN` `CounterSession` must exist.
4. No duplicate `ACTIVE` session for the same `(counter, user)`.

---

## Barcode / SKU Lookup

`POST /api/operations/pos/scan/`  
Input: `{ "barcode_or_sku": "SKU-PIZZA" }`

The backend resolves `MenuItem` by `sku` field, checks branch availability, and returns the authoritative price. **The frontend never submits a price** — it only submits the item ID and quantity.

---

## Order Hold / Resume

`Order.status` is extended with `ON_HOLD` in Phase 19.

```
DRAFT → ON_HOLD → DRAFT → CONFIRMED
```

Rules:
- Only `DRAFT` orders can be held.
- `ON_HOLD` orders can be resumed to `DRAFT`.
- `CONFIRMED` orders cannot be held.
- All items, customer, table, counter, waiter, and notes are preserved.
- Audit log: `ORDER_HELD`, `ORDER_RESUMED`.

---

## Order Editing

### DRAFT orders
Editable directly through the existing `OrderService`. No change request needed.

### CONFIRMED orders (in kitchen)
Require the `OrderChangeRequest` workflow:

```
Cashier submits OrderChangeRequest (PENDING)
         ↓
Manager approves (APPROVED) → service applies change
         ↓  or
Manager rejects (REJECTED)
```

Change types: `ADD_ITEM`, `REMOVE_ITEM`, `CHANGE_QUANTITY`, `CHANGE_NOTE`, `CHANGE_TABLE`, `CHANGE_WAITER`, `CHANGE_CUSTOMER`

Security: approver ≠ requester (enforced in service layer).

---

## Item Modifiers

### Model chain

```
MenuModifierGroup  (restaurant-scoped, e.g. "Spice Level")
 └── MenuModifierOption  (e.g. "Less Spicy", price_adjustment=0.00)

OrderItem
 └── OrderItemModifier  (applied modifier, price_adjustment copied from option)
```

### Price invariant

**Frontend never submits `price_adjustment`.** The backend always resolves it from `MenuModifierOption.price_adjustment`. If a free-text modifier is added without an option, `price_adjustment` defaults to `0.00`.

### Validation (`validate_modifier_selections`)
- `is_required=True` → at least `min_selections` options must be selected.
- `max_selections > 0` → cannot exceed that count (0 = unlimited).
- All selected option IDs must belong to the group and be `is_active=True`.

---

## Kitchen Integration

When an `Order` is confirmed:
1. Existing Phase 7 `KitchenService` creates `KitchenOrder`.
2. Phase 19 `OrderFulfillmentStatus` is created (signal-driven): `CONFIRMED`.
3. When kitchen marks `READY`, fulfillment updates to `READY` and waiter notification is sent via Phase 16 Notification Center.
4. Waiter marks `SERVED` via `mark_order_served()`.

```
OrderFulfillmentStatus:
CONFIRMED → PREPARING → READY → SERVED
                              ↘ CANCELLED
```

Kitchen remains authoritative for `KitchenOrder.status`. `OrderFulfillmentStatus` is the waiter-facing serving state.

---

## Order Priority

`KitchenOrder.priority` already exists (`NORMAL`, `HIGH`, `URGENT`).

Phase 19 exposes this via `POST /api/operations/orders/{id}/priority/`.

- `NORMAL` / `HIGH` → requires `pos.order.priority`
- `URGENT` → additionally requires `pos.order.priority.urgent`

Every priority change is audited with `ORDER_PRIORITY_CHANGED`.

---

## Table Management

### Table status separation

| Model | Purpose | Values |
|---|---|---|
| `DiningTable.status` | Configuration — can this table be used? | `ACTIVE`, `INACTIVE` |
| `TableOperationalStatus.status` | Runtime — what is happening at this table? | `AVAILABLE`, `OCCUPIED`, `RESERVED`, `BILL_PENDING`, `CLEANING`, `OUT_OF_SERVICE` |

`TableOperationalStatus` is created automatically by a signal when a `DiningTable` is created.

### Table Transfer

```
Table A (OCCUPIED)           Table B (AVAILABLE)
     Order ──transfer──────→      Order (moved)
```

`complete_table_transfer()` uses `select_for_update()` on both tables. If Table B becomes occupied between request and completion, the transfer is rejected.

### Table Merge

Combines multiple tables for a large group. Source tables and destination table are tracked in `TableMerge`. Orders continue referencing their original table for historical accuracy.

### Floor Plan (presentation metadata)

`TableFloorPlan` stores `position_x`, `position_y`, `width`, `height`, `rotation`, `shape`. This is purely for frontend floor-plan rendering — never used for authorization.

---

## Order Merging

Combines items from multiple open orders into one destination order. Source orders are cancelled after merge.

Rules:
- Cannot merge `CANCELLED` or already-billed orders.
- All orders must belong to the same branch.
- Approved via `OrderMergeRequest` workflow.
- Audit: `ORDER_MERGED`.

---

## Bill Splitting

`BillSplit` allocates portions of a finalized `Bill` for separate payment. The original `Bill` remains the financial authority — it is never mutated.

### Split types

| Type | Description |
|---|---|
| `EQUAL` | Grand total divided equally into N parts |
| `GUEST` | Same as EQUAL, labeled per guest |
| `ITEM` | Each split contains specific bill items |
| `QUANTITY` | Splits contain fractional quantities of bill items |

### Concurrency

`create_bill_split()` uses `select_for_update()` on the `Bill`. If two cashiers attempt to split the same bill simultaneously, only one succeeds.

### Lifecycle

```
DRAFT → FINALIZED → (payment taken against original Bill referencing split)
     ↘ CANCELLED
```

### Validation

- Sum of split amounts must equal `bill.grand_total` (within 1 cent rounding tolerance).
- For `ITEM`/`QUANTITY`: per-item split quantities must not exceed `BillItem.quantity`.
- Cannot create new splits if `DRAFT` or `FINALIZED` splits already exist.

---

## Receipt Printing

### `ReceiptPrintLog`

Every print and reprint creates an immutable `ReceiptPrintLog`. Records cannot be edited (`save()` guard raises `ValueError`).

Print types: `ORIGINAL`, `REPRINT`, `DUPLICATE`, `KITCHEN`

Reprint and Duplicate require a `reason`. Every event is audited.

### Receipt data

`build_receipt_data(bill)` assembles the receipt from authoritative DB records:
- Item names and prices from `BillItem` **snapshots** (never live menu prices)
- Tax breakdown from `bill.tax_breakdown`
- Payment details from `Payment` records
- Branch, restaurant, counter info from their respective models

**The frontend must not construct receipt totals from its own state.**

### Kitchen ticket

`build_kitchen_ticket_data(kitchen_order)` contains order, items, modifiers, and notes. It explicitly excludes payment details, customer PII, and accounting data.

---

## Waiter Assignment

`Order.assigned_waiter` already exists (Phase 6). Phase 19 adds the operational flow:

- `assign_waiter()` — validates waiter belongs to same branch/restaurant
- `POST /api/operations/orders/{id}/waiter/` — requires `order.waiter.assign`
- Audit: `WAITER_ASSIGNED`

---

## Shift Handover

`OperationalShift` is the branch-level shift record. It is **not** a replacement for `CounterSession` — one shift can span multiple counter sessions.

```
OperationalShift (OPEN)
 ├── CounterSession A (Counter 1)
 ├── CounterSession B (Counter 2)
 └── ShiftHandoverNote[]
```

### Handover notes

Types: `GENERAL`, `KITCHEN`, `INVENTORY`, `CUSTOMER`, `PAYMENT`, `EQUIPMENT`, `STAFF`, `OTHER`  
Priority: `LOW`, `NORMAL`, `HIGH`

### Shift summary

`get_shift_summary(shift)` aggregates from existing services — it does **not** recalculate accounting. It reads from `Order`, `Bill`, `Payment`, `PaymentRefund`, and `KitchenOrder` querysets scoped to the shift's branch and time range.

---

## Concurrency Protection

All critical operations use `transaction.atomic()` + `select_for_update()`:

| Operation | Lock target |
|---|---|
| Start POS session | Counter (prevents duplicate ACTIVE sessions) |
| Table transfer | Source table + destination table |
| Bill split create | Bill |
| Order merge | All source orders |
| Shift close | Shift record |
| Bill split finalize | BillSplit |

---

## Idempotency

Phase 19 reuses existing idempotency infrastructure:
- `Payment.idempotency_key` for payments after splits
- `OrderMergeRequest` and `TableTransfer` models prevent re-processing via status checks
- Receipt prints are not idempotent by design — each print is a new audit record

---

## POS Session Recovery

`GET /api/operations/pos/recovery/?counter_id=`

Returns safe state for browser refresh:
- Active/paused POS session info
- Draft order IDs and order numbers (not financial data)
- Held order IDs
- Occupied table numbers

**Never included in recovery payload:** card data, payment credentials, authoritative financial totals, tokens.

---

## Offline-Aware Design

The POS frontend displays a connectivity status badge: `ONLINE`, `DEGRADED`, `OFFLINE`.

Rules:
- `OFFLINE` → order confirmation and payment are blocked with a visible warning.
- Cart state (item selection, quantity) may be stored in browser memory only.
- `localStorage` may only hold: selected category, selected customer ID, selected table ID, UI preferences.
- `localStorage` must NEVER hold: price, tax, payment status, bill total, payment credentials.

---

## Permissions

| Code | Description |
|---|---|
| `pos.access` | Access POS interface |
| `pos.session.start` | Start a POS session |
| `pos.session.pause` | Pause a POS session |
| `pos.session.end` | End a POS session |
| `pos.order.hold` | Hold a draft order |
| `pos.order.resume` | Resume a held order |
| `pos.order.priority` | Change order priority (NORMAL/HIGH) |
| `pos.order.priority.urgent` | Set URGENT priority (restricted) |
| `order.modifier.manage` | Add/remove item modifiers |
| `order.change.request` | Request changes to confirmed orders |
| `order.change.approve` | Approve/reject order change requests |
| `order.waiter.assign` | Assign/reassign waiter |
| `order.merge` | Request order merge |
| `table.view` | View tables and operational status |
| `table.manage` | Set table operational status |
| `table.transfer` | Request/complete table transfer |
| `table.merge` | Request table merge |
| `bill.split` | Create/finalize bill splits |
| `receipt.print` | Print receipts |
| `receipt.reprint` | Reprint receipts (requires reason + audit) |
| `shift.view` | View shifts and handover |
| `shift.create` | Open a new operational shift |
| `shift.close` | Close an operational shift |
| `operations.dashboard.view` | View operations dashboard |
| `operations.export` | Export operational reports |

### Role defaults (never hard-coded — assigned via Permission model)

| Role | Key permissions |
|---|---|
| Restaurant Manager | All operations permissions |
| Cashier | POS, orders, billing, receipt printing, shifts |
| Waiter | table.view, order.waiter.assign, modifier.manage |
| Kitchen Staff | KDS only (Phase 7) |
| Restaurant Owner | Full restaurant operations |

---

## Security

All operations endpoints enforce:
1. Authentication (JWT — Phase 3)
2. Permission check via `has_perm_code()`
3. Branch scope via `get_accessible_branches(user)` from `accounts.access`
4. Object-level scope: querysets filtered to accessible branches before `.get(pk=…)` — prevents IDOR

**Never trusted from frontend:** `counter_id`, `branch_id`, `table_id`, `order_id`, `bill_id`, `customer_id`, `price`, `price_adjustment`

---

## Frontend Routes

| Route | Component | Permission gate |
|---|---|---|
| `/operations` | `OperationsDashboard` | `operations.dashboard.view` |
| `/operations/pos` | `POSPage` | `pos.access` |
| `/operations/tables` | `TablesPage` | `table.view` |
| `/operations/waiter` | `WaiterPage` | `table.view` |
| `/operations/cashier` | `CashierPage` | `pos.access` |
| `/operations/shifts` | `ShiftsPage` | `shift.view` |
| `/operations/shifts/:id` | `ShiftDetailPage` | `shift.handover.view` |

The POS page (`/operations/pos`) is a desktop-first full-width layout. Waiter page is mobile/tablet optimized. Keyboard shortcuts available in POS: `F1`=Search, `F3`=Hold, `F5`=New Order, `Esc`=Cancel modal.

---

## Notifications Integration (Phase 16)

Phase 19 reuses the Phase 16 Notification Center. Events emitted:

| Event | Recipients |
|---|---|
| `order.ready` (KitchenOrder→READY) | Assigned waiter, manager |
| `bill.pending` | Cashier on duty |
| `table.available` | Floor manager |
| `shift.handover` | Next shift manager |

No new notification engine is created.

---

## Central Control Integration (Phase 15)

Operational alerts raised via existing `CentralAlert`:

| Alert type | Trigger |
|---|---|
| `KITCHEN_BACKLOG` | Kitchen queue exceeds threshold |
| `TABLE_STUCK` | Table occupied with no activity for >N minutes |
| `BILL_PENDING_TOO_LONG` | Finalized bill unpaid for >N minutes |
| `COUNTER_SESSION_OPEN_TOO_LONG` | CounterSession open beyond configured hours |
| `UNSERVED_READY_ORDER` | KitchenOrder READY with no served transition for >N minutes |
| `POS_DEVICE_OFFLINE` | POSSession last_activity_at exceeds threshold |

---

## Reporting Integration (Phase 14)

The `get_shift_summary()` and `get_operations_dashboard_data()` services produce data that Phase 14 reporting can consume:

- Table turnover rate
- Average order preparation time
- Order completion time
- Bill waiting time
- Counter performance
- Waiter performance
- Shift performance

---

## Migrations

`backend/operations/migrations/0001_initial.py`

Creates all 14 Phase 19 models. Depends on:
- `billing.0002_reporting_indexes`
- `counters.0001_initial`
- `menu.0001_initial`
- `orders.0001_initial`
- `organizations.0001_initial`
- `payments.0001_initial`

Run: `python manage.py migrate operations`

---

## Running Tests

```bash
cd backend
python manage.py test operations --verbosity=2
```

Test modules:
- `operations.tests.test_pos_session` — POS session lifecycle + API
- `operations.tests.test_order_ops` — Hold/resume, priority, waiter, change requests, modifiers
- `operations.tests.test_tables` — Operational status, transfer, merge
- `operations.tests.test_bill_split` — Equal/item splits, finalize, cancel, concurrency
- `operations.tests.test_shifts` — Shift open/close, handover notes, summary
- `operations.tests.test_receipts` — Print log, immutability, receipt data builder
- `operations.tests.test_security` — Cross-branch isolation, auth, permissions, IDOR
- `operations.tests.test_modifiers` — Group/option CRUD, validation, API
- `operations.tests.test_order_merge` — Merge workflow, incompatible orders, audit

---

## End-to-End Scenario

```
Manager opens OperationalShift (MORNING)
 └── Cashier opens CounterSession (Counter C01)
      └── Cashier starts POSSession
           └── Customer arrives → Cashier selects Table T05
                └── Creates Order (DINE_IN)
                     └── Adds items: Biryani ×2, Lassi ×1
                          └── Adds modifier: "Spice: Extra Spicy"
                               └── Sends to Kitchen (Order → CONFIRMED)
                                    └── KitchenOrder created (NEW → PREPARING → READY)
                                         └── Waiter notified (Phase 16)
                                              └── Waiter marks SERVED
                                                   └── Cashier requests Bill
                                                        └── Billing calculates (Phase 8)
                                                             └── Promotion applied (Phase 18)
                                                                  └── Customer requests split (2 guests)
                                                                       └── BillSplit ×2 created
                                                                            └── Each guest pays separately
                                                                                 └── Payment recorded (Phase 9)
                                                                                      └── Receipt printed (ReceiptPrintLog)
                                                                                           └── Loyalty points earned (Phase 17)
                                                                                                └── Table closed → AVAILABLE
                                                                                                     └── Manager closes shift
                                                                                                          └── ShiftHandoverNote added
```
