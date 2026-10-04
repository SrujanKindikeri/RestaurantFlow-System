# =============================================================================
# RestaurantFlow — Financials Constants
# Phase 12
# =============================================================================

from decimal import Decimal

# ---------------------------------------------------------------------------
# Decimal precision sentinels
# ---------------------------------------------------------------------------
DECIMAL_MONEY = Decimal("0.01")   # 2 decimal places for monetary values
ZERO = Decimal("0.00")
TWO_PLACES = Decimal("0.01")

# ---------------------------------------------------------------------------
# Expense Status
# ---------------------------------------------------------------------------
EXPENSE_DRAFT     = "DRAFT"
EXPENSE_SUBMITTED = "SUBMITTED"
EXPENSE_APPROVED  = "APPROVED"
EXPENSE_REJECTED  = "REJECTED"
EXPENSE_CANCELLED = "CANCELLED"

EXPENSE_STATUS_CHOICES = [
    (EXPENSE_DRAFT,     "Draft"),
    (EXPENSE_SUBMITTED, "Submitted"),
    (EXPENSE_APPROVED,  "Approved"),
    (EXPENSE_REJECTED,  "Rejected"),
    (EXPENSE_CANCELLED, "Cancelled"),
]

# Valid state transitions for Expense
EXPENSE_VALID_TRANSITIONS = {
    EXPENSE_DRAFT:     [EXPENSE_SUBMITTED, EXPENSE_CANCELLED],
    EXPENSE_SUBMITTED: [EXPENSE_APPROVED, EXPENSE_REJECTED],
    EXPENSE_APPROVED:  [],   # terminal — corrections required
    EXPENSE_REJECTED:  [],   # terminal
    EXPENSE_CANCELLED: [],   # terminal
}

# ---------------------------------------------------------------------------
# Expense Payment Status
# ---------------------------------------------------------------------------
PAYMENT_STATUS_UNPAID         = "UNPAID"
PAYMENT_STATUS_PARTIALLY_PAID = "PARTIALLY_PAID"
PAYMENT_STATUS_PAID           = "PAID"

EXPENSE_PAYMENT_STATUS_CHOICES = [
    (PAYMENT_STATUS_UNPAID,         "Unpaid"),
    (PAYMENT_STATUS_PARTIALLY_PAID, "Partially Paid"),
    (PAYMENT_STATUS_PAID,           "Paid"),
]

# ---------------------------------------------------------------------------
# Expense Approval Status
# ---------------------------------------------------------------------------
APPROVAL_PENDING   = "PENDING"
APPROVAL_APPROVED  = "APPROVED"
APPROVAL_REJECTED  = "REJECTED"
APPROVAL_CANCELLED = "CANCELLED"

APPROVAL_STATUS_CHOICES = [
    (APPROVAL_PENDING,   "Pending"),
    (APPROVAL_APPROVED,  "Approved"),
    (APPROVAL_REJECTED,  "Rejected"),
    (APPROVAL_CANCELLED, "Cancelled"),
]

# ---------------------------------------------------------------------------
# Expense Correction Status
# ---------------------------------------------------------------------------
CORRECTION_PENDING   = "PENDING"
CORRECTION_APPROVED  = "APPROVED"
CORRECTION_REJECTED  = "REJECTED"
CORRECTION_CANCELLED = "CANCELLED"

CORRECTION_STATUS_CHOICES = [
    (CORRECTION_PENDING,   "Pending"),
    (CORRECTION_APPROVED,  "Approved"),
    (CORRECTION_REJECTED,  "Rejected"),
    (CORRECTION_CANCELLED, "Cancelled"),
]

# Correction types
CORRECTION_TYPE_AMOUNT      = "AMOUNT_CORRECTION"
CORRECTION_TYPE_CATEGORY    = "CATEGORY_CORRECTION"
CORRECTION_TYPE_DATE        = "DATE_CORRECTION"
CORRECTION_TYPE_VENDOR      = "VENDOR_CORRECTION"
CORRECTION_TYPE_CANCELLATION = "CANCELLATION"
CORRECTION_TYPE_OTHER       = "OTHER"

CORRECTION_TYPE_CHOICES = [
    (CORRECTION_TYPE_AMOUNT,       "Amount Correction"),
    (CORRECTION_TYPE_CATEGORY,     "Category Correction"),
    (CORRECTION_TYPE_DATE,         "Date Correction"),
    (CORRECTION_TYPE_VENDOR,       "Vendor Correction"),
    (CORRECTION_TYPE_CANCELLATION, "Cancellation"),
    (CORRECTION_TYPE_OTHER,        "Other"),
]

# ---------------------------------------------------------------------------
# Recurring Expense Frequency
# ---------------------------------------------------------------------------
FREQ_WEEKLY    = "WEEKLY"
FREQ_MONTHLY   = "MONTHLY"
FREQ_QUARTERLY = "QUARTERLY"
FREQ_YEARLY    = "YEARLY"

FREQUENCY_CHOICES = [
    (FREQ_WEEKLY,    "Weekly"),
    (FREQ_MONTHLY,   "Monthly"),
    (FREQ_QUARTERLY, "Quarterly"),
    (FREQ_YEARLY,    "Yearly"),
]

# ---------------------------------------------------------------------------
# Supplier Invoice Status
# ---------------------------------------------------------------------------
SINV_DRAFT           = "DRAFT"
SINV_SUBMITTED       = "SUBMITTED"
SINV_APPROVED        = "APPROVED"
SINV_PARTIALLY_PAID  = "PARTIALLY_PAID"
SINV_PAID            = "PAID"
SINV_CANCELLED       = "CANCELLED"

SUPPLIER_INVOICE_STATUS_CHOICES = [
    (SINV_DRAFT,          "Draft"),
    (SINV_SUBMITTED,      "Submitted"),
    (SINV_APPROVED,       "Approved"),
    (SINV_PARTIALLY_PAID, "Partially Paid"),
    (SINV_PAID,           "Paid"),
    (SINV_CANCELLED,      "Cancelled"),
]

SINV_VALID_TRANSITIONS = {
    SINV_DRAFT:          [SINV_SUBMITTED, SINV_CANCELLED],
    SINV_SUBMITTED:      [SINV_APPROVED, SINV_CANCELLED],
    SINV_APPROVED:       [SINV_PARTIALLY_PAID, SINV_PAID, SINV_CANCELLED],
    SINV_PARTIALLY_PAID: [SINV_PAID, SINV_CANCELLED],
    SINV_PAID:           [],    # terminal
    SINV_CANCELLED:      [],    # terminal
}

# ---------------------------------------------------------------------------
# Payable Type
# ---------------------------------------------------------------------------
PAYABLE_TYPE_SUPPLIER_INVOICE = "SUPPLIER_INVOICE"
PAYABLE_TYPE_EXPENSE          = "EXPENSE"

PAYABLE_TYPE_CHOICES = [
    (PAYABLE_TYPE_SUPPLIER_INVOICE, "Supplier Invoice"),
    (PAYABLE_TYPE_EXPENSE,          "Expense"),
]

# ---------------------------------------------------------------------------
# Payable Status
# ---------------------------------------------------------------------------
PAYABLE_OPEN            = "OPEN"
PAYABLE_PARTIALLY_PAID  = "PARTIALLY_PAID"
PAYABLE_PAID            = "PAID"
PAYABLE_OVERDUE         = "OVERDUE"
PAYABLE_CANCELLED       = "CANCELLED"

PAYABLE_STATUS_CHOICES = [
    (PAYABLE_OPEN,           "Open"),
    (PAYABLE_PARTIALLY_PAID, "Partially Paid"),
    (PAYABLE_PAID,           "Paid"),
    (PAYABLE_OVERDUE,        "Overdue"),
    (PAYABLE_CANCELLED,      "Cancelled"),
]

# ---------------------------------------------------------------------------
# Audit actions
# ---------------------------------------------------------------------------
AUDIT_EXPENSE_CREATED              = "EXPENSE_CREATED"
AUDIT_EXPENSE_UPDATED              = "EXPENSE_UPDATED"
AUDIT_EXPENSE_SUBMITTED            = "EXPENSE_SUBMITTED"
AUDIT_EXPENSE_APPROVED             = "EXPENSE_APPROVED"
AUDIT_EXPENSE_REJECTED             = "EXPENSE_REJECTED"
AUDIT_EXPENSE_CANCELLED            = "EXPENSE_CANCELLED"
AUDIT_EXPENSE_CORRECTION_REQUESTED = "EXPENSE_CORRECTION_REQUESTED"
AUDIT_EXPENSE_CORRECTION_APPROVED  = "EXPENSE_CORRECTION_APPROVED"
AUDIT_EXPENSE_CORRECTION_REJECTED  = "EXPENSE_CORRECTION_REJECTED"
AUDIT_EXPENSE_ATTACHMENT_UPLOADED  = "EXPENSE_ATTACHMENT_UPLOADED"
AUDIT_EXPENSE_ATTACHMENT_DELETED   = "EXPENSE_ATTACHMENT_DELETED"
AUDIT_RECURRING_CREATED            = "RECURRING_EXPENSE_CREATED"
AUDIT_RECURRING_UPDATED            = "RECURRING_EXPENSE_UPDATED"
AUDIT_RECURRING_DISABLED           = "RECURRING_EXPENSE_DISABLED"
AUDIT_SINV_CREATED                 = "SUPPLIER_INVOICE_CREATED"
AUDIT_SINV_SUBMITTED               = "SUPPLIER_INVOICE_SUBMITTED"
AUDIT_SINV_APPROVED                = "SUPPLIER_INVOICE_APPROVED"
AUDIT_SINV_CANCELLED               = "SUPPLIER_INVOICE_CANCELLED"
AUDIT_PAYABLE_CREATED              = "PAYABLE_CREATED"
AUDIT_PAYABLE_UPDATED              = "PAYABLE_UPDATED"
AUDIT_PAYABLE_STATUS_CHANGED       = "PAYABLE_STATUS_CHANGED"

AUDIT_ACTION_CHOICES = [
    (AUDIT_EXPENSE_CREATED,              "Expense Created"),
    (AUDIT_EXPENSE_UPDATED,              "Expense Updated"),
    (AUDIT_EXPENSE_SUBMITTED,            "Expense Submitted"),
    (AUDIT_EXPENSE_APPROVED,             "Expense Approved"),
    (AUDIT_EXPENSE_REJECTED,             "Expense Rejected"),
    (AUDIT_EXPENSE_CANCELLED,            "Expense Cancelled"),
    (AUDIT_EXPENSE_CORRECTION_REQUESTED, "Expense Correction Requested"),
    (AUDIT_EXPENSE_CORRECTION_APPROVED,  "Expense Correction Approved"),
    (AUDIT_EXPENSE_CORRECTION_REJECTED,  "Expense Correction Rejected"),
    (AUDIT_EXPENSE_ATTACHMENT_UPLOADED,  "Expense Attachment Uploaded"),
    (AUDIT_EXPENSE_ATTACHMENT_DELETED,   "Expense Attachment Deleted"),
    (AUDIT_RECURRING_CREATED,            "Recurring Expense Created"),
    (AUDIT_RECURRING_UPDATED,            "Recurring Expense Updated"),
    (AUDIT_RECURRING_DISABLED,           "Recurring Expense Disabled"),
    (AUDIT_SINV_CREATED,                 "Supplier Invoice Created"),
    (AUDIT_SINV_SUBMITTED,               "Supplier Invoice Submitted"),
    (AUDIT_SINV_APPROVED,                "Supplier Invoice Approved"),
    (AUDIT_SINV_CANCELLED,               "Supplier Invoice Cancelled"),
    (AUDIT_PAYABLE_CREATED,              "Payable Created"),
    (AUDIT_PAYABLE_UPDATED,              "Payable Updated"),
    (AUDIT_PAYABLE_STATUS_CHANGED,       "Payable Status Changed"),
]

# ---------------------------------------------------------------------------
# Expense number / Supplier-Invoice number formats
# ---------------------------------------------------------------------------
EXPENSE_NUMBER_FORMAT  = "EXP-{seq:06d}"
SINV_NUMBER_FORMAT     = "SINV-{seq:06d}"

# ---------------------------------------------------------------------------
# Attachment constraints
# ---------------------------------------------------------------------------
MAX_ATTACHMENT_SIZE_MB   = 10
MAX_ATTACHMENT_SIZE_BYTES = MAX_ATTACHMENT_SIZE_MB * 1024 * 1024

ALLOWED_ATTACHMENT_CONTENT_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}

ALLOWED_ATTACHMENT_EXTENSIONS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".webp",
    ".doc", ".docx", ".xls", ".xlsx",
}
