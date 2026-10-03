# =============================================================================
# RestaurantFlow — Orders DRF Permission Classes
# Phase 6
#
# Mirrors the pattern in accounts/permissions.py, counters/permissions.py,
# and menu/permissions.py.  All authorization delegates to orders.access.
#
# Object-level permissions:
#   HasTableAccess        — for DiningTable instances
#   HasTableSessionAccess — for TableSession instances
#   HasOrderAccess        — for Order instances
#   HasOrderItemAccess    — for OrderItem instances
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

from orders import access as order_acl

logger = logging.getLogger("orders")


class HasTableAccess(BasePermission):
    """Object-level permission: user must have access to the table's branch."""

    message = "You do not have access to this dining table."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from orders.models import DiningTable
        if not isinstance(obj, DiningTable):
            return False
        result = order_acl.can_access_table(request.user, obj)
        if not result:
            logger.warning(
                "DiningTable access denied: user=%s table=%s",
                request.user.email, obj.pk,
            )
        return result


class HasTableSessionAccess(BasePermission):
    """Object-level permission: user must have access to the table session's branch."""

    message = "You do not have access to this table session."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from orders.models import TableSession
        if not isinstance(obj, TableSession):
            return False
        result = order_acl.can_access_table(request.user, obj.table)
        if not result:
            logger.warning(
                "TableSession access denied: user=%s session=%s",
                request.user.email, obj.pk,
            )
        return result


class HasOrderAccess(BasePermission):
    """Object-level permission: user must have access to the order's branch."""

    message = "You do not have access to this order."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from orders.models import Order
        if not isinstance(obj, Order):
            return False
        result = order_acl.can_access_order(request.user, obj)
        if not result:
            logger.warning(
                "Order access denied: user=%s order=%s",
                request.user.email, obj.pk,
            )
        return result


class HasOrderItemAccess(BasePermission):
    """Object-level permission: user must have access to the order item's branch."""

    message = "You do not have access to this order item."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from orders.models import OrderItem
        if not isinstance(obj, OrderItem):
            return False
        result = order_acl.can_access_order(request.user, obj.order)
        if not result:
            logger.warning(
                "OrderItem access denied: user=%s item=%s",
                request.user.email, obj.pk,
            )
        return result
