# =============================================================================
# RestaurantFlow — Billing Services
# Phase 8
#
# All business logic for the billing lifecycle lives here.
# Views call these; serializers validate input shapes only.
#
# Public API:
#   generate_bill_number(branch)                          → str
#   create_bill_from_order(order, user)                   → Bill
#   calculate_bill(bill)                                  → BillCalculation dict
#   apply_discount(bill, user, discount_type, value, max_pct) → Bill
#   remove_discount(bill, user)                           → Bill
#   finalize_bill(bill, user)                             → Bill
#   cancel_bill(bill, user, reason)                       → Bill
#   void_bill(bill, user, reason)                         → Bill
#   request_bill_correction(bill, user, correction_type, reason) → BillCorrectionRequest
#   approve_bill_correction(correction, reviewer, note)   → BillCorrectionRequest
#   reject_bill_correction(correction, reviewer, note)    → BillCorrectionRequest
#   cancel_bill_correction(correction, user)              → BillCorrectionRequest
#   get_bill_receipt_data(bill)                           → dict
#
# Concurrency:
#   - generate_bill_number uses select_for_update() — never MAX()+1.
#   - create_bill_from_order locks the Order with select_for_update().
#   - finalize_bill locks the Bill with select_for_update().
#   - approve/reject_correction locks the correction with select_for_update().
#   - All mutating operations are wrapped in transaction.atomic().
#
# Calculation sequence (authoritative — mirrors billing/utils.py):
#   1. Per BillItem: gross = quantity × unit_price
#   2. Bill-level discount applied to subtotal
#   3. Proportional tax discount adjustment per item
#   4. Per-item: tax = (gross × (1 - discount_ratio)) × tax_rate / 100
#   5. subtotal = sum(gross)
#   6. taxable_amount = subtotal - discount_amount
#   7. tax_amount = sum(per-item tax)
#   8. Rounding: adjust to nearest whole number
#   9. grand_total = taxable_amount + tax_amount + rounding_amount
#
# Security:
#   - Branch access validated for every operation.
#   - Permission codes checked (see billing/permissions.py).
#   - Frontend totals are NEVER trusted — backend recalculates.
#   - IDOR prevention: caller must pass the Bill object (not just an ID).
# =============================================================================

import logging
from decimal import Decimal, IntegrityError as DecimalIntegrityError
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from billing import utils as money_utils
from billing.validators import (
    validate_bill_is_draft,
    validate_bill_is_finalizable,
    validate_discount_type,
    validate_percentage_discount,
    validate_fixed_discount,
    validate_correction_reason,
    validate_self_approval,
    validate_rounding_amount,
)

logger = logging.getLogger("billing")

ZERO = Decimal("0.00")


# =============================================================================
# Internal helpers
# =============================================================================

def _require_auth(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


def _get_branch_year_key(branch) -> str:
    """Return the current year as 4-char string in the branch's configured timezone."""
    tz_name = _get_branch_timezone(branch)
    now = timezone.now()
    try:
        tz = ZoneInfo(tz_name)
        local_now = now.astimezone(tz)
    except (ZoneInfoNotFoundError, Exception):
        local_now = now
    return local_now.strftime("%Y")


def _get_branch_timezone(branch) -> str:
    """Return the effective timezone string for a branch (mirrors orders/services.py)."""
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


# =============================================================================
# 1. Bill Number Generation
# =============================================================================

def generate_bill_number(branch) -> str:
    """
    Generate a concurrency-safe, human-readable bill number.

    Format: B-{YYYY}-{seq:06d}
    Examples:
        B-2026-000001
        B-2026-000042
        B-2027-000001  (resets annually)

    Sequence resets annually per branch.
    Uses select_for_update() to prevent race conditions.
    Must be called inside a transaction.atomic() block.

    Never uses MAX()+1 — race-condition-safe via database-level locking.
    """
    from billing.models import BillSequence

    year_key = _get_branch_year_key(branch)

    try:
        seq_obj = BillSequence.objects.select_for_update().get(
            branch=branch,
            year_key=year_key,
        )
        seq_obj.last_sequence += 1
        seq_obj.save(update_fields=["last_sequence", "updated_at"])
    except BillSequence.DoesNotExist:
        # First bill of the year for this branch
        try:
            seq_obj, created = BillSequence.objects.get_or_create(
                branch=branch,
                year_key=year_key,
                defaults={"last_sequence": 1},
            )
            if not created:
                # Another concurrent request created it first
                seq_obj = BillSequence.objects.select_for_update().get(
                    branch=branch,
                    year_key=year_key,
                )
                seq_obj.last_sequence += 1
                seq_obj.save(update_fields=["last_sequence", "updated_at"])
        except IntegrityError:
            # Concurrent creation — fetch and increment
            seq_obj = BillSequence.objects.select_for_update().get(
                branch=branch,
                year_key=year_key,
            )
            seq_obj.last_sequence += 1
            seq_obj.save(update_fields=["last_sequence", "updated_at"])

    return f"B-{year_key}-{seq_obj.last_sequence:06d}"


# =============================================================================
# 2. Bill Creation
# =============================================================================

def create_bill_from_order(order, user) -> "Bill":
    """
    Create a Bill (and BillItems) from a confirmed Order.

    This is the entry point for the cashier's billing flow.

    Process:
        1. Validate user authentication.
        2. Validate permission: bill.create
        3. Validate branch access.
        4. Lock the Order with select_for_update() (concurrent protection).
        5. Validate order status (CONFIRMED only).
        6. Check no existing Bill for this order (idempotent: return existing).
        7. Generate bill number inside atomic block.
        8. Read all OrderItems.
        9. Create Bill (DRAFT status).
        10. Create BillItems from OrderItem snapshots.
        11. Run initial calculate_bill().
        12. Return the draft Bill.

    Eligible order types:
        - DINE_IN:  Order must be CONFIRMED.
        - TAKEAWAY: Order must be CONFIRMED.
        - COUNTER:  Order must be CONFIRMED.

    NOT eligible:
        - DRAFT orders → ValidationError
        - CANCELLED orders → ValidationError

    Note: Kitchen state is intentionally NOT checked here.
        Kitchen operations and billing are separated concerns.
        A manager may generate a bill before kitchen marks all items READY
        in certain takeaway/counter workflows.

    Returns:
        Bill (DRAFT status with items calculated)

    Raises:
        PermissionDenied — auth or permission failure
        ValidationError  — ineligible order, missing items, etc.
    """
    from orders.models import OrderStatus, Order
    from billing.models import Bill, BillItem

    _require_auth(user)

    if not acl.has_permission(user, "bill.create"):
        raise PermissionDenied("You do not have permission to create bills.")

    if not acl.can_access_branch(user, order.branch):
        raise PermissionDenied("You do not have access to this order's branch.")

    try:
        with transaction.atomic():
            # Lock the order — prevent concurrent bill creation
            locked_order = Order.objects.select_for_update().get(pk=order.pk)

            # Validate order status
            if locked_order.status == OrderStatus.DRAFT:
                raise ValidationError(
                    {
                        "code": "ORDER_DRAFT",
                        "message": (
                            "Cannot create a bill for a DRAFT order. "
                            "Confirm the order before billing."
                        ),
                    }
                )
            if locked_order.status == OrderStatus.CANCELLED:
                raise ValidationError(
                    {
                        "code": "ORDER_CANCELLED",
                        "message": "Cannot create a bill for a CANCELLED order.",
                    }
                )

            # Idempotency — if bill already exists, return it
            try:
                existing = Bill.objects.get(order=locked_order)
                logger.info(
                    "Bill already exists for order=%s bill=%s — returning existing",
                    locked_order.order_number,
                    existing.bill_number,
                )
                return existing
            except Bill.DoesNotExist:
                pass

            # Verify the order has items
            order_items = list(
                locked_order.items.select_related("menu_item").all()
            )
            if not order_items:
                raise ValidationError(
                    {
                        "code": "ORDER_HAS_NO_ITEMS",
                        "message": "Cannot create a bill for an order with no items.",
                    }
                )

            # Generate bill number (inside the atomic block)
            bill_number = generate_bill_number(locked_order.branch)

            # Create the Bill (DRAFT)
            bill = Bill.objects.create(
                order=locked_order,
                branch=locked_order.branch,
                bill_number=bill_number,
                created_by=user,
            )

            # Create BillItems from OrderItem snapshots
            bill_items = []
            for oi in order_items:
                qty = oi.quantity
                unit_price = oi.unit_price_snapshot
                tax_rate = oi.tax_rate_snapshot  # Decimal(6,3), e.g. 5.000
                tax_code = oi.tax_code_snapshot  # e.g. "GST_STANDARD"

                gross = money_utils.compute_gross(qty, unit_price)

                bi = BillItem(
                    bill=bill,
                    order_item=oi,
                    menu_item=oi.menu_item,
                    item_name_snapshot=oi.item_name_snapshot,
                    sku_snapshot=oi.sku_snapshot,
                    quantity=qty,
                    unit_price=unit_price,
                    gross_amount=gross,
                    discount_amount=money_utils.ZERO,
                    taxable_amount=gross,  # will be recalculated with discount
                    tax_rate=tax_rate,
                    tax_code=tax_code,
                    tax_amount=money_utils.ZERO,  # will be calculated
                    total_amount=gross,  # will be recalculated
                )
                bill_items.append(bi)

            BillItem.objects.bulk_create(bill_items)

            # Initial calculation (no discount yet)
            _calculate_and_save_bill(bill)

            logger.info(
                "Bill created: bill=%s order=%s branch=%s by user=%s",
                bill.bill_number,
                locked_order.order_number,
                locked_order.branch.name,
                user.email,
            )
            return bill

    except IntegrityError:
        # DB-level unique constraint on order — concurrent creation
        logger.warning(
            "Concurrent bill creation for order=%s — returning existing bill",
            order.order_number,
        )
        return Bill.objects.get(order=order)


# =============================================================================
# 3. Bill Calculation
# =============================================================================

def _calculate_and_save_bill(bill) -> dict:
    """
    Internal: recalculate all bill totals and persist to DB.

    This is called by calculate_bill (public) and finalize_bill.
    The bill must already have BillItems.

    Returns a dict with all calculated values (same as calculate_bill()).
    """
    result = _compute_bill_totals(bill)

    # Update all BillItem amounts
    from billing.models import BillItem
    items = list(bill.items.all())

    # Compute discount ratio for proportional tax adjustment
    # Use unrounded full precision to minimize rounding propagation per item
    subtotal = result["subtotal"]
    discount_amount = result["discount_amount"]
    discount_ratio = (
        (discount_amount / subtotal)
        if subtotal > ZERO
        else Decimal("0")
    )

    for item in items:
        gross = money_utils.compute_gross(item.quantity, item.unit_price)
        item_discount = money_utils.money(gross * discount_ratio)
        item_taxable = money_utils.money(gross - item_discount)
        item_tax = money_utils.compute_tax(item_taxable, item.tax_rate)
        item_total = money_utils.money(item_taxable + item_tax)

        item.gross_amount = gross
        item.discount_amount = item_discount
        item.taxable_amount = item_taxable
        item.tax_amount = item_tax
        item.total_amount = item_total

    BillItem.objects.bulk_update(
        items,
        ["gross_amount", "discount_amount", "taxable_amount", "tax_amount", "total_amount"],
    )

    # Update Bill financial fields
    bill.subtotal = result["subtotal"]
    bill.discount_amount = result["discount_amount"]
    bill.taxable_amount = result["taxable_amount"]
    bill.tax_amount = result["tax_amount"]
    bill.tax_breakdown = result["tax_breakdown"]
    bill.rounding_amount = result["rounding_amount"]
    bill.grand_total = result["grand_total"]
    bill.save(update_fields=[
        "subtotal", "discount_amount", "taxable_amount",
        "tax_amount", "tax_breakdown", "rounding_amount", "grand_total",
        "updated_at",
    ])

    return result


def _compute_bill_totals(bill) -> dict:
    """
    Pure computation of bill totals from current BillItems and discount.

    Does NOT save to the database — use _calculate_and_save_bill() for that.

    Returns:
    {
        "subtotal":        Decimal,
        "discount_amount": Decimal,
        "taxable_amount":  Decimal,
        "tax_amount":      Decimal,
        "tax_breakdown":   dict[str, str],
        "rounding_amount": Decimal,
        "grand_total":     Decimal,
    }
    """
    items = list(bill.items.all())

    # 1. Subtotal = sum of gross amounts (before discount)
    subtotal = money_utils.ZERO
    for item in items:
        subtotal += money_utils.compute_gross(item.quantity, item.unit_price)
    subtotal = money_utils.money(subtotal)

    # 2. Discount
    from billing.models import DiscountType
    discount_amount = ZERO
    if bill.discount_type == DiscountType.PERCENTAGE and bill.discount_value > ZERO:
        discount_amount = money_utils.compute_percentage_discount(
            subtotal, bill.discount_value
        )
    elif bill.discount_type == DiscountType.FIXED_AMOUNT and bill.discount_value > ZERO:
        discount_amount = money_utils.compute_fixed_discount(
            subtotal, bill.discount_value
        )

    # 3. Taxable amount
    taxable_amount = money_utils.money(subtotal - discount_amount)

    # 4. Tax — proportional per item (discount reduces taxable amount proportionally)
    # Use full Decimal precision for ratio to avoid per-item rounding drift
    discount_ratio = (
        (discount_amount / subtotal)
        if subtotal > ZERO
        else Decimal("0")
    )

    tax_items = []
    total_tax = ZERO
    for item in items:
        gross = money_utils.compute_gross(item.quantity, item.unit_price)
        item_discount = money_utils.money(gross * discount_ratio)
        item_taxable = money_utils.money(gross - item_discount)
        item_tax = money_utils.compute_tax(item_taxable, item.tax_rate)
        total_tax = money_utils.money(total_tax + item_tax)
        tax_items.append({"tax_code": item.tax_code, "tax_amount": item_tax})

    tax_amount = total_tax
    tax_breakdown = money_utils.build_tax_breakdown(tax_items)

    # 5. Pre-rounding total
    pre_rounding = money_utils.money(taxable_amount + tax_amount)

    # 6. Rounding
    rounding_amount = money_utils.compute_rounding(pre_rounding)
    validate_rounding_amount(rounding_amount)

    # 7. Grand total
    grand_total = money_utils.money(pre_rounding + rounding_amount)

    return {
        "subtotal":        subtotal,
        "discount_amount": discount_amount,
        "taxable_amount":  taxable_amount,
        "tax_amount":      tax_amount,
        "tax_breakdown":   tax_breakdown,
        "rounding_amount": rounding_amount,
        "grand_total":     grand_total,
    }


def calculate_bill(bill) -> dict:
    """
    Public: recalculate all bill totals.

    Does not require the bill to be DRAFT for preview purposes.
    For DRAFT bills, saves the result.
    For FINALIZED bills, returns a preview (does NOT overwrite).

    Returns:
    {
        "subtotal":        str,
        "discount_amount": str,
        "taxable_amount":  str,
        "tax_amount":      str,
        "tax_breakdown":   dict[str, str],
        "rounding_amount": str,
        "grand_total":     str,
    }
    """
    from billing.models import BillStatus
    result = _compute_bill_totals(bill)

    if bill.status == BillStatus.DRAFT:
        _calculate_and_save_bill(bill)

    return {k: str(v) if isinstance(v, Decimal) else v for k, v in result.items()}


# =============================================================================
# 4. Apply / Remove Discount
# =============================================================================

def apply_discount(bill, user, *, discount_type: str, value, max_pct: Decimal = Decimal("100")) -> "Bill":
    """
    Apply a discount to a DRAFT bill.

    Args:
        bill:          The Bill to apply the discount to. Must be DRAFT.
        user:          The actor applying the discount.
        discount_type: "PERCENTAGE" or "FIXED_AMOUNT"
        value:         The discount value (percentage % or fixed amount ₹).
        max_pct:       Maximum percentage this user is authorized to apply.
                       Only relevant for PERCENTAGE type.
                       Configured per role — do NOT hard-code role names here.

    Process:
        1. Validate user auth and permission.
        2. Validate bill is DRAFT.
        3. Validate discount_type.
        4. Validate value within allowed bounds.
        5. Apply discount and recalculate.

    Returns the updated Bill.

    Security:
        - Callers must pass max_pct based on the user's role configuration.
        - Large discounts require bill.discount.apply_large permission
          (checked by the view/caller, not this function).
        - This function validates the value but does NOT check permissions
          beyond bill.discount.apply — the view layer splits permission checks.
    """
    from billing.models import DiscountType

    _require_auth(user)

    if not acl.has_permission(user, "discount.apply"):
        raise PermissionDenied("You do not have permission to apply discounts.")

    if not acl.can_access_branch(user, bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    validate_bill_is_draft(bill)
    validated_type = validate_discount_type(discount_type)

    from billing.utils import ZERO as _ZERO, ONE_HUNDRED

    val = Decimal(str(value))

    if validated_type == DiscountType.PERCENTAGE:
        validate_percentage_discount(val, max_pct)
    else:
        # For fixed: we need the current subtotal to validate cap
        # Calculate subtotal first without saving
        items = list(bill.items.all())
        subtotal = sum(
            money_utils.compute_gross(i.quantity, i.unit_price) for i in items
        )
        validate_fixed_discount(val, money_utils.money(subtotal))

    with transaction.atomic():
        locked_bill = type(bill).objects.select_for_update().get(pk=bill.pk)
        validate_bill_is_draft(locked_bill)

        locked_bill.discount_type = validated_type
        locked_bill.discount_value = money_utils.money(val)
        locked_bill.save(update_fields=["discount_type", "discount_value", "updated_at"])

        _calculate_and_save_bill(locked_bill)

    logger.info(
        "Discount applied: bill=%s type=%s value=%s by user=%s",
        bill.bill_number, validated_type, val, user.email,
    )

    # Refresh from DB to return the latest state
    bill.refresh_from_db()
    return bill


def remove_discount(bill, user) -> "Bill":
    """
    Remove any applied discount from a DRAFT bill.

    Returns the updated Bill.
    """
    _require_auth(user)

    if not acl.has_permission(user, "discount.apply"):
        raise PermissionDenied("You do not have permission to modify discounts.")

    if not acl.can_access_branch(user, bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    validate_bill_is_draft(bill)

    with transaction.atomic():
        locked_bill = type(bill).objects.select_for_update().get(pk=bill.pk)
        validate_bill_is_draft(locked_bill)

        locked_bill.discount_type = None
        locked_bill.discount_value = ZERO
        locked_bill.save(update_fields=["discount_type", "discount_value", "updated_at"])

        _calculate_and_save_bill(locked_bill)

    bill.refresh_from_db()
    return bill


# =============================================================================
# 5. Bill Finalization
# =============================================================================

def finalize_bill(bill, user) -> "Bill":
    """
    Finalize a DRAFT bill — making it immutable.

    Process:
        1. Validate auth and permission.
        2. Validate bill is DRAFT and has items.
        3. Lock bill with select_for_update().
        4. Recalculate totals one final time (prevents stale data).
        5. Validate discount (within limits).
        6. Validate tax (non-negative).
        7. Validate rounding.
        8. Set status = FINALIZED, finalized_by, finalized_at.
        9. Save.

    After finalization:
        - The bill's financial fields are immutable.
        - Corrections require BillCorrectionRequest workflow.
        - Payment (Phase 9) will reference the finalized bill.

    Idempotent: if already FINALIZED, returns the bill without error.
    """
    from billing.models import BillStatus

    _require_auth(user)

    if not acl.has_permission(user, "bill.finalize"):
        raise PermissionDenied("You do not have permission to finalize bills.")

    if not acl.can_access_branch(user, bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    # Idempotent
    if bill.status == BillStatus.FINALIZED:
        logger.info("Bill %s already finalized — returning as-is.", bill.bill_number)
        return bill

    validate_bill_is_finalizable(bill)

    with transaction.atomic():
        locked_bill = type(bill).objects.select_for_update().get(pk=bill.pk)

        # Idempotent check inside lock
        if locked_bill.status == BillStatus.FINALIZED:
            return locked_bill

        validate_bill_is_finalizable(locked_bill)

        # Final recalculation
        _calculate_and_save_bill(locked_bill)

        # Validate tax is non-negative
        if locked_bill.tax_amount < ZERO:
            raise ValidationError(
                {
                    "code": "NEGATIVE_TAX",
                    "message": "Tax amount cannot be negative. Cannot finalize bill.",
                }
            )

        # Validate grand_total is non-negative
        if locked_bill.grand_total < ZERO:
            raise ValidationError(
                {
                    "code": "NEGATIVE_GRAND_TOTAL",
                    "message": "Grand total cannot be negative. Cannot finalize bill.",
                }
            )

        locked_bill.status = BillStatus.FINALIZED
        locked_bill.finalized_by = user
        locked_bill.finalized_at = timezone.now()
        locked_bill.save(update_fields=[
            "status", "finalized_by", "finalized_at", "updated_at"
        ])

    logger.info(
        "Bill finalized: bill=%s total=%s by user=%s",
        locked_bill.bill_number,
        locked_bill.grand_total,
        user.email,
    )

    bill.refresh_from_db()
    return bill


# =============================================================================
# 6. Bill Cancellation / Void
# =============================================================================

def cancel_bill(bill, user, *, reason: str) -> "Bill":
    """
    Cancel a DRAFT or FINALIZED bill.

    DRAFT bills: may be cancelled freely (with reason).
    FINALIZED bills: require bill.cancel permission.

    A finalized bill cannot be deleted — it receives CANCELLED status.
    This is critical for audit trails.

    If cancelled after a payment (Phase 9 concern), the payment
    reconciliation must account for this — tracked via bill status.
    """
    from billing.models import BillStatus

    _require_auth(user)

    if not acl.has_permission(user, "bill.cancel"):
        raise PermissionDenied("You do not have permission to cancel bills.")

    if not acl.can_access_branch(user, bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    if not reason or not reason.strip():
        raise ValidationError(
            {"reason": "A cancellation reason is required."}
        )

    if bill.status in (BillStatus.CANCELLED, BillStatus.VOID):
        raise ValidationError(
            {
                "code": "BILL_ALREADY_TERMINAL",
                "message": f"Bill is already in {bill.status} status.",
            }
        )

    with transaction.atomic():
        locked_bill = type(bill).objects.select_for_update().get(pk=bill.pk)

        if locked_bill.status in (BillStatus.CANCELLED, BillStatus.VOID):
            raise ValidationError(
                {
                    "code": "BILL_ALREADY_TERMINAL",
                    "message": f"Bill is already in {locked_bill.status} status.",
                }
            )

        locked_bill.status = BillStatus.CANCELLED
        locked_bill.cancelled_by = user
        locked_bill.cancelled_at = timezone.now()
        locked_bill.cancellation_reason = reason.strip()
        locked_bill.save(update_fields=[
            "status", "cancelled_by", "cancelled_at",
            "cancellation_reason", "updated_at",
        ])

    logger.info(
        "Bill cancelled: bill=%s reason=%s by user=%s",
        bill.bill_number, reason[:50], user.email,
    )

    bill.refresh_from_db()
    return bill


def void_bill(bill, user, *, reason: str) -> "Bill":
    """
    Void a FINALIZED bill (post-payment, escalated action).

    VOID is a stronger action than CANCEL and requires bill.void permission.
    Typically used for compliance situations after payment has been recorded
    (Phase 9 will handle the payment reversal side).

    CANCELLED status must be used for pre-payment cancellations;
    VOID is for post-payment voiding.
    """
    from billing.models import BillStatus

    _require_auth(user)

    if not acl.has_permission(user, "bill.void"):
        raise PermissionDenied("You do not have permission to void bills.")

    if not acl.can_access_branch(user, bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    if not reason or not reason.strip():
        raise ValidationError({"reason": "A void reason is required."})

    if bill.status != BillStatus.FINALIZED:
        raise ValidationError(
            {
                "code": "BILL_NOT_FINALIZED",
                "message": (
                    f"Only FINALIZED bills can be voided. "
                    f"Current status: {bill.status}."
                ),
            }
        )

    with transaction.atomic():
        locked_bill = type(bill).objects.select_for_update().get(pk=bill.pk)

        if locked_bill.status != BillStatus.FINALIZED:
            raise ValidationError(
                {
                    "code": "BILL_NOT_FINALIZED",
                    "message": f"Only FINALIZED bills can be voided. Current: {locked_bill.status}.",
                }
            )

        locked_bill.status = BillStatus.VOID
        locked_bill.cancelled_by = user
        locked_bill.cancelled_at = timezone.now()
        locked_bill.cancellation_reason = reason.strip()
        locked_bill.save(update_fields=[
            "status", "cancelled_by", "cancelled_at",
            "cancellation_reason", "updated_at",
        ])

    logger.info(
        "Bill voided: bill=%s reason=%s by user=%s",
        bill.bill_number, reason[:50], user.email,
    )

    bill.refresh_from_db()
    return bill


# =============================================================================
# 7. Bill Corrections
# =============================================================================

def request_bill_correction(bill, user, *, correction_type: str, reason: str) -> "BillCorrectionRequest":
    """
    Submit a correction request for a FINALIZED bill.

    Only FINALIZED bills can have correction requests.
    DRAFT bills should be modified directly; finalized bills need this workflow.

    The bill itself is NOT modified — this creates a request record for
    a manager to review and approve.

    Stores a snapshot of the bill's current financial values in requested_data
    for audit comparison later.

    Returns the created BillCorrectionRequest.
    """
    from billing.models import BillStatus, BillCorrectionRequest, CorrectionType

    _require_auth(user)

    if not acl.has_permission(user, "bill.correction.request"):
        raise PermissionDenied(
            "You do not have permission to request bill corrections."
        )

    if not acl.can_access_branch(user, bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    if bill.status != BillStatus.FINALIZED:
        raise ValidationError(
            {
                "code": "BILL_NOT_FINALIZED",
                "message": (
                    "Correction requests can only be made for FINALIZED bills. "
                    f"Current status: {bill.status}."
                ),
            }
        )

    # Validate correction_type
    valid_types = {c[0] for c in CorrectionType.choices}
    if correction_type not in valid_types:
        raise ValidationError(
            {
                "correction_type": (
                    f"Invalid correction type '{correction_type}'. "
                    f"Must be one of: {', '.join(sorted(valid_types))}."
                )
            }
        )

    validated_reason = validate_correction_reason(reason)

    # Build snapshot of current bill values for audit
    requested_data = _build_bill_snapshot(bill)

    correction = BillCorrectionRequest.objects.create(
        bill=bill,
        requested_by=user,
        correction_type=correction_type,
        reason=validated_reason,
        requested_data=requested_data,
    )

    logger.info(
        "Bill correction requested: bill=%s type=%s by user=%s",
        bill.bill_number, correction_type, user.email,
    )

    return correction


def approve_bill_correction(correction, reviewer, *, note: str = "") -> "BillCorrectionRequest":
    """
    Approve a PENDING bill correction request.

    Rules:
        - reviewer must have bill.correction.approve permission.
        - reviewer must NOT be the same as correction.requested_by.
        - correction must be PENDING.

    After approval, the correction is marked APPROVED.
    The bill is transitioned to CANCELLED or VOID depending on correction_type.
    For non-CANCELLATION corrections, the bill status remains FINALIZED
    and a note is appended — a full replacement bill is outside Phase 8 scope.

    Returns the updated BillCorrectionRequest.
    """
    from billing.models import CorrectionStatus, BillStatus, CorrectionType

    _require_auth(reviewer)

    if not acl.has_permission(reviewer, "bill.correction.approve"):
        raise PermissionDenied(
            "You do not have permission to approve bill corrections."
        )

    if not acl.can_access_branch(reviewer, correction.bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    validate_self_approval(correction.requested_by_id, reviewer.pk)

    if correction.status != CorrectionStatus.PENDING:
        raise ValidationError(
            {
                "code": "CORRECTION_NOT_PENDING",
                "message": (
                    f"Only PENDING corrections can be approved. "
                    f"Current status: {correction.status}."
                ),
            }
        )

    with transaction.atomic():
        locked = type(correction).objects.select_for_update().get(pk=correction.pk)

        if locked.status != CorrectionStatus.PENDING:
            raise ValidationError(
                {
                    "code": "CORRECTION_NOT_PENDING",
                    "message": f"Correction is already {locked.status}.",
                }
            )

        validate_self_approval(locked.requested_by_id, reviewer.pk)

        locked.status = CorrectionStatus.APPROVED
        locked.reviewed_by = reviewer
        locked.reviewed_at = timezone.now()
        locked.review_note = note.strip()
        locked.save(update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_note", "updated_at"
        ])

        # For CANCELLATION corrections: void/cancel the bill
        if locked.correction_type == CorrectionType.CANCELLATION:
            bill = type(locked.bill).objects.select_for_update().get(pk=locked.bill_id)
            if bill.status == BillStatus.FINALIZED:
                bill.status = BillStatus.VOID
                bill.cancelled_by = reviewer
                bill.cancelled_at = timezone.now()
                bill.cancellation_reason = (
                    f"Voided via correction {locked.id}. Reason: {locked.reason}"
                )
                bill.save(update_fields=[
                    "status", "cancelled_by", "cancelled_at",
                    "cancellation_reason", "updated_at"
                ])

    logger.info(
        "Bill correction approved: correction=%s bill=%s by reviewer=%s",
        correction.id, correction.bill.bill_number, reviewer.email,
    )

    correction.refresh_from_db()
    return correction


def reject_bill_correction(correction, reviewer, *, note: str) -> "BillCorrectionRequest":
    """
    Reject a PENDING bill correction request.

    Rules:
        - reviewer must have bill.correction.approve permission.
        - reviewer must NOT be the same as requested_by.
        - correction must be PENDING.
        - note (rejection reason) is required.

    Returns the updated BillCorrectionRequest.
    """
    from billing.models import CorrectionStatus

    _require_auth(reviewer)

    if not acl.has_permission(reviewer, "bill.correction.approve"):
        raise PermissionDenied(
            "You do not have permission to reject bill corrections."
        )

    if not acl.can_access_branch(reviewer, correction.bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    validate_self_approval(correction.requested_by_id, reviewer.pk)

    if not note or not note.strip():
        raise ValidationError(
            {"review_note": "A rejection note is required when rejecting a correction."}
        )

    if correction.status != CorrectionStatus.PENDING:
        raise ValidationError(
            {
                "code": "CORRECTION_NOT_PENDING",
                "message": f"Only PENDING corrections can be rejected. Current: {correction.status}.",
            }
        )

    with transaction.atomic():
        locked = type(correction).objects.select_for_update().get(pk=correction.pk)

        if locked.status != CorrectionStatus.PENDING:
            raise ValidationError(
                {
                    "code": "CORRECTION_NOT_PENDING",
                    "message": f"Correction is already {locked.status}.",
                }
            )

        validate_self_approval(locked.requested_by_id, reviewer.pk)

        locked.status = CorrectionStatus.REJECTED
        locked.reviewed_by = reviewer
        locked.reviewed_at = timezone.now()
        locked.review_note = note.strip()
        locked.save(update_fields=[
            "status", "reviewed_by", "reviewed_at", "review_note", "updated_at"
        ])

    logger.info(
        "Bill correction rejected: correction=%s bill=%s by reviewer=%s",
        correction.id, correction.bill.bill_number, reviewer.email,
    )

    correction.refresh_from_db()
    return correction


def cancel_bill_correction(correction, user) -> "BillCorrectionRequest":
    """
    Cancel a PENDING correction request (by the requester or an authorized user).

    Only the original requester or someone with bill.correction.approve
    permission may cancel a PENDING correction.
    """
    from billing.models import CorrectionStatus

    _require_auth(user)

    if correction.requested_by_id != user.pk:
        if not acl.has_permission(user, "bill.correction.approve"):
            raise PermissionDenied(
                "Only the original requester or an approver can cancel a correction request."
            )

    if correction.status != CorrectionStatus.PENDING:
        raise ValidationError(
            {
                "code": "CORRECTION_NOT_PENDING",
                "message": f"Only PENDING corrections can be cancelled. Current: {correction.status}.",
            }
        )

    with transaction.atomic():
        locked = type(correction).objects.select_for_update().get(pk=correction.pk)

        if locked.status != CorrectionStatus.PENDING:
            raise ValidationError(
                {
                    "code": "CORRECTION_NOT_PENDING",
                    "message": f"Correction is already {locked.status}.",
                }
            )

        locked.status = CorrectionStatus.CANCELLED
        locked.reviewed_by = user
        locked.reviewed_at = timezone.now()
        locked.save(update_fields=[
            "status", "reviewed_by", "reviewed_at", "updated_at"
        ])

    correction.refresh_from_db()
    return correction


# =============================================================================
# 8. Receipt Data
# =============================================================================

def get_bill_receipt_data(bill) -> dict:
    """
    Build a structured receipt data dict for printing/display.

    This assembles all the information needed to render a receipt.
    Payment fields are intentionally absent (Phase 9).

    Returns:
    {
        "bill_number":        str,
        "order_number":       str,
        "order_type":         str,
        "date":               str  (ISO),
        "finalized_at":       str | None,
        "restaurant": {
            "name", "address", "city", "state", "postal_code",
            "phone", "email", "tax_id",
        },
        "branch": {
            "name", "address", "city", "state", "postal_code", "phone",
        },
        "cashier":            str | None (full_name),
        "table_number":       str | None,
        "counter_code":       str | None,
        "receipt_header":     str,
        "receipt_footer":     str,
        "items": [
            {
                "name", "sku", "quantity", "unit_price",
                "gross_amount", "discount_amount", "taxable_amount",
                "tax_rate", "tax_code", "tax_amount", "total_amount",
            }
        ],
        "subtotal":           str,
        "discount_amount":    str,
        "discount_type":      str | None,
        "discount_value":     str,
        "taxable_amount":     str,
        "tax_breakdown":      dict,
        "tax_amount":         str,
        "rounding_amount":    str,
        "grand_total":        str,
        "status":             str,
        "correction_count":   int,
    }
    """
    branch = bill.branch
    restaurant = branch.restaurant
    org = restaurant.organization

    # Receipt settings
    try:
        r_settings = restaurant.settings
        receipt_header = r_settings.receipt_header or ""
        receipt_footer = r_settings.receipt_footer or ""
        currency = r_settings.currency or "INR"
    except Exception:
        receipt_header = ""
        receipt_footer = ""
        currency = "INR"

    # Branch override footer
    try:
        b_footer = branch.settings.receipt_footer or ""
        if b_footer:
            receipt_footer = b_footer
    except Exception:
        pass

    items_data = []
    for item in bill.items.select_related("menu_item").order_by("created_at"):
        items_data.append({
            "name":           item.item_name_snapshot,
            "sku":            item.sku_snapshot,
            "quantity":       str(item.quantity),
            "unit_price":     str(item.unit_price),
            "gross_amount":   str(item.gross_amount),
            "discount_amount": str(item.discount_amount),
            "taxable_amount": str(item.taxable_amount),
            "tax_rate":       str(item.tax_rate),
            "tax_code":       item.tax_code,
            "tax_amount":     str(item.tax_amount),
            "total_amount":   str(item.total_amount),
        })

    cashier_name = None
    if bill.finalized_by:
        cashier_name = bill.finalized_by.full_name or bill.finalized_by.email
    elif bill.created_by:
        cashier_name = bill.created_by.full_name or bill.created_by.email

    table_number = None
    counter_code = None
    try:
        if bill.order.table:
            table_number = bill.order.table.table_number
        if bill.order.counter:
            counter_code = bill.order.counter.code
    except Exception:
        pass

    correction_count = bill.correction_requests.count()

    return {
        "bill_number":      bill.bill_number,
        "order_number":     bill.order.order_number,
        "order_type":       bill.order.order_type,
        "date":             bill.created_at.isoformat(),
        "finalized_at":     bill.finalized_at.isoformat() if bill.finalized_at else None,
        "currency":         currency,
        "restaurant": {
            "name":         restaurant.name,
            "address":      restaurant.address,
            "city":         restaurant.city,
            "state":        restaurant.state,
            "postal_code":  restaurant.postal_code,
            "phone":        restaurant.phone,
            "email":        restaurant.email,
            "tax_id":       getattr(org, "tax_id", ""),
        },
        "branch": {
            "name":         branch.name,
            "address":      branch.address,
            "city":         branch.city,
            "state":        branch.state,
            "postal_code":  branch.postal_code,
            "phone":        branch.phone,
        },
        "cashier":          cashier_name,
        "table_number":     table_number,
        "counter_code":     counter_code,
        "receipt_header":   receipt_header,
        "receipt_footer":   receipt_footer,
        "items":            items_data,
        "subtotal":         str(bill.subtotal),
        "discount_amount":  str(bill.discount_amount),
        "discount_type":    bill.discount_type,
        "discount_value":   str(bill.discount_value),
        "taxable_amount":   str(bill.taxable_amount),
        "tax_breakdown":    bill.tax_breakdown,
        "tax_amount":       str(bill.tax_amount),
        "rounding_amount":  str(bill.rounding_amount),
        "grand_total":      str(bill.grand_total),
        "status":           bill.status,
        "correction_count": correction_count,
    }


# =============================================================================
# Internal: Bill Snapshot (for audit)
# =============================================================================

def _build_bill_snapshot(bill) -> dict:
    """Build an audit snapshot of the bill's current financial state."""
    items_snap = []
    for item in bill.items.all():
        items_snap.append({
            "item_name":     item.item_name_snapshot,
            "sku":           item.sku_snapshot,
            "quantity":      str(item.quantity),
            "unit_price":    str(item.unit_price),
            "gross_amount":  str(item.gross_amount),
            "tax_rate":      str(item.tax_rate),
            "tax_code":      item.tax_code,
            "tax_amount":    str(item.tax_amount),
            "total_amount":  str(item.total_amount),
        })
    return {
        "bill_number":     bill.bill_number,
        "status":          bill.status,
        "discount_type":   bill.discount_type,
        "discount_value":  str(bill.discount_value),
        "subtotal":        str(bill.subtotal),
        "discount_amount": str(bill.discount_amount),
        "taxable_amount":  str(bill.taxable_amount),
        "tax_amount":      str(bill.tax_amount),
        "tax_breakdown":   bill.tax_breakdown,
        "rounding_amount": str(bill.rounding_amount),
        "grand_total":     str(bill.grand_total),
        "items":           items_snap,
        "snapshot_at":     timezone.now().isoformat(),
    }
