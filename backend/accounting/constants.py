# =============================================================================
# RestaurantFlow — Accounting Constants
# Phase 13: Accounting Ledger, Double-Entry Bookkeeping
# =============================================================================

from decimal import Decimal

# ---------------------------------------------------------------------------
# Decimal sentinels
# ---------------------------------------------------------------------------
ZERO = Decimal("0.00")
DECIMAL_MONEY = Decimal("0.01")


# ---------------------------------------------------------------------------
# Fiscal Year Status
# ---------------------------------------------------------------------------
FY_OPEN   = "OPEN"
FY_CLOSED = "CLOSED"

FISCAL_YEAR_STATUS_CHOICES = [
    (FY_OPEN,   "Open"),
    (FY_CLOSED, "Closed"),
]

FY_VALID_TRANSITIONS = {
    FY_OPEN:   [FY_CLOSED],
    FY_CLOSED: [],  # terminal
}


# ---------------------------------------------------------------------------
# Accounting Period Status
# ---------------------------------------------------------------------------
PERIOD_OPEN             = "OPEN"
PERIOD_CLOSE_REQUESTED  = "CLOSE_REQUESTED"
PERIOD_CLOSED           = "CLOSED"

PERIOD_STATUS_CHOICES = [
    (PERIOD_OPEN,            "Open"),
    (PERIOD_CLOSE_REQUESTED, "Close Requested"),
    (PERIOD_CLOSED,          "Closed"),
]

PERIOD_VALID_TRANSITIONS = {
    PERIOD_OPEN:            [PERIOD_CLOSE_REQUESTED, PERIOD_CLOSED],
    PERIOD_CLOSE_REQUESTED: [PERIOD_CLOSED, PERIOD_OPEN],   # can reopen to cancel close request
    PERIOD_CLOSED:          [PERIOD_OPEN],                  # controlled reopen
}


# ---------------------------------------------------------------------------
# Account Types
# ---------------------------------------------------------------------------
ACCOUNT_TYPE_ASSET     = "ASSET"
ACCOUNT_TYPE_LIABILITY = "LIABILITY"
ACCOUNT_TYPE_EQUITY    = "EQUITY"
ACCOUNT_TYPE_REVENUE   = "REVENUE"
ACCOUNT_TYPE_EXPENSE   = "EXPENSE"

ACCOUNT_TYPE_CHOICES = [
    (ACCOUNT_TYPE_ASSET,     "Asset"),
    (ACCOUNT_TYPE_LIABILITY, "Liability"),
    (ACCOUNT_TYPE_EQUITY,    "Equity"),
    (ACCOUNT_TYPE_REVENUE,   "Revenue"),
    (ACCOUNT_TYPE_EXPENSE,   "Expense"),
]


# ---------------------------------------------------------------------------
# Account Subtypes
# ---------------------------------------------------------------------------
# Asset subtypes
SUBTYPE_CASH              = "CASH"
SUBTYPE_BANK              = "BANK"
SUBTYPE_ACCOUNTS_RECEIVABLE = "ACCOUNTS_RECEIVABLE"
SUBTYPE_INVENTORY         = "INVENTORY"
SUBTYPE_PREPAID_EXPENSE   = "PREPAID_EXPENSE"
SUBTYPE_FIXED_ASSET       = "FIXED_ASSET"
SUBTYPE_OTHER_ASSET       = "OTHER_ASSET"

# Liability subtypes
SUBTYPE_ACCOUNTS_PAYABLE  = "ACCOUNTS_PAYABLE"
SUBTYPE_TAX_PAYABLE       = "TAX_PAYABLE"
SUBTYPE_OTHER_LIABILITY   = "OTHER_LIABILITY"

# Equity subtypes
SUBTYPE_OWNER_CAPITAL     = "OWNER_CAPITAL"
SUBTYPE_RETAINED_EARNINGS = "RETAINED_EARNINGS"
SUBTYPE_DRAWINGS          = "DRAWINGS"

# Revenue subtypes
SUBTYPE_FOOD_SALES        = "FOOD_SALES"
SUBTYPE_BEVERAGE_SALES    = "BEVERAGE_SALES"
SUBTYPE_OTHER_SALES       = "OTHER_SALES"
SUBTYPE_DISCOUNTS         = "DISCOUNTS"
SUBTYPE_OTHER_REVENUE     = "OTHER_REVENUE"

# Expense subtypes
SUBTYPE_COST_OF_GOODS_SOLD = "COST_OF_GOODS_SOLD"
SUBTYPE_RENT              = "RENT"
SUBTYPE_ELECTRICITY       = "ELECTRICITY"
SUBTYPE_WATER             = "WATER"
SUBTYPE_SALARY            = "SALARY"
SUBTYPE_MARKETING         = "MARKETING"
SUBTYPE_MAINTENANCE       = "MAINTENANCE"
SUBTYPE_TRANSPORT         = "TRANSPORT"
SUBTYPE_OFFICE            = "OFFICE"
SUBTYPE_OTHER_EXPENSE     = "OTHER_EXPENSE"

ACCOUNT_SUBTYPE_CHOICES = [
    # Asset
    (SUBTYPE_CASH,               "Cash"),
    (SUBTYPE_BANK,               "Bank"),
    (SUBTYPE_ACCOUNTS_RECEIVABLE,"Accounts Receivable"),
    (SUBTYPE_INVENTORY,          "Inventory"),
    (SUBTYPE_PREPAID_EXPENSE,    "Prepaid Expense"),
    (SUBTYPE_FIXED_ASSET,        "Fixed Asset"),
    (SUBTYPE_OTHER_ASSET,        "Other Asset"),
    # Liability
    (SUBTYPE_ACCOUNTS_PAYABLE,   "Accounts Payable"),
    (SUBTYPE_TAX_PAYABLE,        "Tax Payable"),
    (SUBTYPE_OTHER_LIABILITY,    "Other Liability"),
    # Equity
    (SUBTYPE_OWNER_CAPITAL,      "Owner Capital"),
    (SUBTYPE_RETAINED_EARNINGS,  "Retained Earnings"),
    (SUBTYPE_DRAWINGS,           "Drawings"),
    # Revenue
    (SUBTYPE_FOOD_SALES,         "Food Sales"),
    (SUBTYPE_BEVERAGE_SALES,     "Beverage Sales"),
    (SUBTYPE_OTHER_SALES,        "Other Sales"),
    (SUBTYPE_DISCOUNTS,          "Discounts"),
    (SUBTYPE_OTHER_REVENUE,      "Other Revenue"),
    # Expense
    (SUBTYPE_COST_OF_GOODS_SOLD, "Cost of Goods Sold"),
    (SUBTYPE_RENT,               "Rent"),
    (SUBTYPE_ELECTRICITY,        "Electricity"),
    (SUBTYPE_WATER,              "Water"),
    (SUBTYPE_SALARY,             "Salary"),
    (SUBTYPE_MARKETING,          "Marketing"),
    (SUBTYPE_MAINTENANCE,        "Maintenance"),
    (SUBTYPE_TRANSPORT,          "Transport"),
    (SUBTYPE_OFFICE,             "Office"),
    (SUBTYPE_OTHER_EXPENSE,      "Other Expense"),
]

# Mapping: account_type → allowed subtypes
ACCOUNT_TYPE_TO_SUBTYPES = {
    ACCOUNT_TYPE_ASSET: [
        SUBTYPE_CASH, SUBTYPE_BANK, SUBTYPE_ACCOUNTS_RECEIVABLE,
        SUBTYPE_INVENTORY, SUBTYPE_PREPAID_EXPENSE, SUBTYPE_FIXED_ASSET,
        SUBTYPE_OTHER_ASSET,
    ],
    ACCOUNT_TYPE_LIABILITY: [
        SUBTYPE_ACCOUNTS_PAYABLE, SUBTYPE_TAX_PAYABLE, SUBTYPE_OTHER_LIABILITY,
    ],
    ACCOUNT_TYPE_EQUITY: [
        SUBTYPE_OWNER_CAPITAL, SUBTYPE_RETAINED_EARNINGS, SUBTYPE_DRAWINGS,
    ],
    ACCOUNT_TYPE_REVENUE: [
        SUBTYPE_FOOD_SALES, SUBTYPE_BEVERAGE_SALES, SUBTYPE_OTHER_SALES,
        SUBTYPE_DISCOUNTS, SUBTYPE_OTHER_REVENUE,
    ],
    ACCOUNT_TYPE_EXPENSE: [
        SUBTYPE_COST_OF_GOODS_SOLD, SUBTYPE_RENT, SUBTYPE_ELECTRICITY,
        SUBTYPE_WATER, SUBTYPE_SALARY, SUBTYPE_MARKETING, SUBTYPE_MAINTENANCE,
        SUBTYPE_TRANSPORT, SUBTYPE_OFFICE, SUBTYPE_OTHER_EXPENSE,
    ],
}


# ---------------------------------------------------------------------------
# Normal Balance (debit increases vs credit increases)
# ---------------------------------------------------------------------------
NORMAL_BALANCE_DEBIT  = "DEBIT"
NORMAL_BALANCE_CREDIT = "CREDIT"

NORMAL_BALANCE_CHOICES = [
    (NORMAL_BALANCE_DEBIT,  "Debit"),
    (NORMAL_BALANCE_CREDIT, "Credit"),
]

# Derived normal balance per account type (the accounting standard rule)
ACCOUNT_TYPE_NORMAL_BALANCE = {
    ACCOUNT_TYPE_ASSET:     NORMAL_BALANCE_DEBIT,
    ACCOUNT_TYPE_EXPENSE:   NORMAL_BALANCE_DEBIT,
    ACCOUNT_TYPE_LIABILITY: NORMAL_BALANCE_CREDIT,
    ACCOUNT_TYPE_EQUITY:    NORMAL_BALANCE_CREDIT,
    ACCOUNT_TYPE_REVENUE:   NORMAL_BALANCE_CREDIT,
}


# ---------------------------------------------------------------------------
# Journal Entry Status
# ---------------------------------------------------------------------------
JE_DRAFT    = "DRAFT"
JE_POSTED   = "POSTED"
JE_REVERSED = "REVERSED"
JE_VOID     = "VOID"

JOURNAL_ENTRY_STATUS_CHOICES = [
    (JE_DRAFT,    "Draft"),
    (JE_POSTED,   "Posted"),
    (JE_REVERSED, "Reversed"),
    (JE_VOID,     "Void"),
]


# ---------------------------------------------------------------------------
# Journal Entry Number format
# ---------------------------------------------------------------------------
JE_NUMBER_FORMAT = "JE-{seq:06d}"


# ---------------------------------------------------------------------------
# Source Types — what business transaction generated this journal entry
# ---------------------------------------------------------------------------
SOURCE_BILL                = "BILL"
SOURCE_PAYMENT             = "PAYMENT"
SOURCE_PAYMENT_REFUND      = "PAYMENT_REFUND"
SOURCE_SUPPLIER_INVOICE    = "SUPPLIER_INVOICE"
SOURCE_EXPENSE             = "EXPENSE"
SOURCE_INVENTORY_CONSUMPTION = "INVENTORY_CONSUMPTION"
SOURCE_CONSUMPTION_REVERSAL  = "CONSUMPTION_REVERSAL"
SOURCE_PAYABLE_PAYMENT     = "PAYABLE_PAYMENT"
SOURCE_MANUAL              = "MANUAL"
SOURCE_PERIOD_CLOSE        = "PERIOD_CLOSE"

SOURCE_TYPE_CHOICES = [
    (SOURCE_BILL,                 "Bill"),
    (SOURCE_PAYMENT,              "Payment"),
    (SOURCE_PAYMENT_REFUND,       "Payment Refund"),
    (SOURCE_SUPPLIER_INVOICE,     "Supplier Invoice"),
    (SOURCE_EXPENSE,              "Expense"),
    (SOURCE_INVENTORY_CONSUMPTION,"Inventory Consumption"),
    (SOURCE_CONSUMPTION_REVERSAL, "Consumption Reversal"),
    (SOURCE_PAYABLE_PAYMENT,      "Payable Payment"),
    (SOURCE_MANUAL,               "Manual"),
    (SOURCE_PERIOD_CLOSE,         "Period Close"),
]


# ---------------------------------------------------------------------------
# Reference Types (for journal entry lines — granular source info)
# ---------------------------------------------------------------------------
REF_BILL_ITEM       = "BILL_ITEM"
REF_PAYMENT         = "PAYMENT"
REF_REFUND          = "REFUND"
REF_EXPENSE         = "EXPENSE"
REF_SUPPLIER_INVOICE = "SUPPLIER_INVOICE"
REF_CONSUMPTION     = "CONSUMPTION"
REF_PAYABLE         = "PAYABLE"

REFERENCE_TYPE_CHOICES = [
    (REF_BILL_ITEM,        "Bill Item"),
    (REF_PAYMENT,          "Payment"),
    (REF_REFUND,           "Refund"),
    (REF_EXPENSE,          "Expense"),
    (REF_SUPPLIER_INVOICE, "Supplier Invoice"),
    (REF_CONSUMPTION,      "Consumption"),
    (REF_PAYABLE,          "Payable"),
]


# ---------------------------------------------------------------------------
# Audit Actions
# ---------------------------------------------------------------------------
AUDIT_ACCOUNT_CREATED         = "ACCOUNT_CREATED"
AUDIT_ACCOUNT_UPDATED         = "ACCOUNT_UPDATED"
AUDIT_ACCOUNT_DEACTIVATED     = "ACCOUNT_DEACTIVATED"

AUDIT_JOURNAL_CREATED         = "JOURNAL_CREATED"
AUDIT_JOURNAL_POSTED          = "JOURNAL_POSTED"
AUDIT_JOURNAL_REVERSED        = "JOURNAL_REVERSED"
AUDIT_JOURNAL_VOIDED          = "JOURNAL_VOIDED"

AUDIT_PERIOD_CREATED          = "PERIOD_CREATED"
AUDIT_PERIOD_CLOSE_REQUESTED  = "PERIOD_CLOSE_REQUESTED"
AUDIT_PERIOD_CLOSED           = "PERIOD_CLOSED"
AUDIT_PERIOD_REOPENED         = "PERIOD_REOPENED"

AUDIT_FY_CREATED              = "FY_CREATED"
AUDIT_FY_CLOSED               = "FY_CLOSED"

AUDIT_SETTINGS_UPDATED        = "SETTINGS_UPDATED"

AUDIT_POSTED_FROM_BILL        = "ACCOUNTING_POSTED_FROM_BILL"
AUDIT_POSTED_FROM_PAYMENT     = "ACCOUNTING_POSTED_FROM_PAYMENT"
AUDIT_POSTED_FROM_REFUND      = "ACCOUNTING_POSTED_FROM_REFUND"
AUDIT_POSTED_FROM_EXPENSE     = "ACCOUNTING_POSTED_FROM_EXPENSE"
AUDIT_POSTED_FROM_SINV        = "ACCOUNTING_POSTED_FROM_SUPPLIER_INVOICE"
AUDIT_POSTED_FROM_CONSUMPTION = "ACCOUNTING_POSTED_FROM_CONSUMPTION"
AUDIT_POSTED_FROM_PAYABLE     = "ACCOUNTING_POSTED_FROM_PAYABLE_PAYMENT"

AUDIT_ACTION_CHOICES = [
    (AUDIT_ACCOUNT_CREATED,         "Account Created"),
    (AUDIT_ACCOUNT_UPDATED,         "Account Updated"),
    (AUDIT_ACCOUNT_DEACTIVATED,     "Account Deactivated"),
    (AUDIT_JOURNAL_CREATED,         "Journal Created"),
    (AUDIT_JOURNAL_POSTED,          "Journal Posted"),
    (AUDIT_JOURNAL_REVERSED,        "Journal Reversed"),
    (AUDIT_JOURNAL_VOIDED,          "Journal Voided"),
    (AUDIT_PERIOD_CREATED,          "Period Created"),
    (AUDIT_PERIOD_CLOSE_REQUESTED,  "Period Close Requested"),
    (AUDIT_PERIOD_CLOSED,           "Period Closed"),
    (AUDIT_PERIOD_REOPENED,         "Period Reopened"),
    (AUDIT_FY_CREATED,              "Fiscal Year Created"),
    (AUDIT_FY_CLOSED,               "Fiscal Year Closed"),
    (AUDIT_SETTINGS_UPDATED,        "Settings Updated"),
    (AUDIT_POSTED_FROM_BILL,        "Posted from Bill"),
    (AUDIT_POSTED_FROM_PAYMENT,     "Posted from Payment"),
    (AUDIT_POSTED_FROM_REFUND,      "Posted from Refund"),
    (AUDIT_POSTED_FROM_EXPENSE,     "Posted from Expense"),
    (AUDIT_POSTED_FROM_SINV,        "Posted from Supplier Invoice"),
    (AUDIT_POSTED_FROM_CONSUMPTION, "Posted from Consumption"),
    (AUDIT_POSTED_FROM_PAYABLE,     "Posted from Payable Payment"),
]


# ---------------------------------------------------------------------------
# Permission Codes
# ---------------------------------------------------------------------------
PERM_ACCOUNT_VIEW         = "accounting.account.view"
PERM_ACCOUNT_CREATE       = "accounting.account.create"
PERM_ACCOUNT_UPDATE       = "accounting.account.update"
PERM_ACCOUNT_DEACTIVATE   = "accounting.account.deactivate"

PERM_JOURNAL_VIEW         = "accounting.journal.view"
PERM_JOURNAL_CREATE       = "accounting.journal.create"
PERM_JOURNAL_POST         = "accounting.journal.post"
PERM_JOURNAL_REVERSE      = "accounting.journal.reverse"

PERM_PERIOD_VIEW          = "accounting.period.view"
PERM_PERIOD_CREATE        = "accounting.period.create"
PERM_PERIOD_CLOSE         = "accounting.period.close"
PERM_PERIOD_REOPEN        = "accounting.period.reopen"

PERM_LEDGER_VIEW          = "accounting.ledger.view"
PERM_TRIAL_BALANCE_VIEW   = "accounting.trial_balance.view"
PERM_PROFIT_LOSS_VIEW     = "accounting.profit_loss.view"
PERM_BALANCE_SHEET_VIEW   = "accounting.balance_sheet.view"
PERM_CASH_FLOW_VIEW       = "accounting.cash_flow.view"

PERM_CONFIG_VIEW          = "accounting.configuration.view"
PERM_CONFIG_MANAGE        = "accounting.configuration.manage"

ALL_ACCOUNTING_PERMISSIONS = [
    (PERM_ACCOUNT_VIEW,       "accounting", "account.view",      "View Chart of Accounts"),
    (PERM_ACCOUNT_CREATE,     "accounting", "account.create",    "Create Accounts"),
    (PERM_ACCOUNT_UPDATE,     "accounting", "account.update",    "Update Accounts"),
    (PERM_ACCOUNT_DEACTIVATE, "accounting", "account.deactivate","Deactivate Accounts"),
    (PERM_JOURNAL_VIEW,       "accounting", "journal.view",      "View Journal Entries"),
    (PERM_JOURNAL_CREATE,     "accounting", "journal.create",    "Create Journal Entries"),
    (PERM_JOURNAL_POST,       "accounting", "journal.post",      "Post Journal Entries"),
    (PERM_JOURNAL_REVERSE,    "accounting", "journal.reverse",   "Reverse Journal Entries"),
    (PERM_PERIOD_VIEW,        "accounting", "period.view",       "View Accounting Periods"),
    (PERM_PERIOD_CREATE,      "accounting", "period.create",     "Create Accounting Periods"),
    (PERM_PERIOD_CLOSE,       "accounting", "period.close",      "Close Accounting Periods"),
    (PERM_PERIOD_REOPEN,      "accounting", "period.reopen",     "Reopen Accounting Periods"),
    (PERM_LEDGER_VIEW,        "accounting", "ledger.view",       "View General Ledger"),
    (PERM_TRIAL_BALANCE_VIEW, "accounting", "trial_balance.view","View Trial Balance"),
    (PERM_PROFIT_LOSS_VIEW,   "accounting", "profit_loss.view",  "View Profit & Loss"),
    (PERM_BALANCE_SHEET_VIEW, "accounting", "balance_sheet.view","View Balance Sheet"),
    (PERM_CASH_FLOW_VIEW,     "accounting", "cash_flow.view",    "View Cash Flow"),
    (PERM_CONFIG_VIEW,        "accounting", "configuration.view","View Accounting Config"),
    (PERM_CONFIG_MANAGE,      "accounting", "configuration.manage","Manage Accounting Config"),
]
