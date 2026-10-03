# =============================================================================
# RestaurantFlow — Payment Constants
# Phase 9
#
# Centralised constants for the payments module.
# Business rules that are expressed as numbers live here.
# Import from here — never hard-code magic numbers in services or views.
#
# NOTE: We use string literals for status/method constants to avoid circular
# imports at module load time. The model enums are the canonical definition;
# these strings must match them exactly.
# =============================================================================

from decimal import Decimal

# ---------------------------------------------------------------------------
# Monetary precision
# ---------------------------------------------------------------------------

ZERO = Decimal("0.00")
ONE  = Decimal("1.00")

# ---------------------------------------------------------------------------
# Payment amount rules
# ---------------------------------------------------------------------------

# Minimum payment amount we accept
MIN_PAYMENT_AMOUNT = Decimal("0.01")

# Maximum single payment amount (sanity cap — not a business rule per se)
MAX_PAYMENT_AMOUNT = Decimal("9999999.99")

# ---------------------------------------------------------------------------
# Refund rules
# ---------------------------------------------------------------------------

# Minimum refund amount
MIN_REFUND_AMOUNT = Decimal("0.01")

# Minimum refund reason length (characters)
MIN_REFUND_REASON_LENGTH = 5

# ---------------------------------------------------------------------------
# Cash rules
# ---------------------------------------------------------------------------

# Maximum change we will allow
# (extremely large change likely indicates a data-entry error)
MAX_CHANGE_AMOUNT = Decimal("999999.99")

# ---------------------------------------------------------------------------
# Payment method string constants — match PaymentMethod enum choices exactly
# ---------------------------------------------------------------------------

CASH_METHODS: set[str] = {"CASH"}

# Methods that MUST have a transaction_reference supplied
DIGITAL_METHODS: set[str] = {
    "UPI",
    "CARD",
    "NET_BANKING",
    "BANK_TRANSFER",
    "CHEQUE",
}

# Methods where transaction_reference is optional
OPTIONAL_REF_METHODS: set[str] = {
    "WALLET",
    "CREDIT",
    "OTHER",
}

# ---------------------------------------------------------------------------
# Bill payment status thresholds
# ---------------------------------------------------------------------------

# When total paid >= bill.grand_total the bill is PAID
PAID_THRESHOLD_RATIO = Decimal("1.00")

# ---------------------------------------------------------------------------
# Idempotency key constraints
# ---------------------------------------------------------------------------

IDEMPOTENCY_KEY_MAX_LENGTH = 128
IDEMPOTENCY_KEY_MIN_LENGTH = 8   # encourage UUID-like keys; not strictly enforced

# ---------------------------------------------------------------------------
# Payment status valid transitions — string literals matching enum choices
# ---------------------------------------------------------------------------

PAYMENT_VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING":            {"COMPLETED", "FAILED", "CANCELLED"},
    "COMPLETED":          {"REFUNDED", "PARTIALLY_REFUNDED"},
    "FAILED":             set(),
    "CANCELLED":          set(),
    "REFUNDED":           set(),
    "PARTIALLY_REFUNDED": {"REFUNDED"},
}

# ---------------------------------------------------------------------------
# Refund status valid transitions
# ---------------------------------------------------------------------------

REFUND_VALID_TRANSITIONS: dict[str, set[str]] = {
    "REQUESTED": {"APPROVED", "REJECTED", "CANCELLED"},
    "APPROVED":  {"PROCESSED"},
    "REJECTED":  set(),
    "PROCESSED": set(),
    "CANCELLED": set(),
}

# ---------------------------------------------------------------------------
# Sequence keys
# ---------------------------------------------------------------------------

PAYMENT_SEQUENCE_KEY = "GLOBAL"
REFUND_SEQUENCE_KEY  = "REFUND"
