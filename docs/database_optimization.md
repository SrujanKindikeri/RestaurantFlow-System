# Database Optimization — Phase 22

## Overview

This document covers the composite indexes added in Phase 22 and the ORM query optimizations applied to the Order, Menu, and Expense views. All migrations are safe `AddIndex`-only operations and can be applied without downtime.

---

## Composite Indexes Added

### Order — `order_branch_status_created_at`

**Model:** `orders.Order`  
**Fields:** `branch`, `status`, `created_at`  
**Migration:** `orders/migrations/0005_phase22_add_composite_indexes.py`

**Rationale:** The order list endpoint filters by `branch + status` and sorts by `created_at`. Before this index the two existing single-field indexes (`branch,status`) and (`branch,created_at`) forced the planner into a less efficient scan. This composite covers the common filter `branch=X AND status=Y ORDER BY created_at DESC` in a single index scan.

---

### Expense — `expense_branch_status_date`

**Model:** `financials.Expense`  
**Fields:** `branch`, `status`, `expense_date`  
**Migration:** `financials/migrations/0005_phase22_add_composite_indexes.py`

**Rationale:** The expense list endpoint commonly filters `branch + status` with a date range on `expense_date`. The previously separate indexes on `(branch,status)` and `(expense_date)` could not be combined efficiently for this query pattern. The composite index allows a single scan.

---

### Notification — `notif_idempotency_check`

**Model:** `notifications.Notification`  
**Fields:** `company`, `branch`, `source_type`, `source_id`, `notification_type`  
**Migration:** `notifications/migrations/0004_phase22_add_composite_indexes.py`

**Rationale:** Every notification creation includes an idempotency guard query on `company + branch + source_type + source_id + notification_type`. Without a covering composite index this query caused a full or partial table scan on high-volume notification tables. This index makes the idempotency check a constant-time lookup.

---

### MenuItem — `menuitem_catalog_order`

**Model:** `menu.MenuItem`  
**Fields:** `restaurant`, `is_active`, `display_order`  
**Migration:** `menu/migrations/0004_phase22_add_composite_indexes.py`

**Rationale:** The POS catalog query filters `restaurant=X AND is_active=True ORDER BY display_order`. This composite covers all three in one scan, replacing two separate single-field passes.

---

## N+1 Query Fixes

### DiningTable list — `prefetch_related("sessions")`

**File:** `backend/orders/views.py` — `DiningTableListCreateView.get_queryset()`

The `DiningTableListSerializer` has two `SerializerMethodField` calls (`get_is_occupied`, `get_active_order`) that both query `obj.sessions`. Without prefetching, each table row in the list triggers two additional queries. Adding `.prefetch_related("sessions")` caches the sessions for all tables in a single batch query, reducing a list of N tables from 2N+1 queries to 3 queries.

---

### Order list — annotated `item_count`

**Files:**
- `backend/orders/views.py` — `OrderListCreateView.get_queryset()`
- `backend/orders/serializers.py` — `OrderSerializer`

The original `item_count` was a `SerializerMethodField` calling `obj.items.count()` per row — one extra query per order. The fix annotates the queryset with `annotate(item_count=Count("items"))`, moving the count into the main query, and changes the serializer field to `IntegerField(read_only=True)` which reads the annotation directly. A list of N orders now costs one query for counts instead of N.

---

### MenuItem list — `prefetch_related("prices", "branch_availability")`

**File:** `backend/menu/views.py` — `MenuItemListCreateView.get_queryset()`

`MenuItemDetailSerializer` accesses `obj.prices` and `obj.branch_availability` via `SerializerMethodField`. Without prefetching, each item in the list triggers separate queries for its prices and availability records. Adding `.prefetch_related("prices", "branch_availability")` batches both relations, reducing a list of N items from 2N+1 queries to 3 queries.

---

## Existing Concurrency Guards

The following service modules already use `select_for_update()` to prevent race conditions on financial and order mutations:

- **`orders/services.py`** — order creation, session management, item mutations
- **`billing/services.py`** — bill generation, payment recording
- **`payments/services.py`** — payment processing, reconciliation
- **`inventory/services.py`** — stock adjustments, purchase order receipt

These guards ensure that concurrent mutations to the same financial record are serialized at the database level, preventing double-spend and lost-update anomalies. No changes were made to these guards in Phase 22.

---

## Migration Safety

All migrations in this phase use only `migrations.AddIndex`. They:

- Do not alter any column types (`AlterField`)
- Do not contain raw SQL
- Do not delete or move data
- Can be applied to a live PostgreSQL database without locking rows (PostgreSQL builds indexes `CONCURRENTLY`-equivalent via Django's migration framework on supported versions)
