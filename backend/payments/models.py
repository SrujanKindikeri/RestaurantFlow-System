# =============================================================================
# RestaurantFlow — Payment Models
# Phase 9
#
# Architecture:
#   Bill (Phase 8, financial document)
#       └── Payment  (one or more — split payments supported)
#               └── PaymentRefund  (separate refund records per payment)
#
#   PaymentSequence  (concurrency-safe PAY-XXXXXX number generation)
#
#   PaymentAuditLog  (immutable audit trail for every payment action)
#
# Design principles:
#   - UUID primary keys on all models.
#   - All monetary values use DecimalField — NEVER float.
#   - Payment amounts are immutable once COMPLETED.
#   - Refunds are separate records — never mutate a completed payment.
#   - Status transitions enforced in service layer, not arbitrarily via API.
#   - Payment.amount = authoritative; cash_received and change_amount
#     are calculated by the backend for CASH payments.
#   - idempotency_key prevents duplicate payments on retry.
#   - Cash payments MUST be linked to an OPEN CounterSession.
#   - counter/counter_session validated to match bill.branch.
#
# Status state machines:
#   Payment:  PENDING → COMPLETED (terminal)
#             PENDING → FAILED    (terminal)
#             PENDING → CANCELLED (terminal)
#             COMPLETED → REFUNDED (full refund)
#             COMPLETED → PARTIALLY_REFUNDED
#
#   PaymentRefund: REQUESTED → APPROVED → PROCESSED (terminal)
#                  REQUESTED → REJECTED  (terminal)
#                  REQUESTED → CANCELLED (terminal)
#
# Financial invariants (enforced in services.py):
#   sum(successful payments) - sum(successful refunds) <= bill.grand_total
#   payment.amount cannot exceed bill.remaining_amount at time of creation
#   refund.amount cannot exceed (payment.amount - already_refunded)
#
# Security:
#   - IDOR prevention: all querysets filtered via payments.access.
#   - Organization/restaurant/branch scope enforced server-side.
#   - Frontend-supplied totals are NEVER trusted.
#   - Only safe transaction references stored (never card/CVV/UPI PIN).
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel

logger = logging.getLogger("payments")


# =============================================================================
# Payment Status
# =============================================================================

class PaymentStatus(models.TextChoices):
    PENDING              = "PENDING",              "Pending"
    COMPLETED            = "COMPLETED",            "Completed"
    FAILED               = "FAILED",               "Failed"
    CANCELLED            = "CANCELLED",            "Cancelled"
    REFUNDED             = "REFUNDED",             "Refunded"
    PARTIALLY_REFUNDED   = "PARTIALLY_REFUNDED",   "Partially Refunded"


# =============================================================================
# Payment Method
# =============================================================================

class PaymentMethod(models.TextChoices):
    CASH         = "CASH",         "Cash"
    UPI          = "UPI",          "UPI"
    CARD         = "CARD",         "Card"
    WALLET       = "WALLET",       "Wallet"
    NET_BANKING  = "NET_BANKING",  "Net Banking"
    BANK_TRANSFER = "BANK_TRANSFER", "Bank Transfer"
    CHEQUE       = "CHEQUE",       "Cheque"
    CREDIT       = "CREDIT",       "Credit"
    OTHER        = "OTHER",        "Other"


# =============================================================================
# Bill Payment Status (derived from payments, stored on bill for querying)
# =============================================================================

class BillPaymentStatus(models.TextChoices):
    UNPAID          = "UNPAID",          "Unpaid"
    PARTIALLY_PAID  = "PARTIALLY_PAID",  "Partially Paid"
    PAID            = "PAID",            "Paid"
    OVERPAID        = "OVERPAID",        "Overpaid"


# =============================================================================
# Refund Status
# =============================================================================

class RefundStatus(models.TextChoices):
    REQUESTED  = "REQUESTED",  "Requested"
    APPROVED   = "APPROVED",   "Approved"
    REJECTED   = "REJECTED",   "Rejected"
    PROCESSED  = "PROCESSED",  "Processed"
    CANCELLED  = "CANCELLED",  "Cancelled"


# =============================================================================
# Audit Action
# =============================================================================

class AuditAction(models.TextChoices):
    PAYMENT_CREATED    = "PAYMENT_CREATED",    "Payment Created"
    PAYMENT_COMPLETED  = "PAYMENT_COMPLETED",  "Payment Completed"
    PAYMENT_FAILED     = "PAYMENT_FAILED",     "Payment Failed"
    PAYMENT_CANCELLED  = "PAYMENT_CANCELLED",  "Payment Cancelled"
    REFUND_REQUESTED   = "REFUND_REQUESTED",   "Refund Requested"
    REFUND_APPROVED    = "REFUND_APPROVED",    "Refund Approved"
    REFUND_REJECTED    = "REFUND_REJECTED",    "Refund Rejected"
    REFUND_PROCESSED   = "REFUND_PROCESSED",   "Refund Processed"
    REFUND_CANCELLED   = "REFUND_CANCELLED",   "Refund Cancelled"


# =============================================================================
# PaymentSequence
# =============================================================================

class PaymentSequence(TimestampedModel):
    """
    Concurrency-safe global payment number sequence.

    Unlike BillSequence (per-branch, annual), payment sequences are
    GLOBAL — they give numbers like:
        PAY-000001
        PAY-000002
        PAY-999999

    One row total (branch=None) or per-branch if multi-branch isolation desired.
    For Phase 9, we use a single global sequence.
    select_for_update() is used in the service layer — never MAX()+1.

    Format: PAY-{seq:06d}

    Immutable once a payment number is issued.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # sequence_key groups numbers — 'GLOBAL' for the single global sequence
    sequence_key = models.CharField(max_length=20, unique=True, db_index=True, default="GLOBAL")

    # The last issued sequence number — incremented atomically
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Payment Sequence"
        verbose_name_plural = "Payment Sequences"

    def __str__(self):
        return f"PaymentSeq key={self.sequence_key} seq={self.last_sequence}"


# =============================================================================
# Payment
# =============================================================================

class Payment(TimestampedModel):
    """
    A payment transaction against a finalized Bill.

    One Bill can have multiple Payment records (split payments).
    A Payment is created in PENDING status and transitions to
    COMPLETED, FAILED, or CANCELLED.

    Financial invariants:
        amount > 0
        sum(COMPLETED payments for bill) <= bill.grand_total
        For CASH: cash_received >= amount (validated by backend)
        change_amount = cash_received - amount (calculated by backend)

    Cash payments require an OPEN CounterSession at the bill's branch.
    Non-cash payments store a safe transaction_reference only.

    Idempotency:
        idempotency_key prevents duplicate payment creation on network retry.
        Unique constraint scoped to (bill, idempotency_key).

    Immutability:
        Once status = COMPLETED, the amount field is immutable.
        Corrections must go through PaymentRefund.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Core references
    # -------------------------------------------------------------------------
    bill = models.ForeignKey(
        "billing.Bill",
        on_delete=models.PROTECT,
        related_name="payments",
        db_index=True,
        help_text="The finalized bill this payment is for.",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="payments",
        db_index=True,
        help_text="Denormalized branch reference for efficient querying.",
    )

    # Counter / session — required for CASH, optional for others
    counter = models.ForeignKey(
        "counters.Counter",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
        db_index=True,
        help_text="Physical counter where cash payment was made.",
    )
    counter_session = models.ForeignKey(
        "counters.CounterSession",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payments",
        db_index=True,
        help_text="Active counter session at time of cash payment.",
    )

    # -------------------------------------------------------------------------
    # Human-readable payment number — immutable after creation
    # -------------------------------------------------------------------------
    payment_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Human-readable payment number. Format: PAY-{seq:06d}. Immutable.",
    )

    # -------------------------------------------------------------------------
    # Financial fields — all Decimal; backend-authoritative
    # -------------------------------------------------------------------------
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Authoritative payment amount. "
            "Must equal bill.grand_total for full payment, "
            "or the partial amount for split payments. "
            "Immutable after COMPLETED."
        ),
    )
    cash_received = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Cash tendered by the customer (CASH method only). "
            "Must be >= amount. Set by the cashier."
        ),
    )
    change_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Change returned to customer. Calculated by backend: "
            "cash_received - amount. Never trusted from frontend."
        ),
    )

    # -------------------------------------------------------------------------
    # Payment method and external references
    # -------------------------------------------------------------------------
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        db_index=True,
        help_text="Payment method used.",
    )
    transaction_reference = models.CharField(
        max_length=200,
        blank=True,
        db_index=True,
        help_text=(
            "Safe external transaction reference. "
            "For UPI: UTR/transaction ID. "
            "For CARD: POS terminal reference. "
            "NEVER store card numbers, CVV, UPI PIN, or credentials."
        ),
    )
    provider_reference = models.CharField(
        max_length=200,
        blank=True,
        help_text=(
            "Provider-internal reference (e.g. bank reference, POS batch ID). "
            "Safe metadata only."
        ),
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )

    notes = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Idempotency
    # -------------------------------------------------------------------------
    idempotency_key = models.CharField(
        max_length=128,
        blank=True,
        db_index=True,
        help_text=(
            "Client-supplied idempotency key. "
            "Prevents duplicate payment creation on network retry. "
            "Unique per bill."
        ),
    )

    # -------------------------------------------------------------------------
    # Actors and timestamps
    # -------------------------------------------------------------------------
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="initiated_payments",
        help_text="User who initiated (created) this payment.",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="completed_payments",
        help_text="User who completed the payment.",
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["bill", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["counter", "status"]),
            models.Index(fields=["counter_session", "status"]),
            models.Index(fields=["payment_method", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["initiated_by", "status"]),
            models.Index(fields=["transaction_reference"]),
        ]
        constraints = [
            # Idempotency: unique (bill, idempotency_key) when key is non-empty.
            # Implemented at service layer (not DB) since blank keys must be allowed.
        ]

    def __str__(self):
        return f"{self.payment_number} [{self.status}] {self.payment_method} {self.amount}"

    @property
    def is_successful(self) -> bool:
        """True if the payment has been completed (contributes to bill total)."""
        return self.status == PaymentStatus.COMPLETED

    @property
    def total_refunded(self):
        """Sum of all PROCESSED refunds for this payment."""
        from django.db.models import Sum
        from decimal import Decimal
        result = self.refunds.filter(status=RefundStatus.PROCESSED).aggregate(
            total=Sum("amount")
        )
        return result["total"] or Decimal("0.00")

    @property
    def refundable_amount(self):
        """Maximum amount that can still be refunded."""
        return self.amount - self.total_refunded


# =============================================================================
# PaymentRefund
# =============================================================================

class PaymentRefund(TimestampedModel):
    """
    A refund against a completed Payment.

    Refunds are SEPARATE records — they never mutate the Payment.amount.
    A Payment can have multiple PaymentRefunds (partial refunds).

    Financial invariants:
        sum(PROCESSED refunds) <= payment.amount
        Each refund.amount > 0

    Status workflow:
        REQUESTED → APPROVED → PROCESSED
        REQUESTED → REJECTED
        REQUESTED → CANCELLED

    Permissions:
        payment.refund.request — initiate a refund request
        payment.refund.approve — approve or reject
        payment.refund.process — mark as processed (trigger actual return)

    Refund number:
        Format: REF-{seq:06d}
        Uses PaymentSequence with key="REFUND" for a separate sequence.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="refunds",
        db_index=True,
        help_text="The completed payment being refunded.",
    )

    # -------------------------------------------------------------------------
    # Human-readable refund number — immutable after creation
    # -------------------------------------------------------------------------
    refund_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Human-readable refund number. Format: REF-{seq:06d}. Immutable.",
    )

    # -------------------------------------------------------------------------
    # Financial fields
    # -------------------------------------------------------------------------
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Refund amount. Must be > 0 and <= (payment.amount - already refunded)."
        ),
    )

    # -------------------------------------------------------------------------
    # Status and reason
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.REQUESTED,
        db_index=True,
    )
    reason = models.TextField(
        help_text="Required reason for the refund request.",
    )
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # External reference (for processed refunds)
    # -------------------------------------------------------------------------
    transaction_reference = models.CharField(
        max_length=200,
        blank=True,
        help_text="External reference for the processed refund transaction.",
    )

    # -------------------------------------------------------------------------
    # Actors and timestamps
    # -------------------------------------------------------------------------
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_refunds",
        help_text="User who requested the refund.",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_refunds",
        help_text="User who approved the refund.",
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="processed_refunds",
        help_text="User who marked the refund as processed.",
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Payment Refund"
        verbose_name_plural = "Payment Refunds"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["payment", "status"]),
            models.Index(fields=["refund_number"]),
            models.Index(fields=["status", "requested_at"]),
            models.Index(fields=["requested_by", "status"]),
        ]

    def __str__(self):
        return f"{self.refund_number} [{self.status}] {self.amount} for {self.payment.payment_number}"


# =============================================================================
# PaymentAuditLog
# =============================================================================

class PaymentAuditLog(TimestampedModel):
    """
    Immutable audit trail for all payment and refund actions.

    Every state transition creates one record.
    Records are never updated or deleted — append only.

    This allows a manager to answer:
        Who paid this bill? When? How much? Which method?
        Which counter? Which counter session? Which cashier?
        Was it refunded? Who approved? Who processed?
        How much refunded?

    Stores:
        actor       — who performed the action
        action      — what was done (AuditAction enum)
        payment     — which payment (nullable for org-level events)
        refund      — which refund (if applicable)
        old_status  — previous status
        new_status  — new status
        amount      — amount involved
        metadata    — JSON blob for extra context
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="audit_logs",
        db_index=True,
        help_text="The payment this audit log entry relates to.",
    )
    refund = models.ForeignKey(
        PaymentRefund,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_logs",
        db_index=True,
        help_text="The refund this audit log entry relates to (if applicable).",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="payment_audit_logs",
        help_text="User who performed the action.",
    )
    action = models.CharField(
        max_length=30,
        choices=AuditAction.choices,
        db_index=True,
    )
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, blank=True)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount involved in this action.",
    )
    reason = models.TextField(blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context: method, reference, counter, session, etc.",
    )

    class Meta:
        verbose_name = "Payment Audit Log"
        verbose_name_plural = "Payment Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["payment", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return (
            f"Audit {self.action} | {self.payment.payment_number} "
            f"| {self.actor.email} | {self.created_at}"
        )

    def save(self, *args, **kwargs):
        # Audit logs are append-only — block updates
        if self.pk and PaymentAuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("PaymentAuditLog records are immutable.")
        super().save(*args, **kwargs)
