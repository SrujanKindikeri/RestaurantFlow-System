# =============================================================================
# RestaurantFlow — Kitchen Access Control
# Phase 7
#
# Single source of truth for kitchen-related authorization decisions.
# Delegates org/restaurant/branch scope to accounts.access.
#
# Public API:
#   get_accessible_kitchen_orders(user)         → QuerySet[KitchenOrder]
#   can_access_kitchen_order(user, order)       → bool
#   get_accessible_kitchen_items(user)          → QuerySet[KitchenOrderItem]
# =============================================================================

import logging

from accounts import access as acl

logger = logging.getLogger("kitchen")


def get_accessible_kitchen_orders(user):
    """
    Return KitchenOrders scoped to the requesting user's accessible branches.

    - Superuser / staff → all kitchen orders
    - All other users → kitchen orders for their accessible branches only

    IDOR protection: never returns orders for branches the user cannot access.
    """
    from kitchen.models import KitchenOrder

    if not user or not user.is_authenticated or not user.is_active:
        return KitchenOrder.objects.none()

    if user.is_superuser or user.is_staff:
        return KitchenOrder.objects.select_related(
            "order__branch__restaurant__organization",
            "order__table",
            "order__counter",
            "order__assigned_waiter",
            "accepted_by",
            "started_by",
            "completed_by",
            "cancelled_by",
        ).prefetch_related("items__menu_item")

    accessible_branch_ids = acl.get_accessible_branches(user).values_list(
        "pk", flat=True
    )
    return (
        KitchenOrder.objects
        .filter(branch_id__in=accessible_branch_ids)
        .select_related(
            "order__branch__restaurant__organization",
            "order__table",
            "order__counter",
            "order__assigned_waiter",
            "accepted_by",
            "started_by",
            "completed_by",
            "cancelled_by",
        )
        .prefetch_related("items__menu_item")
    )


def can_access_kitchen_order(user, kitchen_order) -> bool:
    """Return True if user can access this kitchen order (branch-scoped)."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_branch(user, kitchen_order.branch)


def get_accessible_kitchen_items(user):
    """
    Return KitchenOrderItems scoped to the requesting user's accessible branches.
    """
    from kitchen.models import KitchenOrderItem

    if not user or not user.is_authenticated or not user.is_active:
        return KitchenOrderItem.objects.none()

    if user.is_superuser or user.is_staff:
        return KitchenOrderItem.objects.select_related(
            "kitchen_order__branch",
            "kitchen_order__order",
            "menu_item",
            "order_item",
        )

    accessible_branch_ids = acl.get_accessible_branches(user).values_list(
        "pk", flat=True
    )
    return KitchenOrderItem.objects.filter(
        kitchen_order__branch_id__in=accessible_branch_ids
    ).select_related(
        "kitchen_order__branch",
        "kitchen_order__order",
        "menu_item",
        "order_item",
    )
