# =============================================================================
# RestaurantFlow — Marketing Serializers
# Phase 18
#
# Never expose internal fields unnecessarily.
# Read serializers are separate from write serializers.
# =============================================================================

from decimal import Decimal
from rest_framework import serializers
from marketing.models import (
    MarketingCampaign, CampaignApproval, CampaignAudience,
    CampaignAudienceMember, Promotion, PromotionRule, PromotionUsage,
    CampaignChannel, CampaignMessage, CampaignDelivery,
    CampaignConversion, CampaignEvent, MarketingSettings,
    MarketingContactPolicy,
)
from marketing.constants import (
    CAMPAIGN_TYPE_CHOICES, CAMPAIGN_STATUS_CHOICES,
    AUDIENCE_TYPE_CHOICES, PROMOTION_TYPE_CHOICES,
    DISCOUNT_TYPE_CHOICES, RULE_TYPE_CHOICES,
    CHANNEL_CHOICES, CONVERSION_TYPE_CHOICES,
)
from marketing.validators import (
    validate_campaign_code, validate_promotion_code,
    validate_message_body, validate_promotion_type_fields,
)


# ---------------------------------------------------------------------------
# Campaign Serializers
# ---------------------------------------------------------------------------

class CampaignListSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True, default="")
    branch_name = serializers.CharField(source="branch.name", read_only=True, default="")

    class Meta:
        model = MarketingCampaign
        fields = [
            "id", "name", "code", "campaign_type", "status",
            "start_at", "end_at", "audience_type",
            "restaurant", "restaurant_name", "branch", "branch_name",
            "created_by_email", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CampaignDetailSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    approved_by_email = serializers.EmailField(source="approved_by.email", read_only=True, default="")
    cancelled_by_email = serializers.EmailField(source="cancelled_by.email", read_only=True, default="")
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True, default="")
    branch_name = serializers.CharField(source="branch.name", read_only=True, default="")
    company_name = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = MarketingCampaign
        fields = [
            "id", "name", "code", "description", "campaign_type", "status",
            "start_at", "end_at", "audience_type",
            "company", "company_name",
            "restaurant", "restaurant_name",
            "branch", "branch_name",
            "created_by_email", "approved_by_email", "approved_at",
            "cancelled_by_email", "cancelled_at", "cancellation_reason",
            "metadata", "created_at", "updated_at",
        ]
        read_only_fields = fields


class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    code = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    campaign_type = serializers.ChoiceField(choices=CAMPAIGN_TYPE_CHOICES)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)
    audience_type = serializers.CharField(required=False, allow_blank=True, default="")
    restaurant = serializers.UUIDField(required=False, allow_null=True)
    branch = serializers.UUIDField(required=False, allow_null=True)
    metadata = serializers.JSONField(required=False, default=dict)

    def validate_code(self, value):
        return validate_campaign_code(value)

    def validate(self, attrs):
        start_at = attrs.get("start_at")
        end_at = attrs.get("end_at")
        if start_at and end_at and start_at >= end_at:
            raise serializers.ValidationError({"end_at": "end_at must be after start_at."})
        return attrs


class CampaignUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    campaign_type = serializers.ChoiceField(choices=CAMPAIGN_TYPE_CHOICES, required=False)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)
    audience_type = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)

    def validate(self, attrs):
        start_at = attrs.get("start_at")
        end_at = attrs.get("end_at")
        if start_at and end_at and start_at >= end_at:
            raise serializers.ValidationError({"end_at": "end_at must be after start_at."})
        return attrs


# ---------------------------------------------------------------------------
# Campaign Approval Serializers
# ---------------------------------------------------------------------------

class CampaignApprovalSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)
    reviewed_by_email = serializers.EmailField(source="reviewed_by.email", read_only=True, default="")
    campaign_code = serializers.CharField(source="campaign.code", read_only=True)

    class Meta:
        model = CampaignApproval
        fields = [
            "id", "campaign", "campaign_code",
            "requested_by_email", "reviewed_by_email",
            "status", "review_note",
            "requested_at", "reviewed_at", "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Audience Serializers
# ---------------------------------------------------------------------------

class CampaignAudienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignAudience
        fields = [
            "id", "campaign", "audience_type", "criteria",
            "estimated_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "campaign", "estimated_count", "created_at", "updated_at"]


class CampaignAudienceCreateSerializer(serializers.Serializer):
    audience_type = serializers.ChoiceField(choices=AUDIENCE_TYPE_CHOICES)
    criteria = serializers.JSONField(required=False, default=dict)


class CampaignAudienceMemberSerializer(serializers.ModelSerializer):
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True)
    customer_name = serializers.CharField(source="customer.effective_display_name", read_only=True)

    class Meta:
        model = CampaignAudienceMember
        fields = [
            "id", "campaign", "customer", "customer_number", "customer_name",
            "status", "added_at", "removed_at", "metadata",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Promotion Serializers
# ---------------------------------------------------------------------------

class PromotionListSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True, default="")

    class Meta:
        model = Promotion
        fields = [
            "id", "name", "code", "promotion_type", "discount_type",
            "discount_value", "start_at", "end_at",
            "usage_limit", "usage_limit_per_customer", "current_usage_count",
            "is_active", "restaurant", "restaurant_name",
            "created_by_email", "created_at",
        ]
        read_only_fields = fields


class PromotionDetailSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True, default="")
    branch_name = serializers.CharField(source="branch.name", read_only=True, default="")
    free_item_name = serializers.CharField(source="free_item.name", read_only=True, default="")
    rules = serializers.SerializerMethodField()

    def get_rules(self, obj):
        return PromotionRuleSerializer(
            obj.rules.filter(is_active=True).order_by("priority"), many=True
        ).data

    class Meta:
        model = Promotion
        fields = [
            "id", "name", "code", "description",
            "promotion_type", "discount_type", "discount_value",
            "max_discount_amount", "minimum_order_amount", "minimum_quantity",
            "free_item", "free_item_name",
            "buy_quantity", "get_quantity",
            "loyalty_bonus_multiplier",
            "start_at", "end_at",
            "usage_limit", "usage_limit_per_customer", "current_usage_count",
            "is_active",
            "company", "restaurant", "restaurant_name", "branch", "branch_name",
            "created_by_email", "created_at", "updated_at",
            "rules",
        ]
        read_only_fields = fields


class PromotionCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    code = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")
    promotion_type = serializers.ChoiceField(choices=PROMOTION_TYPE_CHOICES)
    discount_type = serializers.ChoiceField(choices=DISCOUNT_TYPE_CHOICES, required=False, allow_null=True)
    discount_value = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    max_discount_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    minimum_order_amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    minimum_quantity = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    free_item_id = serializers.UUIDField(required=False, allow_null=True)
    buy_quantity = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    get_quantity = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    loyalty_bonus_multiplier = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)
    usage_limit = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    usage_limit_per_customer = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    restaurant = serializers.UUIDField(required=False, allow_null=True)
    branch = serializers.UUIDField(required=False, allow_null=True)

    def validate_code(self, value):
        return validate_promotion_code(value)

    def validate(self, attrs):
        validate_promotion_type_fields(attrs)
        start_at = attrs.get("start_at")
        end_at = attrs.get("end_at")
        if start_at and end_at and start_at >= end_at:
            raise serializers.ValidationError({"end_at": "end_at must be after start_at."})
        return attrs


class PromotionUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    discount_type = serializers.ChoiceField(choices=DISCOUNT_TYPE_CHOICES, required=False, allow_null=True)
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    max_discount_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    minimum_order_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    minimum_quantity = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    start_at = serializers.DateTimeField(required=False, allow_null=True)
    end_at = serializers.DateTimeField(required=False, allow_null=True)
    usage_limit = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    usage_limit_per_customer = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    loyalty_bonus_multiplier = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    buy_quantity = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    get_quantity = serializers.IntegerField(required=False, allow_null=True, min_value=1)

    def validate_code(self, value):
        return validate_promotion_code(value) if value else ""


# ---------------------------------------------------------------------------
# Promotion Rule Serializer
# ---------------------------------------------------------------------------

class PromotionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromotionRule
        fields = [
            "id", "promotion", "rule_type", "configuration",
            "priority", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "promotion", "created_at", "updated_at"]


class PromotionRuleCreateSerializer(serializers.Serializer):
    rule_type = serializers.ChoiceField(choices=RULE_TYPE_CHOICES)
    configuration = serializers.JSONField(required=False, default=dict)
    priority = serializers.IntegerField(required=False, default=10, min_value=1)
    is_active = serializers.BooleanField(required=False, default=True)


# ---------------------------------------------------------------------------
# Promotion Usage Serializer
# ---------------------------------------------------------------------------

class PromotionUsageSerializer(serializers.ModelSerializer):
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True, default="")
    promotion_name = serializers.CharField(source="promotion.name", read_only=True)

    class Meta:
        model = PromotionUsage
        fields = [
            "id", "promotion", "promotion_name",
            "customer", "customer_number",
            "order", "bill",
            "discount_amount", "used_at", "status",
            "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Promotion Validation Serializer
# ---------------------------------------------------------------------------

class PromotionValidateRequestSerializer(serializers.Serializer):
    promotion_code = serializers.CharField(max_length=50, required=False, allow_blank=True)
    promotion_id = serializers.UUIDField(required=False, allow_null=True)
    customer_id = serializers.UUIDField(required=False, allow_null=True)
    order_id = serializers.UUIDField(required=False, allow_null=True)
    branch_id = serializers.UUIDField(required=False, allow_null=True)
    order_subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, default=Decimal("0.00")
    )

    def validate(self, attrs):
        if not attrs.get("promotion_code") and not attrs.get("promotion_id"):
            raise serializers.ValidationError(
                "Either promotion_code or promotion_id is required."
            )
        return attrs


class PromotionValidateResponseSerializer(serializers.Serializer):
    eligible = serializers.BooleanField()
    promotion_id = serializers.CharField(allow_null=True)
    promotion_name = serializers.CharField()
    promotion_type = serializers.CharField()
    estimated_discount = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_type = serializers.CharField(allow_null=True)
    discount_value = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    reason = serializers.CharField()


# ---------------------------------------------------------------------------
# Channel / Message Serializers
# ---------------------------------------------------------------------------

class CampaignChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignChannel
        fields = [
            "id", "campaign", "channel", "enabled",
            "template_id", "scheduled_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "campaign", "created_at", "updated_at"]


class CampaignMessageSerializer(serializers.ModelSerializer):
    def validate_body(self, value):
        return validate_message_body(value)

    class Meta:
        model = CampaignMessage
        fields = [
            "id", "campaign", "channel", "subject", "body",
            "template_data", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "campaign", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# Delivery / Conversion / Event Serializers
# ---------------------------------------------------------------------------

class CampaignDeliverySerializer(serializers.ModelSerializer):
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True)
    campaign_code = serializers.CharField(source="campaign.code", read_only=True)

    class Meta:
        model = CampaignDelivery
        fields = [
            "id", "campaign", "campaign_code",
            "customer", "customer_number",
            "channel", "notification_id", "status",
            "sent_at", "delivered_at", "failed_at", "failure_reason",
            "created_at",
        ]
        read_only_fields = fields


class CampaignConversionSerializer(serializers.ModelSerializer):
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True)
    campaign_code = serializers.CharField(source="campaign.code", read_only=True)

    class Meta:
        model = CampaignConversion
        fields = [
            "id", "campaign", "campaign_code",
            "customer", "customer_number",
            "order", "promotion",
            "conversion_type", "conversion_value", "converted_at",
        ]
        read_only_fields = fields


class CampaignEventSerializer(serializers.ModelSerializer):
    customer_number = serializers.CharField(source="customer.customer_number", read_only=True, default="")

    class Meta:
        model = CampaignEvent
        fields = [
            "id", "campaign", "customer", "customer_number",
            "event_type", "source_type", "source_id",
            "metadata", "created_at",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Settings Serializers
# ---------------------------------------------------------------------------

class MarketingSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingSettings
        fields = [
            "id", "restaurant",
            "default_currency", "max_discount_without_approval",
            "default_campaign_timezone",
            "frequency_limit_enabled",
            "default_daily_contact_limit", "default_weekly_contact_limit",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "restaurant", "created_at", "updated_at"]
