# =============================================================================
# RestaurantFlow — Payment DRF Permission Classes
# Phase 9
#
# All authorization logic delegates to payments.access and accounts.access.
# Views compose these with IsAuthenticated.
#
# Usage:
#   permission_classes = [IsAuthenticated, HasPermission("payment.view")()]
#   permission_classes = [IsAuthenticated, HasPermission("payment.create")(), HasPaymentAccess()]
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

from payments import access as payment_acl

logger = logging.getLogger("payments")

# Re-export HasPermission from accounts for convenience
from accounts.permissions import HasPermission  # noqa: F401


class HasPaymentAccess(BasePermission):
    """
    Object-level permission: user must be able to access this Payment.

    Returns 404 (not 403) via the queryset in views — this class is
    used as an additional safeguard on action endpoints.
    """

    message = "You do not have access to this payment."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from payments.models import Payment
        if not isinstance(obj, Payment):
            return False
        result = payment_acl.can_access_payment(request.user, obj)
        if not result:
            logger.warning(
                "Payment access denied: user=%s payment=%s",
                request.user.email, obj.pk,
            )
        return result


class HasRefundAccess(BasePermission):
    """
    Object-level permission: user must be able to access this PaymentRefund.
    """

    message = "You do not have access to this refund."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from payments.models import PaymentRefund
        if not isinstance(obj, PaymentRefund):
            return False
        result = payment_acl.can_access_refund(request.user, obj)
        if not result:
            logger.warning(
                "Refund access denied: user=%s refund=%s",
                request.user.email, obj.pk,
            )
        return result
