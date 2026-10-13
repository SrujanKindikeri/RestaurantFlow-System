# =============================================================================
# RestaurantFlow — Print Services (Phase 19)
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

import logging
from django.utils import timezone

from operations.constants import (
    PRINT_ORIGINAL, PRINT_REPRINT, PRINT_DUPLICATE, PRINT_KITCHEN,
    AUDIT_RECEIPT_PRINTED, AUDIT_RECEIPT_REPRINTED,
)
from operations.exceptions import ReceiptPrintNotAllowed

logger = logging.getLogger("operations")


def log_receipt_print(*, bill, payment, printed_by, print_type, reason=""):
    """
    Log a receipt print event. Creates an immutable ReceiptPrintLog record.

    For REPRINT/DUPLICATE, reason is required.
    """
    from operations.models import ReceiptPrintLog, OperationsAuditLog
    from django.db import transaction

    if print_type in (PRINT_REPRINT, PRINT_DUPLICATE) and not reason:
        raise ReceiptPrintNotAllowed(
            "A reason is required for receipt reprints and duplicates."
        )

    with transaction.atomic():
        log = ReceiptPrintLog.objects.create(
            bill=bill,
            payment=payment,
            printed_by=printed_by,
            print_type=print_type,
            reason=reason,
        )

        event_type = (
            AUDIT_RECEIPT_REPRINTED
            if print_type in (PRINT_REPRINT, PRINT_DUPLICATE)
            else AUDIT_RECEIPT_PRINTED
        )

        OperationsAuditLog.objects.create(
            actor=printed_by,
            event_type=event_type,
            branch=bill.branch,
            bill_id=bill.id,
            new_value=print_type,
            metadata={
                "print_log_id": str(log.id),
                "reason": reason,
            },
        )

    logger.info(
        "Receipt print logged: bill=%s type=%s by=%s",
        bill.bill_number, print_type, printed_by.email,
    )
    return log


def build_receipt_data(bill, payment=None):
    """
    Build a structured receipt data dictionary from authoritative DB records.

    This is the ONLY receipt data source. Frontend/printer must NOT
    construct receipt data from its own state.

    Returns a dict safe for serialization and rendering.
    """
    from payments.models import Payment, PaymentStatus

    # Get the branch and restaurant
    branch = bill.branch
    try:
        restaurant = branch.restaurant
        organization = restaurant.organization
    except Exception:
        restaurant = None
        organization = None

    # Collect payments if not specified
    if payment is None:
        payments = list(
            bill.payments.filter(status=PaymentStatus.COMPLETED)
            .order_by("completed_at")
        )
    else:
        payments = [payment]

    # Build items
    items = []
    for item in bill.items.select_related("menu_item").order_by("created_at"):
        items.append({
            "name": item.item_name_snapshot,
            "sku": item.sku_snapshot,
            "quantity": str(item.quantity),
            "unit_price": str(item.unit_price),
            "gross_amount": str(item.gross_amount),
            "discount_amount": str(item.discount_amount),
            "taxable_amount": str(item.taxable_amount),
            "tax_rate": str(item.tax_rate),
            "tax_code": item.tax_code,
            "tax_amount": str(item.tax_amount),
            "total_amount": str(item.total_amount),
        })

    # Build payment rows
    payment_rows = []
    for p in payments:
        payment_rows.append({
            "payment_number": p.payment_number,
            "method": p.payment_method,
            "amount": str(p.amount),
            "cash_received": str(p.cash_received) if p.cash_received else None,
            "change_amount": str(p.change_amount) if p.change_amount else None,
            "transaction_reference": p.transaction_reference,
            "completed_at": p.completed_at.isoformat() if p.completed_at else None,
        })

    return {
        "bill_number": bill.bill_number,
        "order_number": bill.order.order_number,
        "order_type": bill.order.order_type,
        "table": (
            bill.order.table.table_number
            if bill.order.table
            else None
        ),
        "counter": (
            bill.order.counter.code
            if bill.order.counter
            else None
        ),
        "branch": {
            "name": branch.name,
            "address": getattr(branch, "address", ""),
            "phone": getattr(branch, "phone", ""),
            "gstin": getattr(branch, "gstin", ""),
        },
        "restaurant": {
            "name": restaurant.name if restaurant else "",
        },
        "organization": {
            "name": organization.name if organization else "",
        },
        "items": items,
        "subtotal": str(bill.subtotal),
        "discount_type": bill.discount_type,
        "discount_value": str(bill.discount_value),
        "discount_amount": str(bill.discount_amount),
        "taxable_amount": str(bill.taxable_amount),
        "tax_amount": str(bill.tax_amount),
        "tax_breakdown": bill.tax_breakdown,
        "rounding_amount": str(bill.rounding_amount),
        "grand_total": str(bill.grand_total),
        "payments": payment_rows,
        "created_by": bill.created_by.email,
        "finalized_at": bill.finalized_at.isoformat() if bill.finalized_at else None,
        "printed_at": timezone.now().isoformat(),
    }


def build_kitchen_ticket_data(kitchen_order):
    """
    Build kitchen ticket data. Does NOT include financial information.
    """
    order = kitchen_order.order
    branch = kitchen_order.branch

    items = []
    for item in kitchen_order.items.order_by("created_at"):
        # Get modifiers if any
        modifiers = []
        try:
            for mod in item.order_item.modifiers.all():
                modifiers.append({
                    "name": mod.name,
                    "value": mod.value,
                })
        except Exception:
            pass

        items.append({
            "name": item.item_name_snapshot,
            "quantity": str(item.quantity),
            "notes": item.notes,
            "food_type": item.food_type,
            "station": item.station,
            "modifiers": modifiers,
        })

    return {
        "order_number": order.order_number,
        "order_type": order.order_type,
        "priority": kitchen_order.priority,
        "table": order.table.table_number if order.table else None,
        "counter": order.counter.code if order.counter else None,
        "kitchen_note": kitchen_order.kitchen_note,
        "items": items,
        "received_at": kitchen_order.received_at.isoformat(),
        "branch": branch.name,
        # NOTE: No payment, customer PII, or accounting data
    }
