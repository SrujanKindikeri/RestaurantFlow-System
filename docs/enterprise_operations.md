# RestaurantFlow — Enterprise Operations

**Phase 20: Multi-Branch Enterprise Operations & Configuration**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Configuration Hierarchy](#configuration-hierarchy)
4. [Effective Value Resolution](#effective-value-resolution)
5. [Allow-Listed Configuration Keys](#allow-listed-configuration-keys)
6. [Branch Lifecycle](#branch-lifecycle)
7. [Closure Workflow](#closure-workflow)
8. [Menu Rollout](#menu-rollout)
9. [Price Rollout](#price-rollout)
10. [Staff Transfer](#staff-transfer)
11. [Approval Policies](#approval-policies)
12. [Permissions](#permissions)
13. [Security & Multi-Tenant Isolation](#security--multi-tenant-isolation)
14. [APIs](#apis)
15. [Concurrency](#concurrency)
16. [Caching](#caching)
17. [Audit Trail](#audit-trail)
18. [Real-Time Events](#real-time-events)
19. [Frontend Pages](#frontend-pages)
20. [Troubleshooting](#troubleshooting)

---

## Overview

The **Enterprise** Django app (`backend/enterprise/`) provides the central management layer that sits above existing Phase 1–19 functionality. It enables a company or restaurant owner to manage multiple branches from one place while allowing per-branch overrides.

Key capabilities:

- **Configuration hierarchy** — company → restaurant → branch inheritance with effective value resolution
- **Branch lifecycle management** — open, close, reopen, maintenance, scheduled closure
- **Menu & price rollouts** — apply changes across all or selected branches atomically
- **Staff assignment & transfer** — controlled branch-to-branch movement with approval workflow
- **Approval policies** — configurable threshold-based rules without hard-coded values
- **Audit trail** — immutable append-only log for all significant enterprise actions

The enterprise app does **not** duplicate functionality from:
- Reporting (sales analytics, financial reports)
- Accounting (journal entries, ledger)
- Inventory (stock transfers, purchase orders)
- POS (counter sessions, order processing)
- Notifications (delivery channels, provider configuration)

It extends those systems through their existing services.

---

## Architecture

```
COMPANY (Organization)
   │
   ├── RESTAURANT A
   │      │
   │      ├── BRANCH A1
   │      │      ├── BranchOperationalStatus
   │      │      ├── BranchOperatingHour (7 rows, one per day)
   │      │      ├── BranchClosure (0..n)
   │      │      ├── EnterpriseConfiguration (branch-level overrides)
   │      │      └── StaffBranchAssignment
   │      │
   │      └── BRANCH A2
   │
   ├── EnterpriseConfiguration (restaurant-level defaults)
   └── ApprovalPolicy
```

**File layout:**

```
backend/enterprise/
├── models.py                  — all 11 enterprise models
├── constants.py               — all permission codes, status choices, config keys
├── exceptions.py              — domain exceptions
├── configuration_resolver.py — ConfigurationResolver (singleton service class)
├── approval_policy_resolver.py — ApprovalPolicyResolver (stateful resolver)
├── services.py                — EnterpriseConfiguration CRUD + ApprovalPolicy CRUD
├── branch_services.py         — branch lifecycle management
├── schedule_services.py       — operating hours + closure management
├── rollout_services.py        — menu availability + price rollouts
├── staff_services.py          — staff assignment + transfer workflow
├── audit_services.py          — record_audit() helper
├── access.py                  — scoped QuerySet functions (IDOR prevention)
├── selectors.py               — read-only query layer
├── validators.py              — pure validation functions
├── serializers.py             — DRF read/write serializers
├── views.py                   — thin API views
├── urls.py                    — URL routing
├── admin.py                   — Django admin registration
└── migrations/
    └── 0001_initial.py
```

---

## Configuration Hierarchy

Configurations are resolved from most-specific to least-specific:

```
Branch Override
      ↓
Restaurant Default
      ↓
Company Default
      ↓
System Default (hard-coded in constants.ALLOWED_CONFIGURATION_KEYS)
```

**Example:**

```
Company:    billing.maximum_discount_percentage = 10%
Restaurant: billing.maximum_discount_percentage = 15%
Branch A1:  billing.maximum_discount_percentage = 25%   ← branch override
Branch A2:  (no override)

Effective:
  Branch A1 → 25%    (branch override wins)
  Branch A2 → 15%    (falls back to restaurant)
```

Effective values are computed server-side by `ConfigurationResolver`. The frontend **never** merges configurations — it calls `/api/enterprise/configuration/effective/`.

### Model: EnterpriseConfiguration

| Field | Description |
|---|---|
| `company` | Organization (required at all scopes) |
| `restaurant` | Null = company-scope; set = restaurant or branch scope |
| `branch` | Null = company or restaurant scope; set = branch scope |
| `configuration_key` | Allow-listed key from `ALLOWED_CONFIGURATION_KEYS` |
| `configuration_value` | String representation (cast by resolver) |
| `value_type` | STRING / INTEGER / DECIMAL / BOOLEAN / JSON |
| `is_active` | Only one active record per key per scope (enforced by UniqueConstraints) |
| `version` | Monotonically increasing per key per scope |

Scope is derived automatically: if `branch` is set → BRANCH; if only `restaurant` is set → RESTAURANT; if neither → COMPANY.

### Model: ConfigurationChange

Immutable append-only history. `save()` raises `ValueError` on update of existing rows.

---

## Effective Value Resolution

```python
from enterprise.configuration_resolver import ConfigurationResolver

# Get a single typed value
value = ConfigurationResolver.get_effective_value(
    key="billing.maximum_discount_percentage",
    branch=branch,   # auto-derives restaurant + company
)
# Returns Decimal("25.00")

# Get value with source metadata
result = ConfigurationResolver.get_effective_config_with_source(
    key="billing.maximum_discount_percentage",
    branch=branch,
)
# Returns:
# {
#     "key": "billing.maximum_discount_percentage",
#     "value": Decimal("25.00"),
#     "raw_value": "25.00",
#     "source": "BRANCH",          # or RESTAURANT / COMPANY / SYSTEM_DEFAULT
#     "is_overridden": True,
#     "description": "Maximum discount percentage allowed...",
#     "value_type": "DECIMAL",
# }

# Full branch configuration (all keys)
full_config = ConfigurationResolver.get_branch_configuration(branch)
```

**Do not** duplicate this logic in other modules. Always call `ConfigurationResolver`.

### Cache Invalidation

Redis caches effective values for 5 minutes (`CACHE_TTL_EFFECTIVE_CONFIG = 300`).

High-impact keys (payment settings, discount maximums) bypass cache and always query the DB directly.

Cache is invalidated by `ConfigurationResolver.invalidate_cache_for_config(config)` after every mutation.

---

## Allow-Listed Configuration Keys

Only keys in `constants.ALLOWED_CONFIGURATION_KEYS` are permitted. Attempting to set an unknown key returns HTTP 400.

| Key | Type | Default | Description |
|---|---|---|---|
| `branch.default_order_type` | STRING | `dine_in` | Default order type |
| `branch.allow_takeaway` | BOOLEAN | `true` | Allow takeaway orders |
| `branch.allow_dine_in` | BOOLEAN | `true` | Allow dine-in orders |
| `branch.allow_counter_orders` | BOOLEAN | `true` | Allow counter orders |
| `branch.auto_close_enabled` | BOOLEAN | `false` | Auto-close at configured time |
| `pos.require_counter_session` | BOOLEAN | `true` | POS requires open counter session |
| `pos.allow_bill_reprint` | BOOLEAN | `true` | Allow bill reprint |
| `pos.allow_order_hold` | BOOLEAN | `true` | Allow order hold |
| `billing.allow_discount` | BOOLEAN | `true` | Allow discounts |
| `billing.maximum_discount_percentage` | DECIMAL | `10.00` | Max discount % without extra approval |
| `inventory.allow_negative_stock` | BOOLEAN | `false` | Allow stock below zero |
| `kitchen.default_priority` | INTEGER | `5` | Default kitchen order priority |
| `kitchen.delay_threshold_minutes` | INTEGER | `20` | Delay threshold (minutes) |
| `expense.approval_required` | BOOLEAN | `true` | Require expense approval |
| `expense.maximum_auto_approval_amount` | DECIMAL | `1000.00` | Auto-approval ceiling |
| `payment.cash_enabled` | BOOLEAN | `true` | Accept cash |
| `payment.upi_enabled` | BOOLEAN | `true` | Accept UPI |
| `payment.card_enabled` | BOOLEAN | `true` | Accept card |
| `customer.loyalty_enabled` | BOOLEAN | `false` | Enable loyalty program |
| `notifications.email_enabled` | BOOLEAN | `true` | Email notifications |

---

## Branch Lifecycle

### Status Values

| Status | Meaning |
|---|---|
| `ACTIVE` | Branch is operational |
| `TEMPORARILY_CLOSED` | Short-term closure (staff illness, etc.) |
| `SCHEDULED_CLOSURE` | Known upcoming closure (holiday) |
| `MAINTENANCE` | Planned maintenance downtime |
| `INACTIVE` | Branch deactivated (no new operations) |

### Valid Transitions

```
ACTIVE → TEMPORARILY_CLOSED, SCHEDULED_CLOSURE, MAINTENANCE, INACTIVE
TEMPORARILY_CLOSED → ACTIVE, INACTIVE, MAINTENANCE
SCHEDULED_CLOSURE → ACTIVE, INACTIVE
MAINTENANCE → ACTIVE, INACTIVE
INACTIVE → ACTIVE
```

### Pre-Close Checks

Before closing a branch, `check_branch_operational_blockers(branch)` is called:

- **BLOCKED** (hard stop): open counter sessions
- **WARNING** (can proceed with `force=True`): unpaid finalized bills, pending kitchen orders

Deactivating a branch does **not** delete or modify historical transactions. All past orders, bills, and payments retain their original branch context.

### API

```
POST /api/enterprise/branches/{id}/open/      — open branch
POST /api/enterprise/branches/{id}/close/     — close branch (checks blockers)
POST /api/enterprise/branches/{id}/reopen/    — reopen from any closed state
PATCH /api/enterprise/branches/{id}/status/  — generic status change
GET  /api/enterprise/branches/{id}/opening-checklist/
```

### Opening Checklist

Returns one entry per check type:

| Check | Passes when |
|---|---|
| `COUNTER_READY` | ≥1 active counter exists |
| `KITCHEN_READY` | ≥1 active kitchen station exists |
| `INVENTORY_READY` | No items at zero stock |
| `STAFF_READY` | ≥1 active staff assignment exists |
| `PAYMENT_METHODS_READY` | At least one payment method enabled via config |
| `POS_READY` | Config check on `pos.require_counter_session` |

Each item has `status`: `READY` | `WARNING` | `BLOCKED`.

---

## Closure Workflow

```
DRAFT
  ↓ (submit for approval)
PENDING_APPROVAL
  ↓ (approved)
APPROVED
  ↓ (start date reached)
ACTIVE
  ↓ (end date reached)
COMPLETED

Any non-terminal state → CANCELLED
PENDING_APPROVAL → REJECTED
```

Overlap detection prevents two non-terminal closures from covering the same date range for the same branch.

Closures are **never deleted** — cancelled/rejected closures remain as historical records.

---

## Menu Rollout

A `MenuRollout` applies a menu availability change (`is_available`) to multiple branches.

### Lifecycle

```
DRAFT → PENDING_APPROVAL → APPROVED → RUNNING → COMPLETED
                                              → PARTIALLY_COMPLETED
                                              → FAILED
     → CANCELLED (any non-terminal state)
```

### Branch Override Preservation

Unless `force_override=True`:
- A branch with `is_available` already equal to the rollout value → **SKIPPED**
- A branch that already has an active price override → **SKIPPED (OVERRIDE)**

Use the **preview endpoint** before executing to see exactly what will change:

```
POST /api/enterprise/rollouts/{id}/preview/
```

**Preview response:**

```json
{
  "rollout_id": "...",
  "total_branches": 3,
  "will_change_count": 2,
  "will_skip_count": 1,
  "branches": [
    {
      "branch_name": "Branch A1",
      "current_value": "true",
      "new_value": "false",
      "will_change": true,
      "skip_reason": null
    },
    {
      "branch_name": "Branch A2",
      "current_value": "false",
      "new_value": "false",
      "will_change": false,
      "skip_reason": "Branch already has is_available=False."
    }
  ]
}
```

### Partial Failure

If one branch fails during `execute_rollout`, execution continues for remaining branches. The rollout ends with `PARTIALLY_COMPLETED` status. `MenuRolloutBranch` records each branch's result with `FAILED` + `failure_reason`.

Bulk operation result format:

```json
{
  "successful": [{"branch_id": "...", "branch_name": "..."}],
  "failed": [{"branch_id": "...", "branch_name": "...", "error": "..."}],
  "skipped": [{"branch_id": "...", "reason": "..."}],
  "warnings": []
}
```

---

## Price Rollout

A `MenuRollout` with `rollout_type=PRICE` applies a price to branches.

**Key rule:** The existing price history is preserved — old `MenuItemPrice` rows are deactivated (`is_active=False`, `effective_to` set), not deleted. A new row is created.

If `force_override=False` (default), any branch that already has an active `MenuItemPrice` is **skipped** (its price override is preserved).

**Example:**

```
Menu item: Chicken Biryani
Restaurant default price: ₹250

Branch A1: ₹250 (set by restaurant)
Branch A2: ₹280 (branch-specific override)

Owner runs price rollout → ₹270, force_override=False

Result:
  Branch A1 → ₹270 (changed)
  Branch A2 → ₹280 (skipped — branch override preserved)
```

---

## Staff Transfer

### Workflow

```
REQUESTED → APPROVED → COMPLETED
          → REJECTED
REQUESTED / APPROVED → CANCELLED
```

### Rules

Before requesting a transfer:
1. Source and destination must be different branches.
2. Both branches must belong to the same restaurant.
3. The user must have an active `StaffBranchAssignment` at the source branch.
4. The user must not have an open `CounterSession` at the source branch (BLOCKED).
5. No other pending/approved transfer for the same user must exist.

On `COMPLETED`:
- The user's source `StaffBranchAssignment` is deactivated.
- A new `StaffBranchAssignment` is created at the destination branch.
- Historical transactions (orders, bills, inventory) retain their original branch context.

### Primary Assignment

A user can have exactly one **active primary** assignment per restaurant. Any `assign_staff_to_branch(..., is_primary=True)` call deactivates the previous primary within the same restaurant.

---

## Approval Policies

Threshold-based approval rules. Resolved hierarchically (most-specific wins):

```
Branch → Restaurant → Company → System default (no approval)
```

```python
from enterprise.approval_policy_resolver import ApprovalPolicyResolver

resolver = ApprovalPolicyResolver(
    policy_type="EXPENSE",
    branch=branch,
    amount=Decimal("12000.00"),
)

if resolver.requires_approval():
    required_permission = resolver.get_required_permission()
    # Check that the approving user has this permission
```

Or the one-shot class method:

```python
needs_approval = ApprovalPolicyResolver.check(
    policy_type="EXPENSE",
    branch=branch,
    amount=Decimal("12000.00"),
)
```

### Policy Types

| Type | Trigger |
|---|---|
| `EXPENSE` | Expense amount exceeds `threshold_amount` |
| `DISCOUNT` | Discount percentage exceeds `threshold_percentage` |
| `REFUND` | Refund amount exceeds `threshold_amount` |
| `WASTAGE` | Wastage amount exceeds threshold |
| `STOCK_TRANSFER` | Stock transfer value exceeds threshold |
| `CONFIGURATION` | High-impact configuration changes |
| `PRICE_ROLLOUT` | Price rollout requiring approval |

---

## Permissions

All enterprise permissions use the `enterprise.*` namespace.

| Code | Description |
|---|---|
| `enterprise.dashboard.view` | View enterprise dashboard |
| `enterprise.branch.view` | View branches |
| `enterprise.branch.create` | Create branches |
| `enterprise.branch.update` | Update branch settings/status |
| `enterprise.branch.open` | Open a branch |
| `enterprise.branch.close` | Close a branch |
| `enterprise.branch.reopen` | Reopen a closed branch |
| `enterprise.configuration.view` | View configuration |
| `enterprise.configuration.create` | Create new configuration entries |
| `enterprise.configuration.update` | Update existing configuration |
| `enterprise.configuration.approve` | Approve high-impact configuration changes |
| `enterprise.configuration.history.view` | View configuration history |
| `enterprise.rollout.view` | View rollouts |
| `enterprise.rollout.create` | Create rollouts |
| `enterprise.rollout.preview` | Preview rollout impact |
| `enterprise.rollout.approve` | Approve rollouts |
| `enterprise.rollout.execute` | Execute rollouts |
| `enterprise.rollout.cancel` | Cancel rollouts |
| `enterprise.staff.view` | View staff assignments |
| `enterprise.staff.assign` | Assign staff to branches |
| `enterprise.staff.transfer` | Request staff transfers |
| `enterprise.staff.transfer.approve` | Approve/reject/complete transfers |
| `enterprise.schedule.view` | View branch schedules |
| `enterprise.schedule.manage` | Manage schedules and closures |
| `enterprise.approval_policy.view` | View approval policies |
| `enterprise.approval_policy.manage` | Create/update approval policies |
| `enterprise.audit.view` | View enterprise audit log |

Permissions are assigned to `Role` objects and checked via `accounts.access.has_permission(user, code)`.

---

## Security & Multi-Tenant Isolation

Every API request enforces:

```
Authentication
+
Permission (code-based, not role-name-based)
+
Organization scope
+
Restaurant scope
+
Branch scope
```

### Cross-Tenant Prevention

The enterprise `access.py` module provides scoped QuerySet functions for every model. Views **never** use `Model.objects.get(pk=pk)` directly — they always use:

```python
ent_acl.get_accessible_configurations(user).get(pk=pk)
# Returns 404 (not 403) for unauthorized UUIDs — IDOR prevention
```

This means:
- Company A cannot read or write Company B's configurations.
- Restaurant A cannot modify Restaurant B's rollouts.
- Branch A's manager cannot access Branch B's staff.
- Cross-restaurant staff transfers are blocked at the service layer.

### Scope IDs from Payload

`company_id`, `restaurant_id`, and `branch_id` in request payloads are **hints only**. The backend validates them against the authenticated user's accessible scope. A user cannot escalate scope by injecting a foreign UUID.

---

## APIs

Base path: `/api/enterprise/`

### Dashboard

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/dashboard/` | `enterprise.dashboard.view` |

### Branch Management

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/branches/` | `enterprise.branch.view` |
| GET | `/api/enterprise/branches/{id}/` | `enterprise.branch.view` |
| PATCH | `/api/enterprise/branches/{id}/status/` | `enterprise.branch.update` |
| POST | `/api/enterprise/branches/{id}/open/` | `enterprise.branch.open` |
| POST | `/api/enterprise/branches/{id}/close/` | `enterprise.branch.close` |
| POST | `/api/enterprise/branches/{id}/reopen/` | `enterprise.branch.reopen` |
| GET | `/api/enterprise/branches/{id}/opening-checklist/` | `enterprise.branch.view` |

### Schedules

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/schedules/?branch_id=...` | `enterprise.schedule.view` |
| POST | `/api/enterprise/schedules/` | `enterprise.schedule.manage` |
| PUT | `/api/enterprise/schedules/bulk/` | `enterprise.schedule.manage` |

### Closures

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/closures/?branch_id=...` | `enterprise.schedule.view` |
| POST | `/api/enterprise/closures/` | `enterprise.schedule.manage` |
| GET | `/api/enterprise/closures/{id}/` | `enterprise.schedule.view` |
| POST | `/api/enterprise/closures/{id}/approve/` | `enterprise.schedule.manage` |
| POST | `/api/enterprise/closures/{id}/reject/` | `enterprise.schedule.manage` |
| POST | `/api/enterprise/closures/{id}/cancel/` | `enterprise.schedule.manage` |

### Configuration

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/configuration/` | `enterprise.configuration.view` |
| POST | `/api/enterprise/configuration/` | `enterprise.configuration.create` |
| POST | `/api/enterprise/configuration/bulk/` | `enterprise.configuration.update` |
| GET | `/api/enterprise/configuration/effective/` | `enterprise.configuration.view` |
| GET | `/api/enterprise/configuration/history/` | `enterprise.configuration.history.view` |
| GET | `/api/enterprise/configuration/{id}/` | `enterprise.configuration.view` |
| PATCH | `/api/enterprise/configuration/{id}/` | `enterprise.configuration.update` |
| POST | `/api/enterprise/configuration/{id}/rollback/` | `enterprise.configuration.update` |

### Rollouts

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/rollouts/?restaurant_id=...` | `enterprise.rollout.view` |
| POST | `/api/enterprise/rollouts/` | `enterprise.rollout.create` |
| GET | `/api/enterprise/rollouts/{id}/` | `enterprise.rollout.view` |
| POST | `/api/enterprise/rollouts/{id}/preview/` | `enterprise.rollout.preview` |
| POST | `/api/enterprise/rollouts/{id}/approve/` | `enterprise.rollout.approve` |
| POST | `/api/enterprise/rollouts/{id}/execute/` | `enterprise.rollout.execute` |
| POST | `/api/enterprise/rollouts/{id}/cancel/` | `enterprise.rollout.cancel` |

### Staff

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/staff/?restaurant_id=...` | `enterprise.staff.view` |
| GET | `/api/enterprise/staff/assignments/?branch_id=...` | `enterprise.staff.view` |
| POST | `/api/enterprise/staff/assign/` | `enterprise.staff.assign` |
| GET | `/api/enterprise/staff/transfers/?restaurant_id=...` | `enterprise.staff.view` |
| POST | `/api/enterprise/staff/transfers/` | `enterprise.staff.transfer` |
| GET | `/api/enterprise/staff/transfers/{id}/` | `enterprise.staff.view` |
| POST | `/api/enterprise/staff/transfers/{id}/approve/` | `enterprise.staff.transfer.approve` |
| POST | `/api/enterprise/staff/transfers/{id}/reject/` | `enterprise.staff.transfer.approve` |
| POST | `/api/enterprise/staff/transfers/{id}/complete/` | `enterprise.staff.transfer.approve` |
| POST | `/api/enterprise/staff/transfers/{id}/cancel/` | authenticated |

### Approval Policies

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/approval-policies/` | `enterprise.approval_policy.view` |
| POST | `/api/enterprise/approval-policies/` | `enterprise.approval_policy.manage` |
| GET | `/api/enterprise/approval-policies/{id}/` | `enterprise.approval_policy.view` |
| PATCH | `/api/enterprise/approval-policies/{id}/` | `enterprise.approval_policy.manage` |

### Audit

| Method | Path | Permission |
|---|---|---|
| GET | `/api/enterprise/audit/` | `enterprise.audit.view` |

---

## Concurrency

The following operations use `select_for_update()` inside `transaction.atomic()`:

| Operation | Concurrency protection |
|---|---|
| `set_configuration` | Locks existing active config row before deactivating |
| `upsert_operating_hour` | `get_or_create` + `select_for_update` prevents race |
| `open/close/reopen_branch` | Locks `BranchOperationalStatus` before transition |
| `approve_branch_closure` | Locks closure row; re-validates status |
| `approve/reject/complete_staff_transfer` | Locks transfer row; re-validates status |
| `execute_rollout` | Sets status to `RUNNING` atomically before branch loop |

Rollout execution applies changes to each branch in a **per-branch `transaction.atomic()`**. A single branch failure does not abort the remaining branches.

---

## Caching

Redis is used for effective configuration caching.

**Cache key format:**

```
enterprise:config:{company_id}:{restaurant_id}:{branch_id}:{key}
```

**TTLs:**

| Setting | TTL |
|---|---|
| Normal keys | 300 seconds (5 minutes) |
| High-impact keys (payment, discount max) | 0 (bypass cache, always DB) |

**High-impact keys** (never cached):

```
pos.require_counter_session
billing.maximum_discount_percentage
payment.cash_enabled
payment.upi_enabled
payment.card_enabled
expense.maximum_auto_approval_amount
```

Cache is always invalidated after `set_configuration()` completes. Invalidation is broad: it clears the key at company, restaurant, and all branch levels.

---

## Audit Trail

`EnterpriseAuditLog` is append-only. Calling `.save()` on an existing row raises `ValueError`.

All significant enterprise actions write an audit entry via `record_audit()` in `audit_services.py`. Audit failures are logged at WARNING level but **never** roll back the business operation.

**Audit actions:**

| Action | Trigger |
|---|---|
| `BRANCH_OPENED` | Branch opened |
| `BRANCH_CLOSED` | Branch closed |
| `BRANCH_REOPENED` | Branch reopened |
| `BRANCH_STATUS_CHANGED` | Generic status change |
| `CONFIGURATION_CREATED` | New config entry |
| `CONFIGURATION_UPDATED` | Config entry updated |
| `CONFIGURATION_ROLLED_BACK` | Config rolled back |
| `MENU_ROLLOUT_CREATED` | Rollout created |
| `MENU_ROLLOUT_APPROVED` | Rollout approved |
| `MENU_ROLLOUT_EXECUTED` | Rollout completed |
| `MENU_ROLLOUT_FAILED` | Rollout failed |
| `PRICE_ROLLOUT_CREATED` | Price rollout created |
| `PRICE_ROLLOUT_EXECUTED` | Price rollout executed |
| `STAFF_ASSIGNED` | Staff assignment created |
| `STAFF_TRANSFER_REQUESTED` | Transfer requested |
| `STAFF_TRANSFER_APPROVED` | Transfer approved |
| `STAFF_TRANSFER_REJECTED` | Transfer rejected |
| `STAFF_TRANSFER_COMPLETED` | Transfer completed |
| `APPROVAL_POLICY_CREATED` | Policy created |
| `APPROVAL_POLICY_UPDATED` | Policy updated |

**Never store secrets in audit metadata.** Use key names, not values.

---

## Real-Time Events

Events are published via Django Channels to the group `enterprise_org_{company_id}`.

| Event | Trigger |
|---|---|
| `enterprise.branch.status_changed` | Branch opened/closed/reopened |
| `enterprise.configuration.updated` | Any configuration mutation |
| `enterprise.rollout.created` | Rollout created |
| `enterprise.rollout.completed` | Rollout successfully completed |
| `enterprise.rollout.failed` | Rollout failed |
| `enterprise.staff.transfer.created` | Transfer request submitted |
| `enterprise.staff.transfer.completed` | Transfer completed |
| `enterprise.schedule.updated` | Operating hours or closure changed |

Events are published **after** the DB transaction commits. PostgreSQL is always the source of truth.

WebSocket publish failures are caught and logged at WARNING level — they never block business operations.

---

## Frontend Pages

| Route | Component | Description |
|---|---|---|
| `/enterprise` | `EnterpriseDashboard` | KPI summary + quick navigation |
| `/enterprise/branches` | `EnterpriseBranchesPage` | Branch list with status filter |
| `/enterprise/branches/:id` | `EnterpriseBranchDetailPage` | Branch detail: status, checklist, hours, closures |
| `/enterprise/configuration` | `EnterpriseConfigurationPage` | Config grouped by category, source-tagged, inline edit |
| `/enterprise/rollouts` | `EnterpriseRolloutsPage` | Rollout list with preview modal + execute |
| `/enterprise/staff` | `EnterpriseStaffPage` | Staff assignments + transfers (tabbed) |
| `/enterprise/approval-policies` | `EnterpriseApprovalPoliciesPage` | Policy management per scope |
| `/enterprise/audit` | `EnterpriseAuditPage` | Immutable audit log with filters |

API service: `frontend/src/services/enterprise.ts`

---

## Troubleshooting

### "Configuration key not permitted"

The key is not in `ALLOWED_CONFIGURATION_KEYS` in `enterprise/constants.py`. Add it to the allow-list there (and a corresponding migration if you add a new Choice).

### "No previous version to roll back to"

The configuration has only one version (was just created). Rollback requires at least one prior `ConfigurationChange` record with a non-empty `old_value`.

### "Branch has open operations that must be resolved"

A counter session is still open at this branch. Close the session via the POS/Counter workflow before attempting branch closure.

### "An active rollout already exists"

A `MenuRollout` in status `DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `SCHEDULED`, or `RUNNING` exists for the same `menu_item` + `restaurant` combination. Cancel or complete the existing rollout first.

### "Staff transfer cannot proceed — user has active operational sessions"

The staff member being transferred has an open `CounterSession`. The session must be closed via the Counter workflow before the transfer can be completed.

### Stale effective configuration

If a cached value appears stale, invalidate manually:

```python
from enterprise.configuration_resolver import ConfigurationResolver
ConfigurationResolver.invalidate_cache_for_config(config)
```

Or reduce `CACHE_TTL_EFFECTIVE_CONFIG` in `constants.py` for high-sensitivity environments.

### Audit log corruption attempt

`EnterpriseAuditLog.save()` and `ConfigurationChange.save()` raise `ValueError` if called on an existing row. This is by design. Use the Django admin or direct DB access (with extreme caution) for disaster recovery only.
