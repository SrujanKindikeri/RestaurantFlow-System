# =============================================================================
# RestaurantFlow — Financials URL Configuration
# Phase 12
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [

    # -------------------------------------------------------------------------
    # Financial Dashboard
    # -------------------------------------------------------------------------
    path(
        "financials/dashboard/",
        views.FinancialDashboardView.as_view(),
        name="financial-dashboard",
    ),

    # -------------------------------------------------------------------------
    # Expense Categories
    # -------------------------------------------------------------------------
    path(
        "financials/expense-categories/",
        views.ExpenseCategoryListView.as_view(),
        name="expense-category-list",
    ),
    path(
        "financials/expense-categories/<uuid:pk>/",
        views.ExpenseCategoryDetailView.as_view(),
        name="expense-category-detail",
    ),

    # -------------------------------------------------------------------------
    # Expenses
    # -------------------------------------------------------------------------
    path(
        "financials/expenses/",
        views.ExpenseListView.as_view(),
        name="expense-list",
    ),
    path(
        "financials/expenses/<uuid:pk>/",
        views.ExpenseDetailView.as_view(),
        name="expense-detail",
    ),
    path(
        "financials/expenses/<uuid:pk>/submit/",
        views.ExpenseSubmitView.as_view(),
        name="expense-submit",
    ),
    path(
        "financials/expenses/<uuid:pk>/approve/",
        views.ExpenseApproveView.as_view(),
        name="expense-approve",
    ),
    path(
        "financials/expenses/<uuid:pk>/reject/",
        views.ExpenseRejectView.as_view(),
        name="expense-reject",
    ),
    path(
        "financials/expenses/<uuid:pk>/cancel/",
        views.ExpenseCancelView.as_view(),
        name="expense-cancel",
    ),

    # -------------------------------------------------------------------------
    # Expense Attachments
    # -------------------------------------------------------------------------
    path(
        "financials/expenses/<uuid:pk>/attachments/",
        views.ExpenseAttachmentView.as_view(),
        name="expense-attachments",
    ),
    path(
        "financials/expenses/<uuid:pk>/attachments/<uuid:att_id>/",
        views.ExpenseAttachmentDeleteView.as_view(),
        name="expense-attachment-delete",
    ),

    # -------------------------------------------------------------------------
    # Expense Corrections
    # -------------------------------------------------------------------------
    path(
        "financials/expense-corrections/",
        views.ExpenseCorrectionListView.as_view(),
        name="expense-correction-list",
    ),
    path(
        "financials/expenses/<uuid:pk>/corrections/",
        views.ExpenseCorrectionRequestView.as_view(),
        name="expense-correction-request",
    ),
    path(
        "financials/expense-corrections/<uuid:pk>/",
        views.ExpenseCorrectionDetailView.as_view(),
        name="expense-correction-detail",
    ),
    path(
        "financials/expense-corrections/<uuid:pk>/approve/",
        views.ExpenseCorrectionApproveView.as_view(),
        name="expense-correction-approve",
    ),
    path(
        "financials/expense-corrections/<uuid:pk>/reject/",
        views.ExpenseCorrectionRejectView.as_view(),
        name="expense-correction-reject",
    ),
    path(
        "financials/expense-corrections/<uuid:pk>/cancel/",
        views.ExpenseCorrectionCancelView.as_view(),
        name="expense-correction-cancel",
    ),

    # -------------------------------------------------------------------------
    # Recurring Expenses
    # -------------------------------------------------------------------------
    path(
        "financials/recurring-expenses/",
        views.RecurringExpenseListView.as_view(),
        name="recurring-expense-list",
    ),
    path(
        "financials/recurring-expenses/<uuid:pk>/",
        views.RecurringExpenseDetailView.as_view(),
        name="recurring-expense-detail",
    ),
    path(
        "financials/recurring-expenses/<uuid:pk>/disable/",
        views.RecurringExpenseDisableView.as_view(),
        name="recurring-expense-disable",
    ),

    # -------------------------------------------------------------------------
    # Supplier Invoices
    # -------------------------------------------------------------------------
    path(
        "financials/supplier-invoices/",
        views.SupplierInvoiceListView.as_view(),
        name="supplier-invoice-list",
    ),
    path(
        "financials/supplier-invoices/<uuid:pk>/",
        views.SupplierInvoiceDetailView.as_view(),
        name="supplier-invoice-detail",
    ),
    path(
        "financials/supplier-invoices/<uuid:pk>/submit/",
        views.SupplierInvoiceSubmitView.as_view(),
        name="supplier-invoice-submit",
    ),
    path(
        "financials/supplier-invoices/<uuid:pk>/approve/",
        views.SupplierInvoiceApproveView.as_view(),
        name="supplier-invoice-approve",
    ),
    path(
        "financials/supplier-invoices/<uuid:pk>/cancel/",
        views.SupplierInvoiceCancelView.as_view(),
        name="supplier-invoice-cancel",
    ),

    # -------------------------------------------------------------------------
    # Payables
    # -------------------------------------------------------------------------
    path(
        "financials/payables/",
        views.PayableListView.as_view(),
        name="payable-list",
    ),
    path(
        "financials/payables/dashboard/",
        views.PayableDashboardView.as_view(),
        name="payable-dashboard",
    ),
    path(
        "financials/payables/<uuid:pk>/",
        views.PayableDetailView.as_view(),
        name="payable-detail",
    ),
    path(
        "financials/payables/<uuid:pk>/record-payment/",
        views.PayableRecordPaymentView.as_view(),
        name="payable-record-payment",
    ),
]
