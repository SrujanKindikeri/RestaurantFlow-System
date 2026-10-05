# =============================================================================
# RestaurantFlow — CRM Constants
# Phase 17
#
# All magic strings and choices live here.
# Never hard-code these values in models, services, or views.
# =============================================================================


# ---------------------------------------------------------------------------
# Permission codes
# ---------------------------------------------------------------------------

PERM_CUSTOMER_VIEW               = "customer.view"
PERM_CUSTOMER_CREATE             = "customer.create"
PERM_CUSTOMER_UPDATE             = "customer.update"
PERM_CUSTOMER_BLOCK              = "customer.block"
PERM_CUSTOMER_LINK               = "customer.link"
PERM_CUSTOMER_HISTORY_VIEW       = "customer.history.view"
PERM_CUSTOMER_CONTACT_VIEW       = "customer.contact.view"
PERM_CUSTOMER_MERGE_REQUEST      = "customer.merge.request"
PERM_CUSTOMER_MERGE_APPROVE      = "customer.merge.approve"
PERM_CUSTOMER_TAG_VIEW           = "customer.tag.view"
PERM_CUSTOMER_TAG_MANAGE         = "customer.tag.manage"
PERM_CUSTOMER_SEGMENT_VIEW       = "customer.segment.view"
PERM_CUSTOMER_SEGMENT_MANAGE     = "customer.segment.manage"
PERM_CUSTOMER_PREFERENCE_VIEW    = "customer.preference.view"
PERM_CUSTOMER_PREFERENCE_MANAGE  = "customer.preference.manage"
PERM_LOYALTY_VIEW                = "loyalty.view"
PERM_LOYALTY_MANAGE              = "loyalty.manage"
PERM_LOYALTY_EARN                = "loyalty.earn"
PERM_LOYALTY_REDEEM              = "loyalty.redeem"
PERM_LOYALTY_ADJUST              = "loyalty.adjust"
PERM_REWARD_VIEW                 = "reward.view"
PERM_REWARD_MANAGE               = "reward.manage"
PERM_REWARD_REDEEM               = "reward.redeem"
PERM_FEEDBACK_VIEW               = "feedback.view"
PERM_FEEDBACK_CREATE             = "feedback.create"
PERM_FEEDBACK_UPDATE             = "feedback.update"
PERM_FEEDBACK_MODERATE           = "feedback.moderate"
PERM_FEEDBACK_RESOLVE            = "feedback.resolve"
PERM_CUSTOMER_CONSENT_VIEW       = "customer.consent.view"
PERM_CUSTOMER_CONSENT_MANAGE     = "customer.consent.manage"
PERM_CRM_DASHBOARD_VIEW          = "crm.dashboard.view"
PERM_CRM_EXPORT                  = "crm.export"

ALL_CRM_PERMISSIONS = [
    (PERM_CUSTOMER_VIEW,              "View Customers",                   "customer", "view"),
    (PERM_CUSTOMER_CREATE,            "Create Customers",                 "customer", "create"),
    (PERM_CUSTOMER_UPDATE,            "Update Customers",                 "customer", "update"),
    (PERM_CUSTOMER_BLOCK,             "Block Customers",                  "customer", "block"),
    (PERM_CUSTOMER_LINK,              "Link Customer to Order",           "customer", "link"),
    (PERM_CUSTOMER_HISTORY_VIEW,      "View Customer History",            "customer", "history.view"),
    (PERM_CUSTOMER_CONTACT_VIEW,      "View Customer Contact Info",       "customer", "contact.view"),
    (PERM_CUSTOMER_MERGE_REQUEST,     "Request Customer Merge",           "customer", "merge.request"),
    (PERM_CUSTOMER_MERGE_APPROVE,     "Approve Customer Merge",           "customer", "merge.approve"),
    (PERM_CUSTOMER_TAG_VIEW,          "View Customer Tags",               "customer", "tag.view"),
    (PERM_CUSTOMER_TAG_MANAGE,        "Manage Customer Tags",             "customer", "tag.manage"),
    (PERM_CUSTOMER_SEGMENT_VIEW,      "View Customer Segments",           "customer", "segment.view"),
    (PERM_CUSTOMER_SEGMENT_MANAGE,    "Manage Customer Segments",         "customer", "segment.manage"),
    (PERM_CUSTOMER_PREFERENCE_VIEW,   "View Customer Preferences",        "customer", "preference.view"),
    (PERM_CUSTOMER_PREFERENCE_MANAGE, "Manage Customer Preferences",      "customer", "preference.manage"),
    (PERM_LOYALTY_VIEW,               "View Loyalty",                     "loyalty",  "view"),
    (PERM_LOYALTY_MANAGE,             "Manage Loyalty Program",           "loyalty",  "manage"),
    (PERM_LOYALTY_EARN,               "Award Loyalty Points",             "loyalty",  "earn"),
    (PERM_LOYALTY_REDEEM,             "Redeem Loyalty Points",            "loyalty",  "redeem"),
    (PERM_LOYALTY_ADJUST,             "Adjust Loyalty Points",            "loyalty",  "adjust"),
    (PERM_REWARD_VIEW,                "View Rewards",                     "reward",   "view"),
    (PERM_REWARD_MANAGE,              "Manage Rewards",                   "reward",   "manage"),
    (PERM_REWARD_REDEEM,              "Redeem Rewards",                   "reward",   "redeem"),
    (PERM_FEEDBACK_VIEW,              "View Customer Feedback",           "feedback", "view"),
    (PERM_FEEDBACK_CREATE,            "Create Customer Feedback",         "feedback", "create"),
    (PERM_FEEDBACK_UPDATE,            "Update Customer Feedback",         "feedback", "update"),
    (PERM_FEEDBACK_MODERATE,          "Moderate Customer Feedback",       "feedback", "moderate"),
    (PERM_FEEDBACK_RESOLVE,           "Resolve Customer Feedback",        "feedback", "resolve"),
    (PERM_CUSTOMER_CONSENT_VIEW,      "View Customer Consents",           "customer", "consent.view"),
    (PERM_CUSTOMER_CONSENT_MANAGE,    "Manage Customer Consents",         "customer", "consent.manage"),
    (PERM_CRM_DASHBOARD_VIEW,         "View CRM Dashboard",               "crm",      "dashboard.view"),
    (PERM_CRM_EXPORT,                 "Export CRM Data",                  "crm",      "export"),
]


# ---------------------------------------------------------------------------
# Gender choices
# ---------------------------------------------------------------------------
GENDER_MALE    = "M"
GENDER_FEMALE  = "F"
GENDER_OTHER   = "O"

GENDER_CHOICES = [
    (GENDER_MALE,   "Male"),
    (GENDER_FEMALE, "Female"),
    (GENDER_OTHER,  "Other"),
]


# ---------------------------------------------------------------------------
# Dietary preferences
# ---------------------------------------------------------------------------
DIET_VEG     = "VEG"
DIET_NON_VEG = "NON_VEG"
DIET_EGG     = "EGG"
DIET_VEGAN   = "VEGAN"
DIET_JAIN    = "JAIN"
DIET_OTHER   = "OTHER"
DIET_UNKNOWN = "UNKNOWN"

DIETARY_CHOICES = [
    (DIET_VEG,     "Vegetarian"),
    (DIET_NON_VEG, "Non-Vegetarian"),
    (DIET_EGG,     "Eggetarian"),
    (DIET_VEGAN,   "Vegan"),
    (DIET_JAIN,    "Jain"),
    (DIET_OTHER,   "Other"),
    (DIET_UNKNOWN, "Unknown"),
]


# ---------------------------------------------------------------------------
# Visit types
# ---------------------------------------------------------------------------
VISIT_DINE_IN  = "DINE_IN"
VISIT_TAKEAWAY = "TAKEAWAY"
VISIT_COUNTER  = "COUNTER"

VISIT_TYPE_CHOICES = [
    (VISIT_DINE_IN,  "Dine In"),
    (VISIT_TAKEAWAY, "Takeaway"),
    (VISIT_COUNTER,  "Counter"),
]


# ---------------------------------------------------------------------------
# Visit statuses
# ---------------------------------------------------------------------------
VISIT_OPEN      = "OPEN"
VISIT_COMPLETED = "COMPLETED"
VISIT_CANCELLED = "CANCELLED"

VISIT_STATUS_CHOICES = [
    (VISIT_OPEN,      "Open"),
    (VISIT_COMPLETED, "Completed"),
    (VISIT_CANCELLED, "Cancelled"),
]


# ---------------------------------------------------------------------------
# Loyalty transaction types
# ---------------------------------------------------------------------------
LOYALTY_EARN       = "EARN"
LOYALTY_REDEEM     = "REDEEM"
LOYALTY_BONUS      = "BONUS"
LOYALTY_ADJUSTMENT = "ADJUSTMENT"
LOYALTY_EXPIRY     = "EXPIRY"
LOYALTY_REVERSAL   = "REVERSAL"

LOYALTY_TRANSACTION_TYPE_CHOICES = [
    (LOYALTY_EARN,       "Earn"),
    (LOYALTY_REDEEM,     "Redeem"),
    (LOYALTY_BONUS,      "Bonus"),
    (LOYALTY_ADJUSTMENT, "Adjustment"),
    (LOYALTY_EXPIRY,     "Expiry"),
    (LOYALTY_REVERSAL,   "Reversal"),
]


# ---------------------------------------------------------------------------
# Loyalty reference types
# ---------------------------------------------------------------------------
LOYALTY_REF_BILL    = "BILL"
LOYALTY_REF_ORDER   = "ORDER"
LOYALTY_REF_MANUAL  = "MANUAL"
LOYALTY_REF_EXPIRY  = "EXPIRY"
LOYALTY_REF_REVERSAL = "REVERSAL"


# ---------------------------------------------------------------------------
# Reward types
# ---------------------------------------------------------------------------
REWARD_DISCOUNT      = "DISCOUNT"
REWARD_FIXED_AMOUNT  = "FIXED_AMOUNT"
REWARD_PERCENTAGE    = "PERCENTAGE"
REWARD_FREE_ITEM     = "FREE_ITEM"
REWARD_OTHER         = "OTHER"

REWARD_TYPE_CHOICES = [
    (REWARD_DISCOUNT,     "Discount"),
    (REWARD_FIXED_AMOUNT, "Fixed Amount"),
    (REWARD_PERCENTAGE,   "Percentage"),
    (REWARD_FREE_ITEM,    "Free Item"),
    (REWARD_OTHER,        "Other"),
]


# ---------------------------------------------------------------------------
# Reward redemption statuses
# ---------------------------------------------------------------------------
REDEMPTION_REQUESTED = "REQUESTED"
REDEMPTION_CONFIRMED = "CONFIRMED"
REDEMPTION_USED      = "USED"
REDEMPTION_CANCELLED = "CANCELLED"
REDEMPTION_EXPIRED   = "EXPIRED"

REDEMPTION_STATUS_CHOICES = [
    (REDEMPTION_REQUESTED, "Requested"),
    (REDEMPTION_CONFIRMED, "Confirmed"),
    (REDEMPTION_USED,      "Used"),
    (REDEMPTION_CANCELLED, "Cancelled"),
    (REDEMPTION_EXPIRED,   "Expired"),
]


# ---------------------------------------------------------------------------
# Feedback statuses
# ---------------------------------------------------------------------------
FEEDBACK_SUBMITTED = "SUBMITTED"
FEEDBACK_REVIEWED  = "REVIEWED"
FEEDBACK_RESOLVED  = "RESOLVED"
FEEDBACK_HIDDEN    = "HIDDEN"

FEEDBACK_STATUS_CHOICES = [
    (FEEDBACK_SUBMITTED, "Submitted"),
    (FEEDBACK_REVIEWED,  "Reviewed"),
    (FEEDBACK_RESOLVED,  "Resolved"),
    (FEEDBACK_HIDDEN,    "Hidden"),
]


# ---------------------------------------------------------------------------
# Feedback moderation statuses
# ---------------------------------------------------------------------------
MODERATION_PENDING  = "PENDING"
MODERATION_APPROVED = "APPROVED"
MODERATION_HIDDEN   = "HIDDEN"
MODERATION_REJECTED = "REJECTED"

MODERATION_STATUS_CHOICES = [
    (MODERATION_PENDING,  "Pending"),
    (MODERATION_APPROVED, "Approved"),
    (MODERATION_HIDDEN,   "Hidden"),
    (MODERATION_REJECTED, "Rejected"),
]


# ---------------------------------------------------------------------------
# Customer segment codes
# ---------------------------------------------------------------------------
SEGMENT_NEW        = "NEW"
SEGMENT_REGULAR    = "REGULAR"
SEGMENT_FREQUENT   = "FREQUENT"
SEGMENT_HIGH_VALUE = "HIGH_VALUE"
SEGMENT_AT_RISK    = "AT_RISK"
SEGMENT_INACTIVE   = "INACTIVE"
SEGMENT_VIP        = "VIP"


# ---------------------------------------------------------------------------
# Consent types
# ---------------------------------------------------------------------------
CONSENT_MARKETING_EMAIL     = "MARKETING_EMAIL"
CONSENT_MARKETING_SMS       = "MARKETING_SMS"
CONSENT_MARKETING_WHATSAPP  = "MARKETING_WHATSAPP"
CONSENT_MARKETING_TELEGRAM  = "MARKETING_TELEGRAM"
CONSENT_LOYALTY             = "LOYALTY"
CONSENT_FEEDBACK_COMM       = "FEEDBACK_COMMUNICATION"

CONSENT_TYPE_CHOICES = [
    (CONSENT_MARKETING_EMAIL,    "Marketing Email"),
    (CONSENT_MARKETING_SMS,      "Marketing SMS"),
    (CONSENT_MARKETING_WHATSAPP, "Marketing WhatsApp"),
    (CONSENT_MARKETING_TELEGRAM, "Marketing Telegram"),
    (CONSENT_LOYALTY,            "Loyalty Programme"),
    (CONSENT_FEEDBACK_COMM,      "Feedback Communication"),
]

CONSENT_GRANTED = "GRANTED"
CONSENT_REVOKED = "REVOKED"

CONSENT_STATUS_CHOICES = [
    (CONSENT_GRANTED, "Granted"),
    (CONSENT_REVOKED, "Revoked"),
]

CONSENT_SOURCE_CUSTOMER = "CUSTOMER"
CONSENT_SOURCE_STAFF    = "STAFF"
CONSENT_SOURCE_ADMIN    = "ADMIN"
CONSENT_SOURCE_IMPORT   = "IMPORT"
CONSENT_SOURCE_SYSTEM   = "SYSTEM"

CONSENT_SOURCE_CHOICES = [
    (CONSENT_SOURCE_CUSTOMER, "Customer"),
    (CONSENT_SOURCE_STAFF,    "Staff"),
    (CONSENT_SOURCE_ADMIN,    "Admin"),
    (CONSENT_SOURCE_IMPORT,   "Import"),
    (CONSENT_SOURCE_SYSTEM,   "System"),
]


# ---------------------------------------------------------------------------
# Customer merge statuses
# ---------------------------------------------------------------------------
MERGE_REQUESTED = "REQUESTED"
MERGE_APPROVED  = "APPROVED"
MERGE_REJECTED  = "REJECTED"
MERGE_CANCELLED = "CANCELLED"

MERGE_STATUS_CHOICES = [
    (MERGE_REQUESTED, "Requested"),
    (MERGE_APPROVED,  "Approved"),
    (MERGE_REJECTED,  "Rejected"),
    (MERGE_CANCELLED, "Cancelled"),
]


# ---------------------------------------------------------------------------
# Audit event types
# ---------------------------------------------------------------------------
AUDIT_CUSTOMER_CREATED           = "CUSTOMER_CREATED"
AUDIT_CUSTOMER_UPDATED           = "CUSTOMER_UPDATED"
AUDIT_CUSTOMER_BLOCKED           = "CUSTOMER_BLOCKED"
AUDIT_CUSTOMER_UNBLOCKED         = "CUSTOMER_UNBLOCKED"
AUDIT_CUSTOMER_LINKED_TO_ORDER   = "CUSTOMER_LINKED_TO_ORDER"
AUDIT_CUSTOMER_TAG_ASSIGNED      = "CUSTOMER_TAG_ASSIGNED"
AUDIT_CUSTOMER_TAG_REMOVED       = "CUSTOMER_TAG_REMOVED"
AUDIT_CUSTOMER_SEGMENT_ASSIGNED  = "CUSTOMER_SEGMENT_ASSIGNED"
AUDIT_CUSTOMER_SEGMENT_REMOVED   = "CUSTOMER_SEGMENT_REMOVED"
AUDIT_LOYALTY_ACCOUNT_CREATED    = "LOYALTY_ACCOUNT_CREATED"
AUDIT_LOYALTY_POINTS_EARNED      = "LOYALTY_POINTS_EARNED"
AUDIT_LOYALTY_POINTS_REDEEMED    = "LOYALTY_POINTS_REDEEMED"
AUDIT_LOYALTY_POINTS_ADJUSTED    = "LOYALTY_POINTS_ADJUSTED"
AUDIT_LOYALTY_POINTS_REVERSED    = "LOYALTY_POINTS_REVERSED"
AUDIT_LOYALTY_POINTS_EXPIRED     = "LOYALTY_POINTS_EXPIRED"
AUDIT_REWARD_CREATED             = "REWARD_CREATED"
AUDIT_REWARD_UPDATED             = "REWARD_UPDATED"
AUDIT_REWARD_REDEEMED            = "REWARD_REDEEMED"
AUDIT_REWARD_CANCELLED           = "REWARD_CANCELLED"
AUDIT_FEEDBACK_CREATED           = "FEEDBACK_CREATED"
AUDIT_FEEDBACK_UPDATED           = "FEEDBACK_UPDATED"
AUDIT_FEEDBACK_MODERATED         = "FEEDBACK_MODERATED"
AUDIT_FEEDBACK_RESOLVED          = "FEEDBACK_RESOLVED"
AUDIT_CONSENT_GRANTED            = "CUSTOMER_CONSENT_GRANTED"
AUDIT_CONSENT_REVOKED            = "CUSTOMER_CONSENT_REVOKED"
AUDIT_MERGE_REQUESTED            = "CUSTOMER_MERGE_REQUESTED"
AUDIT_MERGE_APPROVED             = "CUSTOMER_MERGE_APPROVED"
AUDIT_MERGE_REJECTED             = "CUSTOMER_MERGE_REJECTED"

AUDIT_EVENT_CHOICES = [
    (AUDIT_CUSTOMER_CREATED,          "Customer Created"),
    (AUDIT_CUSTOMER_UPDATED,          "Customer Updated"),
    (AUDIT_CUSTOMER_BLOCKED,          "Customer Blocked"),
    (AUDIT_CUSTOMER_UNBLOCKED,        "Customer Unblocked"),
    (AUDIT_CUSTOMER_LINKED_TO_ORDER,  "Customer Linked to Order"),
    (AUDIT_CUSTOMER_TAG_ASSIGNED,     "Customer Tag Assigned"),
    (AUDIT_CUSTOMER_TAG_REMOVED,      "Customer Tag Removed"),
    (AUDIT_CUSTOMER_SEGMENT_ASSIGNED, "Customer Segment Assigned"),
    (AUDIT_CUSTOMER_SEGMENT_REMOVED,  "Customer Segment Removed"),
    (AUDIT_LOYALTY_ACCOUNT_CREATED,   "Loyalty Account Created"),
    (AUDIT_LOYALTY_POINTS_EARNED,     "Loyalty Points Earned"),
    (AUDIT_LOYALTY_POINTS_REDEEMED,   "Loyalty Points Redeemed"),
    (AUDIT_LOYALTY_POINTS_ADJUSTED,   "Loyalty Points Adjusted"),
    (AUDIT_LOYALTY_POINTS_REVERSED,   "Loyalty Points Reversed"),
    (AUDIT_LOYALTY_POINTS_EXPIRED,    "Loyalty Points Expired"),
    (AUDIT_REWARD_CREATED,            "Reward Created"),
    (AUDIT_REWARD_UPDATED,            "Reward Updated"),
    (AUDIT_REWARD_REDEEMED,           "Reward Redeemed"),
    (AUDIT_REWARD_CANCELLED,          "Reward Cancelled"),
    (AUDIT_FEEDBACK_CREATED,          "Feedback Created"),
    (AUDIT_FEEDBACK_UPDATED,          "Feedback Updated"),
    (AUDIT_FEEDBACK_MODERATED,        "Feedback Moderated"),
    (AUDIT_FEEDBACK_RESOLVED,         "Feedback Resolved"),
    (AUDIT_CONSENT_GRANTED,           "Consent Granted"),
    (AUDIT_CONSENT_REVOKED,           "Consent Revoked"),
    (AUDIT_MERGE_REQUESTED,           "Merge Requested"),
    (AUDIT_MERGE_APPROVED,            "Merge Approved"),
    (AUDIT_MERGE_REJECTED,            "Merge Rejected"),
]


# ---------------------------------------------------------------------------
# Notification types (CRM-specific — added to notifications system)
# ---------------------------------------------------------------------------
NOTIF_CRM_LOYALTY_EARNED       = "CRM_LOYALTY_POINTS_EARNED"
NOTIF_CRM_REWARD_AVAILABLE     = "CRM_REWARD_AVAILABLE"
NOTIF_CRM_REWARD_EXPIRING      = "CRM_REWARD_EXPIRING"
NOTIF_CRM_FEEDBACK_SUBMITTED   = "CRM_FEEDBACK_SUBMITTED"
NOTIF_CRM_FEEDBACK_RESPONSE    = "CRM_FEEDBACK_RESPONSE"

SOURCE_CUSTOMER         = "CUSTOMER"
SOURCE_LOYALTY_ACCOUNT  = "LOYALTY_ACCOUNT"
SOURCE_LOYALTY_TXN      = "LOYALTY_TRANSACTION"
SOURCE_REWARD           = "REWARD"
SOURCE_REDEMPTION       = "REWARD_REDEMPTION"
SOURCE_FEEDBACK         = "FEEDBACK"


# ---------------------------------------------------------------------------
# Customer number prefix
# ---------------------------------------------------------------------------
CUSTOMER_NUMBER_PREFIX = "CUS"


# ---------------------------------------------------------------------------
# Analytics definitions (configurable defaults)
# ---------------------------------------------------------------------------
ANALYTICS_NEW_CUSTOMER_DAYS     = 30   # First order within this many days = "new"
ANALYTICS_INACTIVE_CUSTOMER_DAYS = 90  # No order for this many days = "inactive"
ANALYTICS_RETURNING_MIN_ORDERS  = 2    # At least this many orders = "returning"
ANALYTICS_HIGH_VALUE_THRESHOLD  = None # Set per-restaurant if needed

# Default points expiry check batch size
LOYALTY_EXPIRY_BATCH_SIZE = 500
