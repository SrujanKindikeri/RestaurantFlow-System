# =============================================================================
# RestaurantFlow — Order Services (Phase 19 extensions)
# Phase 19: Advanced POS & Restaurant Operations
#
# Extends existing Order workflow with:
#   - Hold / Resume
#   - Priority changes
#   - Waiter assignment
#   - Order change requests
#   - Order merging
#   - Item modifier management
# =============================================================================

import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from operations.constants import (
    CHANGE_STATUS_PENDING, CHANGE_STATUS_APPROVED,
    CHANGE_STATUS_REJECTED, CHANGE_STATUS_CANCELLED,
    ORDER_MERGE_PENDING, ORDER_MERGE_COMPLETED, ORDER_MERGE_REJECTED,
    ORDER_MERGE_CANCELLED,
    AUDIT_ORDER_HELD, AUDIT_ORDER_RESUMED, AUDIT_ORDER_PRIORITY_CHANGED,
    AUDIT_ORDER_CHANGE_REQUESTED, AUDIT_ORDER_CHANGE_APPROVED,
    AUDIT_ORDER_CHANGE_REJECTED, AUDIT_ORDER_MERGED,
    AUDIT_MODIFIER_ADDED, AUDIT_MODIFIER_REMOVED,
    AUDIT_WAITER_ASSIGNED,
)
from operations.exceptions import (
    OrderStateConflict, OrderMergeConflict, IncompatibleOrders,
    ModifierValidationError,
)

logger = logging.getLogger("operations")

# Sentinel value representing the ON_HOLD extension to Order.status
ORDER_STATUS_ON_HOLD = "ON_HOLD"


def hold_order(*, order, user):
    """
    Put a DRAFT order on hold.

    A held order preserves all items, customer, table, counter, notes,
    waiter, and created_by. It can be resumed later.
    """
    from orders.models import OrderStatus
    from operations.models import OperationsAuditLog

    if order.status not in (OrderStatus.DRAFT, ORDER_STATUS_ON_HOLD):
        raise OrderStateConflict(
            f"Cannot hold an order with status '{order.status}'. "
            "Only DRAFT orders can be held."
        )

    with transaction.atomic():
        order.status = ORDER_STATUS_ON_HOLD
        order.save(update_fields=["status", "updated_at"])

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_ORDER_HELD,
            branch=order.branch,
            order_id=order.id,
            old_value="DRAFT",
            new_value=ORDER_STATUS_ON_HOLD,
        )

    return order


def resume_order(*, order, user):
    """Resume an ON_HOLD order back to DRAFT."""
    from operations.models import OperationsAuditLog

    if order.status != ORDER_STATUS_ON_HOLD:
        raise OrderStateConflict(
            f"Cannot resume an order with status '{order.status}'. "
            "Only ON_HOLD orders can be resumed."
        )

    with transaction.atomic():
        order.status = "DRAFT"
        order.save(update_fields=["status", "updated_at"])

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_ORDER_RESUMED,
            branch=order.branch,
            order_id=order.id,
            old_value=ORDER_STATUS_ON_HOLD,
            new_value="DRAFT",
        )

    return order


def set_order_priority(*, order, priority, user):
    """
    Change the kitchen priority for a confirmed order.

    URGENT priority requires pos.order.priority.urgent permission.
    Permission check is done in the view layer.
    """
    from kitchen.models import KitchenPriority
    from operations.models import OperationsAuditLog

    valid = [p[0] for p in KitchenPriority.choices]
    if priority not in valid:
        raise OrderStateConflict(f"Invalid priority '{priority}'. Choose from {valid}.")

    with transaction.atomic():
        # Update kitchen order if it exists
        try:
            kitchen_order = order.kitchen_order
            old_priority = kitchen_order.priority
            kitchen_order.priority = priority
            kitchen_order.save(update_fields=["priority", "updated_at"])
        except Exception:
            old_priority = "NONE"

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_ORDER_PRIORITY_CHANGED,
            branch=order.branch,
            order_id=order.id,
            old_value=old_priority,
            new_value=priority,
        )

    return order


def assign_waiter(*, order, waiter, user):
    """
    Assign or reassign a waiter to an order.

    Waiter must belong to the same restaurant and authorized branch.
    Validation of waiter scope is enforced here.
    """
    from accounts.models import UserRoleAssignment, Role
    from operations.models import OperationsAuditLog

    # Validate waiter belongs to same branch
    waiter_branches = UserRoleAssignment.objects.filter(
        user=waiter,
        is_active=True,
        branch=order.branch,
    ).exists()
    # Also allow restaurant-scope assignments
    waiter_restaurant = UserRoleAssignment.objects.filter(
        user=waiter,
        is_active=True,
        restaurant=order.branch.restaurant,
    ).exists()

    if not waiter_branches and not waiter_restaurant and not waiter.is_superuser:
        raise OrderStateConflict(
            "The assigned waiter does not belong to this branch or restaurant."
        )

    with transaction.atomic():
        old_waiter_email = (
            order.assigned_waiter.email if order.assigned_waiter else "None"
        )
        order.assigned_waiter = waiter
        order.save(update_fields=["assigned_waiter", "updated_at"])

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_WAITER_ASSIGNED,
            branch=order.branch,
            order_id=order.id,
            old_value=old_waiter_email,
            new_value=waiter.email,
        )

    return order


def create_order_change_request(*, order, requested_by, change_type, reason, requested_data):
    """
    Submit a change request for a CONFIRMED order.

    DRAFT orders should be edited directly through the order service.
    This workflow is for orders that are already in the kitchen.
    """
    from orders.models import OrderStatus
    from operations.models import OrderChangeRequest, OperationsAuditLog

    if order.status == "DRAFT":
        raise OrderStateConflict(
            "DRAFT orders can be edited directly. "
            "OrderChangeRequest is for CONFIRMED orders."
        )
    if order.status == "CANCELLED":
        raise OrderStateConflict("Cannot create a change request for a CANCELLED order.")

    with transaction.atomic():
        change_request = OrderChangeRequest.objects.create(
            order=order,
            requested_by=requested_by,
            change_type=change_type,
            reason=reason,
            requested_data=requested_data,
            status=CHANGE_STATUS_PENDING,
        )

        OperationsAuditLog.objects.create(
            actor=requested_by,
            event_type=AUDIT_ORDER_CHANGE_REQUESTED,
            branch=order.branch,
            order_id=order.id,
            new_value=change_type,
            metadata={"change_request_id": str(change_request.id)},
        )

    return change_request


def approve_order_change_request(*, change_request, approver, review_note=""):
    """
    Approve an OrderChangeRequest and apply the change.

    Approver must NOT be the same as requested_by.
    """
    from operations.models import OperationsAuditLog

    if change_request.status != CHANGE_STATUS_PENDING:
        raise OrderStateConflict(
            f"Cannot approve a change request in status '{change_request.status}'."
        )
    if change_request.requested_by_id == approver.id:
        raise OrderStateConflict(
            "You cannot approve your own change request."
        )

    with transaction.atomic():
        change_request.status = CHANGE_STATUS_APPROVED
        change_request.approved_by = approver
        change_request.approved_at = timezone.now()
        change_request.review_note = review_note
        change_request.save(
            update_fields=["status", "approved_by", "approved_at", "review_note", "updated_at"]
        )

        # Apply the change
        _apply_order_change(change_request)

        OperationsAuditLog.objects.create(
            actor=approver,
            event_type=AUDIT_ORDER_CHANGE_APPROVED,
            branch=change_request.order.branch,
            order_id=change_request.order.id,
            new_value=change_request.change_type,
            metadata={"change_request_id": str(change_request.id)},
        )

    return change_request


def reject_order_change_request(*, change_request, reviewer, review_note=""):
    """Reject a pending OrderChangeRequest."""
    from operations.models import OperationsAuditLog

    if change_request.status != CHANGE_STATUS_PENDING:
        raise OrderStateConflict(
            f"Cannot reject a change request in status '{change_request.status}'."
        )

    with transaction.atomic():
        change_request.status = CHANGE_STATUS_REJECTED
        change_request.approved_by = reviewer
        change_request.rejected_at = timezone.now()
        change_request.review_note = review_note
        change_request.save(
            update_fields=["status", "approved_by", "rejected_at", "review_note", "updated_at"]
        )

        OperationsAuditLog.objects.create(
            actor=reviewer,
            event_type=AUDIT_ORDER_CHANGE_REJECTED,
            branch=change_request.order.branch,
            order_id=change_request.order.id,
            metadata={"change_request_id": str(change_request.id)},
        )

    return change_request


def _apply_order_change(change_request):
    """Internal: apply an approved OrderChangeRequest to the Order."""
    from orders.models import OrderItem
    from operations.constants import (
        CHANGE_ADD_ITEM, CHANGE_REMOVE_ITEM, CHANGE_QUANTITY,
        CHANGE_NOTE, CHANGE_WAITER, CHANGE_CUSTOMER, CHANGE_TABLE,
    )

    order = change_request.order
    data = change_request.requested_data
    ct = change_request.change_type

    if ct == CHANGE_NOTE:
        order.notes = data.get("notes", order.notes)
        order.save(update_fields=["notes", "updated_at"])

    elif ct == CHANGE_WAITER:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        waiter_id = data.get("waiter_id")
        if waiter_id:
            try:
                waiter = User.objects.get(pk=waiter_id)
                order.assigned_waiter = waiter
                order.save(update_fields=["assigned_waiter", "updated_at"])
            except User.DoesNotExist:
                pass

    elif ct == CHANGE_CUSTOMER:
        from crm.models import Customer
        customer_id = data.get("customer_id")
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                order.customer = customer
                order.save(update_fields=["customer", "updated_at"])
            except Customer.DoesNotExist:
                pass

    elif ct == CHANGE_QUANTITY:
        order_item_id = data.get("order_item_id")
        new_quantity = Decimal(str(data.get("quantity", 1)))
        if order_item_id and new_quantity > 0:
            OrderItem.objects.filter(
                pk=order_item_id, order=order
            ).update(quantity=new_quantity)

    elif ct == CHANGE_REMOVE_ITEM:
        order_item_id = data.get("order_item_id")
        if order_item_id:
            OrderItem.objects.filter(
                pk=order_item_id, order=order
            ).delete()


def merge_orders(*, merge_request, approver):
    """
    Execute an approved OrderMergeRequest.

    Moves all items from source orders to the destination order.
    Source orders are cancelled after successful merge.
    """
    from orders.models import OrderStatus, OrderItem
    from operations.models import OperationsAuditLog

    if merge_request.status != ORDER_MERGE_PENDING:
        raise OrderMergeConflict(
            f"Cannot process a merge request in status '{merge_request.status}'."
        )

    destination = merge_request.destination_order
    sources = list(merge_request.source_orders.select_for_update().all())

    # Validate all sources
    for src in sources:
        if src.pk == destination.pk:
            continue
        if src.status in ("CANCELLED",):
            raise IncompatibleOrders(
                f"Order {src.order_number} is CANCELLED and cannot be merged."
            )
        if src.branch_id != destination.branch_id:
            raise IncompatibleOrders(
                "Orders from different branches cannot be merged."
            )
        # Check if it has a bill already
        if hasattr(src, "bill"):
            raise IncompatibleOrders(
                f"Order {src.order_number} already has a bill and cannot be merged."
            )

    with transaction.atomic():
        # Move items from sources to destination
        for src in sources:
            if src.pk == destination.pk:
                continue
            OrderItem.objects.filter(order=src).update(order=destination)
            src.status = "CANCELLED"
            src.cancellation_reason = (
                f"Merged into order {destination.order_number} "
                f"by {approver.email}"
            )
            src.cancelled_at = timezone.now()
            src.cancelled_by = approver
            src.save(
                update_fields=[
                    "status", "cancellation_reason",
                    "cancelled_at", "cancelled_by", "updated_at",
                ]
            )

        merge_request.status = ORDER_MERGE_COMPLETED
        merge_request.approved_by = approver
        merge_request.completed_at = timezone.now()
        merge_request.save(
            update_fields=["status", "approved_by", "completed_at", "updated_at"]
        )

        OperationsAuditLog.objects.create(
            actor=approver,
            event_type=AUDIT_ORDER_MERGED,
            branch=destination.branch,
            order_id=destination.id,
            metadata={
                "merge_request_id": str(merge_request.id),
                "source_orders": [str(s.id) for s in sources],
            },
        )

    return merge_request


def add_item_modifier(*, order_item, modifier_option_id=None, name, value, user):
    """
    Add a modifier to an OrderItem.

    If modifier_option_id is provided, price_adjustment is taken from the DB record.
    Frontend-submitted price_adjustment is NEVER trusted.
    """
    from operations.models import OrderItemModifier, MenuModifierOption, OperationsAuditLog

    price_adjustment = Decimal("0.00")

    if modifier_option_id:
        try:
            option = MenuModifierOption.objects.get(
                pk=modifier_option_id, is_active=True
            )
            price_adjustment = option.price_adjustment
            name = name or option.modifier_group.name
            value = value or option.name
        except MenuModifierOption.DoesNotExist:
            raise ModifierValidationError(
                f"Modifier option '{modifier_option_id}' not found or inactive."
            )

    with transaction.atomic():
        modifier = OrderItemModifier.objects.create(
            order_item=order_item,
            modifier_option_id=modifier_option_id,
            name=name,
            value=value,
            price_adjustment=price_adjustment,
        )

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_MODIFIER_ADDED,
            branch=order_item.order.branch,
            order_id=order_item.order.id,
            metadata={
                "order_item_id": str(order_item.id),
                "modifier_name": name,
                "modifier_value": value,
            },
        )

    return modifier


def remove_item_modifier(*, modifier, user):
    """Remove an OrderItemModifier."""
    from operations.models import OperationsAuditLog

    branch = modifier.order_item.order.branch
    order_id = modifier.order_item.order.id
    meta = {"modifier_name": modifier.name, "modifier_value": modifier.value}

    with transaction.atomic():
        modifier.delete()

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_MODIFIER_REMOVED,
            branch=branch,
            order_id=order_id,
            metadata=meta,
        )


def mark_order_served(*, order, served_by):
    """Mark an order as served (fulfillment status = SERVED)."""
    from operations.models import OrderFulfillmentStatus
    from operations.constants import FULFILLMENT_READY, FULFILLMENT_SERVED

    fulfillment, _ = OrderFulfillmentStatus.objects.get_or_create(
        order=order,
        defaults={"status": FULFILLMENT_READY},
    )

    with transaction.atomic():
        fulfillment.status = FULFILLMENT_SERVED
        fulfillment.served_by = served_by
        fulfillment.served_at = timezone.now()
        fulfillment.save(
            update_fields=["status", "served_by", "served_at", "updated_at"]
        )

    return fulfillment
