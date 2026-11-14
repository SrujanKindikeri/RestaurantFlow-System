# Implementation Plan — Phase 22: Performance, Caching & Scalability

> **Working directory:** `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System`
> **Backend root:** `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\backend`
> **Frontend root:** `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\frontend`
> **Test command:** `cd backend && python manage.py test --settings=config.test_settings`
> **Build check:** `cd backend && python manage.py check`
> **Frontend build:** `cd frontend && npm run build`

---

## FEAT-001 — Database Optimization (indexes + N+1 fixes)

- [ ] 1. **Add missing composite indexes to four models.**
      In `backend/orders/models.py` → `Order.Meta.indexes`: add `models.Index(fields=["branch", "status", "created_at"], name="order_branch_status_created_at")`.
      In `backend/financials/models.py` → `Expense.Meta.indexes`: add `models.Index(fields=["branch", "status", "expense_date"], name="expense_branch_status_date")`.
      In `backend/notifications/models.py` → `Notification.Meta.indexes`: add `models.Index(fields=["company", "branch", "source_type", "source_id", "notification_type"], name="notif_idempotency_check")`.
      In `backend/menu/models.py` → `MenuItem.Meta.indexes`: add `models.Index(fields=["restaurant", "is_active", "display_order"], name="menuitem_catalog_order")`.
      Files: `backend/orders/models.py`, `backend/financials/models.py`, `backend/notifications/models.py`, `backend/menu/models.py`
      Verify: `cd backend && python manage.py makemigrations orders financials notifications menu --name=phase22_add_composite_indexes --settings=config.settings` — confirm generated files contain only `AddIndex` operations.

- [ ] 2. **Generate and validate migrations.**
      Run makemigrations for the four apps modified above. Open each generated file and confirm only `migrations.AddIndex(...)` operations are present — no `AlterField`, no `RunSQL`.
      Files: new migration files under `backend/orders/migrations/`, `backend/financials/migrations/`, `backend/notifications/migrations/`, `backend/menu/migrations/`
      Verify: `cd backend && python manage.py makemigrations --check --settings=config.settings` → exits 0.

- [ ] 3. **Fix N+1 on DiningTable list view.**
      In `backend/orders/views.py`, locate `DiningTableListCreateView.get_queryset()`. Add `.prefetch_related("sessions")` to the returned queryset so that `is_occupied` and `active_session_id` `SerializerMethodField` calls on `DiningTableListSerializer` iterate in-memory rather than issuing one query per row.
      Files: `backend/orders/views.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings tests.test_queries` — `OrderListQueryTest` passes; query count does not regress.

- [ ] 4. **Fix N+1 on Order list — replace item_count SerializerMethodField with annotation.**
      In `backend/orders/views.py`, in `OrderListView.get_queryset()`, add `.annotate(item_count=Count("items"))` (import `Count` from `django.db.models`).
      In `backend/orders/serializers.py`, change `item_count = serializers.SerializerMethodField()` and its `get_item_count` method to `item_count = serializers.IntegerField(read_only=True)`.
      Files: `backend/orders/views.py`, `backend/orders/serializers.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings orders` — all order tests pass.

- [ ] 5. **Fix N+1 on Menu item list — prefetch prices and branch availability.**
      In `backend/menu/views.py`, in the `MenuItem` list view's `get_queryset()`, add `.prefetch_related("prices", "branches")` (or the correct related name for `MenuItemBranch`) so that `active_prices` and `branch_availability` SerializerMethodField calls on `MenuItemSerializer` iterate the prefetched cache.
      Files: `backend/menu/views.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings menu` — all menu tests pass.

- [ ] 6. **Write `docs/database_optimization.md`.**
      Document: (a) all four composite indexes added with the query pattern each serves, (b) the three N+1 fixes made, (c) the existing `select_for_update()` concurrency guards in `orders/services.py`, `billing/services.py`, `payments/services.py`, `inventory/services.py` — confirm concurrent payment cannot overpay a bill and concurrent inventory deduction cannot go negative (both rely on row-level locks already in place).
      Files: `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\docs\database_optimization.md`
      Verify: file exists and is non-empty.

---

## FEAT-002 — Redis Caching Integration

- [ ] 7. **Wire menu catalog cache into the POS catalog endpoint.**
      In `backend/menu/views.py`, find the view serving the POS item catalog (the one that returns `MenuItem + MenuItemBranch + MenuItemPrice` filtered by `branch`). Wrap the ORM fetch in `CacheService.get_or_set(key, callable, ttl)`. Key: `menu_catalog_key(branch_id, make_params_hash(**request.query_params))`. TTL: `MENU_CATALOG_TTL` (300s). Import from `common.caching.services`, `common.caching.keys`, `common.caching.policies`.
      Files: `backend/menu/views.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings tests.test_cache` — existing `CacheHitMissTest` and `RedisFailureFallbackTest` pass.

- [ ] 8. **Wire cache invalidation into menu service write paths.**
      In `backend/menu/services.py` (or the equivalent file where menu items and prices are created/updated/deactivated), after every mutating operation that changes what the catalog endpoint returns, add `invalidate_menu_catalog(branch_id)` from `common.caching.invalidation`. This call must happen inside (or be deferred via `transaction.on_commit()` from within) the same `transaction.atomic()` block already present. The `invalidate_menu_catalog` function already wraps in `transaction.on_commit()` internally.
      Files: `backend/menu/services.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings tests.test_cache` — `InvalidationOnCommitTest` passes.

- [ ] 9. **Wire reporting summary cache into selectors.**
      In `backend/reporting/selectors.py`, in `select_sales_summary()` and any other selector that runs aggregations over `billing.Bill`/`BillItem`, wrap the aggregation call in `CacheService.get_or_set(key, callable, ttl)`. Key: `reporting_key(report_type="sales_summary", scope_hash=make_params_hash(restaurant_id, branch_id), date_from=str(date_from), date_to=str(date_to))`. TTL: `REPORTING_SUMMARY_TTL` (300s). Do NOT wrap payment aggregate calls.
      Files: `backend/reporting/selectors.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings reporting` — all reporting tests pass.

- [ ] 10. **Wire dashboard KPI cache and add invalidation in `finalize_bill`.**
      In the view or selector that returns branch-level KPI summary, wrap in `CacheService.get_or_set()` using `dashboard_kpi_key(user_id, restaurant_id, branch_id, date_str)` and `DASHBOARD_KPI_TTL` (120s).
      In `backend/billing/services.py`, inside `finalize_bill()`, after the bill status update, add `invalidate_dashboard_kpis(restaurant_id, branch_id)` from `common.caching.invalidation` (already wraps in `transaction.on_commit()`).
      Files: `backend/billing/services.py`, plus the KPI view or selector file
      Verify: `cd backend && python manage.py test --settings=config.test_settings billing` — all billing tests pass.

- [ ] 11. **Wire branch config cache into enterprise configuration reads.**
      In `backend/enterprise/` (specifically the view or selector that reads `EnterpriseConfiguration` for a branch), wrap the config read in `CacheService.get_or_set()` using `branch_config_key(branch_id, config_key)` and `BRANCH_CONFIG_TTL` (600s). In the service that saves a branch configuration update, add `invalidate_branch_config(branch_id)` on_commit.
      Files: `backend/enterprise/branch_services.py` (or equivalent), and the enterprise config read path
      Verify: `cd backend && python manage.py test --settings=config.test_settings enterprise` — all enterprise tests pass.

- [ ] 12. **Confirm payments and accounting are never cached.**
      Grep `backend/payments/views.py`, `backend/payments/services.py`, `backend/accounting/views.py` for any `CacheService` import or call. If found, remove it. Document the explicit no-cache policy in a comment.
      Files: none (audit only, remove if found)
      Verify: `cd backend && python manage.py test --settings=config.test_settings payments accounting` — all tests pass.

- [ ] 13. **Write `docs/caching_architecture.md`.**
      Cover: key schema table, TTL table, endpoint cache map, invalidation trigger map (service function → invalidation function), Redis failure behavior (fallback to DB for reads, CACHE_MISS_SENTINEL for auth-sensitive paths), stampede protection (lock-based `get_or_set`), no-cache list (payments, accounting, audit).
      Files: `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\docs\caching_architecture.md`
      Verify: file exists.

---

## FEAT-003 — Frontend Performance

- [ ] 14. **Extend Vite code splitting with feature chunks.**
      In `frontend/vite.config.ts`, change `manualChunks` from a plain object to a function: `(id) => { if (id.includes('lucide-react')) return 'vendor-ui'; if (id.includes('/pages/kitchen/')) return 'feature-kitchen'; if (id.includes('/pages/operations/')) return 'feature-pos'; if (id.includes('/pages/reports/') || id.includes('/pages/accounting/') || id.includes('/pages/financials/')) return 'feature-reports'; if (id.includes('vendor-react') || ...) return 'vendor-react'; ... }`. Keep the existing three vendor chunks. Add `vendor-ui` for lucide-react.
      Files: `frontend/vite.config.ts`
      Verify: `cd frontend && npm run build` — build output shows `feature-kitchen-*.js`, `feature-pos-*.js`, `feature-reports-*.js`, `vendor-ui-*.js` chunk files.

- [ ] 15. **Add useDebounce to remaining search inputs.**
      Pages that have search inputs but do not yet use `useDebounce`: `frontend/src/pages/billing/BillListPage.tsx`, `frontend/src/pages/payments/PaymentHistoryPage.tsx`, `frontend/src/pages/kitchen/KitchenHistory.tsx`, `frontend/src/pages/inventory/StockHistoryPage.tsx`. For each: import `useDebounce` from `@/hooks/useDebounce`, create `const debouncedSearch = useDebounce(searchInput, 300)`, use `debouncedSearch` in the query object.
      Files: the four page files listed above
      Verify: `cd frontend && npm run lint` — no unused-variable warnings; `npm run build` succeeds.

- [ ] 16. **Add AbortController to custom API hooks.**
      In `frontend/src/hooks/useOrders.ts`, `useMenu.ts`, `useReporting.ts`, `useKitchen.ts`, `useNotifications.ts`: for hooks using `useQuery` from TanStack Query, destructure `signal` from the `queryFn` context argument and pass `{ signal }` to the axios call. For hooks using plain `useEffect`, add `const controller = new AbortController()` and `return () => controller.abort()`.
      Files: `frontend/src/hooks/useOrders.ts`, `useMenu.ts`, `useReporting.ts`, `useKitchen.ts`, `useNotifications.ts`
      Verify: `cd frontend && npm run build` succeeds; `npm run lint` exits 0.

- [ ] 17. **Add loading skeleton components and apply them.**
      Create `frontend/src/components/ui/SkeletonCard.tsx` — pulsing placeholder matching StatCard dimensions using Tailwind `animate-pulse`. Create `frontend/src/components/ui/SkeletonTable.tsx` — renders N placeholder rows.
      In `frontend/src/pages/DashboardPage.tsx`, render `<SkeletonCard />` × 4 while KPI query `isLoading === true`.
      In `frontend/src/pages/orders/OrderListPage.tsx` and `frontend/src/pages/billing/BillListPage.tsx`, render `<SkeletonTable rows={5} />` while list query `isLoading === true`.
      Files: `frontend/src/components/ui/SkeletonCard.tsx`, `frontend/src/components/ui/SkeletonTable.tsx`, `frontend/src/pages/DashboardPage.tsx`, `frontend/src/pages/orders/OrderListPage.tsx`, `frontend/src/pages/billing/BillListPage.tsx`
      Verify: `cd frontend && npm run build && npm run lint` both exit 0.

- [ ] 18. **Write `docs/frontend_performance.md`.**
      Cover: chunk split strategy and rationale, React.memo usage (which components, why), debounce usage map, AbortController pattern, skeleton component usage.
      Files: `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\docs\frontend_performance.md`
      Verify: file exists.

---

## FEAT-004 — Tests

- [ ] 19. **Create `backend/tests/test_performance/` and move test content.**
      Create `backend/tests/test_performance/__init__.py`. Copy content of `backend/tests/test_queries.py` → `test_query_counts.py`. Copy `test_cache.py` → same name. Copy `test_concurrency.py` → same name. Copy `test_pagination.py` → same name. Keep originals in place.
      Files: `backend/tests/test_performance/__init__.py`, `test_query_counts.py`, `test_cache.py`, `test_concurrency.py`, `test_pagination.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings tests.test_performance` — all copied tests pass.

- [ ] 20. **Add `MenuCatalogQueryTest` and `DashboardKPIQueryTest` to `test_query_counts.py`.**
      `MenuCatalogQueryTest`: creates 10 `MenuItem` rows with active prices for a branch, GETs the menu catalog endpoint, asserts `self.assertNumQueries(upper_bound)` with bound = 5 (catches N+1 regression). `DashboardKPIQueryTest`: calls the KPI endpoint twice; uses `unittest.mock.patch` to simulate a cache hit on the second call and asserts ≤ 1 DB query.
      Files: `backend/tests/test_performance/test_query_counts.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings tests.test_performance.test_query_counts` passes.

- [ ] 21. **Add `CacheInvalidationIntegrationTest` to `test_cache.py`.**
      `TransactionTestCase` subclass: set a cache key for a menu catalog key, call `invalidate_menu_catalog(branch_id)`, then assert the key returns `None` after commit. This confirms the `transaction.on_commit()` hook fires in the test database.
      Files: `backend/tests/test_performance/test_cache.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings tests.test_performance.test_cache` passes.

- [ ] 22. **Add `ConcurrentInventoryDeductionTest` and `ConcurrentStockTransferTest` to `test_concurrency.py`.**
      Both are `TransactionTestCase` subclasses using `threading.Thread`. Setup creates a `StockBalance` with quantity=100 at a storage location. `ConcurrentInventoryDeductionTest`: two threads each attempt to deduct 60 units; assert the resulting balance ≥ 0 and total deducted ≤ 100. `ConcurrentStockTransferTest`: two threads each initiate a transfer of 60 units from the same source; assert total transferred ≤ 100.
      Files: `backend/tests/test_performance/test_concurrency.py`
      Verify: `cd backend && python manage.py test --settings=config.test_settings tests.test_performance.test_concurrency` passes.

- [ ] 23. **Build Locust load testing infrastructure.**
      Create `performance/locustfile.py` with `RestaurantFlowUser(HttpUser)` class, `wait_time = between(1, 3)`, tasks: `@task(1)` login, `@task(10)` menu catalog GET, `@task(5)` order creation POST, `@task(5)` order confirm POST, `@task(4)` bill finalize POST, `@task(3)` payment POST, `@task(3)` inventory dashboard GET, `@task(2)` reporting GET. Reads `LOCUST_HOST`, `LOCUST_BRANCH_ID`, `LOCUST_USERNAME`, `LOCUST_PASSWORD` from environment.
      Create `performance/scenarios/login.py`, `menu_catalog.py`, `order_flow.py`, `inventory_check.py`, `reporting.py` — each defines a `TaskSet`.
      Create `performance/test_data/seed.py` — script callable via `python performance/test_data/seed.py` from the backend directory, creating minimal fixtures and printing their IDs.
      Create `performance/README.md` with setup instructions, seed command, start command, and target metrics.
      Create `docs/load_testing.md` as a copy of `performance/README.md` plus interpretation notes.
      Files: `performance/locustfile.py`, `performance/scenarios/*.py`, `performance/test_data/seed.py`, `performance/README.md`, `docs/load_testing.md`
      Verify: `python -c "import ast; ast.parse(open('performance/locustfile.py').read()); print('OK')"` from the workspace root exits with `OK`.

---

## FEAT-005 — Scalability Docs, Validation & Commit

- [ ] 24. **Write `docs/scalability_guide.md`.**
      Eight sections: DB connection management (CONN_MAX_AGE, PgBouncer note), Gunicorn worker config, Celery concurrency (separate workers per queue), Redis memory config (maxmemory + allkeys-lru + DB separation for channels vs cache), container resource limits, Nginx config sketch (upstream, proxy_pass, gzip), known bottlenecks list from the performance assessment, scaling milestones (0-10 / 10-50 / 50-200 branches).
      Files: `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\docs\scalability_guide.md`
      Verify: file exists.

- [ ] 25. **Update `docker-compose.yml` with resource limits and a Celery worker service.**
      Add `mem_limit: 512m` to `postgres`. Add `mem_limit: 256m` to `redis` and append `--maxmemory 200mb --maxmemory-policy allkeys-lru` to its command. Add a `celery_worker` service: image same as app, `command: celery -A config worker -l info -c 4 -Q default,notifications,maintenance`, depends_on `[postgres, redis]`, `env_file: .env`.
      Files: `c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System\docker-compose.yml`
      Verify: `docker-compose config` from the workspace root exits 0 (validates YAML syntax). If docker is not available, validate YAML with Python: `python -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"`.

- [ ] 26. **Full backend validation.**
      Run in order:
      1. `cd backend && python manage.py check --settings=config.settings`
      2. `cd backend && python manage.py makemigrations --check --settings=config.settings`
      3. `cd backend && python manage.py test --settings=config.test_settings`
      Fix any failures before proceeding to item 27.
      Files: (fix whatever the commands identify)
      Verify: all three commands exit 0.

- [ ] 27. **Full frontend validation.**
      Run:
      1. `cd frontend && npm run build`
      2. `cd frontend && npm run lint`
      Fix any TypeScript or lint errors before proceeding to item 28.
      Files: (fix whatever the commands identify)
      Verify: both commands exit 0.

- [ ] 28. **Write `final_report.md` and commit.**
      Write `.agents/tasks/phase22-performance/final_report.md` covering: summary of all changes by FEAT, files created/modified, test results, any deviations from the plan.
      Then: `git -C c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System add .` then `git -C c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System commit -m "perf: optimize database caching and application scalability"`.
      Do NOT push.
      Files: `.agents/tasks/phase22-performance/final_report.md`
      Verify: `git -C c:\Users\kindi\OneDrive\Documents\RestaurantFlow-System log -1 --oneline` shows the commit message.

---

## Digest

| File | Block to change | Test covering it | Verified today |
|---|---|---|---|
| `backend/orders/models.py` | `Order.Meta.indexes` — add composite `(branch, status, created_at)` | `tests.test_queries.OrderListQueryTest` | Indexes confirmed from code read |
| `backend/financials/models.py` | `Expense.Meta.indexes` — add `(branch, status, expense_date)` | `financials` test suite | Missing index confirmed from code read |
| `backend/notifications/models.py` | `Notification.Meta.indexes` — add idempotency composite | `notifications` test suite | Missing index confirmed from code read |
| `backend/menu/models.py` | `MenuItem.Meta.indexes` — add `(restaurant, is_active, display_order)` | `menu` test suite | Missing index confirmed from code read |
| `backend/orders/views.py` | `DiningTableListCreateView.get_queryset()` — add `.prefetch_related("sessions")`; `OrderListView.get_queryset()` — add `.annotate(item_count=Count("items"))` | `tests.test_queries` | N+1 patterns confirmed from serializer read |
| `backend/orders/serializers.py` | `item_count` field — change from `SerializerMethodField` to `IntegerField(read_only=True)` | `tests.test_queries` | Pattern confirmed |
| `backend/menu/views.py` | MenuItem list `get_queryset()` — add `prefetch_related("prices", "branches")`; wrap catalog response in `CacheService.get_or_set()` | `tests.test_cache`, `menu` tests | Confirmed no prefetch in current code |
| `backend/menu/services.py` | Write paths — add `invalidate_menu_catalog(branch_id)` after mutations | `tests.test_cache.InvalidationOnCommitTest` | Cache infrastructure confirmed ready |
| `backend/billing/services.py` | `finalize_bill()` — add `invalidate_dashboard_kpis(restaurant_id, branch_id)` on_commit | `billing` tests | `select_for_update()` already in place |
| `backend/reporting/selectors.py` | `select_sales_summary()` and other aggregation selectors — wrap in `CacheService.get_or_set()` | `reporting` tests | Aggregation pattern confirmed |
| `backend/enterprise/branch_services.py` | Config write path — add `invalidate_branch_config(branch_id)` on_commit | `enterprise` tests | Config model confirmed |
| `frontend/vite.config.ts` | `manualChunks` — convert to function, add `vendor-ui`, `feature-kitchen`, `feature-pos`, `feature-reports` | `npm run build` output | Current 3-chunk config confirmed |
| `frontend/src/hooks/useOrders.ts` et al. | Add `signal` from queryFn context to axios calls | `npm run build` | Confirmed no AbortController in hooks |
| `frontend/src/pages/billing/BillListPage.tsx` et al. | Add `useDebounce` to search inputs | `npm run lint` | 3 pages already have it; 4+ do not |
| `frontend/src/components/ui/SkeletonCard.tsx` | New file | `npm run build` | Does not exist yet |
| `frontend/src/components/ui/SkeletonTable.tsx` | New file | `npm run build` | Does not exist yet |
| `docker-compose.yml` | Add `mem_limit`, `maxmemory` to redis, add `celery_worker` service | `python -c "import yaml..."` | Current file confirmed: no limits, no worker |
| `performance/locustfile.py` | New file | `ast.parse(...)` syntax check | Does not exist yet |
| `docs/database_optimization.md` | New file | existence check | Does not exist yet |
| `docs/caching_architecture.md` | New file | existence check | Does not exist yet |
| `docs/frontend_performance.md` | New file | existence check | Does not exist yet |
| `docs/load_testing.md` | New file | existence check | Does not exist yet |
| `docs/scalability_guide.md` | New file | existence check | Does not exist yet |

**Build command (backend):** `cd backend && python manage.py check --settings=config.settings`
**Test command (backend):** `cd backend && python manage.py test --settings=config.test_settings`
**Test command (performance suite):** `cd backend && python manage.py test --settings=config.test_settings tests.test_performance`
**Build command (frontend):** `cd frontend && npm run build`
**Lint command (frontend):** `cd frontend && npm run lint`
