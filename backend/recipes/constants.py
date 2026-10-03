# =============================================================================
# RestaurantFlow — Recipes Constants
# Phase 11: Recipe and Ingredient Consumption
#
# All constants for the recipes domain.
# Import from here — never hard-code values in models or services.
# =============================================================================

from decimal import Decimal


# ---------------------------------------------------------------------------
# Recipe Status
# ---------------------------------------------------------------------------

RECIPE_DRAFT    = "DRAFT"
RECIPE_ACTIVE   = "ACTIVE"
RECIPE_INACTIVE = "INACTIVE"
RECIPE_ARCHIVED = "ARCHIVED"

RECIPE_STATUS_CHOICES = [
    (RECIPE_DRAFT,    "Draft"),
    (RECIPE_ACTIVE,   "Active"),
    (RECIPE_INACTIVE, "Inactive"),
    (RECIPE_ARCHIVED, "Archived"),
]

RECIPE_TERMINAL_STATUSES = {RECIPE_ARCHIVED}

# Statuses from which activation is allowed
RECIPE_ACTIVATABLE_STATUSES = {RECIPE_DRAFT}

# Statuses from which archiving is allowed
RECIPE_ARCHIVABLE_STATUSES = {RECIPE_DRAFT, RECIPE_ACTIVE, RECIPE_INACTIVE}


# ---------------------------------------------------------------------------
# Consumption Trigger
# ---------------------------------------------------------------------------

TRIGGER_KITCHEN_STARTED   = "KITCHEN_STARTED"
TRIGGER_KITCHEN_COMPLETED = "KITCHEN_COMPLETED"

CONSUMPTION_TRIGGER_CHOICES = [
    (TRIGGER_KITCHEN_STARTED,   "Kitchen Started (PREPARING)"),
    (TRIGGER_KITCHEN_COMPLETED, "Kitchen Completed (READY)"),
]

# Default trigger — can be overridden at restaurant-settings level
DEFAULT_CONSUMPTION_TRIGGER = TRIGGER_KITCHEN_COMPLETED


# ---------------------------------------------------------------------------
# Consumption Batch Status
# ---------------------------------------------------------------------------

BATCH_PENDING    = "PENDING"
BATCH_PROCESSING = "PROCESSING"
BATCH_COMPLETED  = "COMPLETED"
BATCH_FAILED     = "FAILED"
BATCH_REVERSED   = "REVERSED"

BATCH_STATUS_CHOICES = [
    (BATCH_PENDING,    "Pending"),
    (BATCH_PROCESSING, "Processing"),
    (BATCH_COMPLETED,  "Completed"),
    (BATCH_FAILED,     "Failed"),
    (BATCH_REVERSED,   "Reversed"),
]


# ---------------------------------------------------------------------------
# Stock Consumption Status
# ---------------------------------------------------------------------------

CONSUMPTION_PENDING  = "PENDING"
CONSUMPTION_CONSUMED = "CONSUMED"
CONSUMPTION_FAILED   = "FAILED"
CONSUMPTION_REVERSED = "REVERSED"

CONSUMPTION_STATUS_CHOICES = [
    (CONSUMPTION_PENDING,  "Pending"),
    (CONSUMPTION_CONSUMED, "Consumed"),
    (CONSUMPTION_FAILED,   "Failed"),
    (CONSUMPTION_REVERSED, "Reversed"),
]


# ---------------------------------------------------------------------------
# Reference types for stock movements originating from consumption
# ---------------------------------------------------------------------------

REF_KITCHEN_ORDER   = "KITCHEN_ORDER"
REF_CONSUMPTION_BATCH = "CONSUMPTION_BATCH"
REF_MANUAL_CONSUMPTION = "MANUAL_CONSUMPTION"


# ---------------------------------------------------------------------------
# Stock movement type for consumption
# ---------------------------------------------------------------------------

MOVEMENT_CONSUMPTION          = "CONSUMPTION"
MOVEMENT_CONSUMPTION_REVERSAL = "CONSUMPTION_REVERSAL"


# ---------------------------------------------------------------------------
# Precision constants (mirrors inventory/constants.py pattern)
# ---------------------------------------------------------------------------

DECIMAL_QTY  = Decimal("0.001")   # 3dp for quantities
DECIMAL_COST = Decimal("0.01")    # 2dp for monetary values
DECIMAL_RATE = Decimal("0.001")   # 3dp for rates
ZERO         = Decimal("0.000")
ZERO_COST    = Decimal("0.00")

# Preparation loss max percent guard
MAX_PREPARATION_LOSS_PCT = Decimal("100")
MIN_PREPARATION_LOSS_PCT = Decimal("0")


# ---------------------------------------------------------------------------
# Audit actions
# ---------------------------------------------------------------------------

AUDIT_RECIPE_CREATED          = "RECIPE_CREATED"
AUDIT_RECIPE_UPDATED          = "RECIPE_UPDATED"
AUDIT_RECIPE_ACTIVATED        = "RECIPE_ACTIVATED"
AUDIT_RECIPE_ARCHIVED         = "RECIPE_ARCHIVED"
AUDIT_CONSUMPTION_CREATED     = "CONSUMPTION_CREATED"
AUDIT_CONSUMPTION_COMPLETED   = "CONSUMPTION_COMPLETED"
AUDIT_CONSUMPTION_FAILED      = "CONSUMPTION_FAILED"
AUDIT_CONSUMPTION_REVERSED    = "CONSUMPTION_REVERSED"
AUDIT_MANUAL_CONSUMPTION      = "MANUAL_CONSUMPTION_CREATED"
