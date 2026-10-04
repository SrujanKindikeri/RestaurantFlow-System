# =============================================================================
# RestaurantFlow — Notifications URL Configuration
# Phase 16
# =============================================================================

from django.urls import path
from notifications import views

app_name = "notifications"

urlpatterns = [
    # -------------------------------------------------------------------------
    # User-facing
    # -------------------------------------------------------------------------
    path(
        "notifications/",
        views.NotificationListView.as_view(),
        name="notification-list",
    ),
    path(
        "notifications/unread-count/",
        views.NotificationUnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "notifications/read-all/",
        views.NotificationReadAllView.as_view(),
        name="notification-read-all",
    ),
    path(
        "notifications/<uuid:pk>/",
        views.NotificationDetailView.as_view(),
        name="notification-detail",
    ),
    path(
        "notifications/<uuid:pk>/read/",
        views.NotificationReadView.as_view(),
        name="notification-read",
    ),
    path(
        "notifications/<uuid:pk>/acknowledge/",
        views.NotificationAcknowledgeView.as_view(),
        name="notification-acknowledge",
    ),

    # -------------------------------------------------------------------------
    # Preferences
    # -------------------------------------------------------------------------
    path(
        "notifications/preferences/",
        views.NotificationPreferenceListView.as_view(),
        name="notification-preferences",
    ),
    path(
        "notifications/preferences/<uuid:pk>/",
        views.NotificationPreferenceDetailView.as_view(),
        name="notification-preference-detail",
    ),

    # -------------------------------------------------------------------------
    # Delivery history (user's own)
    # -------------------------------------------------------------------------
    path(
        "notifications/deliveries/",
        views.NotificationDeliveryListView.as_view(),
        name="notification-deliveries",
    ),

    # -------------------------------------------------------------------------
    # Admin
    # -------------------------------------------------------------------------
    path(
        "notifications/admin/templates/",
        views.AdminTemplateListView.as_view(),
        name="admin-template-list",
    ),
    path(
        "notifications/admin/templates/<uuid:pk>/",
        views.AdminTemplateDetailView.as_view(),
        name="admin-template-detail",
    ),
    path(
        "notifications/admin/providers/",
        views.AdminProviderConfigListView.as_view(),
        name="admin-provider-list",
    ),
    path(
        "notifications/admin/providers/status/",
        views.ProviderStatusView.as_view(),
        name="admin-provider-status",
    ),
    path(
        "notifications/admin/providers/<uuid:pk>/",
        views.AdminProviderConfigDetailView.as_view(),
        name="admin-provider-detail",
    ),
    path(
        "notifications/admin/deliveries/",
        views.AdminDeliveryListView.as_view(),
        name="admin-delivery-list",
    ),
]
