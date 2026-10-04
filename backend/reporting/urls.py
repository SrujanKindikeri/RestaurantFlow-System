# =============================================================================
# RestaurantFlow — Reporting URLs
# Phase 14
# =============================================================================

from django.urls import path
from reporting import views

app_name = "reporting"

urlpatterns = [
    # Dashboard
    path("reporting/dashboard/", views.DashboardView.as_view(), name="dashboard"),

    # Sales
    path("reporting/sales/summary/", views.SalesSummaryView.as_view(), name="sales-summary"),
    path("reporting/sales/trend/", views.SalesTrendView.as_view(), name="sales-trend"),
    path("reporting/sales/hourly/", views.HourlySalesView.as_view(), name="sales-hourly"),

    # Orders
    path("reporting/orders/summary/", views.OrdersSummaryView.as_view(), name="orders-summary"),
    path("reporting/orders/by-type/", views.OrdersByTypeView.as_view(), name="orders-by-type"),

    # Menu
    path("reporting/menu/items/", views.MenuItemsView.as_view(), name="menu-items"),
    path("reporting/menu/top-selling/", views.TopSellingItemsView.as_view(), name="menu-top-selling"),
    path("reporting/menu/categories/", views.CategoryPerformanceView.as_view(), name="menu-categories"),
    path("reporting/menu/profitability/", views.MenuProfitabilityView.as_view(), name="menu-profitability"),

    # Branch / Counter
    path("reporting/branches/performance/", views.BranchPerformanceView.as_view(), name="branch-performance"),
    path("reporting/counters/performance/", views.CounterPerformanceView.as_view(), name="counter-performance"),

    # Payments
    path("reporting/payments/summary/", views.PaymentSummaryView.as_view(), name="payment-summary"),
    path("reporting/payments/methods/", views.PaymentMethodsView.as_view(), name="payment-methods"),

    # Refunds / Discounts
    path("reporting/refunds/", views.RefundsView.as_view(), name="refunds"),
    path("reporting/discounts/", views.DiscountsView.as_view(), name="discounts"),

    # Kitchen
    path("reporting/kitchen/performance/", views.KitchenPerformanceView.as_view(), name="kitchen-performance"),
    path("reporting/kitchen/items/", views.KitchenItemsView.as_view(), name="kitchen-items"),

    # Staff
    path("reporting/staff/waiters/", views.WaiterPerformanceView.as_view(), name="staff-waiters"),
    path("reporting/staff/cashiers/", views.CashierPerformanceView.as_view(), name="staff-cashiers"),

    # Inventory
    path("reporting/inventory/summary/", views.InventorySummaryView.as_view(), name="inventory-summary"),
    path("reporting/inventory/consumption/", views.InventoryConsumptionView.as_view(), name="inventory-consumption"),
    path("reporting/inventory/wastage/", views.WastageView.as_view(), name="inventory-wastage"),

    # Purchases / Suppliers
    path("reporting/purchases/", views.PurchasesView.as_view(), name="purchases"),
    path("reporting/suppliers/", views.SuppliersView.as_view(), name="suppliers"),

    # Expenses / Payables
    path("reporting/expenses/", views.ExpensesView.as_view(), name="expenses"),
    path("reporting/payables/", views.PayablesView.as_view(), name="payables"),

    # Financial summary (delegates to Phase 13)
    path("reporting/financial-summary/", views.FinancialSummaryView.as_view(), name="financial-summary"),

    # Export
    path("reporting/export/<str:report_type>/", views.ExportCSVView.as_view(), name="export-csv"),
]
