# RestaurantFlow — Reporting, Analytics & Business Intelligence

**Phase 14**

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Source-of-Truth Rules](#2-source-of-truth-rules)
3. [Operational vs Accounting Metrics](#3-operational-vs-accounting-metrics)
4. [Permissions](#4-permissions)
5. [Scope & Authorization](#5-scope--authorization)
6. [Date / Time Handling](#6-date--time-handling)
7. [Filters](#7-filters)
8. [API Reference](#8-api-reference)
9. [Dashboard KPIs](#9-dashboard-kpis)
10. [Sales Reports](#10-sales-reports)
11. [Order Reports](#11-order-reports)
12. [Menu Reports](#12-menu-reports)
13. [Payment Reports](#13-payment-reports)
14. [Kitchen Reports](#14-kitchen-reports)
15. [Inventory Reports](#15-inventory-reports)
16. [Expense & Payable Reports](#16-expense--payable-reports)
17. [Branch & Counter Reports](#17-branch--counter-reports)
18. [Staff Reports](#18-staff-reports)
19. [Financial Summary](#19-financial-summary)
20. [Profitability Rules](#20-profitability-rules)
21. [CSV Export](#21-csv-export)
22. [Caching Strategy](#22-caching-strategy)
23. [Performance Guidelines](#23-performance-guidelines)
24. [Real-Time Events](#24-real-time-events)
25. [Data Quality Rules](#25-data-quality-rules)
26. [Security Rules](#26-security-rules)
27. [Frontend Routes](#27-frontend-routes)
28. [Testing](#28-testing)

---

## 1. Architecture Overview

The reporting layer lives in its own Django app:

```
backend/reporting/
    __init__.py
    apps.py
    models.py            # ReportExportAudit only
    admin.py
    constants.py         # Permission codes, report types, cache TTLs
    exceptions.py        # DRF exception classes
    validators.py        # Date range, top-N, scope validators
    permissions.py       # DRF BasePermission classes
    access.py            # Scope resolution wrappers
    filters.py           # ReportFilterParams dataclass
    aggregations.py      # PostgreSQL aggregation helpers
    selectors.py         # Scope-aware selector functions
    services.py          # High-level service functions + Redis caching
    dashboard_services.py# KPI dashboard assembly
    export_services.py   # CSV generation + export audit
    serializers.py       # DRF serializers
    views.py             # Thin API views
    urls.py              # URL patterns
    migrations/
    tests/
```

**Layer responsibilities:**

| Layer | Responsibility |
|---|---|
| `views.py` | Parse request → call service → serialize → return response |
| `services.py` | Orchestrate selector calls + Redis caching |
| `selectors.py` | Apply user scope, delegate to aggregations |
| `aggregations.py` | PostgreSQL `annotate/aggregate` queries |
| `access.py` | Scope resolution (wraps `accounts.access`) |
| `filters.py` | Parse and validate query-string parameters |
| `export_services.py` | Generate CSV bytes + write audit record |

Views must stay thin — no business logic in views or serializers.

---

## 2. Source-of-Truth Rules

Reporting **reads** from existing transactional models. It never creates duplicate tables for transactions.

| Data Domain | Source Models |
|---|---|
| Sales | `billing.Bill`, `billing.BillItem` |
| Payments | `payments.Payment`, `payments.PaymentRefund` |
| Orders | `orders.Order`, `orders.OrderItem` |
| Kitchen | `kitchen.KitchenOrder`, `kitchen.KitchenOrderItem` |
| Inventory | `inventory.StockBalance`, `inventory.StockMovement` |
| Recipes / Consumption | `recipes.StockConsumption`, `recipes.Recipe` |
| Expenses | `financials.Expense`, `financials.SupplierInvoice` |
| Payables | `financials.Payable` |
| Accounting | `accounting.JournalEntry`, `accounting.JournalEntryLine` |
| Suppliers | `inventory.Supplier` |
| Purchases | `inventory.PurchaseOrder` |

**Prohibited models** — do not create:

- `ReportOrder`, `ReportBill`, `AnalyticsBill`, `AnalyticsInventory`
- Any copy of a transactional record for reporting purposes

The only model owned by the reporting app is `ReportExportAudit` (export event log).

---

## 3. Operational vs Accounting Metrics

There are two distinct concepts displayed in reporting:

### Operational metrics (from finalized bills)
- Based on `billing.Bill` with `status = FINALIZED`
- Used for day-to-day sales tracking
- Fast, always available, may differ from accounting by timing

### Accounting metrics (from Phase 13 posted journals)
- Based on `accounting.JournalEntry` with `status = POSTED`
- Authoritative for official financial statements
- Uses Phase 13's existing `get_profit_and_loss()`, `get_balance_sheet()` selectors

**Important:** These two numbers may legitimately differ due to:
- Accounting adjustments not reflected in operational bills
- Refunds and void bills processed after-the-fact
- Timing of accounting period closes
- Corrections posted to different periods

The `/api/reporting/financial-summary/` endpoint surfaces both values with a `source_note` field explaining the distinction. Never merge them silently into one number.

---

## 4. Permissions

All reporting permissions follow the code pattern `reporting.<area>.view`.

### View permissions

| Code | Grants access to |
|---|---|
| `reporting.dashboard.view` | `/api/reporting/dashboard/` |
| `reporting.sales.view` | Sales summary, trend, hourly |
| `reporting.orders.view` | Order summary, by-type |
| `reporting.menu.view` | Menu items, top-selling, categories |
| `reporting.branch.view` | Branch performance |
| `reporting.counter.view` | Counter performance |
| `reporting.payment.view` | Payment summary, methods |
| `reporting.refund.view` | Refund analytics |
| `reporting.discount.view` | Discount analytics |
| `reporting.kitchen.view` | Kitchen performance, items |
| `reporting.staff.view` | Waiter and cashier performance |
| `reporting.inventory.view` | Inventory summary, consumption, wastage |
| `reporting.purchase.view` | Purchase analytics |
| `reporting.supplier.view` | Supplier analytics |
| `reporting.expense.view` | Expense analytics |
| `reporting.payable.view` | Payable analytics |
| `reporting.profitability.view` | Menu profitability |
| `reporting.financial.view` | Financial summary (Phase 13 data) |

### Export permissions

| Code | Grants access to |
|---|---|
| `reporting.export.csv` | CSV export endpoint |
| `reporting.export.excel` | Reserved for future Excel export |
| `reporting.export.pdf` | Reserved for future PDF export |

### Role recommendations

| Role | Suggested reporting access |
|---|---|
| Company Head / Central Admin | All reporting permissions |
| Restaurant Owner | All reporting permissions for their restaurant |
| Restaurant Manager | Sales, orders, menu, payments, kitchen, staff, branch |
| Accountant | Financial, expense, payable, profitability |
| Cashier | Payment summary, counter performance |
| Kitchen Staff | Kitchen performance only |
| Inventory Staff | Inventory reports only |

Permissions are registered via the standard `accounts.models.Permission` model and assigned to `Role` objects. Use the existing seed command or admin to assign them.

---

## 5. Scope & Authorization

Every reporting query is scoped server-side. The frontend must never be trusted for scope decisions.

**Hierarchy:** Organization → Restaurant → Branch → Counter

### How scoping works

1. Request hits a view
2. View calls `ReportFilterParams.from_request(request)` — parses and validates query params
3. View calls service function with `user` and `filters`
4. Service calls selector
5. Selector calls `reporting.access.resolve_report_scope(user, restaurant_id, branch_id)`
6. `resolve_report_scope` validates that the requested IDs are within `acl.get_accessible_branches(user)`
7. If validation fails: raises `ReportScopeError` → 403 response
8. Aggregation is called with the scoped `accessible_branches` queryset

**A user from Restaurant A can never see Restaurant B's data**, even if they pass Restaurant B's UUID in the query string.

### Scope resolution

```python
# Returns (restaurant, branch) or raises ReportScopeError
restaurant, branch = resolve_report_scope(
    user,
    restaurant_id="...",  # optional UUID string
    branch_id="...",      # optional UUID string
)
```

---

## 6. Date / Time Handling

All reports use `date_from` and `date_to` as query parameters in `YYYY-MM-DD` format.

- Default range: last 30 days (today − 29 days → today)
- Maximum range: 730 days (2 years)
- Date ranges are validated: `date_from <= date_to`

### Bill date field

Sales reports filter by `Bill.finalized_at__date` — the authoritative financial timestamp. Not `created_at`. This correctly handles bills created at 23:58 and finalized at 00:02 the next day.

### UTC vs local time

The Django server stores all datetimes in UTC (`USE_TZ = True`). The hourly sales breakdown uses `ExtractHour("finalized_at")` which returns the UTC hour. For restaurants in non-UTC timezones, a future enhancement would annotate with a timezone-converted timestamp.

For the current implementation, hourly reports reflect UTC hours. Operators in non-UTC timezones should be aware of this offset when interpreting peak-hour data.

---

## 7. Filters

`ReportFilterParams` is the single filter object parsed from every request's query string.

### Supported parameters

| Parameter | Type | Description |
|---|---|---|
| `date_from` | `YYYY-MM-DD` | Start date (inclusive). Defaults to 30 days ago |
| `date_to` | `YYYY-MM-DD` | End date (inclusive). Defaults to today |
| `restaurant_id` | UUID | Filter by restaurant. Validated against user scope |
| `branch_id` | UUID | Filter by branch. Validated against user scope |
| `counter_id` | UUID | Filter by counter |
| `order_type` | string | `DINE_IN`, `TAKEAWAY`, `COUNTER` |
| `payment_method` | string | `CASH`, `UPI`, `CARD`, etc. |
| `menu_category_id` | UUID | Filter by menu category |
| `menu_item_id` | UUID | Filter by menu item |
| `waiter_id` | UUID | Filter by assigned waiter |
| `cashier_id` | UUID | Filter by cashier |
| `expense_category_id` | UUID | Filter by expense category |
| `supplier_id` | UUID | Filter by supplier |
| `inventory_item_id` | UUID | Filter by inventory item |
| `granularity` | `daily`/`weekly`/`monthly` | Trend chart grouping |
| `limit` | integer | Top-N limit. Default 10, max 200 |
| `sort_by` | string | `revenue`, `quantity`, `orders` |

Not every report uses every filter. Unsupported filters are silently ignored.

---

## 8. API Reference

All endpoints require authentication (`Bearer` JWT token). All return consistent JSON envelopes:

```json
{
  "period": {
    "date_from": "2026-09-05",
    "date_to": "2026-10-04"
  },
  "filters": {},
  "data": { ... }
}
```

### Full endpoint list

| Method | URL | Permission |
|---|---|---|
| GET | `/api/reporting/dashboard/` | `reporting.dashboard.view` |
| GET | `/api/reporting/sales/summary/` | `reporting.sales.view` |
| GET | `/api/reporting/sales/trend/` | `reporting.sales.view` |
| GET | `/api/reporting/sales/hourly/` | `reporting.sales.view` |
| GET | `/api/reporting/orders/summary/` | `reporting.orders.view` |
| GET | `/api/reporting/orders/by-type/` | `reporting.orders.view` |
| GET | `/api/reporting/menu/items/` | `reporting.menu.view` |
| GET | `/api/reporting/menu/top-selling/` | `reporting.menu.view` |
| GET | `/api/reporting/menu/categories/` | `reporting.menu.view` |
| GET | `/api/reporting/menu/profitability/` | `reporting.profitability.view` |
| GET | `/api/reporting/branches/performance/` | `reporting.branch.view` |
| GET | `/api/reporting/counters/performance/` | `reporting.counter.view` |
| GET | `/api/reporting/payments/summary/` | `reporting.payment.view` |
| GET | `/api/reporting/payments/methods/` | `reporting.payment.view` |
| GET | `/api/reporting/refunds/` | `reporting.refund.view` |
| GET | `/api/reporting/discounts/` | `reporting.discount.view` |
| GET | `/api/reporting/kitchen/performance/` | `reporting.kitchen.view` |
| GET | `/api/reporting/kitchen/items/` | `reporting.kitchen.view` |
| GET | `/api/reporting/staff/waiters/` | `reporting.staff.view` |
| GET | `/api/reporting/staff/cashiers/` | `reporting.staff.view` |
| GET | `/api/reporting/inventory/summary/` | `reporting.inventory.view` |
| GET | `/api/reporting/inventory/consumption/` | `reporting.inventory.view` |
| GET | `/api/reporting/inventory/wastage/` | `reporting.inventory.view` |
| GET | `/api/reporting/purchases/` | `reporting.purchase.view` |
| GET | `/api/reporting/suppliers/` | `reporting.supplier.view` |
| GET | `/api/reporting/expenses/` | `reporting.expense.view` |
| GET | `/api/reporting/payables/` | `reporting.payable.view` |
| GET | `/api/reporting/financial-summary/` | `reporting.financial.view` |
| GET | `/api/reporting/export/<report_type>/` | `reporting.export.csv` |

### Error codes

| Status | Meaning |
|---|---|
| 400 | Invalid date range, invalid filter value |
| 401 | Not authenticated |
| 403 | Insufficient permission or out-of-scope resource |
| 500 | Server error during aggregation or export |

---

## 9. Dashboard KPIs

`GET /api/reporting/dashboard/`

Returns a single consolidated payload covering all KPI sections. Cached in Redis for 60 seconds per (user, restaurant, branch) scope.

### Response structure

```json
{
  "period": { "date_from": "...", "date_to": "...", "today": "..." },
  "sales": {
    "today_net_sales": "125000.00",
    "today_bill_count": 340,
    "today_average_bill_value": "367.65",
    "yesterday_net_sales": "110000.00",
    "today_vs_yesterday_growth": "13.64",
    "week_net_sales": "...",
    "month_net_sales": "...",
    "week_vs_prev_week_growth": "...",
    "month_vs_prev_month_growth": "..."
  },
  "orders": {
    "today_total_orders": 352,
    "today_confirmed_orders": 340,
    "today_cancelled_orders": 12,
    "today_average_order_value": "..."
  },
  "products": {
    "top_revenue_item": { "rank": 1, "menu_item_name": "...", ... },
    "top_quantity_item": { ... },
    "top_category": { ... }
  },
  "payments": {
    "today_total_collected": "125000.00",
    "today_cash": "40000.00",
    "today_upi": "60000.00",
    "today_card": "22500.00",
    "today_other": "2500.00",
    "today_refund_amount": "1250.00",
    "today_refund_count": 3
  },
  "kitchen": {
    "today_orders_received": 352,
    "today_orders_ready": 340,
    "today_orders_pending": 12,
    "today_avg_prep_time_seconds": 720.0
  },
  "inventory": {
    "total_items": 145,
    "low_stock_count": 8,
    "out_of_stock_count": 2,
    "stock_value_estimate": "458000.00"
  },
  "financials": {
    "monthly_expenses": "85000.00",
    "outstanding_payables": "220000.00",
    "overdue_payables": "45000.00"
  }
}
```

### Comparison engine

Growth percentages use the formula:

```
growth_pct = ((current − previous) / previous) × 100
```

- If `previous == 0`: returns `null` (never divides by zero)
- If `previous == null`: returns `null`
- Frontend must handle `null` as "no previous data" (not "0%")

---

## 10. Sales Reports

### Sales Summary (`/api/reporting/sales/summary/`)

Only **FINALIZED** bills are counted. Draft, Cancelled, and Void bills are excluded.

| Field | Description |
|---|---|
| `gross_sales` | Sum of `Bill.subtotal` |
| `discount_amount` | Sum of `Bill.discount_amount` |
| `taxable_amount` | Sum of `Bill.taxable_amount` |
| `tax_amount` | Sum of `Bill.tax_amount` |
| `rounding_amount` | Sum of `Bill.rounding_amount` |
| `net_sales` | Sum of `Bill.grand_total` |
| `number_of_bills` | Count of finalized bills |
| `average_bill_value` | `net_sales / number_of_bills` |

### Sales Trend (`/api/reporting/sales/trend/`)

Query params: `granularity=daily|weekly|monthly`

Returns an array of rows, one per period. Empty periods are omitted (not zero-filled). Each row includes date, sales totals, bill count, order count, average bill value.

### Hourly Sales (`/api/reporting/sales/hourly/`)

Returns 24 rows (hours 0–23). Hours with no sales return `sales: 0`. Based on UTC hours of `Bill.finalized_at`.

---

## 11. Order Reports

Counts **all** orders regardless of status unless a status filter is applied.

- `total_orders` = all orders in period
- `confirmed_orders` = `status = CONFIRMED`
- `cancelled_orders` = `status = CANCELLED`
- Order type breakdown (DINE_IN / TAKEAWAY / COUNTER)

Average order value comes from finalized bills linked to confirmed orders — not from order line items directly.

---

## 12. Menu Reports

### Revenue source

Revenue **always** comes from `BillItem.total_amount` — the immutable financial snapshot at billing time. The current `MenuItem.price` is **never** used for historical revenue calculation.

### Profitability

Menu profitability requires matching `StockConsumption` records:

- Revenue: `BillItem.total_amount` per menu item
- Ingredient cost: `StockConsumption.total_cost` where `status = CONSUMED`
- Matches via: `StockConsumption.order_item → OrderItem → BillItem → menu_item`

**If no consumption records exist for a menu item**, the response returns:
```json
{
  "ingredient_cost": null,
  "gross_profit": null,
  "gross_margin_percentage": null
}
```

Never invent ingredient cost using current recipe prices for historical sales. This would produce incorrect profitability figures.

---

## 13. Payment Reports

Only **COMPLETED** payments are counted. Pending, Failed, and Cancelled payments are excluded.

Only **PROCESSED** refunds are counted. Requested or approved refunds that have not been processed are excluded.

Payment method breakdown sums `Payment.amount` grouped by `Payment.payment_method`.

---

## 14. Kitchen Reports

### Preparation time calculation

```
preparation_time = ready_at − started_at
```

- Only calculated when **both** `started_at` and `ready_at` are non-null
- If either timestamp is missing: preparation time = `null` / `"unavailable"`
- Never fabricate a duration from `preparation_time_minutes` on `KitchenOrderItem`

Average, median, and maximum preparation times are computed from the actual duration values.

### Status breakdown

| Field | Filter |
|---|---|
| `orders_received` | All kitchen orders in period |
| `orders_ready` | `status = READY` |
| `orders_cancelled` | `status = CANCELLED` |
| `orders_pending` | `status IN (NEW, ACCEPTED, PREPARING)` |

---

## 15. Inventory Reports

### Inventory Summary

Stock data is current (a snapshot), not historical. Derived from `StockBalance` records filtered by branches the user can access.

- `total_inventory_items`: distinct `InventoryItem` IDs with at least one balance
- `low_stock_items`: items where `available_quantity ≤ reorder_level`  
- `out_of_stock_items`: items where `available_quantity ≤ 0`
- `stock_value_estimate`: sum of `quantity × average_cost` across all balances

**Note:** This is an inventory valuation estimate based on weighted-average cost. It is not the same as the accounting inventory asset balance from `JournalEntryLine`. Label it clearly as an estimate.

### Wastage

Filters `StockWastage` by `status IN (APPROVED, RECORDED)`. Uses `estimated_cost` (set at approval time). Pending and rejected wastage records are excluded.

### Consumption

Filters `StockConsumption` by `status = CONSUMED`. Consumption cost comes from `total_cost` snapshots — the weighted-average cost at the time of consumption.

---

## 16. Expense & Payable Reports

### Expense status rules

| Status | Included in `approved_expenses` |
|---|---|
| `DRAFT` | No |
| `SUBMITTED` | No (counted as `pending_expenses`) |
| `APPROVED` | **Yes** |
| `REJECTED` | No |
| `CANCELLED` | No |

Only `APPROVED` expenses are counted as actual operating cost.

### Payable status

Outstanding payables: `status IN (OPEN, PARTIALLY_PAID)`  
Overdue payables: `status = OVERDUE`  
Paid: `status = PAID`

`remaining_amount` is the field used (not `amount`), since payables may be partially paid.

---

## 17. Branch & Counter Reports

### Branch Performance

Aggregates from Bill, Payment, PaymentRefund, and StockConsumption per branch.

- Revenue: from finalized bills
- Payments: from completed payments
- Refunds: from processed refunds
- Ingredient cost: from consumed stock consumption records
- Gross profit: `revenue − ingredient_cost` (null if no consumption data)

Users only see branches within their authorized scope. Company Head sees all branches in their organization.

### Counter Performance

Filters `Bill` by `order__counter__isnull=False`. Payment breakdown by method per counter uses `Payment.counter`.

---

## 18. Staff Reports

### Waiter Performance

Only available when `Order.assigned_waiter` is populated. Does not evaluate employee performance beyond operational metrics (order count, sales, cancellations). Never exposes authentication credentials or sensitive HR data.

### Cashier Performance

Based on `Payment.initiated_by` — who created the payment. Refund count based on refunds where `payment__initiated_by` matches.

---

## 19. Financial Summary

`GET /api/reporting/financial-summary/`

This endpoint delegates to Phase 13 accounting selectors for official financial data:

```python
from accounting.selectors import get_profit_and_loss, get_balance_sheet
```

Only **POSTED** journal entries are used. Draft, Void, and Reversed journals are excluded.

The response contains both:

- `accounting_*` fields — from Phase 13 posted journals (authoritative)
- `operational_*` fields — from finalized bills (operational estimate)
- `source_note` — explains the distinction

---

## 20. Profitability Rules

Two separate profitability concepts exist:

### Operational Gross Profit
```
Operational Gross Profit = Revenue (from finalized bills)
                          − Ingredient Cost (from StockConsumption)
```

- Available at menu-item level via `/api/reporting/menu/profitability/`
- Only available when StockConsumption records exist
- Missing consumption → `null` values, never invented

### Accounting Gross Profit
```
Accounting Gross Profit = Total Revenue (POSTED journal entries)
                         − Cost of Goods Sold (POSTED journal entries, COGS subtype)
```

- Available via `/api/reporting/financial-summary/` (from Phase 13)
- Authoritative for financial statements

Never combine these into one number unless both come from the same source.

---

## 21. CSV Export

`GET /api/reporting/export/<report_type>/`

Requires `reporting.export.csv` permission.

Supported report types:

| Type | Description |
|---|---|
| `sales_summary` | Sales summary row |
| `sales_trend` | Sales trend rows |
| `menu_items` | Menu item analytics |
| `menu_top_selling` | Top selling items |
| `menu_categories` | Category performance |
| `menu_profitability` | Menu profitability |
| `branch_performance` | Branch comparison |
| `payment_methods` | Payment method distribution |
| `kitchen_items` | Kitchen item performance |
| `inventory_consumption` | Consumption by item |
| `waiter_performance` | Waiter stats |
| `cashier_performance` | Cashier stats |

The export:
1. Applies identical authentication, permissions, and scope as the corresponding report endpoint
2. Generates UTF-8 CSV with BOM (for Excel compatibility)
3. Sets `Content-Disposition: attachment; filename="<type>_<date_from>_<date_to>.csv"`
4. Creates an immutable `ReportExportAudit` record

### Export audit

Every export attempt (success or failure) writes a `ReportExportAudit` record:

```python
ReportExportAudit(
    actor=request.user,
    organization=...,
    restaurant=...,
    report_type="menu_top_selling",
    export_format="CSV",
    filters_applied={...},
    status="SUCCESS",
    row_count=42,
)
```

Audit records are immutable (update is blocked at the model level).

---

## 22. Caching Strategy

Redis is used for caching expensive aggregations. Cache keys always include user + scope identifiers so data never leaks cross-restaurant.

### Cache key format

```
reporting:{suffix}:u{user_id}:r{restaurant_id}:b{branch_id}
```

### TTLs

| Report | TTL | Rationale |
|---|---|---|
| Dashboard KPIs | 60s | Live operational data |
| Sales trend | 300s | Less time-sensitive |
| Top selling items | 300s | Less time-sensitive |
| Branch summary | 300s | Aggregate, refreshes slowly |
| Inventory alerts | 120s | Important but not per-second |
| Financial data | 60s | Accuracy priority |

### Cache invalidation

Cache expires by TTL. There is no active invalidation on transaction commits — the short TTLs ensure freshness within acceptable bounds for operational dashboards.

For financial reports requiring strict accuracy (auditing, period close review), either use a very short TTL or bypass cache entirely.

---

## 23. Performance Guidelines

### Database

- All queries use `annotate/aggregate` — no Python loops over large datasets
- `select_related` and `prefetch_related` used where applicable
- Key indexes added in Phase 14 migrations:
  - `Bill(branch, status, finalized_at)`
  - `Payment(branch, status, completed_at)`
  - `Payment(branch, payment_method, status)`
  - `Order(branch, order_type, status, created_at)`
  - `StockConsumption(branch, status, consumed_at)`
  - `Expense(branch, status, expense_date)`
  - `Payable(branch, status, due_date)`
  - `KitchenOrder(branch, status, received_at)`

### Query budget (approximate, per endpoint)

| Endpoint | Max queries |
|---|---|
| Sales summary | ~3 |
| Top selling items | ~3 |
| Orders summary | ~5 |
| Payment summary | ~4 |
| Branch performance | ~6 |
| Dashboard | ~15 (multiple aggregations) |

### Pagination

All list endpoints support pagination. The default page size is 20 (configurable). Use `?limit=N` for Top-N endpoints. Do not request unbounded lists.

### Materialized views

No materialized views are implemented in Phase 14. If measured performance demands it, `DailySalesSummary` and `BranchDailySummary` can be introduced as derived tables. They must:
- Never be used as source of truth
- Be clearly marked as derived
- Support idempotent rebuilding
- Handle refunds and bill cancellations in their update logic

---

## 24. Real-Time Events

Django Channels is configured. The following WebSocket events can be emitted to invalidate frontend caches:

```json
{ "type": "reporting.dashboard.updated", "restaurant_id": "...", "branch_id": "..." }
{ "type": "reporting.sales.updated", "restaurant_id": "..." }
{ "type": "reporting.inventory.alert", "branch_id": "...", "item_id": "..." }
```

Events must only fire after a successful database commit. The PostgreSQL database remains the authoritative source — WebSocket events are hints to refetch, not data carriers.

Frontend should refetch the affected dashboard on receiving an invalidation event.

---

## 25. Data Quality Rules

Reporting must never fabricate data. The following rules are enforced:

| Situation | Correct behaviour |
|---|---|
| No finalized bills | Return `number_of_bills: 0`, not fabricated data |
| Previous period has zero sales | `growth_percentage: null`, not `Infinity` |
| Kitchen order with no `started_at` | `preparation_time: null`, not estimated |
| Menu item with no consumption records | `ingredient_cost: null`, `gross_profit: null` |
| Payable with no due date | Omit from due-date breakdown |

### What to never do

- Use current `MenuItem.price` for historical revenue
- Use current recipe ingredient quantities × current `average_cost` for historical COGS
- Return `0` when data is genuinely unavailable (use `null`)
- Return `Infinity` or `NaN` from division operations
- Silently omit refunds from refund reports
- Count DRAFT or CANCELLED bills as sales
- Count PENDING or FAILED payments as collected revenue

---

## 26. Security Rules

### Authentication

All endpoints require a valid JWT Bearer token. Unauthenticated requests return 401.

### Authorization

All endpoints check the appropriate reporting permission. Missing permission returns 403.

### Scope enforcement

Every queryset is filtered server-side to the user's authorized scope. The frontend never controls which organization/restaurant/branch data is queried.

### IDOR prevention

Passing another restaurant's UUID in `?restaurant_id=` or `?branch_id=` returns either:
- 403 (if scope validation fails explicitly)
- 200 with empty data (if the UUID is not in the user's accessible set)

Never reveal whether another restaurant's ID exists.

### Export security

Exports apply identical authentication, permissions, and scope as the corresponding report view. A CSV export cannot bypass backend filters.

---

## 27. Frontend Routes

| Route | Component |
|---|---|
| `/reports` | `ReportingDashboard` |
| `/reports/sales` | `SalesReportPage` |
| `/reports/menu` | `MenuReportPage` |
| `/reports/payments` | `PaymentsReportPage` |
| `/reports/kitchen` | `KitchenReportPage` |
| `/reports/inventory` | `InventoryReportPage` |
| `/reports/expenses` | `ExpensesReportPage` |
| `/reports/branches` | `BranchesReportPage` |

All routes are protected by `ProtectedRoute` and permission-gated in the sidebar (`REPORTING_PERMS` set).

### Charts

Uses `recharts@2.13.3`. Chart types:
- Line chart: sales trend
- Bar chart (horizontal): top selling items
- Bar chart (vertical): hourly sales, branch comparison
- Pie / donut chart: payment methods, category sales

All charts handle:
- Loading state: skeleton placeholder
- Empty data: centered empty message
- Error state: not shown inline (page-level error)

---

## 28. Testing

Tests live in `backend/reporting/tests/`.

### Test files

| File | Coverage |
|---|---|
| `base.py` | Shared fixture stack (2 orgs, 3 branches, users) |
| `test_sales_reports.py` | Finalized/draft/cancelled inclusion, totals, isolation |
| `test_order_reports.py` | Order counts, types, isolation |
| `test_product_reports.py` | Menu items, top selling, categories, profitability |
| `test_payment_reports.py` | Completed only, refunds, method distribution |
| `test_kitchen_reports.py` | Prep times with/without timestamps, status counts |
| `test_inventory_reports.py` | Stock value, low/out-of-stock detection |
| `test_expense_reports.py` | Approved only, draft/rejected excluded |
| `test_branch_reports.py` | Scope, required fields |
| `test_permissions.py` | 401, 403, 200 scenarios |
| `test_isolation.py` | Cross-org data leakage prevention |
| `test_dashboard.py` | KPI structure, comparison engine |
| `test_performance.py` | Query count upper bounds, pagination |
| `test_profitability.py` | Historical cost rules, null-when-no-consumption |
| `test_export.py` | CSV bytes, audit records, scoping |
| `test_validators.py` | Date range, top-N, filter parsing |

### Running tests

```bash
cd backend
python manage.py test reporting
```

### Phase 1–13 regression

```bash
python manage.py test
```

All existing tests must continue to pass. The reporting app is read-only and does not modify any existing model data.

---

## Changelog

| Phase | Change |
|---|---|
| 14.0 | Initial implementation — all reporting, analytics, and BI layer |
