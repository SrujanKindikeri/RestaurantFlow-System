# =============================================================================
# RestaurantFlow — CRM Serializers
# Phase 17
#
# Separate serializers for list / detail / create / update / search
# to avoid over-exposing PII and keep response shapes clean.
#
# PII masking:
#   - phone / email are masked in list/search responses
#   - Full PII only in CustomerDetailSerializer (requires customer.contact.view)
# =============================================================================

from rest_framework import serializers

from crm.models import (
    Customer, CustomerPreference, CustomerVisit,
    CustomerTag, CustomerTagAssignment,
    CustomerSegment, CustomerSegmentAssignment,
    LoyaltyProgram, LoyaltyAccount, LoyaltyTransaction,
    LoyaltyReward, RewardRedemption,
    CustomerFeedback, FeedbackModeration,
    CustomerConsent, CustomerConsentHistory,
    CustomerMergeRequest,
)


# =============================================================================
# Customer serializers
# =============================================================================

class CustomerListSerializer(serializers.ModelSerializer):
    """Minimal fields for list views — no full PII."""
    masked_phone = serializers.SerializerMethodField()
    masked_email = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id", "customer_number", "first_name", "last_name", "display_name",
            "masked_phone", "masked_email",
            "is_active", "is_blocked",
            "total_orders", "total_visits", "lifetime_spend",
            "last_visit_at", "last_order_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_masked_phone(self, obj):
        return obj.masked_phone

    def get_masked_email(self, obj):
        return obj.masked_email

    def get_display_name(self, obj):
        return obj.effective_display_name


class CustomerSearchSerializer(serializers.ModelSerializer):
    """Minimal response for POS search — masked PII."""
    masked_phone = serializers.SerializerMethodField()
    masked_email = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    loyalty_points = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id", "customer_number", "display_name",
            "masked_phone", "masked_email",
            "loyalty_points", "last_visit_at",
        ]
        read_only_fields = fields

    def get_masked_phone(self, obj):
        return obj.masked_phone

    def get_masked_email(self, obj):
        return obj.masked_email

    def get_display_name(self, obj):
        return obj.effective_display_name

    def get_loyalty_points(self, obj):
        # Sum all active loyalty accounts
        total = 0
        for acc in obj.loyalty_accounts.all():
            total += acc.points_balance
        return total


class CustomerDetailSerializer(serializers.ModelSerializer):
    """Full customer details — full PII, only for authorized users."""
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = [
            "id", "customer_number",
            "first_name", "last_name", "display_name",
            "phone", "email", "date_of_birth", "gender",
            "address", "city", "state", "postal_code", "country",
            "preferred_language", "notes",
            "is_active", "is_blocked", "blocked_reason",
            "total_orders", "total_visits", "lifetime_spend",
            "first_order_at", "last_order_at", "last_visit_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "customer_number",
            "total_orders", "total_visits", "lifetime_spend",
            "first_order_at", "last_order_at", "last_visit_at",
            "created_at", "updated_at",
        ]

    def get_display_name(self, obj):
        return obj.effective_display_name


class CustomerCreateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, default="")
    phone = serializers.CharField(max_length=30, required=False, default="")
    email = serializers.EmailField(required=False, default="")
    date_of_birth = serializers.DateField(required=False, allow_null=True, default=None)
    gender = serializers.ChoiceField(
        choices=["M", "F", "O"], required=False, default=""
    )
    address = serializers.CharField(required=False, default="")
    city = serializers.CharField(max_length=100, required=False, default="")
    state = serializers.CharField(max_length=100, required=False, default="")
    postal_code = serializers.CharField(max_length=20, required=False, default="")
    country = serializers.CharField(max_length=100, required=False, default="India")
    notes = serializers.CharField(required=False, default="")
    preferred_language = serializers.CharField(max_length=10, required=False, default="")
    restaurant_id = serializers.UUIDField()


class CustomerUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    phone = serializers.CharField(max_length=30, required=False)
    email = serializers.EmailField(required=False)
    date_of_birth = serializers.DateField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=["M", "F", "O"], required=False)
    address = serializers.CharField(required=False)
    city = serializers.CharField(max_length=100, required=False)
    state = serializers.CharField(max_length=100, required=False)
    postal_code = serializers.CharField(max_length=20, required=False)
    country = serializers.CharField(max_length=100, required=False)
    notes = serializers.CharField(required=False)
    preferred_language = serializers.CharField(max_length=10, required=False)
    display_name = serializers.CharField(max_length=200, required=False)


class CustomerBlockSerializer(serializers.Serializer):
    blocked_reason = serializers.CharField()
    is_blocked = serializers.BooleanField()


# =============================================================================
# Visit serializers
# =============================================================================

class CustomerVisitSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = CustomerVisit
        fields = [
            "id", "visit_number", "branch_name",
            "visit_type", "status",
            "visit_started_at", "visit_completed_at",
            "guest_count", "created_at",
        ]
        read_only_fields = fields


# =============================================================================
# Preference serializers
# =============================================================================

class CustomerPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerPreference
        fields = [
            "id", "preferred_order_type", "preferred_branch",
            "favorite_category", "favorite_menu_item",
            "dietary_preference", "allergy_note", "special_request_note",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# Tag serializers
# =============================================================================

class CustomerTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerTag
        fields = ["id", "name", "code", "description", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class CustomerTagAssignmentSerializer(serializers.ModelSerializer):
    tag = CustomerTagSerializer(read_only=True)
    tag_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = CustomerTagAssignment
        fields = [
            "id", "tag", "tag_id", "assigned_at", "expires_at", "is_active"
        ]
        read_only_fields = ["id", "assigned_at", "is_active"]


# =============================================================================
# Segment serializers
# =============================================================================

class CustomerSegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerSegment
        fields = [
            "id", "name", "code", "description", "criteria",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class CustomerSegmentAssignmentSerializer(serializers.ModelSerializer):
    segment = CustomerSegmentSerializer(read_only=True)

    class Meta:
        model = CustomerSegmentAssignment
        fields = [
            "id", "segment", "assigned_at", "expires_at", "is_active",
            "evaluation_snapshot",
        ]
        read_only_fields = fields


# =============================================================================
# Loyalty serializers
# =============================================================================

class LoyaltyProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyProgram
        fields = [
            "id", "name", "description", "is_active",
            "points_per_currency_unit", "minimum_redemption_points",
            "point_expiry_days", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class LoyaltyAccountSerializer(serializers.ModelSerializer):
    program_name = serializers.CharField(source="loyalty_program.name", read_only=True)

    class Meta:
        model = LoyaltyAccount
        fields = [
            "id", "program_name",
            "points_balance", "lifetime_points_earned",
            "lifetime_points_redeemed", "created_at", "updated_at",
        ]
        read_only_fields = fields


class LoyaltyTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyTransaction
        fields = [
            "id", "transaction_type", "points",
            "balance_before", "balance_after",
            "reference_type", "reference_id",
            "reason", "created_at",
        ]
        read_only_fields = fields


class LoyaltyRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyReward
        fields = [
            "id", "name", "description",
            "reward_type", "points_required",
            "reward_value", "discount_type", "discount_value",
            "max_discount_amount",
            "is_active", "valid_from", "valid_until",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RewardRedemptionSerializer(serializers.ModelSerializer):
    reward_name = serializers.CharField(source="reward.name", read_only=True)

    class Meta:
        model = RewardRedemption
        fields = [
            "id", "reward_name", "points_used",
            "status", "reference_code",
            "redeemed_at", "expires_at", "created_at",
        ]
        read_only_fields = fields


# =============================================================================
# Feedback serializers
# =============================================================================

class CustomerFeedbackSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True, default="")

    class Meta:
        model = CustomerFeedback
        fields = [
            "id", "branch_name",
            "rating", "service_rating", "food_rating", "ambience_rating",
            "comment", "status", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "created_at", "updated_at"]


class CustomerFeedbackCreateSerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    order_id = serializers.UUIDField(required=False, allow_null=True)
    rating = serializers.IntegerField(min_value=1, max_value=5)
    service_rating = serializers.IntegerField(
        min_value=1, max_value=5, required=False, allow_null=True
    )
    food_rating = serializers.IntegerField(
        min_value=1, max_value=5, required=False, allow_null=True
    )
    ambience_rating = serializers.IntegerField(
        min_value=1, max_value=5, required=False, allow_null=True
    )
    comment = serializers.CharField(required=False, default="")


class FeedbackModerationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedbackModeration
        fields = [
            "id", "status", "moderation_note",
            "reviewed_at", "central_issue_id", "created_at",
        ]
        read_only_fields = ["id", "reviewed_at", "created_at"]


class FeedbackModerationActionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["APPROVED", "HIDDEN", "REJECTED"])
    moderation_note = serializers.CharField(required=False, default="")
    create_central_issue = serializers.BooleanField(default=False)


# =============================================================================
# Consent serializers
# =============================================================================

class CustomerConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerConsent
        fields = [
            "id", "consent_type", "status", "source",
            "granted_at", "revoked_at", "updated_at",
        ]
        read_only_fields = ["id", "granted_at", "revoked_at", "updated_at"]


class CustomerConsentUpdateSerializer(serializers.Serializer):
    consent_type = serializers.CharField()
    status = serializers.ChoiceField(choices=["GRANTED", "REVOKED"])
    source = serializers.ChoiceField(
        choices=["CUSTOMER", "STAFF", "ADMIN", "IMPORT", "SYSTEM"],
        default="STAFF",
    )


class CustomerConsentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerConsentHistory
        fields = [
            "id", "consent_type", "previous_status", "new_status",
            "source", "changed_at",
        ]
        read_only_fields = fields


# =============================================================================
# Merge serializers
# =============================================================================

class CustomerMergeRequestSerializer(serializers.ModelSerializer):
    source_customer_number = serializers.CharField(
        source="source_customer.customer_number", read_only=True
    )
    target_customer_number = serializers.CharField(
        source="target_customer.customer_number", read_only=True
    )

    class Meta:
        model = CustomerMergeRequest
        fields = [
            "id",
            "source_customer", "source_customer_number",
            "target_customer", "target_customer_number",
            "status", "reason", "notes",
            "created_at", "approved_at", "rejected_at",
        ]
        read_only_fields = [
            "id", "status", "created_at", "approved_at", "rejected_at",
            "source_customer_number", "target_customer_number",
        ]


class MergeRequestCreateSerializer(serializers.Serializer):
    source_customer_id = serializers.UUIDField()
    target_customer_id = serializers.UUIDField()
    reason = serializers.CharField()


# =============================================================================
# Customer order history serializer
# =============================================================================

class CustomerOrderHistorySerializer(serializers.Serializer):
    """Read-only summary of an order for CRM view — no financial recalculation."""
    order_id = serializers.UUIDField(source="id")
    order_number = serializers.CharField()
    order_type = serializers.CharField()
    branch_name = serializers.CharField(source="branch.name")
    order_date = serializers.DateTimeField(source="created_at")
    status = serializers.CharField()
    item_count = serializers.IntegerField()
    bill_number = serializers.SerializerMethodField()
    bill_total = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    def get_bill_number(self, obj):
        try:
            return obj.bill.bill_number
        except Exception:
            return None

    def get_bill_total(self, obj):
        try:
            return str(obj.bill.grand_total)
        except Exception:
            return None

    def get_payment_status(self, obj):
        try:
            # Return latest payment status
            payment = obj.bill.payments.order_by("-created_at").first()
            return payment.status if payment else None
        except Exception:
            return None


class CustomerSpendingSerializer(serializers.Serializer):
    """Read-only spending entry per finalized bill."""
    bill_id = serializers.UUIDField(source="id")
    bill_number = serializers.CharField()
    date = serializers.DateTimeField(source="created_at")
    branch_name = serializers.CharField(source="branch.name")
    gross_amount = serializers.DecimalField(source="subtotal", max_digits=12, decimal_places=2)
    discount = serializers.DecimalField(source="discount_amount", max_digits=12, decimal_places=2)
    tax = serializers.DecimalField(source="tax_amount", max_digits=12, decimal_places=2)
    grand_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    refund_amount = serializers.SerializerMethodField()
    net_spend = serializers.SerializerMethodField()

    def get_refund_amount(self, obj):
        try:
            from django.db.models import Sum
            total = (
                obj.order.bill.payments.aggregate(
                    r=Sum("refunds__amount")
                )["r"]
                or 0
            )
            return str(total)
        except Exception:
            return "0.00"

    def get_net_spend(self, obj):
        try:
            refund = float(self.get_refund_amount(obj) or 0)
            return str(float(obj.grand_total) - refund)
        except Exception:
            return str(obj.grand_total)
