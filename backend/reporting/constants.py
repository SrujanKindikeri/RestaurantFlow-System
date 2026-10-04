# =============================================================================
# RestaurantFlow — Reporting Constants
# Phase 14
#
# All reporting permission codes, report type codes, and shared constants.
# Import from here — never hard-code these values in views or services.
# =============================================================================

from decimal import Decimal

# ---------------------------------------------------------------------------
# Reporting permission codes
# ---------------------------------------------------------------------------

PERM_DASHBOARD_VIEW        = "reporting.dashboard.view"
PERM_SALES_VIEW            = "reporting.sales.view"
PERM_ORDERS_VIEW           = "reporting.orders.view"
PERM_MENU_VIEW             = "reporting.menu.view"
PERM_BRANCH_VIEW           = "reporting.branch.view"
PERM_COUNTER_VIEW          = "reporting.counter.view"
PERM_PAYMENT_VIEW          = "reporting.payment.view"
PERM_REFUND_VIEW           = "reporting.refund.view"
PERM_DISCOUNT_VIEW         = "reporting.discount.view"
PERM_KITCHEN_VIEW          = "reporting.kitchen.view"
PERM_STAFF_VIEW            = "reporting.staff.view"
PERM_INVENTORY_VIEW        = "reporting.inventory.view"
PERM_PURCHASE_VIEW         = "reporting.purchase.view"
PERM_SUPPLIER_VIEW         = "reporting.supplier.view"
PERM_EXPENSE_VIEW          = "reporting.expense.view"
PERM_PAYABLE_VIEW          = "reporting.payable.view"
PERM_PROFITABILITY_VIEW    = "reporting.profitability.view"
PERM_FINANCIAL_VIEW        = "reporting.financial.view"

# Export permissions
PERM_EXPORT_CSV            = "reporting.export.csv"
PERM_EXPORT_EXCEL          = "reporting.export.excel"
PERM_EXPORT_PDF            = "reporting.export.pdf"

# ---------------------------------------------------------------------------
# Report type codes (used in audit log and cache keys)
# ---------------------------------------------------------------------------

REPORT_DASHBOARD           = "dashboard"
REPORT_SALES_SUMMARY       = "sales_summary"
REPORT_SALES_TREND         = "sales_trend"
REPORT_SALES_HOURLY        = "sales_hourly"
REPORT_ORDERS_SUMMARY      = "orders_summary"
REPORT_ORDERS_BY_TYPE      = "orders_by_type"
REPORT_MENU_ITEMS          = "menu_items"
REPORT_MENU_TOP_SELLING    = "menu_top_selling"
REPORT_MENU_CATEGORIES     = "menu_categories"
REPORT_MENU_PROFITABILITY  = "menu_profitability"
REPORT_BRANCH_PERFORMANCE  = "branch_performance"
REPORT_COUNTER_PERFORMANCE = "counter_performance"
REPORT_PAYMENT_SUMMARY     = "payment_summary"
REPORT_PAYMENT_METHODS     = "payment_methods"
REPORT_REFUNDS             = "refunds"
REPORT_DISCOUNTS           = "discounts"
REPORT_KITCHEN_PERFORMANCE = "kitchen_performance"
REPORT_KITCHEN_ITEMS       = "kitchen_items"
REPORT_STAFF_WAITERS       = "staff_waiters"
REPORT_STAFF_CASHIERS      = "staff_cashiers"
REPORT_INVENTORY_SUMMARY   = "inventory_summary"
REPORT_INVENTORY_CONSUMPTION = "inventory_consumption"
REPORT_INVENTORY_WASTAGE   = "inventory_wastage"
REPORT_PURCHASES           = "purchases"
REPORT_SUPPLIERS           = "suppliers"
REPORT_EXPENSES            = "expenses"
REPORT_PAYABLES            = "payables"
REPORT_FINANCIAL_SUMMARY   = "financial_summary"

# ---------------------------------------------------------------------------
# Trend granularity options
# ---------------------------------------------------------------------------

TREND_DAILY   = "daily"
TREND_WEEKLY  = "weekly"
TREND_MONTHLY = "monthly"

TREND_CHOICES = [
    (TREND_DAILY,   "Daily"),
    (TREND_WEEKLY,  "Weekly"),
    (TREND_MONTHLY, "Monthly"),
]

# ---------------------------------------------------------------------------
# Comparison periods
# ---------------------------------------------------------------------------

COMPARE_YESTERDAY     = "yesterday"
COMPARE_PREV_WEEK     = "prev_week"
COMPARE_PREV_MONTH    = "prev_month"
COMPARE_PREV_YEAR     = "prev_year"

# ---------------------------------------------------------------------------
# Default pagination
# ---------------------------------------------------------------------------

DEFAULT_PAGE_SIZE    = 20
MAX_PAGE_SIZE        = 200
DEFAULT_TOP_N        = 10
MAX_TOP_N            = 100

# ---------------------------------------------------------------------------
# Cache TTLs (seconds)
# ---------------------------------------------------------------------------

CACHE_TTL_DASHBOARD    = 60        # 1 minute for live KPIs
CACHE_TTL_TREND        = 300       # 5 minutes for trend data
CACHE_TTL_TOP_ITEMS    = 300       # 5 minutes for top selling
CACHE_TTL_BRANCH       = 300       # 5 minutes for branch summary
CACHE_TTL_INVENTORY    = 120       # 2 minutes for inventory alerts
# Financial accuracy is paramount — very short or no cache
CACHE_TTL_FINANCIAL    = 60        # 1 minute

# ---------------------------------------------------------------------------
# Precision
# ---------------------------------------------------------------------------

ZERO    = Decimal("0.00")
HUNDRED = Decimal("100")

# ---------------------------------------------------------------------------
# Date range presets
# ---------------------------------------------------------------------------

DATE_RANGE_TODAY       = "today"
DATE_RANGE_YESTERDAY   = "yesterday"
DATE_RANGE_LAST_7      = "last_7_days"
DATE_RANGE_LAST_30     = "last_30_days"
DATE_RANGE_THIS_MONTH  = "this_month"
DATE_RANGE_PREV_MONTH  = "prev_month"
DATE_RANGE_CUSTOM      = "custom"

# ---------------------------------------------------------------------------
# Export formats
# ---------------------------------------------------------------------------

EXPORT_FORMAT_CSV   = "CSV"
EXPORT_FORMAT_EXCEL = "EXCEL"
EXPORT_FORMAT_PDF   = "PDF"

# ---------------------------------------------------------------------------
# All permission codes list (for seed command)
# ---------------------------------------------------------------------------

ALL_REPORTING_PERMISSIONS = [
    (PERM_DASHBOARD_VIEW,     "View Reporting Dashboard",             "reporting", "dashboard.view"),
    (PERM_SALES_VIEW,         "View Sales Reports",                   "reporting", "sales.view"),
    (PERM_ORDERS_VIEW,        "View Order Reports",                   "reporting", "orders.view"),
    (PERM_MENU_VIEW,          "View Menu Analytics",                  "reporting", "menu.view"),
    (PERM_BRANCH_VIEW,        "View Branch Performance Reports",      "reporting", "branch.view"),
    (PERM_COUNTER_VIEW,       "View Counter Performance Reports",     "reporting", "counter.view"),
    (PERM_PAYMENT_VIEW,       "View Payment Analytics",               "reporting", "payment.view"),
    (PERM_REFUND_VIEW,        "View Refund Analytics",                "reporting", "refund.view"),
    (PERM_DISCOUNT_VIEW,      "View Discount Analytics",              "reporting", "discount.view"),
    (PERM_KITCHEN_VIEW,       "View Kitchen Performance Reports",     "reporting", "kitchen.view"),
    (PERM_STAFF_VIEW,         "View Staff Performance Reports",       "reporting", "staff.view"),
    (PERM_INVENTORY_VIEW,     "View Inventory Analytics",             "reporting", "inventory.view"),
    (PERM_PURCHASE_VIEW,      "View Purchase Analytics",              "reporting", "purchase.view"),
    (PERM_SUPPLIER_VIEW,      "View Supplier Analytics",              "reporting", "supplier.view"),
    (PERM_EXPENSE_VIEW,       "View Expense Analytics",               "reporting", "expense.view"),
    (PERM_PAYABLE_VIEW,       "View Payable Analytics",               "reporting", "payable.view"),
    (PERM_PROFITABILITY_VIEW, "View Profitability Reports",           "reporting", "profitability.view"),
    (PERM_FINANCIAL_VIEW,     "View Financial Summary Reports",       "reporting", "financial.view"),
    (PERM_EXPORT_CSV,         "Export Reports as CSV",                "reporting", "export.csv"),
    (PERM_EXPORT_EXCEL,       "Export Reports as Excel",              "reporting", "export.excel"),
    (PERM_EXPORT_PDF,         "Export Reports as PDF",                "reporting", "export.pdf"),
]
