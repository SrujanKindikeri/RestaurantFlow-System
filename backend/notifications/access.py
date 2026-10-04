# =============================================================================
# RestaurantFlow — Notifications Access Control
# Phase 16
#
# Pure Python access-check helpers (no DRF dependency).
# =============================================================================

from accounts import access as acl
from notifications.constants import (
    PERM_NOTIFICATION_VIEW,
    PERM_NOTIFICATION_ADMIN,
    PERM_NOTIFICATION_TEMPLATE_MGMT,
    PERM_NOTIFICATION_DELIVERY_VIEW,
    PERM_PROVIDER_CONFIG_MANAGE,
)


def can_view_own_notifications(user) -> bool:
    """Any authenticated active user can view their own notifications."""
    return bool(user and user.is_authenticated and user.is_active)


def can_view_delivery_history(user) -> bool:
    return acl.has_permission(user, PERM_NOTIFICATION_DELIVERY_VIEW)


def can_manage_templates(user) -> bool:
    return acl.has_permission(user, PERM_NOTIFICATION_TEMPLATE_MGMT)


def can_manage_provider_config(user) -> bool:
    return acl.has_permission(user, PERM_PROVIDER_CONFIG_MANAGE)


def is_notification_admin(user) -> bool:
    return (
        getattr(user, "is_superuser", False) or
        acl.has_permission(user, PERM_NOTIFICATION_ADMIN)
    )


def user_can_access_notification(user, notification) -> bool:
    """
    Verify that a user can see a specific Notification.
    The user must have an active assignment in the notification's company.
    """
    return acl.can_access_organization(user, notification.company)
