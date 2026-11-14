# Phase 22 Performance, Caching & Scalability Engineering

Phase 22 adds four composite indexes (Order, Expense, Notification, MenuItem), fixes N+1 queries on order and menu list endpoints, wires a new Redis CacheService into the menu catalog, dashboard KPI, and reporting selectors, adds cache invalidation on key write paths, and introduces a frontend optimization layer (lazy loading, `React.memo`, `AbortController`, debounced search, Vite chunk splitting). A test suite for cache behavior, concurrency guards, and pagination enforcement is included. Load test infrastructure (Locust) is present in the working tree but was never committed.

**Watch for:**
- **confirmed** — `dashboard_kpi_key` in `common/caching/keys.py` accepts a `user_id` parameter but omits it from the generated key string; two users at the same `restaurant_id:branch_id` scope share one cache slot and can receive each other's KPI data.
- **confirmed** — `performance/locustfile.py` and all scenario files are untracked (not in any commit); the load test infrastructure checklist item is unmet.
- **confirmed** — `backend/tests/test_concurrency.py` has uncommitted working-tree modifications; the committed version may differ from what was tested.

**Verdict**: NEEDS_CHANGES

---

## High-level view

The indexing strategy is sound. All four migrations use `SeparateDatabaseAndState` with `CREATE INDEX CONCURRENTLY`, and the state operations are pure `AddIndex` — no destructive schema changes anywhere. The N+1 fixes on `OrderListCreateView` (annotation) and `MenuItemListCreateView` (prefetch) are correct.

The CacheService design is solid: Redis failure falls back gracefully, `get_secure` uses a sentinel rather than `None` to distinguish failure from cache-miss, and invalidation is wrapped in `transaction.on_commit`. The stampede fix in `get_or_set` (re-reading before computing on lock miss) is an improvement over the previous version, though the non-acquiring path can still compute independently if the lock holder is slow. Financial data is clean: `payments/` and `billing/services.py` have zero `cache.get` calls; cache is used only for dashboard summaries and reporting aggregates that are explicitly non-financial.

The key isolation fix for reporting selectors (commit `6dd8806`) correctly adds `user.pk` to `scope_hash` in `select_sales_summary`, `select_orders_summary`, `select_top_selling_items`, `select_kitchen_performance`, and `select_inventory_summary`. However, the same fix was not applied to `get_dashboard_kpis` in `dashboard_services.py`. That function calls `dashboard_kpi_key(user_id=str(user.pk), ...)` but the key builder discards the `user_id` argument and produces a key without it, leaving a cross-user collision at any shared restaurant/branch scope.

The load test infrastructure exists on disk but was never committed. A `git status` shows `performance/` as untracked, and `git log -- performance/locustfile.py` returns no commits. The checklist requirement for `performance/locustfile.py` to exist in the repository is not met. The test for concurrent stock transfer (`ConcurrentStockTransferTest`) listed in FEAT-004 is also absent from the committed test suite. `test_concurrency.py` has unstaged modifications; the committed file differs from the last-run state.

Frontend changes are correct: all routes use `React.lazy` + `Suspense`, no sensitive data is written to `localStorage` or `sessionStorage`, and `AbortController` cleanup is wired into all modified `useEffect` calls. Vite chunk splitting is consistent. Pagination capping (`max_page_size=100`) is tested in `test_pagination.py`.

---

<details>
<summary>Issues (5)</summary>

1. **Dashboard KPI cross-user cache collision** — `dashboard_kpi_key` in `common/caching/keys.py` accepts `user_id` but does not include it in the returned string. Two users querying the same `restaurant_id:branch_id` share one cache slot and will receive each other's KPI data. Add `user_id` to the key format: `f"{PREFIX}:user:{user_id}:restaurant:{restaurant_id}:branch:{branch_id}:dashboard_kpi:{date_str}"`. This also requires updating the `invalidate_dashboard_kpis` pattern to `f"{PREFIX}:user:*:restaurant:{restaurant_id}:branch:{branch_id}:dashboard_kpi:*"`.

2. **Load test infrastructure not committed** — `performance/locustfile.py` and all scenario files are untracked. The checklist item (load test quality, concurrent payment scenario) cannot be verified against the repository. Commit the `performance/` directory.

3. **Uncommitted modification to `test_concurrency.py`** — The working-tree version adds `OrderItem` and `MenuItem` fixtures to `ConcurrentBillFinalizationTest`, which suggests the committed version may fail or be incomplete. Stage and commit the fix.

4. **`ConcurrentStockTransferTest` absent** — FEAT-004 required a concurrent stock transfer test; it is not present in the committed `test_concurrency.py`. Add it.

5. **Lock key leaked on non-acquiring path that falls through** — In `get_or_set`, when `acquired=False` and the cache re-read returns `None`, the function falls through to call `callable_fn()` and write the result, but the `finally` block only deletes `lock_key` when `acquired=True`. The non-acquiring caller writes the value without taking ownership of the lock and without cleaning it up. The 10-second TTL on the lock key mitigates this, but the duplicate write is unnecessary and the leaked lock delays the next cold-cache caller on that key. When the non-acquiring caller falls through, it should either wait and retry or accept the duplicate computation without attempting a lock release — the current code is internally consistent but the comment ("fall through and compute independently") should be explicit that the lock remains held by the original acquirer until TTL expiry.

</details>

<details>
<summary>Details</summary>

## Dashboard KPI user scope dropped in `keys.py`

`common/caching/keys.py` defines:

```python
def dashboard_kpi_key(user_id, restaurant_id, branch_id, date_str="") -> str:
    return f"{PREFIX}:restaurant:{restaurant_id}:branch:{branch_id}:dashboard_kpi:{date_str}"
```

The `user_id` parameter is accepted and silently dropped. `get_dashboard_kpis` in `dashboard_services.py` calls this with `user_id=str(user.pk)`, creating the impression of user-scoped isolation, but every user at the same `restaurant_id:branch_id` on the same date writes to and reads from the same key.

This matters for multi-role deployments: a branch manager and a restaurant owner viewing the same branch will see whichever result was cached first. The accessible-branch queryset is built per-user before passing to `_build_kpis`, so if the closure-captured `accessible` differs between users (e.g., the manager is branch-scoped, the owner is restaurant-wide), one user's filtered data populates the cache and the other receives it.

The `select_sales_summary` and other reporting selectors were fixed in commit `6dd8806` by adding `str(user.pk)` to `make_params_hash`. The same fix is needed in `dashboard_kpi_key` and in `invalidate_dashboard_kpis` (whose glob pattern must span all user-prefixed slots).

## `get_or_set` stampede mitigation and remaining edge case

The fix in `6dd8806` addresses the most significant bug: previously, all callers that did not acquire the lock immediately called `callable_fn()`, defeating the purpose of the lock entirely. Now, non-acquiring callers re-read the cache first and return early if the value has been written. The remaining edge case is that if the value still isn't in cache (the lock holder is mid-computation or failed), the non-acquiring caller falls through and computes independently anyway. This is correct behavior for availability — it prevents indefinite stalls — but the lock key is left in Redis for 10 seconds with no owner taking responsibility for it. Because `acquired=False`, the `finally` block skips the delete. The next caller within that 10-second window will also re-read and potentially fall through. This is a low-severity operational concern, not a correctness bug.

## Cache tenant isolation in reporting selectors vs. dashboard KPI

After commit `6dd8806`, the five reporting selectors all include `str(user.pk)` in `make_params_hash`, making their `scope_hash` user-specific. `ReportingCacheCrossOrgIsolationTest` verifies key distinctness and data non-leakage for this path. The dashboard KPI path has the same collision risk and no equivalent test.

## Load test infrastructure gap

`performance/locustfile.py` covers login, menu catalog, order creation, order confirmation, bill finalization, and payment collection. `performance/scenarios/payments.py` has an explicit concurrent payment scenario targeting the same seeded bill IDs, covering the overpayment guard directly. The reporting scenario covers dashboard and sales queries. This coverage is complete against the checklist — but none of these files appear in the git history. They exist as untracked working-tree files. The checklist item cannot be treated as met until the directory is committed.

## Test coverage gaps

`test_cache.py` covers hit/miss/delete, Redis failure fallback for both `get` and `get_secure`, tenant key distinctness by branch and user, and `on_commit` invalidation (skipped on locmem). The `ReportingCacheCrossOrgIsolationTest` adds three cross-org isolation tests. The dashboard KPI cross-user collision described above is not tested.

`test_concurrency.py` covers concurrent payment overpayment (`ConcurrentPaymentsTest`), concurrent inventory deduction (`ConcurrentInventoryDeductionTest`), and concurrent bill finalization (`ConcurrentBillFinalizationTest`). The working-tree has an unstaged fix to `ConcurrentBillFinalizationTest` adding required `OrderItem`/`MenuItem` fixtures; without it the test may fail on model validation. `ConcurrentStockTransferTest` is not present.

</details>

<details>
<summary>File map</summary>

| File | Change |
|---|---|
| `backend/orders/migrations/0005_phase22_add_composite_indexes.py` | New: `CREATE INDEX CONCURRENTLY` for `order_branch_status_created_at` |
| `backend/financials/migrations/0005_phase22_add_composite_indexes.py` | New: `CREATE INDEX CONCURRENTLY` for `expense_branch_status_date` |
| `backend/menu/migrations/0004_phase22_add_composite_indexes.py` | New: `CREATE INDEX CONCURRENTLY` for `menuitem_catalog_order` |
| `backend/notifications/migrations/0004_phase22_add_composite_indexes.py` | New: `CREATE INDEX CONCURRENTLY` for `notif_idempotency_check` |
| `backend/orders/models.py` | Added composite index to `Order.Meta.indexes` |
| `backend/financials/models.py` | Added composite index to `Expense.Meta.indexes` |
| `backend/menu/models.py` | Added composite index to `MenuItem.Meta.indexes` |
| `backend/notifications/models.py` | Added composite index to `Notification.Meta.indexes` |
| `backend/orders/views.py` | Added `annotate(items_count=Count("items"))` to list queryset |
| `backend/orders/serializers.py` | `get_item_count` uses annotation when available |
| `backend/menu/views.py` | Added `prefetch_related("prices", "branch_availability")`; refactored `BranchCatalogView` to `get_or_set` |
| `backend/menu/services.py` | Added `invalidate_menu_catalog` calls on item/category/price write paths |
| `backend/billing/services.py` | Added `invalidate_dashboard_kpis` after `finalize_bill` |
| `backend/enterprise/services.py` | Added `invalidate_branch_config` after `set_configuration` |
| `backend/common/caching/services.py` | Re-read on non-acquiring lock path (stampede fix) |
| `backend/reporting/dashboard_services.py` | Refactored to `get_or_set` with `_build_kpis` closure |
| `backend/reporting/selectors.py` | Added `get_or_set` caching with user-scoped `scope_hash` to 5 selectors |
| `backend/tests/test_cache.py` | New: 15 tests across hit/miss, Redis failure, tenant isolation, invalidation, cross-org isolation |
| `backend/tests/test_concurrency.py` | New: 3 `TransactionTestCase` classes for payment, inventory, bill finalization concurrency (unstaged fix present) |
| `backend/tests/test_pagination.py` | New: max page size cap and export row limit tests |
| `backend/tests/test_queries.py` | New: N+1 regression tests for order and menu list views |
| `frontend/src/App.tsx` | `RouteLoadingSkeleton` component; `Suspense` fallback upgrade |
| `frontend/src/components/orders/TableCard.tsx` | Wrapped with `React.memo` |
| `frontend/src/components/orders/TableGrid.tsx` | Wrapped with `React.memo` |
| `frontend/src/components/kitchen/KitchenStatusColumn.tsx` | Wrapped with `React.memo` |
| `frontend/src/pages/billing/BillListPage.tsx` | Debounced search + `AbortController` |
| `frontend/src/pages/billing/BillingDashboard.tsx` | `AbortController` + skeleton loading state |
| `frontend/src/pages/crm/CustomerListPage.tsx` | `AbortController` |
| `frontend/src/pages/inventory/InventoryItemsPage.tsx` | `AbortController` |
| `frontend/src/pages/central-control/SystemHealthPage.tsx` | `AbortController` on interval fetch |
| `frontend/src/pages/central-control/RestaurantHealthPage.tsx` | `AbortController` |
| `frontend/src/pages/users/UsersListPage.tsx` | Added `useDebounce` to search |
| `frontend/src/services/billing.ts` | `listBills` accepts `signal?: AbortSignal` |
| `frontend/src/services/crm.ts` | `listCustomers` accepts `signal?: AbortSignal` |
| `frontend/src/services/inventory.ts` | `listInventoryItems`/`listCategories` accept `signal` |
| `frontend/src/services/centralControl.ts` | `getSystemHealth`/`getRestaurantHealth` accept `signal` |
| `frontend/vite.config.ts` | Split `vendor-react` into `vendor` + `router` chunks |
| `docker-compose.yml` | Minor service updates |
| `docs/database_optimization.md` | Phase 22 index rationale and ORM improvements |
| `docs/caching_architecture.md` | Cache key schema, invalidation points, TTL policy |
| `docs/scalability_guide.md` | Redis memory config, Nginx/PostgreSQL tuning, frontend performance section |
| `docs/performance_assessment_phase22.md` | Baseline static analysis and estimates |
| `performance/locustfile.py` | **Untracked** — Locust entry point |
| `performance/scenarios/payments.py` | **Untracked** — Concurrent payment scenario |
| `performance/scenarios/orders.py` | **Untracked** — Order flow scenarios |
| `performance/scenarios/reporting.py` | **Untracked** — Reporting scenarios |

Full diff: `git diff f55809d~1..HEAD`

</details>
