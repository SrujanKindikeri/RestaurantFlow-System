# Kitchen Display System (KDS) — RestaurantFlow Phase 7

## What Is the KDS?

The Kitchen Display System is the screen(s) mounted in the kitchen or prep area that shows incoming orders in real time. Staff use it to accept, start, and complete orders without any paper tickets.

---

## Screen Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ KITCHEN DISPLAY                        Branch: Main Branch     🔔   │
│ Saturday, Oct 3 2026          ●  Live        [Filters]             │
├─────────────────────────────────────────────────────────────────────┤
│ Status: ALL ▼   Type: ALL ▼   Priority: ALL ▼          12 orders    │
├──────────────┬──────────────┬──────────────┬──────────────────────┤
│     NEW (3)  │ ACCEPTED (2) │ PREPARING (5)│     READY (2)        │
├──────────────┼──────────────┼──────────────┼──────────────────────┤
│ ┌──────────┐ │ ┌──────────┐ │ ┌──────────┐ │ ┌──────────────────┐ │
│ │C01-0001  │ │ │D-0009    │ │ │D-0007    │ │ │C01-0004          │ │
│ │TAKEAWAY  │ │ │DINE-IN   │ │ │DINE-IN   │ │ │TAKEAWAY          │ │
│ │03:22     │ │ │T05       │ │ │T03       │ │ │✓ READY           │ │
│ │🔴 URGENT │ │ │08:14     │ │ │12:45     │ │ │                  │ │
│ │          │ │ │          │ │ │🔴 2×     │ │ │                  │ │
│ │🔴 2×Biryn│ │ │🟢 1×     │ │ │  Biryani │ │ │                  │ │
│ │🟢 1×Fries│ │ │  Masala  │ │ │🟢 1×     │ │ │                  │ │
│ │🟢 1×Coffe│ │ │🟢 2×Naan │ │ │  Coffee  │ │ │                  │ │
│ │          │ │ │          │ │ │          │ │ │                  │ │
│ │[ACCEPT]  │ │ │[START]   │ │ │[READY ▶] │ │ │                  │ │
│ └──────────┘ │ └──────────┘ │ └──────────┘ │ └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Order Card Contents

Each card shows:

| Field | Source |
|---|---|
| Order number | `KitchenOrder.order.order_number` |
| Order type | DINE-IN / TAKEAWAY / COUNTER |
| Table number | `Order.table.table_number` (DINE_IN only) |
| Counter code | `Order.counter.code` (COUNTER/TAKEAWAY) |
| Waiter name | `Order.assigned_waiter.full_name` |
| Age timer | Live countdown from `KitchenOrder.received_at` |
| Priority badge | NORMAL / HIGH / URGENT |
| Items list | `KitchenOrderItem` — name, quantity, notes, food type icon |
| Kitchen note | `KitchenOrder.kitchen_note` |
| Action button | Context-sensitive (ACCEPT / START PREP / ORDER READY) |

**Not shown:** prices, taxes, cash amounts, payment methods, profit, or any financial data.

---

## Action Buttons

| Order Status | Button Shown | Action |
|---|---|---|
| NEW | `ACCEPT` | → ACCEPTED |
| ACCEPTED | `START PREP` | → PREPARING |
| PREPARING | `ORDER READY` | → READY (validates all items ready first) |
| READY | ✓ READY FOR PICKUP | no action |
| Any active | `Cancel` (with confirmation) | → CANCELLED |

### Per-Item Buttons

Each item row also shows micro-actions for fine-grained control:
- `START` on NEW items → PREPARING
- `DONE` on PREPARING items → READY

When the last non-cancelled item is marked DONE, the order auto-advances to READY.

---

## Order Age Timer

The timer counts up from `KitchenOrder.received_at` (set server-side). The timer is calculated client-side from this timestamp — no polling required.

| Age | Color |
|---|---|
| 0–5 min | Gray |
| 5–10 min | Yellow |
| 10–20 min | Orange |
| 20+ min | Red |

The timer survives page refresh because it is derived from the server timestamp, not a browser `Date.now()` counter.

---

## Priority System

| Level | Visual |
|---|---|
| NORMAL | Gray badge |
| HIGH | Orange badge |
| URGENT | Pulsing red badge |

Priority is explicitly set by authorized staff (managers). The system never auto-escalates an order based on age or speculation.

Users with `kitchen.priority_update` permission see a priority dropdown on each active card.

---

## Sound Notifications

When a new `kitchen.order.created` WebSocket event arrives, a short audio beep plays via the Web Audio API.

- Toggle on/off via the 🔔 button in the header
- Sound plays once per event (deduplicated by `event_id`)
- Does not replay on WebSocket reconnect

---

## Filter Bar

| Filter | Options |
|---|---|
| Status | All / New / Accepted / Preparing / Ready |
| Order Type | All / Dine-In / Takeaway / Counter |
| Priority | All / Normal / High / Urgent |

Filters are applied client-side for instant response. The source of truth for filtering is the server-provided data — the KDS does not fabricate state.

---

## History View (`/kitchen/history`)

Shows past kitchen orders with:
- Date range filter (from / to)
- Status filter
- Preparation time (received_at → ready_at duration)
- Item count per order

Requires `kitchen.view_history` permission.

---

## Responsive Design

| Screen | Layout |
|---|---|
| Large monitor (≥ 1280px) | 4 columns (NEW / ACCEPTED / PREPARING / READY) |
| Desktop (≥ 1024px) | 4 columns |
| Tablet (< 1024px) | 2 columns, scrollable |

Buttons are large enough for touch operation on a tablet mounted in the kitchen.

---

## Performance Notes

- Initial state loaded via REST on mount (one query with `select_related` + `prefetch_related`)
- Subsequent updates driven by WebSocket (no polling)
- Timers are computed client-side from server timestamps — no repeat DB queries
- Mutations (accept/start/ready) refresh the full list from REST to ensure consistency
- N+1 queries eliminated via `select_related("order__table", "order__counter")` + `prefetch_related("items__menu_item")`
