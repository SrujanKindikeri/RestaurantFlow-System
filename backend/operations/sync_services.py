# =============================================================================
# RestaurantFlow — Sync / Recovery Services (Phase 19)
# Phase 19: Advanced POS & Restaurant Operations
#
# POS Session Recovery — allows the frontend to recover safe state
# after a browser refresh or disconnect.
#
# CRITICAL: Never return sensitive financial data.
# Safe state only: session info, open orders, held orders, table status.
# =============================================================================

import logging
from django.utils import timezone

logger = logging.getLogger("operations")


def get_pos_recovery_data(*, user, counter):
    """
    Return safe POS recovery data for the given user+counter.

    Used when the browser refreshes — the POS app can restore:
        - active POS session
        - current counter info
        - open draft orders (not CONFIRMED)
        - held orders
        - pending bills (by bill_number only — no financial totals in localStorage)

    NEVER included in the recovery payload:
        - card data
        - payment credentials
        - tokens
        - authoritative financial totals
    """
    from operations.models import POSSession
    from orders.models import Order, OrderStatus
    from operations.constants import POS_SESSION_ACTIVE, POS_SESSION_PAUSED
    from operations.pos_services import ORDER_STATUS_ON_HOLD

    active_session = POSSession.objects.filter(
        user=user,
        counter=counter,
        status__in=[POS_SESSION_ACTIVE, POS_SESSION_PAUSED],
    ).first()

    if not active_session:
        return {"active_session": None, "recovery_data": None}

    branch = active_session.branch

    # Open draft orders at this counter
    draft_orders = Order.objects.filter(
        branch=branch,
        counter=counter,
        status=OrderStatus.DRAFT,
    ).values("id", "order_number", "order_type", "created_at", "guest_count")

    # Held orders
    held_orders = Order.objects.filter(
        branch=branch,
        counter=counter,
        status=ORDER_STATUS_ON_HOLD,
    ).values("id", "order_number", "order_type", "created_at")

    # Tables with active sessions (for dine-in recovery)
    from orders.models import DiningTable, TableSessionStatus
    from operations.models import TableOperationalStatus
    from operations.constants import TABLE_OP_OCCUPIED, TABLE_OP_BILL_PENDING

    occupied_tables = DiningTable.objects.filter(
        branch=branch,
    ).filter(
        operational_status__status__in=[TABLE_OP_OCCUPIED, TABLE_OP_BILL_PENDING]
    ).values("id", "table_number", "section", "capacity")

    return {
        "active_session": {
            "id": str(active_session.id),
            "status": active_session.status,
            "started_at": active_session.started_at.isoformat(),
            "counter_id": str(counter.id),
            "counter_code": counter.code,
            "branch_id": str(branch.id),
            "branch_name": branch.name,
        },
        "recovery_data": {
            "draft_orders": [
                {
                    "id": str(o["id"]),
                    "order_number": o["order_number"],
                    "order_type": o["order_type"],
                }
                for o in draft_orders
            ],
            "held_orders": [
                {
                    "id": str(o["id"]),
                    "order_number": o["order_number"],
                    "order_type": o["order_type"],
                }
                for o in held_orders
            ],
            "occupied_tables": [
                {
                    "id": str(t["id"]),
                    "table_number": t["table_number"],
                    "section": t["section"],
                    "capacity": t["capacity"],
                }
                for t in occupied_tables
            ],
        },
    }


def get_operations_dashboard_data(*, branch, user):
    """
    Aggregate operational dashboard data for a branch.

    Used by: Cashier dashboard, Manager dashboard, Shift summary.
    Does NOT calculate accounting — reads operational state only.
    """
    from orders.models import Order, OrderStatus, DiningTable, TableSessionStatus
    from billing.models import Bill, BillStatus
    from kitchen.models import KitchenOrder, KitchenOrderStatus
    from operations.models import POSSession, OperationalShift
    from operations.constants import (
        POS_SESSION_ACTIVE, OP_SHIFT_OPEN,
        TABLE_OP_AVAILABLE, TABLE_OP_OCCUPIED, TABLE_OP_BILL_PENDING,
    )

    now = timezone.now()

    # Active POS sessions
    active_pos_sessions = POSSession.objects.filter(
        branch=branch,
        status=POS_SESSION_ACTIVE,
    ).count()

    # Orders
    open_orders = Order.objects.filter(
        branch=branch,
        status__in=[OrderStatus.DRAFT, OrderStatus.CONFIRMED],
    ).count()

    held_orders = Order.objects.filter(
        branch=branch,
        status="ON_HOLD",
    ).count()

    # Bills awaiting payment
    pending_bills = Bill.objects.filter(
        branch=branch,
        status=BillStatus.FINALIZED,
    ).exclude(
        order__status="CANCELLED"
    ).count()

    # Kitchen backlog
    kitchen_backlog = KitchenOrder.objects.filter(
        branch=branch,
        status__in=[
            KitchenOrderStatus.NEW,
            KitchenOrderStatus.ACCEPTED,
            KitchenOrderStatus.PREPARING,
        ],
    ).count()

    ready_orders = KitchenOrder.objects.filter(
        branch=branch,
        status=KitchenOrderStatus.READY,
    ).count()

    # Tables
    total_tables = DiningTable.objects.filter(
        branch=branch,
        status="ACTIVE",
    ).count()

    occupied_tables = DiningTable.objects.filter(
        branch=branch,
        sessions__status=TableSessionStatus.OPEN,
    ).distinct().count()

    # Current open shift
    current_shift = OperationalShift.objects.filter(
        branch=branch,
        status=OP_SHIFT_OPEN,
    ).order_by("-started_at").first()

    return {
        "branch_id": str(branch.id),
        "branch_name": branch.name,
        "timestamp": now.isoformat(),
        "pos": {
            "active_sessions": active_pos_sessions,
        },
        "orders": {
            "open": open_orders,
            "on_hold": held_orders,
        },
        "billing": {
            "pending_payment": pending_bills,
        },
        "kitchen": {
            "backlog": kitchen_backlog,
            "ready": ready_orders,
        },
        "tables": {
            "total": total_tables,
            "occupied": occupied_tables,
            "available": total_tables - occupied_tables,
        },
        "current_shift": {
            "id": str(current_shift.id),
            "shift_type": current_shift.shift_type,
            "started_at": current_shift.started_at.isoformat(),
        } if current_shift else None,
    }
