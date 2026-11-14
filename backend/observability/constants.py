# =============================================================================
# RestaurantFlow — Observability Constants
# Phase 24
#
# Centralised configuration values for the observability app. Import from
# here; never hard-code magic strings.
# =============================================================================

# ---------------------------------------------------------------------------
# Service / environment identity
# ---------------------------------------------------------------------------
SERVICE_NAME = "restaurantflow-api"

ENV_PRODUCTION = "production"
ENV_STAGING = "staging"
ENV_DEVELOPMENT = "development"

# ---------------------------------------------------------------------------
# Request correlation
# ---------------------------------------------------------------------------
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_MAX_LENGTH = 128
# Accept only this character class for client-supplied IDs to prevent log
# injection and keep correlation keys safe to index.
REQUEST_ID_PATTERN = r"^[A-Za-z0-9._\-]{1,128}$"

# Fallback when a client supplies an invalid (e.g. too long / unsafe) ID.
REQUEST_ID_INVALID = "[invalid]"

# ---------------------------------------------------------------------------
# Log formats
# ---------------------------------------------------------------------------
LOG_FORMAT_JSON = "json"
LOG_FORMAT_TEXT = "text"

# ---------------------------------------------------------------------------
# Sensitive fields that must NEVER appear in structured logs.
# Matched case-insensitively against record keys and the redaction scan.
# ---------------------------------------------------------------------------
SENSITIVE_LOG_KEYS = {
    "password",
    "password1",
    "password2",
    "new_password",
    "old_password",
    "token",
    "access_token",
    "refresh_token",
    "auth",
    "authorization",
    "api_key",
    "apikey",
    "secret",
    "secret_key",
    "db_password",
    "redis_password",
    "card_number",
    "pan",
    "cvv",
    "cvc",
    "upi_id",
    "upi_pin",
    "session_key",
    "private_key",
}

# Default structured-log fields emitted in order.
LOG_BASE_FIELDS = (
    "timestamp",
    "level",
    "service",
    "environment",
    "request_id",
    "user_id",
    "company_id",
    "restaurant_id",
    "branch_id",
    "module",
    "event",
    "message",
    "duration_ms",
    "error_code",
)

# ---------------------------------------------------------------------------
# Metric names (low-cardinality by design — labels are explicit, capped)
# ---------------------------------------------------------------------------
METRIC_HTTP_REQUESTS_TOTAL = "restaurantflow_http_requests_total"
METRIC_HTTP_REQUEST_DURATION = "restaurantflow_http_request_duration_seconds"
METRIC_HTTP_ERRORS_TOTAL = "restaurantflow_http_errors_total"
METRIC_HTTP_REQUEST_SIZE = "restaurantflow_http_request_size_bytes"
METRIC_HTTP_RESPONSE_SIZE = "restaurantflow_http_response_size_bytes"

METRIC_CELERY_TASKS_TOTAL = "restaurantflow_celery_tasks_total"
METRIC_CELERY_TASK_DURATION = "restaurantflow_celery_task_duration_seconds"
METRIC_CELERY_TASK_FAILURES = "restaurantflow_celery_task_failures_total"
METRIC_CELERY_QUEUE_DEPTH = "restaurantflow_celery_queue_depth"
METRIC_CELERY_WORKER_UP = "restaurantflow_celery_worker_up"

METRIC_DB_CONNECTIONS_IN_USE = "restaurantflow_db_connections_in_use"
METRIC_DB_CONNECTIONS_AVAILABLE = "restaurantflow_db_connections_available"

METRIC_WS_CONNECTIONS = "restaurantflow_websocket_connections"
METRIC_WS_EVENTS = "restaurantflow_websocket_events_total"
METRIC_WS_ERRORS = "restaurantflow_websocket_errors_total"

METRIC_BUSINESS_EVENTS = "restaurantflow_business_events_total"

METRIC_HEALTH_CHECK = "restaurantflow_health_check"

# Hard cap on distinct label combinations per metric. Prevents runaway
# cardinality (e.g. a developer accidentally labelling by user_id) from
# exhausting memory. New combinations beyond the cap are dropped + logged.
METRIC_CARDINALITY_CAP = 4096

# Default histogram buckets for request/task latency (seconds).
DEFAULT_LATENCY_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0,
)

# Default buckets for byte sizes (powers-of-two-ish).
DEFAULT_SIZE_BUCKETS = (
    64, 256, 1024, 4096, 16384, 65536, 262144, 1048576, 10485760,
)

# ---------------------------------------------------------------------------
# Business events emitted by record_business_event()
# ---------------------------------------------------------------------------
EVENT_ORDER_CREATION_FAILED = "order.creation.failed"
EVENT_ORDER_CONFIRMATION_FAILED = "order.confirmation.failed"
EVENT_DUPLICATE_REQUEST = "order.duplicate_request"
EVENT_ORDER_DELAYED = "order.abnormally_delayed"
EVENT_KITCHEN_BACKLOG = "kitchen.backlog"
EVENT_KITCHEN_PREPARATION_DELAYED = "kitchen.preparation.delayed"
EVENT_KITCHEN_EVENT_FAILED = "kitchen.event.failed"
EVENT_BILL_FINALIZATION_FAILED = "bill.finalization.failed"
EVENT_PAYMENT_COMPLETION_FAILED = "payment.completion.failed"
EVENT_REFUND_PROCESSING_FAILED = "refund.processing.failed"
EVENT_IDEMPOTENCY_CONFLICT = "payment.idempotency_conflict"
EVENT_INVENTORY_CONSUMPTION_FAILED = "inventory.consumption.failed"
EVENT_INVENTORY_TRANSFER_FAILED = "inventory.transfer.failed"
EVENT_NEGATIVE_STOCK_PREVENTED = "inventory.negative_stock_prevented"
EVENT_REPEATED_LOW_STOCK = "inventory.repeated_low_stock"
EVENT_JOURNAL_POSTING_FAILED = "accounting.journal_posting.failed"
EVENT_UNBALANCED_JOURNAL_REJECTED = "accounting.unbalanced_journal_rejected"
EVENT_ACCOUNTING_PERIOD_CLOSE_FAILED = "accounting.period_close.failed"
EVENT_RECONCILIATION_EXCEPTION = "accounting.reconciliation_exception"
EVENT_MENU_ROLLOUT_FAILED = "enterprise.menu_rollout.failed"
EVENT_CONFIG_UPDATE_FAILED = "enterprise.configuration_update.failed"
EVENT_STAFF_TRANSFER_FAILED = "enterprise.staff_transfer.failed"
EVENT_BRANCH_OPENING_FAILED = "enterprise.branch_opening.failed"

# ---------------------------------------------------------------------------
# Alert source / routing (forwarded into Central Control)
# ---------------------------------------------------------------------------
ALERT_SOURCE_MONITORING = "MONITORING"
ALERTMANAGER_SEVERITY_MAP = {
    "critical": "CRITICAL",
    "high": "HIGH",
    "warning": "MEDIUM",
    "info": "INFO",
}
