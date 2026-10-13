# =============================================================================
# RestaurantFlow — Table Services (Phase 19)
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone

from operations.constants import (
    TRANSFER_REQUESTED, TRANSFER_COMPLETED, TRANSFER_CANCELLED,
    MERGE_REQUESTED, MERGE_COMPLETED, MERGE_CANCELLED,
    TABLE_OP_AVAILABLE, TABLE_OP_OCCUPIED, TABLE_OP_CLEANING,
    TABLE_OP_OUT_OF_SERVICE, TABLE_OP_BILL_PENDING,
    AUDIT_TABLE_TRANSFER_REQUESTED, AUDIT_TABLE_TRANSFER_COMPLETED,
    AUDIT_TABLE_MERGED, AUDIT_TABLE_OP_STATUS_CHANGED,
)
from operations.exceptions import (
    TableTransferConflict, TableMergeConflict, TableNotAvailable,
)

logger = logging.getLogger("operations")


def get_table_operational_status(table):
    """
    Return (or create) the TableOperationalStatus for a table.
    """
    from operations.models import TableOperationalStatus

    status_obj, _ = TableOperationalStatus.objects.get_or_create(
        table=table,
        defaults={"status": TABLE_OP_AVAILABLE},
    )
    return status_obj


def set_table_operational_status(*, table, new_status, user, notes=""):
    """Set the operational status of a table explicitly."""
    from operations.models import OperationsAuditLog

    status_obj = get_table_operational_status(table)
    old_status = status_obj.status

    valid_statuses = [s[0] for s in [
        (TABLE_OP_AVAILABLE, ""), (TABLE_OP_OCCUPIED, ""),
        (TABLE_OP_CLEANING, ""), (TABLE_OP_OUT_OF_SERVICE, ""),
        (TABLE_OP_BILL_PENDING, ""),
    ]]

    with transaction.atomic():
        status_obj.status = new_status
        status_obj.updated_by = user
        status_obj.notes = notes
        status_obj.save(
            update_fields=["status", "updated_by", "notes", "updated_at"]
        )

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_TABLE_OP_STATUS_CHANGED,
            table_id=table.id,
            old_value=old_status,
            new_value=new_status,
            metadata={"notes": notes},
        )

    return status_obj


def request_table_transfer(*, order, destination_table, requested_by, reason=""):
    """
    Request that an order be transferred to a different table.

    Rules:
        - Destination must be AVAILABLE (no open TableSession).
        - Order must be in an open state (DRAFT or CONFIRMED).
        - Destination table must be in the same branch.
    """
    from orders.models import TableSessionStatus
    from operations.models import TableTransfer, OperationsAuditLog

    source_table = order.table
    if not source_table:
        raise TableTransferConflict(
            "This order is not a DINE_IN order — no table to transfer."
        )

    if destination_table.branch_id != order.branch_id:
        raise TableTransferConflict(
            "Destination table must be in the same branch as the order."
        )

    # Check destination availability
    dest_op_status = get_table_operational_status(destination_table)
    has_open_session = destination_table.sessions.filter(
        status=TableSessionStatus.OPEN
    ).exists()

    if has_open_session or dest_op_status.status == TABLE_OP_OCCUPIED:
        raise TableNotAvailable(
            f"Table '{destination_table.table_number}' is currently occupied."
        )

    if order.status in ("CANCELLED",):
        raise TableTransferConflict(
            f"Cannot transfer a {order.status} order."
        )

    with transaction.atomic():
        transfer = TableTransfer.objects.create(
            source_table=source_table,
            destination_table=destination_table,
            order=order,
            requested_by=requested_by,
            status=TRANSFER_REQUESTED,
            reason=reason,
        )

        OperationsAuditLog.objects.create(
            actor=requested_by,
            event_type=AUDIT_TABLE_TRANSFER_REQUESTED,
            branch=order.branch,
            order_id=order.id,
            table_id=destination_table.id,
            metadata={
                "source_table": source_table.table_number,
                "destination_table": destination_table.table_number,
                "transfer_id": str(transfer.id),
            },
        )

    return transfer


def complete_table_transfer(*, transfer, approver):
    """
    Complete a table transfer by moving the order to the destination table.

    Concurrency: select_for_update() on both tables.
    """
    from orders.models import TableSession, TableSessionStatus, DiningTable
    from operations.models import OperationsAuditLog, TableOperationalStatus

    if transfer.status != TRANSFER_REQUESTED:
        raise TableTransferConflict(
            f"Transfer is in status '{transfer.status}' — cannot complete."
        )

    with transaction.atomic():
        # Lock both tables
        source = (
            DiningTable.objects
            .select_for_update()
            .get(pk=transfer.source_table_id)
        )
        dest = (
            DiningTable.objects
            .select_for_update()
            .get(pk=transfer.destination_table_id)
        )

        # Re-check destination is still available
        if dest.sessions.filter(status=TableSessionStatus.OPEN).exists():
            raise TableNotAvailable(
                f"Table '{dest.table_number}' is now occupied. Transfer cancelled."
            )

        order = transfer.order
        old_table = order.table
        old_session = order.table_session

        # Open a new session on the destination table
        new_session = TableSession.objects.create(
            table=dest,
            opened_by=approver,
            guest_count=old_session.guest_count if old_session else 1,
            notes=f"Transferred from table {source.table_number}",
        )

        # Update the order
        order.table = dest
        order.table_session = new_session
        order.save(update_fields=["table", "table_session", "updated_at"])

        # Close old session if no other orders reference it
        if old_session:
            remaining = old_session.orders.filter(
                status__in=["DRAFT", "CONFIRMED"]
            ).count()
            if remaining == 0:
                old_session.status = TableSessionStatus.CLOSED
                old_session.closed_at = timezone.now()
                old_session.closed_by = approver
                old_session.save(
                    update_fields=["status", "closed_at", "closed_by", "updated_at"]
                )

        # Update table operational statuses
        TableOperationalStatus.objects.filter(table=dest).update(
            status=TABLE_OP_OCCUPIED
        )

        # Mark transfer complete
        transfer.status = TRANSFER_COMPLETED
        transfer.approved_by = approver
        transfer.completed_at = timezone.now()
        transfer.save(
            update_fields=["status", "approved_by", "completed_at", "updated_at"]
        )

        OperationsAuditLog.objects.create(
            actor=approver,
            event_type=AUDIT_TABLE_TRANSFER_COMPLETED,
            branch=order.branch,
            order_id=order.id,
            table_id=dest.id,
            old_value=source.table_number,
            new_value=dest.table_number,
            metadata={"transfer_id": str(transfer.id)},
        )

    return transfer


def request_table_merge(*, source_tables, destination_table, requested_by, branch, reason=""):
    """
    Request merging of multiple tables for a large group.
    """
    from operations.models import TableMerge, OperationsAuditLog

    if destination_table not in source_tables:
        source_tables = list(source_tables) + [destination_table]

    for t in source_tables:
        if t.branch_id != branch.id:
            raise TableMergeConflict(
                "All tables must belong to the same branch."
            )

    with transaction.atomic():
        merge = TableMerge.objects.create(
            restaurant=branch.restaurant,
            branch=branch,
            destination_table=destination_table,
            requested_by=requested_by,
            status=MERGE_REQUESTED,
            reason=reason,
        )
        merge.source_tables.set(source_tables)

        OperationsAuditLog.objects.create(
            actor=requested_by,
            event_type=AUDIT_TABLE_MERGED,
            branch=branch,
            table_id=destination_table.id,
            metadata={
                "merge_id": str(merge.id),
                "source_tables": [t.table_number for t in source_tables],
                "destination_table": destination_table.table_number,
            },
        )

    return merge


def close_table(*, table, user, branch):
    """
    Close a table after the bill has been paid and guests have left.

    Sets operational status to AVAILABLE.
    Closes any open TableSession that has no unpaid orders.
    """
    from orders.models import TableSession, TableSessionStatus
    from operations.models import TableOperationalStatus

    with transaction.atomic():
        # Check no unpaid orders remain
        open_session = table.sessions.filter(
            status=TableSessionStatus.OPEN
        ).first()

        if open_session:
            active_orders = open_session.orders.filter(
                status__in=["DRAFT", "CONFIRMED"]
            ).count()
            if active_orders > 0:
                raise TableTransferConflict(
                    "Cannot close table — there are still active orders."
                )

            # Check all bills are paid
            from billing.models import Bill, BillStatus
            unpaid_bills = Bill.objects.filter(
                order__table_session=open_session,
                status=BillStatus.FINALIZED,
            ).exclude(
                order__in=open_session.orders.filter(
                    status="CANCELLED"
                )
            )
            for bill in unpaid_bills:
                paid = bill.payments.filter(status="COMPLETED").exists()
                if not paid:
                    raise TableTransferConflict(
                        f"Bill {bill.bill_number} is not yet paid."
                    )

            open_session.status = TableSessionStatus.CLOSED
            open_session.closed_at = timezone.now()
            open_session.closed_by = user
            open_session.save(
                update_fields=["status", "closed_at", "closed_by", "updated_at"]
            )

        # Set operational status to AVAILABLE
        TableOperationalStatus.objects.filter(table=table).update(
            status=TABLE_OP_AVAILABLE
        )

    return table
