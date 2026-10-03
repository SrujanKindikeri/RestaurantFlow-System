# =============================================================================
# RestaurantFlow — Kitchen URL Configuration
# Phase 7
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Kitchen Orders — live KDS
    # -------------------------------------------------------------------------
    path(
        "kitchen/orders/",
        views.KitchenOrderListView.as_view(),
        name="kitchen-order-list",
    ),
    path(
        "kitchen/orders/<uuid:pk>/",
        views.KitchenOrderDetailView.as_view(),
        name="kitchen-order-detail",
    ),
    path(
        "kitchen/orders/<uuid:pk>/accept/",
        views.KitchenOrderAcceptView.as_view(),
        name="kitchen-order-accept",
    ),
    path(
        "kitchen/orders/<uuid:pk>/start/",
        views.KitchenOrderStartView.as_view(),
        name="kitchen-order-start",
    ),
    path(
        "kitchen/orders/<uuid:pk>/ready/",
        views.KitchenOrderReadyView.as_view(),
        name="kitchen-order-ready",
    ),
    path(
        "kitchen/orders/<uuid:pk>/cancel/",
        views.KitchenOrderCancelView.as_view(),
        name="kitchen-order-cancel",
    ),
    path(
        "kitchen/orders/<uuid:pk>/priority/",
        views.KitchenOrderPriorityView.as_view(),
        name="kitchen-order-priority",
    ),

    # -------------------------------------------------------------------------
    # Kitchen History
    # -------------------------------------------------------------------------
    path(
        "kitchen/history/",
        views.KitchenHistoryView.as_view(),
        name="kitchen-history",
    ),

    # -------------------------------------------------------------------------
    # Kitchen Items
    # -------------------------------------------------------------------------
    path(
        "kitchen/items/<uuid:pk>/",
        views.KitchenOrderItemDetailView.as_view(),
        name="kitchen-item-detail",
    ),
    path(
        "kitchen/items/<uuid:pk>/start/",
        views.KitchenItemStartView.as_view(),
        name="kitchen-item-start",
    ),
    path(
        "kitchen/items/<uuid:pk>/ready/",
        views.KitchenItemReadyView.as_view(),
        name="kitchen-item-ready",
    ),
]
