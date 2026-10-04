# =============================================================================
# RestaurantFlow — Central Control Center Constants
# Phase 15
#
# All permission codes, status constants, alert types, severity levels,
# issue categories, health statuses, and cache configuration live here.
# Import from here — never hard-code magic strings in models, services or views.
# =============================================================================

from decimal import Decimal

# ---------------------------------------------------------------------------
# Decimal sentinels
# ---------------------------------------------------------------------------
ZERO = Decimal("0.00")
DECIMAL_MONEY = Decimal("0.01")

# ---------------------------------------------------------------------------
# Permission codes
# ---------------------------------------------------------------------------

PERM_DASHBOARD_VIEW       = "central_control.dashboard.view"
PERM_RESTAURANT_VIEW      = "central_control.restaurant.view"
PERM_BRANCH_VIEW          = "central_control.branch.view"
PERM_ALERT_VIEW           = "central_control.alert.view"
PERM_ALERT_ACKNOWLEDGE    = "central_control.alert.acknowledge"
PERM_ALERT_RESOLVE        = "central_control.alert.resolve"
PERM_ALERT_DISMISS        = "central_control.alert.dismiss"
PERM_ISSUE_VIEW           = "central_control.issue.view"
PERM_ISSUE_CREATE         = "central_control.issue.create"
PERM_ISSUE_ASSIGN         = "central_control.issue.assign"
PERM_ISSUE_UPDATE         = "central_control.issue.update"
PERM_ISSUE_RESOLVE        = "central_control.issue.resolve"
PERM_ISSUE_CLOSE          = "central_control.issue.close"
PERM_HEALTH_VIEW          = "central_control.health.view"
PERM_SYSTEM_EVENT_VIEW    = "central_control.system_event.view"
PERM_AUDIT_VIEW           = "central_control.audit.view"
PERM_USER_ACCESS_VIEW     = "central_control.user_access.view"
PERM_USER_ACCESS_MANAGE   = "central_control.user_access.manage"
PERM_CONFIGURATION_VIEW   = "central_control.configuration.view"
PERM_CONFIGURATION_MANAGE = "central_control.configuration.manage"
PERM_EXPORT               = "central_control.export"

# Full list for seed command: (code, name, module, action)
ALL_CENTRAL_CONTROL_PERMISSIONS = [
    (PERM_DASHBOARD_VIEW,       "View Central Control Dashboard",  "central_control", "dashboard.view"),
    (PERM_RESTAURANT_VIEW,      "View Restaurant Overview",         "central_control", "restaurant.view"),
    (PERM_BRANCH_VIEW,          "View Branch Overview",             "central_control", "branch.view"),
    (PERM_ALERT_VIEW,           "View Central Alerts",              "central_control", "alert.view"),
    (PERM_ALERT_ACKNOWLEDGE,    "Acknowledge Central Alerts",       "central_control", "alert.acknowledge"),
    (PERM_ALERT_RESOLVE,        "Resolve Central Alerts",           "central_control", "alert.resolve"),
    (PERM_ALERT_DISMISS,        "Dismiss Central Alerts",           "central_control", "alert.dismiss"),
    (PERM_ISSUE_VIEW,           "View Central Issues",              "central_control", "issue.view"),
    (PERM_ISSUE_CREATE,         "Create Central Issues",            "central_control", "issue.create"),
    (PERM_ISSUE_ASSIGN,         "Assign Central Issues",            "central_control", "issue.assign"),
    (PERM_ISSUE_UPDATE,         "Update Central Issues",            "central_control", "issue.update"),
    (PERM_ISSUE_RESOLVE,        "Resolve Central Issues",           "central_control", "issue.resolve"),
    (PERM_ISSUE_CLOSE,          "Close Central Issues",             "central_control", "issue.close"),
    (PERM_HEALTH_VIEW,          "View System Health",               "central_control", "health.view"),
    (PERM_SYSTEM_EVENT_VIEW,    "View System Events",               "central_control", "system_event.view"),
    (PERM_AUDIT_VIEW,           "View Central Audit Log",           "central_control", "audit.view"),
    (PERM_USER_ACCESS_VIEW,     "View User Access Information",     "central_control", "user_access.view"),
    (PERM_USER_ACCESS_MANAGE,   "Manage User Access",               "central_control", "user_access.manage"),
    (PERM_CONFIGURATION_VIEW,   "View Central Configuration",       "central_control", "configuration.view"),
    (PERM_CONFIGURATION_MANAGE, "Manage Central Configuration",     "central_control", "configuration.manage"),
    (PERM_EXPORT,               "Export Central Control Data",      "central_control", "export"),
]

# ---------------------------------------------------------------------------
# Alert Severity
# ---------------------------------------------------------------------------
SEVERITY_INFO     = "INFO"
SEVERITY_LOW      = "LOW"
SEVERITY_MEDIUM   = "MEDIUM"
SEVERITY_HIGH     = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

ALERT_SEVERITY_CHOICES = [
    (SEVERITY_INFO,     "Info"),
    (SEVERITY_LOW,      "Low"),
    (SEVERITY_MEDIUM,   "Medium"),
    (SEVERITY_HIGH,     "High"),
    (SEVERITY_CRITICAL, "Critical"),
]

# Severity ordering (lower = less severe)
SEVERITY_ORDER = {
    SEVERITY_INFO:     0,
    SEVERITY_LOW:      1,
    SEVERITY_MEDIUM:   2,
    SEVERITY_HIGH:     3,
    SEVERITY_CRITICAL: 4,
}

# ---------------------------------------------------------------------------
# Alert Status
# ---------------------------------------------------------------------------
ALERT_OPEN         = "OPEN"
ALERT_ACKNOWLEDGED = "ACKNOWLEDGED"
ALERT_RESOLVED     = "RESOLVED"
ALERT_DISMISSED    = "DISMISSED"
ALERT_EXPIRED      = "EXPIRED"

ALERT_STATUS_CHOICES = [
    (ALERT_OPEN,         "Open"),
    (ALERT_ACKNOWLEDGED, "Acknowledged"),
    (ALERT_RESOLVED,     "Resolved"),
    (ALERT_DISMISSED,    "Dismissed"),
    (ALERT_EXPIRED,      "Expired"),
]

ALERT_VALID_TRANSITIONS: dict[str, list[str]] = {
    ALERT_OPEN:         [ALERT_ACKNOWLEDGED, ALERT_RESOLVED, ALERT_DISMISSED, ALERT_EXPIRED],
    ALERT_ACKNOWLEDGED: [ALERT_RESOLVED, ALERT_DISMISSED],
    ALERT_RESOLVED:     [],   # terminal
    ALERT_DISMISSED:    [],   # terminal
    ALERT_EXPIRED:      [],   # terminal
}

# Statuses that block new alerts of the same fingerprint from being created
ALERT_ACTIVE_STATUSES = {ALERT_OPEN, ALERT_ACKNOWLEDGED}

# Statuses that are terminal
ALERT_TERMINAL_STATUSES = {ALERT_RESOLVED, ALERT_DISMISSED, ALERT_EXPIRED}

# ---------------------------------------------------------------------------
# Alert Types
# ---------------------------------------------------------------------------
ALERT_TYPE_KITCHEN_DELAY           = "KITCHEN_DELAY"
ALERT_TYPE_KITCHEN_BACKLOG         = "KITCHEN_BACKLOG"
ALERT_TYPE_LOW_STOCK               = "LOW_STOCK"
ALERT_TYPE_OUT_OF_STOCK            = "OUT_OF_STOCK"
ALERT_TYPE_PAYMENT_FAILURE         = "PAYMENT_FAILURE"
ALERT_TYPE_PAYMENT_EXCEPTION       = "PAYMENT_EXCEPTION"
ALERT_TYPE_REFUND_EXCEPTION        = "REFUND_EXCEPTION"
ALERT_TYPE_EXPENSE_PENDING         = "EXPENSE_PENDING"
ALERT_TYPE_PAYABLE_OVERDUE         = "PAYABLE_OVERDUE"
ALERT_TYPE_ACCOUNTING_EXCEPTION    = "ACCOUNTING_EXCEPTION"
ALERT_TYPE_COUNTER_SESSION         = "COUNTER_SESSION_EXCEPTION"
ALERT_TYPE_BRANCH_INACTIVE         = "BRANCH_INACTIVE"
ALERT_TYPE_RESTAURANT_INACTIVE     = "RESTAURANT_INACTIVE"
ALERT_TYPE_USER_ACCESS             = "USER_ACCESS_EXCEPTION"
ALERT_TYPE_SYSTEM_HEALTH           = "SYSTEM_HEALTH"
ALERT_TYPE_DATA_INTEGRITY          = "DATA_INTEGRITY"
ALERT_TYPE_UNUSUAL_ACTIVITY        = "UNUSUAL_ACTIVITY"

ALERT_TYPE_CHOICES = [
    (ALERT_TYPE_KITCHEN_DELAY,        "Kitchen Delay"),
    (ALERT_TYPE_KITCHEN_BACKLOG,      "Kitchen Backlog"),
    (ALERT_TYPE_LOW_STOCK,            "Low Stock"),
    (ALERT_TYPE_OUT_OF_STOCK,         "Out of Stock"),
    (ALERT_TYPE_PAYMENT_FAILURE,      "Payment Failure"),
    (ALERT_TYPE_PAYMENT_EXCEPTION,    "Payment Exception"),
    (ALERT_TYPE_REFUND_EXCEPTION,     "Refund Exception"),
    (ALERT_TYPE_EXPENSE_PENDING,      "Expense Pending"),
    (ALERT_TYPE_PAYABLE_OVERDUE,      "Payable Overdue"),
    (ALERT_TYPE_ACCOUNTING_EXCEPTION, "Accounting Exception"),
    (ALERT_TYPE_COUNTER_SESSION,      "Counter Session Exception"),
    (ALERT_TYPE_BRANCH_INACTIVE,      "Branch Inactive"),
    (ALERT_TYPE_RESTAURANT_INACTIVE,  "Restaurant Inactive"),
    (ALERT_TYPE_USER_ACCESS,          "User Access Exception"),
    (ALERT_TYPE_SYSTEM_HEALTH,        "System Health"),
    (ALERT_TYPE_DATA_INTEGRITY,       "Data Integrity"),
    (ALERT_TYPE_UNUSUAL_ACTIVITY,     "Unusual Activity"),
]

# Alert types that represent stock-condition alerts (auto-resolve when stock changes)
STOCK_CONDITION_ALERT_TYPES = {ALERT_TYPE_LOW_STOCK, ALERT_TYPE_OUT_OF_STOCK}

# ---------------------------------------------------------------------------
# Issue Category
# ---------------------------------------------------------------------------
ISSUE_CATEGORY_OPERATIONS = "OPERATIONS"
ISSUE_CATEGORY_KITCHEN    = "KITCHEN"
ISSUE_CATEGORY_INVENTORY  = "INVENTORY"
ISSUE_CATEGORY_PAYMENTS   = "PAYMENTS"
ISSUE_CATEGORY_FINANCE    = "FINANCE"
ISSUE_CATEGORY_ACCOUNTING = "ACCOUNTING"
ISSUE_CATEGORY_ACCESS     = "ACCESS"
ISSUE_CATEGORY_SYSTEM     = "SYSTEM"
ISSUE_CATEGORY_OTHER      = "OTHER"

ISSUE_CATEGORY_CHOICES = [
    (ISSUE_CATEGORY_OPERATIONS, "Operations"),
    (ISSUE_CATEGORY_KITCHEN,    "Kitchen"),
    (ISSUE_CATEGORY_INVENTORY,  "Inventory"),
    (ISSUE_CATEGORY_PAYMENTS,   "Payments"),
    (ISSUE_CATEGORY_FINANCE,    "Finance"),
    (ISSUE_CATEGORY_ACCOUNTING, "Accounting"),
    (ISSUE_CATEGORY_ACCESS,     "Access"),
    (ISSUE_CATEGORY_SYSTEM,     "System"),
    (ISSUE_CATEGORY_OTHER,      "Other"),
]

# ---------------------------------------------------------------------------
# Issue Severity (reuses alert severity levels for consistency)
# ---------------------------------------------------------------------------
ISSUE_SEVERITY_LOW      = "LOW"
ISSUE_SEVERITY_MEDIUM   = "MEDIUM"
ISSUE_SEVERITY_HIGH     = "HIGH"
ISSUE_SEVERITY_CRITICAL = "CRITICAL"

ISSUE_SEVERITY_CHOICES = [
    (ISSUE_SEVERITY_LOW,      "Low"),
    (ISSUE_SEVERITY_MEDIUM,   "Medium"),
    (ISSUE_SEVERITY_HIGH,     "High"),
    (ISSUE_SEVERITY_CRITICAL, "Critical"),
]

# ---------------------------------------------------------------------------
# Issue Status
# ---------------------------------------------------------------------------
ISSUE_OPEN        = "OPEN"
ISSUE_ASSIGNED    = "ASSIGNED"
ISSUE_IN_PROGRESS = "IN_PROGRESS"
ISSUE_RESOLVED    = "RESOLVED"
ISSUE_CLOSED      = "CLOSED"
ISSUE_CANCELLED   = "CANCELLED"

ISSUE_STATUS_CHOICES = [
    (ISSUE_OPEN,        "Open"),
    (ISSUE_ASSIGNED,    "Assigned"),
    (ISSUE_IN_PROGRESS, "In Progress"),
    (ISSUE_RESOLVED,    "Resolved"),
    (ISSUE_CLOSED,      "Closed"),
    (ISSUE_CANCELLED,   "Cancelled"),
]

ISSUE_VALID_TRANSITIONS: dict[str, list[str]] = {
    ISSUE_OPEN:        [ISSUE_ASSIGNED, ISSUE_IN_PROGRESS, ISSUE_RESOLVED, ISSUE_CANCELLED],
    ISSUE_ASSIGNED:    [ISSUE_IN_PROGRESS, ISSUE_OPEN, ISSUE_CANCELLED],
    ISSUE_IN_PROGRESS: [ISSUE_RESOLVED, ISSUE_ASSIGNED, ISSUE_CANCELLED],
    ISSUE_RESOLVED:    [ISSUE_CLOSED],
    ISSUE_CLOSED:      [],    # terminal — immutable
    ISSUE_CANCELLED:   [],    # terminal
}

# Statuses where the issue is still active
ISSUE_ACTIVE_STATUSES = {ISSUE_OPEN, ISSUE_ASSIGNED, ISSUE_IN_PROGRESS}

# Statuses that are terminal
ISSUE_TERMINAL_STATUSES = {ISSUE_RESOLVED, ISSUE_CLOSED, ISSUE_CANCELLED}

# ---------------------------------------------------------------------------
# Health Status
# ---------------------------------------------------------------------------
HEALTH_HEALTHY  = "HEALTHY"
HEALTH_WARNING  = "WARNING"
HEALTH_CRITICAL = "CRITICAL"
HEALTH_OFFLINE  = "OFFLINE"
HEALTH_UNKNOWN  = "UNKNOWN"

HEALTH_STATUS_CHOICES = [
    (HEALTH_HEALTHY,  "Healthy"),
    (HEALTH_WARNING,  "Warning"),
    (HEALTH_CRITICAL, "Critical"),
    (HEALTH_OFFLINE,  "Offline / Inactive"),
    (HEALTH_UNKNOWN,  "Unknown"),
]

# System component health statuses
COMPONENT_HEALTHY   = "HEALTHY"
COMPONENT_DEGRADED  = "DEGRADED"
COMPONENT_UNAVAILABLE = "UNAVAILABLE"
COMPONENT_UNKNOWN   = "UNKNOWN"

COMPONENT_STATUS_CHOICES = [
    (COMPONENT_HEALTHY,     "Healthy"),
    (COMPONENT_DEGRADED,    "Degraded"),
    (COMPONENT_UNAVAILABLE, "Unavailable"),
    (COMPONENT_UNKNOWN,     "Unknown"),
]

# ---------------------------------------------------------------------------
# Audit Actions
# ---------------------------------------------------------------------------
AUDIT_ALERT_ACKNOWLEDGED    = "CENTRAL_ALERT_ACKNOWLEDGED"
AUDIT_ALERT_RESOLVED        = "CENTRAL_ALERT_RESOLVED"
AUDIT_ALERT_DISMISSED       = "CENTRAL_ALERT_DISMISSED"
AUDIT_ISSUE_CREATED         = "CENTRAL_ISSUE_CREATED"
AUDIT_ISSUE_ASSIGNED        = "CENTRAL_ISSUE_ASSIGNED"
AUDIT_ISSUE_UPDATED         = "CENTRAL_ISSUE_UPDATED"
AUDIT_ISSUE_RESOLVED        = "CENTRAL_ISSUE_RESOLVED"
AUDIT_ISSUE_CLOSED          = "CENTRAL_ISSUE_CLOSED"
AUDIT_ISSUE_CANCELLED       = "CENTRAL_ISSUE_CANCELLED"
AUDIT_CONFIGURATION_UPDATED = "CENTRAL_CONFIGURATION_UPDATED"

AUDIT_ACTION_CHOICES = [
    (AUDIT_ALERT_ACKNOWLEDGED,    "Alert Acknowledged"),
    (AUDIT_ALERT_RESOLVED,        "Alert Resolved"),
    (AUDIT_ALERT_DISMISSED,       "Alert Dismissed"),
    (AUDIT_ISSUE_CREATED,         "Issue Created"),
    (AUDIT_ISSUE_ASSIGNED,        "Issue Assigned"),
    (AUDIT_ISSUE_UPDATED,         "Issue Updated"),
    (AUDIT_ISSUE_RESOLVED,        "Issue Resolved"),
    (AUDIT_ISSUE_CLOSED,          "Issue Closed"),
    (AUDIT_ISSUE_CANCELLED,       "Issue Cancelled"),
    (AUDIT_CONFIGURATION_UPDATED, "Configuration Updated"),
]

# ---------------------------------------------------------------------------
# WebSocket Event Types
# ---------------------------------------------------------------------------
WS_ALERT_CREATED           = "central.alert.created"
WS_ALERT_UPDATED           = "central.alert.updated"
WS_ALERT_RESOLVED          = "central.alert.resolved"
WS_ISSUE_CREATED           = "central.issue.created"
WS_ISSUE_UPDATED           = "central.issue.updated"
WS_ISSUE_RESOLVED          = "central.issue.resolved"
WS_HEALTH_UPDATED          = "central.health.updated"
WS_RESTAURANT_STATUS       = "central.restaurant.status_changed"
WS_BRANCH_STATUS           = "central.branch.status_changed"

# ---------------------------------------------------------------------------
# WebSocket Group Name Templates
# ---------------------------------------------------------------------------
WS_GROUP_COMPANY    = "company_{company_id}_central_control"
WS_GROUP_RESTAURANT = "restaurant_{restaurant_id}_central_control"

# ---------------------------------------------------------------------------
# Cache keys and TTLs (seconds)
# ---------------------------------------------------------------------------
CACHE_TTL_DASHBOARD    = 30     # 30 sec for live central dashboard
CACHE_TTL_RESTAURANT   = 60     # 1 min for restaurant health
CACHE_TTL_ALERTS       = 15     # 15 sec for alert counts (must stay fresh)
CACHE_TTL_HEALTH       = 120    # 2 min for system health
CACHE_TTL_HEAVY        = 300    # 5 min for expensive aggregations

CACHE_KEY_DASHBOARD    = "central_control:dashboard:org:{org_id}"
CACHE_KEY_RESTAURANT   = "central_control:restaurant_health:org:{org_id}"
CACHE_KEY_ALERT_COUNTS = "central_control:alert_counts:org:{org_id}"
CACHE_KEY_SYSTEM_HEALTH = "central_control:system_health"

# ---------------------------------------------------------------------------
# Default thresholds (configurable via CentralControlSettings)
# ---------------------------------------------------------------------------
DEFAULT_KITCHEN_DELAY_MINUTES     = 20
DEFAULT_KITCHEN_BACKLOG_THRESHOLD = 15
DEFAULT_PAYMENT_FAILURE_THRESHOLD = 5
DEFAULT_COUNTER_SESSION_MAX_HOURS = 16

# ---------------------------------------------------------------------------
# Source types for alerts (what kind of object triggered the alert)
# ---------------------------------------------------------------------------
SOURCE_TYPE_KITCHEN_ORDER   = "KITCHEN_ORDER"
SOURCE_TYPE_INVENTORY_ITEM  = "INVENTORY_ITEM"
SOURCE_TYPE_PAYMENT         = "PAYMENT"
SOURCE_TYPE_EXPENSE         = "EXPENSE"
SOURCE_TYPE_PAYABLE         = "PAYABLE"
SOURCE_TYPE_JOURNAL_ENTRY   = "JOURNAL_ENTRY"
SOURCE_TYPE_COUNTER_SESSION = "COUNTER_SESSION"
SOURCE_TYPE_SYSTEM          = "SYSTEM"
SOURCE_TYPE_USER            = "USER"

SOURCE_TYPE_CHOICES = [
    (SOURCE_TYPE_KITCHEN_ORDER,   "Kitchen Order"),
    (SOURCE_TYPE_INVENTORY_ITEM,  "Inventory Item"),
    (SOURCE_TYPE_PAYMENT,         "Payment"),
    (SOURCE_TYPE_EXPENSE,         "Expense"),
    (SOURCE_TYPE_PAYABLE,         "Payable"),
    (SOURCE_TYPE_JOURNAL_ENTRY,   "Journal Entry"),
    (SOURCE_TYPE_COUNTER_SESSION, "Counter Session"),
    (SOURCE_TYPE_SYSTEM,          "System"),
    (SOURCE_TYPE_USER,            "User"),
]

# ---------------------------------------------------------------------------
# Sequence format
# ---------------------------------------------------------------------------
ALERT_NUMBER_FORMAT = "CA-{seq:06d}"
ISSUE_NUMBER_FORMAT = "CI-{seq:06d}"
