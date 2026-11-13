# RestaurantFlow Performance Assessment — Phase 22

**Date**: January 2025  
**Purpose**: Establish baseline performance metrics and document optimization opportunities

---

## 1. N+1 Query Patterns Found

### 1.1 OrderListCreateView
**File**: `backend/orders/views.py`  
**Issue**: Fetches orders with `.prefetch_related('items')` but does not preload `branch`, `created_by`, `assigned_waiter`, `table`, or `counter` FKs. This causes one query per order to resolve these relationships when serializing.  
**Impact**: High-traffic view — order lists are accessed frequently from POS terminals and kitchen displays.

### 1.2 BillListView
**File**: `backend/billing/views.py`  
**Issue**: Preloads `order`, `branch`, `branch__restaurant`, `created_by`, and `finalized_by` but does not use `.prefetch_related('items__menu_item')` for bill detail displays.  
**Impact**: Medium — bill listing is less frequent than orders, but still a high-value operation.

### 1.3 Kitchen Order List
**File**: `backend/kitchen/views.py`  
**Issue**: No select_related for `order__branch`, `order__table`, `order__counter` on KitchenOrderListView. The detail view already uses select_related correctly.  
**Impact**: High — KDS (Kitchen Display System) views poll this endpoint frequently.

### 1.4 Inventory Views
**File**: `backend/inventory/views.py`  
**Issue**: StockBalance list does not preload `inventory_item__restaurant`, `storage_location__branch`. PurchaseOrder list does not preload `supplier`, `branch`, `restaurant`, `created_by`. StockMovement list does not preload `inventory_item`, `storage_location`, `performed_by`.  
**Impact**: Medium — accessed during stock checks and receiving operations.

### 1.5 Notification List
**File**: `backend/notifications/views.py`  
**Issue**: NotificationRecipient queries returned by `get_notification_recipients_for_user` do not preload `notification.company`, `notification.restaurant`, or `notification.branch`.  
**Impact**: Medium-high — notifications list is accessed on every page load for unread badge counts.

### 1.6 Enterprise Configuration and Staff Views
**File**: `backend/enterprise/views.py`  
**Issue**: EnterpriseConfiguration lists do not select_related `company`, `restaurant`, `branch`. StaffTransfer lists do not select_related `from_branch`, `to_branch`, `requested_by`, `approved_by`.  
**Impact**: Low-medium — admin/management views accessed less frequently.

### 1.7 Reporting Dashboard
**File**: `backend/reporting/dashboard_services.py`  
**Status**: **Already optimized** — uses `.aggregate()`, `.annotate()`, and proper aggregation patterns. No Python-based iteration found.  
**Verification**: Confirmed aggregation at database level.

---

## 2. Missing Database Indexes

### 2.1 Notification Table
- **Missing**: Composite index on `(company, notification_type, created_at)` for time-series queries
- **Missing**: Composite index on `(source_type, source_id)` — **EXISTS** in 0001_initial
- **Missing**: Composite index on `(restaurant, status, created_at)`
- **Missing**: Composite index on `(branch, status, created_at)`

### 2.2 NotificationRecipient Table
- **Missing**: Composite index on `(user, is_read, created_at)` for unread queries — **PARTIAL**: index on `(user, read_at)` exists
- **Missing**: Composite index on `(notification, user)` — **EXISTS** as unique_together

### 2.3 EnterpriseConfiguration Table
- **Partial**: Index on `(company, key, effective_from)` exists as `company_config_key_active_idx` but does not include `effective_from`
- **Missing**: Composite index on `(branch, key, is_active)` — **EXISTS** as `enterprise_config_br_key_active_idx`

### 2.4 StaffBranchAssignment Table
- **EXISTS**: Index on `(user, branch, is_active)` already declared in 0001_initial

### 2.5 MenuRollout Table
- **EXISTS**: Index on `(company, status, created_at)` does not exist — table has `restaurant` FK not `company`
- **EXISTS**: Index on `(restaurant, status)` already declared in 0001_initial

### 2.6 Customer Table (CRM)
- **Missing**: Composite index on `(restaurant, is_active, created_at)` — **PARTIAL**: `(restaurant, is_active)` exists
- **Missing**: Standalone index on `email` — **EXISTS** as `crm_cust_email_idx`

### 2.7 LoyaltyAccount Table (CRM)
- **Missing**: Composite index on `(loyalty_program, points_balance)` for ranking queries

### 2.8 Campaign Table (Marketing)
- **EXISTS**: Index on `(restaurant, status, start_date)` — **PARTIAL**: `(restaurant, status)` exists
- **EXISTS**: Index on `(restaurant, status, end_date)` — **PARTIAL**: as above

### 2.9 MenuItemPrice Table
- **Missing**: Composite index on `(menu_item, branch, effective_from)` — **EXISTS** as `menu_price_item_from_idx`
- **Missing**: Composite index on `(menu_item, branch, is_active)` — **EXISTS** as `menu_price_item_active_idx`

### 2.10 MenuItemBranch Table
- **Missing**: Composite index on `(branch, is_available)` for availability queries
- **Missing**: Composite index on `(menu_item, branch)` — **EXISTS** as unique constraint

**Summary**: Most critical indexes already exist. New migrations will add missing composite indexes for notifications, enterprise, CRM, and marketing tables where they genuinely improve query performance.

---

## 3. Existing Cache Usage

### 3.1 Reporting Service
**File**: `backend/reporting/services.py`  
**Status**: Uses `django.core.cache` for:
- `sales_trend` (TTL: CACHE_TTL_* from reporting/constants.py)
- `top_items`
- `branch` summaries
- `financial` summaries

**Cache Keys**: Scope-aware keys include `user:`, `restaurant:`, `branch:` segments to prevent cross-tenant leakage.

### 3.2 Dashboard KPIs
**File**: `backend/reporting/dashboard_services.py`  
**Status**: `get_dashboard_kpis` uses Redis cache with scope-aware keys. TTL set to `CACHE_TTL_DASHBOARD`.

### 3.3 Menu Catalog
**Status**: **NOT CACHED** — menu items fetched from database on every request.  
**Opportunity**: Menu catalog changes infrequently; suitable for short-lived cache (60-300s TTL).

### 3.4 Notifications List
**Status**: **NOT CACHED** — notification lists fetched from database on every page load.  
**Opportunity**: Cache unread count per user with 30s TTL; invalidate on notification create/read.

### 3.5 User Permissions
**Status**: **NOT CACHED** at application level — Django permissions loaded per request.  
**Opportunity**: Cache user permission checks (60s TTL) with cache key scoped to `user_id`.

### 3.6 Payments, Accounting, Audit
**Status**: **Correctly NOT CACHED** — financial data should never be stale. PostgreSQL is the authoritative source.

---

## 4. Pagination

### 4.1 Global Settings
**File**: `backend/config/settings.py`  
**Status**: `REST_FRAMEWORK['PAGE_SIZE'] = 20` set globally.  
**Issue**: Several list views do not enforce a `MAX` page size cap. A client can request `?page_size=10000` and cause expensive queries.

### 4.2 Vulnerable Views
- OrderListCreateView
- BillListView
- PaymentListView
- KitchenOrderListView
- NotificationListView

**Recommendation**: Add `max_page_size = 100` to paginator configuration or enforce in view-level get_queryset.

---

## 5. WebSocket Channel Groups

### 5.1 KitchenConsumer
**File**: `backend/kitchen/consumers.py`  
**Group**: `kitchen_{branch_id}`  
**Scope**: Branch-scoped (correct)  
**Status**: `_get_current_state` already uses `.select_related('order__branch', 'order__table')` and `.prefetch_related('items__menu_item')`. **Optimization already in place.**

### 5.2 CentralControlConsumer
**File**: `backend/central_control/consumers.py`  
**Group**: `company_{org_id}_central_control`  
**Scope**: Organization-scoped (correct)  
**Status**: Already uses select_related in state fetch.

### 5.3 NotificationsConsumer
**File**: `backend/notifications/consumers.py`  
**Group**: `notifications_user_{user_id}`  
**Scope**: User-scoped (correct)  
**Status**: Initial list views do not preload notification FK relationships (see item 1.5).

---

## 6. Celery Task Configuration

### 6.1 Task Files Found
- `backend/notifications/tasks.py`
- `backend/crm/tasks.py`
- `backend/marketing/tasks.py`

**Status**: All tasks currently use the default Celery queue. No queue routing configured.

### 6.2 Recommended Queue Configuration
| Queue | Tasks | Priority | Workers |
|---|---|---|---|
| `notifications` | `notifications.*` | High | 2-4 |
| `maintenance` | `crm.*`, `marketing.*` | Low | 1-2 |
| `reports` | `reports.*` | Medium | 1-2 |
| `default` | All others | Medium | 2 |

**Configuration**: Add `CELERY_TASK_ROUTES` to `config/settings.py`.

---

## 7. Frontend Performance

### 7.1 App.tsx Component
**File**: `frontend/src/App.tsx`  
**Issue**: Imports ~50 page components eagerly at the top level using static `import` statements. This increases initial JavaScript parse time and bundle size.

**Example**:
```typescript
import OrderListPage from './pages/orders/OrderListPage';
import BillListPage from './pages/billing/BillListPage';
import KitchenDisplayPage from './pages/kitchen/KitchenDisplayPage';
// ... 47 more imports
```

**Impact**: Initial page load parses all routes even if the user never visits them. Increases Time to Interactive (TTI).

**Recommendation**: Use `React.lazy()` and `Suspense` for code-splitting:
```typescript
const OrderListPage = React.lazy(() => import('./pages/orders/OrderListPage'));
```

### 7.2 No Virtualized Lists
**Status**: `frontend/package.json` does not include `react-window` or `react-virtual`.  
**Impact**: Long lists (orders, bills, notifications) render all DOM nodes at once, causing jank on scroll.  
**Recommendation**: Introduce `react-window` for lists exceeding 50 items.

---

## 8. Metrics Unavailable Without Running Environment

The following metrics require a live deployment with realistic data:

### 8.1 API Response Times
- **p50, p95, p99 latency** for common endpoints
- **Measurement Tool**: Application Performance Monitoring (APM) — New Relic, Datadog, or Prometheus + Grafana

### 8.2 Database Query Latency
- **Slow query log** analysis (queries > 100ms)
- **EXPLAIN ANALYZE** plans for top 10 queries
- **Measurement Tool**: `pg_stat_statements` PostgreSQL extension

### 8.3 Cache Hit/Miss Ratios
- **Redis stats**: `INFO stats` — `keyspace_hits` vs `keyspace_misses`
- **Measurement Tool**: Redis CLI or monitoring integration

### 8.4 Frontend Bundle Size
- **Current bundle size**: **UNAVAILABLE** (requires `npm run build` in live environment)
- **Measurement Tool**: Vite build output, Lighthouse, or Webpack Bundle Analyzer

### 8.5 Memory and CPU Utilization
- **Django worker memory**: **UNAVAILABLE**
- **Celery worker memory**: **UNAVAILABLE**
- **PostgreSQL connection usage**: **UNAVAILABLE**
- **Measurement Tool**: `docker stats`, `htop`, Prometheus node_exporter

### 8.6 Background Task Execution Times
- **Celery task duration**: **UNAVAILABLE**
- **Measurement Tool**: Celery Flower, or `django_celery_results` table queries

### 8.7 WebSocket Connection Behavior
- **Concurrent connections**: **UNAVAILABLE**
- **Message throughput**: **UNAVAILABLE**
- **Measurement Tool**: Django Channels metrics, Redis Pub/Sub monitoring

---

## 9. Performance Targets (Initial Engineering Goals)

These targets are initial engineering goals, not guaranteed results. Actual performance depends on hardware, data volume, and deployment configuration.

| Area | Target | Baseline | Status |
|---|---|---|---|
| Simple API reads (e.g., menu list) | p95 < 300ms | **UNMEASURED** | To be benchmarked |
| Common API writes (e.g., create order) | p95 < 500ms | **UNMEASURED** | To be benchmarked |
| Dashboard APIs | p95 < 800ms | **UNMEASURED** | To be benchmarked |
| Database query latency | Optimize slow queries (>100ms) | **UNMEASURED** | Requires `pg_stat_statements` |
| Frontend initial load | Minimize unused JS | **UNMEASURED** | Requires build + Lighthouse |
| Cache hit ratio | Establish measurable improvement | **UNMEASURED** | Requires live Redis stats |
| Error rate | No increase from baseline | **UNMEASURED** | Requires APM |
| Financial operations | Maintain correctness under concurrency | **ASSUMED CORRECT** | Verified in Phase 8-9 tests |

---

## 10. Recommendations Summary

### 10.1 Immediate Wins (Phase 22 Scope)
1. **Add select_related/prefetch_related** to N+1 patterns (orders, billing, kitchen, inventory, notifications, enterprise)
2. **Add missing composite indexes** (notifications, enterprise, CRM, marketing)
3. **Set CONN_MAX_AGE=60** in DATABASES config for connection reuse
4. **Configure CELERY_TASK_ROUTES** for queue separation

### 10.2 Next Phase Opportunities (Post-Phase 22)
1. **Frontend code-splitting** with React.lazy/Suspense
2. **Virtualized lists** with react-window for long lists
3. **Menu catalog caching** with 60s TTL and invalidation on menu updates
4. **Unread notification count caching** with 30s TTL
5. **Max page size enforcement** (cap at 100 items per page)
6. **PgBouncer** for connection pooling (external deployment component)
7. **APM integration** for real-time metrics (Prometheus + Grafana)

### 10.3 Not Recommended
- ❌ **Caching financial data** (payments, accounting, audit) — correctness > performance
- ❌ **Removing existing indexes** — all current indexes serve legitimate query patterns
- ❌ **Aggressive denormalization** — normalized schema ensures data consistency

---

## 11. Conclusion

RestaurantFlow's current architecture is **fundamentally sound**:
- Reporting services already use database-level aggregation
- Cache keys are properly scoped to prevent cross-tenant leakage
- Financial operations remain transactionally correct
- Most critical indexes already exist

**Key findings**:
- N+1 patterns exist in 6-7 high-traffic views
- 3-5 composite indexes genuinely missing
- Frontend eager-loads all routes (optimization opportunity)
- No measurable baseline exists yet (requires live deployment)

**Phase 22 will address**:
- Database query optimization (select_related/prefetch_related)
- Missing index creation (safe, non-duplicate)
- Connection pooling (CONN_MAX_AGE)
- Celery queue routing
- Documentation for future optimization work

**Phase 22 will NOT address**:
- Frontend code-splitting (requires deeper refactoring)
- Live metrics collection (requires deployment infrastructure)
- PgBouncer setup (external component, documented for optional use)

---

**Next Steps**: Proceed with FEAT-001 implementation — database query optimization and index migrations.
