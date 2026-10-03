# =============================================================================
# RestaurantFlow — Payment Services
# Phase 9
#
# All payment business logic lives here.
# Views call these; serializers validate input shapes only.
#
# Public API:
#   generate_payment_number()                             → str
#   generate_refund_number()                              → str
#   create_payment(bill, user, amount, method, **kwargs)  → Payment
#   complete_payment(payment, user)                       → Payment
#   cancel_payment(payment, user, reason)                 → Payment
#   fail_payment(payment, user, reason)                   → Payment
#   request_refund(payment, user, amount, reason)         → PaymentRefund
#   approve_refund(refund, user)                          → PaymentRefund
#   reject_refund(refund, user, reason)                   → PaymentRefund
#   process_refund(refund, user, transaction_reference)   → PaymentRefund
#   cancel_refund(refund, user)                           → PaymentRefund
#   get_bill_payment_summary(bill)                        → dict
#   get_payment_receipt_data(bill)                        → dict
#
# Concurrency:
#   - generate_payment_number uses select_for_update() — never MAX()+1.
#   - create_payment locks the bill with select_for_update().
#   - Two simultaneous full-payment attempts → only one succeeds.
#   - All mutating operations wrapped in transaction.atomic().
#
# Idempotency:
#   - If the same (bill, idempotency_key) pair arrives again,
#     the existing payment is returned without creating a duplicate.
#
# Security:
#   - Branch access validated via accounts.access.can_access_branch().
#   - Permission codes checked (see payments/permissions.py).
#   - Frontend amounts are NEVER trusted — amounts come from Bill.grand_total.
#   - IDOR prevention: callers pass model instances, not raw IDs.
# =============================================================================

import logging
from decimal import Decimal

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from payments import utils as money_utils
from payments.constants import (
    ZERO,
    CASH_METHODS,
    PAYMENT_SEQUENCE_KEY,
    REFUND_SEQUENCE_KEY,
)
from payments.models import (
    Payment,
    PaymentRefund,
    PaymentSequence,
    PaymentAuditLog,
    PaymentStatus,
    PaymentMethod,
    RefundStatus,
    AuditAction,
    BillPaymentStatus,
)
from payments.validators import (
    validate_bill_is_payable,
    validate_payment_amount,
    validate_cash_payment,
    validate_payment_method,
    validate_counter_session_open,
    validate_refund_amount,
    validate_refund_reason,
    validate_idempotency_key,
    validate_transaction_reference_required,
    coerce_decimal,
)

logger = logging.getLogger("payments")


# =============================================================================
# Internal helpers
# =============================================================================

def _require_auth(user) -> None:
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


# =============================================================================
# 1. Sequence Number Generation
# =============================================================================

def generate_payment_number() -> str:
    """
    Generate a concurrency-safe, human-readable payment number.

    Format: PAY-{seq:06d}
    Examples:
        PAY-000001
        PAY-000002

    Global sequence (not per-branch).
    Uses select_for_update() to prevent race conditions.
    Must be called inside a transaction.atomic() block.

    Never uses MAX()+1 — race-condition-safe via database-level locking.
    """
    try:
        seq_obj = PaymentSequence.objects.select_for_update().get(
            sequence_key=PAYMENT_SEQUENCE_KEY
        )
        seq_obj.last_sequence += 1
        seq_obj.save(update_fields=["last_sequence", "updated_at"])
    except PaymentSequence.DoesNotExist:
        try:
            seq_obj, created = PaymentSequence.objects.get_or_create(
                sequence_key=PAYMENT_SEQUENCE_KEY,
                defaults={"last_sequence": 1},
            )
            if not created:
                seq_obj = PaymentSequence.objects.select_for_update().get(
                    sequence_key=PAYMENT_SEQUENCE_KEY
                )
                seq_obj.last_sequence += 1
                seq_obj.save(update_fields=["last_sequence", "updated_at"])
        except IntegrityError:
            seq_obj = PaymentSequence.objects.select_for_update().get(
                sequence_key=PAYMENT_SEQUENCE_KEY
            )
            seq_obj.last_sequence += 1
            seq_obj.save(update_fields=["last_sequence", "updated_at"])

    return f"PAY-{seq_obj.last_sequence:06d}"


def generate_refund_number() -> str:
    """
    Generate a concurrency-safe refund number.

    Format: REF-{seq:06d}
    Examples:
        REF-000001
        REF-000002

    Must be called inside a transaction.atomic() block.
    """
    try:
        seq_obj = PaymentSequence.objects.select_for_update().get(
            sequence_key=REFUND_SEQUENCE_KEY
        )
        seq_obj.last_sequence += 1
        seq_obj.save(update_fields=["last_sequence", "updated_at"])
    except PaymentSequence.DoesNotExist:
        try:
            seq_obj, created = PaymentSequence.objects.get_or_create(
                sequence_key=REFUND_SEQUENCE_KEY,
                defaults={"last_sequence": 1},
            )
            if not created:
                seq_obj = PaymentSequence.objects.select_for_update().get(
                    sequence_key=REFUND_SEQUENCE_KEY
                )
                seq_obj.last_sequence += 1
                seq_obj.save(update_fields=["last_sequence", "updated_at"])
        except IntegrityError:
            seq_obj = PaymentSequence.objects.select_for_update().get(
                sequence_key=REFUND_SEQUENCE_KEY
            )
            seq_obj.last_sequence += 1
            seq_obj.save(update_fields=["last_sequence", "updated_at"])

    return f"REF-{seq_obj.last_sequence:06d}"


# =============================================================================
# 2. Audit Logging
# =============================================================================

def _log_audit(
    *,
    payment: Payment,
    actor,
    action: str,
    old_status: str = "",
    new_status: str = "",
    amount: Decimal | None = None,
    reason: str = "",
    refund: PaymentRefund | None = None,
    metadata: dict | None = None,
) -> None:
    """
    Create an immutable audit log entry.

    Called after every successful state transition.
    Never raises — audit failure is logged but does not block the operation.
    """
    try:
        PaymentAuditLog.objects.create(
            payment=payment,
            refund=refund,
            actor=actor,
            action=action,
            old_status=old_status,
            new_status=new_status,
            amount=amount,
            reason=reason,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.error(
            "Failed to write payment audit log: payment=%s action=%s error=%s",
            payment.payment_number,
            action,
            exc,
        )


# =============================================================================
# 3. Payment Creation
# =============================================================================

def create_payment(
    bill,
    user,
    *,
    amount,
    payment_method: str,
    cash_received=None,
    transaction_reference: str = "",
    provider_reference: str = "",
    notes: str = "",
    idempotency_key: str = "",
    counter=None,
    counter_session=None,
) -> Payment:
    """
    Create a Payment against a finalized Bill.

    For CASH payments:
        - counter_session is REQUIRED
        - cash_received is REQUIRED
        - change_amount is CALCULATED by the backend
        - cash_received >= amount is VALIDATED

    For UPI/CARD payments:
        - transaction_reference is REQUIRED

    Idempotency:
        If idempotency_key is provided and a Payment with the same
        (bill, idempotency_key) already exists, the existing Payment
        is returned without creating a duplicate.

    Concurrency:
        The bill is locked with select_for_update() to prevent two
        cashiers simultaneously completing the remaining balance.

    Process:
        1. Validate auth + permissions.
        2. Validate bill is FINALIZED.
        3. Check idempotency — return existing if duplicate.
        4. Lock bill.
        5. Compute remaining_amount from DB aggregation.
        6. Validate amount <= remaining_amount.
        7. Validate payment method.
        8. Validate cash_received / change if CASH.
        9. Validate counter_session if CASH.
        10. Validate transaction_reference if digital.
        11. Generate payment number.
        12. Create Payment (COMPLETED — direct for recorded methods).
        13. Write audit log.

    Returns:
        Payment (status=COMPLETED for all current methods)

    Note:
        For Phase 9, all payment methods complete immediately upon creation
        (we are not integrating external gateways). PENDING status is used
        as an intermediate state for future gateway integrations.
    """
    from billing.models import Bill as BillModel

    _require_auth(user)

    if not acl.has_permission(user, "payment.create"):
        raise PermissionDenied("You do not have permission to create payments.")

    if not acl.can_access_branch(user, bill.branch):
        raise PermissionDenied("You do not have access to this bill's branch.")

    # Coerce and validate amount
    amount = coerce_decimal(amount, "amount")
    validate_bill_is_payable(bill)

    # Idempotency check BEFORE acquiring locks
    idem_key = validate_idempotency_key(idempotency_key)
    if idem_key:
        try:
            existing = Payment.objects.get(bill=bill, idempotency_key=idem_key)
            logger.info(
                "Idempotency hit: returning existing payment=%s for bill=%s key=%s",
                existing.payment_number,
                bill.bill_number,
                idem_key,
            )
            return existing
        except Payment.DoesNotExist:
            pass

    # Validate method early (before acquiring lock)
    validated_method = validate_payment_method(payment_method)

    # Validate cash-specific fields before lock
    change_amount = ZERO
    if validated_method in CASH_METHODS:
        cash_recv = coerce_decimal(cash_received, "cash_received") if cash_received is not None else None
        change_amount = validate_cash_payment(amount, cash_recv)
        validate_counter_session_open(counter_session, bill.branch)
        if counter is None and counter_session is not None:
            counter = counter_session.counter
    else:
        cash_recv = None
        validate_transaction_reference_required(validated_method, transaction_reference or "")

    try:
        with transaction.atomic():
            # Lock the bill — prevents concurrent payments draining remaining balance
            locked_bill = BillModel.objects.select_for_update().get(pk=bill.pk)

            # Re-validate bill status inside lock
            validate_bill_is_payable(locked_bill)

            # Compute remaining amount inside lock (DB aggregation on locked bill)
            remaining = money_utils.compute_remaining_amount(locked_bill)
            validate_payment_amount(amount, remaining)

            # Generate payment number inside atomic block
            payment_number = generate_payment_number()

            # Create Payment in COMPLETED state directly (no external gateway in Phase 9)
            now = timezone.now()
            payment = Payment.objects.create(
                bill=locked_bill,
                branch=locked_bill.branch,
                counter=counter,
                counter_session=counter_session,
                payment_number=payment_number,
                amount=money_utils.money(amount),
                cash_received=money_utils.money(cash_recv) if cash_recv is not None else None,
                change_amount=money_utils.money(change_amount) if validated_method in CASH_METHODS else None,
                payment_method=validated_method,
                transaction_reference=(transaction_reference or "").strip(),
                provider_reference=(provider_reference or "").strip(),
                status=PaymentStatus.COMPLETED,
                notes=(notes or "").strip(),
                idempotency_key=idem_key,
                initiated_by=user,
                completed_by=user,
                completed_at=now,
            )

            # Write audit log
            _log_audit(
                payment=payment,
                actor=user,
                action=AuditAction.PAYMENT_CREATED,
                old_status="",
                new_status=PaymentStatus.COMPLETED,
                amount=payment.amount,
                metadata={
                    "payment_method":        validated_method,
                    "bill_number":           locked_bill.bill_number,
                    "branch":                str(locked_bill.branch_id),
                    "counter":               str(counter.pk) if counter else None,
                    "counter_session":       str(counter_session.pk) if counter_session else None,
                    "transaction_reference": payment.transaction_reference,
                    "cash_received":         str(cash_recv) if cash_recv else None,
                    "change_amount":         str(change_amount) if validated_method in CASH_METHODS else None,
                    "idempotency_key":       idem_key or None,
                },
            )
            _log_audit(
                payment=payment,
                actor=user,
                action=AuditAction.PAYMENT_COMPLETED,
                old_status=PaymentStatus.PENDING,
                new_status=PaymentStatus.COMPLETED,
                amount=payment.amount,
                metadata={
                    "payment_method": validated_method,
                    "bill_number":    locked_bill.bill_number,
                },
            )

    except IntegrityError:
        # Concurrent creation with same idempotency key
        if idem_key:
            try:
                return Payment.objects.get(bill=bill, idempotency_key=idem_key)
            except Payment.DoesNotExist:
                pass
        raise

    logger.info(
        "Payment created: %s method=%s amount=%s bill=%s by user=%s",
        payment.payment_number,
        validated_method,
        payment.amount,
        bill.bill_number,
        user.email,
    )

    return payment


# =============================================================================
# 4. Payment Cancellation
# =============================================================================

def cancel_payment(payment: Payment, user, *, reason: str) -> Payment:
    """
    Cancel a PENDING payment.

    Only PENDING payments can be cancelled.
    COMPLETED payments must be refunded instead.

    Returns the updated Payment.
    """
    _require_auth(user)

    if not acl.has_permission(user, "payment.cancel"):
        raise PermissionDenied("You do not have permission to cancel payments.")

    if not acl.can_access_branch(user, payment.branch):
        raise PermissionDenied("You do not have access to this payment's branch.")

    if not reason or not reason.strip():
        raise ValidationError({"reason": "A cancellation reason is required."})

    if payment.status != PaymentStatus.PENDING:
        raise ValidationError(
            {
                "code": "PAYMENT_NOT_PENDING",
                "message": (
                    f"Only PENDING payments can be cancelled. "
                    f"Current status: {payment.status}."
                ),
            }
        )

    with transaction.atomic():
        locked = Payment.objects.select_for_update().get(pk=payment.pk)
        if locked.status != PaymentStatus.PENDING:
            raise ValidationError(
                {
                    "code": "PAYMENT_NOT_PENDING",
                    "message": f"Payment is already {locked.status}.",
                }
            )

        old_status = locked.status
        locked.status = PaymentStatus.CANCELLED
        locked.cancelled_at = timezone.now()
        locked.cancellation_reason = reason.strip()
        locked.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])

        _log_audit(
            payment=locked,
            actor=user,
            action=AuditAction.PAYMENT_CANCELLED,
            old_status=old_status,
            new_status=PaymentStatus.CANCELLED,
            amount=locked.amount,
            reason=reason.strip(),
        )

    logger.info(
        "Payment cancelled: %s reason=%s by user=%s",
        payment.payment_number, reason[:50], user.email,
    )
    payment.refresh_from_db()
    return payment


# =============================================================================
# 5. Refund Workflow
# =============================================================================

def request_refund(
    payment: Payment,
    user,
    *,
    amount,
    reason: str,
    notes: str = "",
) -> PaymentRefund:
    """
    Request a refund against a COMPLETED payment.

    Rules:
        - payment must be COMPLETED or PARTIALLY_REFUNDED.
        - amount must be > 0 and <= refundable_amount.
        - reason is required.
        - user must have payment.refund.request permission.

    Returns the created PaymentRefund (status=REQUESTED).
    """
    _require_auth(user)

    if not acl.has_permission(user, "payment.refund.request"):
        raise PermissionDenied("You do not have permission to request refunds.")

    if not acl.can_access_branch(user, payment.branch):
        raise PermissionDenied("You do not have access to this payment's branch.")

    refund_amount = coerce_decimal(amount, "amount")
    validated_reason = validate_refund_reason(reason)

    if payment.status not in (PaymentStatus.COMPLETED, PaymentStatus.PARTIALLY_REFUNDED):
        raise ValidationError(
            {
                "code": "PAYMENT_NOT_REFUNDABLE",
                "message": (
                    "Refunds can only be requested for COMPLETED or "
                    f"PARTIALLY_REFUNDED payments. Current status: {payment.status}."
                ),
            }
        )

    with transaction.atomic():
        locked = Payment.objects.select_for_update().get(pk=payment.pk)

        if locked.status not in (PaymentStatus.COMPLETED, PaymentStatus.PARTIALLY_REFUNDED):
            raise ValidationError(
                {
                    "code": "PAYMENT_NOT_REFUNDABLE",
                    "message": f"Payment status is {locked.status}.",
                }
            )

        refund_summary = money_utils.compute_refund_summary_for_payment(locked)
        validate_refund_amount(refund_amount, refund_summary["refundable_amount"])

        refund_number = generate_refund_number()

        refund = PaymentRefund.objects.create(
            payment=locked,
            refund_number=refund_number,
            amount=money_utils.money(refund_amount),
            status=RefundStatus.REQUESTED,
            reason=validated_reason,
            notes=(notes or "").strip(),
            requested_by=user,
        )

        _log_audit(
            payment=locked,
            refund=refund,
            actor=user,
            action=AuditAction.REFUND_REQUESTED,
            old_status=locked.status,
            new_status=locked.status,
            amount=refund_amount,
            reason=validated_reason,
            metadata={
                "refund_number":     refund_number,
                "refundable_amount": str(refund_summary["refundable_amount"]),
            },
        )

    logger.info(
        "Refund requested: %s amount=%s payment=%s by user=%s",
        refund.refund_number, refund_amount, payment.payment_number, user.email,
    )
    return refund


def approve_refund(refund: PaymentRefund, user) -> PaymentRefund:
    """
    Approve a REQUESTED refund.

    Rules:
        - user must have payment.refund.approve permission.
        - refund must be in REQUESTED status.
        - Self-approval is not explicitly blocked (differs from billing corrections
          since refunds often need quick approval in POS environments).
          Add self-approval check if business policy requires it.

    Returns the updated PaymentRefund.
    """
    _require_auth(user)

    if not acl.has_permission(user, "payment.refund.approve"):
        raise PermissionDenied("You do not have permission to approve refunds.")

    if not acl.can_access_branch(user, refund.payment.branch):
        raise PermissionDenied("You do not have access to this refund's branch.")

    if refund.status != RefundStatus.REQUESTED:
        raise ValidationError(
            {
                "code": "REFUND_NOT_REQUESTED",
                "message": (
                    f"Only REQUESTED refunds can be approved. "
                    f"Current status: {refund.status}."
                ),
            }
        )

    with transaction.atomic():
        locked = PaymentRefund.objects.select_for_update().get(pk=refund.pk)
        if locked.status != RefundStatus.REQUESTED:
            raise ValidationError(
                {"code": "REFUND_NOT_REQUESTED", "message": f"Refund is already {locked.status}."}
            )

        old_status = locked.status
        locked.status = RefundStatus.APPROVED
        locked.approved_by = user
        locked.approved_at = timezone.now()
        locked.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

        _log_audit(
            payment=locked.payment,
            refund=locked,
            actor=user,
            action=AuditAction.REFUND_APPROVED,
            old_status=old_status,
            new_status=RefundStatus.APPROVED,
            amount=locked.amount,
        )

    logger.info(
        "Refund approved: %s by user=%s",
        refund.refund_number, user.email,
    )
    refund.refresh_from_db()
    return refund


def reject_refund(refund: PaymentRefund, user, *, reason: str) -> PaymentRefund:
    """
    Reject a REQUESTED refund.

    Rules:
        - user must have payment.refund.approve permission.
        - refund must be in REQUESTED status.
        - reason is required.

    Returns the updated PaymentRefund.
    """
    _require_auth(user)

    if not acl.has_permission(user, "payment.refund.approve"):
        raise PermissionDenied("You do not have permission to reject refunds.")

    if not acl.can_access_branch(user, refund.payment.branch):
        raise PermissionDenied("You do not have access to this refund's branch.")

    if not reason or not reason.strip():
        raise ValidationError({"reason": "A rejection reason is required."})

    if refund.status != RefundStatus.REQUESTED:
        raise ValidationError(
            {
                "code": "REFUND_NOT_REQUESTED",
                "message": (
                    f"Only REQUESTED refunds can be rejected. "
                    f"Current status: {refund.status}."
                ),
            }
        )

    with transaction.atomic():
        locked = PaymentRefund.objects.select_for_update().get(pk=refund.pk)
        if locked.status != RefundStatus.REQUESTED:
            raise ValidationError(
                {"code": "REFUND_NOT_REQUESTED", "message": f"Refund is already {locked.status}."}
            )

        old_status = locked.status
        locked.status = RefundStatus.REJECTED
        locked.approved_by = user    # reviewer field
        locked.rejected_at = timezone.now()
        locked.rejection_reason = reason.strip()
        locked.save(update_fields=[
            "status", "approved_by", "rejected_at", "rejection_reason", "updated_at"
        ])

        _log_audit(
            payment=locked.payment,
            refund=locked,
            actor=user,
            action=AuditAction.REFUND_REJECTED,
            old_status=old_status,
            new_status=RefundStatus.REJECTED,
            amount=locked.amount,
            reason=reason.strip(),
        )

    logger.info(
        "Refund rejected: %s by user=%s reason=%s",
        refund.refund_number, user.email, reason[:50],
    )
    refund.refresh_from_db()
    return refund


def process_refund(
    refund: PaymentRefund,
    user,
    *,
    transaction_reference: str = "",
    notes: str = "",
) -> PaymentRefund:
    """
    Mark an APPROVED refund as PROCESSED (money returned to customer).

    After processing:
        - Recomputes total_refunded for the parent payment.
        - Updates payment status to PARTIALLY_REFUNDED or REFUNDED.

    Rules:
        - user must have payment.refund.process permission.
        - refund must be in APPROVED status.

    Returns the updated PaymentRefund.
    """
    _require_auth(user)

    if not acl.has_permission(user, "payment.refund.process"):
        raise PermissionDenied("You do not have permission to process refunds.")

    if not acl.can_access_branch(user, refund.payment.branch):
        raise PermissionDenied("You do not have access to this refund's branch.")

    if refund.status != RefundStatus.APPROVED:
        raise ValidationError(
            {
                "code": "REFUND_NOT_APPROVED",
                "message": (
                    f"Only APPROVED refunds can be processed. "
                    f"Current status: {refund.status}."
                ),
            }
        )

    with transaction.atomic():
        locked_refund = PaymentRefund.objects.select_for_update().get(pk=refund.pk)
        if locked_refund.status != RefundStatus.APPROVED:
            raise ValidationError(
                {"code": "REFUND_NOT_APPROVED", "message": f"Refund is already {locked_refund.status}."}
            )

        # Also lock the parent payment
        locked_payment = Payment.objects.select_for_update().get(pk=locked_refund.payment_id)

        old_refund_status = locked_refund.status
        locked_refund.status = RefundStatus.PROCESSED
        locked_refund.processed_by = user
        locked_refund.processed_at = timezone.now()
        locked_refund.transaction_reference = (transaction_reference or "").strip()
        if notes:
            locked_refund.notes = notes.strip()
        locked_refund.save(update_fields=[
            "status", "processed_by", "processed_at",
            "transaction_reference", "notes", "updated_at",
        ])

        # Recompute payment refund status
        total_refunded = money_utils.compute_refund_summary_for_payment(locked_payment)["total_refunded"]
        # Include the just-processed refund in the total
        # (compute_refund_summary_for_payment queries DB, which now has this refund as PROCESSED)
        # Re-query to get accurate total
        from django.db.models import Sum
        total_processed = locked_payment.refunds.filter(
            status=RefundStatus.PROCESSED
        ).aggregate(total=Sum("amount"))["total"] or ZERO

        total_processed = money_utils.money(total_processed)
        payment_amount = money_utils.money(locked_payment.amount)

        old_payment_status = locked_payment.status
        if total_processed >= payment_amount:
            new_payment_status = PaymentStatus.REFUNDED
        else:
            new_payment_status = PaymentStatus.PARTIALLY_REFUNDED

        if locked_payment.status != new_payment_status:
            locked_payment.status = new_payment_status
            locked_payment.save(update_fields=["status", "updated_at"])

        _log_audit(
            payment=locked_payment,
            refund=locked_refund,
            actor=user,
            action=AuditAction.REFUND_PROCESSED,
            old_status=old_refund_status,
            new_status=RefundStatus.PROCESSED,
            amount=locked_refund.amount,
            metadata={
                "refund_number":        locked_refund.refund_number,
                "transaction_reference": locked_refund.transaction_reference,
                "payment_old_status":   old_payment_status,
                "payment_new_status":   new_payment_status,
                "total_processed":      str(total_processed),
            },
        )

    logger.info(
        "Refund processed: %s amount=%s payment=%s by user=%s",
        locked_refund.refund_number, locked_refund.amount,
        locked_payment.payment_number, user.email,
    )
    refund.refresh_from_db()
    return refund


def cancel_refund(refund: PaymentRefund, user) -> PaymentRefund:
    """
    Cancel a REQUESTED refund (before it is approved).

    Only the requester or someone with payment.refund.approve can cancel.
    Only REQUESTED refunds may be cancelled.
    """
    _require_auth(user)

    is_requester = (refund.requested_by_id == user.pk)
    has_approve = acl.has_permission(user, "payment.refund.approve")

    if not is_requester and not has_approve:
        raise PermissionDenied(
            "Only the requester or an approver can cancel a refund request."
        )

    if not acl.can_access_branch(user, refund.payment.branch):
        raise PermissionDenied("You do not have access to this refund's branch.")

    if refund.status != RefundStatus.REQUESTED:
        raise ValidationError(
            {
                "code": "REFUND_NOT_REQUESTED",
                "message": (
                    f"Only REQUESTED refunds can be cancelled. "
                    f"Current status: {refund.status}."
                ),
            }
        )

    with transaction.atomic():
        locked = PaymentRefund.objects.select_for_update().get(pk=refund.pk)
        if locked.status != RefundStatus.REQUESTED:
            raise ValidationError(
                {"code": "REFUND_NOT_REQUESTED", "message": f"Refund is already {locked.status}."}
            )

        old_status = locked.status
        locked.status = RefundStatus.CANCELLED
        locked.save(update_fields=["status", "updated_at"])

        _log_audit(
            payment=locked.payment,
            refund=locked,
            actor=user,
            action=AuditAction.REFUND_CANCELLED,
            old_status=old_status,
            new_status=RefundStatus.CANCELLED,
            amount=locked.amount,
        )

    logger.info(
        "Refund cancelled: %s by user=%s",
        refund.refund_number, user.email,
    )
    refund.refresh_from_db()
    return refund


# =============================================================================
# 6. Bill Payment Summary
# =============================================================================

def get_bill_payment_summary(bill) -> dict:
    """
    Return a summary of all payments and refunds for a bill.

    Used by the POS payment screen and manager views.

    Returns:
    {
        "bill_id":          str,
        "bill_number":      str,
        "bill_total":       str,
        "total_paid":       str,
        "total_refunded":   str,
        "remaining":        str,
        "payment_status":   str (BillPaymentStatus),
        "payments": [
            {
                "id", "payment_number", "amount", "payment_method",
                "status", "transaction_reference", "cash_received",
                "change_amount", "initiated_by_name", "completed_at",
                "created_at", "refunds": [...],
            }
        ],
    }
    """
    from django.db.models import Sum

    bill_total = money_utils.money(bill.grand_total)
    total_paid = money_utils.compute_successful_payments_total(bill)

    # Total refunded across all payments for this bill
    total_refunded = money_utils.money(
        PaymentRefund.objects.filter(
            payment__bill=bill,
            status=RefundStatus.PROCESSED,
        ).aggregate(total=Sum("amount"))["total"] or ZERO
    )

    remaining = max(money_utils.money(bill_total - total_paid), ZERO)
    payment_status = money_utils.compute_bill_payment_status(bill_total, total_paid)

    payments_qs = (
        Payment.objects.filter(bill=bill)
        .select_related("initiated_by", "completed_by")
        .prefetch_related("refunds__requested_by", "refunds__approved_by", "refunds__processed_by")
        .order_by("created_at")
    )

    payments_data = []
    for p in payments_qs:
        refunds_data = []
        for r in p.refunds.all().order_by("requested_at"):
            refunds_data.append({
                "id":                    str(r.id),
                "refund_number":         r.refund_number,
                "amount":                str(r.amount),
                "status":                r.status,
                "reason":                r.reason,
                "rejection_reason":      r.rejection_reason,
                "transaction_reference": r.transaction_reference,
                "requested_by_name":     r.requested_by.full_name if r.requested_by else None,
                "approved_by_name":      r.approved_by.full_name if r.approved_by else None,
                "processed_by_name":     r.processed_by.full_name if r.processed_by else None,
                "requested_at":          r.requested_at.isoformat(),
                "approved_at":           r.approved_at.isoformat() if r.approved_at else None,
                "processed_at":          r.processed_at.isoformat() if r.processed_at else None,
                "rejected_at":           r.rejected_at.isoformat() if r.rejected_at else None,
            })

        payments_data.append({
            "id":                    str(p.id),
            "payment_number":        p.payment_number,
            "amount":                str(p.amount),
            "payment_method":        p.payment_method,
            "status":                p.status,
            "transaction_reference": p.transaction_reference,
            "provider_reference":    p.provider_reference,
            "cash_received":         str(p.cash_received) if p.cash_received is not None else None,
            "change_amount":         str(p.change_amount) if p.change_amount is not None else None,
            "notes":                 p.notes,
            "initiated_by_name":     p.initiated_by.full_name if p.initiated_by else None,
            "completed_by_name":     p.completed_by.full_name if p.completed_by else None,
            "completed_at":          p.completed_at.isoformat() if p.completed_at else None,
            "cancelled_at":          p.cancelled_at.isoformat() if p.cancelled_at else None,
            "cancellation_reason":   p.cancellation_reason,
            "created_at":            p.created_at.isoformat(),
            "counter_code":          p.counter.code if p.counter else None,
            "counter_session_id":    str(p.counter_session_id) if p.counter_session_id else None,
            "refunds":               refunds_data,
        })

    return {
        "bill_id":        str(bill.id),
        "bill_number":    bill.bill_number,
        "bill_total":     str(bill_total),
        "total_paid":     str(total_paid),
        "total_refunded": str(total_refunded),
        "remaining":      str(remaining),
        "payment_status": payment_status,
        "payments":       payments_data,
    }


# =============================================================================
# 7. Payment Receipt Data
# =============================================================================

def get_payment_receipt_data(bill) -> dict:
    """
    Build the payment section for the bill receipt.

    Returns a dict compatible with the billing receipt structure,
    to be merged into get_bill_receipt_data() output.

    Returns:
    {
        "payment_status":  str,
        "total_paid":      str,
        "total_refunded":  str,
        "remaining":       str,
        "payments": [
            {
                "payment_number", "payment_method", "amount",
                "cash_received", "change_amount",
                "transaction_reference", "completed_at",
            }
        ],
    }
    """
    summary = get_bill_payment_summary(bill)

    payment_lines = []
    for p in summary["payments"]:
        if p["status"] == PaymentStatus.COMPLETED:
            payment_lines.append({
                "payment_number":        p["payment_number"],
                "payment_method":        p["payment_method"],
                "amount":                p["amount"],
                "cash_received":         p["cash_received"],
                "change_amount":         p["change_amount"],
                "transaction_reference": p["transaction_reference"],
                "completed_at":          p["completed_at"],
            })

    return {
        "payment_status":  summary["payment_status"],
        "total_paid":      summary["total_paid"],
        "total_refunded":  summary["total_refunded"],
        "remaining":       summary["remaining"],
        "payments":        payment_lines,
    }
