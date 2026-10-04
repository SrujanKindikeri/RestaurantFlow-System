# =============================================================================
# RestaurantFlow — Notifications Constants
# Phase 16
#
# All magic strings live here. Never hard-code these values in models,
# services, or views — always import from here.
# =============================================================================

# ---------------------------------------------------------------------------
# Permission codes
# ---------------------------------------------------------------------------
PERM_NOTIFICATION_VIEW          = "notifications.view"
PERM_NOTIFICATION_MANAGE        = "notifications.manage"
PERM_NOTIFICATION_PREF_MANAGE   = "notifications.preferences.manage"
PERM_NOTIFICATION_ADMIN         = "notifications.admin"
PERM_NOTIFICATION_TEMPLATE_MGMT = "notifications.templates.manage"
PERM_NOTIFICATION_DELIVERY_VIEW = "notifications.deliveries.view"
PERM_PROVIDER_CONFIG_MANAGE     = "notifications.providers.manage"

ALL_NOTIFICATION_PERMISSIONS = [
    (PERM_NOTIFICATION_VIEW,          "View Own Notifications",                 "notifications", "view"),
    (PERM_NOTIFICATION_MANAGE,        "Manage Notifications",                   "notifications", "manage"),
    (PERM_NOTIFICATION_PREF_MANAGE,   "Manage Notification Preferences",        "notifications", "preferences.manage"),
    (PERM_NOTIFICATION_ADMIN,         "Admin Notifications",                    "notifications", "admin"),
    (PERM_NOTIFICATION_TEMPLATE_MGMT, "Manage Notification Templates",          "notifications", "templates.manage"),
    (PERM_NOTIFICATION_DELIVERY_VIEW, "View Notification Delivery History",     "notifications", "deliveries.view"),
    (PERM_PROVIDER_CONFIG_MANAGE,     "Manage Notification Provider Config",    "notifications", "providers.manage"),
]

# ---------------------------------------------------------------------------
# Notification Types
# ---------------------------------------------------------------------------

# Order
NOTIF_ORDER_CONFIRMED        = "ORDER_CONFIRMED"
NOTIF_ORDER_READY            = "ORDER_READY"
NOTIF_ORDER_CANCELLED        = "ORDER_CANCELLED"

# Kitchen
NOTIF_KITCHEN_ORDER_READY    = "KITCHEN_ORDER_READY"
NOTIF_KITCHEN_ORDER_DELAYED  = "KITCHEN_ORDER_DELAYED"
NOTIF_KITCHEN_BACKLOG        = "KITCHEN_BACKLOG"

# Inventory
NOTIF_INVENTORY_LOW_STOCK    = "INVENTORY_LOW_STOCK"
NOTIF_INVENTORY_OUT_OF_STOCK = "INVENTORY_OUT_OF_STOCK"
NOTIF_INVENTORY_PURCHASE_RECEIVED = "INVENTORY_PURCHASE_RECEIVED"
NOTIF_INVENTORY_CONSUMPTION_FAILED = "INVENTORY_CONSUMPTION_FAILED"

# Payment
NOTIF_PAYMENT_COMPLETED      = "PAYMENT_COMPLETED"
NOTIF_PAYMENT_FAILED         = "PAYMENT_FAILED"
NOTIF_REFUND_PROCESSED       = "REFUND_PROCESSED"

# Expense
NOTIF_EXPENSE_SUBMITTED      = "EXPENSE_SUBMITTED"
NOTIF_EXPENSE_APPROVAL_REQUIRED = "EXPENSE_APPROVAL_REQUIRED"
NOTIF_EXPENSE_APPROVED       = "EXPENSE_APPROVED"
NOTIF_EXPENSE_REJECTED       = "EXPENSE_REJECTED"

# Payable
NOTIF_PAYABLE_OVERDUE        = "PAYABLE_OVERDUE"
NOTIF_SUPPLIER_INVOICE_SUBMITTED = "SUPPLIER_INVOICE_SUBMITTED"

# Accounting
NOTIF_ACCOUNTING_POSTING_FAILED = "ACCOUNTING_POSTING_FAILED"
NOTIF_ACCOUNTING_PERIOD_CLOSED  = "ACCOUNTING_PERIOD_CLOSED"

# Central alerts
NOTIF_CENTRAL_ALERT_CREATED  = "CENTRAL_ALERT_CREATED"
NOTIF_CENTRAL_ALERT_RESOLVED = "CENTRAL_ALERT_RESOLVED"
NOTIF_CENTRAL_ISSUE_ASSIGNED = "CENTRAL_ISSUE_ASSIGNED"
NOTIF_CENTRAL_ISSUE_RESOLVED = "CENTRAL_ISSUE_RESOLVED"

# User / access
NOTIF_USER_ACCESS_GRANTED    = "USER_ACCESS_GRANTED"
NOTIF_USER_ACCESS_REVOKED    = "USER_ACCESS_REVOKED"
NOTIF_COUNTER_SESSION_CLOSED = "COUNTER_SESSION_CLOSED"

# System
NOTIF_SYSTEM_HEALTH_DEGRADED = "SYSTEM_HEALTH_DEGRADED"
NOTIF_NOTIFICATION_PROVIDER_FAILURE = "NOTIFICATION_PROVIDER_FAILURE"

NOTIFICATION_TYPE_CHOICES = [
    # Order
    (NOTIF_ORDER_CONFIRMED,        "Order Confirmed"),
    (NOTIF_ORDER_READY,            "Order Ready"),
    (NOTIF_ORDER_CANCELLED,        "Order Cancelled"),
    # Kitchen
    (NOTIF_KITCHEN_ORDER_READY,    "Kitchen Order Ready"),
    (NOTIF_KITCHEN_ORDER_DELAYED,  "Kitchen Order Delayed"),
    (NOTIF_KITCHEN_BACKLOG,        "Kitchen Backlog"),
    # Inventory
    (NOTIF_INVENTORY_LOW_STOCK,    "Inventory Low Stock"),
    (NOTIF_INVENTORY_OUT_OF_STOCK, "Inventory Out of Stock"),
    (NOTIF_INVENTORY_PURCHASE_RECEIVED, "Purchase Received"),
    (NOTIF_INVENTORY_CONSUMPTION_FAILED, "Inventory Consumption Failed"),
    # Payment
    (NOTIF_PAYMENT_COMPLETED,      "Payment Completed"),
    (NOTIF_PAYMENT_FAILED,         "Payment Failed"),
    (NOTIF_REFUND_PROCESSED,       "Refund Processed"),
    # Expense
    (NOTIF_EXPENSE_SUBMITTED,      "Expense Submitted"),
    (NOTIF_EXPENSE_APPROVAL_REQUIRED, "Expense Approval Required"),
    (NOTIF_EXPENSE_APPROVED,       "Expense Approved"),
    (NOTIF_EXPENSE_REJECTED,       "Expense Rejected"),
    # Payable
    (NOTIF_PAYABLE_OVERDUE,        "Payable Overdue"),
    (NOTIF_SUPPLIER_INVOICE_SUBMITTED, "Supplier Invoice Submitted"),
    # Accounting
    (NOTIF_ACCOUNTING_POSTING_FAILED, "Accounting Posting Failed"),
    (NOTIF_ACCOUNTING_PERIOD_CLOSED,  "Accounting Period Closed"),
    # Central
    (NOTIF_CENTRAL_ALERT_CREATED,  "Central Alert Created"),
    (NOTIF_CENTRAL_ALERT_RESOLVED, "Central Alert Resolved"),
    (NOTIF_CENTRAL_ISSUE_ASSIGNED, "Central Issue Assigned"),
    (NOTIF_CENTRAL_ISSUE_RESOLVED, "Central Issue Resolved"),
    # User / access
    (NOTIF_USER_ACCESS_GRANTED,    "User Access Granted"),
    (NOTIF_USER_ACCESS_REVOKED,    "User Access Revoked"),
    (NOTIF_COUNTER_SESSION_CLOSED, "Counter Session Closed"),
    # System
    (NOTIF_SYSTEM_HEALTH_DEGRADED, "System Health Degraded"),
    (NOTIF_NOTIFICATION_PROVIDER_FAILURE, "Notification Provider Failure"),
]

# ---------------------------------------------------------------------------
# Severity levels (mirrors central_control for consistency)
# ---------------------------------------------------------------------------
SEVERITY_INFO     = "INFO"
SEVERITY_LOW      = "LOW"
SEVERITY_MEDIUM   = "MEDIUM"
SEVERITY_HIGH     = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

SEVERITY_CHOICES = [
    (SEVERITY_INFO,     "Info"),
    (SEVERITY_LOW,      "Low"),
    (SEVERITY_MEDIUM,   "Medium"),
    (SEVERITY_HIGH,     "High"),
    (SEVERITY_CRITICAL, "Critical"),
]

SEVERITY_ORDER = {
    SEVERITY_INFO:     0,
    SEVERITY_LOW:      1,
    SEVERITY_MEDIUM:   2,
    SEVERITY_HIGH:     3,
    SEVERITY_CRITICAL: 4,
}

# ---------------------------------------------------------------------------
# Delivery channels
# ---------------------------------------------------------------------------
CHANNEL_IN_APP    = "IN_APP"
CHANNEL_WEBSOCKET = "WEBSOCKET"
CHANNEL_EMAIL     = "EMAIL"
CHANNEL_SMS       = "SMS"
CHANNEL_WHATSAPP  = "WHATSAPP"
CHANNEL_TELEGRAM  = "TELEGRAM"

CHANNEL_CHOICES = [
    (CHANNEL_IN_APP,    "In-App"),
    (CHANNEL_WEBSOCKET, "WebSocket"),
    (CHANNEL_EMAIL,     "Email"),
    (CHANNEL_SMS,       "SMS"),
    (CHANNEL_WHATSAPP,  "WhatsApp"),
    (CHANNEL_TELEGRAM,  "Telegram"),
]

# Channels that are instant / internal (never need provider credentials)
INSTANT_CHANNELS = {CHANNEL_IN_APP, CHANNEL_WEBSOCKET}

# Channels that require external provider configuration
EXTERNAL_CHANNELS = {CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_WHATSAPP, CHANNEL_TELEGRAM}

# ---------------------------------------------------------------------------
# Delivery status
# ---------------------------------------------------------------------------
DELIVERY_PENDING   = "PENDING"
DELIVERY_QUEUED    = "QUEUED"
DELIVERY_SENT      = "SENT"
DELIVERY_DELIVERED = "DELIVERED"
DELIVERY_FAILED    = "FAILED"
DELIVERY_CANCELLED = "CANCELLED"
DELIVERY_NOT_CONFIGURED = "NOT_CONFIGURED"

DELIVERY_STATUS_CHOICES = [
    (DELIVERY_PENDING,        "Pending"),
    (DELIVERY_QUEUED,         "Queued"),
    (DELIVERY_SENT,           "Sent"),
    (DELIVERY_DELIVERED,      "Delivered"),
    (DELIVERY_FAILED,         "Failed"),
    (DELIVERY_CANCELLED,      "Cancelled"),
    (DELIVERY_NOT_CONFIGURED, "Not Configured"),
]

# Terminal statuses — never retry
DELIVERY_TERMINAL_STATUSES = {
    DELIVERY_DELIVERED,
    DELIVERY_FAILED,
    DELIVERY_CANCELLED,
    DELIVERY_NOT_CONFIGURED,
}

# ---------------------------------------------------------------------------
# Recipient delivery status
# ---------------------------------------------------------------------------
RECIPIENT_PENDING      = "PENDING"
RECIPIENT_DELIVERED    = "DELIVERED"
RECIPIENT_FAILED       = "FAILED"
RECIPIENT_READ         = "READ"
RECIPIENT_ACKNOWLEDGED = "ACKNOWLEDGED"

RECIPIENT_STATUS_CHOICES = [
    (RECIPIENT_PENDING,      "Pending"),
    (RECIPIENT_DELIVERED,    "Delivered"),
    (RECIPIENT_FAILED,       "Failed"),
    (RECIPIENT_READ,         "Read"),
    (RECIPIENT_ACKNOWLEDGED, "Acknowledged"),
]

# ---------------------------------------------------------------------------
# Source types (what created this notification)
# ---------------------------------------------------------------------------
SOURCE_ORDER          = "ORDER"
SOURCE_KITCHEN_ORDER  = "KITCHEN_ORDER"
SOURCE_STOCK_BALANCE  = "STOCK_BALANCE"
SOURCE_PAYMENT        = "PAYMENT"
SOURCE_REFUND         = "REFUND"
SOURCE_EXPENSE        = "EXPENSE"
SOURCE_PAYABLE        = "PAYABLE"
SOURCE_SUPPLIER_INVOICE = "SUPPLIER_INVOICE"
SOURCE_ACCOUNTING_POSTING = "ACCOUNTING_POSTING"
SOURCE_CENTRAL_ALERT  = "CENTRAL_ALERT"
SOURCE_CENTRAL_ISSUE  = "CENTRAL_ISSUE"
SOURCE_USER           = "USER"
SOURCE_COUNTER_SESSION = "COUNTER_SESSION"
SOURCE_SYSTEM         = "SYSTEM"

SOURCE_TYPE_CHOICES = [
    (SOURCE_ORDER,              "Order"),
    (SOURCE_KITCHEN_ORDER,      "Kitchen Order"),
    (SOURCE_STOCK_BALANCE,      "Stock Balance"),
    (SOURCE_PAYMENT,            "Payment"),
    (SOURCE_REFUND,             "Refund"),
    (SOURCE_EXPENSE,            "Expense"),
    (SOURCE_PAYABLE,            "Payable"),
    (SOURCE_SUPPLIER_INVOICE,   "Supplier Invoice"),
    (SOURCE_ACCOUNTING_POSTING, "Accounting Posting"),
    (SOURCE_CENTRAL_ALERT,      "Central Alert"),
    (SOURCE_CENTRAL_ISSUE,      "Central Issue"),
    (SOURCE_USER,               "User"),
    (SOURCE_COUNTER_SESSION,    "Counter Session"),
    (SOURCE_SYSTEM,             "System"),
]

# ---------------------------------------------------------------------------
# Provider names
# ---------------------------------------------------------------------------
PROVIDER_DJANGO_EMAIL  = "DJANGO_EMAIL"
PROVIDER_SENDGRID      = "SENDGRID"
PROVIDER_MAILGUN       = "MAILGUN"
PROVIDER_TWILIO        = "TWILIO"
PROVIDER_VONAGE        = "VONAGE"
PROVIDER_WHATSAPP_CLOUD = "WHATSAPP_CLOUD"
PROVIDER_TELEGRAM_BOT  = "TELEGRAM_BOT"

# ---------------------------------------------------------------------------
# Delivery retry policy
# ---------------------------------------------------------------------------
MAX_DELIVERY_ATTEMPTS  = 3
RETRY_DELAYS_SECONDS   = [0, 60, 300]   # immediate, 1m, 5m

# ---------------------------------------------------------------------------
# Rate-limiting / cooldown (seconds)
# ---------------------------------------------------------------------------
COOLDOWN_LOW_STOCK_SECONDS      = 3600   # 1 hour between same low-stock notifications
COOLDOWN_PAYMENT_FAILED_SECONDS = 300    # 5 minutes
COOLDOWN_PROVIDER_FAILURE_ALERT = 600    # 10 minutes — before a new provider-failure central alert
PROVIDER_FAILURE_THRESHOLD      = 5      # failures within window before alert

# ---------------------------------------------------------------------------
# WebSocket event types
# ---------------------------------------------------------------------------
WS_NOTIFICATION_CREATED = "notification.created"
WS_NOTIFICATION_UPDATED = "notification.updated"
WS_NOTIFICATION_READ    = "notification.read"

# WebSocket group name template
WS_GROUP_USER = "notifications_user_{user_id}"

# ---------------------------------------------------------------------------
# Default preferences by notification type
# Key: notification_type
# Value: dict of channel → enabled (bool)
# ---------------------------------------------------------------------------
DEFAULT_CHANNEL_PREFS: dict[str, dict[str, bool]] = {
    # Critical operational
    NOTIF_KITCHEN_ORDER_DELAYED:    {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_KITCHEN_BACKLOG:          {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_KITCHEN_ORDER_READY:      {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_ORDER_CONFIRMED:          {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_ORDER_CANCELLED:          {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_ORDER_READY:              {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    # Inventory
    NOTIF_INVENTORY_LOW_STOCK:      {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_INVENTORY_OUT_OF_STOCK:   {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_INVENTORY_PURCHASE_RECEIVED: {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: False, CHANNEL_EMAIL: False},
    NOTIF_INVENTORY_CONSUMPTION_FAILED: {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    # Payment
    NOTIF_PAYMENT_COMPLETED:        {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_PAYMENT_FAILED:           {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_REFUND_PROCESSED:         {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    # Expense / Financial
    NOTIF_EXPENSE_SUBMITTED:        {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_EXPENSE_APPROVAL_REQUIRED: {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_EXPENSE_APPROVED:         {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_EXPENSE_REJECTED:         {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_PAYABLE_OVERDUE:          {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_SUPPLIER_INVOICE_SUBMITTED: {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    # Accounting
    NOTIF_ACCOUNTING_POSTING_FAILED: {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_ACCOUNTING_PERIOD_CLOSED:  {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: False, CHANNEL_EMAIL: False},
    # Central
    NOTIF_CENTRAL_ALERT_CREATED:    {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_CENTRAL_ALERT_RESOLVED:   {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    NOTIF_CENTRAL_ISSUE_ASSIGNED:   {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_CENTRAL_ISSUE_RESOLVED:   {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    # Access / User
    NOTIF_USER_ACCESS_GRANTED:      {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_USER_ACCESS_REVOKED:      {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_COUNTER_SESSION_CLOSED:   {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: False},
    # System
    NOTIF_SYSTEM_HEALTH_DEGRADED:   {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
    NOTIF_NOTIFICATION_PROVIDER_FAILURE: {CHANNEL_IN_APP: True, CHANNEL_WEBSOCKET: True, CHANNEL_EMAIL: True},
}

# Notification types that are ALWAYS delivered via in-app + websocket (never suppressed by cooldown)
CRITICAL_NOTIFICATION_TYPES = {
    NOTIF_CENTRAL_ALERT_CREATED,
    NOTIF_CENTRAL_ISSUE_ASSIGNED,
    NOTIF_USER_ACCESS_REVOKED,
    NOTIF_SYSTEM_HEALTH_DEGRADED,
    NOTIF_NOTIFICATION_PROVIDER_FAILURE,
    NOTIF_INVENTORY_OUT_OF_STOCK,
    NOTIF_ACCOUNTING_POSTING_FAILED,
}

# Notification types subject to rate-limiting / cooldown (non-critical informational)
COOLDOWN_NOTIFICATION_TYPES = {
    NOTIF_INVENTORY_LOW_STOCK,
    NOTIF_PAYMENT_FAILED,
    NOTIF_KITCHEN_BACKLOG,
    NOTIF_KITCHEN_ORDER_DELAYED,
}

# ---------------------------------------------------------------------------
# Audit action codes
# ---------------------------------------------------------------------------
AUDIT_NOTIFICATION_CREATED          = "NOTIFICATION_CREATED"
AUDIT_NOTIFICATION_DELIVERED        = "NOTIFICATION_DELIVERED"
AUDIT_NOTIFICATION_FAILED           = "NOTIFICATION_FAILED"
AUDIT_NOTIFICATION_READ             = "NOTIFICATION_READ"
AUDIT_NOTIFICATION_ACKNOWLEDGED     = "NOTIFICATION_ACKNOWLEDGED"
AUDIT_NOTIFICATION_PREF_UPDATED     = "NOTIFICATION_PREFERENCE_UPDATED"
AUDIT_NOTIFICATION_TEMPLATE_CREATED = "NOTIFICATION_TEMPLATE_CREATED"
AUDIT_NOTIFICATION_TEMPLATE_UPDATED = "NOTIFICATION_TEMPLATE_UPDATED"
AUDIT_NOTIFICATION_PROVIDER_UPDATED = "NOTIFICATION_PROVIDER_UPDATED"

# ---------------------------------------------------------------------------
# Allowed safe template variables (for template renderer)
# ---------------------------------------------------------------------------
SAFE_TEMPLATE_VARS = frozenset({
    "order_number",
    "branch_name",
    "restaurant_name",
    "company_name",
    "item_name",
    "quantity",
    "alert_title",
    "issue_title",
    "expense_number",
    "payable_amount",
    "payable_due_date",
    "payment_amount",
    "refund_amount",
    "user_name",
    "user_email",
    "kitchen_order_number",
    "delay_minutes",
    "low_stock_count",
    "provider_name",
    "channel_name",
    "failure_reason",
    "action_url",
    "timestamp",
})

# ---------------------------------------------------------------------------
# Cache keys and TTLs
# ---------------------------------------------------------------------------
CACHE_TTL_UNREAD_COUNT  = 30   # seconds
CACHE_KEY_UNREAD_COUNT  = "notifications:unread:{user_id}"
CACHE_KEY_COOLDOWN      = "notifications:cooldown:{notif_type}:{scope_key}"
CACHE_KEY_PROVIDER_FAIL = "notifications:provider_fail:{channel}:{company_id}"
