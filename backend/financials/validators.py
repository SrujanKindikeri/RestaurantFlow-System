# =============================================================================
# RestaurantFlow — Financials Validators
# Phase 12
#
# Pure validation functions — no DB access, no side effects.
# Each raises rest_framework.exceptions.ValidationError on failure.
# =============================================================================

import os
from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

from financials.constants import (
    EXPENSE_VALID_TRANSITIONS,
    SINV_VALID_TRANSITIONS,
    ALLOWED_ATTACHMENT_CONTENT_TYPES,
    ALLOWED_ATTACHMENT_EXTENSIONS,
    MAX_ATTACHMENT_SIZE_BYTES,
)


# ---------------------------------------------------------------------------
# Decimal / monetary validators
# ---------------------------------------------------------------------------

def validate_non_negative_amount(value, field_name: str = "amount") -> Decimal:
    """Validate that a monetary value is non-negative."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError({field_name: f"'{value}' is not a valid monetary amount."})
    if d < Decimal("0"):
        raise ValidationError(
            {field_name: f"{field_name} must be >= 0. Got {d}."}
        )
    return d


def validate_positive_amount(value, field_name: str = "amount") -> Decimal:
    """Validate that a monetary value is strictly positive."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError({field_name: f"'{value}' is not a valid monetary amount."})
    if d <= Decimal("0"):
        raise ValidationError(
            {field_name: f"{field_name} must be > 0. Got {d}."}
        )
    return d


# ---------------------------------------------------------------------------
# Status transition validators
# ---------------------------------------------------------------------------

def validate_expense_transition(current_status: str, target_status: str) -> None:
    """Validate a permitted Expense status transition."""
    allowed = EXPENSE_VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        from financials.exceptions import InvalidStatusTransition
        raise InvalidStatusTransition(current_status, target_status, allowed)


def validate_sinv_transition(current_status: str, target_status: str) -> None:
    """Validate a permitted SupplierInvoice status transition."""
    allowed = SINV_VALID_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        from financials.exceptions import InvalidStatusTransition
        raise InvalidStatusTransition(current_status, target_status, allowed)


# ---------------------------------------------------------------------------
# Rejection reason validator
# ---------------------------------------------------------------------------

def validate_rejection_reason(reason: str, min_length: int = 5) -> str:
    """Rejection must be non-empty and meet a minimum length."""
    if not reason or not reason.strip():
        raise ValidationError({"rejection_reason": "A rejection reason is required."})
    if len(reason.strip()) < min_length:
        raise ValidationError(
            {"rejection_reason": f"Rejection reason must be at least {min_length} characters."}
        )
    return reason.strip()


def validate_correction_reason(reason: str, min_length: int = 10) -> str:
    """Correction reason must be substantive."""
    if not reason or not reason.strip():
        raise ValidationError({"reason": "A correction reason is required."})
    if len(reason.strip()) < min_length:
        raise ValidationError(
            {"reason": f"Correction reason must be at least {min_length} characters."}
        )
    return reason.strip()


# ---------------------------------------------------------------------------
# Attachment validators
# ---------------------------------------------------------------------------

def validate_attachment_file(file) -> None:
    """
    Validate an uploaded attachment file for:
      - size limit
      - allowed MIME types
      - allowed file extensions
    """
    if file.size > MAX_ATTACHMENT_SIZE_BYTES:
        from financials.exceptions import AttachmentTooLarge
        raise AttachmentTooLarge(file.size, MAX_ATTACHMENT_SIZE_BYTES)

    # MIME type check
    content_type = getattr(file, "content_type", "") or ""
    if content_type and content_type not in ALLOWED_ATTACHMENT_CONTENT_TYPES:
        from financials.exceptions import AttachmentTypeNotAllowed
        raise AttachmentTypeNotAllowed(content_type)

    # Extension check (fallback when content_type not available)
    _, ext = os.path.splitext(file.name.lower())
    if ext and ext not in ALLOWED_ATTACHMENT_EXTENSIONS:
        from financials.exceptions import AttachmentTypeNotAllowed
        raise AttachmentTypeNotAllowed(ext)


# ---------------------------------------------------------------------------
# Supplier invoice validators
# ---------------------------------------------------------------------------

def validate_supplier_invoice_amounts(subtotal, tax_amount, discount_amount, total_amount) -> None:
    """
    Validate supplier invoice financial fields consistency:
      - all non-negative
      - total = subtotal + tax - discount
    """
    s = validate_non_negative_amount(subtotal, "subtotal")
    t = validate_non_negative_amount(tax_amount, "tax_amount")
    d = validate_non_negative_amount(discount_amount, "discount_amount")

    expected = s + t - d
    if Decimal(str(total_amount)) != expected:
        raise ValidationError(
            {
                "total_amount": (
                    f"total_amount must equal subtotal + tax_amount - discount_amount. "
                    f"Expected {expected}, got {total_amount}."
                )
            }
        )


# ---------------------------------------------------------------------------
# Payable validators
# ---------------------------------------------------------------------------

def validate_payable_payment(paid_amount: Decimal, new_payment: Decimal, total: Decimal) -> None:
    """
    Validate that a payment update does not exceed the payable total.
    """
    new_total_paid = paid_amount + new_payment
    if new_total_paid > total:
        raise ValidationError(
            {
                "code": "OVERPAYMENT",
                "message": (
                    f"Payment of {new_payment} would exceed the payable total of {total}. "
                    f"Already paid: {paid_amount}, remaining: {total - paid_amount}."
                ),
            }
        )
