# =============================================================================
# RestaurantFlow — Payment Validators
# Phase 9
#
# Pure validation functions used by the service layer.
# Each function raises rest_framework.exceptions.ValidationError on failure.
# None of these functions touch the database or perform business logic.
#
# Public API:
#   validate_bill_is_payable(bill)
#   validate_payment_amount(amount, remaining_amount)
#   validate_cash_payment(amount, cash_received)
#   validate_payment_method(method)
#   validate_counter_session_open(counter_session, branch)
#   validate_refund_amount(refund_amount, refundable_amount)
#   validate_refund_reason(reason)
#   validate_idempotency_key(key)
#   validate_transaction_reference_required(method, reference)
# =============================================================================

from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

from payments.constants import (
    ZERO,
    MIN_PAYMENT_AMOUNT,
    MAX_PAYMENT_AMOUNT,
    MIN_REFUND_AMOUNT,
    MIN_REFUND_REASON_LENGTH,
    MAX_CHANGE_AMOUNT,
    IDEMPOTENCY_KEY_MAX_LENGTH,
)
from payments.models import PaymentMethod


def validate_bill_is_payable(bill) -> None:
    """
    Raise ValidationError if the bill cannot receive a payment.

    Rules:
      - Must be FINALIZED.
      - Must not be CANCELLED or VOID.
    """
    from billing.models import BillStatus

    if bill.status == BillStatus.FINALIZED:
        return  # OK

    if bill.status == BillStatus.DRAFT:
        raise ValidationError(
            {
                "code": "BILL_NOT_FINALIZED",
                "message": (
                    "Cannot create a payment for a DRAFT bill. "
                    "Finalize the bill first."
                ),
            }
        )
    if bill.status == BillStatus.CANCELLED:
        raise ValidationError(
            {
                "code": "BILL_CANCELLED",
                "message": "Cannot create a payment for a CANCELLED bill.",
            }
        )
    if bill.status == BillStatus.VOID:
        raise ValidationError(
            {
                "code": "BILL_VOID",
                "message": "Cannot create a payment for a VOID bill.",
            }
        )
    raise ValidationError(
        {
            "code": "BILL_NOT_PAYABLE",
            "message": f"Bill status '{bill.status}' is not payable.",
        }
    )


def validate_payment_amount(amount: Decimal, remaining_amount: Decimal) -> None:
    """
    Validate the requested payment amount.

    Rules:
      - amount must be > 0
      - amount must be <= remaining_amount (no overpayment)
      - amount must be <= MAX_PAYMENT_AMOUNT
    """
    if amount <= ZERO:
        raise ValidationError(
            {
                "code": "INVALID_AMOUNT",
                "message": "Payment amount must be greater than zero.",
            }
        )
    if amount < MIN_PAYMENT_AMOUNT:
        raise ValidationError(
            {
                "code": "AMOUNT_TOO_SMALL",
                "message": f"Payment amount must be at least {MIN_PAYMENT_AMOUNT}.",
            }
        )
    if amount > MAX_PAYMENT_AMOUNT:
        raise ValidationError(
            {
                "code": "AMOUNT_TOO_LARGE",
                "message": f"Payment amount cannot exceed {MAX_PAYMENT_AMOUNT}.",
            }
        )
    if remaining_amount <= ZERO:
        raise ValidationError(
            {
                "code": "BILL_ALREADY_PAID",
                "message": "This bill has already been fully paid.",
            }
        )
    if amount > remaining_amount:
        raise ValidationError(
            {
                "code": "OVERPAYMENT",
                "message": (
                    f"Payment amount ({amount}) exceeds the remaining balance "
                    f"({remaining_amount}). Overpayment is not permitted."
                ),
            }
        )


def validate_cash_payment(amount: Decimal, cash_received: Decimal) -> Decimal:
    """
    Validate a CASH payment and return the calculated change.

    Rules:
      - cash_received must be provided.
      - cash_received must be >= amount.

    Returns:
      change_amount = cash_received - amount  (Decimal, >= 0)
    """
    if cash_received is None:
        raise ValidationError(
            {
                "code": "CASH_RECEIVED_REQUIRED",
                "message": "cash_received is required for CASH payments.",
            }
        )
    if cash_received <= ZERO:
        raise ValidationError(
            {
                "code": "INVALID_CASH_RECEIVED",
                "message": "cash_received must be greater than zero.",
            }
        )
    if cash_received < amount:
        raise ValidationError(
            {
                "code": "INSUFFICIENT_CASH",
                "message": (
                    f"Cash received ({cash_received}) is less than the payment "
                    f"amount ({amount}). Please collect sufficient cash."
                ),
            }
        )

    change = cash_received - amount

    if change > MAX_CHANGE_AMOUNT:
        raise ValidationError(
            {
                "code": "CHANGE_TOO_LARGE",
                "message": (
                    f"Calculated change ({change}) exceeds the maximum allowed "
                    f"({MAX_CHANGE_AMOUNT}). Please check the amounts entered."
                ),
            }
        )

    return change


def validate_payment_method(method: str) -> str:
    """
    Validate the payment method is one of the supported enum values.
    Returns the validated method string.
    """
    valid_methods = {m[0] for m in PaymentMethod.choices}
    if method not in valid_methods:
        raise ValidationError(
            {
                "code": "INVALID_PAYMENT_METHOD",
                "message": (
                    f"Invalid payment method '{method}'. "
                    f"Must be one of: {', '.join(sorted(valid_methods))}."
                ),
            }
        )
    return method


def validate_counter_session_open(counter_session, branch) -> None:
    """
    Validate that the counter session is OPEN and belongs to the given branch.

    Rules:
      - counter_session.status must be OPEN.
      - counter_session.counter.branch must equal bill.branch.
    """
    from counters.models import SessionStatus

    if counter_session is None:
        raise ValidationError(
            {
                "code": "COUNTER_SESSION_REQUIRED",
                "message": "An open counter session is required for CASH payments.",
            }
        )

    session_status = getattr(counter_session, "status", None)
    if session_status != SessionStatus.OPEN:
        raise ValidationError(
            {
                "code": "COUNTER_SESSION_NOT_OPEN",
                "message": (
                    "The counter session is not OPEN. "
                    "Please open a counter session before accepting cash payments."
                ),
            }
        )

    # Verify the counter belongs to the same branch as the bill
    counter = counter_session.counter
    if counter.branch_id != branch.pk:
        raise ValidationError(
            {
                "code": "COUNTER_BRANCH_MISMATCH",
                "message": (
                    "The counter session belongs to a different branch. "
                    "Cash payments must be processed through a counter at the bill's branch."
                ),
            }
        )


def validate_refund_amount(refund_amount: Decimal, refundable_amount: Decimal) -> None:
    """
    Validate a refund amount.

    Rules:
      - refund_amount must be > 0
      - refund_amount must be <= refundable_amount
    """
    if refund_amount <= ZERO:
        raise ValidationError(
            {
                "code": "INVALID_REFUND_AMOUNT",
                "message": "Refund amount must be greater than zero.",
            }
        )
    if refund_amount < MIN_REFUND_AMOUNT:
        raise ValidationError(
            {
                "code": "REFUND_AMOUNT_TOO_SMALL",
                "message": f"Refund amount must be at least {MIN_REFUND_AMOUNT}.",
            }
        )
    if refundable_amount <= ZERO:
        raise ValidationError(
            {
                "code": "PAYMENT_FULLY_REFUNDED",
                "message": "This payment has already been fully refunded.",
            }
        )
    if refund_amount > refundable_amount:
        raise ValidationError(
            {
                "code": "REFUND_EXCEEDS_PAYMENT",
                "message": (
                    f"Refund amount ({refund_amount}) exceeds the remaining "
                    f"refundable amount ({refundable_amount})."
                ),
            }
        )


def validate_refund_reason(reason: str) -> str:
    """
    Validate the refund reason is non-empty and meets minimum length.
    Returns the stripped, validated reason.
    """
    if not reason or not reason.strip():
        raise ValidationError(
            {
                "code": "REFUND_REASON_REQUIRED",
                "message": "A reason is required for refund requests.",
            }
        )
    stripped = reason.strip()
    if len(stripped) < MIN_REFUND_REASON_LENGTH:
        raise ValidationError(
            {
                "code": "REFUND_REASON_TOO_SHORT",
                "message": (
                    f"Refund reason must be at least "
                    f"{MIN_REFUND_REASON_LENGTH} characters."
                ),
            }
        )
    return stripped


def validate_idempotency_key(key: str) -> str:
    """
    Validate the idempotency key if provided.
    Returns the stripped key.
    """
    if not key:
        return ""
    stripped = key.strip()
    if len(stripped) > IDEMPOTENCY_KEY_MAX_LENGTH:
        raise ValidationError(
            {
                "code": "IDEMPOTENCY_KEY_TOO_LONG",
                "message": (
                    f"idempotency_key must not exceed "
                    f"{IDEMPOTENCY_KEY_MAX_LENGTH} characters."
                ),
            }
        )
    return stripped


def validate_transaction_reference_required(method: str, reference: str) -> None:
    """
    For digital payment methods, a transaction_reference is strongly recommended.
    For UPI and CARD it is required in this implementation.
    """
    from payments.constants import DIGITAL_METHODS
    if method in DIGITAL_METHODS and not reference:
        raise ValidationError(
            {
                "code": "TRANSACTION_REFERENCE_REQUIRED",
                "message": (
                    f"A transaction_reference is required for {method} payments. "
                    "Please enter the transaction ID from the payment terminal."
                ),
            }
        )


def coerce_decimal(value, field_name: str) -> Decimal:
    """
    Safely coerce a value to Decimal.
    Raises ValidationError if conversion fails.
    """
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValidationError(
            {
                "code": "INVALID_DECIMAL",
                "message": f"'{field_name}' must be a valid decimal number.",
            }
        )
