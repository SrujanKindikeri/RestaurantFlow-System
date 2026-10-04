# =============================================================================
# RestaurantFlow — Accounting URL Configuration
# Phase 13
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------
    path(
        "accounting/dashboard/",
        views.AccountingDashboardView.as_view(),
        name="accounting-dashboard",
    ),

    # -------------------------------------------------------------------------
    # Fiscal Years
    # -------------------------------------------------------------------------
    path(
        "accounting/fiscal-years/",
        views.FiscalYearListView.as_view(),
        name="fiscal-year-list",
    ),
    path(
        "accounting/fiscal-years/<uuid:pk>/",
        views.FiscalYearDetailView.as_view(),
        name="fiscal-year-detail",
    ),
    path(
        "accounting/fiscal-years/<uuid:pk>/close/",
        views.FiscalYearDetailView.as_view(),
        name="fiscal-year-close",
    ),

    # -------------------------------------------------------------------------
    # Accounting Periods
    # -------------------------------------------------------------------------
    path(
        "accounting/periods/",
        views.AccountingPeriodListView.as_view(),
        name="accounting-period-list",
    ),
    path(
        "accounting/periods/<uuid:pk>/",
        views.AccountingPeriodDetailView.as_view(),
        name="accounting-period-detail",
    ),
    path(
        "accounting/periods/<uuid:pk>/close/",
        views.PeriodCloseView.as_view(),
        name="accounting-period-close",
    ),
    path(
        "accounting/periods/<uuid:pk>/reopen/",
        views.PeriodReopenView.as_view(),
        name="accounting-period-reopen",
    ),

    # -------------------------------------------------------------------------
    # Chart of Accounts
    # -------------------------------------------------------------------------
    path(
        "accounting/accounts/",
        views.AccountListView.as_view(),
        name="account-list",
    ),
    path(
        "accounting/accounts/tree/",
        views.AccountTreeView.as_view(),
        name="account-tree",
    ),
    path(
        "accounting/accounts/<uuid:pk>/",
        views.AccountDetailView.as_view(),
        name="account-detail",
    ),
    path(
        "accounting/accounts/<uuid:pk>/deactivate/",
        views.AccountDeactivateView.as_view(),
        name="account-deactivate",
    ),
    path(
        "accounting/accounts/<uuid:pk>/statement/",
        views.AccountStatementView.as_view(),
        name="account-statement",
    ),

    # -------------------------------------------------------------------------
    # Accounting Settings
    # -------------------------------------------------------------------------
    path(
        "accounting/settings/",
        views.AccountingSettingsView.as_view(),
        name="accounting-settings",
    ),

    # -------------------------------------------------------------------------
    # Journal Entries
    # -------------------------------------------------------------------------
    path(
        "accounting/journals/",
        views.JournalEntryListView.as_view(),
        name="journal-entry-list",
    ),
    path(
        "accounting/journals/<uuid:pk>/",
        views.JournalEntryDetailView.as_view(),
        name="journal-entry-detail",
    ),
    path(
        "accounting/journals/<uuid:pk>/post/",
        views.JournalPostView.as_view(),
        name="journal-entry-post",
    ),
    path(
        "accounting/journals/<uuid:pk>/reverse/",
        views.JournalReverseView.as_view(),
        name="journal-entry-reverse",
    ),
    path(
        "accounting/journals/<uuid:pk>/void/",
        views.JournalVoidView.as_view(),
        name="journal-entry-void",
    ),

    # -------------------------------------------------------------------------
    # Reports
    # -------------------------------------------------------------------------
    path(
        "accounting/general-ledger/",
        views.GeneralLedgerView.as_view(),
        name="general-ledger",
    ),
    path(
        "accounting/trial-balance/",
        views.TrialBalanceView.as_view(),
        name="trial-balance",
    ),
    path(
        "accounting/profit-loss/",
        views.ProfitLossView.as_view(),
        name="profit-loss",
    ),
    path(
        "accounting/balance-sheet/",
        views.BalanceSheetView.as_view(),
        name="balance-sheet",
    ),
    path(
        "accounting/cash-flow/",
        views.CashFlowView.as_view(),
        name="cash-flow",
    ),

    # -------------------------------------------------------------------------
    # Payable Payment
    # -------------------------------------------------------------------------
    path(
        "accounting/payable-payment/",
        views.PayablePaymentView.as_view(),
        name="payable-payment",
    ),

    # -------------------------------------------------------------------------
    # Audit Log
    # -------------------------------------------------------------------------
    path(
        "accounting/audit-log/",
        views.AccountingAuditLogListView.as_view(),
        name="accounting-audit-log",
    ),
]
