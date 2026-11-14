# Caching Architecture

## Overview

RestaurantFlow uses Redis (via `django-redis`) as its cache backend for read-heavy, non-financial data. All caching goes through `common/caching/services.py` (`CacheService`) which provides graceful fallback: on Redis failure, reads fall back to the database and writes are silently skipped, so the application remains functional.

---

## Key Schema

All keys share the prefix `restaurantflow:`.

| Key Pattern | Description |
|---|---|
| `restaurantflow:branch:{branch_id}:menu_catalog:{params_hash}` | POS catalog for a branch, parameterised by query filters |
| `restaurantflow:branch:{branch_id}:config:{key}` | Effective enterprise configuration for a branch |
| `restaurantflow:restaurant:{restaurant_id}:branch:{branch_id}:dashboard_kpi:{date_str}` | Dashboard KPI payload, scoped to restaurant/branch/day |
| `restaurantflow:report:{report_type}:{scope_hash}:{date_from}:{date_to}` | Reporting aggregation results |
| `restaurantflow:user:{user_id}:branch:{branch_id}:permissions` | User permission set (populated separately) |
| `restaurantflow:branch:{branch_id}:inventory:{item_id}` | Inventory availability for a specific item |

`scope_hash` and `params_hash` are 12-character MD5 hex digests produced by `common.caching.keys.make_params_hash()`.

The menu catalog and branch config keys are branch-scoped, which is the correct tenant boundary. The reporting and dashboard keys include both restaurant and branch scope to prevent cross-tenant data leaks.

---

## TTL Table

| Data type | TTL | Constant |
|---|---|---|
| Menu catalog | 300 s (5 min) | `MENU_CATALOG_TTL` |
| Branch config | 600 s (10 min) | `BRANCH_CONFIG_TTL` |
| User permissions | 300 s (5 min) | `USER_PERMISSIONS_TTL` |
| Dashboard KPI | 120 s (2 min) | `DASHBOARD_KPI_TTL` |
| Reporting summary | 300 s (5 min) | `REPORTING_SUMMARY_TTL` |
| Inventory availability | 60 s (1 min) | `INVENTORY_AVAILABILITY_TTL` |

All TTLs have ±15 % random jitter applied by `common.caching.policies.add_jitter()` to prevent simultaneous cache expiry (stampede protection). `CacheService.get_or_set()` applies jitter automatically; callers do not need to call `add_jitter` themselves.

---

## Cached Endpoints

| Endpoint | Cache key | TTL |
|---|---|---|
| `GET /api/menu/branches/{id}/catalog/` | `menu_catalog_key(branch_id, params_hash)` | `MENU_CATALOG_TTL` |
| `GET /api/reporting/dashboard/` | `dashboard_kpi_key(user_id, restaurant_id, branch_id, date_str)` | `DASHBOARD_KPI_TTL` |
| `GET /api/reporting/sales/summary/` | `reporting_key("sales_summary", scope_hash, date_from, date_to)` | `REPORTING_SUMMARY_TTL` |
| `GET /api/reporting/orders/summary/` | `reporting_key("orders_summary", scope_hash, date_from, date_to)` | `REPORTING_SUMMARY_TTL` |
| `GET /api/reporting/menu/top-selling/` | `reporting_key("top_selling_items", scope_hash, date_from, date_to)` | `REPORTING_SUMMARY_TTL` |
| `GET /api/reporting/kitchen/performance/` | `reporting_key("kitchen_performance", scope_hash, date_from, date_to)` | `REPORTING_SUMMARY_TTL` |
| `GET /api/reporting/inventory/summary/` | `reporting_key("inventory_summary", scope_hash, "none", "none")` | `REPORTING_SUMMARY_TTL` |
| Enterprise config reads (`ConfigurationResolver`) | `CACHE_KEY_EFFECTIVE_CONFIG` format | `CACHE_TTL_EFFECTIVE_CONFIG` |

---

## Explicitly NOT Cached

The following data is never stored in Redis as authoritative state:

- **Payments** (`payments.Payment`, `payments.PaymentRefund`) — financial transactions must always read from the database.
- **Accounting balances** (`accounting.JournalEntry`, balance sheet, P&L) — posted journals are authoritative; stale cache would misrepresent financial state.
- **Audit logs** (`accounting.AccountingAuditLog`, `payments.PaymentAuditLog`) — immutable records must reflect actual DB state.

`payments/views.py` and `accounting/views.py` contain no `CacheService` calls. This is enforced by code review and CI.

---

## Invalidation Trigger Map

Invalidation functions live in `common/caching/invalidation.py`. All of them schedule the actual delete via `transaction.on_commit()`, so cache keys are only removed after the database transaction commits. A transaction rollback leaves the cache untouched.

| Trigger (service function) | Invalidation call | Cache cleared |
|---|---|---|
| `menu.services.set_item_active()` | `invalidate_menu_catalog(branch_id)` for every branch of the restaurant | Menu catalog for all affected branches |
| `menu.services.set_category_active()` | `invalidate_menu_catalog(branch_id)` for every branch of the restaurant | Menu catalog for all affected branches |
| `menu.services.deactivate_price()` | `invalidate_menu_catalog(branch_id)` | Menu catalog for that branch |
| `billing.services.finalize_bill()` | `invalidate_dashboard_kpis(restaurant_id, branch_id)` | Dashboard KPI for that restaurant/branch |
| `enterprise.services.set_configuration()` | `ConfigurationResolver.invalidate_cache_for_config(config)` + `invalidate_branch_config(branch_id)` | Effective config cache (all scopes for the key) + common branch config keys |

### Pattern used for invalidation

`invalidate_menu_catalog(branch_id)` deletes all keys matching `restaurantflow:branch:{branch_id}:menu_catalog:*`, which covers every query-parameter variant cached for that branch.

`invalidate_dashboard_kpis(restaurant_id, branch_id)` deletes `restaurantflow:restaurant:{restaurant_id}:branch:{branch_id}:dashboard_kpi:*`, clearing every date variant.

`invalidate_branch_config(branch_id)` deletes `restaurantflow:branch:{branch_id}:config:*`.

---

## Redis Failure Behavior

| Operation | Failure outcome |
|---|---|
| `CacheService.get()` | Returns `None`; caller proceeds to DB |
| `CacheService.set()` | Silently skipped; next request hits DB |
| `CacheService.delete()` | Silently skipped; key expires at TTL |
| `CacheService.delete_pattern()` | Silently skipped; stale data served until natural TTL expiry |
| `CacheService.get_secure()` | Returns `CACHE_MISS_SENTINEL`; caller must not grant/deny access based on stale data — must go to DB |
| `CacheService.get_or_set()` | Falls through to callable; result stored if Redis recovers |

Redis failure never rolls back a database transaction. Cache correctness is eventually consistent: after a failure, TTL-based expiry restores consistency within the configured TTL window.

---

## Implementation Files

| File | Role |
|---|---|
| `backend/common/caching/services.py` | `CacheService` — all read/write/delete operations |
| `backend/common/caching/keys.py` | Key builders and `make_params_hash()` |
| `backend/common/caching/policies.py` | TTL constants and `add_jitter()` |
| `backend/common/caching/invalidation.py` | `on_commit`-wrapped invalidation helpers |
| `backend/menu/views.py` | `BranchCatalogView` — menu catalog caching |
| `backend/menu/services.py` | Invalidation after item/category/price mutations |
| `backend/reporting/dashboard_services.py` | Dashboard KPI caching via `get_or_set()` |
| `backend/reporting/selectors.py` | Sales, orders, top items, kitchen, inventory caching |
| `backend/billing/services.py` | `finalize_bill()` triggers `invalidate_dashboard_kpis()` |
| `backend/enterprise/services.py` | `set_configuration()` triggers `invalidate_branch_config()` |
| `backend/enterprise/configuration_resolver.py` | Per-key effective config caching (separate from common layer) |
