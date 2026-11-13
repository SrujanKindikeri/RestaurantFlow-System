# Database Optimization — Phase 22

**Purpose**: Document every index added, every select_related/prefetch_related change made, and the
rationale behind connection pooling settings introduced in Phase 22.

---

## 1. Indexes Added

### 1.1 `notifications` app

| Model | Fields | Index Name | Query Pattern Supported |
|---|---|---|---|
| `Notification` | `(company, notification_type, created_at)` | `notif_company_type_created_idx` | "Get latest N notifications of type X for company Y" |
| `Notification` | `(restaurant, notification_type, created_at)` | `notif_rest_type_created_idx` | "Get recent notifications of type X for restaurant Y" |
| `Notification` | `(branch, notification_type, created_at)` | `notif_branch_type_created_idx` | "Get recent notifications of type X for branch Y" |
| `NotificationRecipient` | `(user, delivery_status, created_at)` | `notif_recip_user_status_created_idx` | "Get unread/pending notifications for user ordered by recency" |

**Migration**: `notifications/migrations/0002_performance_indexes.py`

---

### 1.2 `enterprise` app

| Model | Fields | Index Name | Query Pattern Supported |
|---|---|---|---|
| `EnterpriseConfiguration` | `(company, configuration_key, created_at)` | `ent_config_co_key_created_idx` | "Get configuration history for key X in company Y" |
| `StaffBranchAssignment` | `(user, branch, is_active)` | `ent_staffassign_user_branch_active` | "Get active assignment for user U at branch B" |
| `MenuRollout` | `(restaurant, status, created_at)` | `ent_rollout_rest_status_created` | "Get rollouts by status ordered by time for restaurant Y" |

**Migration**: `enterprise/migrations/0002_performance_indexes.py`

---

### 1.3 `crm` app

| Model | Fields | Index Name | Query Pattern Supported |
|---|---|---|---|
| `Customer` | `(restaurant, is_active, created_at)` | `crm_cust_rest_active_created_idx` | "Get active customers for restaurant Y ordered by join date" |
| `LoyaltyAccount` | `(loyalty_program, points_balance)` | `crm_loyalty_prog_balance_idx` | "Rank accounts by points balance for a loyalty program" |

**Migration**: `crm/migrations/0002_performance_indexes.py`

---

### 1.4 `marketing` app

| Model | Fields | Index Name | Query Pattern Supported |
|---|---|---|---|
| `MarketingCampaign` | `(restaurant, status, start_at)` | `mktg_campaign_rest_status_start` | "Get running/scheduled campaigns starting after date D for restaurant Y" |
| `MarketingCampaign` | `(restaurant, status, end_at)` | `mktg_campaign_rest_status_end` | "Get campaigns ending before date D for restaurant Y" |

**Migration**: `marketing/migrations/0002_performance_indexes.py`

---

### 1.5 `menu` app

| Model | Fields | Index Name | Query Pattern Supported |
|---|---|---|---|
| `MenuItemBranch` | `(branch, is_available)` | `menu_avail_branch_available_idx` | "Get all currently available menu items for a branch" (POS catalog query) |

**Migration**: `menu/migrations/0002_performance_indexes.py`

**Note**: `MenuItemPrice` already had `(menu_item, branch, is_active)` and `(menu_item, branch, effective_from)` declared in `0001_initial.py` via `Meta.indexes`. No duplication was introduced.

---

### 1.6 Indexes NOT Added (Already Existed in `0001_initial`)

The following indexes were requested in the plan but were found to already exist after reviewing each app's `0001_initial.py`. They were deliberately skipped to avoid duplication:

| App | Model | Fields | Existing Index Name |
|---|---|---|---|
| `notifications` | `Notification` | `(source_type, source_id)` | pre-existing via `db_index=True` |
| `notifications` | `NotificationRecipient` | `(notification, user)` | pre-existing unique constraint |
| `enterprise` | `EnterpriseConfiguration` | `(company, key, is_active)` | `enterprise_config_co_key_active_idx` |
| `enterprise` | `EnterpriseConfiguration` | `(branch, key, is_active)` | `enterprise_config_br_key_active_idx` |
| `enterprise` | `StaffBranchAssignment` | `(user, branch, is_active)` partial | `enterprise_staffassign_branch_idx` |
| `crm` | `Customer` | `(restaurant, is_active)` | `crm_cust_rest_active_idx` |
| `crm` | `Customer` | `email` | `crm_cust_email_idx` |
| `menu` | `MenuItemPrice` | `(menu_item, branch, effective_from)` | `menu_price_item_from_idx` |
| `menu` | `MenuItemPrice` | `(menu_item, branch, is_active)` | `menu_price_item_active_idx` |
| `menu` | `MenuItemBranch` | `(menu_item, branch)` | `unique_menuitem_branch_availability` |

---

## 2. select_related / prefetch_related Changes

### 2.1 `backend/orders/views.py`

| View | Change | N+1 Eliminated |
|---|---|---|
| `OrderListCreateView.get_queryset` | Added `.select_related('branch', 'created_by', 'assigned_waiter', 'table', 'counter')` before `.prefetch_related('items')` | Per-order FK lookups for branch, waiter, table, counter |
| `OrderDetailView.get_queryset` | Added `.select_related('branch', 'created_by', 'assigned_waiter', 'table', 'counter')` before `.prefetch_related('items__menu_item')` | Per-order FK lookups + per-item menu_item lookups |
| `TableSessionListView.get_queryset` | Added `.select_related('table__branch', 'opened_by')` | Per-session lookups for table FK and opener |

### 2.2 `backend/billing/views.py`

| View | Change | N+1 Eliminated |
|---|---|---|
| `BillListView.get_queryset` | Added `order__branch` to `.select_related(...)` | Per-bill order branch lookup on list page |
| `BillDetailView` / `_get_bill_or_404` | Already has `.select_related('order', 'order__table', 'order__counter', 'branch', 'created_by', 'finalized_by')` + `.prefetch_related('items__menu_item', 'items__order_item')` | All N+1s on bill detail |

### 2.3 `backend/payments/views.py`

| View | Change | N+1 Eliminated |
|---|---|---|
| `PaymentListView` | Already has `.select_related('bill', 'bill__order', 'branch', 'counter', 'initiated_by')` | Per-payment FK lookups |
| `_get_accessible_refund` | Already has `.select_related('payment', 'payment__branch', 'requested_by', 'approved_by', 'processed_by')` | Per-refund FK lookups |

### 2.4 `backend/inventory/views.py`

| View | Change | N+1 Eliminated |
|---|---|---|
| `StockBalanceListView.get_queryset` | Already has `.select_related('inventory_item', 'inventory_item__category', 'storage_location', 'storage_location__branch')` | Per-balance item and location lookups |
| `PurchaseOrderListView.get` | Already has `.select_related('supplier', 'branch', 'restaurant', 'created_by')` | Per-PO FK lookups |
| `StockMovementListView.get_queryset` | Already has `.select_related('inventory_item', 'storage_location', 'storage_location__branch', 'performed_by')` | Per-movement FK lookups |

### 2.5 `backend/notifications/selectors.py`

| Function | Change | N+1 Eliminated |
|---|---|---|
| `get_notification_recipients_for_user` | Already has `.select_related('notification', 'notification__company', 'notification__restaurant', 'notification__branch')` | Per-recipient notification FK lookups |

### 2.6 `backend/enterprise/selectors.py`

| Function | Change | N+1 Eliminated |
|---|---|---|
| `get_configurations_for_scope` | Already has `.select_related('created_by', 'updated_by', 'company', 'restaurant', 'branch')` | Per-config scope FK lookups |
| `get_transfers_for_restaurant` | Already has `.select_related('user', 'source_branch', 'destination_branch', 'requested_by', 'approved_by')` | Per-transfer FK lookups |

### 2.7 `backend/reporting/dashboard_services.py`

**Status**: No changes required. `get_dashboard_kpis()` delegates to `reporting/aggregations.py` which uses DB-level `.aggregate(Sum/Count/Coalesce)` throughout. No Python-loop aggregations found.

---

## 3. CONN_MAX_AGE Rationale

**Setting**: `DATABASES['default']['CONN_MAX_AGE'] = 60`

**File**: `backend/config/settings.py`

**Why 60 seconds?**

Gunicorn runs synchronous workers — by default one worker handles one request at a time. Without persistent connections, every request opens and closes a database connection, adding TCP + PostgreSQL auth overhead (typically 5–20 ms) per request.

With `CONN_MAX_AGE = 60`, each Gunicorn worker reuses its database connection for up to 60 seconds. The number of live connections at any point is bounded by the number of workers, making connection usage predictable.

**Rule of thumb**: `max_connections_to_postgres ≈ gunicorn_workers + a few overhead connections`

**When to set CONN_MAX_AGE = 0**: If using PgBouncer in transaction-pooling mode, set `CONN_MAX_AGE = 0` (or remove it). PgBouncer itself manages connection multiplexing — persistent Django connections would conflict with its pooling logic.

---

## 4. Guidelines for Future Query Review

### 4.1 Development: django-debug-toolbar

Install and enable `django-debug-toolbar` for local development:

```python
# In settings (DEBUG mode only)
if DEBUG:
    INSTALLED_APPS += ["debug_toolbar"]
    MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
    INTERNAL_IPS = ["127.0.0.1"]
```

The toolbar shows the number of DB queries per request and highlights duplicate queries (the sign of an N+1). **Any list endpoint showing N+1 or more queries should be reviewed before merge.**

Rule: list endpoints should fire at most:
- 1 query for auth/session
- 1 query for the main queryset (with joins from select_related)
- 1 query per prefetch_related relationship
- 1 query for pagination count (if applicable)

### 4.2 Staging: EXPLAIN ANALYZE

Before adding a new index to production, validate it in staging with real data:

```sql
-- Connect to staging DB
EXPLAIN ANALYZE
SELECT *
FROM notifications_notification
WHERE company_id = '...' AND notification_type = 'ORDER_CREATED'
ORDER BY created_at DESC
LIMIT 20;
```

Look for:
- `Seq Scan` on large tables — indicates a missing index
- `Index Scan` — good
- `Bitmap Index Scan` + `Bitmap Heap Scan` — good for range queries
- High `actual time` values — investigate further

**Add an index only if EXPLAIN ANALYZE confirms it is used and reduces cost.** Unused indexes waste write performance and storage.

### 4.3 Detecting Regressions

Enable `pg_stat_statements` on staging/production:

```sql
-- In postgresql.conf
shared_preload_libraries = 'pg_stat_statements'

-- Query top slow queries after a load test
SELECT query, calls, total_exec_time / calls AS avg_ms
FROM pg_stat_statements
ORDER BY avg_ms DESC
LIMIT 20;
```

Review any query with `avg_ms > 100` before each release.

### 4.4 Index Naming Convention

All Phase 22 indexes follow the pattern: `{app_abbr}_{model_abbr}_{field_abbr}_idx`

Examples:
- `notif_company_type_created_idx` — notifications.Notification
- `crm_cust_rest_active_created_idx` — crm.Customer
- `mktg_campaign_rest_status_start` — marketing.MarketingCampaign

Always check `0001_initial.py` (and any subsequent migrations) before adding an index to avoid duplication.
