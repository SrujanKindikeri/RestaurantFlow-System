# =============================================================================
# RestaurantFlow — Orders Access Control
# Phase 6
#
# Single source of truth for orders-related authorization decisions.
# Delegates org/restaurant/branch scope to accounts.access.
#
# Public API:
#   get_accessible_tables(user)             → QuerySet[DiningTable]
#   can_access_table(user, table)           → bool
#   get_accessible_table_sessions(user)     → QuerySet[TableSession]
#   get_accessible_orders(user)             → QuerySet[Order]
#   can_access_order(user, order)           → bool
#   get_accessible_order_items(user)        → QuerySet[OrderItem]
# =============================================================================

import logging

from accounts import access as acl

logger = logging.getLogger("orders")


# ---------------------------------------------------------------------------
# DiningTable
# ---------------------------------------------------------------------------

def get_accessible_tables(user):
    """
    Return DiningTables scoped to the requesting user's accessible branches.
    """
    from orders.models import DiningTable

    if not user or not user.is_authenticated or not user.is_active:
        return DiningTable.objects.none()

    if user.is_superuser or user.is_staff:
        return DiningTable.objects.select_related(
            "branch__restaurant__organization"
        )

    accessible_branch_ids = acl.get_accessible_branches(user).values_list(
        "pk", flat=True
    )
    return DiningTable.objects.filter(
        branch_id__in=accessible_branch_ids
    ).select_related("branch__restaurant__organization")


def can_access_table(user, table) -> bool:
    """Return True if user can access this dining table."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    accessible = get_accessible_tables(user)
    return accessible.filter(pk=table.pk).exists()


# ---------------------------------------------------------------------------
# TableSession
# ---------------------------------------------------------------------------

def get_accessible_table_sessions(user):
    """
    Return TableSessions scoped to the user's accessible branches.
    """
    from orders.models import TableSession

    if not user or not user.is_authenticated or not user.is_active:
        return TableSession.objects.none()

    if user.is_superuser or user.is_staff:
        return TableSession.objects.select_related(
            "table__branch__restaurant__organization",
            "opened_by",
            "closed_by",
        )

    accessible_branch_ids = acl.get_accessible_branches(user).values_list(
        "pk", flat=True
    )
    return TableSession.objects.filter(
        table__branch_id__in=accessible_branch_ids
    ).select_related(
        "table__branch__restaurant__organization",
        "opened_by",
        "closed_by",
    )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def get_accessible_orders(user):
    """
    Return Orders scoped to the requesting user.

    Scope rules:
    - Superuser/staff:     all orders
    - Org-scope roles:     all orders in their org's branches
    - Restaurant-scope:    all orders in their restaurant's branches
    - Branch-scope:        orders in their assigned branch
    - Own orders:          orders they created or are assigned to as waiter
                           (additional filter applied in view layer when needed)
    """
    from orders.models import Order

    if not user or not user.is_authenticated or not user.is_active:
        return Order.objects.none()

    if user.is_superuser or user.is_staff:
        return Order.objects.select_related(
            "branch__restaurant__organization",
            "table",
            "table_session",
            "counter",
            "counter_session",
            "created_by",
            "assigned_waiter",
            "cancelled_by",
        )

    accessible_branch_ids = acl.get_accessible_branches(user).values_list(
        "pk", flat=True
    )
    return Order.objects.filter(
        branch_id__in=accessible_branch_ids
    ).select_related(
        "branch__restaurant__organization",
        "table",
        "table_session",
        "counter",
        "counter_session",
        "created_by",
        "assigned_waiter",
        "cancelled_by",
    )


def can_access_order(user, order) -> bool:
    """Return True if user can access this order."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    accessible = get_accessible_orders(user)
    return accessible.filter(pk=order.pk).exists()


# ---------------------------------------------------------------------------
# OrderItem
# ---------------------------------------------------------------------------

def get_accessible_order_items(user):
    """
    Return OrderItems scoped to the user's accessible branches.
    """
    from orders.models import OrderItem

    if not user or not user.is_authenticated or not user.is_active:
        return OrderItem.objects.none()

    if user.is_superuser or user.is_staff:
        return OrderItem.objects.select_related(
            "order__branch__restaurant__organization",
            "menu_item",
        )

    accessible_branch_ids = acl.get_accessible_branches(user).values_list(
        "pk", flat=True
    )
    return OrderItem.objects.filter(
        order__branch_id__in=accessible_branch_ids
    ).select_related(
        "order__branch__restaurant__organization",
        "menu_item",
    )
