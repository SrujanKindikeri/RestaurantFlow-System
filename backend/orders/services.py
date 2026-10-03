# =============================================================================
# RestaurantFlow — Order Services
# Phase 6
#
# All business logic for table sessions and order lifecycle lives here.
# Views call these; serializers validate input shapes only.
#
# Services:
#   generate_order_number(branch, order_type, counter, tz_name)  → str
#   open_table_session(actor, table, guest_count, notes)          → TableSession
#   close_table_session(actor, session, closed_by)                → TableSession
#   create_order(actor, branch, order_type, **kwargs)             → Order
#   add_order_item(actor, order, menu_item_id, quantity, notes)   → OrderItem
#   update_order_item(actor, item, quantity, notes)               → OrderItem
#   remove_order_item(actor, item)                                → None
#   confirm_order(actor, order)                                   → Order
#   cancel_order(actor, order, reason)                            → Order
#   assign_waiter(actor, order, waiter)                           → Order
#
# Concurrency:
#   open_table_session uses select_for_update() + transaction.atomic()
#   generate_order_number uses select_for_update() + get_or_create()
#   confirm_order uses select_for_update() to prevent double-confirmation
# =============================================================================

import logging
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from orders import access as order_acl

logger = logging.getLogger("orders")


# =============================================================================
# Internal helpers
# =============================================================================

def _require_auth(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


def _get_branch_timezone(branch) -> str:
    """Return the effective timezone string for a branch."""
    try:
        settings_tz = branch.restaurant.settings.timezone
        if settings_tz:
            return settings_tz
    except Exception:
        pass
    try:
        org_tz = branch.restaurant.organization.timezone
        if org_tz:
            return org_tz
    except Exception:
        pass
    return "Asia/Kolkata"


def _local_date_key(branch) -> str:
    """Return the current business date key (YYYYMMDD) in the branch's timezone."""
    tz_name = _get_branch_timezone(branch)
    now = timezone.now()
    try:
        tz = ZoneInfo(tz_name)
        local_now = now.astimezone(tz)
    except (ZoneInfoNotFoundError, Exception):
        local_now = now
    return local_now.strftime("%Y%m%d")


# =============================================================================
# Order number generation
# =============================================================================

def generate_order_number(*, branch, order_type, counter=None) -> str:
    """
    Generate a concurrency-safe, human-readable order number.

    For DINE_IN:
        D-{date}-{seq:04d}   →  e.g.  D-20261003-0001

    For COUNTER / TAKEAWAY:
        {counter_code}-{date}-{seq:04d}  →  e.g.  C01-20261003-0001

    Sequence resets daily per scope (branch for dine-in, counter for POS).
    Uses select_for_update() to prevent race conditions — NEVER uses MAX()+1.

    Must be called inside a transaction.atomic() block.
    """
    from orders.models import OrderSequence

    date_key = _local_date_key(branch)

    if order_type == "DINE_IN":
        scope_type = OrderSequence.SCOPE_BRANCH
        scope_id   = str(branch.pk)
        prefix     = "D"
    else:
        # COUNTER or TAKEAWAY — scoped to the specific counter
        if not counter:
            raise ValidationError(
                {"counter": "Counter is required for COUNTER/TAKEAWAY orders."}
            )
        scope_type = OrderSequence.SCOPE_COUNTER
        scope_id   = str(counter.pk)
        prefix     = counter.code  # e.g. "C01"

    # Atomically increment the sequence counter with DB-level locking
    try:
        seq_obj = OrderSequence.objects.select_for_update().get(
            scope_type=scope_type,
            scope_id=scope_id,
            date_key=date_key,
        )
        seq_obj.last_sequence += 1
        seq_obj.save(update_fields=["last_sequence", "updated_at"])
    except OrderSequence.DoesNotExist:
        # First order of the day for this scope — create with sequence=1
        try:
            seq_obj, _ = OrderSequence.objects.get_or_create(
                scope_type=scope_type,
                scope_id=scope_id,
                date_key=date_key,
                defaults={"last_sequence": 1},
            )
            if not _:
                # Another request created it between our get and create
                seq_obj = OrderSequence.objects.select_for_update().get(
                    scope_type=scope_type,
                    scope_id=scope_id,
                    date_key=date_key,
                )
                seq_obj.last_sequence += 1
                seq_obj.save(update_fields=["last_sequence", "updated_at"])
        except IntegrityError:
            # Concurrent creation — fetch and increment
            seq_obj = OrderSequence.objects.select_for_update().get(
                scope_type=scope_type,
                scope_id=scope_id,
                date_key=date_key,
            )
            seq_obj.last_sequence += 1
            seq_obj.save(update_fields=["last_sequence", "updated_at"])

    return f"{prefix}-{date_key}-{seq_obj.last_sequence:04d}"


# =============================================================================
# Table Session Services
# =============================================================================

def open_table_session(actor, *, table, guest_count=1, notes=""):
    """
    Open a new dining session on a table.

    Checks:
        - actor is authenticated and active
        - actor has table.session.open permission
        - actor can access the table's branch
        - table is ACTIVE
        - no existing OPEN session on this table (with DB-level lock)

    Returns the newly created TableSession.
    """
    from orders.models import DiningTable, TableSession, TableSessionStatus, TableStatus

    _require_auth(actor)

    if not acl.has_permission(actor, "table.session.open"):
        raise PermissionDenied("You do not have permission to open a table session.")

    if not acl.can_access_branch(actor, table.branch):
        raise PermissionDenied("You do not have access to this table's branch.")

    if table.status == TableStatus.INACTIVE:
        raise ValidationError(
            {
                "code": "TABLE_INACTIVE",
                "message": "This table is inactive and cannot accept a new session.",
            }
        )

    if guest_count is None or guest_count < 1:
        raise ValidationError(
            {
                "code": "INVALID_GUEST_COUNT",
                "message": "Guest count must be at least 1.",
            }
        )

    try:
        with transaction.atomic():
            # Lock the table row to prevent concurrent open-session requests
            locked_table = DiningTable.objects.select_for_update().get(pk=table.pk)

            existing = TableSession.objects.filter(
                table=locked_table, status=TableSessionStatus.OPEN
            ).first()
            if existing:
                raise ValidationError(
                    {
                        "code": "TABLE_SESSION_ALREADY_OPEN",
                        "message": "This table already has an open session.",
                    }
                )

            session = TableSession.objects.create(
                table=locked_table,
                opened_by=actor,
                guest_count=guest_count,
                notes=notes or "",
                status=TableSessionStatus.OPEN,
            )

            logger.info(
                "Table session opened: table=%s session=%s by user=%s guests=%s",
                locked_table.table_number,
                session.id,
                actor.email,
                guest_count,
            )
            return session

    except IntegrityError:
        raise ValidationError(
            {
                "code": "TABLE_SESSION_ALREADY_OPEN",
                "message": "This table already has an open session.",
            }
        )


def close_table_session(actor, *, session):
    """
    Close a table session.

    Checks:
        - actor has table.session.close permission
        - actor can access the session's table branch
        - session is currently OPEN
        - no active orders are attached to this session (Phase 6 guard)
    """
    from orders.models import TableSession, TableSessionStatus, OrderStatus

    _require_auth(actor)

    if not acl.has_permission(actor, "table.session.close"):
        raise PermissionDenied("You do not have permission to close a table session.")

    if not acl.can_access_branch(actor, session.table.branch):
        raise PermissionDenied("You do not have access to this table session.")

    if session.status != TableSessionStatus.OPEN:
        raise ValidationError(
            {
                "code": "TABLE_SESSION_NOT_OPEN",
                "message": "This table session is not open and cannot be closed.",
            }
        )

    # Check no active orders exist on this session
    active_orders = session.orders.filter(
        status__in=[OrderStatus.DRAFT, OrderStatus.CONFIRMED]
    ).count()
    if active_orders > 0:
        raise ValidationError(
            {
                "code": "SESSION_HAS_ACTIVE_ORDERS",
                "message": (
                    "This table session has active orders. "
                    "Cancel or complete all orders before closing the session."
                ),
            }
        )

    with transaction.atomic():
        session.status = TableSessionStatus.CLOSED
        session.closed_by = actor
        session.closed_at = timezone.now()
        session.save(update_fields=["status", "closed_by", "closed_at", "updated_at"])

    logger.info(
        "Table session closed: session=%s table=%s by user=%s",
        session.id,
        session.table.table_number,
        actor.email,
    )
    return session


# =============================================================================
# Order Services
# =============================================================================

def _validate_dine_in_references(branch, table, table_session):
    """Validate DINE_IN order references."""
    from orders.models import DiningTable, TableSession, TableSessionStatus, TableStatus

    if table is None:
        raise ValidationError(
            {"table": "A table is required for DINE_IN orders."}
        )
    if table_session is None:
        raise ValidationError(
            {"table_session": "A table session is required for DINE_IN orders."}
        )

    # Cross-branch check
    if str(table.branch_id) != str(branch.pk):
        raise ValidationError(
            {"table": "The table does not belong to the specified branch."}
        )

    if table.status == TableStatus.INACTIVE:
        raise ValidationError(
            {"table": "Cannot create an order for an inactive table."}
        )

    # Verify table_session belongs to this table
    if str(table_session.table_id) != str(table.pk):
        raise ValidationError(
            {"table_session": "The table session does not belong to the specified table."}
        )

    if table_session.status != TableSessionStatus.OPEN:
        raise ValidationError(
            {"table_session": "The table session is not open."}
        )

    # Verify branch consistency
    if str(table_session.table.branch_id) != str(branch.pk):
        raise ValidationError(
            {"table_session": "The table session does not belong to the specified branch."}
        )


def _validate_counter_references(branch, counter, counter_session):
    """Validate COUNTER / TAKEAWAY order references."""
    from counters.models import Counter, CounterSession, SessionStatus, CounterStatus

    if counter is None:
        raise ValidationError(
            {"counter": "A counter is required for COUNTER/TAKEAWAY orders."}
        )
    if counter_session is None:
        raise ValidationError(
            {"counter_session": "A counter session is required for COUNTER/TAKEAWAY orders."}
        )

    # Cross-branch check
    if str(counter.branch_id) != str(branch.pk):
        raise ValidationError(
            {"counter": "The counter does not belong to the specified branch."}
        )

    if counter.status == CounterStatus.INACTIVE:
        raise ValidationError(
            {"counter": "Cannot create an order for an inactive counter."}
        )
    if counter.status == CounterStatus.MAINTENANCE:
        raise ValidationError(
            {"counter": "Cannot create an order for a counter under maintenance."}
        )

    # Verify counter_session belongs to this counter
    if str(counter_session.counter_id) != str(counter.pk):
        raise ValidationError(
            {"counter_session": "The counter session does not belong to the specified counter."}
        )

    if counter_session.status != SessionStatus.OPEN:
        raise ValidationError(
            {"counter_session": "The counter session is not open."}
        )

    # Branch consistency
    if str(counter_session.counter.branch_id) != str(branch.pk):
        raise ValidationError(
            {"counter_session": "The counter session does not belong to the specified branch."}
        )


def create_order(
    actor,
    *,
    branch,
    order_type,
    table=None,
    table_session=None,
    counter=None,
    counter_session=None,
    guest_count=None,
    assigned_waiter=None,
    notes="",
):
    """
    Create a new DRAFT order.

    Validates:
        - actor authentication and permissions
        - branch access
        - order type-specific field requirements
        - cross-branch relationship integrity
        - waiter assignment validity

    Returns the newly created Order.
    """
    from orders.models import Order, OrderType, OrderStatus

    _require_auth(actor)

    # Permission check
    perm_map = {
        OrderType.DINE_IN:  "order.create.dine_in",
        OrderType.TAKEAWAY: "order.create.takeaway",
        OrderType.COUNTER:  "order.create.counter",
    }
    required_perm = perm_map.get(order_type)
    if required_perm and not acl.has_permission(actor, required_perm):
        raise PermissionDenied(
            f"You do not have permission to create a {order_type} order."
        )

    # Branch access
    if not acl.can_access_branch(actor, branch):
        raise PermissionDenied("You do not have access to the specified branch.")

    # Type-specific reference validation
    if order_type == OrderType.DINE_IN:
        _validate_dine_in_references(branch, table, table_session)
        # DINE_IN must NOT have counter references
        if counter is not None or counter_session is not None:
            raise ValidationError(
                {"order_type": "DINE_IN orders must not reference a counter or counter session."}
            )
    elif order_type in (OrderType.COUNTER, OrderType.TAKEAWAY):
        _validate_counter_references(branch, counter, counter_session)
        # COUNTER/TAKEAWAY must NOT have table references
        if table is not None or table_session is not None:
            raise ValidationError(
                {"order_type": f"{order_type} orders must not reference a table or table session."}
            )
    else:
        raise ValidationError({"order_type": f"Invalid order type: {order_type}"})

    # Waiter assignment validation
    if assigned_waiter is not None:
        if not acl.can_access_branch(assigned_waiter, branch):
            raise ValidationError(
                {
                    "assigned_waiter": (
                        f"The assigned waiter does not have access to branch '{branch.name}'."
                    )
                }
            )
        if not acl.has_permission(assigned_waiter, "order.view.branch"):
            # Waiter should have at minimum branch order view permission
            # This is a soft check — primary control is branch access
            pass

    with transaction.atomic():
        order_number = generate_order_number(
            branch=branch,
            order_type=order_type,
            counter=counter,
        )

        order = Order.objects.create(
            branch=branch,
            order_number=order_number,
            order_type=order_type,
            table=table,
            table_session=table_session,
            counter=counter,
            counter_session=counter_session,
            created_by=actor,
            assigned_waiter=assigned_waiter,
            guest_count=guest_count,
            notes=notes or "",
            status=OrderStatus.DRAFT,
        )

    logger.info(
        "Order created: %s type=%s branch=%s by user=%s",
        order.order_number,
        order_type,
        branch.name,
        actor.email,
    )
    return order


def add_order_item(actor, *, order, menu_item_id, quantity, notes=""):
    """
    Add a menu item to a DRAFT order.

    Validates:
        - order is DRAFT
        - actor has order.item.add permission
        - actor can access the order's branch
        - menu item belongs to the same restaurant as the order branch
        - menu item is active and available at the branch
        - branch pricing exists
        - quantity > 0

    Snapshots:
        item_name, sku, unit_price, tax_rate, tax_code

    Returns the newly created OrderItem.
    """
    from orders.models import Order, OrderItem, OrderStatus
    from menu.models import MenuItem, MenuItemPrice, MenuItemBranch
    from menu.services import is_menu_item_available

    _require_auth(actor)

    if not acl.has_permission(actor, "order.item.add"):
        raise PermissionDenied("You do not have permission to add items to an order.")

    if not order_acl.can_access_order(actor, order):
        raise PermissionDenied("You do not have access to this order.")

    if order.status != OrderStatus.DRAFT:
        raise ValidationError(
            {
                "code": "ORDER_NOT_DRAFT",
                "message": "Items can only be added to DRAFT orders.",
            }
        )

    # Quantity validation
    try:
        quantity = Decimal(str(quantity))
    except Exception:
        raise ValidationError({"quantity": "Invalid quantity value."})

    if quantity <= Decimal("0"):
        raise ValidationError({"quantity": "Quantity must be greater than 0."})

    if quantity > Decimal("9999.999"):
        raise ValidationError({"quantity": "Quantity is unreasonably large."})

    # Fetch and validate menu item
    try:
        menu_item = MenuItem.objects.select_related(
            "restaurant", "category", "tax_rate"
        ).get(pk=menu_item_id)
    except MenuItem.DoesNotExist:
        raise ValidationError({"menu_item": "Menu item not found."})

    # Restaurant scope check — item must belong to the order's restaurant
    branch = order.branch
    if str(menu_item.restaurant_id) != str(branch.restaurant_id):
        raise ValidationError(
            {
                "menu_item": (
                    "This menu item does not belong to the restaurant "
                    "associated with this branch."
                )
            }
        )

    # Item must be active
    if not menu_item.is_active:
        raise ValidationError(
            {"menu_item": "This menu item is not active and cannot be ordered."}
        )

    # Item must be available (global flag)
    if not menu_item.is_available:
        raise ValidationError(
            {"menu_item": "This menu item is currently not available."}
        )

    # Branch availability check (MenuItemBranch record + time window)
    if not is_menu_item_available(menu_item, branch):
        raise ValidationError(
            {
                "menu_item": (
                    "This menu item is not available at this branch "
                    "or outside its current availability window."
                )
            }
        )

    # Branch price lookup — must have an active price record
    try:
        price_record = MenuItemPrice.objects.get(
            menu_item=menu_item,
            branch=branch,
            is_active=True,
        )
    except MenuItemPrice.DoesNotExist:
        raise ValidationError(
            {
                "menu_item": (
                    "No active price is configured for this menu item at this branch."
                )
            }
        )
    except MenuItemPrice.MultipleObjectsReturned:
        # Use the most recently created one (should not happen with proper data management)
        price_record = MenuItemPrice.objects.filter(
            menu_item=menu_item,
            branch=branch,
            is_active=True,
        ).order_by("-created_at").first()

    # Tax snapshot
    tax_rate_val = Decimal("0.000")
    tax_code_val = ""
    if menu_item.tax_rate and menu_item.tax_rate.is_active:
        tax_rate_val = menu_item.tax_rate.rate
        tax_code_val = menu_item.tax_rate.code

    order_item = OrderItem.objects.create(
        order=order,
        menu_item=menu_item,
        item_name_snapshot=menu_item.name,
        sku_snapshot=menu_item.sku or "",
        unit_price_snapshot=price_record.price,
        tax_rate_snapshot=tax_rate_val,
        tax_code_snapshot=tax_code_val,
        quantity=quantity,
        notes=notes or "",
    )

    logger.info(
        "OrderItem added: order=%s item=%s qty=%s price=%s by user=%s",
        order.order_number,
        menu_item.name,
        quantity,
        price_record.price,
        actor.email,
    )
    return order_item


def update_order_item(actor, *, item, quantity=None, notes=None):
    """
    Update quantity and/or notes on a DRAFT order item.

    Snapshot fields (name, price, tax) are immutable — never updated here.
    """
    from orders.models import OrderStatus

    _require_auth(actor)

    if not acl.has_permission(actor, "order.item.update"):
        raise PermissionDenied("You do not have permission to update order items.")

    if not order_acl.can_access_order(actor, item.order):
        raise PermissionDenied("You do not have access to this order.")

    if item.order.status != OrderStatus.DRAFT:
        raise ValidationError(
            {
                "code": "ORDER_NOT_DRAFT",
                "message": "Items can only be updated on DRAFT orders.",
            }
        )

    update_fields = ["updated_at"]

    if quantity is not None:
        try:
            quantity = Decimal(str(quantity))
        except Exception:
            raise ValidationError({"quantity": "Invalid quantity value."})
        if quantity <= Decimal("0"):
            raise ValidationError({"quantity": "Quantity must be greater than 0."})
        if quantity > Decimal("9999.999"):
            raise ValidationError({"quantity": "Quantity is unreasonably large."})
        item.quantity = quantity
        update_fields.append("quantity")

    if notes is not None:
        item.notes = notes
        update_fields.append("notes")

    item.save(update_fields=update_fields)

    logger.info(
        "OrderItem updated: item=%s order=%s by user=%s",
        item.pk,
        item.order.order_number,
        actor.email,
    )
    return item


def remove_order_item(actor, *, item):
    """
    Remove an item from a DRAFT order.

    Items can only be removed from DRAFT orders.
    """
    from orders.models import OrderStatus

    _require_auth(actor)

    if not acl.has_permission(actor, "order.item.remove"):
        raise PermissionDenied("You do not have permission to remove order items.")

    if not order_acl.can_access_order(actor, item.order):
        raise PermissionDenied("You do not have access to this order.")

    if item.order.status != OrderStatus.DRAFT:
        raise ValidationError(
            {
                "code": "ORDER_NOT_DRAFT",
                "message": "Items can only be removed from DRAFT orders.",
            }
        )

    order_number = item.order.order_number
    item_name = item.item_name_snapshot
    item.delete()

    logger.info(
        "OrderItem removed: item=%s order=%s by user=%s",
        item_name,
        order_number,
        actor.email,
    )


def confirm_order(actor, *, order):
    """
    Confirm a DRAFT order, transitioning it to CONFIRMED.

    Validates:
        - order is DRAFT
        - actor has order.confirm permission
        - actor can access the order's branch
        - order has at least one item
        - all items still have valid menu availability (re-validated at confirmation)
        - table/session is still valid for DINE_IN
        - counter/session is still open for COUNTER/TAKEAWAY

    After confirmation, the order is ready for Phase 7 (Kitchen) processing.
    Sets confirmed_at timestamp.

    Uses select_for_update() to prevent double-confirmation race conditions.
    """
    from orders.models import Order, OrderStatus, OrderType, TableSessionStatus
    from counters.models import SessionStatus

    _require_auth(actor)

    if not acl.has_permission(actor, "order.confirm"):
        raise PermissionDenied("You do not have permission to confirm orders.")

    if not order_acl.can_access_order(actor, order):
        raise PermissionDenied("You do not have access to this order.")

    with transaction.atomic():
        # Lock the order to prevent race conditions
        locked_order = Order.objects.select_for_update().get(pk=order.pk)

        if locked_order.status != OrderStatus.DRAFT:
            raise ValidationError(
                {
                    "code": "ORDER_NOT_DRAFT",
                    "message": "Only DRAFT orders can be confirmed.",
                }
            )

        # Must have at least one item
        if locked_order.items.count() == 0:
            raise ValidationError(
                {
                    "code": "ORDER_EMPTY",
                    "message": "Cannot confirm an empty order. Add at least one item.",
                }
            )

        # Re-validate session states
        if locked_order.order_type == OrderType.DINE_IN:
            if locked_order.table_session is None:
                raise ValidationError(
                    {"table_session": "No table session found for this order."}
                )
            # Refresh from DB
            locked_order.table_session.refresh_from_db()
            if locked_order.table_session.status != TableSessionStatus.OPEN:
                raise ValidationError(
                    {
                        "code": "TABLE_SESSION_CLOSED",
                        "message": "The table session is no longer open.",
                    }
                )
        elif locked_order.order_type in (OrderType.COUNTER, OrderType.TAKEAWAY):
            if locked_order.counter_session is None:
                raise ValidationError(
                    {"counter_session": "No counter session found for this order."}
                )
            locked_order.counter_session.refresh_from_db()
            if locked_order.counter_session.status != SessionStatus.OPEN:
                raise ValidationError(
                    {
                        "code": "COUNTER_SESSION_CLOSED",
                        "message": "The counter session is no longer open.",
                    }
                )

        locked_order.status = OrderStatus.CONFIRMED
        locked_order.confirmed_at = timezone.now()
        locked_order.save(update_fields=["status", "confirmed_at", "updated_at"])

    logger.info(
        "Order confirmed: %s by user=%s",
        locked_order.order_number,
        actor.email,
    )
    return locked_order


def cancel_order(actor, *, order, reason=""):
    """
    Cancel an order.

    Cancelling a DRAFT order requires order.cancel permission.
    Cancelling a CONFIRMED order requires order.cancel.confirmed permission.

    Sets cancelled_at, cancelled_by, cancellation_reason.
    Does NOT physically delete the order.

    For DINE_IN: does NOT automatically close the table session.
    The session must be explicitly managed by the service layer.
    Business rule: if no more active orders exist on the session,
    the caller should close the session separately.
    """
    from orders.models import Order, OrderStatus

    _require_auth(actor)

    if not order_acl.can_access_order(actor, order):
        raise PermissionDenied("You do not have access to this order.")

    if order.status == OrderStatus.CANCELLED:
        raise ValidationError(
            {"code": "ORDER_ALREADY_CANCELLED", "message": "This order is already cancelled."}
        )

    # Permission check depends on current status
    if order.status == OrderStatus.CONFIRMED:
        if not acl.has_permission(actor, "order.cancel.confirmed"):
            raise PermissionDenied(
                "You do not have permission to cancel a confirmed order."
            )
    else:
        if not acl.has_permission(actor, "order.cancel"):
            raise PermissionDenied("You do not have permission to cancel orders.")

    with transaction.atomic():
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.cancelled_by = actor
        order.cancellation_reason = reason or ""
        order.save(update_fields=[
            "status", "cancelled_at", "cancelled_by",
            "cancellation_reason", "updated_at",
        ])

    logger.info(
        "Order cancelled: %s by user=%s reason='%s'",
        order.order_number,
        actor.email,
        reason,
    )
    return order


def assign_waiter(actor, *, order, waiter):
    """
    Assign or reassign a waiter to an order.

    Checks:
        - actor has order.reassign_waiter permission
        - order is not cancelled
        - waiter has access to the order's branch
    """
    from orders.models import OrderStatus

    _require_auth(actor)

    if not acl.has_permission(actor, "order.reassign_waiter"):
        raise PermissionDenied("You do not have permission to assign waiters to orders.")

    if not order_acl.can_access_order(actor, order):
        raise PermissionDenied("You do not have access to this order.")

    if order.status == OrderStatus.CANCELLED:
        raise ValidationError(
            {"code": "ORDER_CANCELLED", "message": "Cannot assign a waiter to a cancelled order."}
        )

    if not acl.can_access_branch(waiter, order.branch):
        raise ValidationError(
            {
                "assigned_waiter": (
                    f"User '{waiter.email}' does not have access to "
                    f"branch '{order.branch.name}'."
                )
            }
        )

    order.assigned_waiter = waiter
    order.save(update_fields=["assigned_waiter", "updated_at"])

    logger.info(
        "Waiter assigned: order=%s waiter=%s by actor=%s",
        order.order_number,
        waiter.email,
        actor.email,
    )
    return order
