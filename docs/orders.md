# RestaurantFlow — Orders

Phase 6

---

## Overview

An `Order` is the central transaction record that connects a Branch, optional Table/Counter, menu items, and a user actor.  Phase 6 establishes the order foundation that Phase 7 (Kitchen), Phase 8 (Billing), and Phase 9 (Inventory) will consume.

```
Branch
  └── Order  (DINE_IN / TAKEAWAY / COUNTER)
          └── OrderItem  (price + tax snapshot)
```

---

## Order Model

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | Immutable |
| `branch` | FK → Branch | PROTECT |
| `order_number` | CharField(50) | Human-readable, immutable after creation |
| `order_type` | DINE_IN / TAKEAWAY / COUNTER | |
| `table` | FK → DiningTable (nullable) | DINE_IN only |
| `table_session` | FK → TableSession (nullable) | DINE_IN only |
| `counter` | FK → Counter (nullable) | COUNTER / TAKEAWAY |
| `counter_session` | FK → CounterSession (nullable) | COUNTER / TAKEAWAY |
| `created_by` | FK → User | PROTECT |
| `assigned_waiter` | FK → User (nullable) | PROTECT |
| `guest_count` | PositiveInt (nullable) | Primarily for DINE_IN |
| `status` | DRAFT / CONFIRMED / CANCELLED | |
| `notes` | TextField | |
| `confirmed_at` | DateTimeField (nullable) | |
| `cancelled_at` | DateTimeField (nullable) | |
| `cancelled_by` | FK → User (nullable) | |
| `cancellation_reason` | TextField | |
| `created_at / updated_at` | DateTimeField | Auto |

### Status lifecycle (Phase 6)

```
DRAFT ──→ CONFIRMED ──→ (Phase 7: ACCEPTED → PREPARING → READY → SERVED)
  │
  └──────────────────→ CANCELLED
```

Orders are **never physically deleted**. Use `status = CANCELLED`.

---

## OrderItem Model

Each item records a **snapshot** of the menu item's price and tax at the moment of ordering. This snapshot is immutable — future menu price changes cannot alter existing orders.

| Field | Type | Notes |
|---|---|---|
| `id` | UUID PK | Immutable |
| `order` | FK → Order | CASCADE (items are subordinate) |
| `menu_item` | FK → MenuItem | PROTECT |
| `item_name_snapshot` | CharField(200) | Immutable after creation |
| `sku_snapshot` | CharField(100) | Immutable |
| `unit_price_snapshot` | Decimal(12,2) | Immutable — branch price at order time |
| `tax_rate_snapshot` | Decimal(6,3) | Immutable — e.g. 5.000 = 5% |
| `tax_code_snapshot` | CharField(50) | Immutable — e.g. GST_STANDARD |
| `quantity` | Decimal(7,3) | Mutable on DRAFT orders only |
| `notes` | TextField | Mutable on DRAFT |

### Why snapshots?

If Chicken Biryani costs ₹250 today and the price changes to ₹280 tomorrow, the historical order must still show ₹250. The billing phase reads these snapshots directly — never the live menu price.

---

## OrderSequence

A concurrency-safe sequence counter for human-readable order numbers.

| Field | Type | Notes |
|---|---|---|
| `scope_type` | counter / branch | Scope of sequence |
| `scope_id` | CharField(50) | UUID of counter or branch |
| `date_key` | CharField(8) | YYYYMMDD business date |
| `last_sequence` | PositiveInt | Atomically incremented |

Order number formats:

| Type | Format | Example |
|---|---|---|
| DINE_IN | `D-{YYYYMMDD}-{seq:04d}` | `D-20261003-0042` |
| COUNTER | `{counter_code}-{YYYYMMDD}-{seq:04d}` | `C01-20261003-0007` |
| TAKEAWAY | `{counter_code}-{YYYYMMDD}-{seq:04d}` | `C02-20261003-0003` |

Sequences reset daily per scope. The internal UUID is the permanent, immutable identifier. The display order number is human-readable and also immutable, but is only used for display and search — never as a FK.

**Never use `MAX(order_number) + 1`** — this creates race conditions under concurrent load. The sequence service uses `select_for_update()`.

---

## Service Layer

All business logic lives in `orders/services.py`. Views only call services; they never contain business rules.

| Function | Description |
|---|---|
| `generate_order_number(branch, order_type, counter)` | Concurrency-safe number generation |
| `open_table_session(actor, table, guest_count)` | Open a table session with lock |
| `close_table_session(actor, session)` | Close session (blocks if active orders exist) |
| `create_order(actor, branch, order_type, ...)` | Validate + create DRAFT order |
| `add_order_item(actor, order, menu_item_id, quantity)` | Resolve price/tax + snapshot |
| `update_order_item(actor, item, quantity, notes)` | Mutate DRAFT item only |
| `remove_order_item(actor, item)` | Delete DRAFT item only |
| `confirm_order(actor, order)` | DRAFT → CONFIRMED with re-validation |
| `cancel_order(actor, order, reason)` | DRAFT/CONFIRMED → CANCELLED |
| `assign_waiter(actor, order, waiter)` | Assign waiter with scope check |

---

## API Endpoints

| Method | URL | Permission | Description |
|---|---|---|---|
| GET | `/api/orders/` | `order.view.branch` | List (scoped, filterable) |
| POST | `/api/orders/` | type-specific | Create order |
| GET | `/api/orders/{id}/` | `order.view.branch` | Detail with items |
| PATCH | `/api/orders/{id}/` | `order.update` | Update notes (DRAFT only) |
| POST | `/api/orders/{id}/confirm/` | `order.confirm` | Confirm DRAFT |
| POST | `/api/orders/{id}/cancel/` | `order.cancel` | Cancel |
| POST | `/api/orders/{id}/assign-waiter/` | `order.reassign_waiter` | Assign waiter |
| POST | `/api/orders/{id}/items/` | `order.item.add` | Add item |
| PATCH | `/api/order-items/{id}/` | `order.item.update` | Update item |
| DELETE | `/api/order-items/{id}/` | `order.item.remove` | Remove item |

### Query filters (orders list)

| Param | Example | Description |
|---|---|---|
| `branch` | `?branch=<uuid>` | Filter by branch |
| `order_type` | `?order_type=DINE_IN` | DINE_IN / COUNTER / TAKEAWAY |
| `status` | `?status=CONFIRMED` | DRAFT / CONFIRMED / CANCELLED |
| `table` | `?table=<uuid>` | Filter by table |
| `counter` | `?counter=<uuid>` | Filter by counter |
| `assigned_waiter` | `?assigned_waiter=<id>` | Filter by waiter |
| `created_by` | `?created_by=<id>` | Filter by creator |
| `date` | `?date=2026-10-03` | Filter by date (YYYY-MM-DD) |

---

## Permissions

| Code | Description |
|---|---|
| `order.view.own` | See own orders only |
| `order.view.branch` | See all branch orders |
| `order.create.dine_in` | Create DINE_IN orders |
| `order.create.counter` | Create COUNTER orders |
| `order.create.takeaway` | Create TAKEAWAY orders |
| `order.update` | Update DRAFT order notes |
| `order.confirm` | Confirm an order |
| `order.cancel` | Cancel DRAFT orders |
| `order.cancel.confirmed` | Cancel CONFIRMED orders (stronger) |
| `order.item.add` | Add items to DRAFT order |
| `order.item.update` | Update items on DRAFT order |
| `order.item.remove` | Remove items from DRAFT order |
| `order.reassign_waiter` | Change assigned waiter |

---

## Preview total

`Order.preview_total` is a convenience sum of `quantity × unit_price_snapshot` across all items. It is **not** the authoritative billing total — that belongs to Phase 8 (Billing), which will apply discounts, rounding, and payment logic.

---

## Future integration points

| Phase | Consumes from Order |
|---|---|
| Phase 7 — Kitchen | `Order.status = CONFIRMED`, `OrderItem.menu_item.preparation_time_minutes` |
| Phase 8 — Billing | All `OrderItem` snapshot fields; `Order.branch`, `order_type` |
| Phase 9 — Inventory | `OrderItem.menu_item` → Recipe/BOM → stock deduction |
