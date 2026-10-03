# =============================================================================
# RestaurantFlow — Billing URL Configuration
# Phase 8
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Bills — list + create-from-order
    # -------------------------------------------------------------------------
    path(
        "billing/bills/",
        views.BillListView.as_view(),
        name="bill-list",
    ),
    path(
        "billing/bills/from-order/<uuid:order_id>/",
        views.CreateBillFromOrderView.as_view(),
        name="bill-create-from-order",
    ),

    # -------------------------------------------------------------------------
    # Bill — detail
    # -------------------------------------------------------------------------
    path(
        "billing/bills/<uuid:pk>/",
        views.BillDetailView.as_view(),
        name="bill-detail",
    ),

    # -------------------------------------------------------------------------
    # Bill — calculate (preview totals)
    # -------------------------------------------------------------------------
    path(
        "billing/bills/<uuid:pk>/calculate/",
        views.BillCalculateView.as_view(),
        name="bill-calculate",
    ),

    # -------------------------------------------------------------------------
    # Bill — discount actions
    # -------------------------------------------------------------------------
    path(
        "billing/bills/<uuid:pk>/discount/",
        views.BillDiscountView.as_view(),
        name="bill-discount",
    ),

    # -------------------------------------------------------------------------
    # Bill — lifecycle actions
    # -------------------------------------------------------------------------
    path(
        "billing/bills/<uuid:pk>/finalize/",
        views.BillFinalizeView.as_view(),
        name="bill-finalize",
    ),
    path(
        "billing/bills/<uuid:pk>/cancel/",
        views.BillCancelView.as_view(),
        name="bill-cancel",
    ),
    path(
        "billing/bills/<uuid:pk>/void/",
        views.BillVoidView.as_view(),
        name="bill-void",
    ),

    # -------------------------------------------------------------------------
    # Bill — receipt
    # -------------------------------------------------------------------------
    path(
        "billing/bills/<uuid:pk>/receipt/",
        views.BillReceiptView.as_view(),
        name="bill-receipt",
    ),

    # -------------------------------------------------------------------------
    # Corrections — request (nested under bill)
    # -------------------------------------------------------------------------
    path(
        "billing/bills/<uuid:pk>/corrections/",
        views.RequestBillCorrectionView.as_view(),
        name="bill-correction-request",
    ),

    # -------------------------------------------------------------------------
    # Corrections — list (global, scoped to user)
    # -------------------------------------------------------------------------
    path(
        "billing/bill-corrections/",
        views.BillCorrectionListView.as_view(),
        name="bill-correction-list",
    ),

    # -------------------------------------------------------------------------
    # Corrections — detail + actions
    # -------------------------------------------------------------------------
    path(
        "billing/bill-corrections/<uuid:pk>/",
        views.BillCorrectionDetailView.as_view(),
        name="bill-correction-detail",
    ),
    path(
        "billing/bill-corrections/<uuid:pk>/approve/",
        views.ApproveCorrectionView.as_view(),
        name="bill-correction-approve",
    ),
    path(
        "billing/bill-corrections/<uuid:pk>/reject/",
        views.RejectCorrectionView.as_view(),
        name="bill-correction-reject",
    ),
    path(
        "billing/bill-corrections/<uuid:pk>/cancel/",
        views.CancelCorrectionView.as_view(),
        name="bill-correction-cancel",
    ),
]
