# =============================================================================
# RestaurantFlow — Inventory Validators
# Phase 10
#
# Pure validation functions used by services and serializers.
# No database access here — validators are stateless.
# Each function raises rest_framework.exceptions.ValidationError on failure.
# =============================================================================

from decimal import Decimal, InvalidOperation
from rest_framework.exceptions import ValidationError

from inventory.constants import (
    UNIT_CHOICES,
    are_units_compatible,
    ZERO,
    ZERO_COST,
    PO_VALID_TRANSITIONS,
    TRANSFER_VALID_TRANSITIONS,
    PO_RECEIVABLE_STATUSES,
    PO_CANCELLABLE_STATUSES,
)


# ---------------------------------------------------------------------------
# Decimal / quantity validators
# ---------------------------------------------------------------------------

def validate_positive_quantity(value, field_name: str = "quantity") -> Decimal:
    """
    Validate that quantity is a strictly positive Decimal.
    """
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError({field_name: f"'{value}' is not a valid quantity."})
    if d <= Decimal("0"):
        raise ValidationError(
            {field_name: f"{field_name} must be greater than 0. Got {d}."}
        )
    return d


def validate_non_negative_quantity(value, field_name: str = "quantity") -> Decimal:
    """
    Validate that quantity is non-negative.
    """
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError({field_name: f"'{value}' is not a valid quantity."})
    if d < Decimal("0"):
        raise ValidationError(
            {field_name: f"{field_name} must be >= 0. Got {d}."}
        )
    return d


def validate_non_negative_cost(value, field_name: str = "unit_cost") -> Decimal:
    """
    Validate that a cost value is non-negative.
    """
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError({field_name: f"'{value}' is not a valid monetary value."})
    if d < Decimal("0"):
        raise ValidationError(
            {field_name: f"{field_name} must be >= 0. Got {d}."}
        )
    return d


# ---------------------------------------------------------------------------
# Unit validators
# ---------------------------------------------------------------------------

VALID_UNITS = {code for code, _ in UNIT_CHOICES}


def validate_unit(unit: str, field_name: str = "unit") -> str:
    """Validate that unit is a known unit code."""
    if unit not in VALID_UNITS:
        raise ValidationError(
            {field_name: f"'{unit}' is not a valid unit. Choices: {sorted(VALID_UNITS)}."}
        )
    return unit


def validate_compatible_units(unit_a: str, unit_b: str) -> None:
    """
    Raise ValidationError if the two units are incompatible.
    (e.g. KG and LITRE cannot be mixed)
    """
    if not are_units_compatible(unit_a, unit_b):
        raise ValidationError(
            {
                "unit": (
                    f"Units '{unit_a}' and '{unit_b}' are incompatible. "
                    "Cannot mix weight, volume, and count units."
                )
            }
        )


# ---------------------------------------------------------------------------
# Stock balance validators
# ---------------------------------------------------------------------------

def validate_sufficient_stock(available: Decimal, requested: Decimal, item_name: str = "item") -> None:
    """
    Raise ValidationError if available stock < requested quantity.
    Enforces the default: negative stock is NOT allowed.
    """
    if available < requested:
        raise ValidationError(
            {
                "code": "INSUFFICIENT_STOCK",
                "message": (
                    f"Insufficient stock for '{item_name}'. "
                    f"Available: {available}, Requested: {requested}."
                ),
            }
        )


# ---------------------------------------------------------------------------
# Purchase order validators
# ---------------------------------------------------------------------------

def validate_purchase_order_transition(current_status: str, target_status: str) -> None:
    """
    Validate that a PO status transition is permitted.
    """
    allowed = PO_VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise ValidationError(
            {
                "code": "INVALID_STATUS_TRANSITION",
                "message": (
                    f"Cannot transition PurchaseOrder from '{current_status}' "
                    f"to '{target_status}'. "
                    f"Allowed: {allowed}."
                ),
            }
        )


def validate_purchase_order_receivable(status: str) -> None:
    """Raise ValidationError if PO is not in a receivable state."""
    if status not in PO_RECEIVABLE_STATUSES:
        raise ValidationError(
            {
                "code": "PO_NOT_RECEIVABLE",
                "message": (
                    f"Cannot receive goods for a PurchaseOrder in status '{status}'. "
                    f"PO must be APPROVED or PARTIALLY_RECEIVED."
                ),
            }
        )


def validate_purchase_order_cancellable(status: str) -> None:
    """Raise ValidationError if PO cannot be cancelled from its current state."""
    if status not in PO_CANCELLABLE_STATUSES:
        raise ValidationError(
            {
                "code": "PO_NOT_CANCELLABLE",
                "message": (
                    f"Cannot cancel a PurchaseOrder in status '{status}'. "
                    f"Terminal statuses (RECEIVED, CANCELLED) cannot be changed."
                ),
            }
        )


def validate_receive_quantity(ordered: Decimal, already_received: Decimal, receiving: Decimal, item_name: str) -> None:
    """
    Validate that receiving does not exceed ordered quantity.
    """
    remaining = ordered - already_received
    if receiving > remaining:
        raise ValidationError(
            {
                "code": "OVER_RECEIVING",
                "message": (
                    f"Cannot receive {receiving} of '{item_name}'. "
                    f"Ordered: {ordered}, Already received: {already_received}, "
                    f"Remaining: {remaining}."
                ),
            }
        )
    if receiving <= Decimal("0"):
        raise ValidationError(
            {
                "code": "INVALID_RECEIVE_QUANTITY",
                "message": f"Receive quantity must be > 0. Got {receiving}.",
            }
        )


# ---------------------------------------------------------------------------
# Transfer validators
# ---------------------------------------------------------------------------

def validate_transfer_transition(current_status: str, target_status: str) -> None:
    """Validate a stock transfer status transition."""
    allowed = TRANSFER_VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise ValidationError(
            {
                "code": "INVALID_STATUS_TRANSITION",
                "message": (
                    f"Cannot transition StockTransfer from '{current_status}' "
                    f"to '{target_status}'. Allowed: {allowed}."
                ),
            }
        )


def validate_transfer_locations(source_id, destination_id) -> None:
    """Raise ValidationError if source and destination are the same location."""
    if source_id == destination_id:
        raise ValidationError(
            {
                "code": "SAME_LOCATION",
                "message": "Source and destination locations cannot be the same.",
            }
        )


# ---------------------------------------------------------------------------
# Reason validators
# ---------------------------------------------------------------------------

def validate_reason(reason: str, field_name: str = "reason", min_length: int = 5) -> str:
    """Validate that a reason string is non-empty and meets minimum length."""
    if not reason or not reason.strip():
        raise ValidationError(
            {field_name: "A reason is required and cannot be blank."}
        )
    if len(reason.strip()) < min_length:
        raise ValidationError(
            {field_name: f"Reason must be at least {min_length} characters."}
        )
    return reason.strip()
