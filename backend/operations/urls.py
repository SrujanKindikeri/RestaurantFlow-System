# =============================================================================
# RestaurantFlow — Operations URLs
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from django.urls import path
from operations import views

app_name = "operations"

urlpatterns = [
    # -------------------------------------------------------------------------
    # POS Session
    # -------------------------------------------------------------------------
    path(
        "operations/pos/session/",
        views.POSSessionView.as_view(),
        name="pos-session",
    ),
    path(
        "operations/pos/session/start/",
        views.POSSessionStartView.as_view(),
        name="pos-session-start",
    ),
    path(
        "operations/pos/session/<uuid:session_id>/pause/",
        views.POSSessionPauseView.as_view(),
        name="pos-session-pause",
    ),
    path(
        "operations/pos/session/<uuid:session_id>/resume/",
        views.POSSessionResumeView.as_view(),
        name="pos-session-resume",
    ),
    path(
        "operations/pos/session/<uuid:session_id>/end/",
        views.POSSessionEndView.as_view(),
        name="pos-session-end",
    ),
    path(
        "operations/pos/recovery/",
        views.POSRecoveryView.as_view(),
        name="pos-recovery",
    ),

    # -------------------------------------------------------------------------
    # Barcode / SKU Scan
    # -------------------------------------------------------------------------
    path(
        "operations/pos/scan/",
        views.BarcodeScanView.as_view(),
        name="pos-scan",
    ),

    # -------------------------------------------------------------------------
    # Order Operations
    # -------------------------------------------------------------------------
    path(
        "operations/orders/<uuid:order_id>/hold/",
        views.OrderHoldView.as_view(),
        name="order-hold",
    ),
    path(
        "operations/orders/<uuid:order_id>/resume/",
        views.OrderResumeView.as_view(),
        name="order-resume",
    ),
    path(
        "operations/orders/<uuid:order_id>/priority/",
        views.OrderPriorityView.as_view(),
        name="order-priority",
    ),
    path(
        "operations/orders/<uuid:order_id>/waiter/",
        views.OrderWaiterView.as_view(),
        name="order-waiter",
    ),
    path(
        "operations/orders/<uuid:order_id>/change-request/",
        views.OrderChangeRequestView.as_view(),
        name="order-change-request",
    ),
    path(
        "operations/orders/merge/",
        views.OrderMergeView.as_view(),
        name="order-merge",
    ),

    # -------------------------------------------------------------------------
    # Order Change Request Review
    # -------------------------------------------------------------------------
    path(
        "operations/change-requests/<uuid:change_request_id>/approve/",
        views.OrderChangeRequestApproveView.as_view(),
        name="change-request-approve",
    ),
    path(
        "operations/change-requests/<uuid:change_request_id>/reject/",
        views.OrderChangeRequestRejectView.as_view(),
        name="change-request-reject",
    ),

    # -------------------------------------------------------------------------
    # Modifiers
    # -------------------------------------------------------------------------
    path(
        "operations/menu-items/<uuid:menu_item_id>/modifiers/",
        views.MenuItemModifiersView.as_view(),
        name="menu-item-modifiers",
    ),
    path(
        "operations/order-items/<uuid:order_item_id>/modifiers/",
        views.OrderItemModifierView.as_view(),
        name="order-item-modifiers",
    ),
    path(
        "operations/order-item-modifiers/<uuid:modifier_id>/",
        views.OrderItemModifierDeleteView.as_view(),
        name="order-item-modifier-delete",
    ),

    # -------------------------------------------------------------------------
    # Tables
    # -------------------------------------------------------------------------
    path(
        "operations/tables/",
        views.TablesOperationalView.as_view(),
        name="tables",
    ),
    path(
        "operations/tables/<uuid:table_id>/status/",
        views.TableStatusView.as_view(),
        name="table-status",
    ),
    path(
        "operations/tables/<uuid:table_id>/transfer/",
        views.TableTransferView.as_view(),
        name="table-transfer",
    ),
    path(
        "operations/tables/merge/",
        views.TableMergeView.as_view(),
        name="table-merge",
    ),
    path(
        "operations/tables/<uuid:table_id>/close/",
        views.TableCloseView.as_view(),
        name="table-close",
    ),

    # -------------------------------------------------------------------------
    # Bill Splits
    # -------------------------------------------------------------------------
    path(
        "operations/bills/<uuid:bill_id>/split/",
        views.BillSplitListCreateView.as_view(),
        name="bill-split",
    ),
    path(
        "operations/bills/<uuid:bill_id>/splits/",
        views.BillSplitListCreateView.as_view(),
        name="bill-splits",
    ),
    path(
        "operations/bills/<uuid:bill_id>/splits/<uuid:split_id>/finalize/",
        views.BillSplitFinalizeView.as_view(),
        name="bill-split-finalize",
    ),

    # -------------------------------------------------------------------------
    # Receipts
    # -------------------------------------------------------------------------
    path(
        "operations/bills/<uuid:bill_id>/receipt/print/",
        views.ReceiptPrintView.as_view(),
        name="receipt-print",
    ),
    path(
        "operations/bills/<uuid:bill_id>/receipt/reprint/",
        views.ReceiptReprintView.as_view(),
        name="receipt-reprint",
    ),

    # -------------------------------------------------------------------------
    # Shifts
    # -------------------------------------------------------------------------
    path(
        "operations/shifts/",
        views.ShiftListCreateView.as_view(),
        name="shifts",
    ),
    path(
        "operations/shifts/<uuid:shift_id>/close/",
        views.ShiftCloseView.as_view(),
        name="shift-close",
    ),
    path(
        "operations/shifts/<uuid:shift_id>/handover/",
        views.ShiftHandoverView.as_view(),
        name="shift-handover",
    ),

    # -------------------------------------------------------------------------
    # Operations Dashboard
    # -------------------------------------------------------------------------
    path(
        "operations/dashboard/",
        views.OperationsDashboardView.as_view(),
        name="dashboard",
    ),
]
