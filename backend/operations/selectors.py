# =============================================================================
# RestaurantFlow — Operations Selectors
# Phase 19: Advanced POS & Restaurant Operations
#
# Selectors provide optimized read-only querysets for views.
# All selectors respect user scope via access.py.
# =============================================================================

import logging

logger = logging.getLogger("operations")


def get_pos_session_for_user_counter(user, counter):
    """Return active/paused POSSession for user+counter."""
    from operations.models import POSSession
    from operations.constants import POS_SESSION_ACTIVE, POS_SESSION_PAUSED

    return POSSession.objects.filter(
        user=user,
        counter=counter,
        status__in=[POS_SESSION_ACTIVE, POS_SESSION_PAUSED],
    ).select_related("counter", "counter_session", "branch").first()


def get_tables_with_status(branch):
    """
    Return DiningTables for a branch with their operational status.
    Prefetches operational_status and active session info.
    """
    from orders.models import DiningTable

    return (
        DiningTable.objects
        .filter(branch=branch, status="ACTIVE")
        .select_related("operational_status")
        .prefetch_related("sessions")
        .order_by("display_order", "table_number")
    )


def get_open_orders_for_branch(branch):
    """Return open (DRAFT + CONFIRMED + ON_HOLD) orders for a branch."""
    from orders.models import Order

    return (
        Order.objects
        .filter(
            branch=branch,
            status__in=["DRAFT", "CONFIRMED", "ON_HOLD"],
        )
        .select_related(
            "table", "counter", "assigned_waiter", "customer",
            "table_session",
        )
        .prefetch_related("items")
        .order_by("-created_at")
    )


def get_orders_for_waiter(user, branch):
    """Return orders assigned to this waiter."""
    from orders.models import Order

    return (
        Order.objects
        .filter(
            branch=branch,
            assigned_waiter=user,
            status__in=["DRAFT", "CONFIRMED"],
        )
        .select_related("table", "customer")
        .prefetch_related("items", "kitchen_order")
        .order_by("-created_at")
    )


def get_pending_bills_for_branch(branch):
    """Return finalized bills awaiting payment."""
    from billing.models import Bill, BillStatus
    from payments.models import PaymentStatus

    return (
        Bill.objects
        .filter(branch=branch, status=BillStatus.FINALIZED)
        .exclude(payments__status=PaymentStatus.COMPLETED)
        .select_related("order", "order__table", "order__customer")
        .order_by("-finalized_at")
        .distinct()
    )


def get_modifier_groups_for_menu_item(menu_item):
    """Return active modifier groups for a menu item."""
    from operations.models import MenuModifierGroup

    return (
        MenuModifierGroup.objects
        .filter(menu_items=menu_item, is_active=True)
        .prefetch_related("options")
        .order_by("name")
    )


def get_shift_handover_notes(shift):
    """Return handover notes for a shift, ordered by priority then date."""
    from operations.models import ShiftHandoverNote

    priority_order = {"HIGH": 0, "NORMAL": 1, "LOW": 2}
    notes = ShiftHandoverNote.objects.filter(shift=shift).select_related("created_by")
    return sorted(notes, key=lambda n: (priority_order.get(n.priority, 1), -n.created_at.timestamp()))


def get_print_history_for_bill(bill):
    """Return all print logs for a bill."""
    from operations.models import ReceiptPrintLog

    return (
        ReceiptPrintLog.objects
        .filter(bill=bill)
        .select_related("printed_by", "payment")
        .order_by("-printed_at")
    )
