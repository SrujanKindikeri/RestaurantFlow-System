# =============================================================================
# RestaurantFlow — Orders URL Configuration
# Phase 6
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Dining Tables
    # -------------------------------------------------------------------------
    path("tables/",                               views.DiningTableListCreateView.as_view(),  name="table-list-create"),
    path("tables/<uuid:pk>/",                     views.DiningTableDetailView.as_view(),       name="table-detail"),
    path("tables/<uuid:pk>/disable/",             views.DiningTableDisableView.as_view(),      name="table-disable"),
    path("tables/<uuid:pk>/enable/",              views.DiningTableEnableView.as_view(),       name="table-enable"),
    path("tables/<uuid:pk>/sessions/open/",       views.TableSessionOpenView.as_view(),        name="table-session-open"),

    # -------------------------------------------------------------------------
    # Table Sessions (standalone)
    # -------------------------------------------------------------------------
    path("table-sessions/",                       views.TableSessionListView.as_view(),        name="table-session-list"),
    path("table-sessions/<uuid:pk>/",             views.TableSessionDetailView.as_view(),      name="table-session-detail"),
    path("table-sessions/<uuid:pk>/close/",       views.TableSessionCloseView.as_view(),       name="table-session-close"),

    # -------------------------------------------------------------------------
    # Orders
    # -------------------------------------------------------------------------
    path("orders/",                               views.OrderListCreateView.as_view(),         name="order-list-create"),
    path("orders/<uuid:pk>/",                     views.OrderDetailView.as_view(),             name="order-detail"),
    path("orders/<uuid:pk>/confirm/",             views.OrderConfirmView.as_view(),            name="order-confirm"),
    path("orders/<uuid:pk>/cancel/",              views.OrderCancelView.as_view(),             name="order-cancel"),
    path("orders/<uuid:pk>/assign-waiter/",       views.OrderAssignWaiterView.as_view(),       name="order-assign-waiter"),

    # -------------------------------------------------------------------------
    # Order Items
    # -------------------------------------------------------------------------
    path("orders/<uuid:pk>/items/",               views.OrderItemAddView.as_view(),            name="order-item-add"),
    path("order-items/<uuid:pk>/",                views.OrderItemDetailView.as_view(),         name="order-item-detail"),
]
