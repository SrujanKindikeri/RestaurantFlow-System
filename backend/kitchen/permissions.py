# =============================================================================
# RestaurantFlow — Kitchen DRF Permission Classes
# Phase 7
#
# Mirrors the pattern in accounts/permissions.py and orders/permissions.py.
# All authorization delegates to accounts.access — never duplicated here.
#
# Usage:
#   class MyView(APIView):
#       permission_classes = [IsAuthenticated, HasPermission("kitchen.view")]
#
# Kitchen permission codes:
#   kitchen.view            — view kitchen orders for assigned branch
#   kitchen.view_history    — view historical kitchen data
#   kitchen.accept          — accept a NEW kitchen order
#   kitchen.start           — start preparation (ACCEPTED → PREPARING)
#   kitchen.item_start      — start an individual item (NEW → PREPARING)
#   kitchen.item_ready      — mark an individual item READY
#   kitchen.order_ready     — mark the full order READY
#   kitchen.cancel          — cancel a kitchen order
#   kitchen.priority_update — change order priority
# =============================================================================

import logging

from rest_framework.permissions import BasePermission

from accounts import access as acl
from kitchen import access as kitchen_acl

logger = logging.getLogger("kitchen")


# ---------------------------------------------------------------------------
# Re-export HasPermission from accounts for convenience
# ---------------------------------------------------------------------------
from accounts.permissions import HasPermission  # noqa: F401 — re-exported


# ---------------------------------------------------------------------------
# Object-level: access to a specific KitchenOrder
# ---------------------------------------------------------------------------

class HasKitchenOrderAccess(BasePermission):
    """
    Object-level permission: user must have access to the
    KitchenOrder's branch.
    """

    message = "You do not have access to this kitchen order."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from kitchen.models import KitchenOrder
        if not isinstance(obj, KitchenOrder):
            return False
        result = kitchen_acl.can_access_kitchen_order(request.user, obj)
        if not result:
            logger.warning(
                "KitchenOrder access denied: user=%s kitchen_order=%s",
                request.user.email, obj.pk,
            )
        return result


# ---------------------------------------------------------------------------
# Object-level: access to a specific KitchenOrderItem
# ---------------------------------------------------------------------------

class HasKitchenItemAccess(BasePermission):
    """
    Object-level permission: user must have access to the
    KitchenOrderItem's branch (via parent KitchenOrder).
    """

    message = "You do not have access to this kitchen order item."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from kitchen.models import KitchenOrderItem
        if not isinstance(obj, KitchenOrderItem):
            return False
        result = kitchen_acl.can_access_kitchen_order(
            request.user, obj.kitchen_order
        )
        if not result:
            logger.warning(
                "KitchenOrderItem access denied: user=%s item=%s",
                request.user.email, obj.pk,
            )
        return result
