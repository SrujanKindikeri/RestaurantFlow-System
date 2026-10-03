# =============================================================================
# RestaurantFlow — Kitchen Services
# Phase 7: Kitchen Display System
#
# All business logic for kitchen order lifecycle lives here.
# Views and signals call these functions; serializers handle I/O shapes only.
#
# Public API:
#   send_order_to_kitchen(order)                    → KitchenOrder
#   accept_kitchen_order(actor, kitchen_order)      → KitchenOrder
#   start_preparation(actor, kitchen_order)         → KitchenOrder
#   mark_order_ready(actor, kitchen_order)          → KitchenOrder
#   cancel_kitchen_order(actor, kitchen_order, reason) → KitchenOrder
#   start_item_preparation(actor, kitchen_item)     → KitchenOrderItem
#   mark_item_ready(actor, kitchen_item)            → KitchenOrderItem
#   update_kitchen_priority(actor, kitchen_order, priority) → KitchenOrder
#   publish_kitchen_event(event_type, kitchen_order, **extra) → None
#
# Concurrency:
#   All state transitions use select_for_update() + transaction.atomic()
#   to prevent simultaneous double-clicks from corrupting state.
#
# Event ordering:
#   Database is committed BEFORE any WebSocket event is published.
#   If Redis is unavailable, the DB state is still correct and the KDS
#   can recover via REST polling on reconnect.
#
# Security:
#   Every mutating service function checks permissions and branch access.
#   Kitchen does NOT handle pricing, payments, billing, or refunds.
# =============================================================================

import uuid
import logging

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl

logger = logging.getLogger("kitchen")


# =============================================================================
# Internal helpers
# =============================================================================

def _require_auth(user):
    """Raise PermissionDenied if user is not authenticated and active."""
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


def _check_kitchen_branch_access(user, kitchen_order):
    """Raise PermissionDenied if user cannot access this kitchen order's branch."""
    if not acl.can_access_branch(user, kitchen_order.branch):
        raise PermissionDenied(
            "You do not have access to this kitchen order's branch."
        )


def _transition_error(current: str, target: str) -> ValidationError:
    return ValidationError(
        {
            "code": "INVALID_KITCHEN_TRANSITION",
            "message": (
                f"Cannot transition kitchen order from {current} to {target}. "
                "This transition is not permitted."
            ),
        }
    )


def _item_transition_error(current: str, target: str) -> ValidationError:
    return ValidationError(
        {
            "code": "INVALID_ITEM_TRANSITION",
            "message": (
                f"Cannot transition kitchen item from {current} to {target}. "
                "This transition is not permitted."
            ),
        }
    )


# =============================================================================
# 1. send_order_to_kitchen
# =============================================================================

def send_order_to_kitchen(order) -> "KitchenOrder":
    """
    Create a KitchenOrder (and KitchenOrderItems) for a confirmed Order.

    This is called automatically when an Order transitions to CONFIRMED,
    either from the signal handler or directly from order confirmation flow.

    Rules:
        - Order must be CONFIRMED (not DRAFT or CANCELLED).
        - A KitchenOrder must not already exist for this order (idempotent
          protection: if called twice, returns the existing record).
        - KitchenOrder.branch is copied from Order.branch.
        - KitchenOrderItem snapshots are copied from OrderItem (name, quantity,
          notes, food_type, preparation_time_minutes).
        - Financial fields (price, tax) are intentionally NOT copied.

    This function is designed to be called inside the same transaction as
    order confirmation when possible.  If called standalone (e.g. from signal),
    it wraps its own transaction.

    Returns the KitchenOrder (newly created or pre-existing).
    """
    from orders.models import OrderStatus
    from kitchen.models import (
        KitchenOrder, KitchenOrderItem,
        KitchenOrderStatus, KitchenItemStatus,
    )

    # Idempotency: if kitchen order already exists, return it
    try:
        existing = KitchenOrder.objects.get(order=order)
        logger.info(
            "send_order_to_kitchen: KitchenOrder already exists for order=%s — returning existing",
            order.order_number,
        )
        return existing
    except KitchenOrder.DoesNotExist:
        pass

    # Guard: only CONFIRMED orders enter the kitchen
    if order.status != OrderStatus.CONFIRMED:
        raise ValidationError(
            {
                "code": "ORDER_NOT_CONFIRMED",
                "message": (
                    f"Order {order.order_number} has status '{order.status}'. "
                    "Only CONFIRMED orders can be sent to the kitchen."
                ),
            }
        )

    # Guard: order must have items
    items = list(
        order.items.select_related("menu_item").all()
    )
    if not items:
        raise ValidationError(
            {
                "code": "ORDER_EMPTY",
                "message": (
                    f"Order {order.order_number} has no items. "
                    "Cannot create a kitchen order for an empty order."
                ),
            }
        )

    with transaction.atomic():
        kitchen_order = KitchenOrder.objects.create(
            order=order,
            branch=order.branch,
            status=KitchenOrderStatus.NEW,
        )

        kitchen_items = []
        for order_item in items:
            menu_item = order_item.menu_item
            kitchen_items.append(
                KitchenOrderItem(
                    kitchen_order=kitchen_order,
                    order_item=order_item,
                    menu_item=menu_item,
                    # Snapshots from OrderItem — never overwritten
                    item_name_snapshot=order_item.item_name_snapshot,
                    quantity=order_item.quantity,
                    notes=order_item.notes,
                    # Additional snapshots from MenuItem
                    food_type=menu_item.food_type,
                    preparation_time_minutes=menu_item.preparation_time_minutes,
                    status=KitchenItemStatus.NEW,
                )
            )
        KitchenOrderItem.objects.bulk_create(kitchen_items)

    logger.info(
        "send_order_to_kitchen: created KitchenOrder id=%s for order=%s branch=%s items=%d",
        kitchen_order.id,
        order.order_number,
        order.branch.name,
        len(items),
    )
    return kitchen_order


# =============================================================================
# 2. accept_kitchen_order
# =============================================================================

def accept_kitchen_order(actor, *, kitchen_order) -> "KitchenOrder":
    """
    Transition KitchenOrder: NEW → ACCEPTED.

    Idempotent: if already ACCEPTED by this transition logic (concurrent
    double-click), the state check inside select_for_update will detect it
    and raise a validation error — the client can safely retry a GET.

    Permission required: kitchen.accept
    """
    from kitchen.models import KitchenOrder, KitchenOrderStatus

    _require_auth(actor)

    if not acl.has_permission(actor, "kitchen.accept"):
        raise PermissionDenied("You do not have permission to accept kitchen orders.")

    _check_kitchen_branch_access(actor, kitchen_order)

    with transaction.atomic():
        locked = KitchenOrder.objects.select_for_update().get(pk=kitchen_order.pk)

        # Idempotency: already accepted
        if locked.status == KitchenOrderStatus.ACCEPTED:
            logger.info(
                "accept_kitchen_order: order=%s already ACCEPTED — idempotent return",
                locked.order_number,
            )
            return locked

        if not locked.can_transition_to(KitchenOrderStatus.ACCEPTED):
            raise _transition_error(locked.status, KitchenOrderStatus.ACCEPTED)

        locked.status = KitchenOrderStatus.ACCEPTED
        locked.accepted_at = timezone.now()
        locked.accepted_by = actor
        locked.save(update_fields=["status", "accepted_at", "accepted_by", "updated_at"])

    logger.info(
        "accept_kitchen_order: order=%s ACCEPTED by user=%s",
        locked.order_number, actor.email,
    )

    # Publish after commit
    publish_kitchen_event("kitchen.order.accepted", locked)
    return locked


# =============================================================================
# 3. start_preparation
# =============================================================================

def start_preparation(actor, *, kitchen_order) -> "KitchenOrder":
    """
    Transition KitchenOrder: ACCEPTED → PREPARING.
    Also transitions all NEW items to PREPARING.

    Permission required: kitchen.start
    """
    from kitchen.models import (
        KitchenOrder, KitchenOrderItem,
        KitchenOrderStatus, KitchenItemStatus,
    )

    _require_auth(actor)

    if not acl.has_permission(actor, "kitchen.start"):
        raise PermissionDenied("You do not have permission to start kitchen preparation.")

    _check_kitchen_branch_access(actor, kitchen_order)

    with transaction.atomic():
        locked = KitchenOrder.objects.select_for_update().get(pk=kitchen_order.pk)

        # Idempotency
        if locked.status == KitchenOrderStatus.PREPARING:
            logger.info(
                "start_preparation: order=%s already PREPARING — idempotent return",
                locked.order_number,
            )
            return locked

        if not locked.can_transition_to(KitchenOrderStatus.PREPARING):
            raise _transition_error(locked.status, KitchenOrderStatus.PREPARING)

        now = timezone.now()

        locked.status = KitchenOrderStatus.PREPARING
        locked.started_at = now
        locked.started_by = actor
        locked.save(update_fields=["status", "started_at", "started_by", "updated_at"])

        # Transition all NEW items to PREPARING atomically
        KitchenOrderItem.objects.filter(
            kitchen_order=locked,
            status=KitchenItemStatus.NEW,
        ).update(status=KitchenItemStatus.PREPARING, started_at=now, updated_at=now)

    logger.info(
        "start_preparation: order=%s PREPARING by user=%s",
        locked.order_number, actor.email,
    )

    publish_kitchen_event("kitchen.order.preparing", locked)
    return locked


# =============================================================================
# 4. mark_order_ready
# =============================================================================

def mark_order_ready(actor, *, kitchen_order) -> "KitchenOrder":
    """
    Transition KitchenOrder: PREPARING → READY.

    Validates that all non-cancelled KitchenOrderItems are READY before
    allowing the order to be marked ready.

    Permission required: kitchen.order_ready
    """
    from kitchen.models import (
        KitchenOrder, KitchenOrderStatus, KitchenItemStatus,
    )

    _require_auth(actor)

    if not acl.has_permission(actor, "kitchen.order_ready"):
        raise PermissionDenied("You do not have permission to mark orders as ready.")

    _check_kitchen_branch_access(actor, kitchen_order)

    with transaction.atomic():
        locked = KitchenOrder.objects.select_for_update().get(pk=kitchen_order.pk)

        # Idempotency
        if locked.status == KitchenOrderStatus.READY:
            logger.info(
                "mark_order_ready: order=%s already READY — idempotent return",
                locked.order_number,
            )
            return locked

        if not locked.can_transition_to(KitchenOrderStatus.READY):
            raise _transition_error(locked.status, KitchenOrderStatus.READY)

        # Check all active items are ready
        non_ready_count = locked.items.filter(
            status__in=[KitchenItemStatus.NEW, KitchenItemStatus.PREPARING]
        ).count()
        if non_ready_count > 0:
            raise ValidationError(
                {
                    "code": "ITEMS_NOT_READY",
                    "message": (
                        f"{non_ready_count} item(s) are still being prepared. "
                        "All items must be READY or CANCELLED before marking the order ready."
                    ),
                }
            )

        now = timezone.now()
        locked.status = KitchenOrderStatus.READY
        locked.ready_at = now
        locked.completed_by = actor
        locked.save(update_fields=["status", "ready_at", "completed_by", "updated_at"])

    logger.info(
        "mark_order_ready: order=%s READY by user=%s",
        locked.order_number, actor.email,
    )

    publish_kitchen_event("kitchen.order.ready", locked)

    # Phase 11 — Trigger inventory consumption after kitchen order is READY.
    # Called outside the transaction so that DB state is fully committed before
    # consumption begins. Failure is non-fatal: the kitchen order remains READY.
    _trigger_inventory_consumption(locked, actor)

    return locked


# =============================================================================
# 5. cancel_kitchen_order
# =============================================================================

def cancel_kitchen_order(actor, *, kitchen_order, reason="") -> "KitchenOrder":
    """
    Cancel a KitchenOrder.

    Allowed from: NEW, ACCEPTED, PREPARING.
    READY and CANCELLED orders cannot be cancelled through this path.

    Cancelling from PREPARING requires kitchen.cancel permission (stronger).

    Permission required:
        - kitchen.cancel for NEW / ACCEPTED
        - kitchen.cancel (same code, but PREPARING state is noted in audit)
    """
    from kitchen.models import (
        KitchenOrder, KitchenOrderItem,
        KitchenOrderStatus, KitchenItemStatus,
    )

    _require_auth(actor)

    if not acl.has_permission(actor, "kitchen.cancel"):
        raise PermissionDenied("You do not have permission to cancel kitchen orders.")

    _check_kitchen_branch_access(actor, kitchen_order)

    with transaction.atomic():
        locked = KitchenOrder.objects.select_for_update().get(pk=kitchen_order.pk)

        # Idempotency
        if locked.status == KitchenOrderStatus.CANCELLED:
            logger.info(
                "cancel_kitchen_order: order=%s already CANCELLED — idempotent return",
                locked.order_number,
            )
            return locked

        if not locked.can_transition_to(KitchenOrderStatus.CANCELLED):
            raise _transition_error(locked.status, KitchenOrderStatus.CANCELLED)

        now = timezone.now()
        locked.status = KitchenOrderStatus.CANCELLED
        locked.cancelled_at = now
        locked.cancelled_by = actor
        locked.cancellation_reason = reason or ""
        locked.save(update_fields=[
            "status", "cancelled_at", "cancelled_by",
            "cancellation_reason", "updated_at",
        ])

        # Cancel all non-terminal items
        KitchenOrderItem.objects.filter(
            kitchen_order=locked,
            status__in=[KitchenItemStatus.NEW, KitchenItemStatus.PREPARING],
        ).update(
            status=KitchenItemStatus.CANCELLED,
            cancelled_at=now,
            updated_at=now,
        )

    logger.info(
        "cancel_kitchen_order: order=%s CANCELLED by user=%s reason='%s'",
        locked.order_number, actor.email, reason,
    )

    publish_kitchen_event("kitchen.order.cancelled", locked)
    return locked


# =============================================================================
# 6. start_item_preparation
# =============================================================================

def start_item_preparation(actor, *, kitchen_item) -> "KitchenOrderItem":
    """
    Transition KitchenOrderItem: NEW → PREPARING.

    Allows individual item tracking when items are started independently
    (e.g. a beverage station starts the cold coffee before the grill starts).

    Permission required: kitchen.item_start
    """
    from kitchen.models import KitchenOrderItem, KitchenItemStatus

    _require_auth(actor)

    if not acl.has_permission(actor, "kitchen.item_start"):
        raise PermissionDenied("You do not have permission to start item preparation.")

    # Check branch access via parent kitchen order
    _check_kitchen_branch_access(actor, kitchen_item.kitchen_order)

    with transaction.atomic():
        locked_item = KitchenOrderItem.objects.select_for_update().get(pk=kitchen_item.pk)

        # Idempotency
        if locked_item.status == KitchenItemStatus.PREPARING:
            return locked_item

        if not locked_item.can_transition_to(KitchenItemStatus.PREPARING):
            raise _item_transition_error(locked_item.status, KitchenItemStatus.PREPARING)

        now = timezone.now()
        locked_item.status = KitchenItemStatus.PREPARING
        locked_item.started_at = now
        locked_item.save(update_fields=["status", "started_at", "updated_at"])

    logger.info(
        "start_item_preparation: item=%s order=%s PREPARING by user=%s",
        locked_item.item_name_snapshot,
        locked_item.kitchen_order.order_number,
        actor.email,
    )

    publish_kitchen_event(
        "kitchen.item.preparing",
        locked_item.kitchen_order,
        item_id=str(locked_item.id),
        item_name=locked_item.item_name_snapshot,
    )
    return locked_item


# =============================================================================
# 7. mark_item_ready
# =============================================================================

def mark_item_ready(actor, *, kitchen_item) -> "KitchenOrderItem":
    """
    Transition KitchenOrderItem: PREPARING → READY.

    After marking an item ready, checks if ALL non-cancelled items are now
    READY.  If so, automatically advances the parent KitchenOrder to READY
    if it is currently PREPARING.

    Permission required: kitchen.item_ready
    """
    from kitchen.models import (
        KitchenOrder, KitchenOrderItem,
        KitchenOrderStatus, KitchenItemStatus,
    )

    _require_auth(actor)

    if not acl.has_permission(actor, "kitchen.item_ready"):
        raise PermissionDenied("You do not have permission to mark items as ready.")

    _check_kitchen_branch_access(actor, kitchen_item.kitchen_order)

    with transaction.atomic():
        locked_item = KitchenOrderItem.objects.select_for_update().get(pk=kitchen_item.pk)

        # Idempotency
        if locked_item.status == KitchenItemStatus.READY:
            return locked_item

        if not locked_item.can_transition_to(KitchenItemStatus.READY):
            raise _item_transition_error(locked_item.status, KitchenItemStatus.READY)

        now = timezone.now()
        locked_item.status = KitchenItemStatus.READY
        locked_item.ready_at = now
        locked_item.save(update_fields=["status", "ready_at", "updated_at"])

        logger.info(
            "mark_item_ready: item=%s order=%s READY by user=%s",
            locked_item.item_name_snapshot,
            locked_item.kitchen_order.order_number,
            actor.email,
        )

        # Check if all non-cancelled items are now ready → auto-advance order
        parent_order = KitchenOrder.objects.select_for_update().get(
            pk=locked_item.kitchen_order_id
        )
        remaining = parent_order.items.filter(
            status__in=[KitchenItemStatus.NEW, KitchenItemStatus.PREPARING]
        ).count()

        order_auto_readied = False
        if (
            remaining == 0
            and parent_order.status == KitchenOrderStatus.PREPARING
            and parent_order.can_transition_to(KitchenOrderStatus.READY)
        ):
            parent_order.status = KitchenOrderStatus.READY
            parent_order.ready_at = now
            parent_order.completed_by = actor
            parent_order.save(update_fields=[
                "status", "ready_at", "completed_by", "updated_at"
            ])
            order_auto_readied = True
            logger.info(
                "mark_item_ready: all items ready — auto-advanced order=%s to READY",
                parent_order.order_number,
            )

    # Publish item event
    publish_kitchen_event(
        "kitchen.item.ready",
        locked_item.kitchen_order,
        item_id=str(locked_item.id),
        item_name=locked_item.item_name_snapshot,
    )

    # Publish order ready event if auto-advanced
    if order_auto_readied:
        publish_kitchen_event("kitchen.order.ready", parent_order)
        # Phase 11 — Trigger inventory consumption after auto-advance to READY.
        _trigger_inventory_consumption(parent_order, actor)

    return locked_item


# =============================================================================
# 8. update_kitchen_priority
# =============================================================================

def update_kitchen_priority(actor, *, kitchen_order, priority) -> "KitchenOrder":
    """
    Update the priority of a KitchenOrder (NORMAL / HIGH / URGENT).

    Can only be set on non-terminal orders (not READY or CANCELLED).
    Permission required: kitchen.priority_update
    """
    from kitchen.models import KitchenOrder, KitchenOrderStatus, KitchenPriority

    _require_auth(actor)

    if not acl.has_permission(actor, "kitchen.priority_update"):
        raise PermissionDenied("You do not have permission to update kitchen order priority.")

    _check_kitchen_branch_access(actor, kitchen_order)

    if priority not in KitchenPriority.values:
        raise ValidationError(
            {
                "code": "INVALID_PRIORITY",
                "message": f"Priority must be one of: {', '.join(KitchenPriority.values)}",
            }
        )

    with transaction.atomic():
        locked = KitchenOrder.objects.select_for_update().get(pk=kitchen_order.pk)

        if locked.status in (KitchenOrderStatus.READY, KitchenOrderStatus.CANCELLED):
            raise ValidationError(
                {
                    "code": "TERMINAL_STATUS",
                    "message": (
                        f"Cannot update priority on a {locked.status} order."
                    ),
                }
            )

        old_priority = locked.priority
        locked.priority = priority
        locked.save(update_fields=["priority", "updated_at"])

    logger.info(
        "update_kitchen_priority: order=%s priority %s→%s by user=%s",
        locked.order_number, old_priority, priority, actor.email,
    )

    publish_kitchen_event(
        "kitchen.priority.changed",
        locked,
        old_priority=old_priority,
        new_priority=priority,
    )
    return locked


# =============================================================================
# Phase 11 — Inventory Consumption Bridge
# =============================================================================

def _trigger_inventory_consumption(kitchen_order, actor) -> None:
    """
    Trigger recipe-based inventory consumption after a KitchenOrder reaches READY.

    Called AFTER the kitchen transaction commits — never inside it.
    Delegates entirely to the recipes service layer; any failure is logged
    but does NOT affect the kitchen order state (kitchen remains READY).

    The recipes service is responsible for:
        - Idempotency (duplicate calls produce only one batch)
        - Atomic stock deduction (all-or-nothing)
        - Recording failure reason on the ConsumptionBatch
    """
    try:
        from recipes.services import trigger_consumption_for_kitchen_order
        batch = trigger_consumption_for_kitchen_order(kitchen_order, actor)
        if batch is not None:
            logger.info(
                "_trigger_inventory_consumption: batch=%s status=%s for order=%s",
                batch.id, batch.status, kitchen_order.order_number,
            )
        else:
            logger.debug(
                "_trigger_inventory_consumption: no batch created for order=%s "
                "(trigger may not match configured setting)",
                kitchen_order.order_number,
            )
    except Exception as exc:
        # Consumption failure must never crash the kitchen service
        logger.error(
            "_trigger_inventory_consumption: FAILED for order=%s error=%s",
            kitchen_order.order_number, exc,
        )


# =============================================================================
# 9. publish_kitchen_event
# =============================================================================

def publish_kitchen_event(event_type: str, kitchen_order, **extra) -> None:
    """
    Publish a real-time WebSocket event to the branch kitchen channel group.

    Channel group naming convention:
        kitchen_{branch_id}

    This function is always called AFTER the database transaction is committed.
    If Redis/Channels is unavailable, the error is logged but does NOT raise —
    the database state is authoritative and the KDS can recover via REST poll.

    Event payload intentionally omits financial data (price, tax, cash amounts).
    """
    import asyncio
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    branch_id = str(kitchen_order.branch_id)
    group_name = f"kitchen_{branch_id}"
    event_id = str(uuid.uuid4())

    # Build safe payload — NO financial data
    order = kitchen_order.order
    payload: dict = {
        "event_id": event_id,
        "event": event_type,
        "kitchen_order_id": str(kitchen_order.id),
        "order_id": str(order.id),
        "order_number": order.order_number,
        "order_type": order.order_type,
        "status": kitchen_order.status,
        "priority": kitchen_order.priority,
        "branch_id": branch_id,
        "received_at": kitchen_order.received_at.isoformat(),
        "timestamp": timezone.now().isoformat(),
    }

    # Add table/counter context if present (no financial data)
    if order.table_id:
        payload["table"] = order.table.table_number if order.table else None
    else:
        payload["table"] = None

    if order.counter_id:
        payload["counter"] = order.counter.code if order.counter else None
    else:
        payload["counter"] = None

    # Merge any extra caller-supplied fields (must not include financial data)
    payload.update(extra)

    try:
        channel_layer = get_channel_layer()
        if channel_layer is None:
            logger.warning(
                "publish_kitchen_event: channel layer not available — "
                "event=%s order=%s not published",
                event_type, kitchen_order.order_number,
            )
            return

        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "kitchen.event",
                "payload": payload,
            },
        )
        logger.debug(
            "publish_kitchen_event: event=%s group=%s order=%s published",
            event_type, group_name, kitchen_order.order_number,
        )

    except Exception as exc:
        # Redis failure must not crash the API — DB state is already committed
        logger.error(
            "publish_kitchen_event: failed to publish event=%s order=%s error=%s",
            event_type, kitchen_order.order_number, exc,
        )


# =============================================================================
# 10. get_kitchen_orders_for_branch (query helper)
# =============================================================================

def get_kitchen_orders_for_branch(branch, *, date=None, statuses=None, today_only=True):
    """
    Return a queryset of KitchenOrders for a branch, optimized for KDS queries.

    By default returns today's non-terminal orders (NEW/ACCEPTED/PREPARING/READY).
    Suitable for the live KDS view.

    Parameters:
        branch      — Branch instance
        date        — specific date (date object or YYYY-MM-DD string)
        statuses    — list of KitchenOrderStatus values to filter
        today_only  — if True and date is None, filter to today's orders
    """
    from kitchen.models import KitchenOrder, KitchenOrderStatus
    from django.utils import timezone as tz

    qs = (
        KitchenOrder.objects
        .filter(branch=branch)
        .select_related(
            "order__table",
            "order__counter",
            "order__assigned_waiter",
        )
        .prefetch_related("items__menu_item")
        .order_by("priority", "received_at")
    )

    if statuses:
        qs = qs.filter(status__in=statuses)

    if date:
        qs = qs.filter(received_at__date=date)
    elif today_only:
        today = tz.now().date()
        qs = qs.filter(received_at__date=today)

    return qs
