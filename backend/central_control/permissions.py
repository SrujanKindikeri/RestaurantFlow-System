# =============================================================================
# RestaurantFlow — Central Control Center DRF Permission Classes
# Phase 15
#
# All classes delegate to accounts.access — never duplicate logic.
# Usage:
#   permission_classes = [IsAuthenticated, HasCentralPermission("central_control.dashboard.view")]
# =============================================================================

import logging
from rest_framework.permissions import BasePermission, IsAuthenticated  # noqa: F401

from accounts import access as acl

logger = logging.getLogger("central_control")


def HasCentralPermission(code: str):
    """
    Factory that returns a DRF BasePermission class checking a specific
    Central Control permission code.

    Usage:
        permission_classes = [IsAuthenticated, HasCentralPermission("central_control.alert.view")]
    """
    from central_control.constants import PERM_DASHBOARD_VIEW

    class _HasCentralPermission(BasePermission):
        message = f"You do not have the required permission: {code}"
        required_code = code

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            result = acl.has_permission(request.user, self.required_code)
            if not result:
                logger.warning(
                    "CentralControl permission denied: user=%s code=%s view=%s",
                    request.user.email,
                    self.required_code,
                    view.__class__.__name__,
                )
            return result

    _HasCentralPermission.__name__ = f"HasCentralPermission_{code.replace('.', '_')}"
    return _HasCentralPermission


class IsCentralControlUser(BasePermission):
    """
    Request-level: user must have at least the dashboard.view permission,
    indicating they are a Central Control user (COMPANY_HEAD or CENTRAL_ADMIN).
    """
    message = "Central Control access required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True

        from central_control.constants import PERM_DASHBOARD_VIEW
        return acl.has_permission(request.user, PERM_DASHBOARD_VIEW)
