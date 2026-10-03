# =============================================================================
# RestaurantFlow — Billing DRF Permission Classes
# Phase 8
#
# All authorization logic delegates to billing.access and accounts.access.
# Views compose these with IsAuthenticated.
#
# Usage:
#   permission_classes = [IsAuthenticated, HasPermission("bill.view")()]
#   permission_classes = [IsAuthenticated, HasPermission("bill.finalize")(), HasBillAccess()]
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

from accounts import access as acl
from billing import access as bill_acl

logger = logging.getLogger("billing")

# Re-export for convenience — views import from here
from accounts.permissions import HasPermission  # noqa: F401


class HasBillAccess(BasePermission):
    """
    Object-level permission: user must be able to access this Bill.

    Used for retrieve/update/action views where the Bill is the object.
    Returns 404 (not 403) via the queryset in views — this class is
    used as an additional safeguard on actions.
    """

    message = "You do not have access to this bill."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from billing.models import Bill
        if not isinstance(obj, Bill):
            return False
        result = bill_acl.can_access_bill(request.user, obj)
        if not result:
            logger.warning(
                "Bill access denied: user=%s bill=%s",
                request.user.email, obj.pk,
            )
        return result


class HasCorrectionAccess(BasePermission):
    """
    Object-level permission: user must be able to access this
    BillCorrectionRequest.
    """

    message = "You do not have access to this correction request."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from billing.models import BillCorrectionRequest
        if not isinstance(obj, BillCorrectionRequest):
            return False
        result = bill_acl.can_access_correction(request.user, obj)
        if not result:
            logger.warning(
                "Correction access denied: user=%s correction=%s",
                request.user.email, obj.pk,
            )
        return result
