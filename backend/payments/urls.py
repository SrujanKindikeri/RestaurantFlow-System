# =============================================================================
# RestaurantFlow — Payment URL Configuration
# Phase 9
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Payments — create + list
    # -------------------------------------------------------------------------
    path(
        "payments/",
        views.CreatePaymentView.as_view(),
        name="payment-create",
    ),
    path(
        "payments/list/",
        views.PaymentListView.as_view(),
        name="payment-list",
    ),

    # -------------------------------------------------------------------------
    # Bill-scoped payment endpoints
    # Must be registered BEFORE payments/{id}/ to avoid UUID conflict
    # -------------------------------------------------------------------------
    path(
        "payments/bill/<uuid:bill_id>/",
        views.BillPaymentsView.as_view(),
        name="bill-payments",
    ),
    path(
        "payments/bill/<uuid:bill_id>/summary/",
        views.BillPaymentSummaryView.as_view(),
        name="bill-payment-summary",
    ),
    path(
        "payments/bill/<uuid:bill_id>/receipt/",
        views.BillReceiptView.as_view(),
        name="bill-receipt-with-payments",
    ),

    # -------------------------------------------------------------------------
    # Refund endpoints — standalone (by refund UUID)
    # Must be registered BEFORE payments/{id}/ to avoid UUID conflict
    # -------------------------------------------------------------------------
    path(
        "payments/refunds/<uuid:refund_id>/",
        views.RefundDetailView.as_view(),
        name="refund-detail",
    ),
    path(
        "payments/refunds/<uuid:refund_id>/approve/",
        views.ApproveRefundView.as_view(),
        name="refund-approve",
    ),
    path(
        "payments/refunds/<uuid:refund_id>/reject/",
        views.RejectRefundView.as_view(),
        name="refund-reject",
    ),
    path(
        "payments/refunds/<uuid:refund_id>/process/",
        views.ProcessRefundView.as_view(),
        name="refund-process",
    ),
    path(
        "payments/refunds/<uuid:refund_id>/cancel/",
        views.CancelRefundView.as_view(),
        name="refund-cancel",
    ),

    # -------------------------------------------------------------------------
    # Payment — detail + actions (by payment UUID)
    # -------------------------------------------------------------------------
    path(
        "payments/<uuid:pk>/",
        views.PaymentDetailView.as_view(),
        name="payment-detail",
    ),
    path(
        "payments/<uuid:pk>/cancel/",
        views.CancelPaymentView.as_view(),
        name="payment-cancel",
    ),
    path(
        "payments/<uuid:pk>/refunds/",
        views.PaymentRefundListCreateView.as_view(),
        name="payment-refunds",
    ),
    path(
        "payments/<uuid:pk>/audit/",
        views.PaymentAuditLogView.as_view(),
        name="payment-audit",
    ),
]
