# Phase 7 — Kitchen Display System: Implementation Summary

## What Was Built

Phase 7 adds real-time kitchen order management (KDS) on top of the Phase 6 Order system. When a cashier or waiter confirms an order, it automatically appears on the kitchen display without any page refresh.

---

## New Files

### Backend (`backend/kitchen/`)

| File | Purpose |
|---|---|
| `models.py` | `KitchenOrder`, `KitchenOrderItem` models with state machines |
| `services.py` | All kitchen business logic (8 service functions + event publisher) |
| `serializers.py` | KDS-safe serializers — no financial data |
| `views.py` | 11 REST API endpoints |
| `urls.py` | URL routing for kitchen API |
| `signals.py` | `post_save` on Order → auto-creates KitchenOrder on CONFIRMED |
| `consumers.py` | Async WebSocket consumer with JWT auth + branch isolation |
| `routing.py` | WebSocket URL patterns |
| `permissions.py` | `HasKitchenOrderAccess`, `HasKitchenItemAccess` permission classes |
| `access.py` | `get_accessible_kitchen_orders()`, `can_access_kitchen_order()` |
| `validators.py` | Standalone transition and priority validators |
| `admin.py` | Django admin with colored status column + inline items |
| `apps.py` | App config — registers signals on `ready()` |
| `migrations/0001_initial.py` | Initial DB migration |
| `tests/test_kitchen.py` | Order creation, state machine, idempotency tests |
| `tests/test_kitchen_items.py` | Item lifecycle, partial completion, auto-advance tests |
| `tests/test_permissions.py` | Service + API permission and IDOR tests |
| `tests/test_websocket.py` | WebSocket auth, sync, event delivery, branch isolation |
| `tests/test_concurrency.py` | Simultaneous accept/start/item_ready thread tests |

### Backend (modified)

| File | Change |
|---|---|
| `config/settings.py` | Added `kitchen` to `LOCAL_APPS`, added `kitchen` logger |
| `config/urls.py` | Added `path("api/", include("kitchen.urls"))` |
| `config/asgi.py` | Wired up `AuthMiddlewareStack(URLRouter(websocket_urlpatterns))` |
| `backend/.env.example` | Added `VITE_WS_URL` note |

### Frontend (`frontend/src/`)

| File | Purpose |
|---|---|
| `types/index.ts` | Added `KitchenOrder`, `KitchenOrderItem`, `KitchenEvent`, `KitchenSyncMessage` types |
| `services/kitchen.ts` | All kitchen REST API calls |
| `hooks/useKitchenWebSocket.ts` | WebSocket hook: JWT auth, reconnect, deduplication |
| `hooks/useKitchen.ts` | State management hook + all action mutations |
| `components/kitchen/KitchenConnectionStatus.tsx` | Live/Connecting/Disconnected indicator |
| `components/kitchen/KitchenOrderTimer.tsx` | Client-side age timer from server timestamp |
| `components/kitchen/KitchenPriorityBadge.tsx` | Priority badge + dropdown control |
| `components/kitchen/KitchenOrderCard.tsx` | Full order card with item rows and action buttons |
| `components/kitchen/KitchenStatusColumn.tsx` | Status column with count badge |
| `components/kitchen/KitchenFilters.tsx` | Status / type / priority filter pills |
| `pages/kitchen/KitchenDashboard.tsx` | Main KDS page with 4-column board |
| `pages/kitchen/KitchenHistory.tsx` | Date range history table |
| `App.tsx` | Routes: `/kitchen`, `/kitchen/history` |
| `layouts/MainLayout.tsx` | Kitchen section in sidebar nav |
| `frontend/.env.example` | Added `VITE_WS_URL` |

### Documentation (`docs/`)

| File | Content |
|---|---|
| `docs/kitchen.md` | Kitchen architecture, models, state machine, service API |
| `docs/kds.md` | KDS screen layout, card contents, filters, timers |
| `docs/realtime.md` | WebSocket architecture, events, reconnection, Redis failure |
| `docs/phase-7.md` | This file — implementation summary |

---

## REST API Endpoints

| Method | URL | Description | Permission |
|---|---|---|---|
| GET | `/api/kitchen/orders/` | Live KDS list (today, filterable) | `kitchen.view` |
| GET | `/api/kitchen/orders/<id>/` | Full order detail with items | `kitchen.view` |
| POST | `/api/kitchen/orders/<id>/accept/` | NEW → ACCEPTED | `kitchen.accept` |
| POST | `/api/kitchen/orders/<id>/start/` | ACCEPTED → PREPARING | `kitchen.start` |
| POST | `/api/kitchen/orders/<id>/ready/` | PREPARING → READY | `kitchen.order_ready` |
| POST | `/api/kitchen/orders/<id>/cancel/` | → CANCELLED | `kitchen.cancel` |
| POST | `/api/kitchen/orders/<id>/priority/` | Update priority | `kitchen.priority_update` |
| GET | `/api/kitchen/history/` | Historical orders | `kitchen.view_history` |
| GET | `/api/kitchen/items/<id>/` | Item detail | `kitchen.view` |
| POST | `/api/kitchen/items/<id>/start/` | Item NEW → PREPARING | `kitchen.item_start` |
| POST | `/api/kitchen/items/<id>/ready/` | Item PREPARING → READY | `kitchen.item_ready` |

---

## WebSocket Endpoint

```
ws://host/ws/kitchen/<branch_id>/?token=<jwt>
```

---

## Permissions Added

| Permission Code | Description |
|---|---|
| `kitchen.view` | View kitchen orders for assigned branch |
| `kitchen.view_history` | View historical kitchen data |
| `kitchen.accept` | Accept a NEW kitchen order |
| `kitchen.start` | Start preparation (ACCEPTED → PREPARING) |
| `kitchen.item_start` | Start an individual item |
| `kitchen.item_ready` | Mark an individual item READY |
| `kitchen.order_ready` | Mark the full order READY |
| `kitchen.cancel` | Cancel a kitchen order |
| `kitchen.priority_update` | Change order priority |

These permissions must be seeded via the Permission model and assigned to the relevant Roles (e.g. KITCHEN_STAFF, RESTAURANT_MANAGER).

---

## Key Design Decisions

### 1. Separate State Machines
`Order.status` (transaction) and `KitchenOrder.status` (kitchen execution) are independent. This prevents kitchen workflow from blocking future billing/payment phases.

### 2. Signals for Integration
The `post_save` signal on Order fires `send_order_to_kitchen()` when status transitions to CONFIRMED. This keeps the orders app clean — it does not need to import from kitchen.

### 3. Event-After-Commit
WebSocket events are published after `transaction.atomic()` commits. Redis failure cannot cause a false "success" on the DB operation.

### 4. Idempotency
`send_order_to_kitchen()` checks for an existing KitchenOrder before creating a new one. All state transition services return the current state if already in the target status, preventing double-click corruption.

### 5. IDOR Protection
All views use `kitchen_acl.get_accessible_kitchen_orders(user)` as the base queryset. A user from Branch B receives HTTP 404 (not 403) when accessing Branch A's kitchen orders — preventing enumeration.

### 6. No Financial Data in Kitchen
Serializers, event payloads, and KitchenOrderItem snapshots are all designed without unit prices, tax rates, SKUs, cash amounts, or any billing information.

---

## What Is NOT in Phase 7

| Feature | Future Phase |
|---|---|
| Billing / Invoice | Phase 8 |
| Payments / UPI / Card | Phase 8+ |
| Inventory deduction | Future |
| Waiter notification screen | Phase 8+ |
| Kitchen station management | Future |
| Customer CRM / delivery | Future |
| SERVED / COLLECTED status | Phase 8 |
| Transactional outbox | Future |

---

## Recommended Next Phase

**Phase 8 — Billing + Invoices + Tax Calculation + Discounts**

Phase 8 can consume:
- `Order` + `OrderItem` (with price/tax snapshots)
- `KitchenOrder.status == READY` as a readiness signal
- `KitchenOrder.ready_at` as the preparation completion timestamp

Phase 8 should NOT modify KitchenOrder status or kitchen workflow.
