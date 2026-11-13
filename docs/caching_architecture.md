# RestaurantFlow Caching Architecture

## Overview

The caching layer lives in `backend/common/caching/` and is wired into the
service and view layers across the application. All Redis access goes through
`CacheService` — never raw `django.core.cache.cache` calls — so that Redis
failures are handled uniformly and never propagate to callers as exceptions.

---

## Module layout

```
backend/common/caching/
    __init__.py        (empty)
    keys.py            key-builder functions
    policies.py        TTL constants and jitter helper
    services.py        CacheService class
    invalidation.py    invalidation functions (always use transaction.on_commit)
```

---

## Cache key schema

All keys share the prefix `restaurantflow` and always include an explicit
tenant-scope component (branch, restaurant, or user ID).

| Data category         | Key pattern                                                          |
|-----------------------|----------------------------------------------------------------------|
| Menu catalog          | `restaurantflow:branch:{branch_id}:menu_catalog:{params_hash}`       |
| Branch config         | `restaurantflow:branch:{branch_id}:config:{key}`                     |
| User permissions      | `restaurantflow:user:{user_id}:branch:{branch_id}:permissions`       |
| Dashboard KPIs        | `restaurantflow:restaurant:{rid}:branch:{bid}:dashboard_kpi:{date}`  |
| Reporting summaries   | `restaurantflow:report:{type}:{scope_hash}:{date_from}:{date_to}`    |
| Inventory availability| `restaurantflow:branch:{branch_id}:inventory:{item_id}`              |

### Key examples

```
restaurantflow:branch:550e8400-e29b-41d4-a716-446655440000:menu_catalog:a3f7c9d1e2b4
restaurantflow:user:42:branch:550e8400:permissions
restaurantflow:restaurant:1:branch:2:dashboard_kpi:2024-07-15
restaurantflow:report:sales_trend:u42:r1:b2:2024-07-01:2024-07-15
```

---

## TTL table

| Data category          | TTL      | Constant                   | Reason                                    |
|------------------------|----------|----------------------------|-------------------------------------------|
| Menu catalog           | 5 min    | `MENU_CATALOG_TTL = 300`   | Changes infrequently; invalidated on save |
| Branch config          | 10 min   | `BRANCH_CONFIG_TTL = 600`  | Very stable enterprise config             |
| User permissions       | 5 min    | `USER_PERMISSIONS_TTL = 300` | Security-sensitive; short TTL            |
| Dashboard KPIs         | 2 min    | `DASHBOARD_KPI_TTL = 120`  | Near-real-time operational data           |
| Reporting summaries    | 5 min    | `REPORTING_SUMMARY_TTL = 300` | Analytical queries are expensive        |
| Inventory availability | 1 min    | `INVENTORY_AVAILABILITY_TTL = 60` | Stock changes rapidly              |

All TTLs have ±15% random jitter applied by `add_jitter(ttl)` to prevent
cache stampede when many keys expire simultaneously.

---

## Invalidation trigger table

| Model saved/deleted         | Invalidation function called             | Cache keys invalidated                            |
|-----------------------------|------------------------------------------|---------------------------------------------------|
| `menu.MenuItem`             | `invalidate_menu_catalog(branch_id)`     | All catalog keys for each branch carrying the item|
| `menu.MenuItemPrice`        | `invalidate_menu_catalog(branch_id)`     | Catalog keys for the affected branch              |
| `menu.MenuItemBranch`       | `invalidate_menu_catalog(branch_id)`     | Catalog keys for the affected branch              |
| `enterprise.EnterpriseConfiguration` | `invalidate_branch_config(branch_id, key)` | Config key for the specific branch/key  |
| `accounts.UserRoleAssignment` | `invalidate_user_permissions(user_id)` | All permissions keys for the user                 |
| `inventory.StockBalance`    | `invalidate_inventory_availability(branch_id, item_id)` | Availability key for item at branch |

All invalidations are wrapped in `transaction.on_commit()` so the cache is
only cleared after the DB transaction commits successfully. Redis failure
during invalidation is logged as a warning and never causes the DB transaction
to roll back.

---

## Stampede protection

`CacheService.get_or_set(key, callable_fn, ttl)` acquires a Redis `SET NX EX`
lock before calling the expensive `callable_fn`. If the lock cannot be
acquired (e.g. another worker is already regenerating the value), the caller
falls through to `callable_fn()` directly — the lock is advisory, not blocking.
Lock keys are cleaned up in a `finally` block.

---

## Redis failure behavior

| Data category     | Redis GET failure behavior                                  |
|-------------------|-------------------------------------------------------------|
| Menu catalog      | Graceful fallback: miss treated as cache miss, queries DB   |
| Dashboard KPIs    | Graceful fallback: miss treated as cache miss, queries DB   |
| Reporting         | Graceful fallback: miss treated as cache miss, queries DB   |
| Inventory         | Graceful fallback: miss treated as cache miss, queries DB   |
| User permissions  | `get_secure()` returns `CACHE_MISS_SENTINEL`; caller **always** goes to DB — Redis failure can never silently grant or deny access |

---

## What is NOT cached

| Category              | Reason                                                                          |
|-----------------------|---------------------------------------------------------------------------------|
| Payment transactions  | Real-time financial state; stale cache could cause double-charge or under-charge |
| Accounting balances   | Authoritative financial data; correctness is paramount over performance         |
| Security audit logs   | Append-only immutable records; never read from cache                            |
| Order status          | High update frequency; cache TTL would exceed business tolerance               |

Sentinel constants `PAYMENTS_NO_CACHE = True` and `ACCOUNTING_NO_CACHE = True`
in `policies.py` document this intent explicitly.

---

## Adding new cache entries

1. Add a TTL constant to `policies.py`.
2. Add a key-builder function to `keys.py` with tenant-scope in the key.
3. Use `CacheService.get()` / `CacheService.set()` in the service layer.
4. For security-sensitive data, use `CacheService.get_secure()` and handle
   `CACHE_MISS_SENTINEL`.
5. Add an invalidation function to `invalidation.py` using `transaction.on_commit()`.
6. Connect a `post_save` / `post_delete` signal in the relevant `signals.py`.
7. Register the signal handler in the app's `apps.py` `ready()` method.
