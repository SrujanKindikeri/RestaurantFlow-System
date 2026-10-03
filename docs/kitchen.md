# Kitchen Architecture — RestaurantFlow Phase 7

## Overview

The Kitchen module is a separate execution workflow that sits on top of the Phase 6 Order system. It receives confirmed orders from the POS/waiter layer and manages their journey through the kitchen preparation pipeline.

**Kitchen does NOT handle:** payments, billing, discounts, refunds, inventory deduction, cash, or accounting.

---

## Core Principle: Separate State Machines

Phase 6 Order and Phase 7 KitchenOrder have **independent state machines**:

| Layer | Model | States |
|---|---|---|
| Transaction | `Order` | DRAFT → CONFIRMED → CANCELLED |
| Kitchen | `KitchenOrder` | NEW → ACCEPTED → PREPARING → READY → CANCELLED |

This separation prevents the kitchen workflow from being tightly coupled to future billing or order lifecycle extensions.

---

## Models

### KitchenOrder

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `order` | OneToOne → Order | Source confirmed order |
| `branch` | FK → Branch | Denormalized for efficient KDS queries |
| `status` | CharField | NEW / ACCEPTED / PREPARING / READY / CANCELLED |
| `priority` | CharField | NORMAL / HIGH / URGENT |
| `kitchen_note` | TextField | Manager note visible on KDS |
| `received_at` | DateTimeField | Auto-set at creation |
| `accepted_at` | DateTimeField | Set when kitchen accepts |
| `started_at` | DateTimeField | Set when preparation begins |
| `ready_at` | DateTimeField | Set when all items are ready |
| `cancelled_at` | DateTimeField | Set if cancelled |
| `accepted_by` | FK → User | Who accepted |
| `started_by` | FK → User | Who started prep |
| `completed_by` | FK → User | Who marked ready |
| `cancelled_by` | FK → User | Who cancelled |
| `cancellation_reason` | TextField | Optional reason |

### KitchenOrderItem

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Primary key |
| `kitchen_order` | FK → KitchenOrder | Parent order |
| `order_item` | OneToOne → OrderItem | Source Phase 6 item |
| `menu_item` | FK → MenuItem | For future station routing |
| `item_name_snapshot` | CharField | Copied from OrderItem at creation, immutable |
| `quantity` | DecimalField | Copied from OrderItem at creation |
| `notes` | TextField | Preparation notes (e.g. "Less spicy") |
| `food_type` | CharField | VEG / NON_VEG / EGG / VEGAN / OTHER |
| `preparation_time_minutes` | PositiveIntegerField | Copied from MenuItem |
| `status` | CharField | NEW / PREPARING / READY / CANCELLED |
| `station` | CharField | Future kitchen station (blank by default) |
| `started_at` | DateTimeField | When this item started |
| `ready_at` | DateTimeField | When this item was marked ready |

**Important:** Financial data (unit_price, tax_rate, sku) is intentionally absent from KitchenOrderItem. Kitchen staff see only operational information.

---

## State Machine

### KitchenOrder Transitions

```
NEW ──→ ACCEPTED ──→ PREPARING ──→ READY
 │           │              │
 └─→ CANCELLED ←────────────┘
```

| From | Allowed To |
|---|---|
| NEW | ACCEPTED, CANCELLED |
| ACCEPTED | PREPARING, CANCELLED |
| PREPARING | READY, CANCELLED |
| READY | *(terminal)* |
| CANCELLED | *(terminal)* |

### KitchenOrderItem Transitions

```
NEW ──→ PREPARING ──→ READY
 │           │
 └─→ CANCELLED
```

**Auto-advance rule:** When all non-cancelled items reach READY, the parent KitchenOrder is automatically advanced to READY. This happens inside the same `transaction.atomic()` block as the item update — atomically.

---

## Service Layer

All business logic is in `kitchen/services.py`. Views are thin dispatchers.

| Function | Description |
|---|---|
| `send_order_to_kitchen(order)` | Creates KitchenOrder + KitchenOrderItems for a CONFIRMED Order. Idempotent. |
| `accept_kitchen_order(actor, kitchen_order)` | NEW → ACCEPTED |
| `start_preparation(actor, kitchen_order)` | ACCEPTED → PREPARING; also sets all NEW items to PREPARING |
| `mark_order_ready(actor, kitchen_order)` | PREPARING → READY; validates all items READY first |
| `cancel_kitchen_order(actor, kitchen_order, reason)` | Cancels order + all non-terminal items |
| `start_item_preparation(actor, kitchen_item)` | Item NEW → PREPARING |
| `mark_item_ready(actor, kitchen_item)` | Item PREPARING → READY; auto-advances order if all done |
| `update_kitchen_priority(actor, kitchen_order, priority)` | Updates priority on non-terminal orders |
| `publish_kitchen_event(event_type, kitchen_order)` | Publishes WebSocket event after DB commit |

---

## Concurrency Protection

All state transition services use:

```python
with transaction.atomic():
    locked = KitchenOrder.objects.select_for_update().get(pk=kitchen_order.pk)
    # validate transition
    # update state
```

This prevents two workers double-clicking ACCEPT from creating a corrupt state. PostgreSQL row-level locks ensure only one transition succeeds at a time.

---

## Order Cancellation Handling

When a Phase 6 Order is cancelled, the corresponding KitchenOrder must be handled:

- If `KitchenOrder.status` is NEW or ACCEPTED: cancel via `cancel_kitchen_order()`
- If PREPARING: requires `kitchen.cancel` permission; records who cancelled and why
- READY orders cannot be cancelled through the normal path

The KitchenOrder is **never deleted** — historical records are preserved for audit.

---

## Snapshot Principle

KitchenOrderItem snapshots are copied from OrderItem **at creation time** and never updated:

- `item_name_snapshot` ← `OrderItem.item_name_snapshot`
- `quantity` ← `OrderItem.quantity`
- `notes` ← `OrderItem.notes`
- `food_type` ← `MenuItem.food_type`
- `preparation_time_minutes` ← `MenuItem.preparation_time_minutes`

This ensures the kitchen always sees the original order details, even if the underlying menu data changes.

---

## Future: Kitchen Stations

The `KitchenOrderItem.station` field is nullable and reserved for future station routing:

```
MenuItem → KitchenStation
OrderItem → KitchenStation (via MenuItem)
KitchenOrderItem.station = "Grill" | "Cold" | "Beverage" | "Dessert"
```

No station management system is built in Phase 7.

---

## Database Indexes

KitchenOrder indexes:
- `(branch, status)` — live KDS queries
- `(branch, priority)` — priority-filtered views
- `(branch, received_at)` — time-ordered display
- `(status, priority)` — cross-branch priority dashboards
- `(branch, status, received_at)` — composite KDS query

KitchenOrderItem indexes:
- `(kitchen_order, status)` — item status checks
- `(menu_item, status)` — future station routing
