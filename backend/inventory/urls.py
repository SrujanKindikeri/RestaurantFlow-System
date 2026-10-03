# =============================================================================
# RestaurantFlow — Inventory URL Configuration
# Phase 10
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------
    path("inventory/dashboard/", views.InventoryDashboardView.as_view(), name="inventory-dashboard"),

    # -------------------------------------------------------------------------
    # Categories
    # -------------------------------------------------------------------------
    path("inventory/categories/", views.InventoryCategoryListView.as_view(), name="inventory-category-list"),
    path("inventory/categories/<uuid:pk>/", views.InventoryCategoryDetailView.as_view(), name="inventory-category-detail"),

    # -------------------------------------------------------------------------
    # Items
    # -------------------------------------------------------------------------
    path("inventory/items/", views.InventoryItemListView.as_view(), name="inventory-item-list"),
    path("inventory/items/<uuid:pk>/", views.InventoryItemDetailView.as_view(), name="inventory-item-detail"),

    # -------------------------------------------------------------------------
    # Storage Locations
    # -------------------------------------------------------------------------
    path("inventory/locations/", views.StorageLocationListView.as_view(), name="inventory-location-list"),
    path("inventory/locations/<uuid:pk>/", views.StorageLocationDetailView.as_view(), name="inventory-location-detail"),

    # -------------------------------------------------------------------------
    # Stock Balances
    # -------------------------------------------------------------------------
    path("inventory/stock/", views.StockBalanceListView.as_view(), name="inventory-stock-list"),
    path("inventory/stock/<uuid:item_id>/", views.StockBalanceByItemView.as_view(), name="inventory-stock-by-item"),

    # -------------------------------------------------------------------------
    # Stock Movements (history)
    # -------------------------------------------------------------------------
    path("inventory/movements/", views.StockMovementListView.as_view(), name="inventory-movement-list"),

    # -------------------------------------------------------------------------
    # Suppliers
    # -------------------------------------------------------------------------
    path("inventory/suppliers/", views.SupplierListView.as_view(), name="inventory-supplier-list"),
    path("inventory/suppliers/<uuid:pk>/", views.SupplierDetailView.as_view(), name="inventory-supplier-detail"),

    # -------------------------------------------------------------------------
    # Purchase Orders
    # -------------------------------------------------------------------------
    path("inventory/purchases/", views.PurchaseOrderListView.as_view(), name="inventory-purchase-list"),
    path("inventory/purchases/<uuid:pk>/", views.PurchaseOrderDetailView.as_view(), name="inventory-purchase-detail"),
    path("inventory/purchases/<uuid:pk>/submit/", views.PurchaseOrderSubmitView.as_view(), name="inventory-purchase-submit"),
    path("inventory/purchases/<uuid:pk>/approve/", views.PurchaseOrderApproveView.as_view(), name="inventory-purchase-approve"),
    path("inventory/purchases/<uuid:pk>/receive/", views.PurchaseOrderReceiveView.as_view(), name="inventory-purchase-receive"),
    path("inventory/purchases/<uuid:pk>/cancel/", views.PurchaseOrderCancelView.as_view(), name="inventory-purchase-cancel"),

    # -------------------------------------------------------------------------
    # Stock Transfers
    # -------------------------------------------------------------------------
    path("inventory/transfers/", views.StockTransferListView.as_view(), name="inventory-transfer-list"),
    path("inventory/transfers/<uuid:pk>/", views.StockTransferDetailView.as_view(), name="inventory-transfer-detail"),
    path("inventory/transfers/<uuid:pk>/request/", views.StockTransferRequestView.as_view(), name="inventory-transfer-request"),
    path("inventory/transfers/<uuid:pk>/approve/", views.StockTransferApproveView.as_view(), name="inventory-transfer-approve"),
    path("inventory/transfers/<uuid:pk>/complete/", views.StockTransferCompleteView.as_view(), name="inventory-transfer-complete"),
    path("inventory/transfers/<uuid:pk>/cancel/", views.StockTransferCancelView.as_view(), name="inventory-transfer-cancel"),

    # -------------------------------------------------------------------------
    # Wastage
    # -------------------------------------------------------------------------
    path("inventory/wastage/", views.StockWastageListView.as_view(), name="inventory-wastage-list"),
    path("inventory/wastage/<uuid:pk>/", views.StockWastageDetailView.as_view(), name="inventory-wastage-detail"),
    path("inventory/wastage/<uuid:pk>/approve/", views.StockWastageApproveView.as_view(), name="inventory-wastage-approve"),
    path("inventory/wastage/<uuid:pk>/reject/", views.StockWastageRejectView.as_view(), name="inventory-wastage-reject"),

    # -------------------------------------------------------------------------
    # Adjustments
    # -------------------------------------------------------------------------
    path("inventory/adjustments/", views.StockAdjustmentListView.as_view(), name="inventory-adjustment-list"),
]
