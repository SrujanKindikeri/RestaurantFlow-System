# =============================================================================
# RestaurantFlow — Notifications DRF Permission Classes
# Phase 16
# =============================================================================

from rest_framework.permissions import BasePermission
from accounts import access as acl
from notifications.constants import (
    PERM_NOTIFICATION_VIEW,
    PERM_NOTIFICATION_ADMIN,
    PERM_NOTIFICATION_TEMPLATE_MGMT,
    PERM_NOTIFICATION_DELIVERY_VIEW,
    PERM_PROVIDER_CONFIG_MANAGE,
)


class CanViewOwnNotifications(BasePermission):
    """Any authenticated active user can view their own notifications."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class CanManageNotificationPreferences(BasePermission):
    """Any authenticated user can manage their own notification preferences."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_active)


class CanViewDeliveryHistory(BasePermission):
    """User must have delivery history view permission."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            acl.has_permission(request.user, PERM_NOTIFICATION_DELIVERY_VIEW)
        )


class CanManageNotificationTemplates(BasePermission):
    """User must have template management permission."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            acl.has_permission(request.user, PERM_NOTIFICATION_TEMPLATE_MGMT)
        )


class CanManageProviderConfig(BasePermission):
    """Only users with provider config management permission."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            acl.has_permission(request.user, PERM_PROVIDER_CONFIG_MANAGE)
        )


class IsNotificationAdmin(BasePermission):
    """Full notification admin access."""

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (
                acl.has_permission(request.user, PERM_NOTIFICATION_ADMIN) or
                request.user.is_superuser
            )
        )
