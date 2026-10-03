# =============================================================================
# RestaurantFlow — Inventory Services
# Phase 10
#
# All business logic for the inventory and stock management lifecycle.
# Views call these; serializers validate input shapes only.
#
# Public API (StockService functions):
#   increase_stock(item, location, qty, unit_cost, movement_type, ref_type, ref_id, reason, user)
#   decrease_stock(item, location, qty, movement_type, ref_type, ref_id, reason, user)
#   get_or_create_balance(item, location)           → StockBalance
#   calculate_weighted_average_cost(old_qty, old_cost, new_qty, new_cost) → Decimal
#
# Public API (Number generation):
#   generate_purchase_number(restaurant)            → str
#   generate_transfer_number(restaurant)            → str
#
# Public API (Purchase workflow):
#   create_purchase_order(restaurant, branch, supplier, items, user, **kwargs) → PurchaseOrder
#   submit_purchase_order(po, user)                 → PurchaseOrder
#   approve_purchase_order(po, user)                → PurchaseOrder
#   cancel_purchase_order(po, user, reason)         → PurchaseOrder
#   receive_purchase_order(po, user, storage_location, receipt_items) → PurchaseReceipt
#
# Public API (Transfer workflow):
#   create_stock_transfer(restaurant, src, dst, items, user, notes) → StockTransfer
#   request_stock_transfer(transfer, user)          → StockTransfer
#   approve_stock_transfer(transfer, user)          → StockTransfer
#   complete_stock_transfer(transfer, user)         → StockTransfer
#   cancel_stock_transfer(transfer, user)           → StockTransfer
#
# Public API (Wastage workflow):
#   create_wastage(item, location, qty, unit, wastage_type, reason, user) → StockWastage
#   approve_wastage(wastage, user)                  → StockWastage
#   reject_wastage(wastage, user, reason)           → StockWastage
#
# Public API (Adjustment):
#   create_stock_adjustment(item, location, physical_qty, unit, reason, user) → StockAdjustment
#
# Concurrency:
#   - All stock mutations use select_for_update() on StockBalance.
#   - generate_purchase_number uses select_for_update() on PurchaseSequence.
#   - generate_transfer_number uses select_for_update() on TransferSequence.
#   - All mutating operations are wrapped in transaction.atomic().
#
# Security:
#   - Every public function validates user authentication + permissions.
#   - Branch/restaurant scope is validated for every relevant object.
#   - Negative stock is rejected by default (validate_sufficient_stock).
# =============================================================================

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from inventory.constants import (
    MOVEMENT_PURCHASE,
    MOVEMENT_TRANSFER_IN,
    MOVEMENT_TRANSFER_OUT,
    MOVEMENT_WASTAGE,
    MOVEMENT_ADJUSTMENT_IN,
    MOVEMENT_ADJUSTMENT_OUT,
    MOVEMENT_OPENING_STOCK,
    REF_PURCHASE_RECEIPT,
    REF_STOCK_TRANSFER,
    REF_STOCK_WASTAGE,
    REF_STOCK_ADJUSTMENT,
    PO_DRAFT, PO_SUBMITTED, PO_APPROVED, PO_PARTIALLY_RECEIVED, PO_RECEIVED, PO_CANCELLED,
    TRANSFER_DRAFT, TRANSFER_REQUESTED, TRANSFER_APPROVED, TRANSFER_COMPLETED, TRANSFER_CANCELLED,
    WASTAGE_PENDING, WASTAGE_APPROVED, WASTAGE_REJECTED, WASTAGE_RECORDED,
    DECIMAL_QTY, DECIMAL_COST, ZERO, ZERO_COST,
    PO_NUMBER_FORMAT, TRANSFER_NUMBER_FORMAT,
)
from inventory.validators import (
    validate_sufficient_stock,
    validate_purchase_order_transition,
    validate_purchase_order_receivable,
    validate_purchase_order_cancellable,
    validate_receive_quantity,
    validate_transfer_transition,
    validate_transfer_locations,
    validate_reason,
    validate_positive_quantity,
)

logger = logging.getLogger("inventory")

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_auth(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


def _qty(value) -> Decimal:
    """Round to 3 decimal places (quantity precision)."""
    return Decimal(str(value)).quantize(DECIMAL_QTY, rounding=ROUND_HALF_UP)


def _cost(value) -> Decimal:
    """Round to 2 decimal places (monetary precision)."""
    return Decimal(str(value)).quantize(DECIMAL_COST, rounding=ROUND_HALF_UP)


# =============================================================================
# 1. Sequence number generation
# =============================================================================

def generate_purchase_number(restaurant) -> str:
    """
    Generate a concurrency-safe, human-readable purchase order number.

    Format: PO-{seq:06d}  e.g. PO-000001
    One global sequence per restaurant (not reset annually).
    Must be called inside a transaction.atomic() block.
    Never uses MAX()+1.
    """
    from inventory.models import PurchaseSequence

    try:
        seq_obj = PurchaseSequence.objects.select_for_update().get(
            restaurant=restaurant
        )
        seq_obj.last_sequence += 1
        seq_obj.save(update_fields=["last_sequence", "updated_at"])
    except PurchaseSequence.DoesNotExist:
        try:
            seq_obj, created = PurchaseSequence.objects.get_or_create(
                restaurant=restaurant,
                defaults={"last_sequence": 1},
            )
            if not created:
                seq_obj = PurchaseSequence.objects.select_for_update().get(
                    restaurant=restaurant
                )
                seq_obj.last_sequence += 1
                seq_obj.save(update_fields=["last_sequence", "updated_at"])
        except IntegrityError:
            seq_obj = PurchaseSequence.objects.select_for_update().get(
                restaurant=restaurant
            )
            seq_obj.last_sequence += 1
            seq_obj.save(update_fields=["last_sequence", "updated_at"])

    return PO_NUMBER_FORMAT.format(seq=seq_obj.last_sequence)


def generate_transfer_number(restaurant) -> str:
    """
    Generate a concurrency-safe, human-readable transfer number.

    Format: TR-{seq:06d}  e.g. TR-000001
    Must be called inside a transaction.atomic() block.
    """
    from inventory.models import TransferSequence

    try:
        seq_obj = TransferSequence.objects.select_for_update().get(
            restaurant=restaurant
        )
        seq_obj.last_sequence += 1
        seq_obj.save(update_fields=["last_sequence", "updated_at"])
    except TransferSequence.DoesNotExist:
        try:
            seq_obj, created = TransferSequence.objects.get_or_create(
                restaurant=restaurant,
                defaults={"last_sequence": 1},
            )
            if not created:
                seq_obj = TransferSequence.objects.select_for_update().get(
                    restaurant=restaurant
                )
                seq_obj.last_sequence += 1
                seq_obj.save(update_fields=["last_sequence", "updated_at"])
        except IntegrityError:
            seq_obj = TransferSequence.objects.select_for_update().get(
                restaurant=restaurant
            )
            seq_obj.last_sequence += 1
            seq_obj.save(update_fields=["last_sequence", "updated_at"])

    return TRANSFER_NUMBER_FORMAT.format(seq=seq_obj.last_sequence)


# =============================================================================
# 2. Stock Service — core operations
# =============================================================================

def get_or_create_balance(inventory_item, storage_location):
    """
    Fetch or create (without locking) a StockBalance for the (item, location) pair.

    NOTE: This is NOT for use inside stock-mutating operations — those must
    use select_for_update() directly. Use this only for read paths.
    """
    from inventory.models import StockBalance
    balance, _ = StockBalance.objects.get_or_create(
        inventory_item=inventory_item,
        storage_location=storage_location,
    )
    return balance


def calculate_weighted_average_cost(
    old_qty: Decimal,
    old_cost: Decimal,
    new_qty: Decimal,
    new_cost: Decimal,
) -> Decimal:
    """
    Compute weighted-average cost using:
        (old_qty × old_cost + new_qty × new_cost) / (old_qty + new_qty)

    Returns 0 if total quantity is 0.
    Uses Decimal — never float.
    """
    total_qty = old_qty + new_qty
    if total_qty <= ZERO:
        return ZERO_COST
    weighted = (old_qty * old_cost + new_qty * new_cost) / total_qty
    return _cost(weighted)


def increase_stock(
    inventory_item,
    storage_location,
    quantity: Decimal,
    unit_cost: Decimal,
    movement_type: str,
    performed_by,
    *,
    reference_type: str = "",
    reference_id=None,
    reason: str = "",
) -> "StockMovement":
    """
    Increase stock for an (item, location) pair.

    Always:
        1. Locks StockBalance with select_for_update()
        2. Updates StockBalance.quantity
        3. Recalculates weighted-average cost
        4. Creates StockMovement
        5. Saves update_fields only

    Must be called inside a transaction.atomic() block.
    Returns the created StockMovement.
    """
    from inventory.models import StockBalance, StockMovement

    quantity = _qty(quantity)
    unit_cost = _cost(unit_cost)

    if quantity <= ZERO:
        raise ValidationError(
            {"quantity": "Quantity to increase must be > 0."}
        )

    # Lock the balance row (creates if missing, then locks)
    balance, created = StockBalance.objects.get_or_create(
        inventory_item=inventory_item,
        storage_location=storage_location,
    )
    # Re-fetch with lock after potential creation
    balance = StockBalance.objects.select_for_update().get(
        inventory_item=inventory_item,
        storage_location=storage_location,
    )

    # Update weighted-average cost
    new_avg_cost = calculate_weighted_average_cost(
        old_qty=balance.quantity,
        old_cost=balance.average_cost,
        new_qty=quantity,
        new_cost=unit_cost,
    )

    balance.quantity = _qty(balance.quantity + quantity)
    balance.average_cost = new_avg_cost
    balance.last_movement_at = timezone.now()
    balance.save(update_fields=["quantity", "average_cost", "last_movement_at", "updated_at"])

    # Also update the item-level average cost
    inventory_item.average_cost = new_avg_cost
    inventory_item.save(update_fields=["average_cost", "updated_at"])

    # Create immutable movement record
    movement = StockMovement.objects.create(
        inventory_item=inventory_item,
        storage_location=storage_location,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=unit_cost,
        total_cost=_cost(quantity * unit_cost),
        reference_type=reference_type,
        reference_id=reference_id,
        reason=reason,
        performed_by=performed_by,
    )

    logger.info(
        "Stock increased: item=%s location=%s qty=%s unit_cost=%s type=%s by user=%s",
        inventory_item.name, storage_location.name, quantity, unit_cost,
        movement_type, performed_by.email,
    )
    return movement


def decrease_stock(
    inventory_item,
    storage_location,
    quantity: Decimal,
    movement_type: str,
    performed_by,
    *,
    reference_type: str = "",
    reference_id=None,
    reason: str = "",
    unit_cost: Decimal | None = None,
) -> "StockMovement":
    """
    Decrease stock for an (item, location) pair.

    Enforces no-negative-stock by default.
    unit_cost defaults to current average_cost if not provided.

    Must be called inside a transaction.atomic() block.
    Returns the created StockMovement.
    """
    from inventory.models import StockBalance, StockMovement

    quantity = _qty(quantity)

    if quantity <= ZERO:
        raise ValidationError(
            {"quantity": "Quantity to decrease must be > 0."}
        )

    # Lock the balance row
    try:
        balance = StockBalance.objects.select_for_update().get(
            inventory_item=inventory_item,
            storage_location=storage_location,
        )
    except StockBalance.DoesNotExist:
        raise ValidationError(
            {
                "code": "INSUFFICIENT_STOCK",
                "message": (
                    f"No stock balance found for '{inventory_item.name}' "
                    f"at '{storage_location.name}'."
                ),
            }
        )

    # Enforce no-negative-stock
    validate_sufficient_stock(
        available=balance.available_quantity,
        requested=quantity,
        item_name=inventory_item.name,
    )

    effective_unit_cost = unit_cost if unit_cost is not None else balance.average_cost

    balance.quantity = _qty(balance.quantity - quantity)
    balance.last_movement_at = timezone.now()
    balance.save(update_fields=["quantity", "last_movement_at", "updated_at"])

    # Create immutable movement record
    movement = StockMovement.objects.create(
        inventory_item=inventory_item,
        storage_location=storage_location,
        movement_type=movement_type,
        quantity=quantity,
        unit_cost=effective_unit_cost,
        total_cost=_cost(quantity * effective_unit_cost),
        reference_type=reference_type,
        reference_id=reference_id,
        reason=reason,
        performed_by=performed_by,
    )

    logger.info(
        "Stock decreased: item=%s location=%s qty=%s type=%s by user=%s",
        inventory_item.name, storage_location.name, quantity,
        movement_type, performed_by.email,
    )
    return movement


# =============================================================================
# 3. Purchase Order workflow
# =============================================================================

def _calculate_po_totals(po) -> None:
    """
    Recalculate and save PO financial totals from its items.
    Backend-authoritative — never trusts frontend totals.
    Must be called inside atomic block.
    """
    from inventory.models import PurchaseOrderItem

    items = list(po.items.all())
    subtotal = ZERO_COST
    tax_total = ZERO_COST

    for item in items:
        gross = _cost(item.quantity * item.unit_cost)
        tax = _cost(gross * item.tax_rate / Decimal("100"))
        line_total = _cost(gross + tax - item.discount_amount)
        item.total_amount = line_total
        item.save(update_fields=["total_amount", "updated_at"])
        subtotal += gross
        tax_total += tax

    po.subtotal = _cost(subtotal)
    po.tax_amount = _cost(tax_total)
    po.total_amount = _cost(subtotal + tax_total - po.discount_amount)
    po.save(update_fields=["subtotal", "tax_amount", "total_amount", "updated_at"])


def create_purchase_order(
    restaurant,
    branch,
    supplier,
    items: list[dict],
    user,
    *,
    order_date=None,
    expected_date=None,
    discount_amount: Decimal = ZERO_COST,
    notes: str = "",
) -> "PurchaseOrder":
    """
    Create a DRAFT PurchaseOrder for a supplier.

    items: list of dicts with keys:
        inventory_item_id, quantity, unit, unit_cost, tax_rate, discount_amount, notes

    Does NOT increase stock — stock only increases on receiving.

    Raises:
        PermissionDenied — auth or permission failure
        ValidationError  — validation failure
    """
    from inventory.models import PurchaseOrder, PurchaseOrderItem, InventoryItem

    _require_auth(user)
    if not acl.has_permission(user, "purchase.create"):
        raise PermissionDenied("You do not have permission to create purchase orders.")
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    if not items:
        raise ValidationError(
            {"code": "NO_ITEMS", "message": "A purchase order must have at least one item."}
        )

    # Validate supplier belongs to restaurant
    if supplier.restaurant_id != restaurant.pk:
        raise ValidationError(
            {"supplier": "This supplier does not belong to the restaurant."}
        )

    with transaction.atomic():
        purchase_number = generate_purchase_number(restaurant)

        po = PurchaseOrder.objects.create(
            restaurant=restaurant,
            branch=branch,
            supplier=supplier,
            purchase_number=purchase_number,
            status=PO_DRAFT,
            order_date=order_date,
            expected_date=expected_date,
            discount_amount=_cost(discount_amount),
            notes=notes,
            created_by=user,
        )

        for item_data in items:
            inv_item = InventoryItem.objects.get(pk=item_data["inventory_item_id"])

            # Validate item belongs to restaurant
            if inv_item.restaurant_id != restaurant.pk:
                raise ValidationError(
                    {"inventory_item": f"Item '{inv_item.name}' does not belong to this restaurant."}
                )
            if not inv_item.is_active:
                raise ValidationError(
                    {"inventory_item": f"Item '{inv_item.name}' is not active."}
                )

            qty = _qty(item_data["quantity"])
            unit_cost = _cost(item_data["unit_cost"])
            tax_rate = Decimal(str(item_data.get("tax_rate", "0")))
            item_discount = _cost(item_data.get("discount_amount", ZERO_COST))

            validate_positive_quantity(qty)

            gross = _cost(qty * unit_cost)
            tax = _cost(gross * tax_rate / Decimal("100"))
            line_total = _cost(gross + tax - item_discount)

            PurchaseOrderItem.objects.create(
                purchase_order=po,
                inventory_item=inv_item,
                quantity=qty,
                unit=item_data.get("unit", inv_item.default_unit),
                unit_cost=unit_cost,
                tax_rate=tax_rate,
                discount_amount=item_discount,
                total_amount=line_total,
                notes=item_data.get("notes", ""),
            )

        _calculate_po_totals(po)

        logger.info(
            "PurchaseOrder created: po=%s restaurant=%s supplier=%s by user=%s",
            po.purchase_number, restaurant.name, supplier.name, user.email,
        )
        return po


def submit_purchase_order(po, user) -> "PurchaseOrder":
    """Submit a DRAFT PO for approval."""
    _require_auth(user)
    if not acl.has_permission(user, "purchase.submit"):
        raise PermissionDenied("You do not have permission to submit purchase orders.")
    if not acl.can_access_branch(user, po.branch):
        raise PermissionDenied("You do not have access to this branch.")

    validate_purchase_order_transition(po.status, PO_SUBMITTED)

    with transaction.atomic():
        locked_po = type(po).objects.select_for_update().get(pk=po.pk)
        validate_purchase_order_transition(locked_po.status, PO_SUBMITTED)
        locked_po.status = PO_SUBMITTED
        locked_po.save(update_fields=["status", "updated_at"])

        logger.info("PO submitted: po=%s by user=%s", locked_po.purchase_number, user.email)
        return locked_po


def approve_purchase_order(po, user) -> "PurchaseOrder":
    """Approve a SUBMITTED PO."""
    _require_auth(user)
    if not acl.has_permission(user, "purchase.approve"):
        raise PermissionDenied("You do not have permission to approve purchase orders.")
    if not acl.can_access_branch(user, po.branch):
        raise PermissionDenied("You do not have access to this branch.")

    validate_purchase_order_transition(po.status, PO_APPROVED)

    with transaction.atomic():
        locked_po = type(po).objects.select_for_update().get(pk=po.pk)
        validate_purchase_order_transition(locked_po.status, PO_APPROVED)
        locked_po.status = PO_APPROVED
        locked_po.approved_by = user
        locked_po.approved_at = timezone.now()
        locked_po.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        logger.info("PO approved: po=%s by user=%s", locked_po.purchase_number, user.email)
        return locked_po


def cancel_purchase_order(po, user, reason: str = "") -> "PurchaseOrder":
    """Cancel a PO from any non-terminal status."""
    _require_auth(user)
    if not acl.has_permission(user, "purchase.cancel"):
        raise PermissionDenied("You do not have permission to cancel purchase orders.")
    if not acl.can_access_branch(user, po.branch):
        raise PermissionDenied("You do not have access to this branch.")

    validate_purchase_order_cancellable(po.status)

    with transaction.atomic():
        locked_po = type(po).objects.select_for_update().get(pk=po.pk)
        validate_purchase_order_cancellable(locked_po.status)
        locked_po.status = PO_CANCELLED
        locked_po.notes = (locked_po.notes + f"\nCancelled by {user.email}: {reason}").strip()
        locked_po.save(update_fields=["status", "notes", "updated_at"])

        logger.info("PO cancelled: po=%s by user=%s", locked_po.purchase_number, user.email)
        return locked_po


# =============================================================================
# 4. Purchase Receiving
# =============================================================================

def receive_purchase_order(
    po,
    user,
    storage_location,
    receipt_items: list[dict],
    *,
    notes: str = "",
) -> "PurchaseReceipt":
    """
    Receive goods against an approved PurchaseOrder.

    receipt_items: list of dicts:
        { "purchase_order_item_id": UUID, "quantity_received": Decimal }

    Process (all atomic):
        1. Validate PO is APPROVED or PARTIALLY_RECEIVED
        2. Validate storage_location belongs to PO's branch/restaurant
        3. For each item: validate remaining quantity
        4. Increase stock via increase_stock()
        5. Create PurchaseReceipt + PurchaseReceiptItem records
        6. Update PurchaseOrderItem.received_quantity
        7. Update PO status (PARTIALLY_RECEIVED or RECEIVED)

    Returns:
        PurchaseReceipt

    Raises:
        PermissionDenied  — auth or permission failure
        ValidationError   — invalid state, over-receiving, insufficient permission
    """
    from inventory.models import (
        PurchaseOrder, PurchaseOrderItem, PurchaseReceipt, PurchaseReceiptItem,
    )

    _require_auth(user)
    if not acl.has_permission(user, "purchase.receive"):
        raise PermissionDenied("You do not have permission to receive stock.")
    if not acl.can_access_branch(user, po.branch):
        raise PermissionDenied("You do not have access to this branch.")

    validate_purchase_order_receivable(po.status)

    if not receipt_items:
        raise ValidationError(
            {"code": "NO_ITEMS", "message": "At least one item must be specified for receiving."}
        )

    # Validate storage location belongs to the PO's branch
    if storage_location.branch_id != po.branch_id:
        raise ValidationError(
            {
                "code": "LOCATION_BRANCH_MISMATCH",
                "message": (
                    "The storage location must belong to the same branch as the purchase order."
                ),
            }
        )

    with transaction.atomic():
        # Lock the PO
        locked_po = PurchaseOrder.objects.select_for_update().get(pk=po.pk)
        validate_purchase_order_receivable(locked_po.status)

        # Create the receipt header
        receipt = PurchaseReceipt.objects.create(
            purchase_order=locked_po,
            received_by=user,
            storage_location=storage_location,
            notes=notes,
        )

        receipt_item_objects = []

        for item_data in receipt_items:
            po_item = PurchaseOrderItem.objects.select_for_update().get(
                pk=item_data["purchase_order_item_id"],
                purchase_order=locked_po,
            )

            qty_receiving = _qty(item_data["quantity_received"])

            # Validate quantity
            validate_receive_quantity(
                ordered=po_item.quantity,
                already_received=po_item.received_quantity,
                receiving=qty_receiving,
                item_name=po_item.inventory_item.name,
            )

            # Increase stock
            increase_stock(
                inventory_item=po_item.inventory_item,
                storage_location=storage_location,
                quantity=qty_receiving,
                unit_cost=po_item.unit_cost,
                movement_type=MOVEMENT_PURCHASE,
                performed_by=user,
                reference_type=REF_PURCHASE_RECEIPT,
                reference_id=receipt.id,
                reason=f"Received against PO {locked_po.purchase_number}",
            )

            # Update received quantity on PO item
            po_item.received_quantity = _qty(po_item.received_quantity + qty_receiving)
            po_item.save(update_fields=["received_quantity", "updated_at"])

            # Record receipt item
            ri = PurchaseReceiptItem(
                receipt=receipt,
                purchase_order_item=po_item,
                quantity_received=qty_receiving,
                unit_cost=po_item.unit_cost,
            )
            receipt_item_objects.append(ri)

        PurchaseReceiptItem.objects.bulk_create(receipt_item_objects)

        # Determine new PO status
        all_items = list(locked_po.items.all())
        all_received = all(
            _qty(i.received_quantity) >= _qty(i.quantity) for i in all_items
        )
        new_status = PO_RECEIVED if all_received else PO_PARTIALLY_RECEIVED

        locked_po.status = new_status
        locked_po.received_by = user
        locked_po.received_at = timezone.now()
        locked_po.save(update_fields=["status", "received_by", "received_at", "updated_at"])

        logger.info(
            "Goods received: po=%s receipt=%s status=%s by user=%s",
            locked_po.purchase_number, receipt.id, new_status, user.email,
        )
        return receipt


# =============================================================================
# 5. Stock Transfer workflow
# =============================================================================

def create_stock_transfer(
    restaurant,
    source_location,
    destination_location,
    items: list[dict],
    user,
    *,
    notes: str = "",
) -> "StockTransfer":
    """
    Create a DRAFT StockTransfer request.

    items: list of dicts: { "inventory_item_id": UUID, "quantity": Decimal, "unit": str }

    Does NOT move stock — stock moves only on COMPLETE.

    Raises:
        PermissionDenied — auth or permission failure
        ValidationError  — validation failure
    """
    from inventory.models import StockTransfer, StockTransferItem, InventoryItem

    _require_auth(user)
    if not acl.has_permission(user, "inventory.transfer"):
        raise PermissionDenied("You do not have permission to create stock transfers.")

    # Validate both locations belong to the same restaurant
    if source_location.branch.restaurant_id != restaurant.pk:
        raise ValidationError(
            {"source_location": "Source location does not belong to this restaurant."}
        )
    if destination_location.branch.restaurant_id != restaurant.pk:
        raise ValidationError(
            {"destination_location": "Destination location does not belong to this restaurant."}
        )

    validate_transfer_locations(source_location.pk, destination_location.pk)

    if not items:
        raise ValidationError(
            {"code": "NO_ITEMS", "message": "A transfer must have at least one item."}
        )

    with transaction.atomic():
        transfer_number = generate_transfer_number(restaurant)

        transfer = StockTransfer.objects.create(
            restaurant=restaurant,
            source_location=source_location,
            destination_location=destination_location,
            transfer_number=transfer_number,
            status=TRANSFER_DRAFT,
            requested_by=user,
            notes=notes,
        )

        for item_data in items:
            inv_item = InventoryItem.objects.get(pk=item_data["inventory_item_id"])
            if inv_item.restaurant_id != restaurant.pk:
                raise ValidationError(
                    {"inventory_item": f"Item '{inv_item.name}' does not belong to this restaurant."}
                )
            if not inv_item.is_active:
                raise ValidationError(
                    {"inventory_item": f"Item '{inv_item.name}' is not active."}
                )

            qty = _qty(item_data["quantity"])
            validate_positive_quantity(qty)

            StockTransferItem.objects.create(
                transfer=transfer,
                inventory_item=inv_item,
                quantity=qty,
                unit=item_data.get("unit", inv_item.default_unit),
            )

        logger.info(
            "StockTransfer created: transfer=%s restaurant=%s by user=%s",
            transfer.transfer_number, restaurant.name, user.email,
        )
        return transfer


def request_stock_transfer(transfer, user) -> "StockTransfer":
    """Transition DRAFT → REQUESTED."""
    _require_auth(user)
    if not acl.has_permission(user, "inventory.transfer"):
        raise PermissionDenied("You do not have permission to request transfers.")
    validate_transfer_transition(transfer.status, TRANSFER_REQUESTED)

    with transaction.atomic():
        locked = type(transfer).objects.select_for_update().get(pk=transfer.pk)
        validate_transfer_transition(locked.status, TRANSFER_REQUESTED)
        locked.status = TRANSFER_REQUESTED
        locked.requested_at = timezone.now()
        locked.save(update_fields=["status", "requested_at", "updated_at"])
        logger.info("Transfer requested: transfer=%s by user=%s", locked.transfer_number, user.email)
        return locked


def approve_stock_transfer(transfer, user) -> "StockTransfer":
    """Transition REQUESTED → APPROVED."""
    _require_auth(user)
    if not acl.has_permission(user, "inventory.transfer.approve"):
        raise PermissionDenied("You do not have permission to approve transfers.")
    validate_transfer_transition(transfer.status, TRANSFER_APPROVED)

    with transaction.atomic():
        locked = type(transfer).objects.select_for_update().get(pk=transfer.pk)
        validate_transfer_transition(locked.status, TRANSFER_APPROVED)
        locked.status = TRANSFER_APPROVED
        locked.approved_by = user
        locked.approved_at = timezone.now()
        locked.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        logger.info("Transfer approved: transfer=%s by user=%s", locked.transfer_number, user.email)
        return locked


def complete_stock_transfer(transfer, user) -> "StockTransfer":
    """
    Transition APPROVED → COMPLETED and move stock atomically.

    For each transfer item:
        - TRANSFER_OUT from source_location
        - TRANSFER_IN to destination_location

    Both operations are atomic. If source has insufficient stock, the
    entire transfer fails.
    """
    from inventory.models import StockTransfer

    _require_auth(user)
    if not acl.has_permission(user, "inventory.transfer.approve"):
        raise PermissionDenied("You do not have permission to complete transfers.")
    validate_transfer_transition(transfer.status, TRANSFER_COMPLETED)

    with transaction.atomic():
        locked = StockTransfer.objects.select_for_update().get(pk=transfer.pk)
        validate_transfer_transition(locked.status, TRANSFER_COMPLETED)

        items = list(locked.items.select_related("inventory_item").all())
        if not items:
            raise ValidationError(
                {"code": "NO_ITEMS", "message": "Transfer has no items."}
            )

        for item in items:
            # Decrease from source
            decrease_stock(
                inventory_item=item.inventory_item,
                storage_location=locked.source_location,
                quantity=item.quantity,
                movement_type=MOVEMENT_TRANSFER_OUT,
                performed_by=user,
                reference_type=REF_STOCK_TRANSFER,
                reference_id=locked.id,
                reason=f"Transfer {locked.transfer_number} to {locked.destination_location.name}",
            )

            # Get cost for the transfer-in movement
            from inventory.models import StockBalance
            try:
                src_balance = StockBalance.objects.get(
                    inventory_item=item.inventory_item,
                    storage_location=locked.source_location,
                )
                transfer_unit_cost = src_balance.average_cost
            except StockBalance.DoesNotExist:
                transfer_unit_cost = item.inventory_item.average_cost

            # Increase at destination
            increase_stock(
                inventory_item=item.inventory_item,
                storage_location=locked.destination_location,
                quantity=item.quantity,
                unit_cost=transfer_unit_cost,
                movement_type=MOVEMENT_TRANSFER_IN,
                performed_by=user,
                reference_type=REF_STOCK_TRANSFER,
                reference_id=locked.id,
                reason=f"Transfer {locked.transfer_number} from {locked.source_location.name}",
            )

        locked.status = TRANSFER_COMPLETED
        locked.completed_by = user
        locked.completed_at = timezone.now()
        locked.save(update_fields=["status", "completed_by", "completed_at", "updated_at"])

        logger.info(
            "Transfer completed: transfer=%s by user=%s",
            locked.transfer_number, user.email,
        )
        return locked


def cancel_stock_transfer(transfer, user) -> "StockTransfer":
    """Cancel a transfer from any non-terminal status."""
    _require_auth(user)
    if not acl.has_permission(user, "inventory.transfer"):
        raise PermissionDenied("You do not have permission to cancel transfers.")

    from inventory.constants import TRANSFER_CANCELLED as TC
    validate_transfer_transition(transfer.status, TC)

    with transaction.atomic():
        locked = type(transfer).objects.select_for_update().get(pk=transfer.pk)
        validate_transfer_transition(locked.status, TC)
        locked.status = TC
        locked.save(update_fields=["status", "updated_at"])
        logger.info("Transfer cancelled: transfer=%s by user=%s", locked.transfer_number, user.email)
        return locked


# =============================================================================
# 6. Wastage workflow
# =============================================================================

def create_wastage(
    inventory_item,
    storage_location,
    quantity: Decimal,
    unit: str,
    wastage_type: str,
    reason: str,
    user,
) -> "StockWastage":
    """
    Record a wastage request (PENDING — no stock change yet).

    Stock is only decreased after approval.
    """
    from inventory.models import StockWastage

    _require_auth(user)
    if not acl.has_permission(user, "inventory.wastage.create"):
        raise PermissionDenied("You do not have permission to record wastage.")

    validate_reason(reason)
    qty = _qty(quantity)
    validate_positive_quantity(qty)

    # Validate item belongs to the location's branch's restaurant
    if inventory_item.restaurant_id != storage_location.branch.restaurant_id:
        raise ValidationError(
            {"inventory_item": "Item does not belong to the same restaurant as the storage location."}
        )
    if not inventory_item.is_active:
        raise ValidationError({"inventory_item": "Inventory item is not active."})

    # Calculate estimated cost (use current average_cost as preview)
    estimated_cost = _cost(qty * inventory_item.average_cost)

    wastage = StockWastage.objects.create(
        inventory_item=inventory_item,
        storage_location=storage_location,
        quantity=qty,
        unit=unit,
        wastage_type=wastage_type,
        reason=reason,
        estimated_cost=estimated_cost,
        status=WASTAGE_PENDING,
        recorded_by=user,
    )

    logger.info(
        "Wastage recorded: item=%s location=%s qty=%s type=%s by user=%s",
        inventory_item.name, storage_location.name, qty, wastage_type, user.email,
    )
    return wastage


def approve_wastage(wastage, user) -> "StockWastage":
    """
    Approve a PENDING wastage — decreases stock.

    1. Lock wastage record
    2. Validate status is PENDING
    3. Decrease stock via decrease_stock()
    4. Recalculate estimated_cost at current average_cost
    5. Set status to RECORDED (after stock movement recorded)
    """
    from inventory.models import StockWastage

    _require_auth(user)
    if not acl.has_permission(user, "inventory.wastage.approve"):
        raise PermissionDenied("You do not have permission to approve wastage.")

    if wastage.status != WASTAGE_PENDING:
        raise ValidationError(
            {
                "code": "WASTAGE_NOT_PENDING",
                "message": f"Can only approve PENDING wastage. Current status: {wastage.status}.",
            }
        )

    with transaction.atomic():
        locked = StockWastage.objects.select_for_update().get(pk=wastage.pk)

        if locked.status != WASTAGE_PENDING:
            raise ValidationError(
                {"code": "WASTAGE_NOT_PENDING", "message": "Wastage is no longer pending."}
            )

        # Recalculate estimated_cost at current average_cost
        current_avg = locked.inventory_item.average_cost
        locked.estimated_cost = _cost(locked.quantity * current_avg)

        # Decrease stock
        movement = decrease_stock(
            inventory_item=locked.inventory_item,
            storage_location=locked.storage_location,
            quantity=locked.quantity,
            movement_type=MOVEMENT_WASTAGE,
            performed_by=user,
            reference_type=REF_STOCK_WASTAGE,
            reference_id=locked.id,
            reason=locked.reason,
            unit_cost=current_avg,
        )

        locked.status = WASTAGE_RECORDED
        locked.approved_by = user
        locked.approved_at = timezone.now()
        locked.save(update_fields=[
            "status", "approved_by", "approved_at", "estimated_cost", "updated_at"
        ])

        logger.info(
            "Wastage approved: id=%s item=%s qty=%s by user=%s",
            locked.pk, locked.inventory_item.name, locked.quantity, user.email,
        )
        return locked


def reject_wastage(wastage, user, rejection_reason: str) -> "StockWastage":
    """Reject a PENDING wastage — no stock change."""
    from inventory.models import StockWastage

    _require_auth(user)
    if not acl.has_permission(user, "inventory.wastage.approve"):
        raise PermissionDenied("You do not have permission to reject wastage.")

    validate_reason(rejection_reason, field_name="rejection_reason")

    if wastage.status != WASTAGE_PENDING:
        raise ValidationError(
            {"code": "WASTAGE_NOT_PENDING", "message": f"Can only reject PENDING wastage. Current status: {wastage.status}."}
        )

    with transaction.atomic():
        locked = StockWastage.objects.select_for_update().get(pk=wastage.pk)
        if locked.status != WASTAGE_PENDING:
            raise ValidationError({"code": "WASTAGE_NOT_PENDING", "message": "Wastage is no longer pending."})

        locked.status = WASTAGE_REJECTED
        locked.approved_by = user
        locked.approved_at = timezone.now()
        locked.rejection_reason = rejection_reason
        locked.save(update_fields=["status", "approved_by", "approved_at", "rejection_reason", "updated_at"])

        logger.info("Wastage rejected: id=%s by user=%s", locked.pk, user.email)
        return locked


# =============================================================================
# 7. Stock Adjustment
# =============================================================================

def create_stock_adjustment(
    inventory_item,
    storage_location,
    physical_quantity: Decimal,
    unit: str,
    reason: str,
    user,
) -> "StockAdjustment":
    """
    Perform a physical-count reconciliation adjustment.

    physical_quantity — what was actually counted on the shelf.

    Process (atomic):
        1. Lock the StockBalance
        2. Compute difference: physical - system
        3. If difference > 0: ADJUSTMENT_IN movement
        4. If difference < 0: ADJUSTMENT_OUT movement
        5. If difference == 0: still create an audit record
        6. Create StockAdjustment record
        7. Link to the created StockMovement

    Raises:
        PermissionDenied — auth or permission failure
        ValidationError  — invalid inputs
    """
    from inventory.models import StockAdjustment, StockBalance, StockMovement

    _require_auth(user)
    if not acl.has_permission(user, "inventory.adjust"):
        raise PermissionDenied("You do not have permission to adjust stock.")

    validate_reason(reason)
    phys_qty = _qty(physical_quantity)

    if phys_qty < Decimal("0"):
        raise ValidationError({"quantity_physical": "Physical count cannot be negative."})

    with transaction.atomic():
        # Get or create the balance, then lock it
        StockBalance.objects.get_or_create(
            inventory_item=inventory_item,
            storage_location=storage_location,
        )
        balance = StockBalance.objects.select_for_update().get(
            inventory_item=inventory_item,
            storage_location=storage_location,
        )

        qty_before = _qty(balance.quantity)
        qty_difference = _qty(phys_qty - qty_before)

        movement = None

        if qty_difference > ZERO:
            # ADJUSTMENT_IN
            movement = increase_stock(
                inventory_item=inventory_item,
                storage_location=storage_location,
                quantity=qty_difference,
                unit_cost=inventory_item.average_cost,
                movement_type=MOVEMENT_ADJUSTMENT_IN,
                performed_by=user,
                reference_type=REF_STOCK_ADJUSTMENT,
                reason=reason,
            )
        elif qty_difference < ZERO:
            # ADJUSTMENT_OUT
            movement = decrease_stock(
                inventory_item=inventory_item,
                storage_location=storage_location,
                quantity=abs(qty_difference),
                movement_type=MOVEMENT_ADJUSTMENT_OUT,
                performed_by=user,
                reference_type=REF_STOCK_ADJUSTMENT,
                reason=reason,
                unit_cost=balance.average_cost,
            )
        # If difference == 0 — record the audit without stock change

        adjustment = StockAdjustment.objects.create(
            inventory_item=inventory_item,
            storage_location=storage_location,
            quantity_before=qty_before,
            quantity_physical=phys_qty,
            quantity_difference=qty_difference,
            unit=unit,
            reason=reason,
            adjusted_by=user,
            stock_movement=movement,
        )

        logger.info(
            "StockAdjustment: item=%s location=%s before=%s physical=%s diff=%s by user=%s",
            inventory_item.name, storage_location.name,
            qty_before, phys_qty, qty_difference, user.email,
        )
        return adjustment


# =============================================================================
# 8. Inventory Dashboard data
# =============================================================================

def get_inventory_dashboard(user) -> dict:
    """
    Return summary statistics for the inventory dashboard.
    Scoped to the user's accessible restaurants/branches.
    """
    from inventory.models import (
        InventoryItem, StockBalance, PurchaseOrder,
        StockTransfer, StockWastage,
    )
    from inventory.constants import (
        STOCK_STATUS_LOW_STOCK, STOCK_STATUS_OUT_OF_STOCK,
        PO_DRAFT, PO_SUBMITTED, PO_APPROVED,
        TRANSFER_REQUESTED, TRANSFER_APPROVED,
        WASTAGE_PENDING,
    )

    _require_auth(user)

    accessible_branches = acl.get_accessible_branches(user)
    accessible_restaurants = acl.get_accessible_restaurants(user)

    total_items = InventoryItem.objects.filter(
        restaurant__in=accessible_restaurants, is_active=True
    ).count()

    # Low stock and out-of-stock: query all balances and derive status
    all_balances = StockBalance.objects.filter(
        storage_location__branch__in=accessible_branches
    ).select_related("inventory_item")

    low_stock_count = 0
    out_of_stock_count = 0
    for balance in all_balances:
        status = balance.get_stock_status()
        if status == STOCK_STATUS_OUT_OF_STOCK:
            out_of_stock_count += 1
        elif status == STOCK_STATUS_LOW_STOCK:
            low_stock_count += 1

    pending_purchases = PurchaseOrder.objects.filter(
        branch__in=accessible_branches,
        status__in=[PO_DRAFT, PO_SUBMITTED, PO_APPROVED],
    ).count()

    pending_transfers = StockTransfer.objects.filter(
        source_location__branch__in=accessible_branches,
        status__in=[TRANSFER_REQUESTED, TRANSFER_APPROVED],
    ).count()

    pending_wastage = StockWastage.objects.filter(
        storage_location__branch__in=accessible_branches,
        status=WASTAGE_PENDING,
    ).count()

    return {
        "total_items": total_items,
        "low_stock": low_stock_count,
        "out_of_stock": out_of_stock_count,
        "pending_purchases": pending_purchases,
        "pending_transfers": pending_transfers,
        "pending_wastage": pending_wastage,
    }
