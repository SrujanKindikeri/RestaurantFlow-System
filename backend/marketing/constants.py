# =============================================================================
# RestaurantFlow — Marketing Constants
# Phase 18: Marketing, Promotions & Campaign Management
#
# All magic strings live here. Never hard-code in models, services, or views.
# =============================================================================

# ---------------------------------------------------------------------------
# Permission codes
# ---------------------------------------------------------------------------

PERM_MARKETING_DASHBOARD_VIEW   = "marketing.dashboard.view"
PERM_CAMPAIGN_VIEW              = "marketing.campaign.view"
PERM_CAMPAIGN_CREATE            = "marketing.campaign.create"
PERM_CAMPAIGN_UPDATE            = "marketing.campaign.update"
PERM_CAMPAIGN_SUBMIT            = "marketing.campaign.submit"
PERM_CAMPAIGN_APPROVE           = "marketing.campaign.approve"
PERM_CAMPAIGN_REJECT            = "marketing.campaign.reject"
PERM_CAMPAIGN_SCHEDULE          = "marketing.campaign.schedule"
PERM_CAMPAIGN_PAUSE             = "marketing.campaign.pause"
PERM_CAMPAIGN_RESUME            = "marketing.campaign.resume"
PERM_CAMPAIGN_CANCEL            = "marketing.campaign.cancel"
PERM_AUDIENCE_VIEW              = "marketing.audience.view"
PERM_AUDIENCE_MANAGE            = "marketing.audience.manage"
PERM_PROMOTION_VIEW             = "marketing.promotion.view"
PERM_PROMOTION_CREATE           = "marketing.promotion.create"
PERM_PROMOTION_UPDATE           = "marketing.promotion.update"
PERM_PROMOTION_ACTIVATE         = "marketing.promotion.activate"
PERM_PROMOTION_DEACTIVATE       = "marketing.promotion.deactivate"
PERM_PROMOTION_APPLY            = "marketing.promotion.apply"
PERM_PROMOTION_APPROVE          = "marketing.promotion.approve"
PERM_ANALYTICS_VIEW             = "marketing.analytics.view"
PERM_MARKETING_EXPORT           = "marketing.export"
PERM_SETTINGS_VIEW              = "marketing.settings.view"
PERM_SETTINGS_MANAGE            = "marketing.settings.manage"

ALL_MARKETING_PERMISSIONS = [
    (PERM_MARKETING_DASHBOARD_VIEW, "View Marketing Dashboard",          "marketing", "dashboard.view"),
    (PERM_CAMPAIGN_VIEW,            "View Campaigns",                     "marketing", "campaign.view"),
    (PERM_CAMPAIGN_CREATE,          "Create Campaigns",                   "marketing", "campaign.create"),
    (PERM_CAMPAIGN_UPDATE,          "Update Campaigns",                   "marketing", "campaign.update"),
    (PERM_CAMPAIGN_SUBMIT,          "Submit Campaigns for Approval",      "marketing", "campaign.submit"),
    (PERM_CAMPAIGN_APPROVE,         "Approve Campaigns",                  "marketing", "campaign.approve"),
    (PERM_CAMPAIGN_REJECT,          "Reject Campaigns",                   "marketing", "campaign.reject"),
    (PERM_CAMPAIGN_SCHEDULE,        "Schedule Campaigns",                 "marketing", "campaign.schedule"),
    (PERM_CAMPAIGN_PAUSE,           "Pause Running Campaigns",            "marketing", "campaign.pause"),
    (PERM_CAMPAIGN_RESUME,          "Resume Paused Campaigns",            "marketing", "campaign.resume"),
    (PERM_CAMPAIGN_CANCEL,          "Cancel Campaigns",                   "marketing", "campaign.cancel"),
    (PERM_AUDIENCE_VIEW,            "View Campaign Audiences",            "marketing", "audience.view"),
    (PERM_AUDIENCE_MANAGE,          "Manage Campaign Audiences",          "marketing", "audience.manage"),
    (PERM_PROMOTION_VIEW,           "View Promotions",                    "marketing", "promotion.view"),
    (PERM_PROMOTION_CREATE,         "Create Promotions",                  "marketing", "promotion.create"),
    (PERM_PROMOTION_UPDATE,         "Update Promotions",                  "marketing", "promotion.update"),
    (PERM_PROMOTION_ACTIVATE,       "Activate Promotions",                "marketing", "promotion.activate"),
    (PERM_PROMOTION_DEACTIVATE,     "Deactivate Promotions",              "marketing", "promotion.deactivate"),
    (PERM_PROMOTION_APPLY,          "Apply Promotions to Bills",          "marketing", "promotion.apply"),
    (PERM_PROMOTION_APPROVE,        "Approve High-Impact Promotions",     "marketing", "promotion.approve"),
    (PERM_ANALYTICS_VIEW,           "View Marketing Analytics",           "marketing", "analytics.view"),
    (PERM_MARKETING_EXPORT,         "Export Marketing Data",              "marketing", "export"),
    (PERM_SETTINGS_VIEW,            "View Marketing Settings",            "marketing", "settings.view"),
    (PERM_SETTINGS_MANAGE,          "Manage Marketing Settings",          "marketing", "settings.manage"),
]

# ---------------------------------------------------------------------------
# Campaign types
# ---------------------------------------------------------------------------
CAMPAIGN_PROMOTION       = "PROMOTION"
CAMPAIGN_LOYALTY         = "LOYALTY"
CAMPAIGN_REACTIVATION    = "REACTIVATION"
CAMPAIGN_NEW_CUSTOMER    = "NEW_CUSTOMER"
CAMPAIGN_REPEAT_CUSTOMER = "REPEAT_CUSTOMER"
CAMPAIGN_BIRTHDAY        = "BIRTHDAY"
CAMPAIGN_SEASONAL        = "SEASONAL"
CAMPAIGN_EVENT           = "EVENT"
CAMPAIGN_FEEDBACK        = "FEEDBACK"
CAMPAIGN_ANNOUNCEMENT    = "ANNOUNCEMENT"
CAMPAIGN_OTHER           = "OTHER"

CAMPAIGN_TYPE_CHOICES = [
    (CAMPAIGN_PROMOTION,       "Promotion"),
    (CAMPAIGN_LOYALTY,         "Loyalty"),
    (CAMPAIGN_REACTIVATION,    "Reactivation"),
    (CAMPAIGN_NEW_CUSTOMER,    "New Customer"),
    (CAMPAIGN_REPEAT_CUSTOMER, "Repeat Customer"),
    (CAMPAIGN_BIRTHDAY,        "Birthday"),
    (CAMPAIGN_SEASONAL,        "Seasonal"),
    (CAMPAIGN_EVENT,           "Event"),
    (CAMPAIGN_FEEDBACK,        "Feedback"),
    (CAMPAIGN_ANNOUNCEMENT,    "Announcement"),
    (CAMPAIGN_OTHER,           "Other"),
]

# ---------------------------------------------------------------------------
# Campaign statuses
# ---------------------------------------------------------------------------
CAMPAIGN_DRAFT            = "DRAFT"
CAMPAIGN_PENDING_APPROVAL = "PENDING_APPROVAL"
CAMPAIGN_APPROVED         = "APPROVED"
CAMPAIGN_SCHEDULED        = "SCHEDULED"
CAMPAIGN_RUNNING          = "RUNNING"
CAMPAIGN_PAUSED           = "PAUSED"
CAMPAIGN_COMPLETED        = "COMPLETED"
CAMPAIGN_CANCELLED        = "CANCELLED"
CAMPAIGN_FAILED           = "FAILED"

CAMPAIGN_STATUS_CHOICES = [
    (CAMPAIGN_DRAFT,            "Draft"),
    (CAMPAIGN_PENDING_APPROVAL, "Pending Approval"),
    (CAMPAIGN_APPROVED,         "Approved"),
    (CAMPAIGN_SCHEDULED,        "Scheduled"),
    (CAMPAIGN_RUNNING,          "Running"),
    (CAMPAIGN_PAUSED,           "Paused"),
    (CAMPAIGN_COMPLETED,        "Completed"),
    (CAMPAIGN_CANCELLED,        "Cancelled"),
    (CAMPAIGN_FAILED,           "Failed"),
]

# Terminal campaign statuses — no further transitions allowed
CAMPAIGN_TERMINAL_STATUSES = {CAMPAIGN_COMPLETED, CAMPAIGN_CANCELLED, CAMPAIGN_FAILED}

# Valid status transitions: {from_status: set of allowed to_statuses}
CAMPAIGN_STATUS_TRANSITIONS = {
    CAMPAIGN_DRAFT:            {CAMPAIGN_PENDING_APPROVAL, CAMPAIGN_CANCELLED},
    CAMPAIGN_PENDING_APPROVAL: {CAMPAIGN_APPROVED, CAMPAIGN_CANCELLED},
    CAMPAIGN_APPROVED:         {CAMPAIGN_SCHEDULED, CAMPAIGN_RUNNING, CAMPAIGN_CANCELLED},
    CAMPAIGN_SCHEDULED:        {CAMPAIGN_RUNNING, CAMPAIGN_PAUSED, CAMPAIGN_CANCELLED},
    CAMPAIGN_RUNNING:          {CAMPAIGN_PAUSED, CAMPAIGN_COMPLETED, CAMPAIGN_CANCELLED, CAMPAIGN_FAILED},
    CAMPAIGN_PAUSED:           {CAMPAIGN_SCHEDULED, CAMPAIGN_RUNNING, CAMPAIGN_CANCELLED},
    CAMPAIGN_COMPLETED:        set(),
    CAMPAIGN_CANCELLED:        set(),
    CAMPAIGN_FAILED:           set(),
}

# ---------------------------------------------------------------------------
# Approval statuses
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
# Audience types
# ---------------------------------------------------------------------------
AUDIENCE_ALL_CUSTOMERS      = "ALL_CUSTOMERS"
AUDIENCE_NEW_CUSTOMERS      = "NEW_CUSTOMERS"
AUDIENCE_RETURNING          = "RETURNING_CUSTOMERS"
AUDIENCE_VIP                = "VIP"
AUDIENCE_HIGH_VALUE         = "HIGH_VALUE"
AUDIENCE_FREQUENT           = "FREQUENT"
AUDIENCE_INACTIVE           = "INACTIVE"
AUDIENCE_AT_RISK            = "AT_RISK"
AUDIENCE_CUSTOM_SEGMENT     = "CUSTOM_SEGMENT"
AUDIENCE_CUSTOM_TAG         = "CUSTOM_TAG"
AUDIENCE_CUSTOM_FILTER      = "CUSTOM_FILTER"

AUDIENCE_TYPE_CHOICES = [
    (AUDIENCE_ALL_CUSTOMERS,  "All Customers"),
    (AUDIENCE_NEW_CUSTOMERS,  "New Customers"),
    (AUDIENCE_RETURNING,      "Returning Customers"),
    (AUDIENCE_VIP,            "VIP"),
    (AUDIENCE_HIGH_VALUE,     "High Value"),
    (AUDIENCE_FREQUENT,       "Frequent"),
    (AUDIENCE_INACTIVE,       "Inactive"),
    (AUDIENCE_AT_RISK,        "At Risk"),
    (AUDIENCE_CUSTOM_SEGMENT, "Custom Segment"),
    (AUDIENCE_CUSTOM_TAG,     "Custom Tag"),
    (AUDIENCE_CUSTOM_FILTER,  "Custom Filter"),
]

# ---------------------------------------------------------------------------
# Audience member statuses
# ---------------------------------------------------------------------------
MEMBER_ELIGIBLE     = "ELIGIBLE"
MEMBER_EXCLUDED     = "EXCLUDED"
MEMBER_CONTACTED    = "CONTACTED"
MEMBER_CONVERTED    = "CONVERTED"
MEMBER_UNSUBSCRIBED = "UNSUBSCRIBED"

MEMBER_STATUS_CHOICES = [
    (MEMBER_ELIGIBLE,     "Eligible"),
    (MEMBER_EXCLUDED,     "Excluded"),
    (MEMBER_CONTACTED,    "Contacted"),
    (MEMBER_CONVERTED,    "Converted"),
    (MEMBER_UNSUBSCRIBED, "Unsubscribed"),
]

# ---------------------------------------------------------------------------
# Promotion types
# ---------------------------------------------------------------------------
PROMO_PERCENTAGE_DISCOUNT = "PERCENTAGE_DISCOUNT"
PROMO_FIXED_DISCOUNT      = "FIXED_DISCOUNT"
PROMO_FREE_ITEM           = "FREE_ITEM"
PROMO_BUY_X_GET_Y         = "BUY_X_GET_Y"
PROMO_LOYALTY_BONUS       = "LOYALTY_BONUS"
PROMO_OTHER               = "OTHER"

PROMOTION_TYPE_CHOICES = [
    (PROMO_PERCENTAGE_DISCOUNT, "Percentage Discount"),
    (PROMO_FIXED_DISCOUNT,      "Fixed Discount"),
    (PROMO_FREE_ITEM,           "Free Item"),
    (PROMO_BUY_X_GET_Y,        "Buy X Get Y"),
    (PROMO_LOYALTY_BONUS,      "Loyalty Bonus"),
    (PROMO_OTHER,              "Other"),
]

# Promotion types that involve billing discounts
DISCOUNT_PROMOTION_TYPES = {PROMO_PERCENTAGE_DISCOUNT, PROMO_FIXED_DISCOUNT}

# ---------------------------------------------------------------------------
# Discount types (mirrors billing)
# ---------------------------------------------------------------------------
DISCOUNT_PERCENTAGE   = "PERCENTAGE"
DISCOUNT_FIXED_AMOUNT = "FIXED_AMOUNT"

DISCOUNT_TYPE_CHOICES = [
    (DISCOUNT_PERCENTAGE,   "Percentage"),
    (DISCOUNT_FIXED_AMOUNT, "Fixed Amount"),
]

# ---------------------------------------------------------------------------
# Promotion rule types
# ---------------------------------------------------------------------------
RULE_MIN_ORDER_VALUE   = "MIN_ORDER_VALUE"
RULE_MIN_QUANTITY      = "MIN_QUANTITY"
RULE_CUSTOMER_SEGMENT  = "CUSTOMER_SEGMENT"
RULE_CUSTOMER_TAG      = "CUSTOMER_TAG"
RULE_FIRST_ORDER       = "FIRST_ORDER"
RULE_REPEAT_ORDER      = "REPEAT_ORDER"
RULE_SPECIFIC_ITEM     = "SPECIFIC_MENU_ITEM"
RULE_MENU_CATEGORY     = "MENU_CATEGORY"
RULE_BRANCH            = "BRANCH"
RULE_ORDER_TYPE        = "ORDER_TYPE"
RULE_DAY_OF_WEEK       = "DAY_OF_WEEK"
RULE_TIME_WINDOW       = "TIME_WINDOW"
RULE_LOYALTY_POINTS    = "LOYALTY_POINTS"
RULE_USAGE_LIMIT       = "USAGE_LIMIT"

RULE_TYPE_CHOICES = [
    (RULE_MIN_ORDER_VALUE,  "Minimum Order Value"),
    (RULE_MIN_QUANTITY,     "Minimum Quantity"),
    (RULE_CUSTOMER_SEGMENT, "Customer Segment"),
    (RULE_CUSTOMER_TAG,     "Customer Tag"),
    (RULE_FIRST_ORDER,      "First Order"),
    (RULE_REPEAT_ORDER,     "Repeat Order"),
    (RULE_SPECIFIC_ITEM,    "Specific Menu Item"),
    (RULE_MENU_CATEGORY,    "Menu Category"),
    (RULE_BRANCH,           "Branch"),
    (RULE_ORDER_TYPE,       "Order Type"),
    (RULE_DAY_OF_WEEK,      "Day of Week"),
    (RULE_TIME_WINDOW,      "Time Window"),
    (RULE_LOYALTY_POINTS,   "Loyalty Points"),
    (RULE_USAGE_LIMIT,      "Usage Limit"),
]

# ---------------------------------------------------------------------------
# Promotion usage statuses
# ---------------------------------------------------------------------------
USAGE_RESERVED  = "RESERVED"
USAGE_APPLIED   = "APPLIED"
USAGE_REVERSED  = "REVERSED"
USAGE_CANCELLED = "CANCELLED"

USAGE_STATUS_CHOICES = [
    (USAGE_RESERVED,  "Reserved"),
    (USAGE_APPLIED,   "Applied"),
    (USAGE_REVERSED,  "Reversed"),
    (USAGE_CANCELLED, "Cancelled"),
]

# ---------------------------------------------------------------------------
# Campaign channel types
# ---------------------------------------------------------------------------
CHANNEL_IN_APP   = "IN_APP"
CHANNEL_EMAIL    = "EMAIL"
CHANNEL_SMS      = "SMS"
CHANNEL_WHATSAPP = "WHATSAPP"
CHANNEL_TELEGRAM = "TELEGRAM"

CHANNEL_CHOICES = [
    (CHANNEL_IN_APP,   "In-App"),
    (CHANNEL_EMAIL,    "Email"),
    (CHANNEL_SMS,      "SMS"),
    (CHANNEL_WHATSAPP, "WhatsApp"),
    (CHANNEL_TELEGRAM, "Telegram"),
]

# Mapping channel → consent type (from crm.constants)
CHANNEL_CONSENT_MAP = {
    CHANNEL_EMAIL:    "MARKETING_EMAIL",
    CHANNEL_SMS:      "MARKETING_SMS",
    CHANNEL_WHATSAPP: "MARKETING_WHATSAPP",
    CHANNEL_TELEGRAM: "MARKETING_TELEGRAM",
}

# ---------------------------------------------------------------------------
# Campaign delivery statuses
# ---------------------------------------------------------------------------
DELIVERY_PENDING     = "PENDING"
DELIVERY_QUEUED      = "QUEUED"
DELIVERY_SENT        = "SENT"
DELIVERY_DELIVERED   = "DELIVERED"
DELIVERY_FAILED      = "FAILED"
DELIVERY_SKIPPED     = "SKIPPED"
DELIVERY_UNSUBSCRIBED = "UNSUBSCRIBED"

DELIVERY_STATUS_CHOICES = [
    (DELIVERY_PENDING,      "Pending"),
    (DELIVERY_QUEUED,       "Queued"),
    (DELIVERY_SENT,         "Sent"),
    (DELIVERY_DELIVERED,    "Delivered"),
    (DELIVERY_FAILED,       "Failed"),
    (DELIVERY_SKIPPED,      "Skipped"),
    (DELIVERY_UNSUBSCRIBED, "Unsubscribed"),
]

# ---------------------------------------------------------------------------
# Conversion types
# ---------------------------------------------------------------------------
CONVERSION_PROMOTION_REDEEMED = "PROMOTION_REDEEMED"
CONVERSION_ORDER_PLACED       = "ORDER_PLACED"
CONVERSION_REPEAT_ORDER       = "REPEAT_ORDER"
CONVERSION_LOYALTY_ACTION     = "LOYALTY_ACTION"
CONVERSION_FEEDBACK_ACTION    = "FEEDBACK_ACTION"

CONVERSION_TYPE_CHOICES = [
    (CONVERSION_PROMOTION_REDEEMED, "Promotion Redeemed"),
    (CONVERSION_ORDER_PLACED,       "Order Placed"),
    (CONVERSION_REPEAT_ORDER,       "Repeat Order"),
    (CONVERSION_LOYALTY_ACTION,     "Loyalty Action"),
    (CONVERSION_FEEDBACK_ACTION,    "Feedback Action"),
]

# ---------------------------------------------------------------------------
# Campaign event types
# ---------------------------------------------------------------------------
EVENT_AUDIENCE_ADDED        = "AUDIENCE_ADDED"
EVENT_AUDIENCE_REMOVED      = "AUDIENCE_REMOVED"
EVENT_NOTIFICATION_SENT     = "NOTIFICATION_SENT"
EVENT_NOTIFICATION_DELIVERED = "NOTIFICATION_DELIVERED"
EVENT_PROMOTION_VIEWED      = "PROMOTION_VIEWED"
EVENT_PROMOTION_USED        = "PROMOTION_USED"
EVENT_ORDER_CREATED         = "ORDER_CREATED"
EVENT_ORDER_COMPLETED       = "ORDER_COMPLETED"
EVENT_REWARD_REDEEMED       = "REWARD_REDEEMED"
EVENT_UNSUBSCRIBED          = "UNSUBSCRIBED"

EVENT_TYPE_CHOICES = [
    (EVENT_AUDIENCE_ADDED,         "Audience Added"),
    (EVENT_AUDIENCE_REMOVED,       "Audience Removed"),
    (EVENT_NOTIFICATION_SENT,      "Notification Sent"),
    (EVENT_NOTIFICATION_DELIVERED, "Notification Delivered"),
    (EVENT_PROMOTION_VIEWED,       "Promotion Viewed"),
    (EVENT_PROMOTION_USED,         "Promotion Used"),
    (EVENT_ORDER_CREATED,          "Order Created"),
    (EVENT_ORDER_COMPLETED,        "Order Completed"),
    (EVENT_REWARD_REDEEMED,        "Reward Redeemed"),
    (EVENT_UNSUBSCRIBED,           "Unsubscribed"),
]

# ---------------------------------------------------------------------------
# Audit event codes
# ---------------------------------------------------------------------------
AUDIT_CAMPAIGN_CREATED        = "CAMPAIGN_CREATED"
AUDIT_CAMPAIGN_UPDATED        = "CAMPAIGN_UPDATED"
AUDIT_CAMPAIGN_SUBMITTED      = "CAMPAIGN_SUBMITTED"
AUDIT_CAMPAIGN_APPROVED       = "CAMPAIGN_APPROVED"
AUDIT_CAMPAIGN_REJECTED       = "CAMPAIGN_REJECTED"
AUDIT_CAMPAIGN_SCHEDULED      = "CAMPAIGN_SCHEDULED"
AUDIT_CAMPAIGN_STARTED        = "CAMPAIGN_STARTED"
AUDIT_CAMPAIGN_PAUSED         = "CAMPAIGN_PAUSED"
AUDIT_CAMPAIGN_RESUMED        = "CAMPAIGN_RESUMED"
AUDIT_CAMPAIGN_COMPLETED      = "CAMPAIGN_COMPLETED"
AUDIT_CAMPAIGN_CANCELLED      = "CAMPAIGN_CANCELLED"
AUDIT_PROMOTION_CREATED       = "PROMOTION_CREATED"
AUDIT_PROMOTION_UPDATED       = "PROMOTION_UPDATED"
AUDIT_PROMOTION_ACTIVATED     = "PROMOTION_ACTIVATED"
AUDIT_PROMOTION_DEACTIVATED   = "PROMOTION_DEACTIVATED"
AUDIT_PROMOTION_USED          = "PROMOTION_USED"
AUDIT_PROMOTION_REVERSED      = "PROMOTION_REVERSED"
AUDIT_AUDIENCE_CREATED        = "CAMPAIGN_AUDIENCE_CREATED"
AUDIT_AUDIENCE_UPDATED        = "CAMPAIGN_AUDIENCE_UPDATED"
AUDIT_MESSAGE_CREATED         = "CAMPAIGN_MESSAGE_CREATED"
AUDIT_MESSAGE_UPDATED         = "CAMPAIGN_MESSAGE_UPDATED"
AUDIT_CONSENT_BLOCKED         = "MARKETING_CONSENT_BLOCKED"
AUDIT_DELIVERY_FAILED         = "MARKETING_DELIVERY_FAILED"

AUDIT_EVENT_CHOICES = [
    (AUDIT_CAMPAIGN_CREATED,      "Campaign Created"),
    (AUDIT_CAMPAIGN_UPDATED,      "Campaign Updated"),
    (AUDIT_CAMPAIGN_SUBMITTED,    "Campaign Submitted"),
    (AUDIT_CAMPAIGN_APPROVED,     "Campaign Approved"),
    (AUDIT_CAMPAIGN_REJECTED,     "Campaign Rejected"),
    (AUDIT_CAMPAIGN_SCHEDULED,    "Campaign Scheduled"),
    (AUDIT_CAMPAIGN_STARTED,      "Campaign Started"),
    (AUDIT_CAMPAIGN_PAUSED,       "Campaign Paused"),
    (AUDIT_CAMPAIGN_RESUMED,      "Campaign Resumed"),
    (AUDIT_CAMPAIGN_COMPLETED,    "Campaign Completed"),
    (AUDIT_CAMPAIGN_CANCELLED,    "Campaign Cancelled"),
    (AUDIT_PROMOTION_CREATED,     "Promotion Created"),
    (AUDIT_PROMOTION_UPDATED,     "Promotion Updated"),
    (AUDIT_PROMOTION_ACTIVATED,   "Promotion Activated"),
    (AUDIT_PROMOTION_DEACTIVATED, "Promotion Deactivated"),
    (AUDIT_PROMOTION_USED,        "Promotion Used"),
    (AUDIT_PROMOTION_REVERSED,    "Promotion Reversed"),
    (AUDIT_AUDIENCE_CREATED,      "Campaign Audience Created"),
    (AUDIT_AUDIENCE_UPDATED,      "Campaign Audience Updated"),
    (AUDIT_MESSAGE_CREATED,       "Campaign Message Created"),
    (AUDIT_MESSAGE_UPDATED,       "Campaign Message Updated"),
    (AUDIT_CONSENT_BLOCKED,       "Marketing Consent Blocked"),
    (AUDIT_DELIVERY_FAILED,       "Marketing Delivery Failed"),
]

# ---------------------------------------------------------------------------
# Source types for notification integration
# ---------------------------------------------------------------------------
SOURCE_MARKETING_CAMPAIGN = "MARKETING_CAMPAIGN"
SOURCE_MARKETING_PROMOTION = "MARKETING_PROMOTION"

# Notification type codes (added to notifications.constants domain)
NOTIF_CAMPAIGN_DELIVERY = "MARKETING_CAMPAIGN_DELIVERY"
NOTIF_PROMOTION_AVAILABLE = "MARKETING_PROMOTION_AVAILABLE"
NOTIF_LOYALTY_BONUS = "MARKETING_LOYALTY_BONUS"

# ---------------------------------------------------------------------------
# Central Control alert types
# ---------------------------------------------------------------------------
ALERT_CAMPAIGN_FAILURE          = "MARKETING_CAMPAIGN_FAILURE"
ALERT_PROMOTION_ABUSE           = "PROMOTION_ABUSE"
ALERT_HIGH_CAMPAIGN_FAILURE     = "HIGH_CAMPAIGN_FAILURE_RATE"
ALERT_UNUSUAL_REDEMPTION        = "UNUSUAL_PROMOTION_REDEMPTION"

# ---------------------------------------------------------------------------
# Real-time WebSocket event names
# ---------------------------------------------------------------------------
WS_CAMPAIGN_CREATED      = "marketing.campaign.created"
WS_CAMPAIGN_UPDATED      = "marketing.campaign.updated"
WS_CAMPAIGN_STARTED      = "marketing.campaign.started"
WS_CAMPAIGN_PAUSED       = "marketing.campaign.paused"
WS_CAMPAIGN_COMPLETED    = "marketing.campaign.completed"
WS_PROMOTION_CREATED     = "marketing.promotion.created"
WS_PROMOTION_UPDATED     = "marketing.promotion.updated"
WS_PROMOTION_USED        = "marketing.promotion.used"
WS_DELIVERY_FAILED       = "marketing.campaign.delivery.failed"
WS_CONVERSION_CREATED    = "marketing.campaign.conversion.created"

# ---------------------------------------------------------------------------
# Cache key templates
# ---------------------------------------------------------------------------
CACHE_KEY_PROMO_VALIDATE = "marketing:promo:validate:{promo_id}:{customer_id}"
CACHE_KEY_CONTACT_POLICY = "marketing:contact_policy:{restaurant_id}:{customer_id}:{channel}:{date}"
CACHE_KEY_FREQUENCY_DAY  = "marketing:freq:day:{restaurant_id}:{customer_id}:{channel}:{date}"
CACHE_KEY_FREQUENCY_WEEK = "marketing:freq:week:{restaurant_id}:{customer_id}:{channel}:{week}"

# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------
PROMO_CODE_MAX_LENGTH = 50
CAMPAIGN_CODE_MAX_LENGTH = 50
MAX_PROMO_CODE_LOOKUP_ATTEMPTS = 5  # per IP per minute (rate limiting)
