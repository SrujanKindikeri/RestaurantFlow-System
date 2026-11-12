# Central Control Center — Phase 15

RestaurantFlow Central Control Center (CCC) is an organization-wide observability and exception-management layer that sits above restaurant-level operations. It gives Company Heads and Central Admins a single view of the health, alerts, and issues across all restaurants and branches in their organization.

---

## Architecture

```
Company (Organization)
  └── Central Control Center   ← Phase 15
        ├── System Health
        ├── Restaurant Health (per restaurant)
        ├── Branch Health (per branch)
        ├── Operational Alerts
        ├── Central Issues
        ├── Event Timeline
        ├── User Access Visibility
        └── Configuration

Company
  ├── Restaurant A → Branch A1, Branch A2
  ├── Restaurant B → Branch B1
  └── Restaurant C → Branch C1, Branch C2, Branch C3
```

Central Control does **not** replace:
- Restaurant Owner dashboard
- Restaurant Manager dashboard  
- Kitchen Display System
- Inventory management
- Accounting/reporting

It observes, detects, prioritizes, and escalates — it does not execute restaurant-level transactions.

---

## Scope Model

Every API call and WebSocket connection is authorized against the requesting user's scope:

| Role | Visible Scope |
|------|---------------|
| Superuser | All organizations |
| COMPANY_HEAD | All restaurants/branches in their org |
| CENTRAL_ADMIN | All restaurants/branches in their org (per permissions) |
| RESTAURANT_OWNER | **Not granted CC access by default** |
| RESTAURANT_MANAGER | **Not granted CC access by default** |
| Branch-level roles | **Not granted CC access** |

Scope is enforced server-side via `accounts.access`. Frontend route guards are supplementary — the backend is authoritative.

---

## Django App

```
backend/central_control/
├── models.py            # CentralControlSettings, CentralAlert, EscalationRule,
│                        # CentralIssue, CentralSystemEvent, CentralControlAuditLog
├── constants.py         # All permission codes, status constants, alert types,
│                        # health statuses, WebSocket event types, cache keys
├── exceptions.py        # Business logic and API exceptions
├── validators.py        # Field-level and business-rule validators
├── alert_rules.py       # AlertDetectionService, EscalationEngine, deduplication logic
├── health_services.py   # RestaurantHealthService, SystemHealthService
├── selectors.py         # Read-only scoped query layer
├── services.py          # AlertService lifecycle + audit/broadcast helpers
├── issue_services.py    # IssueService full workflow
├── dashboard_services.py# Central dashboard + restaurant health + system health (cached)
├── permissions.py       # DRF permission classes
├── serializers.py       # Input/output serializers for all endpoints
├── views.py             # Thin API views (20 endpoints)
├── urls.py              # URL routing
├── consumers.py         # WebSocket consumer (AsyncWebsocketConsumer)
├── routing.py           # WebSocket URL patterns
├── admin.py             # Django admin registration
└── tests/               # Test suite (alerts, issues, health, permissions, scope, escalation, realtime)
```

---

## Dashboard

`GET /api/central-control/dashboard/`

Returns organization-level KPIs assembled from:
- Restaurant/branch counts
- Today's orders and sales (from billing.Bill)
- Kitchen pending and delayed orders
- Inventory low/out-of-stock counts
- Financial: pending expenses, overdue payables
- Active alert counts by severity
- Active issue counts

Requires: `central_control.dashboard.view`

Cached in Redis at 30-second TTL, scoped to organization_id.

---

## Restaurant Health

`GET /api/central-control/restaurants/health/`

Returns a health status for each accessible restaurant, computed by `RestaurantHealthService`.

Requires: `central_control.health.view`

### Health Rule Engine

Health status is derived from explicit rules evaluated in severity order:

| Status | Conditions |
|--------|-----------|
| OFFLINE | `restaurant.is_active = False` OR all branches inactive |
| CRITICAL | Any unresolved CRITICAL alert exists OR >50% branches inactive OR >5 delayed kitchen orders |
| WARNING | Any HIGH alert exists OR out-of-stock items exist OR >5 low-stock items OR overdue payables OR >3 open issues OR any delayed kitchen orders |
| HEALTHY | None of the above conditions met |

Thresholds are configurable via `CentralControlSettings`.

---

## Alerts

### Alert Types

| Type | Source |
|------|--------|
| KITCHEN_DELAY | KitchenOrder PREPARING beyond threshold |
| KITCHEN_BACKLOG | Too many active kitchen orders in a branch |
| LOW_STOCK | StockBalance.available_quantity <= InventoryItem.reorder_level |
| OUT_OF_STOCK | StockBalance.available_quantity <= 0 |
| PAYMENT_FAILURE | High failed payment count in a branch today |
| PAYMENT_EXCEPTION | Unresolved payment exceptions |
| REFUND_EXCEPTION | Refund processing issues |
| EXPENSE_PENDING | Submitted expense awaiting approval >3 days |
| PAYABLE_OVERDUE | Payable.status = OVERDUE |
| ACCOUNTING_EXCEPTION | Accounting posting failures |
| COUNTER_SESSION_EXCEPTION | Long-open or force-closed sessions with cash differences |
| BRANCH_INACTIVE | Branch deactivated |
| RESTAURANT_INACTIVE | Restaurant deactivated |
| USER_ACCESS_EXCEPTION | Unusual permission/role changes |
| SYSTEM_HEALTH | Infrastructure degradation |
| DATA_INTEGRITY | Data integrity issues |
| UNUSUAL_ACTIVITY | Unusual operational patterns |

### Alert Lifecycle

```
OPEN
  ├── → ACKNOWLEDGED
  │         └── → RESOLVED (terminal)
  │         └── → DISMISSED (terminal)
  ├── → RESOLVED (terminal)
  ├── → DISMISSED (terminal)
  └── → EXPIRED (terminal, automatic)
```

Critical alerts require a non-empty `resolution_note` to resolve.

### Deduplication

Each alert has a `fingerprint` field — an SHA-256 digest of:
```
alert_type | source_type | source_id | org_id | restaurant_id | branch_id
```

A `UniqueConstraint` on `(organization, fingerprint, status)` filtered to `status IN ('OPEN', 'ACKNOWLEDGED')` prevents duplicate active alerts for the same condition. Re-detection increments `detection_count` and updates `last_detected_at`.

### Alert Storm Prevention

- Deduplication via fingerprint
- Automatic resolution when underlying condition clears (e.g. stock replenished)
- Alert detection services are idempotent — safe to call repeatedly
- Concurrent detection workers are safe via `select_for_update()`

---

## Alert Detection Service

`AlertDetectionService` in `alert_rules.py` reads from:
- `KitchenOrder` (kitchen delays and backlogs)
- `StockBalance` + `InventoryItem` (low/out-of-stock)
- `Payment` (payment failure counts)
- `Expense` + `Payable` (financial exceptions)
- `CounterSession` (long-open and force-closed sessions)

All detection methods are:
- **Idempotent** — safe to run multiple times
- **Read-only** — never modify source records
- **Atomic** — wrapped in `transaction.atomic()`

To run detection manually (staff/superuser only):
```
POST /api/central-control/run-detection/
```

---

## Issues

### Issue Workflow

```
OPEN
  ├── → ASSIGNED
  │         └── → IN_PROGRESS
  │                   └── → RESOLVED
  │                               └── → CLOSED (terminal, immutable)
  └── → CANCELLED (terminal)
```

CLOSED issues are immutable — no further changes are permitted.

### Issue Assignment

Assignee scope is validated: the assigned user must have a role that covers the issue's restaurant/branch scope. Assigning a branch issue to a user without branch access raises `IssueAssignmentScopeError`.

### Alert → Issue Escalation

`EscalationRule` records define when an unresolved alert auto-creates a `CentralIssue`:

```python
EscalationRule(
    alert_type  = "KITCHEN_DELAY",
    severity    = "HIGH",
    threshold_minutes = 30,
    auto_create_issue = True,
    escalation_target_role = "RESTAURANT_MANAGER",
)
```

The `EscalationEngine.run()` method:
1. Finds active alerts older than `threshold_minutes`
2. Checks no existing active issue is already linked
3. Creates a `CentralIssue` referencing the alert

---

## Central Event Timeline

`GET /api/central-control/events/`

An append-only stream of significant operational events:
- Kitchen delays detected/resolved
- Alert created/resolved
- Issue created/resolved
- Branch status changes
- Accounting exceptions
- User access events

Events are `CentralSystemEvent` records created by services during state transitions. They are **never deleted**.

---

## System Health

`GET /api/central-control/system-health/`

Performs lightweight application-level checks. Returns:

```json
{
  "overall": "HEALTHY",
  "api": "HEALTHY",
  "database": "HEALTHY",
  "redis": "HEALTHY",
  "workers": "UNKNOWN",
  "websocket": "HEALTHY",
  "checked_at": "2026-10-04T10:30:00Z"
}
```

Component statuses: `HEALTHY | DEGRADED | UNAVAILABLE | UNKNOWN`

**Security rules:**
- Never exposes database URLs, Redis URLs, passwords, or secrets
- Uses try/except with timeouts on every check
- Returns DEGRADED rather than crashing on partial failures
- Stack traces are never sent to frontend users

---

## Real-Time Events (WebSocket)

**URL:** `ws://host/ws/central-control/<organization_id>/`

**Group name:** `company_{organization_id}_central_control`

### Authentication

Follows the same pattern as the Kitchen consumer (Phase 7):
1. JWT from query string `?token=<jwt>` or `AuthMiddlewareStack`
2. Must have `central_control.dashboard.view` permission
3. Must have access to the requested organization

Unauthorized connections are closed with specific codes:
- `4001` — unauthenticated
- `4003` — insufficient permission
- `4004` — organization not accessible
- `4005` — channel layer error

### Events

| Event Type | Triggered By |
|-----------|-------------|
| `central.alert.created` | New alert detected |
| `central.alert.updated` | Alert acknowledged/dismissed |
| `central.alert.resolved` | Alert resolved |
| `central.issue.created` | New issue created |
| `central.issue.updated` | Issue status changed |
| `central.issue.resolved` | Issue resolved |
| `central.health.updated` | Restaurant health status changed |
| `central.restaurant.status_changed` | Restaurant activated/deactivated |
| `central.branch.status_changed` | Branch activated/deactivated |

### Reconnection

On connect or `sync` message, the consumer sends a `central.sync` message with current alert and issue counts. Frontend should use REST resync after reconnection to fill any gaps.

---

## Permissions

All permissions are in `central_control.constants.ALL_CENTRAL_CONTROL_PERMISSIONS`.

| Permission Code | Grants |
|-----------------|--------|
| `central_control.dashboard.view` | View main dashboard |
| `central_control.restaurant.view` | View restaurant overview |
| `central_control.branch.view` | View branch overview |
| `central_control.alert.view` | List and view alerts |
| `central_control.alert.acknowledge` | Acknowledge alerts |
| `central_control.alert.resolve` | Resolve alerts |
| `central_control.alert.dismiss` | Dismiss alerts |
| `central_control.issue.view` | List and view issues |
| `central_control.issue.create` | Create issues |
| `central_control.issue.assign` | Assign issues |
| `central_control.issue.update` | Update issue fields and start |
| `central_control.issue.resolve` | Resolve issues |
| `central_control.issue.close` | Close issues |
| `central_control.health.view` | View health status |
| `central_control.system_event.view` | View event timeline |
| `central_control.audit.view` | View audit log |
| `central_control.user_access.view` | View user access info |
| `central_control.user_access.manage` | Manage user access |
| `central_control.configuration.view` | View settings |
| `central_control.configuration.manage` | Update settings |
| `central_control.export` | Export data |

---

## Security

- All endpoints enforce: authentication + permission + company scope
- Backend is authoritative — frontend guards are supplementary
- WebSocket group membership derived server-side from validated organization
- Cross-company data leakage prevented at selector layer
- Audit log is immutable (`save()` raises `ValueError` on update)
- System health never exposes credentials or infrastructure details
- User access endpoint exposes minimum required fields (no passwords/tokens)

---

## Caching

Redis caching uses organization-scoped keys — never shared across companies.

| Data | Cache Key | TTL |
|------|-----------|-----|
| Dashboard | `central_control:dashboard:org:{org_id}` | 30s |
| Restaurant health | `central_control:restaurant_health:org:{org_id}` | 60s |
| Alert counts | `central_control:alert_counts:org:{org_id}` | 15s |
| System health | `central_control:system_health` | 120s |

Cache is invalidated by `invalidate_dashboard_cache(organization_id)` after significant state changes.

---

## Configuration

`CentralControlSettings` (one per Organization):

| Field | Default | Description |
|-------|---------|-------------|
| `kitchen_delay_minutes` | 20 | Minutes before PREPARING order is delayed |
| `kitchen_backlog_threshold` | 15 | Active orders before BACKLOG alert |
| `low_stock_alert_enabled` | True | Toggle LOW_STOCK alerts |
| `out_of_stock_alert_enabled` | True | Toggle OUT_OF_STOCK alerts |
| `payable_overdue_alert_enabled` | True | Toggle PAYABLE_OVERDUE alerts |
| `payment_failure_threshold` | 5 | Failed payments per day per branch before alert |
| `counter_session_max_hours` | 16 | Hours before open session is flagged |
| `alert_escalation_enabled` | True | Master switch for escalation engine |
| `issue_auto_creation_enabled` | True | Allow escalation to auto-create issues |

---

## Audit Events

Every Central Control action produces an immutable `CentralControlAuditLog` entry:

| Action | Triggered By |
|--------|-------------|
| `CENTRAL_ALERT_ACKNOWLEDGED` | AlertService.acknowledge_alert() |
| `CENTRAL_ALERT_RESOLVED` | AlertService.resolve_alert() |
| `CENTRAL_ALERT_DISMISSED` | AlertService.dismiss_alert() |
| `CENTRAL_ISSUE_CREATED` | IssueService.create_issue() |
| `CENTRAL_ISSUE_ASSIGNED` | IssueService.assign_issue() |
| `CENTRAL_ISSUE_UPDATED` | IssueService.update_issue() |
| `CENTRAL_ISSUE_RESOLVED` | IssueService.resolve_issue() |
| `CENTRAL_ISSUE_CLOSED` | IssueService.close_issue() |
| `CENTRAL_ISSUE_CANCELLED` | IssueService.cancel_issue() |
| `CENTRAL_CONFIGURATION_UPDATED` | CentralSettingsView.patch() |

---

## Database Indexes

All models have indexes on commonly filtered fields:
- `CentralAlert`: organization+status, organization+severity, organization+alert_type, restaurant+status, branch+status, fingerprint, detected_at, source_type+source_id, expires_at
- `CentralIssue`: organization+status, organization+severity, restaurant+status, branch+status, assigned_to+status, due_at, status+created_at
- `CentralSystemEvent`: organization+occurred_at, organization+event_type, restaurant+occurred_at, branch+occurred_at
- `CentralControlAuditLog`: actor+created_at, action+created_at, entity_type+entity_id, organization+created_at

---

## Frontend Pages

| Route | Component | Required Permission |
|-------|-----------|---------------------|
| `/central-control` | `CentralControlDashboard` | `central_control.dashboard.view` |
| `/central-control/alerts` | `AlertCenterPage` | `central_control.alert.view` |
| `/central-control/issues` | `IssueCenterPage` | `central_control.issue.view` |
| `/central-control/restaurants/health` | `RestaurantHealthPage` | `central_control.health.view` |
| `/central-control/system-health` | `SystemHealthPage` | `central_control.health.view` |
| `/central-control/events` | `EventTimelinePage` | `central_control.system_event.view` |

---

## Performance

- Dashboard aggregations use `Sum`, `Count`, `Avg` at the database level (no Python-level loops)
- `select_related` and `prefetch_related` prevent N+1 queries
- All list endpoints are paginated (default page size 20, max 200)
- Detection services query across all restaurants in one pass (not one query per restaurant)
- Redis caching prevents repeated expensive aggregations within TTL windows

---

## Background Detection

Celery is configured in `config/settings.py` but not yet wired (`celery.py` not created). The detection services are designed to be called from Celery periodic tasks when the infrastructure is activated:

```python
# Suggested periodic tasks (add when Celery is activated):
# Every 5 minutes: kitchen + inventory + financial alerts
# Every 10 minutes: system health checks
# Every 1 hour: expire stale alerts

@shared_task
def run_detection_for_all_orgs():
    for org in Organization.objects.filter(is_active=True):
        svc = AlertDetectionService(org)
        svc.run_all()
        EscalationEngine(org).run()
```

Until Celery is activated, detection can be triggered via:
```
POST /api/central-control/run-detection/   (staff/superuser only)
```
