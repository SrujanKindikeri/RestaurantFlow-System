# =============================================================================
# RestaurantFlow — Payment Serializers
# Phase 9
#
# Input serializers validate the shape of incoming data only.
# They do NOT perform business logic — that belongs in services.py.
#
# Output serializers render payment data for API responses.
# They are read-only and never expose sensitive data.
#
# Security rules enforced here:
#   - Frontend must NOT send: grand_total, change_amount, remaining_amount,
#     payment_status, bill_total.
#   - Frontend MUST send: bill_id, amount, payment_method.
#   - For CASH: cash_received is required (validated in service).
#   - For UPI/CARD: transaction_reference is required (validated in service).
#   - idempotency_key is client-supplied; max 128 chars.
# =============================================================================

from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from payments.models import (
    Payment,
    PaymentRefund,
    PaymentAuditLog,
    PaymentStatus,
    PaymentMethod,
    RefundStatus,
)


# =============================================================================
# Read serializers
# =============================================================================

class PaymentRefundReadSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.SerializerMethodField()
    requested_by_name  = serializers.SerializerMethodField()
    approved_by_email  = serializers.SerializerMethodField()
    approved_by_name   = serializers.SerializerMethodField()
    processed_by_name  = serializers.SerializerMethodField()

    class Meta:
        model  = PaymentRefund
        fields = [
            "id",
            "refund_number",
            "payment",
            "amount",
            "status",
            "reason",
            "rejection_reason",
            "notes",
            "transaction_reference",
            "requested_by",
            "requested_by_email",
            "requested_by_name",
            "approved_by",
            "approved_by_email",
            "approved_by_name",
            "processed_by",
            "processed_by_name",
            "requested_at",
            "approved_at",
            "processed_at",
            "rejected_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_requested_by_email(self, obj):
        return obj.requested_by.email if obj.requested_by else None

    def get_requested_by_name(self, obj):
        return obj.requested_by.full_name if obj.requested_by else None

    def get_approved_by_email(self, obj):
        return obj.approved_by.email if obj.approved_by else None

    def get_approved_by_name(self, obj):
        return obj.approved_by.full_name if obj.approved_by else None

    def get_processed_by_name(self, obj):
        return obj.processed_by.full_name if obj.processed_by else None


class PaymentReadSerializer(serializers.ModelSerializer):
    """Full payment detail including nested refunds."""
    bill_number          = serializers.SerializerMethodField()
    branch_name          = serializers.SerializerMethodField()
    counter_code         = serializers.SerializerMethodField()
    counter_session_id   = serializers.SerializerMethodField()
    initiated_by_email   = serializers.SerializerMethodField()
    initiated_by_name    = serializers.SerializerMethodField()
    completed_by_name    = serializers.SerializerMethodField()
    refunds              = PaymentRefundReadSerializer(many=True, read_only=True)

    class Meta:
        model  = Payment
        fields = [
            "id",
            "payment_number",
            "bill",
            "bill_number",
            "branch",
            "branch_name",
            "counter",
            "counter_code",
            "counter_session",
            "counter_session_id",
            "amount",
            "payment_method",
            "status",
            "transaction_reference",
            "provider_reference",
            "cash_received",
            "change_amount",
            "notes",
            "idempotency_key",
            "initiated_by",
            "initiated_by_email",
            "initiated_by_name",
            "completed_by",
            "completed_by_name",
            "completed_at",
            "failed_at",
            "cancelled_at",
            "cancellation_reason",
            "refunds",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_bill_number(self, obj):
        try:
            return obj.bill.bill_number
        except Exception:
            return None

    def get_branch_name(self, obj):
        try:
            return obj.branch.name
        except Exception:
            return None

    def get_counter_code(self, obj):
        return obj.counter.code if obj.counter else None

    def get_counter_session_id(self, obj):
        return str(obj.counter_session_id) if obj.counter_session_id else None

    def get_initiated_by_email(self, obj):
        return obj.initiated_by.email if obj.initiated_by else None

    def get_initiated_by_name(self, obj):
        return obj.initiated_by.full_name if obj.initiated_by else None

    def get_completed_by_name(self, obj):
        return obj.completed_by.full_name if obj.completed_by else None


class PaymentListSerializer(serializers.ModelSerializer):
    """Compact serializer for list views — no nested refunds."""
    bill_number        = serializers.SerializerMethodField()
    order_number       = serializers.SerializerMethodField()
    branch_name        = serializers.SerializerMethodField()
    counter_code       = serializers.SerializerMethodField()
    initiated_by_name  = serializers.SerializerMethodField()

    class Meta:
        model  = Payment
        fields = [
            "id",
            "payment_number",
            "bill",
            "bill_number",
            "order_number",
            "branch",
            "branch_name",
            "counter_code",
            "amount",
            "payment_method",
            "status",
            "transaction_reference",
            "cash_received",
            "change_amount",
            "initiated_by",
            "initiated_by_name",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_bill_number(self, obj):
        try:
            return obj.bill.bill_number
        except Exception:
            return None

    def get_order_number(self, obj):
        try:
            return obj.bill.order.order_number
        except Exception:
            return None

    def get_branch_name(self, obj):
        try:
            return obj.branch.name
        except Exception:
            return None

    def get_counter_code(self, obj):
        return obj.counter.code if obj.counter else None

    def get_initiated_by_name(self, obj):
        return obj.initiated_by.full_name if obj.initiated_by else None


# =============================================================================
# Write serializers (input validation only)
# =============================================================================

class CreatePaymentSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/payments/

    Frontend sends:
        bill_id              (required) — UUID of the finalized bill
        amount               (required) — Decimal string, e.g. "500.00"
        payment_method       (required) — "CASH", "UPI", "CARD", etc.
        cash_received        (optional) — required for CASH method
        transaction_reference (optional) — required for UPI/CARD
        provider_reference   (optional) — optional for all methods
        notes                (optional)
        idempotency_key      (optional) — client-generated UUID
        counter_session      (optional) — UUID of open counter session (required for CASH)

    Frontend must NOT send:
        change_amount, remaining_amount, bill_total, grand_total,
        payment_status, tax_amount, subtotal.
    """
    bill_id               = serializers.UUIDField()
    amount                = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    payment_method        = serializers.ChoiceField(choices=PaymentMethod.choices)
    cash_received         = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    transaction_reference = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    provider_reference    = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    notes                 = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    idempotency_key       = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    counter_session       = serializers.UUIDField(required=False, allow_null=True, default=None)

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("amount must be greater than zero.")
        return value

    def validate_cash_received(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("cash_received must be greater than zero.")
        return value


class CancelPaymentSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3, max_length=500)


class CreateRefundSerializer(serializers.Serializer):
    """Input serializer for POST /api/payments/{id}/refunds/"""
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    reason = serializers.CharField(min_length=5, max_length=1000)
    notes  = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Refund amount must be greater than zero.")
        return value


class RejectRefundSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=5, max_length=500)


class ProcessRefundSerializer(serializers.Serializer):
    transaction_reference = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    notes                 = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


# =============================================================================
# Bill payment summary serializer (output only)
# =============================================================================

class BillPaymentSummarySerializer(serializers.Serializer):
    """
    Read-only response shape for GET /api/payments/bill/{bill_id}/summary/

    All fields are computed by the service layer.
    """
    bill_id        = serializers.CharField()
    bill_number    = serializers.CharField()
    bill_total     = serializers.CharField()
    total_paid     = serializers.CharField()
    total_refunded = serializers.CharField()
    remaining      = serializers.CharField()
    payment_status = serializers.CharField()
    payments       = serializers.ListField(child=serializers.DictField())


# =============================================================================
# Audit log serializer (read only)
# =============================================================================

class PaymentAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.SerializerMethodField()
    actor_name  = serializers.SerializerMethodField()

    class Meta:
        model  = PaymentAuditLog
        fields = [
            "id",
            "payment",
            "refund",
            "actor",
            "actor_email",
            "actor_name",
            "action",
            "old_status",
            "new_status",
            "amount",
            "reason",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_email(self, obj):
        return obj.actor.email if obj.actor else None

    def get_actor_name(self, obj):
        return obj.actor.full_name if obj.actor else None
