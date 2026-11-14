# RestaurantFlow — Phase 22 Performance Assessment
## Performance, Caching & Scalability Engineering

*All measurements marked ESTIMATED are derived from static code analysis without a running server. Measurements marked UNAVAILABLE require a live PostgreSQL instance.*

---

## 1. API Response Time Baselines

### Method
`python manage.py check` passes cleanly (config-level, no DB required). Actual timing requires a running server; estimates below are based on query pattern analysis.

| Endpoint Category | Estimated Latency (cold, no cache) | Primary Risk |
|---|---|---|
| POS catalog (`/api/menu/`) | 50–150 ms ESTIMATED | 2–4 joins; `MenuItemBranch.is_available` filter |
| Order list (`/api/orders/`) | 80–200 ms ESTIMATED | Multiple `SerializerMethodField` traversals |
| Bill list (`/api/bills/`) | 60–150 ms ESTIMATED | `select_related` present; N+1 on correction counts |
| Kitchen dashboard (`/ws/kitchen/<branch>/`) | 20–50 ms ESTIMATED (WS connect) | Full KO list on connect |
| Reporting summary | 200–800 ms ESTIMATED | Multi-table aggregation over `billing.Bill` |
| Central Control dashboard | 150–400 ms ESTIMATED | Counts across alerts, issues, branches |
| Inventory overview | 100–300 ms ESTIMATED | `StockBalance` per-item queries |
| Notifications list | 50–120 ms ESTIMATED | `NotificationRecipient` join per row |

---

## 2. Database Query Patterns

### 2.1 Existing `select_related` / `prefetch_related` Coverage

The codebase applies `select_related` and `prefetch_related` broadly across views. Coverage was confirmed in:
- `billing/views.py` — `select_related("order__branch", "created_by")`, `prefetch_related("items__menu_item")`
- `accounting/views.py` — `select_related(...)`, `prefetch_related("lines__account")`
- `inventory/views.py` — `select_related(...)` on all major list views
- `orders/views.py` — `prefetch_related("items__menu_item")` on detail views
- `payments/views.py` — `select_related("bill", "branch")`, `prefetch_related("refunds")`

### 2.2 Identified N+1 Risk Points

The following patterns carry N+1 risk and are **not yet fully mitigated**:

| File | Field | Risk |
|---|---|---|
| `orders/serializers.py` | `is_occupied` (`SerializerMethodField`) | Calls `sessions.filter(status=OPEN).exists()` per DiningTable row |
| `orders/serializers.py` | `active_session_id` (`SerializerMethodField`) | Per-row DB query to `TableSession` |
| `orders/serializers.py` | `item_count` | `self.items.count()` on Order — per-row count query |
| `orders/serializers.py` | `table_number`, `table_section`, `counter_name`, `counter_code` | Traverses related FK per row without prefetch |
| `menu/serializers.py` | `active_prices` (`SerializerMethodField`) | Per-row `prices.filter(is_active=True)` |
| `menu/serializers.py` | `branch_availability` (`SerializerMethodField`) | Per-row `MenuItemBranch` lookup |
| `kitchen/serializers.py` | `age_seconds` | `SerializerMethodField` — computed but not a DB query |
| `notifications/selectors.py` | Unread counts | Per-recipient `NotificationRecipient` count |

### 2.3 Slow Query Candidates

| Query Pattern | Model | Reason |
|---|---|---|
| `Order.objects.filter(branch=..., status=...)` with `created_at` range | `orders.Order` | Range scan on `created_at` without composite `(branch, status, created_at)` |
| `StockBalance.objects.filter(storage_location__branch=...)` | `inventory.StockBalance` | No branch-level index; must join through `StorageLocation` |
| `JournalEntry.objects.filter(restaurant=..., accounting_period=...)` | `accounting.JournalEntry` | Composite `(restaurant, accounting_period)` exists but `entry_date` range may not hit it |
| `Notification.objects.filter(company=..., source_type=..., source_id=...)` | `notifications.Notification` | Idempotency check on `(source_type, source_id, notification_type)` — no composite index |
| `Payment.objects.filter(bill=..., status=COMPLETED)` for overpayment guard | `payments.Payment` | Runs inside `transaction.atomic()` during payment creation |
| Dashboard KPI aggregations over `billing.Bill` for date range | `billing.Bill` | `SUM(grand_total)` groupby `branch` with date filter — no partial index |

---

## 3. Existing Indexes (Complete Inventory)

### `orders.Order`
```
(branch, status)
(branch, order_type)
(branch, created_at)
(order_number)
(table, status)
(counter, status)
(assigned_waiter, status)
(created_by, status)
(status, created_at)
(customer, status)
(customer, created_at)
```
**Missing:** `(branch, status, created_at)` — needed for time-boxed branch order queries

### `orders.OrderItem`
```
(order, menu_item)
(menu_item)
```
**Missing:** no issue — always queried via `order` FK

### `billing.Bill`
```
(branch, status)
(branch, created_at)
(branch, status, created_at)   ← composite exists ✓
(status, created_at)
(bill_number)
(order)
(created_by, status)
```
Well-indexed.

### `billing.BillItem`
```
(bill)
(order_item)
(menu_item)
```
Adequate for joins.

### `payments.Payment`
```
(bill, status)
(branch, status)
(branch, created_at)
(counter, status)
(counter_session, status)
(payment_method, status)
(status, created_at)
(initiated_by, status)
(transaction_reference)
```
Well-indexed. Overpayment guard locks via `select_for_update()` on Bill.

### `payments.PaymentRefund`
```
(payment, status)
(refund_number)
(status, requested_at)
(requested_by, status)
```
**Missing:** `(payment, status)` exists. Adequate.

### `inventory.StockBalance`
```
(inventory_item, storage_location)
(storage_location)
(inventory_item)
```
**Missing:** `(storage_location__branch)` — requires join; a branch-level dashboard query must join to `StorageLocation` first

### `inventory.StockMovement`
```
(inventory_item, created_at)
(storage_location, created_at)
(movement_type, created_at)
(reference_type, reference_id)
(performed_by, created_at)
(created_at)
```
Well-indexed.

### `inventory.PurchaseOrder`
```
(restaurant, status)
(branch, status)
(supplier, status)
(purchase_number)
(status, created_at)
(created_at)
```
Adequate.

### `menu.MenuItem`
```
(restaurant, is_active)
(restaurant, category)
(restaurant, food_type)
(restaurant, slug)
(restaurant, sku)
```
**Missing:** `(restaurant, is_active, display_order)` — POS catalog query sorts by `display_order`

### `menu.MenuItemPrice`
```
(menu_item, branch, is_active)
(menu_item, branch, effective_from)
(branch, is_active)
```
Adequate for price lookups.

### `kitchen.KitchenOrder`
```
(branch, status)
(branch, priority)
(branch, received_at)
(status, priority)
(status, received_at)
(branch, status, received_at)  ← composite ✓
```
Well-indexed.

### `notifications.Notification`
```
(company, created_at)
(company, notification_type)
(company, severity)
(restaurant, created_at)
(source_type, source_id)
(notification_type, source_type, source_id)
```
**Missing:** `(company, branch, source_type, source_id, notification_type)` — idempotency check runs this filter on every notification creation

### `accounting.JournalEntry`
```
(restaurant, entry_date)
(restaurant, status)
(restaurant, accounting_period)
(source_type, source_id)
(entry_date, status)
(created_by)
(branch, entry_date)
```
Adequate.

### `financials.Expense`
```
(restaurant, status)
(restaurant, payment_status)
(branch, status)
(category, status)
(expense_date)
(due_date)
(created_by)
(status, created_at)
(expense_number)
```
**Missing:** `(branch, status, expense_date)` — branch manager dashboard queries expenses by branch + status + date range

### `accounts.SecurityAuditLog` / `AuditEvent`
```
(event, created_at)
(actor, created_at)
(target_user, created_at)
(organization, created_at)
(outcome, created_at)
(ip_address, created_at)
```
Adequate for audit queries.

### `operations.OperationalShift`
```
(branch, status)
(branch, started_at)
```
Adequate.

---

## 4. Cache Usage

### Existing Cache Infrastructure
- **Backend:** `django.core.cache.backends.redis.RedisCache` via `REDIS_URL`
- **Channel layer:** `channels_redis.core.RedisChannelLayer` (separate connection, same Redis instance)
- `common/caching/` module fully implemented with:
  - `services.py` — `CacheService.get/set/delete/delete_pattern/get_or_set/get_secure`
  - `keys.py` — tenant-scoped key builders
  - `invalidation.py` — `transaction.on_commit()` invalidation functions
  - `policies.py` — TTL constants with ±15% jitter

### Current Cache Integration Status

| Resource | Cached? | Key Schema | TTL |
|---|---|---|---|
| Menu catalog | **Partial** — infrastructure exists, not wired into views | `restaurantflow:branch:{id}:menu_catalog:{hash}` | 300s |
| Branch config | **Partial** — infrastructure exists, not wired | `restaurantflow:branch:{id}:config:{key}` | 600s |
| User permissions | **Partial** — infrastructure exists, not wired | `restaurantflow:user:{id}:branch:{id}:permissions` | 300s |
| Dashboard KPIs | **Not wired** | `restaurantflow:restaurant:{id}:branch:{id}:dashboard_kpi:{date}` | 120s |
| Reporting summaries | **Not wired** | `restaurantflow:report:{type}:{scope}:{from}:{to}` | 300s |
| Inventory availability | **Not wired** | `restaurantflow:branch:{id}:inventory:{item_id}` | 60s |
| Payments | **Never cached** ✓ | — | — |
| Accounting balances | **Never cached** ✓ | — | — |
| Audit records | **Never cached** ✓ | — | — |

### Cache Invalidation Hooks
All invalidation functions exist in `invalidation.py` and use `transaction.on_commit()`. They are **not yet called** from service layer write paths.

---

## 5. Frontend Bundle Configuration

### Current State (vite.config.ts)
```
manualChunks:
  vendor-react:  [react, react-dom, react-router-dom]
  vendor-query:  [@tanstack/react-query]
  vendor-charts: [recharts]
```
- All 60+ route pages are already split with `React.lazy()` ✓
- `Suspense` boundary present in `App.tsx` ✓
- `useDebounce` hook exists (300ms default) — used in 3 pages only
- `React.memo` applied on 5 components only (StatCard, MenuItemCard, NotificationBell, BillItemsTable, KitchenOrderCard)
- No `AbortController` usage found — requests are not cancelled on route change
- No virtualized list library installed — large tables render all rows

### Missing Chunks
No `ui-components` or `feature` chunk groups defined. Lucide icons, recharts, and tailwind utilities are bundled together, increasing initial parse time.

---

## 6. Celery Task Patterns

### Registered Tasks
| Task | Queue | Idempotent? | Timeout |
|---|---|---|---|
| `notifications.dispatch_notification` | `notifications` (via `CELERY_TASK_ROUTES`) | ✓ (NotificationRecipient dedup) | 300s hard / 240s soft |
| `notifications.retry_pending_deliveries` | `notifications` | ✓ | 300s |
| `notifications.cleanup_old_notifications` | `notifications` | ✓ | 300s |
| `crm.expire_loyalty_points` | `maintenance` | ✓ | 300s |
| `crm.cleanup_expired_redemptions` | `maintenance` | ✓ | 300s |
| `crm.run_segmentation_all_restaurants` | `maintenance` | ✓ | 300s |
| `marketing.*` (5 tasks) | `maintenance` | ✓ | 300s |

### Queue Routing Status
`CELERY_TASK_ROUTES` in settings.py routes `notifications.*` → `notifications`, `crm.*` / `marketing.*` → `maintenance`. **Missing routes:** `default` queue unspecified; `reports.*` and `maintenance.*` queue names are defined in routing but no `reports` queue tasks exist yet.

### Worker Configuration
No Gunicorn or Celery worker concurrency settings configured in docker-compose or deployment files. `CELERY_TASK_TIME_LIMIT = 300` and `CELERY_TASK_SOFT_TIME_LIMIT = 240` are set globally.

---

## 7. WebSocket Group Patterns

| Consumer | Group Name Pattern | Scope |
|---|---|---|
| `kitchen/consumers.py` | `kitchen_{branch_id}` | Branch-scoped — all kitchen staff in a branch share one group |
| `notifications/consumers.py` | `notifications_user_{user_id}` | Per-user — structurally prevents cross-user leakage |

### Payload Analysis
- Kitchen consumer sends full `KitchenOrder` state on connect (REST sync). Payload size is unbounded; a branch with 100 open kitchen orders serializes all of them on connect.
- Notification consumer sends `unread_count` on sync — lightweight.
- Group naming correctly scopes by branch/user. No cross-tenant leakage possible.

---

## 8. Known Bottlenecks

### High Priority
1. **Menu catalog not cached** — POS catalog endpoint fetches `MenuItem + MenuItemBranch + MenuItemPrice` on every request. At 50 POS terminals across branches, this generates ~3,000 reads/min during peak.
2. **Dashboard KPI not cached** — `reporting/aggregations.py` runs `Sum(grand_total)` over `billing.Bill` on every dashboard load. No result caching.
3. **Reporting summaries not cached** — `select_sales_summary()` aggregates `BillItem` rows on every report page load.
4. **Cache invalidation hooks not wired** — All infrastructure exists but service layer write paths do not call `invalidate_menu_catalog()`, `invalidate_dashboard_kpis()`, etc.

### Medium Priority
5. **N+1 on DiningTable list** — `is_occupied` and `active_session_id` cause one DB query per table row.
6. **N+1 on Order list** — `item_count` calls `self.items.count()` per order; not replaced by `annotate(item_count=Count('items'))`.
7. **Menu serializer N+1** — `active_prices` and `branch_availability` cause 2 queries per MenuItem in list views.
8. **Kitchen WS payload** — Full kitchen state on connect is unbounded; should be paginated or limited to `status IN (PENDING, ACCEPTED, PREPARING)`.
9. **No `react-window` / list virtualization** — Inventory, order history, and kitchen tables that return 100+ rows render every DOM node.

### Low Priority
10. **Frontend search fields** — Only 3 pages use `useDebounce`; 20+ search inputs fire on every keystroke.
11. **No request cancellation** — AbortController not used; stale requests from rapid navigation accumulate.
12. **Missing composite indexes** — `(branch, status, created_at)` missing on `Order`; `(branch, status, expense_date)` missing on `Expense`.
13. **`CONN_MAX_AGE` set to 60** — Good for Gunicorn sync workers, but must be set to `0` if PgBouncer in transaction-pooling mode is added.

---

## 9. Concurrency & Financial Correctness — Current State

| Operation | Mechanism | Status |
|---|---|---|
| Order confirmation | `select_for_update()` on Order | ✓ Implemented |
| Bill finalization | `select_for_update()` on Bill | ✓ Implemented |
| Payment creation | `select_for_update()` on Bill (overpayment guard) | ✓ Implemented |
| Payment number generation | `select_for_update()` on `PaymentSequence` | ✓ Implemented |
| Refund processing | `select_for_update()` on `PaymentRefund` | ✓ Implemented |
| Inventory deduction | `select_for_update()` on `StockBalance` | ✓ Implemented |
| Inventory transfer | `select_for_update()` on source + destination `StockBalance` | ✓ Implemented |
| Recipe consumption | `select_for_update()` on `StockBalance` | ✓ Implemented |
| Accounting posting | `transaction.atomic()` with balance invariant check | ✓ Implemented |
| Accounting reversal | `select_for_update()` on `JournalEntry` | ✓ Implemented |
| Bill sequence (number gen) | `select_for_update()` on `BillSequence` | ✓ Implemented |
| Order sequence (number gen) | `select_for_update()` on `OrderSequence` | ✓ Implemented |

Existing tests: `backend/tests/test_concurrency.py` covers concurrent payment on the same bill. Inventory concurrent deduction and transfer tests not yet written.

---

## 10. Infrastructure Summary

| Component | Current Config | Phase 22 Gap |
|---|---|---|
| PostgreSQL | 15-alpine, `CONN_MAX_AGE=60` | No PgBouncer; `CONN_MAX_AGE` must be `0` with transaction-pooling PgBouncer |
| Redis | 7-alpine, `appendonly yes`, password-protected | No `maxmemory` / `maxmemory-policy` set |
| Celery | Auto-discovered tasks, beat on DB scheduler | Workers not configured in docker-compose |
| Gunicorn | Not in docker-compose (dev uses `runserver`) | No worker/thread config documented |
| Nginx | No nginx service in docker-compose | Not present |
| Channel Layer | `channels_redis` on same Redis DB 0 | Should use separate Redis DB for channels vs cache |
| Resource Limits | No `mem_limit` / `cpus` on any service | No container limits set |
