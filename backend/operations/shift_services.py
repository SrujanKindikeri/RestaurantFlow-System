# =============================================================================
# RestaurantFlow — Shift Services (Phase 19)
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Count, Q

from operations.constants import (
    OP_SHIFT_OPEN, OP_SHIFT_CLOSED,
    AUDIT_SHIFT_CREATED, AUDIT_SHIFT_CLOSED, AUDIT_SHIFT_HANDOVER_CREATED,
)
from operations.exceptions import ShiftAlreadyClosed

logger = logging.getLogger("operations")


def open_shift(*, branch, shift_type, opened_by, notes=""):
    """Open a new OperationalShift for a branch."""
    from operations.models import OperationalShift, OperationsAuditLog

    with transaction.atomic():
        shift = OperationalShift.objects.create(
            branch=branch,
            shift_type=shift_type,
            status=OP_SHIFT_OPEN,
            started_at=timezone.now(),
            opened_by=opened_by,
            notes=notes,
        )

        OperationsAuditLog.objects.create(
            actor=opened_by,
            event_type=AUDIT_SHIFT_CREATED,
            branch=branch,
            shift_id=shift.id,
            new_value=shift_type,
        )

    logger.info(
        "Operational shift opened: branch=%s type=%s shift=%s",
        branch.name, shift_type, shift.id,
    )
    return shift


def close_shift(*, shift, closed_by, actual_notes=""):
    """Close an open OperationalShift."""
    from operations.models import OperationsAuditLog

    if shift.status == OP_SHIFT_CLOSED:
        raise ShiftAlreadyClosed(
            f"Shift {shift.id} is already closed."
        )

    with transaction.atomic():
        shift.status = OP_SHIFT_CLOSED
        shift.ended_at = timezone.now()
        shift.closed_by = closed_by
        if actual_notes:
            shift.notes = actual_notes
        shift.save(
            update_fields=["status", "ended_at", "closed_by", "notes", "updated_at"]
        )

        OperationsAuditLog.objects.create(
            actor=closed_by,
            event_type=AUDIT_SHIFT_CLOSED,
            branch=shift.branch,
            shift_id=shift.id,
        )

    return shift


def add_handover_note(*, shift, created_by, note_type, content, priority="NORMAL"):
    """Add a handover note to a shift."""
    from operations.models import ShiftHandoverNote, OperationsAuditLog

    with transaction.atomic():
        note = ShiftHandoverNote.objects.create(
            shift=shift,
            created_by=created_by,
            note_type=note_type,
            content=content,
            priority=priority,
        )

        OperationsAuditLog.objects.create(
            actor=created_by,
            event_type=AUDIT_SHIFT_HANDOVER_CREATED,
            branch=shift.branch,
            shift_id=shift.id,
            new_value=note_type,
        )

    return note


def get_shift_summary(shift):
    """
    Build a shift handover summary from existing service data.

    Uses existing Payment, Order, Bill, KitchenOrder services.
    Does NOT recalculate accounting — reads from DB aggregates only.
    """
    from orders.models import Order, OrderStatus
    from billing.models import Bill, BillStatus
    from payments.models import Payment, PaymentStatus, PaymentMethod
    from kitchen.models import KitchenOrder, KitchenOrderStatus
    from operations.models import ShiftHandoverNote

    branch = shift.branch
    start = shift.started_at
    end = shift.ended_at or timezone.now()

    # Orders during this shift
    orders_qs = Order.objects.filter(
        branch=branch,
        created_at__gte=start,
        created_at__lte=end,
    )
    total_orders = orders_qs.count()
    confirmed_orders = orders_qs.filter(status=OrderStatus.CONFIRMED).count()
    cancelled_orders = orders_qs.filter(status="CANCELLED").count()
    open_orders = orders_qs.filter(
        status__in=["DRAFT", "CONFIRMED"]
    ).count()

    # Bills
    bills_qs = Bill.objects.filter(
        branch=branch,
        created_at__gte=start,
        created_at__lte=end,
    )
    total_bills = bills_qs.count()
    pending_bills = bills_qs.filter(status=BillStatus.FINALIZED).filter(
        ~Q(payments__status=PaymentStatus.COMPLETED)
    ).distinct().count()

    # Payments
    payments_qs = Payment.objects.filter(
        branch=branch,
        created_at__gte=start,
        created_at__lte=end,
        status=PaymentStatus.COMPLETED,
    )
    total_sales = payments_qs.aggregate(
        total=Sum("amount")
    )["total"] or 0
    cash_total = payments_qs.filter(
        payment_method=PaymentMethod.CASH
    ).aggregate(total=Sum("amount"))["total"] or 0
    payment_count = payments_qs.count()

    # Refunds
    from payments.models import PaymentRefund, RefundStatus
    refund_total = PaymentRefund.objects.filter(
        payment__branch=branch,
        created_at__gte=start,
        created_at__lte=end,
        status=RefundStatus.PROCESSED,
    ).aggregate(total=Sum("amount"))["total"] or 0

    # Kitchen
    pending_kitchen = KitchenOrder.objects.filter(
        branch=branch,
        status__in=[
            KitchenOrderStatus.NEW,
            KitchenOrderStatus.ACCEPTED,
            KitchenOrderStatus.PREPARING,
        ],
    ).count()

    # Handover notes
    notes = ShiftHandoverNote.objects.filter(
        shift=shift
    ).values("note_type", "priority", "content", "created_at")

    return {
        "shift_id": str(shift.id),
        "shift_type": shift.shift_type,
        "branch": branch.name,
        "started_at": shift.started_at,
        "ended_at": shift.ended_at,
        "status": shift.status,
        "orders": {
            "total": total_orders,
            "confirmed": confirmed_orders,
            "cancelled": cancelled_orders,
            "open": open_orders,
        },
        "bills": {
            "total": total_bills,
            "pending_payment": pending_bills,
        },
        "payments": {
            "count": payment_count,
            "total_sales": str(total_sales),
            "cash_total": str(cash_total),
            "refund_total": str(refund_total),
            "net_sales": str(total_sales - refund_total),
        },
        "kitchen": {
            "pending_orders": pending_kitchen,
        },
        "handover_notes": list(notes),
    }
