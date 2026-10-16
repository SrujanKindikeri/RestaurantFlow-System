# =============================================================================
# RestaurantFlow — Enterprise Constants
# Phase 20: Multi-Branch Enterprise Operations & Configuration
#
# All permission codes, status constants, and domain enumerations live here.
# Never hard-code magic strings in models, services, or views.
# Always import from this module.
# =============================================================================

# ---------------------------------------------------------------------------
# Permission codes
# ---------------------------------------------------------------------------

# Dashboard
PERM_DASHBOARD_VIEW = "enterprise.dashboard.view"

# Branch management
PERM_BRANCH_VIEW    = "enterprise.branch.view"
PERM_BRANCH_CREATE  = "enterprise.branch.create"
PERM_BRANCH_UPDATE  = "enterprise.branch.update"
PERM_BRANCH_OPEN    = "enterprise.branch.open"
PERM_BRANCH_CLOSE   = "enterprise.branch.close"
PERM_BRANCH_REOPEN  = "enterprise.branch.reopen"

# Configuration
PERM_CONFIG_VIEW    = "enterprise.configuration.view"
PERM_CONFIG_CREATE  = "enterprise.configuration.create"
PERM_CONFIG_UPDATE  = "enterprise.configuration.update"
PERM_CONFIG_APPROVE = "enterprise.configuration.approve"
PERM_CONFIG_HISTORY = "enterprise.configuration.history.view"

# Rollout
PERM_ROLLOUT_VIEW    = "enterprise.rollout.view"
PERM_ROLLOUT_CREATE  = "enterprise.rollout.create"
PERM_ROLLOUT_PREVIEW = "enterprise.rollout.preview"
PERM_ROLLOUT_APPROVE = "enterprise.rollout.approve"
PERM_ROLLOUT_EXECUTE = "enterprise.rollout.execute"
PERM_ROLLOUT_CANCEL  = "enterprise.rollout.cancel"

# Staff
PERM_STAFF_VIEW     = "enterprise.staff.view"
PERM_STAFF_ASSIGN   = "enterprise.staff.assign"
PERM_STAFF_TRANSFER = "enterprise.staff.transfer"
PERM_STAFF_TRANSFER_APPROVE = "enterprise.staff.transfer.approve"

# Schedule
PERM_SCHEDULE_VIEW   = "enterprise.schedule.view"
PERM_SCHEDULE_MANAGE = "enterprise.schedule.manage"

# Approval policy
PERM_APPROVAL_POLICY_VIEW   = "enterprise.approval_policy.view"
PERM_APPROVAL_POLICY_MANAGE = "enterprise.approval_policy.manage"

# Audit
PERM_AUDIT_VIEW = "enterprise.audit.view"

# Full list for seed command: (code, name, module, action)
ALL_ENTERPRISE_PERMISSIONS = [
    (PERM_DASHBOARD_VIEW,           "View Enterprise Dashboard",          "enterprise", "dashboard.view"),
    (PERM_BRANCH_VIEW,              "View Enterprise Branches",           "enterprise", "branch.view"),
    (PERM_BRANCH_CREATE,            "Create Branches",                    "enterprise", "branch.create"),
    (PERM_BRANCH_UPDATE,            "Update Branches",                    "enterprise", "branch.update"),
    (PERM_BRANCH_OPEN,              "Open Branch",                        "enterprise", "branch.open"),
    (PERM_BRANCH_CLOSE,             "Close Branch",                       "enterprise", "branch.close"),
    (PERM_BRANCH_REOPEN,            "Reopen Branch",                      "enterprise", "branch.reopen"),
    (PERM_CONFIG_VIEW,              "View Enterprise Configuration",      "enterprise", "configuration.view"),
    (PERM_CONFIG_CREATE,            "Create Enterprise Configuration",    "enterprise", "configuration.create"),
    (PERM_CONFIG_UPDATE,            "Update Enterprise Configuration",    "enterprise", "configuration.update"),
    (PERM_CONFIG_APPROVE,           "Approve Enterprise Configuration",   "enterprise", "configuration.approve"),
    (PERM_CONFIG_HISTORY,           "View Configuration History",         "enterprise", "configuration.history.view"),
    (PERM_ROLLOUT_VIEW,             "View Rollouts",                      "enterprise", "rollout.view"),
    (PERM_ROLLOUT_CREATE,           "Create Rollouts",                    "enterprise", "rollout.create"),
    (PERM_ROLLOUT_PREVIEW,          "Preview Rollouts",                   "enterprise", "rollout.preview"),
    (PERM_ROLLOUT_APPROVE,          "Approve Rollouts",                   "enterprise", "rollout.approve"),
    (PERM_ROLLOUT_EXECUTE,          "Execute Rollouts",                   "enterprise", "rollout.execute"),
    (PERM_ROLLOUT_CANCEL,           "Cancel Rollouts",                    "enterprise", "rollout.cancel"),
    (PERM_STAFF_VIEW,               "View Staff Assignments",             "enterprise", "staff.view"),
    (PERM_STAFF_ASSIGN,             "Assign Staff to Branches",           "enterprise", "staff.assign"),
    (PERM_STAFF_TRANSFER,           "Request Staff Transfers",            "enterprise", "staff.transfer"),
    (PERM_STAFF_TRANSFER_APPROVE,   "Approve Staff Transfers",            "enterprise", "staff.transfer.approve"),
    (PERM_SCHEDULE_VIEW,            "View Branch Schedules",              "enterprise", "schedule.view"),
    (PERM_SCHEDULE_MANAGE,          "Manage Branch Schedules",            "enterprise", "schedule.manage"),
    (PERM_APPROVAL_POLICY_VIEW,     "View Approval Policies",             "enterprise", "approval_policy.view"),
    (PERM_APPROVAL_POLICY_MANAGE,   "Manage Approval Policies",           "enterprise", "approval_policy.manage"),
    (PERM_AUDIT_VIEW,               "View Enterprise Audit Log",          "enterprise", "audit.view"),
]

# ---------------------------------------------------------------------------
# Branch Operational Status
# ---------------------------------------------------------------------------
BRANCH_STATUS_ACTIVE              = "ACTIVE"
BRANCH_STATUS_TEMPORARILY_CLOSED  = "TEMPORARILY_CLOSED"
BRANCH_STATUS_SCHEDULED_CLOSURE   = "SCHEDULED_CLOSURE"
BRANCH_STATUS_MAINTENANCE         = "MAINTENANCE"
BRANCH_STATUS_INACTIVE            = "INACTIVE"

BRANCH_STATUS_CHOICES = [
    (BRANCH_STATUS_ACTIVE,             "Active"),
    (BRANCH_STATUS_TEMPORARILY_CLOSED, "Temporarily Closed"),
    (BRANCH_STATUS_SCHEDULED_CLOSURE,  "Scheduled Closure"),
    (BRANCH_STATUS_MAINTENANCE,        "Under Maintenance"),
    (BRANCH_STATUS_INACTIVE,           "Inactive"),
]

BRANCH_STATUS_ACTIVE_STATES = {BRANCH_STATUS_ACTIVE}
BRANCH_STATUS_CLOSED_STATES = {
    BRANCH_STATUS_TEMPORARILY_CLOSED,
    BRANCH_STATUS_SCHEDULED_CLOSURE,
    BRANCH_STATUS_MAINTENANCE,
    BRANCH_STATUS_INACTIVE,
}

# Valid branch status transitions
BRANCH_STATUS_TRANSITIONS: dict[str, list[str]] = {
    BRANCH_STATUS_ACTIVE: [
        BRANCH_STATUS_TEMPORARILY_CLOSED,
        BRANCH_STATUS_SCHEDULED_CLOSURE,
        BRANCH_STATUS_MAINTENANCE,
        BRANCH_STATUS_INACTIVE,
    ],
    BRANCH_STATUS_TEMPORARILY_CLOSED: [
        BRANCH_STATUS_ACTIVE,
        BRANCH_STATUS_INACTIVE,
        BRANCH_STATUS_MAINTENANCE,
    ],
    BRANCH_STATUS_SCHEDULED_CLOSURE: [
        BRANCH_STATUS_ACTIVE,
        BRANCH_STATUS_INACTIVE,
    ],
    BRANCH_STATUS_MAINTENANCE: [
        BRANCH_STATUS_ACTIVE,
        BRANCH_STATUS_INACTIVE,
    ],
    BRANCH_STATUS_INACTIVE: [
        BRANCH_STATUS_ACTIVE,
    ],
}

# ---------------------------------------------------------------------------
# Days of week
# ---------------------------------------------------------------------------
DAY_MONDAY    = "MONDAY"
DAY_TUESDAY   = "TUESDAY"
DAY_WEDNESDAY = "WEDNESDAY"
DAY_THURSDAY  = "THURSDAY"
DAY_FRIDAY    = "FRIDAY"
DAY_SATURDAY  = "SATURDAY"
DAY_SUNDAY    = "SUNDAY"

DAY_OF_WEEK_CHOICES = [
    (DAY_MONDAY,    "Monday"),
    (DAY_TUESDAY,   "Tuesday"),
    (DAY_WEDNESDAY, "Wednesday"),
    (DAY_THURSDAY,  "Thursday"),
    (DAY_FRIDAY,    "Friday"),
    (DAY_SATURDAY,  "Saturday"),
    (DAY_SUNDAY,    "Sunday"),
]

DAY_ORDER = {
    DAY_MONDAY: 0,
    DAY_TUESDAY: 1,
    DAY_WEDNESDAY: 2,
    DAY_THURSDAY: 3,
    DAY_FRIDAY: 4,
    DAY_SATURDAY: 5,
    DAY_SUNDAY: 6,
}

# ---------------------------------------------------------------------------
# Closure Types & Statuses
# ---------------------------------------------------------------------------
CLOSURE_TYPE_HOLIDAY       = "HOLIDAY"
CLOSURE_TYPE_MAINTENANCE   = "MAINTENANCE"
CLOSURE_TYPE_PRIVATE_EVENT = "PRIVATE_EVENT"
CLOSURE_TYPE_EMERGENCY     = "EMERGENCY"
CLOSURE_TYPE_OTHER         = "OTHER"

CLOSURE_TYPE_CHOICES = [
    (CLOSURE_TYPE_HOLIDAY,       "Public Holiday"),
    (CLOSURE_TYPE_MAINTENANCE,   "Maintenance"),
    (CLOSURE_TYPE_PRIVATE_EVENT, "Private Event"),
    (CLOSURE_TYPE_EMERGENCY,     "Emergency"),
    (CLOSURE_TYPE_OTHER,         "Other"),
]

CLOSURE_STATUS_DRAFT            = "DRAFT"
CLOSURE_STATUS_PENDING_APPROVAL = "PENDING_APPROVAL"
CLOSURE_STATUS_APPROVED         = "APPROVED"
CLOSURE_STATUS_REJECTED         = "REJECTED"
CLOSURE_STATUS_CANCELLED        = "CANCELLED"
CLOSURE_STATUS_ACTIVE           = "ACTIVE"
CLOSURE_STATUS_COMPLETED        = "COMPLETED"

CLOSURE_STATUS_CHOICES = [
    (CLOSURE_STATUS_DRAFT,            "Draft"),
    (CLOSURE_STATUS_PENDING_APPROVAL, "Pending Approval"),
    (CLOSURE_STATUS_APPROVED,         "Approved"),
    (CLOSURE_STATUS_REJECTED,         "Rejected"),
    (CLOSURE_STATUS_CANCELLED,        "Cancelled"),
    (CLOSURE_STATUS_ACTIVE,           "Active"),
    (CLOSURE_STATUS_COMPLETED,        "Completed"),
]

# ---------------------------------------------------------------------------
# Configuration Value Types
# ---------------------------------------------------------------------------
VALUE_TYPE_STRING  = "STRING"
VALUE_TYPE_INTEGER = "INTEGER"
VALUE_TYPE_DECIMAL = "DECIMAL"
VALUE_TYPE_BOOLEAN = "BOOLEAN"
VALUE_TYPE_JSON    = "JSON"

VALUE_TYPE_CHOICES = [
    (VALUE_TYPE_STRING,  "String"),
    (VALUE_TYPE_INTEGER, "Integer"),
    (VALUE_TYPE_DECIMAL, "Decimal"),
    (VALUE_TYPE_BOOLEAN, "Boolean"),
    (VALUE_TYPE_JSON,    "JSON"),
]

# Allow-listed configuration keys with their metadata:
# (key, value_type, description, default_value)
ALLOWED_CONFIGURATION_KEYS: dict[str, dict] = {
    "branch.default_order_type":           {"type": VALUE_TYPE_STRING,  "default": "dine_in",     "description": "Default order type for the branch"},
    "branch.allow_takeaway":               {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Allow takeaway orders"},
    "branch.allow_dine_in":                {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Allow dine-in orders"},
    "branch.allow_counter_orders":         {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Allow counter orders"},
    "branch.auto_close_enabled":           {"type": VALUE_TYPE_BOOLEAN, "default": "false",        "description": "Automatically close branch at configured time"},
    "pos.require_counter_session":         {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Require an open counter session for POS"},
    "pos.allow_bill_reprint":              {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Allow bill reprint after finalization"},
    "pos.allow_order_hold":                {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Allow orders to be placed on hold"},
    "billing.allow_discount":              {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Allow discounts to be applied on bills"},
    "billing.maximum_discount_percentage": {"type": VALUE_TYPE_DECIMAL, "default": "10.00",        "description": "Maximum discount percentage allowed without additional approval"},
    "inventory.allow_negative_stock":      {"type": VALUE_TYPE_BOOLEAN, "default": "false",        "description": "Allow stock to go below zero"},
    "kitchen.default_priority":            {"type": VALUE_TYPE_INTEGER, "default": "5",            "description": "Default kitchen order priority (1-10)"},
    "kitchen.delay_threshold_minutes":     {"type": VALUE_TYPE_INTEGER, "default": "20",           "description": "Minutes before a kitchen order is considered delayed"},
    "expense.approval_required":           {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Require approval for expense submissions"},
    "expense.maximum_auto_approval_amount":{"type": VALUE_TYPE_DECIMAL, "default": "1000.00",      "description": "Maximum expense amount auto-approved without manager review"},
    "payment.cash_enabled":                {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Accept cash payments"},
    "payment.upi_enabled":                 {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Accept UPI payments"},
    "payment.card_enabled":                {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Accept card payments"},
    "customer.loyalty_enabled":            {"type": VALUE_TYPE_BOOLEAN, "default": "false",        "description": "Enable customer loyalty program at this branch"},
    "notifications.email_enabled":         {"type": VALUE_TYPE_BOOLEAN, "default": "true",         "description": "Enable email notifications for branch events"},
}

ALLOWED_CONFIGURATION_KEY_CHOICES = [(k, k) for k in ALLOWED_CONFIGURATION_KEYS.keys()]

# ---------------------------------------------------------------------------
# Configuration Scope
# ---------------------------------------------------------------------------
CONFIG_SCOPE_COMPANY    = "COMPANY"
CONFIG_SCOPE_RESTAURANT = "RESTAURANT"
CONFIG_SCOPE_BRANCH     = "BRANCH"

CONFIG_SCOPE_CHOICES = [
    (CONFIG_SCOPE_COMPANY,    "Company"),
    (CONFIG_SCOPE_RESTAURANT, "Restaurant"),
    (CONFIG_SCOPE_BRANCH,     "Branch"),
]

# ---------------------------------------------------------------------------
# Rollout Target Scope
# ---------------------------------------------------------------------------
ROLLOUT_SCOPE_ALL_BRANCHES      = "ALL_BRANCHES"
ROLLOUT_SCOPE_SELECTED_BRANCHES = "SELECTED_BRANCHES"

ROLLOUT_SCOPE_CHOICES = [
    (ROLLOUT_SCOPE_ALL_BRANCHES,      "All Branches"),
    (ROLLOUT_SCOPE_SELECTED_BRANCHES, "Selected Branches"),
]

# ---------------------------------------------------------------------------
# Rollout Status
# ---------------------------------------------------------------------------
ROLLOUT_STATUS_DRAFT               = "DRAFT"
ROLLOUT_STATUS_PENDING_APPROVAL    = "PENDING_APPROVAL"
ROLLOUT_STATUS_APPROVED            = "APPROVED"
ROLLOUT_STATUS_SCHEDULED           = "SCHEDULED"
ROLLOUT_STATUS_RUNNING             = "RUNNING"
ROLLOUT_STATUS_COMPLETED           = "COMPLETED"
ROLLOUT_STATUS_PARTIALLY_COMPLETED = "PARTIALLY_COMPLETED"
ROLLOUT_STATUS_FAILED              = "FAILED"
ROLLOUT_STATUS_CANCELLED           = "CANCELLED"

ROLLOUT_STATUS_CHOICES = [
    (ROLLOUT_STATUS_DRAFT,               "Draft"),
    (ROLLOUT_STATUS_PENDING_APPROVAL,    "Pending Approval"),
    (ROLLOUT_STATUS_APPROVED,            "Approved"),
    (ROLLOUT_STATUS_SCHEDULED,           "Scheduled"),
    (ROLLOUT_STATUS_RUNNING,             "Running"),
    (ROLLOUT_STATUS_COMPLETED,           "Completed"),
    (ROLLOUT_STATUS_PARTIALLY_COMPLETED, "Partially Completed"),
    (ROLLOUT_STATUS_FAILED,              "Failed"),
    (ROLLOUT_STATUS_CANCELLED,           "Cancelled"),
]

ROLLOUT_TERMINAL_STATUSES = {
    ROLLOUT_STATUS_COMPLETED,
    ROLLOUT_STATUS_FAILED,
    ROLLOUT_STATUS_CANCELLED,
}

ROLLOUT_ACTIVE_STATUSES = {
    ROLLOUT_STATUS_RUNNING,
    ROLLOUT_STATUS_SCHEDULED,
    ROLLOUT_STATUS_APPROVED,
    ROLLOUT_STATUS_PENDING_APPROVAL,
}

# ---------------------------------------------------------------------------
# Rollout Types
# ---------------------------------------------------------------------------
ROLLOUT_TYPE_MENU_AVAILABILITY = "MENU_AVAILABILITY"
ROLLOUT_TYPE_PRICE             = "PRICE"

ROLLOUT_TYPE_CHOICES = [
    (ROLLOUT_TYPE_MENU_AVAILABILITY, "Menu Item Availability"),
    (ROLLOUT_TYPE_PRICE,             "Price Rollout"),
]

# ---------------------------------------------------------------------------
# Staff Transfer Status
# ---------------------------------------------------------------------------
TRANSFER_STATUS_REQUESTED = "REQUESTED"
TRANSFER_STATUS_APPROVED  = "APPROVED"
TRANSFER_STATUS_REJECTED  = "REJECTED"
TRANSFER_STATUS_COMPLETED = "COMPLETED"
TRANSFER_STATUS_CANCELLED = "CANCELLED"

TRANSFER_STATUS_CHOICES = [
    (TRANSFER_STATUS_REQUESTED, "Requested"),
    (TRANSFER_STATUS_APPROVED,  "Approved"),
    (TRANSFER_STATUS_REJECTED,  "Rejected"),
    (TRANSFER_STATUS_COMPLETED, "Completed"),
    (TRANSFER_STATUS_CANCELLED, "Cancelled"),
]

TRANSFER_TERMINAL_STATUSES = {
    TRANSFER_STATUS_REJECTED,
    TRANSFER_STATUS_COMPLETED,
    TRANSFER_STATUS_CANCELLED,
}

# ---------------------------------------------------------------------------
# Approval Policy Types
# ---------------------------------------------------------------------------
POLICY_TYPE_EXPENSE         = "EXPENSE"
POLICY_TYPE_DISCOUNT        = "DISCOUNT"
POLICY_TYPE_REFUND          = "REFUND"
POLICY_TYPE_WASTAGE         = "WASTAGE"
POLICY_TYPE_STOCK_TRANSFER  = "STOCK_TRANSFER"
POLICY_TYPE_CONFIGURATION   = "CONFIGURATION"
POLICY_TYPE_PRICE_ROLLOUT   = "PRICE_ROLLOUT"

POLICY_TYPE_CHOICES = [
    (POLICY_TYPE_EXPENSE,        "Expense"),
    (POLICY_TYPE_DISCOUNT,       "Discount"),
    (POLICY_TYPE_REFUND,         "Refund"),
    (POLICY_TYPE_WASTAGE,        "Wastage"),
    (POLICY_TYPE_STOCK_TRANSFER, "Stock Transfer"),
    (POLICY_TYPE_CONFIGURATION,  "Configuration Change"),
    (POLICY_TYPE_PRICE_ROLLOUT,  "Price Rollout"),
]

# ---------------------------------------------------------------------------
# Opening Checklist Item Types
# ---------------------------------------------------------------------------
CHECKLIST_COUNTER_READY         = "COUNTER_READY"
CHECKLIST_KITCHEN_READY         = "KITCHEN_READY"
CHECKLIST_INVENTORY_READY       = "INVENTORY_READY"
CHECKLIST_STAFF_READY           = "STAFF_READY"
CHECKLIST_PAYMENT_METHODS_READY = "PAYMENT_METHODS_READY"
CHECKLIST_POS_READY             = "POS_READY"

CHECKLIST_STATUS_READY   = "READY"
CHECKLIST_STATUS_WARNING = "WARNING"
CHECKLIST_STATUS_BLOCKED = "BLOCKED"

# ---------------------------------------------------------------------------
# Audit Action Types
# ---------------------------------------------------------------------------
AUDIT_BRANCH_OPENED        = "BRANCH_OPENED"
AUDIT_BRANCH_CLOSED        = "BRANCH_CLOSED"
AUDIT_BRANCH_REOPENED      = "BRANCH_REOPENED"
AUDIT_BRANCH_STATUS_CHANGED = "BRANCH_STATUS_CHANGED"

AUDIT_CONFIG_CREATED        = "CONFIGURATION_CREATED"
AUDIT_CONFIG_UPDATED        = "CONFIGURATION_UPDATED"
AUDIT_CONFIG_ROLLED_BACK    = "CONFIGURATION_ROLLED_BACK"

AUDIT_ROLLOUT_CREATED       = "MENU_ROLLOUT_CREATED"
AUDIT_ROLLOUT_APPROVED      = "MENU_ROLLOUT_APPROVED"
AUDIT_ROLLOUT_EXECUTED      = "MENU_ROLLOUT_EXECUTED"
AUDIT_ROLLOUT_FAILED        = "MENU_ROLLOUT_FAILED"

AUDIT_PRICE_ROLLOUT_CREATED  = "PRICE_ROLLOUT_CREATED"
AUDIT_PRICE_ROLLOUT_EXECUTED = "PRICE_ROLLOUT_EXECUTED"

AUDIT_STAFF_ASSIGNED             = "STAFF_ASSIGNED"
AUDIT_STAFF_TRANSFER_REQUESTED   = "STAFF_TRANSFER_REQUESTED"
AUDIT_STAFF_TRANSFER_APPROVED    = "STAFF_TRANSFER_APPROVED"
AUDIT_STAFF_TRANSFER_REJECTED    = "STAFF_TRANSFER_REJECTED"
AUDIT_STAFF_TRANSFER_COMPLETED   = "STAFF_TRANSFER_COMPLETED"

AUDIT_APPROVAL_POLICY_CREATED    = "APPROVAL_POLICY_CREATED"
AUDIT_APPROVAL_POLICY_UPDATED    = "APPROVAL_POLICY_UPDATED"

AUDIT_ACTION_CHOICES = [
    (AUDIT_BRANCH_OPENED,            "Branch Opened"),
    (AUDIT_BRANCH_CLOSED,            "Branch Closed"),
    (AUDIT_BRANCH_REOPENED,          "Branch Reopened"),
    (AUDIT_BRANCH_STATUS_CHANGED,    "Branch Status Changed"),
    (AUDIT_CONFIG_CREATED,           "Configuration Created"),
    (AUDIT_CONFIG_UPDATED,           "Configuration Updated"),
    (AUDIT_CONFIG_ROLLED_BACK,       "Configuration Rolled Back"),
    (AUDIT_ROLLOUT_CREATED,          "Rollout Created"),
    (AUDIT_ROLLOUT_APPROVED,         "Rollout Approved"),
    (AUDIT_ROLLOUT_EXECUTED,         "Rollout Executed"),
    (AUDIT_ROLLOUT_FAILED,           "Rollout Failed"),
    (AUDIT_PRICE_ROLLOUT_CREATED,    "Price Rollout Created"),
    (AUDIT_PRICE_ROLLOUT_EXECUTED,   "Price Rollout Executed"),
    (AUDIT_STAFF_ASSIGNED,           "Staff Assigned"),
    (AUDIT_STAFF_TRANSFER_REQUESTED, "Staff Transfer Requested"),
    (AUDIT_STAFF_TRANSFER_APPROVED,  "Staff Transfer Approved"),
    (AUDIT_STAFF_TRANSFER_REJECTED,  "Staff Transfer Rejected"),
    (AUDIT_STAFF_TRANSFER_COMPLETED, "Staff Transfer Completed"),
    (AUDIT_APPROVAL_POLICY_CREATED,  "Approval Policy Created"),
    (AUDIT_APPROVAL_POLICY_UPDATED,  "Approval Policy Updated"),
]

# ---------------------------------------------------------------------------
# Notification types (Phase 20 extensions)
# ---------------------------------------------------------------------------
NOTIF_BRANCH_CLOSURE_APPROVED  = "ENTERPRISE_BRANCH_CLOSURE_APPROVED"
NOTIF_BRANCH_REOPENED          = "ENTERPRISE_BRANCH_REOPENED"
NOTIF_ROLLOUT_COMPLETED        = "ENTERPRISE_ROLLOUT_COMPLETED"
NOTIF_ROLLOUT_FAILED           = "ENTERPRISE_ROLLOUT_FAILED"
NOTIF_PRICE_ROLLOUT_COMPLETED  = "ENTERPRISE_PRICE_ROLLOUT_COMPLETED"
NOTIF_TRANSFER_APPROVED        = "ENTERPRISE_STAFF_TRANSFER_APPROVED"
NOTIF_TRANSFER_REJECTED        = "ENTERPRISE_STAFF_TRANSFER_REJECTED"
NOTIF_CONFIG_APPROVAL_REQUIRED = "ENTERPRISE_CONFIG_APPROVAL_REQUIRED"
NOTIF_CONFIG_HIGH_IMPACT       = "ENTERPRISE_CONFIG_HIGH_IMPACT_CHANGED"

ENTERPRISE_NOTIFICATION_TYPES = [
    (NOTIF_BRANCH_CLOSURE_APPROVED,  "Branch Closure Approved"),
    (NOTIF_BRANCH_REOPENED,          "Branch Reopened"),
    (NOTIF_ROLLOUT_COMPLETED,        "Menu Rollout Completed"),
    (NOTIF_ROLLOUT_FAILED,           "Menu Rollout Failed"),
    (NOTIF_PRICE_ROLLOUT_COMPLETED,  "Price Rollout Completed"),
    (NOTIF_TRANSFER_APPROVED,        "Staff Transfer Approved"),
    (NOTIF_TRANSFER_REJECTED,        "Staff Transfer Rejected"),
    (NOTIF_CONFIG_APPROVAL_REQUIRED, "Configuration Approval Required"),
    (NOTIF_CONFIG_HIGH_IMPACT,       "High-Impact Configuration Changed"),
]

# Alert types for Central Control integration
ALERT_TYPE_BRANCH_CLOSED            = "BRANCH_CLOSED"
ALERT_TYPE_BRANCH_NOT_OPENED        = "BRANCH_NOT_OPENED"
ALERT_TYPE_CONFIG_EXCEPTION         = "CONFIGURATION_EXCEPTION"
ALERT_TYPE_ROLLOUT_FAILED           = "ROLLOUT_FAILED"
ALERT_TYPE_ROLLOUT_PARTIAL          = "ROLLOUT_PARTIAL_FAILURE"
ALERT_TYPE_STAFF_TRANSFER_EXCEPTION = "STAFF_TRANSFER_EXCEPTION"

# ---------------------------------------------------------------------------
# Cache keys
# ---------------------------------------------------------------------------
CACHE_KEY_EFFECTIVE_CONFIG = "enterprise:config:{company_id}:{restaurant_id}:{branch_id}:{key}"
CACHE_TTL_EFFECTIVE_CONFIG = 300   # 5 minutes
CACHE_TTL_CRITICAL_CONFIG  = 0     # no caching for security-sensitive config

# High-impact keys that bypass cache and require immediate DB resolution
HIGH_IMPACT_CONFIG_KEYS = {
    "pos.require_counter_session",
    "billing.maximum_discount_percentage",
    "payment.cash_enabled",
    "payment.upi_enabled",
    "payment.card_enabled",
    "expense.maximum_auto_approval_amount",
}

# ---------------------------------------------------------------------------
# WebSocket event types
# ---------------------------------------------------------------------------
WS_BRANCH_STATUS_CHANGED    = "enterprise.branch.status_changed"
WS_CONFIG_UPDATED           = "enterprise.configuration.updated"
WS_ROLLOUT_CREATED          = "enterprise.rollout.created"
WS_ROLLOUT_COMPLETED        = "enterprise.rollout.completed"
WS_ROLLOUT_FAILED           = "enterprise.rollout.failed"
WS_TRANSFER_CREATED         = "enterprise.staff.transfer.created"
WS_TRANSFER_COMPLETED       = "enterprise.staff.transfer.completed"
WS_SCHEDULE_UPDATED         = "enterprise.schedule.updated"
