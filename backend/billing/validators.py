# =============================================================================
# RestaurantFlow — Billing Validators
# Phase 8
#
# Pure validation functions used by:
#   - billing/services.py  (service layer)
#   - billing/serializers.py  (DRF input validation)
#
# Each function either returns nothing (passes) or raises
# rest_framework.exceptions.ValidationError.
#
# No database access here — validators are stateless.
# =============================================================================

from decimal import Decimal, InvalidOperation
from rest_framework.exceptions import ValidationError

from billing.utils import ZERO, ONE_HUNDRED


# ---------------------------------------------------------------------------
# Money value validators
# ---------------------------------------------------------------------------

def validate_non_negative_decimal(value, field_name: str = "value") -> Decimal:
    """
    Validate that value is a non-negative Decimal.

    Raises ValidationError if:
        - value cannot be parsed as Decimal
        - value < 0

    Returns the Decimal value.
    """
    try:
        d = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError(
            {field_name: f"'{value}' is not a valid decimal number."}
        )
    if d < ZERO:
        raise ValidationError(
            {field_name: f"{field_name} must be greater than or equal to 0. Got {d}."}
        )
    return d


def validate_positive_decimal(value, field_name: str = "value") -> Decimal:
    """
    Validate that value is a strictly positive Decimal.

    Raises ValidationError if value <= 0.
    """
    d = validate_non_negative_decimal(value, field_name)
    if d <= ZERO:
        raise ValidationError(
            {field_name: f"{field_name} must be greater than 0. Got {d}."}
        )
    return d


# ---------------------------------------------------------------------------
# Discount validators
# ---------------------------------------------------------------------------

def validate_percentage_discount(pct, max_pct: Decimal = Decimal("100")) -> Decimal:
    """
    Validate a percentage discount value.

    Rules:
        0 ≤ pct ≤ max_pct (configurable maximum, default 100)

    Args:
        pct:     The percentage value (e.g. 10 for 10%)
        max_pct: Maximum allowed percentage for this user's role.

    Returns Decimal.
    """
    d = validate_non_negative_decimal(pct, "discount_value")
    if d > ONE_HUNDRED:
        raise ValidationError(
            {"discount_value": f"Percentage discount cannot exceed 100%. Got {d}%."}
        )
    if d > max_pct:
        raise ValidationError(
            {
                "discount_value": (
                    f"You are not authorized to apply a discount of {d}%. "
                    f"Your maximum is {max_pct}%."
                )
            }
        )
    return d


def validate_fixed_discount(fixed, subtotal: Decimal) -> Decimal:
    """
    Validate a fixed-amount discount value.

    Rules:
        0 ≤ fixed ≤ subtotal

    Args:
        fixed:    The fixed discount amount (e.g. 50 for ₹50)
        subtotal: The bill subtotal the discount is applied against.

    Returns Decimal.
    """
    d = validate_non_negative_decimal(fixed, "discount_value")
    if subtotal <= ZERO:
        # If nothing to discount, no discount can apply
        if d > ZERO:
            raise ValidationError(
                {
                    "discount_value": (
                        "Cannot apply a fixed discount when the bill subtotal is zero."
                    )
                }
            )
        return d
    if d > subtotal:
        raise ValidationError(
            {
                "discount_value": (
                    f"Fixed discount of {d} exceeds the bill subtotal of {subtotal}. "
                    "Discount cannot exceed the amount owed."
                )
            }
        )
    return d


# ---------------------------------------------------------------------------
# Discount type validator
# ---------------------------------------------------------------------------

def validate_discount_type(discount_type: str) -> str:
    """
    Validate that discount_type is a known value.

    Accepted: 'PERCENTAGE', 'FIXED_AMOUNT'
    """
    from billing.models import DiscountType
    valid = {c[0] for c in DiscountType.choices}
    if discount_type not in valid:
        raise ValidationError(
            {
                "discount_type": (
                    f"Invalid discount type '{discount_type}'. "
                    f"Must be one of: {', '.join(sorted(valid))}."
                )
            }
        )
    return discount_type


# ---------------------------------------------------------------------------
# Correction validators
# ---------------------------------------------------------------------------

def validate_correction_reason(reason: str) -> str:
    """Reason field must be a non-empty, meaningful string."""
    if not reason or not reason.strip():
        raise ValidationError(
            {"reason": "A correction reason is required and cannot be blank."}
        )
    if len(reason.strip()) < 10:
        raise ValidationError(
            {
                "reason": (
                    "Correction reason must be at least 10 characters. "
                    "Please provide a descriptive reason."
                )
            }
        )
    return reason.strip()


def validate_self_approval(requester_id, reviewer_id) -> None:
    """
    Prevent a user from approving their own correction request.

    Raises ValidationError if requester_id == reviewer_id.
    """
    if requester_id == reviewer_id:
        raise ValidationError(
            {
                "reviewed_by": (
                    "You cannot approve or reject your own correction request. "
                    "A different authorized user must review it."
                )
            }
        )


# ---------------------------------------------------------------------------
# Bill status validators
# ---------------------------------------------------------------------------

def validate_bill_is_draft(bill) -> None:
    """
    Raise ValidationError if bill is not in DRAFT status.

    Used before any operation that requires an editable bill.
    """
    from billing.models import BillStatus
    if bill.status != BillStatus.DRAFT:
        raise ValidationError(
            {
                "code": "BILL_NOT_DRAFT",
                "message": (
                    f"This operation requires a DRAFT bill. "
                    f"Current status: {bill.status}."
                ),
            }
        )


def validate_bill_is_finalizable(bill) -> None:
    """
    Raise ValidationError if bill cannot be finalized.

    Must be DRAFT and have at least one item.
    """
    from billing.models import BillStatus
    validate_bill_is_draft(bill)
    if not bill.items.exists():
        raise ValidationError(
            {
                "code": "BILL_HAS_NO_ITEMS",
                "message": "Cannot finalize a bill with no items.",
            }
        )


def validate_rounding_amount(rounding: Decimal) -> None:
    """
    Validate that rounding adjustment is within the allowed range.

    Allowed: -0.99 ≤ rounding ≤ +0.99
    """
    limit = Decimal("0.99")
    if rounding < -limit or rounding > limit:
        raise ValidationError(
            {
                "rounding_amount": (
                    f"Rounding adjustment must be between -0.99 and +0.99. Got {rounding}."
                )
            }
        )
