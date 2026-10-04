# =============================================================================
# RestaurantFlow — Central Control Center URL Configuration
# Phase 15
#
# All routes prefixed with /api/central-control/ in root urls.py.
# =============================================================================

from django.urls import path

from central_control.views import (
    CentralDashboardView,
    RestaurantOverviewView,
    RestaurantHealthView,
    BranchOverviewView,
    AlertListView,
    AlertDetailView,
    AlertAcknowledgeView,
    AlertResolveView,
    AlertDismissView,
    IssueListCreateView,
    IssueDetailView,
    IssueAssignView,
    IssueStartView,
    IssueResolveView,
    IssueCloseView,
    IssueCancelView,
    EventTimelineView,
    SystemHealthView,
    CentralSettingsView,
    AuditLogView,
    UserAccessView,
    RunDetectionView,
)

urlpatterns = [
    # Dashboard
    path("central-control/dashboard/", CentralDashboardView.as_view(), name="cc-dashboard"),

    # Restaurants
    path("central-control/restaurants/", RestaurantOverviewView.as_view(), name="cc-restaurants"),
    path("central-control/restaurants/health/", RestaurantHealthView.as_view(), name="cc-restaurant-health"),

    # Branches
    path("central-control/branches/", BranchOverviewView.as_view(), name="cc-branches"),

    # Alerts
    path("central-control/alerts/", AlertListView.as_view(), name="cc-alerts"),
    path("central-control/alerts/<uuid:pk>/", AlertDetailView.as_view(), name="cc-alert-detail"),
    path("central-control/alerts/<uuid:pk>/acknowledge/", AlertAcknowledgeView.as_view(), name="cc-alert-acknowledge"),
    path("central-control/alerts/<uuid:pk>/resolve/", AlertResolveView.as_view(), name="cc-alert-resolve"),
    path("central-control/alerts/<uuid:pk>/dismiss/", AlertDismissView.as_view(), name="cc-alert-dismiss"),

    # Issues
    path("central-control/issues/", IssueListCreateView.as_view(), name="cc-issues"),
    path("central-control/issues/<uuid:pk>/", IssueDetailView.as_view(), name="cc-issue-detail"),
    path("central-control/issues/<uuid:pk>/assign/", IssueAssignView.as_view(), name="cc-issue-assign"),
    path("central-control/issues/<uuid:pk>/start/", IssueStartView.as_view(), name="cc-issue-start"),
    path("central-control/issues/<uuid:pk>/resolve/", IssueResolveView.as_view(), name="cc-issue-resolve"),
    path("central-control/issues/<uuid:pk>/close/", IssueCloseView.as_view(), name="cc-issue-close"),
    path("central-control/issues/<uuid:pk>/cancel/", IssueCancelView.as_view(), name="cc-issue-cancel"),

    # Event timeline
    path("central-control/events/", EventTimelineView.as_view(), name="cc-events"),

    # System health
    path("central-control/system-health/", SystemHealthView.as_view(), name="cc-system-health"),

    # Settings
    path("central-control/settings/", CentralSettingsView.as_view(), name="cc-settings"),

    # Audit log
    path("central-control/audit/", AuditLogView.as_view(), name="cc-audit"),

    # User access monitoring
    path("central-control/users/", UserAccessView.as_view(), name="cc-users"),

    # Admin: manual detection trigger
    path("central-control/run-detection/", RunDetectionView.as_view(), name="cc-run-detection"),
]
