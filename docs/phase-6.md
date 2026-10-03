# RestaurantFlow — Phase 6: Tables + Dine-In Management + Order Foundation + Order Types

---

## What was built

Phase 6 connects the existing Restaurant → Branch → Counter → Menu chain to a new Table → Order → OrderItem transaction foundation that future Kitchen, Billing, Payment, and Inventory phases will consume.

---

## Architecture

```
Organization
  └── Restaurant
        └── Branch
              ├── Counters
              │     └── CounterSessions
              │
              ├── DiningTables
              │     └── TableSessions
              │
              └── Menu (Phase 5)
                    ├── Categories
                    ├── MenuItems
                    ├── Branch Prices
                    ├── Availability
                    └── Tax Configuration

Transaction flow:

DINE_IN:   Waiter → Table → TableSession → Order → OrderItems → (Kitchen) → (Bill) → (Payment)
COUNTER:   Cashier → Counter → CounterSession → Order → OrderItems → (Kitchen) → (Bill) → (Payment)
TAKEAWAY:  Cashier → Counter → CounterSession → Order → OrderItems → (Kitchen) → (Bill) → (Payment)
```

---

## Database Models

### DiningTable
Physical table configuration. `table_number` is unique per branch. Occupancy is derived, never stored as a flag.

### TableSession
One group of guests occupying a table. DB partial unique constraint: only one OPEN session per table at a time. Closed sessions are preserved for history.

### OrderSequence
Concurrency-safe daily sequence counter for human-readable order numbers. Uses `select_for_update()` — never `MAX() + 1`.

### Order
Central transaction record. Supports DRAFT → CONFIRMED → CANCELLED lifecycle. Three types: DINE_IN, TAKEAWAY, COUNTER. Never physically deleted.

### OrderItem
Price and tax snapshot stored at time of order. Immutable after creation. Future menu price changes cannot alter existing historical orders.

---

## New Django App: `orders`

```
backend/orders/
  models.py          — DiningTable, TableSession, OrderSequence, Order, OrderItem
  access.py          — Scoped querysets (branch-isolated)
  services.py        — All business logic (10 service functions)
  serializers.py     — Read + write serializers, action serializers
  permissions.py     — DRF object-level permission classes
  views.py           — 12 view classes (generics + APIView)
  urls.py            — 16 URL patterns
  admin.py           — Admin registration with inline OrderItems
  migrations/
    0001_initial.py  — Creates all 5 tables with constraints and indexes
  tests/
    test_tables.py          — Table model + service + API tests
    test_orders.py          — Order + item lifecycle tests
    test_order_security.py  — IDOR, cross-restaurant, permission boundary tests
    test_concurrency.py     — DB constraint + sequence uniqueness tests
  management/commands/
    seed_order_data.py      — Seeds permissions + demo tables
```

---

## APIs Created

### Tables
| Endpoint | Description |
|---|---|
| `GET /api/tables/` | List (branch-scoped, filterable by section/occupancy) |
| `POST /api/tables/` | Create table |
| `GET /api/tables/{id}/` | Retrieve |
| `PATCH /api/tables/{id}/` | Update |
| `POST /api/tables/{id}/disable/` | Soft disable |
| `POST /api/tables/{id}/enable/` | Re-enable |
| `POST /api/tables/{id}/sessions/open/` | Open table session |
| `GET /api/table-sessions/` | List sessions |
| `GET /api/table-sessions/{id}/` | Retrieve session |
| `POST /api/table-sessions/{id}/close/` | Close session |

### Orders
| Endpoint | Description |
|---|---|
| `GET /api/orders/` | List (scoped, filterable by type/status/date/table/counter/waiter) |
| `POST /api/orders/` | Create order (type-aware validation) |
| `GET /api/orders/{id}/` | Detail with all items |
| `PATCH /api/orders/{id}/` | Update notes (DRAFT only) |
| `POST /api/orders/{id}/confirm/` | DRAFT → CONFIRMED |
| `POST /api/orders/{id}/cancel/` | Cancel with reason |
| `POST /api/orders/{id}/assign-waiter/` | Assign/reassign waiter |
| `POST /api/orders/{id}/items/` | Add item (resolves price + tax server-side) |
| `PATCH /api/order-items/{id}/` | Update quantity/notes |
| `DELETE /api/order-items/{id}/` | Remove item |

---

## Permissions Added

20 new permission codes:

```
table.view / table.create / table.update / table.disable
table.session.view / table.session.open / table.session.close
order.view.own / order.view.branch
order.create.dine_in / order.create.counter / order.create.takeaway
order.update / order.confirm
order.cancel / order.cancel.confirmed
order.item.add / order.item.update / order.item.remove
order.reassign_waiter
```

Run `python manage.py seed_order_data` to register permissions and assign them to roles.

---

## Frontend Changes

### New files
```
frontend/src/
  services/orders.ts                      — API client functions
  hooks/useOrders.ts                      — React Query hooks
  types/index.ts                          — Phase 6 types appended
  components/orders/
    OrderStatusBadge.tsx                  — Status + type badges
    TableCard.tsx                         — Single table tile
    TableGrid.tsx                         — Section-grouped table grid
    MenuCategoryTabs.tsx                  — POS fast category switching
    MenuItemCard.tsx                      — POS menu item quick-add
    OrderItemList.tsx                     — Editable (DRAFT) / read-only item list
    OrderSummary.tsx                      — Preview total display
  pages/tables/
    TablesDashboard.tsx                   — Tables page with grid + stats
  pages/orders/
    OrderListPage.tsx                     — Filterable order list
    OrderDetailPage.tsx                   — Order detail with inline items
    POSOrderScreen.tsx                    — Full-screen POS order entry
```

### Modified files
- `App.tsx` — Phase 6 routes added (`/tables`, `/orders`, `/orders/:id`, `/orders/new`, `/pos`)
- `MainLayout.tsx` — "Tables & Orders" nav section added

### Routes
| Route | Component | Description |
|---|---|---|
| `/tables` | `TablesDashboard` | Table grid with section grouping |
| `/orders` | `OrderListPage` | Order list with filters |
| `/orders/:id` | `OrderDetailPage` | Order detail + item management |
| `/orders/new` | `POSOrderScreen` | POS within layout |
| `/pos` | `POSOrderScreen` | Full-screen POS (no sidebar) |

---

## Security Model

Every API enforces: **authenticated user + permission code + branch scope**.

| Attack | Defence |
|---|---|
| User A accesses Restaurant B's table by UUID | Scoped queryset returns 404 |
| User A creates an order with Restaurant B's branch UUID | Service layer verifies branch access |
| User A adds Restaurant B's menu item to their order | Service layer checks `menu_item.restaurant == order.branch.restaurant` |
| Frontend sends a fake price | Backend resolves price from `MenuItemPrice` and ignores client value |
| Double-click confirm race | `select_for_update()` on Order row |
| Two waiters open same table simultaneously | DB partial unique constraint + `select_for_update()` |
| Order number race condition | `select_for_update()` on `OrderSequence` row |

---

## Concurrency

| Scenario | Protection |
|---|---|
| Two open table sessions for same table | DB partial unique: `UNIQUE (table) WHERE status='OPEN'` |
| Duplicate order numbers | `select_for_update()` on `OrderSequence` |
| Double-confirm same order | `select_for_update()` on `Order` in `confirm_order()` |
| Two open counter sessions | Already handled by Phase 4 |

---

## Order Numbering

Sequences are scoped and reset daily:

- `D-20261003-0001` — first dine-in order on that branch on 3 Oct 2026
- `C01-20261003-0042` — 42nd order on counter C01 that day
- Sequence date uses the **restaurant's local timezone** (not UTC)

The internal UUID never changes. The display `order_number` is set once at creation and never mutated.

---

## Seed Data

```bash
# Seed permissions only (safe in production)
python manage.py seed_order_data --permissions-only

# Seed permissions + demo tables for all branches
python manage.py seed_order_data

# Seed permissions + demo tables for a specific branch
python manage.py seed_order_data --branch MAIN
```

Demo tables created: T01–T08 across Indoor / Outdoor / Terrace sections.

---

## Known issues / limitations

| Item | Notes |
|---|---|
| Menu migrations | The `menu` app has no migration file; `orders` migration drops this dependency. When `menu` gets a named migration, add `("menu", "0001_initial")` to the orders migration dependencies. |
| Vite build | Blocked on this machine by Windows Application Control policy on rollup native binary. TypeScript check passes with 0 errors. Build works in Docker/Linux. |
| Table close with active orders | `close_table_session()` rejects close if active orders exist. The caller must cancel/complete all orders first. |
| DELIVERY order type | Not implemented. Reserved for a future phase. |

---

## What Phase 7 needs from Phase 6

Phase 7 (Kitchen / KDS) will:

1. Subscribe to the `order.confirmed` event (or poll `Order.status = CONFIRMED`)
2. Read `Order.order_type`, `Order.table`, `Order.counter`
3. Read `OrderItem.menu_item.preparation_time_minutes` for KDS scheduling
4. Extend `Order.status` with `ACCEPTED → PREPARING → READY → SERVED`
5. Optionally open a WebSocket channel (`django-channels` is already installed)

The service layer is deliberately structured so Phase 7 can add a post-confirm signal/event without touching the Phase 6 confirm logic.

---

## What Phase 8 (Billing) needs from Phase 6

All snapshot fields on `OrderItem` are designed for billing:

```python
item_name_snapshot      # Item name at time of order
sku_snapshot            # SKU at time of order
unit_price_snapshot     # Price per unit at time of order  ← immutable
tax_rate_snapshot       # Tax % at time of order           ← immutable
tax_code_snapshot       # Tax code at time of order        ← immutable
quantity                # Quantity ordered
line_total              # quantity × unit_price (preview only)
```

Phase 8 will add: subtotal, discount, tax total, rounding, grand total, payment, refund.

---

## Git commit

```
feat: add tables and order foundation (Phase 6)

- Django orders app: DiningTable, TableSession, OrderSequence, Order, OrderItem
- Concurrency-safe order numbering with daily reset
- Table sessions with DB partial unique constraint
- Three order types: DINE_IN, TAKEAWAY, COUNTER
- Price/tax snapshot on OrderItem (immutable after creation)
- 10 service functions with select_for_update + transaction.atomic
- 16 REST API endpoints with branch scope isolation
- 20 new permission codes seeded to system roles
- 4 test modules: tables, orders, security, concurrency
- Frontend: TablesDashboard, OrderList, OrderDetail, POSOrderScreen
- Frontend: 7 reusable order/table components
- TypeScript: 0 errors (tsc --noEmit clean)
```
