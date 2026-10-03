# =============================================================================
# RestaurantFlow — Billing Serializers
# Phase 8
#
# Two serializer types per resource:
#   READ  serializers — ModelSerializer, include denormalized fields,
#                       used for GET responses.
#   WRITE serializers — plain Serializer, validate input only,
#                       never accept computed financial totals from the client.
#
# Security principles:
#   - Never accept subtotal, tax_amount, grand_total from the client.
#   - Never accept discount_amount (computed) — only discount_type + value.
#   - The backend is the authoritative source for all financial values.
#   - All monetary string values in responses are 2dp Decimal strings.
# =============================================================================

import logging
from decimal import Decimal

from rest_framework import serializers

from billing.models import (
    Bill, BillItem, BillCorrectionRequest,
    BillStatus, DiscountType, CorrectionType, CorrectionStatus,
)

logger = logging.getLogger("billing")


# =============================================================================
# BillItem — Read
# =============================================================================

class BillItemSerializer(serializers.ModelSerializer):
    """Read serializer for BillItem — line items on a bill."""

    class Meta:
        model = BillItem
        fields = [
            "id",
            "order_item",
            "menu_item",
            "item_name_snapshot",
            "sku_snapshot",
            "quantity",
            "unit_price",
            "gross_amount",
            "discount_amount",
            "taxable_amount",
            "tax_rate",
            "tax_code",
            "tax_amount",
            "total_amount",
            "created_at",
        ]
        read_only_fields = fields


# =============================================================================
# Bill — Read (list view, minimal)
# =============================================================================

class BillListSerializer(serializers.ModelSerializer):
    """Lightweight read serializer for bill list view."""

    order_number    = serializers.SerializerMethodField()
    order_type      = serializers.SerializerMethodField()
    branch_name     = serializers.CharField(source="branch.name", read_only=True)
    restaurant_name = serializers.CharField(
        source="branch.restaurant.name", read_only=True
    )
    created_by_email = serializers.SerializerMethodField()
    created_by_name  = serializers.SerializerMethodField()
    finalized_by_email = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            "id",
            "bill_number",
            "order_number",
            "order_type",
            "branch",
            "branch_name",
            "restaurant_name",
            "status",
            "subtotal",
            "discount_amount",
            "tax_amount",
            "grand_total",
            "discount_type",
            "discount_value",
            "created_by",
            "created_by_email",
            "created_by_name",
            "finalized_by",
            "finalized_by_email",
            "finalized_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_order_number(self, obj):
        try:
            return obj.order.order_number
        except Exception:
            return None

    def get_order_type(self, obj):
        try:
            return obj.order.order_type
        except Exception:
            return None

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by_id else None

    def get_created_by_name(self, obj):
        if obj.created_by_id:
            return obj.created_by.full_name or obj.created_by.email
        return None

    def get_finalized_by_email(self, obj):
        return obj.finalized_by.email if obj.finalized_by_id else None


# =============================================================================
# Bill — Read (detail view, full)
# =============================================================================

class BillDetailSerializer(serializers.ModelSerializer):
    """Full read serializer for bill detail — includes all fields and nested items."""

    order_number      = serializers.SerializerMethodField()
    order_type        = serializers.SerializerMethodField()
    branch_name       = serializers.CharField(source="branch.name", read_only=True)
    restaurant_id     = serializers.UUIDField(
        source="branch.restaurant.id", read_only=True
    )
    restaurant_name   = serializers.CharField(
        source="branch.restaurant.name", read_only=True
    )
    organization_id   = serializers.UUIDField(
        source="branch.restaurant.organization.id", read_only=True
    )
    table_number      = serializers.SerializerMethodField()
    counter_code      = serializers.SerializerMethodField()
    counter_session   = serializers.SerializerMethodField()

    created_by_email  = serializers.SerializerMethodField()
    created_by_name   = serializers.SerializerMethodField()
    finalized_by_email = serializers.SerializerMethodField()
    finalized_by_name  = serializers.SerializerMethodField()
    cancelled_by_email = serializers.SerializerMethodField()

    items             = BillItemSerializer(many=True, read_only=True)
    correction_count  = serializers.SerializerMethodField()
    has_pending_correction = serializers.SerializerMethodField()

    class Meta:
        model = Bill
        fields = [
            "id",
            "bill_number",
            "order",
            "order_number",
            "order_type",
            "branch",
            "branch_name",
            "restaurant_id",
            "restaurant_name",
            "organization_id",
            "table_number",
            "counter_code",
            "counter_session",
            "status",
            "discount_type",
            "discount_value",
            "subtotal",
            "discount_amount",
            "taxable_amount",
            "tax_amount",
            "tax_breakdown",
            "rounding_amount",
            "grand_total",
            "notes",
            "created_by",
            "created_by_email",
            "created_by_name",
            "finalized_by",
            "finalized_by_email",
            "finalized_by_name",
            "finalized_at",
            "cancelled_by",
            "cancelled_by_email",
            "cancelled_at",
            "cancellation_reason",
            "correction_count",
            "has_pending_correction",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_order_number(self, obj):
        try:
            return obj.order.order_number
        except Exception:
            return None

    def get_order_type(self, obj):
        try:
            return obj.order.order_type
        except Exception:
            return None

    def get_table_number(self, obj):
        try:
            return obj.order.table.table_number if obj.order.table_id else None
        except Exception:
            return None

    def get_counter_code(self, obj):
        try:
            return obj.order.counter.code if obj.order.counter_id else None
        except Exception:
            return None

    def get_counter_session(self, obj):
        try:
            return str(obj.order.counter_session_id) if obj.order.counter_session_id else None
        except Exception:
            return None

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by_id else None

    def get_created_by_name(self, obj):
        if obj.created_by_id:
            return obj.created_by.full_name or obj.created_by.email
        return None

    def get_finalized_by_email(self, obj):
        return obj.finalized_by.email if obj.finalized_by_id else None

    def get_finalized_by_name(self, obj):
        if obj.finalized_by_id:
            return obj.finalized_by.full_name or obj.finalized_by.email
        return None

    def get_cancelled_by_email(self, obj):
        return obj.cancelled_by.email if obj.cancelled_by_id else None

    def get_correction_count(self, obj):
        return obj.correction_requests.count()

    def get_has_pending_correction(self, obj):
        from billing.models import CorrectionStatus
        return obj.correction_requests.filter(
            status=CorrectionStatus.PENDING
        ).exists()


# =============================================================================
# Bill — Write: Apply Discount
# =============================================================================

class ApplyDiscountSerializer(serializers.Serializer):
    """
    Input serializer for POST /bills/{id}/discount/

    Frontend sends:
        {
            "discount_type": "PERCENTAGE" | "FIXED_AMOUNT",
            "discount_value": "10.00"
        }

    Backend recalculates everything.
    Grand total is NEVER accepted from the frontend.
    """

    discount_type = serializers.ChoiceField(
        choices=DiscountType.choices,
        help_text="PERCENTAGE or FIXED_AMOUNT.",
    )
    discount_value = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        help_text=(
            "Discount value. "
            "For PERCENTAGE: 0–100 (e.g. 10.00 = 10%%). "
            "For FIXED_AMOUNT: non-negative amount (e.g. 50.00 = ₹50)."
        ),
    )

    def validate_discount_value(self, value):
        if value is None:
            raise serializers.ValidationError("discount_value is required.")
        if value < Decimal("0"):
            raise serializers.ValidationError(
                "discount_value must be greater than or equal to 0."
            )
        return value


# =============================================================================
# Bill — Write: Finalize
# =============================================================================

class FinalizeBillSerializer(serializers.Serializer):
    """
    Input serializer for POST /bills/{id}/finalize/

    No body required — finalization is triggered by the action itself.
    Notes field is optional.
    """
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=500,
        help_text="Optional notes to attach to the finalized bill.",
    )


# =============================================================================
# Bill — Write: Cancel
# =============================================================================

class CancelBillSerializer(serializers.Serializer):
    """Input serializer for POST /bills/{id}/cancel/"""

    reason = serializers.CharField(
        min_length=5,
        max_length=500,
        help_text="Required reason for cancellation.",
    )


# =============================================================================
# Bill — Write: Void
# =============================================================================

class VoidBillSerializer(serializers.Serializer):
    """Input serializer for POST /bills/{id}/void/"""

    reason = serializers.CharField(
        min_length=5,
        max_length=500,
        help_text="Required reason for voiding the bill.",
    )


# =============================================================================
# BillCorrectionRequest — Read
# =============================================================================

class BillCorrectionRequestSerializer(serializers.ModelSerializer):
    """Read serializer for BillCorrectionRequest."""

    bill_number       = serializers.CharField(source="bill.bill_number", read_only=True)
    requested_by_email = serializers.SerializerMethodField()
    requested_by_name  = serializers.SerializerMethodField()
    reviewed_by_email  = serializers.SerializerMethodField()
    reviewed_by_name   = serializers.SerializerMethodField()

    class Meta:
        model = BillCorrectionRequest
        fields = [
            "id",
            "bill",
            "bill_number",
            "correction_type",
            "reason",
            "requested_data",
            "status",
            "requested_by",
            "requested_by_email",
            "requested_by_name",
            "reviewed_by",
            "reviewed_by_email",
            "reviewed_by_name",
            "reviewed_at",
            "review_note",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_requested_by_email(self, obj):
        return obj.requested_by.email if obj.requested_by_id else None

    def get_requested_by_name(self, obj):
        if obj.requested_by_id:
            return obj.requested_by.full_name or obj.requested_by.email
        return None

    def get_reviewed_by_email(self, obj):
        return obj.reviewed_by.email if obj.reviewed_by_id else None

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by_id:
            return obj.reviewed_by.full_name or obj.reviewed_by.email
        return None


# =============================================================================
# BillCorrectionRequest — Write: Create
# =============================================================================

class CreateCorrectionRequestSerializer(serializers.Serializer):
    """
    Input serializer for POST /bill-corrections/

    The bill ID is taken from the URL (not the body) in the view.
    Body provides the correction details.
    """

    correction_type = serializers.ChoiceField(
        choices=CorrectionType.choices,
        help_text="Type of correction being requested.",
    )
    reason = serializers.CharField(
        min_length=10,
        max_length=1000,
        help_text=(
            "Detailed reason for the correction request. "
            "Must be at least 10 characters."
        ),
    )

    def validate_reason(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Reason cannot be blank.")
        return value.strip()


# =============================================================================
# BillCorrectionRequest — Write: Review (Approve / Reject)
# =============================================================================

class ReviewCorrectionSerializer(serializers.Serializer):
    """Input serializer for approve/reject correction endpoints."""

    review_note = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Reviewer's note explaining the decision.",
    )


# =============================================================================
# Bill Calculate Preview
# =============================================================================

class BillCalculationSerializer(serializers.Serializer):
    """
    Read serializer for the calculate endpoint response.

    Used for GET /bills/{id}/calculate/ preview.
    All values are strings to avoid floating-point issues in JSON.
    """
    subtotal        = serializers.CharField(read_only=True)
    discount_amount = serializers.CharField(read_only=True)
    taxable_amount  = serializers.CharField(read_only=True)
    tax_amount      = serializers.CharField(read_only=True)
    tax_breakdown   = serializers.DictField(child=serializers.CharField(), read_only=True)
    rounding_amount = serializers.CharField(read_only=True)
    grand_total     = serializers.CharField(read_only=True)
