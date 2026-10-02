# =============================================================================
# RestaurantFlow — Counters URL Configuration
# Phase 4
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Counters
    # -------------------------------------------------------------------------
    path("counters/",                              views.CounterListCreateView.as_view(),      name="counter-list-create"),
    path("counters/<uuid:pk>/",                    views.CounterDetailView.as_view(),          name="counter-detail"),
    path("counters/<uuid:pk>/disable/",            views.CounterDisableView.as_view(),         name="counter-disable"),
    path("counters/<uuid:pk>/reactivate/",         views.CounterReactivateView.as_view(),      name="counter-reactivate"),
    path("counters/<uuid:pk>/sessions/open/",      views.CounterOpenSessionView.as_view(),     name="counter-session-open"),

    # -------------------------------------------------------------------------
    # Counter Sessions (standalone)
    # -------------------------------------------------------------------------
    path("counter-sessions/",                      views.CounterSessionListView.as_view(),     name="counter-session-list"),
    path("counter-sessions/<uuid:pk>/",            views.CounterSessionDetailView.as_view(),   name="counter-session-detail"),
    path("counter-sessions/<uuid:pk>/close/",      views.CounterSessionCloseView.as_view(),    name="counter-session-close"),
    path("counter-sessions/<uuid:pk>/force-close/",views.CounterSessionForceCloseView.as_view(),name="counter-session-force-close"),

    # -------------------------------------------------------------------------
    # Counter Assignments
    # -------------------------------------------------------------------------
    path("counter-assignments/",                   views.CounterAssignmentListCreateView.as_view(),  name="counter-assignment-list-create"),
    path("counter-assignments/<uuid:pk>/",         views.CounterAssignmentDetailView.as_view(),      name="counter-assignment-detail"),
    path("counter-assignments/<uuid:pk>/deactivate/", views.CounterAssignmentDeactivateView.as_view(), name="counter-assignment-deactivate"),

    # -------------------------------------------------------------------------
    # Shifts
    # -------------------------------------------------------------------------
    path("shifts/",                                views.ShiftListCreateView.as_view(),        name="shift-list-create"),
    path("shifts/<uuid:pk>/",                      views.ShiftDetailView.as_view(),            name="shift-detail"),

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------
    path("counter-dashboard/",                     views.CounterDashboardView.as_view(),       name="counter-dashboard"),
]
