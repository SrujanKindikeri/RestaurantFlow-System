# =============================================================================
# RestaurantFlow — Bill Services (Phase 19: Split)
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.utils import timezone

from operations.constants import (
    SPLIT_DRAFT, SPLIT_FINALIZED, SPLIT_CANCELLED,
    SPLIT_ITEM, SPLIT_QUANTITY, SPLIT_EQUAL, SPLIT_GUEST,
    AUDIT_BILL_SPLIT_CREATED, AUDIT_BILL_SPLIT_FINALIZED,
)
from operations.exceptions import BillSplitConflict, BillNotSplittable

logger = logging.getLogger("operations")


def create_bill_split(*, bill, split_type, requested_by, num_splits=2, item_allocations=None):
    """
    Create BillSplit records for a finalized bill.

    bill must be FINALIZED — cannot split DRAFT or CANCELLED bills.
    Concurrency: select_for_update() on the bill.

    split_type:
        EQUAL    — divide grand_total equally into num_splits parts
        ITEM     — item_allocations = [{split_number, bill_item_id, quantity, amount}]
        QUANTITY — item_allocations same structure with fractional quantities
        GUEST    — similar to EQUAL but labeled per guest

    Returns list of created BillSplit objects.
    """
    from billing.models import Bill, BillStatus, BillItem
    from operations.models import BillSplit, BillSplitItem, OperationsAuditLog

    with transaction.atomic():
        # Lock the bill
        bill = Bill.objects.select_for_update().get(pk=bill.pk)

        if bill.status != BillStatus.FINALIZED:
            raise BillNotSplittable(
                f"Only FINALIZED bills can be split. Current status: {bill.status}"
            )

        # Check no existing DRAFT/FINALIZED splits
        existing = bill.splits.filter(
            status__in=[SPLIT_DRAFT, SPLIT_FINALIZED]
        ).count()
        if existing > 0:
            raise BillSplitConflict(
                "This bill already has active splits. "
                "Cancel them before creating new splits."
            )

        splits = []

        if split_type in (SPLIT_EQUAL, SPLIT_GUEST):
            # Equal division
            per_split = (
                bill.grand_total / Decimal(str(num_splits))
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Adjust last split for rounding
            remaining = bill.grand_total
            for i in range(1, num_splits + 1):
                amount = per_split if i < num_splits else remaining
                split = BillSplit.objects.create(
                    bill=bill,
                    split_number=i,
                    split_type=split_type,
                    amount=amount,
                    status=SPLIT_DRAFT,
                    created_by=requested_by,
                )
                splits.append(split)
                remaining -= per_split

        elif split_type in (SPLIT_ITEM, SPLIT_QUANTITY):
            if not item_allocations:
                raise BillSplitConflict(
                    "item_allocations is required for ITEM and QUANTITY splits."
                )

            # Group allocations by split_number
            split_groups: dict = {}
            for alloc in item_allocations:
                sn = alloc["split_number"]
                split_groups.setdefault(sn, []).append(alloc)

            # Validate allocations don't exceed bill item quantities
            _validate_split_allocations(bill, item_allocations)

            for split_number, allocs in sorted(split_groups.items()):
                split_amount = sum(
                    Decimal(str(a["amount"])) for a in allocs
                )
                split = BillSplit.objects.create(
                    bill=bill,
                    split_number=split_number,
                    split_type=split_type,
                    amount=split_amount,
                    status=SPLIT_DRAFT,
                    created_by=requested_by,
                )
                # Create split items
                for alloc in allocs:
                    bill_item = BillItem.objects.get(pk=alloc["bill_item_id"])
                    BillSplitItem.objects.create(
                        bill_split=split,
                        bill_item=bill_item,
                        quantity=Decimal(str(alloc["quantity"])),
                        amount=Decimal(str(alloc["amount"])),
                    )
                splits.append(split)

        OperationsAuditLog.objects.create(
            actor=requested_by,
            event_type=AUDIT_BILL_SPLIT_CREATED,
            bill_id=bill.id,
            branch=bill.branch,
            metadata={
                "split_type": split_type,
                "num_splits": len(splits),
                "split_ids": [str(s.id) for s in splits],
            },
        )

    return splits


def _validate_split_allocations(bill, allocations):
    """
    Validate that item allocations don't over-allocate bill items.
    """
    from billing.models import BillItem

    # Build a map of bill_item_id → max quantity / amount
    item_totals: dict = {}
    for alloc in allocations:
        bid = str(alloc["bill_item_id"])
        qty = Decimal(str(alloc.get("quantity", 0)))
        amt = Decimal(str(alloc.get("amount", 0)))
        if bid not in item_totals:
            item_totals[bid] = {"quantity": Decimal("0"), "amount": Decimal("0")}
        item_totals[bid]["quantity"] += qty
        item_totals[bid]["amount"] += amt

    for bid_str, totals in item_totals.items():
        try:
            bill_item = bill.items.get(pk=bid_str)
        except Exception:
            raise BillSplitConflict(
                f"BillItem '{bid_str}' does not belong to this bill."
            )

        if totals["quantity"] > bill_item.quantity:
            raise BillSplitConflict(
                f"Split quantity {totals['quantity']} exceeds "
                f"bill item quantity {bill_item.quantity} "
                f"for item '{bill_item.item_name_snapshot}'."
            )

        if totals["amount"] > bill_item.total_amount + Decimal("0.01"):
            raise BillSplitConflict(
                f"Split amount {totals['amount']} exceeds "
                f"bill item total {bill_item.total_amount} "
                f"for item '{bill_item.item_name_snapshot}'."
            )


def finalize_bill_split(*, bill_split, user):
    """
    Finalize a BillSplit — lock it for payment.
    """
    from operations.models import OperationsAuditLog

    if bill_split.status != SPLIT_DRAFT:
        raise BillSplitConflict(
            f"Cannot finalize a split in status '{bill_split.status}'."
        )

    with transaction.atomic():
        bill_split.status = SPLIT_FINALIZED
        bill_split.save(update_fields=["status", "updated_at"])

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_BILL_SPLIT_FINALIZED,
            bill_id=bill_split.bill_id,
            branch=bill_split.bill.branch,
            metadata={"split_id": str(bill_split.id), "amount": str(bill_split.amount)},
        )

    return bill_split


def cancel_bill_split(*, bill_split, user):
    """Cancel a DRAFT BillSplit."""
    if bill_split.status != SPLIT_DRAFT:
        raise BillSplitConflict(
            f"Cannot cancel a split in status '{bill_split.status}'."
        )

    with transaction.atomic():
        bill_split.status = SPLIT_CANCELLED
        bill_split.save(update_fields=["status", "updated_at"])

    return bill_split
