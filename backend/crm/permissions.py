# =============================================================================
# RestaurantFlow — CRM DRF Permission Classes
# Phase 17
#
# All authorization logic delegates to crm.access and accounts.access.
# Never duplicate permission logic here.
#
# Usage:
#   permission_classes = [IsAuthenticated, HasPermission("customer.view")]
#   permission_classes = [IsAuthenticated, HasCRMAccess]
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

from accounts import access as acl
from accounts.permissions import HasPermission  # noqa: F401 — re-exported for convenience
import crm.access as crm_acl

logger = logging.getLogger("crm")


class HasCRMAccess(BasePermission):
    """
    Request-level: user must have at least customer.view permission.
    Used as a baseline guard on all CRM views.
    """
    message = "CRM access required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return acl.has_permission(request.user, "customer.view")


class HasCustomerAccess(BasePermission):
    """
    Object-level: the requesting user must have access to the Customer instance.
    """
    message = "You do not have access to this customer."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from crm.models import Customer
        if not isinstance(obj, Customer):
            return False
        result = crm_acl.can_access_customer(request.user, obj)
        if not result:
            logger.warning(
                "Customer access denied: user=%s customer=%s",
                request.user.email, obj.pk,
            )
        return result
