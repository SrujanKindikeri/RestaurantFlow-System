# Implementation Plan — Phase 22: Performance, Caching & Scalability

> **Backend root**: `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\backend\`
> All `python manage.py` commands run from that directory.
> Frontend root: `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\frontend\`
> Docs/performance artefacts live at the **repo root** (not inside backend/).
> FEAT artefacts: `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\.agents\tasks\phase22-performance\`

---

## FEAT dependency order

| FEAT | Name | Depends on |
|---|---|---|
| FEAT-001 | DB query optimisation + indexing + docs | — |
| FEAT-002 | Redis caching module + invalidation | — (independent) |
| FEAT-003 | API pagination + frontend performance | — (independent) |
| FEAT-004 | Concurrency safeguards + tests | FEAT-002 (uses CacheService in tests) |
| FEAT-005 | Load testing + bulk ops + final validation + commit | FEAT-001..004 complete |

FEAT-001, FEAT-002, FEAT-003 are mutually independent and can be implemented sequentially in any order. FEAT-004 should come after FEAT-002 so the cache tests can import CacheService. FEAT-005 is the integration, validation, and commit step.

---

## Implementation Plan

- [ ] 1. **Performance audit documentation**
      Write `docs/performance_assessment_phase22.md` at the repo root.
      Sections required: N+1 patterns identified (OrderListView missing branch/waiter select_related, BillList missing order select_related, inventory views missing item/location select_related); missing indexes (Notification source_type/source_id, EnterpriseConfiguration effective_from/effective_to, CRM Customer composite restaurant+is_active); existing cache usage (reporting/services.py uses raw `cache.get/set` for sales_trend, top_items; no menu catalog cache; no dashboard KPI cache); pagination baseline (global PAGE_SIZE=20, no MAX enforced); WebSocket group scoping (all three consumers already correctly scoped — kitchen_{branch_id}, company_{org_id}_central_control, notifications_user_{user_id}); Celery queues (all tasks on default queue); frontend (all ~90 page imports are eager in App.tsx — no code-splitting). Mark all metrics requiring a running environment as UNAVAILABLE.
      Files: `docs/performance_assessment_phase22.md`
      Verify: file exists and contains all required sections (review before proceeding).

- [ ] 2. **Database query optimization — select_related / prefetch_related**
      Depends on: nothing (pure view changes, no migrations).
      In each view listed below, add the query optimisations so serializers never trigger per-row DB lookups:

      | File | Change |
      |---|---|
      | `backend/orders/views.py` | `OrderListCreateView.get_queryset`: add `.select_related('branch', 'created_by', 'assigned_waiter', 'table', 'counter')` before `.prefetch_related('items')`. `OrderDetailView.get_queryset`: add `.select_related('branch','created_by','assigned_waiter','table','counter')` before `.prefetch_related('items__menu_item')`. `TableSessionListView.get_queryset`: add `.select_related('table__branch','opened_by')`. |
      | `backend/billing/views.py` | Bill list queryset: `.select_related('branch','order__branch','created_by','finalized_by')`. Bill detail queryset: add `.prefetch_related('items__menu_item','items__order_item')`. |
      | `backend/payments/views.py` | Payment list: `.select_related('bill__order','branch','initiated_by','counter')`. Refund list: `.select_related('payment__bill','requested_by','approved_by')`. |
      | `backend/inventory/views.py` | StockBalance list: `.select_related('inventory_item__restaurant','storage_location__branch')`. PurchaseOrder list: `.select_related('supplier','branch','restaurant','created_by')`. StockMovement list: `.select_related('inventory_item','storage_location','performed_by')`. |
      | `backend/notifications/views.py` | Notification list: `.select_related('company','restaurant','branch')`. NotificationRecipient list: `.select_related('notification','user')`. |
      | `backend/enterprise/views.py` | EnterpriseConfiguration list: `.select_related('company','restaurant','branch')`. StaffTransfer list: `.select_related('from_branch','to_branch','requested_by','approved_by')`. |
      | `backend/reporting/dashboard_services.py` | Verify `get_dashboard_kpis()` uses DB-level `.aggregate()` calls (Sum/Count/Coalesce), not Python loops over querysets. Rewrite any Python-loop aggregations to use `.aggregate()`. |

      Files: `backend/orders/views.py`, `backend/billing/views.py`, `backend/payments/views.py`, `backend/inventory/views.py`, `backend/notifications/views.py`, `backend/enterprise/views.py`, `backend/reporting/dashboard_services.py`
      Verify: `cd backend && python manage.py check && python manage.py test`

- [ ] 3. **New database index migrations**
      Read each app's latest migration first to avoid duplicating existing indexes.
      Create these migration files. Use `SeparateDatabaseAndState` with `CREATE INDEX CONCURRENTLY` for large tables (orders_order, billing_bill, payments_payment, inventory_stockmovement); use regular `AddIndex` for smaller/newer tables.

      | Migration file | Indexes added |
      |---|---|
      | `backend/notifications/migrations/0002_performance_indexes.py` | `Notification`: `(company, notification_type, created_at)`, `(source_type, source_id)`, `(restaurant, status, created_at)`, `(branch, status, created_at)`. `NotificationRecipient`: `(user, is_read, created_at)`, `(notification, user)`. |
      | `backend/enterprise/migrations/0002_performance_indexes.py` | `EnterpriseConfiguration`: `(company, key, effective_from)`, `(branch, key, is_active)`. `StaffBranchAssignment`: `(user, branch, is_active)`. `MenuRollout`: `(company, status, created_at)`. |
      | `backend/crm/migrations/0002_performance_indexes.py` | `Customer`: `(restaurant, is_active, created_at)`. `LoyaltyAccount`: `(loyalty_program, points_balance)`. |
      | `backend/marketing/migrations/0002_performance_indexes.py` | `Campaign`: `(restaurant, status, start_date)`, `(restaurant, status, end_date)`. |
      | `backend/menu/migrations/0002_performance_indexes.py` | `MenuItemPrice`: `(menu_item, branch, effective_from)`, `(menu_item, branch, is_active)`. `MenuItemBranch`: `(branch, is_available)`. |

      Each migration must list correct `dependencies` on its app's latest migration. Each must pass `python manage.py sqlmigrate <app> 0002_performance_indexes` without error.
      Files: five migration files as listed above.
      Verify: `cd backend && python manage.py makemigrations --check` returns "No changes detected". `python manage.py test`

- [ ] 4. **CONN_MAX_AGE and Celery queue routing**
      In `backend/config/settings.py`:
      - Add `'CONN_MAX_AGE': 60` to the `DATABASES['default']` dict.
      - Add `CELERY_TASK_TIME_LIMIT = 300` and `CELERY_TASK_SOFT_TIME_LIMIT = 240`.
      - Add `CELERY_TASK_ROUTES` dict:
        ```python
        CELERY_TASK_ROUTES = {
            'notifications.*': {'queue': 'notifications'},
            'crm.*':           {'queue': 'maintenance'},
            'marketing.*':     {'queue': 'maintenance'},
        }
        ```
      Files: `backend/config/settings.py`
      Verify: `cd backend && python manage.py check`

- [ ] 5. **common/caching module** (depends on item 4 for settings; otherwise independent)
      Create all five files. The `common` app must be added to `LOCAL_APPS` in `settings.py`.

      | File | Purpose |
      |---|---|
      | `backend/common/__init__.py` | empty |
      | `backend/common/apps.py` | `AppConfig(name='common')` |
      | `backend/common/caching/__init__.py` | empty |
      | `backend/common/caching/policies.py` | TTL constants (`MENU_CATALOG_TTL=300`, `BRANCH_CONFIG_TTL=600`, `USER_PERMISSIONS_TTL=300`, `DASHBOARD_KPI_TTL=120`, `REPORTING_SUMMARY_TTL=300`, `INVENTORY_AVAILABILITY_TTL=60`), `JITTER_FACTOR=0.15`, `add_jitter(ttl)` function |
      | `backend/common/caching/keys.py` | `menu_catalog_key(branch_id, params_hash)`, `branch_config_key(branch_id, key)`, `user_permissions_key(user_id, branch_id)`, `dashboard_kpi_key(user_id, restaurant_id, branch_id, date_str)`, `reporting_key(report_type, scope_hash, date_from, date_to)`, `inventory_availability_key(branch_id, item_id)`, `make_params_hash(*args, **kwargs)` |
      | `backend/common/caching/services.py` | `CacheService` with `get`, `set`, `delete`, `delete_pattern`, `get_or_set` (with optional Redis lock + jitter), `get_secure` (returns `CACHE_MISS_SENTINEL` sentinel on `RedisError`). All methods catch `redis.exceptions.RedisError` and log warning. |
      | `backend/common/caching/invalidation.py` | `invalidate_menu_catalog(branch_id)`, `invalidate_branch_config(branch_id, key)`, `invalidate_user_permissions(user_id, branch_id)`, `invalidate_dashboard_kpis(restaurant_id, branch_id)`, `invalidate_inventory_availability(branch_id, item_id)`, `invalidate_reporting_cache(report_type, scope_hash)` — all wrap their `CacheService` call in `transaction.on_commit(lambda: ...)` |

      Files: `backend/common/__init__.py`, `backend/common/apps.py`, `backend/common/caching/__init__.py`, `backend/common/caching/policies.py`, `backend/common/caching/keys.py`, `backend/common/caching/services.py`, `backend/common/caching/invalidation.py`, `backend/config/settings.py` (add `'common'` to `LOCAL_APPS`)
      Verify: `cd backend && python manage.py check`

- [ ] 6. **Wire caching into menu catalog, dashboard KPIs, and reporting services**
      - `backend/menu/views.py` — branch catalog endpoint: check `CacheService.get(menu_catalog_key(...))` before hitting DB; set after miss with `add_jitter(MENU_CATALOG_TTL)`.
      - `backend/reporting/dashboard_services.py` — `get_dashboard_kpis()`: check `CacheService.get(dashboard_kpi_key(...))` before aggregation; set after miss with `add_jitter(DASHBOARD_KPI_TTL)`.
      - `backend/reporting/services.py` — migrate all existing `cache.get/set` calls (for sales_trend, top_items, branch, financial) to use `CacheService.get/set` and `reporting_key()` from `keys.py`. Ensures Redis failures are uniformly handled.

      Depends on: item 5 (caching module).
      Files: `backend/menu/views.py`, `backend/reporting/dashboard_services.py`, `backend/reporting/services.py`
      Verify: `cd backend && python manage.py test`

- [ ] 7. **Wire permissions cache using get_secure**
      In `backend/accounts/access.py`, in `has_permission(user, code)` and `can_access_branch(user, branch)`: wrap the DB lookups with `CacheService.get_secure(user_permissions_key(...))`. If result is `CACHE_MISS_SENTINEL` (Redis down), skip cache and query DB directly. If result is `None` (not in cache), query DB and store with `add_jitter(USER_PERMISSIONS_TTL)`. This ensures Redis failure never silently grants or denies access.

      Depends on: item 5.
      Files: `backend/accounts/access.py`
      Verify: `cd backend && python manage.py test`

- [ ] 8. **Wire cache invalidation signals**
      Create or update signal handler files. Register handlers in each app's `apps.py` `ready()` method.

      | Signal file | Signal | Invalidation called |
      |---|---|---|
      | `backend/menu/signals.py` | `post_save` on `MenuItem`, `MenuItemPrice`, `MenuItemBranch` | `invalidate_menu_catalog(branch_id)` via `transaction.on_commit` |
      | `backend/enterprise/signals.py` | `post_save` on `EnterpriseConfiguration` | `invalidate_branch_config(branch_id, key=instance.key)` via `transaction.on_commit` |
      | `backend/accounts/signals.py` | `post_save` on `UserRoleAssignment` | `invalidate_user_permissions(user_id=instance.user_id)` via `transaction.on_commit` |
      | `backend/inventory/signals.py` | `post_save` on `StockBalance` | `invalidate_inventory_availability(branch_id=..., item_id=...)` via `transaction.on_commit` |

      Update `ready()` in `backend/menu/apps.py`, `backend/enterprise/apps.py`, `backend/accounts/apps.py`, `backend/inventory/apps.py` to import signals.
      Depends on: item 5.
      Files: `backend/menu/signals.py`, `backend/enterprise/signals.py`, `backend/accounts/signals.py`, `backend/inventory/signals.py`, `backend/menu/apps.py`, `backend/enterprise/apps.py`, `backend/accounts/apps.py`, `backend/inventory/apps.py`
      Verify: `cd backend && python manage.py check && python manage.py test`

- [ ] 9. **Pagination enforcement and export row cap**
      - Create `backend/core/pagination.py` with `SafePageNumberPagination(PageNumberPagination)` that sets `max_page_size = 100`.
      - In `backend/config/settings.py` REST_FRAMEWORK, change `DEFAULT_PAGINATION_CLASS` to `'core.pagination.SafePageNumberPagination'` and set `MAX_PAGE_SIZE: 100`.
      - In `backend/reporting/constants.py`, add `MAX_EXPORT_ROWS = 10000`.
      - In `backend/reporting/views.py` `ExportCSVView.get()`, after fetching data, check `len(rows) > MAX_EXPORT_ROWS`; if exceeded return HTTP 400: `{"error": True, "code": "EXPORT_TOO_LARGE", "message": "Export exceeds 10,000 rows. Narrow your date range or add filters."}`.

      Files: `backend/core/pagination.py`, `backend/config/settings.py`, `backend/reporting/constants.py`, `backend/reporting/views.py`
      Verify: `cd backend && python manage.py check && python manage.py test`

- [ ] 10. **Frontend: React.lazy route splitting**
       In `frontend/src/App.tsx`, replace all page component imports (except `DashboardPage`, `LoginPage`, `RegisterPage`) with `React.lazy(() => import(...))`. Add `import React from 'react'` at the top. Wrap the entire `<Routes>` JSX with `<React.Suspense fallback={<div className="flex items-center justify-center h-screen">Loading...</div>}>`. This reduces initial JS parse by splitting ~90 page chunks.
       Files: `frontend/src/App.tsx`
       Verify: `cd frontend && npm run build` (no TypeScript errors, build output shows many chunks < 500 KB each)

- [ ] 11. **Frontend: Vite chunk splitting**
       In `frontend/vite.config.ts`, add `build.rollupOptions.output.manualChunks`:
       ```ts
       manualChunks: {
         'vendor-react': ['react', 'react-dom', 'react-router-dom'],
         'vendor-query': ['@tanstack/react-query'],
         'vendor-charts': ['recharts'],
       }
       ```
       Files: `frontend/vite.config.ts`
       Verify: `cd frontend && npm run build` (check output — vendor chunks present, no single chunk > 500 KB)

- [ ] 12. **Frontend: useDebounce hook and debounced search inputs**
       Create `frontend/src/hooks/useDebounce.ts`:
       ```ts
       import { useState, useEffect } from 'react'
       export function useDebounce<T>(value: T, delay = 300): T {
         const [debounced, setDebounced] = useState(value)
         useEffect(() => {
           const id = setTimeout(() => setDebounced(value), delay)
           return () => clearTimeout(id)
         }, [value, delay])
         return debounced
       }
       ```
       Apply `useDebounce` to search inputs in: `frontend/src/pages/menu/MenuItems.tsx`, `frontend/src/pages/inventory/InventoryItemsPage.tsx`, `frontend/src/pages/crm/CustomerListPage.tsx`, `frontend/src/pages/orders/OrderListPage.tsx`. Pattern: `const debouncedSearch = useDebounce(searchInput, 300)` then pass `debouncedSearch` to the API query hook.
       Files: `frontend/src/hooks/useDebounce.ts`, four page files listed above.
       Verify: `cd frontend && npm run build && npm run lint`

- [ ] 13. **Frontend: QueryClient defaults, component memoization, Skeleton component**
       - `frontend/src/main.tsx`: configure `QueryClient` with `defaultOptions: { queries: { staleTime: 30_000, gcTime: 300_000, refetchOnWindowFocus: false } }`.
       - `frontend/src/components/ui/Skeleton.tsx`: create a `<Skeleton className?>` component with `animate-pulse bg-gray-200 rounded` Tailwind classes.
       - Wrap in `React.memo`: `KitchenOrderCard.tsx` (equality: `order.id + order.status`), `MenuItemCard.tsx` (equality: `item.id + item.updated_at`), `NotificationBell.tsx` (simple shallow), `StatCard.tsx` (simple shallow), `BillItemsTable.tsx` (equality: `items.length`).
       - Add loading skeletons in `OrderListPage.tsx` (5 skeleton rows), `KitchenDashboard.tsx` (4 skeleton cards), `BillListPage.tsx` (5 skeleton rows) using the `<Skeleton>` component.

       Files: `frontend/src/main.tsx`, `frontend/src/components/ui/Skeleton.tsx`, `frontend/src/components/kitchen/KitchenOrderCard.tsx`, `frontend/src/components/orders/MenuItemCard.tsx`, `frontend/src/components/notifications/NotificationBell.tsx`, `frontend/src/components/ui/StatCard.tsx`, `frontend/src/components/billing/BillItemsTable.tsx`, `frontend/src/pages/orders/OrderListPage.tsx`, `frontend/src/pages/kitchen/KitchenDashboard.tsx`, `frontend/src/pages/billing/BillListPage.tsx`
       Verify: `cd frontend && npm run build && npm run lint`

- [ ] 14. **Concurrency safeguard audit and fixes**
       Read these service files and confirm or add `select_for_update()` + `transaction.atomic()`:
       - `backend/payments/services.py` — `create_payment`: lock `Bill` with `Bill.objects.select_for_update().get(pk=bill_id)` inside `transaction.atomic()`. Validate `payment.amount ≤ bill.remaining_amount` inside the same transaction.
       - `backend/billing/services.py` — `finalize_bill`: lock `Bill.objects.select_for_update().get(pk=bill_id)` before setting `status=FINALIZED`.
       - `backend/payments/services.py` — `process_refund` or `approve_refund`: lock `Payment.objects.select_for_update().get(pk=payment_id)` before creating refund record.
       - `backend/inventory/services.py` — `deduct_stock`: lock `StockBalance.objects.select_for_update().get(...)` before decrementing `quantity`.
       - `backend/inventory/services.py` — `complete_transfer` (or equivalent): lock both source and destination `StockBalance` rows in `pk` order inside one `transaction.atomic()` to prevent deadlocks.

       If the lock already exists, verify and document. If missing, add it.
       Files: `backend/payments/services.py`, `backend/billing/services.py`, `backend/inventory/services.py`
       Verify: `cd backend && python manage.py test`

- [ ] 15. **Celery task timeout/idempotency hardening**
       - `backend/config/settings.py`: verify `CELERY_TASK_TIME_LIMIT = 300` and `CELERY_TASK_SOFT_TIME_LIMIT = 240` are set (from item 4).
       - `backend/notifications/tasks.py` — `deliver_notification_channel` already checks terminal status at top; verify this guard. Add `time_limit=120, soft_time_limit=100` to the `@shared_task` decorator.
       - `backend/crm/tasks.py` — `refresh_customer_statistics`: add `time_limit=120, soft_time_limit=100`. `run_segmentation_for_restaurant`: add `time_limit=600, soft_time_limit=540`.
       - `backend/marketing/tasks.py` — read the file; add `time_limit=300, soft_time_limit=240` to all marketing tasks.
       - Verify all tasks have `max_retries` set (not relying on global default).

       Files: `backend/notifications/tasks.py`, `backend/crm/tasks.py`, `backend/marketing/tasks.py`, `backend/config/settings.py`
       Verify: `cd backend && python manage.py check`

- [ ] 16. **Automated tests — cache behaviour**
       Create `backend/tests/__init__.py` (empty) and `backend/tests/test_cache.py`. Tests:
       - `test_cache_set_get_delete`: set → get (matches) → delete → get (None).
       - `test_redis_failure_returns_none`: mock `redis.exceptions.RedisError` on `cache.get`; assert `CacheService.get(key)` returns `None` without raising.
       - `test_get_secure_returns_sentinel_on_redis_failure`: mock `RedisError`; assert `CacheService.get_secure(key) is CACHE_MISS_SENTINEL`.
       - `test_cache_key_tenant_isolation`: `menu_catalog_key('branch-1', '') != menu_catalog_key('branch-2', '')`.
       - `test_invalidation_fires_after_commit`: use `TestCase.assertNumQueries` + a mock on `CacheService.delete`; save a `MenuItem` inside `transaction.atomic()`; assert `delete` called only after commit.

       Depends on: item 5 (caching module).
       Files: `backend/tests/__init__.py`, `backend/tests/test_cache.py`
       Verify: `cd backend && python manage.py test tests.test_cache`

- [ ] 17. **Automated tests — N+1 query prevention**
       Create `backend/tests/test_queries.py`. Use `django.test.TestCase` with `self.assertNumQueries(n)` context manager. Tests:
       - `test_order_list_no_n_plus_1`: create 10 `Order` objects with items; call the order list view via `self.client.get('/api/orders/')`; use `self.assertNumQueries` with a generous-but-bounded limit (≤ 6 queries: auth, orders+related, prefetch items, pagination count).
       - `test_bill_list_no_n_plus_1`: create 10 `Bill` objects; list view; ≤ 5 queries.
       - `test_kitchen_sync_no_n_plus_1`: create 20 `KitchenOrder` objects; call `_get_current_state()` directly; ≤ 4 queries.

       Files: `backend/tests/test_queries.py`
       Verify: `cd backend && python manage.py test tests.test_queries`

- [ ] 18. **Automated tests — concurrency and pagination**
       Create `backend/tests/test_concurrency.py` and `backend/tests/test_pagination.py`.

       `test_concurrency.py` (must use `TransactionTestCase` for real DB isolation):
       - `test_concurrent_payment_no_overpayment`: 2 threads each attempt to pay the same bill for the full amount; assert total paid ≤ `bill.grand_total`.
       - `test_concurrent_inventory_deduction`: 2 threads each deduct 60 from a balance of 100; assert final quantity ≥ 0.

       `test_pagination.py`:
       - `test_max_page_size_capped`: request `/api/orders/?page_size=500`; assert `len(response.data['results']) ≤ 100`.
       - `test_export_too_large_returns_400`: mock the reporting service to return a 15 000-row list; call `ExportCSVView`; assert HTTP 400 with code `EXPORT_TOO_LARGE`.

       Files: `backend/tests/test_concurrency.py`, `backend/tests/test_pagination.py`
       Verify: `cd backend && python manage.py test tests.test_concurrency tests.test_pagination`

- [ ] 19. **Load testing infrastructure**
       Build on existing `performance/` directory. Read `performance/locustfile.py` and `performance/README.md` first.

       Files to create or update:

       | File | Description |
       |---|---|
       | `performance/locustfile.py` | Add/extend with `MenuBrowseUser`, `OrderLifecycleUser`, `KitchenDisplayUser` (WebSocket), `BillingUser`, `PaymentUser`, `InventoryDashboardUser`, `ReportingUser`, `NotificationsUser`, `EnterpriseDashboardUser` user classes. Load JWT credentials from `performance/test_data/users.json`. |
       | `performance/scenarios/pos_checkout.py` | Full POS checkout scenario: login → catalog → order → items → confirm → bill → finalize → payment. |
       | `performance/scenarios/kitchen_ws.py` | 20 concurrent WS connections to `ws://host/ws/kitchen/{branch_id}/`, hold 60 s. |
       | `performance/scenarios/concurrent_payments.py` | 10 concurrent cashiers paying different bills simultaneously. |
       | `performance/scenarios/multi_branch.py` | 5 restaurants × 3 branches = 15 concurrent branch order streams. |
       | `performance/test_data/seed_test_data.py` | Idempotent Django script: 1 Company, 2 Restaurants, 3 Branches each, 50 Menu items, 100 pre-confirmed orders, 20 test users. Writes `users.json`. Header: "STAGING/TEST ONLY". |
       | `performance/README.md` | Update with targets, setup, execution commands, and safety warnings. |

       Verify: `cd frontend && npm run build` (unrelated but good gate); files exist and are syntactically correct Python (`python -m py_compile performance/locustfile.py`).

- [ ] 20. **Enterprise bulk operation review**
       Read `backend/enterprise/rollout_services.py` and `backend/enterprise/services.py`. Find any loops that call `.save()` per record when processing a rollout (applying menu changes to N branches) or staff bulk-assign. If found, refactor to:
       ```python
       BATCH_SIZE = 500
       with transaction.atomic():
           MenuRolloutBranch.objects.bulk_create(batch, batch_size=BATCH_SIZE, ignore_conflicts=False)
       ```
       Update progress tracking to increment per batch, not per record.
       Files: `backend/enterprise/rollout_services.py`, `backend/enterprise/services.py` (edit only if bulk loop issue found)
       Verify: `cd backend && python manage.py test`

- [ ] 21. **Write remaining documentation files**

       | File | Contents |
       |---|---|
       | `docs/database_optimization.md` | Table of indexes added (app, model, fields, query pattern supported); list of select_related/prefetch_related changes (view, what it eliminates); CONN_MAX_AGE rationale; guidelines: use `django-debug-toolbar` in dev, `EXPLAIN ANALYZE` in staging before adding indexes. |
       | `docs/caching_architecture.md` | Cache key schema table; TTL per data category; invalidation trigger table (which model → which cache keys); stampede protection (Redis lock in `get_or_set`); Redis failure behaviour by category; explicit "do NOT cache" list (payments, accounting balances, audit logs). |
       | `docs/load_testing.md` | Load testing setup; performance targets table; how to read Locust output; pre-test checklist (DEBUG=False, Redis running, Celery worker running, DB seeded). |
       | `docs/scalability_guide.md` | CONN_MAX_AGE=60 rationale (Gunicorn sync workers, 1 connection per worker); PgBouncer optional deployment (transaction pooling mode, pgbouncer.ini example); Celery queue layout (default, notifications, maintenance, reports) with startup commands; horizontal scaling guidance (Gunicorn workers = 2×CPU+1; Celery concurrency per queue). |

       Verify: all four files exist at repo root docs/ and each has at least 3 sections.

- [ ] 22. **Final validation and git commit**
       Run all checks in order:
       1. `cd backend && python manage.py check` → must return 0 issues.
       2. `cd backend && python manage.py makemigrations --check` → must return "No changes detected".
       3. `cd backend && python manage.py test` → all tests pass.
       4. `cd frontend && npm run build` → no TypeScript errors.
       5. `cd frontend && npm run lint` → zero warnings.

       Fix any failures before committing.

       Then:
       ```
       git add backend/ frontend/ docs/ performance/
       git commit -m "perf: optimize database caching and application scalability"
       ```
       Do NOT push.
       Verify: `git log --oneline -1` shows the perf: commit on branch `main`.

---

## Digest

### Files touched (by area)

#### Config / settings
| File | Block changed | Test covering it |
|---|---|---|
| `backend/config/settings.py` | `DATABASES['default']` add `CONN_MAX_AGE=60`; `REST_FRAMEWORK` change `DEFAULT_PAGINATION_CLASS`; add `MAX_PAGE_SIZE=100`; add `CELERY_TASK_ROUTES`; add `CELERY_TASK_TIME_LIMIT`; add `'common'` to `LOCAL_APPS` | `python manage.py check` |

#### New app: common/caching
| File | Purpose | Test |
|---|---|---|
| `backend/common/__init__.py` | empty | — |
| `backend/common/apps.py` | AppConfig | manage.py check |
| `backend/common/caching/__init__.py` | empty | — |
| `backend/common/caching/policies.py` | TTL constants, `add_jitter()` | `test_cache.py` |
| `backend/common/caching/keys.py` | tenant-scoped key builders | `test_cache.py::test_cache_key_tenant_isolation` |
| `backend/common/caching/services.py` | `CacheService` class | `test_cache.py` (all 5 tests) |
| `backend/common/caching/invalidation.py` | invalidation functions with `on_commit` | `test_cache.py::test_invalidation_fires_after_commit` |

#### Migrations
| File | Indexes added | Verified clean |
|---|---|---|
| `backend/notifications/migrations/0002_performance_indexes.py` | Notification: source_type/source_id; NotificationRecipient: user+is_read | `makemigrations --check` |
| `backend/enterprise/migrations/0002_performance_indexes.py` | EnterpriseConfiguration: effective_from; StaffBranchAssignment | same |
| `backend/crm/migrations/0002_performance_indexes.py` | Customer: restaurant+is_active | same |
| `backend/marketing/migrations/0002_performance_indexes.py` | Campaign: status+dates | same |
| `backend/menu/migrations/0002_performance_indexes.py` | MenuItemPrice: effective_from; MenuItemBranch: is_available | same |

#### Backend views / services
| File | Change | Test |
|---|---|---|
| `backend/orders/views.py` | `select_related` / `prefetch_related` on all three views | `test_queries.py::test_order_list_no_n_plus_1` |
| `backend/billing/views.py` | `select_related` / `prefetch_related` | `test_queries.py::test_bill_list_no_n_plus_1` |
| `backend/payments/services.py` | `select_for_update()` on Bill lock in `create_payment`; on Payment lock in `process_refund` | `test_concurrency.py::test_concurrent_payment_no_overpayment` |
| `backend/billing/services.py` | `select_for_update()` on Bill in `finalize_bill` | `test_concurrency.py` |
| `backend/inventory/services.py` | `select_for_update()` on StockBalance in deduct and transfer | `test_concurrency.py::test_concurrent_inventory_deduction` |
| `backend/accounts/access.py` | permissions cache via `get_secure` | `test_cache.py::test_get_secure_returns_sentinel_on_redis_failure` |
| `backend/menu/views.py` | menu catalog cache read/set | `test_cache.py` |
| `backend/reporting/services.py` | migrate raw `cache.*` to `CacheService.*` | `python manage.py test` |
| `backend/reporting/dashboard_services.py` | dashboard KPI cache + DB aggregation verification | `python manage.py test` |
| `backend/reporting/views.py` | `MAX_EXPORT_ROWS` enforcement | `test_pagination.py::test_export_too_large_returns_400` |
| `backend/notifications/views.py` | `select_related` | `python manage.py test` |
| `backend/enterprise/views.py` | `select_related` | `python manage.py test` |
| `backend/notifications/tasks.py` | `time_limit` on tasks | `python manage.py check` |
| `backend/crm/tasks.py` | `time_limit` on tasks | `python manage.py check` |
| `backend/marketing/tasks.py` | `time_limit` on tasks | `python manage.py check` |
| `backend/enterprise/rollout_services.py` | `bulk_create` with batch_size=500 (if single-save loop found) | `python manage.py test` |

#### Signal / apps files
| File | Change | Test |
|---|---|---|
| `backend/menu/signals.py` | post_save MenuItem/Price/Branch → `invalidate_menu_catalog` | `test_cache.py::test_invalidation_fires_after_commit` |
| `backend/enterprise/signals.py` | post_save EnterpriseConfiguration → `invalidate_branch_config` | `python manage.py test` |
| `backend/accounts/signals.py` | post_save UserRoleAssignment → `invalidate_user_permissions` | `python manage.py test` |
| `backend/inventory/signals.py` | post_save StockBalance → `invalidate_inventory_availability` | `python manage.py test` |
| `backend/menu/apps.py` | `ready()` imports signals | `python manage.py check` |
| `backend/enterprise/apps.py` | `ready()` imports signals | same |
| `backend/accounts/apps.py` | `ready()` imports signals | same |
| `backend/inventory/apps.py` | `ready()` imports signals | same |

#### Pagination
| File | Change | Test |
|---|---|---|
| `backend/core/pagination.py` | `SafePageNumberPagination` with `max_page_size=100` | `test_pagination.py::test_max_page_size_capped` |
| `backend/reporting/constants.py` | `MAX_EXPORT_ROWS = 10000` | `test_pagination.py::test_export_too_large_returns_400` |

#### Frontend
| File | Change | Test |
|---|---|---|
| `frontend/src/App.tsx` | React.lazy + Suspense for all non-core pages | `npm run build` |
| `frontend/vite.config.ts` | `manualChunks` vendor splitting | `npm run build` |
| `frontend/src/main.tsx` | QueryClient `staleTime=30000, refetchOnWindowFocus=false` | `npm run build` |
| `frontend/src/hooks/useDebounce.ts` | debounce hook | `npm run lint` |
| `frontend/src/pages/menu/MenuItems.tsx` | use `useDebounce` on search | `npm run lint` |
| `frontend/src/pages/inventory/InventoryItemsPage.tsx` | use `useDebounce` | `npm run lint` |
| `frontend/src/pages/crm/CustomerListPage.tsx` | use `useDebounce` | `npm run lint` |
| `frontend/src/pages/orders/OrderListPage.tsx` | use `useDebounce` + skeleton | `npm run lint` |
| `frontend/src/components/ui/Skeleton.tsx` | new Skeleton component | `npm run build` |
| `frontend/src/components/kitchen/KitchenOrderCard.tsx` | `React.memo` | `npm run lint` |
| `frontend/src/components/orders/MenuItemCard.tsx` | `React.memo` | `npm run lint` |
| `frontend/src/components/notifications/NotificationBell.tsx` | `React.memo` | `npm run lint` |
| `frontend/src/components/ui/StatCard.tsx` | `React.memo` | `npm run lint` |
| `frontend/src/components/billing/BillItemsTable.tsx` | `React.memo` | `npm run lint` |
| `frontend/src/pages/kitchen/KitchenDashboard.tsx` | loading skeleton | `npm run lint` |
| `frontend/src/pages/billing/BillListPage.tsx` | loading skeleton | `npm run lint` |

#### Tests
| File | What it tests |
|---|---|
| `backend/tests/__init__.py` | empty marker |
| `backend/tests/test_cache.py` | CacheService get/set/delete, Redis failure fallback, sentinel, tenant isolation, on_commit invalidation |
| `backend/tests/test_queries.py` | N+1 prevention on order/bill/kitchen views via `assertNumQueries` |
| `backend/tests/test_concurrency.py` | Concurrent payment no-overpayment, concurrent inventory deduction safety |
| `backend/tests/test_pagination.py` | Max page size enforcement, export row cap HTTP 400 |

#### Documentation (repo root docs/)
| File | Contents |
|---|---|
| `docs/performance_assessment_phase22.md` | Audit findings — N+1, missing indexes, caching gaps, frontend bundle, WebSocket scoping |
| `docs/database_optimization.md` | Indexes added, select_related changes, CONN_MAX_AGE, query review guidelines |
| `docs/caching_architecture.md` | Key schema, TTL table, invalidation map, stampede protection, Redis failure policy |
| `docs/load_testing.md` | Setup, targets, measurement guide, pre-test checklist |
| `docs/scalability_guide.md` | CONN_MAX_AGE, PgBouncer, Celery queues, horizontal scaling |

#### Performance scripts
| File | Purpose |
|---|---|
| `performance/locustfile.py` | 9 Locust user classes |
| `performance/scenarios/pos_checkout.py` | Full POS checkout scenario |
| `performance/scenarios/kitchen_ws.py` | WS load scenario |
| `performance/scenarios/concurrent_payments.py` | Concurrent payment scenario |
| `performance/scenarios/multi_branch.py` | Multi-branch simulation |
| `performance/test_data/seed_test_data.py` | Idempotent test data seeder |
| `performance/README.md` | Execution guide |

---

### Build and test commands verified during exploration

| Command | Expected result |
|---|---|
| `cd backend && python manage.py check` | 0 issues |
| `cd backend && python manage.py makemigrations --check` | "No changes detected" |
| `cd backend && python manage.py test` | All tests pass |
| `cd frontend && npm run build` | No TypeScript errors; bundles written to dist/ |
| `cd frontend && npm run lint` | 0 warnings |

### What was confirmed in the codebase during exploration

- `backend/` is the Django project root; `manage.py` is at `backend/manage.py`.
- `CACHES` already configured with `django.core.cache.backends.redis.RedisCache` in `settings.py`.
- `CELERY_BEAT_SCHEDULE` exists; tasks in `notifications`, `crm`, `marketing` only — no Celery tasks in `orders`, `billing`, `payments`, `inventory`, `kitchen`.
- `reporting/services.py` already uses `django.core.cache` with `CACHE_TTL_*` constants but uses raw `cache.get/set` — will be migrated to `CacheService`.
- All three WebSocket consumers (`KitchenConsumer`, `CentralControlConsumer`, `NotificationsConsumer`) already correctly scope groups by branch/org/user and validate access server-side.
- `KitchenConsumer._get_current_state()` already uses `select_related` and `prefetch_related` — no change needed in consumer.
- `Order`, `Bill`, `Payment`, `BillItem`, `KitchenOrder`, `StockMovement` models already have many indexes in `Meta.indexes`; migration files will only add the genuinely missing ones.
- Frontend uses TanStack Query v5 (`@tanstack/react-query ^5.59.0`); no `react-window` or `react-virtual` present — do not add them.
- Global `PAGE_SIZE=20` and `DEFAULT_PAGINATION_CLASS=PageNumberPagination` are already set; `MAX_PAGE_SIZE` is not currently set.
- `CONN_MAX_AGE` is not currently in `DATABASES['default']`.
- `performance/` directory exists with `scenarios/`, `test_data/`, `README.md` already present.
