# =============================================================================
# RestaurantFlow — Marketing Models
# Phase 18: Marketing, Promotions & Campaign Management
#
# Models:
#   MarketingCampaign          — campaign definition and lifecycle
#   CampaignApproval           — approval workflow record
#   CampaignAudience           — audience definition per campaign
#   CampaignAudienceMember     — resolved customer membership snapshot
#   Promotion                  — promotion/offer definition
#   PromotionRule              — eligibility rules for a promotion
#   PromotionUsage             — per-customer usage ledger
#   CampaignChannel            — channel configuration per campaign
#   CampaignMessage            — message/template per channel
#   CampaignDelivery           — per-customer per-channel delivery record
#   CampaignConversion         — attribution/conversion record
#   CampaignEvent              — append-only event timeline
#   MarketingSettings          — restaurant-level marketing configuration
#   MarketingContactPolicy     — frequency/cooldown policy per channel
#   MarketingAuditLog          — append-only audit trail
#
# Design principles:
#   - UUID primary keys on all business models.
#   - TimestampedModel base for created_at / updated_at.
#   - PROTECT foreign keys — no accidental cascade deletion.
#   - All monetary values use DecimalField — never float.
#   - Marketing does NOT own: Customer, Order, Bill, Payment, Notification delivery.
#   - Audit logs are immutable (save() guard).
#   - Company / restaurant / branch scope enforced in service layer.
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

from core.models import TimestampedModel
from marketing.constants import (
    CAMPAIGN_TYPE_CHOICES, CAMPAIGN_DRAFT,
    CAMPAIGN_STATUS_CHOICES,
    APPROVAL_STATUS_CHOICES, APPROVAL_PENDING,
    AUDIENCE_TYPE_CHOICES,
    MEMBER_STATUS_CHOICES, MEMBER_ELIGIBLE,
    PROMOTION_TYPE_CHOICES,
    DISCOUNT_TYPE_CHOICES,
    RULE_TYPE_CHOICES,
    USAGE_STATUS_CHOICES, USAGE_RESERVED,
    CHANNEL_CHOICES,
    DELIVERY_STATUS_CHOICES, DELIVERY_PENDING,
    CONVERSION_TYPE_CHOICES,
    EVENT_TYPE_CHOICES,
    AUDIT_EVENT_CHOICES,
)

logger = logging.getLogger("marketing")


# =============================================================================
# MarketingCampaign
# =============================================================================

class MarketingCampaign(TimestampedModel):
    """
    Core marketing campaign definition.

    A campaign orchestrates WHO receives WHAT message WHEN, via WHICH channels,
    and what promotion (if any) is associated.

    Marketing does NOT own: customer data, orders, bills, payments, notifications.
    It only defines the campaign intent and tracks delivery/conversion.

    company-level campaigns: restaurant = NULL (still scope-validated in service).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Scope
    # -------------------------------------------------------------------------
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="marketing_campaigns",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketing_campaigns",
        db_index=True,
        help_text="Null for company-wide campaigns.",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketing_campaigns",
        db_index=True,
        help_text="Null for restaurant-wide or company-wide campaigns.",
    )

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Unique campaign code within company/restaurant scope.",
    )
    description = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Type & status
    # -------------------------------------------------------------------------
    campaign_type = models.CharField(
        max_length=30,
        choices=CAMPAIGN_TYPE_CHOICES,
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=CAMPAIGN_STATUS_CHOICES,
        default=CAMPAIGN_DRAFT,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Schedule
    # -------------------------------------------------------------------------
    start_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the campaign should start delivering.",
    )
    end_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When the campaign should stop.",
    )

    # -------------------------------------------------------------------------
    # Audience
    # -------------------------------------------------------------------------
    audience_type = models.CharField(
        max_length=30,
        choices=[
            ("ALL_CUSTOMERS", "All Customers"),
            ("SEGMENT", "Segment"),
            ("TAG", "Tag"),
            ("CUSTOM", "Custom Filter"),
        ],
        blank=True,
    )

    # -------------------------------------------------------------------------
    # Lifecycle actors
    # -------------------------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="marketing_campaigns_created",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketing_campaigns_approved",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketing_campaigns_cancelled",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary extra data for the campaign.",
    )

    class Meta:
        verbose_name = "Marketing Campaign"
        verbose_name_plural = "Marketing Campaigns"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "restaurant", "code"],
                name="unique_campaign_code_per_restaurant",
                condition=models.Q(restaurant__isnull=False),
            ),
            models.UniqueConstraint(
                fields=["company", "code"],
                name="unique_campaign_code_per_company",
                condition=models.Q(restaurant__isnull=True),
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["company", "campaign_type"]),
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "campaign_type"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["status", "start_at"]),
            models.Index(fields=["status", "end_at"]),
            models.Index(fields=["company", "start_at", "end_at"]),
            # Phase 22 performance indexes
            models.Index(
                fields=["restaurant", "status", "start_at"],
                name="mktg_camp_rest_stat_start_idx",
            ),
            models.Index(
                fields=["restaurant", "status", "end_at"],
                name="mktg_camp_rest_stat_end_idx",
            ),
        ]

    def __str__(self):
        return f"{self.code} — {self.name} [{self.status}]"

    @property
    def is_active(self) -> bool:
        return self.status in ("RUNNING", "SCHEDULED")


# =============================================================================
# CampaignApproval
# =============================================================================

class CampaignApproval(TimestampedModel):
    """
    Records the approval workflow for a campaign.

    A campaign creator must NOT self-approve unless explicitly allowed.
    Only users with marketing.campaign.approve permission can approve.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.PROTECT,
        related_name="approvals",
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="campaign_approvals_requested",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="campaign_approvals_reviewed",
    )
    status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_PENDING,
        db_index=True,
    )
    review_note = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Campaign Approval"
        verbose_name_plural = "Campaign Approvals"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["status", "requested_at"]),
        ]

    def __str__(self):
        return f"Approval for {self.campaign.code} [{self.status}]"


# =============================================================================
# CampaignAudience
# =============================================================================

class CampaignAudience(TimestampedModel):
    """
    Audience targeting definition for a campaign.

    The criteria JSON defines HOW to resolve the audience.
    Actual resolved members are in CampaignAudienceMember.

    Examples:
        {"segment": "VIP"}
        {"tag": "FREQUENT"}
        {"days_since_last_order": 60}
        {"segment_id": "<uuid>"}
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.PROTECT,
        related_name="audiences",
        db_index=True,
    )
    audience_type = models.CharField(
        max_length=30,
        choices=AUDIENCE_TYPE_CHOICES,
        db_index=True,
    )
    criteria = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Targeting criteria as JSON. "
            'Examples: {"segment": "VIP"}, {"tag": "FREQUENT"}, '
            '{"days_since_last_order": 60}, {"segment_id": "<uuid>"}'
        ),
    )
    estimated_count = models.PositiveIntegerField(
        default=0,
        help_text="Estimated number of customers matching this audience.",
    )

    class Meta:
        verbose_name = "Campaign Audience"
        verbose_name_plural = "Campaign Audiences"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign"]),
            models.Index(fields=["audience_type"]),
        ]

    def __str__(self):
        return f"Audience [{self.audience_type}] for {self.campaign.code}"


# =============================================================================
# CampaignAudienceMember
# =============================================================================

class CampaignAudienceMember(TimestampedModel):
    """
    Resolved audience membership snapshot for a specific campaign + customer.

    Generated asynchronously for large campaigns.
    Status tracks the customer's journey through the campaign funnel.

    Unique constraint: one row per campaign/customer.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.PROTECT,
        related_name="audience_members",
        db_index=True,
    )
    customer = models.ForeignKey(
        "crm.Customer",
        on_delete=models.PROTECT,
        related_name="campaign_memberships",
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=MEMBER_STATUS_CHOICES,
        default=MEMBER_ELIGIBLE,
        db_index=True,
    )
    added_at = models.DateTimeField(auto_now_add=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Exclusion reason, consent status, frequency flag, etc.",
    )

    class Meta:
        verbose_name = "Campaign Audience Member"
        verbose_name_plural = "Campaign Audience Members"
        ordering = ["-added_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "customer"],
                name="unique_campaign_audience_member",
            ),
        ]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["campaign", "customer"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["campaign", "status", "added_at"]),
        ]

    def __str__(self):
        return f"{self.customer.customer_number} in {self.campaign.code} [{self.status}]"


# =============================================================================
# Promotion
# =============================================================================

class Promotion(TimestampedModel):
    """
    Promotion / offer definition.

    This model DEFINES the promotion. The billing system remains responsible
    for the actual bill discount calculation. Marketing never modifies
    Bill.grand_total directly.

    The promotion code (if set) is case-insensitive and scope-aware.
    Usage tracking is in PromotionUsage.

    Concurrency:
        current_usage_count is incremented via select_for_update() in service.
        Never update this directly.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Scope
    # -------------------------------------------------------------------------
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="promotions",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promotions",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promotions",
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    name = models.CharField(max_length=200)
    code = models.CharField(
        max_length=50,
        db_index=True,
        blank=True,
        help_text=(
            "Optional promo code (case-insensitive, normalized to uppercase). "
            "Examples: WELCOME10, SAVE200, WEEKEND20."
        ),
    )
    description = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Type
    # -------------------------------------------------------------------------
    promotion_type = models.CharField(
        max_length=30,
        choices=PROMOTION_TYPE_CHOICES,
        db_index=True,
    )
    discount_type = models.CharField(
        max_length=20,
        choices=DISCOUNT_TYPE_CHOICES,
        null=True,
        blank=True,
        help_text="Applicable for PERCENTAGE_DISCOUNT and FIXED_DISCOUNT types.",
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator("0.01")],
        help_text=(
            "Discount input value. "
            "PERCENTAGE: e.g. 10.00 = 10%. "
            "FIXED_AMOUNT: e.g. 50.00 = ₹50."
        ),
    )
    max_discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator("0.00")],
        help_text="Cap on discount amount. Applicable for percentage type.",
    )

    # -------------------------------------------------------------------------
    # Eligibility thresholds
    # -------------------------------------------------------------------------
    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator("0.00")],
    )
    minimum_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Minimum total item quantity in the order.",
    )

    # -------------------------------------------------------------------------
    # Free item / BUY_X_GET_Y
    # -------------------------------------------------------------------------
    free_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="free_item_promotions",
        help_text="Required for FREE_ITEM promotion type.",
    )
    buy_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="X in BUY_X_GET_Y.",
    )
    get_quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Y in BUY_X_GET_Y.",
    )

    # -------------------------------------------------------------------------
    # Loyalty bonus multiplier (for LOYALTY_BONUS type)
    # -------------------------------------------------------------------------
    loyalty_bonus_multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator("1.00")],
        help_text="Points multiplier for LOYALTY_BONUS promotions (e.g. 2.0 = 2x points).",
    )

    # -------------------------------------------------------------------------
    # Validity
    # -------------------------------------------------------------------------
    start_at = models.DateTimeField(null=True, blank=True, db_index=True)
    end_at = models.DateTimeField(null=True, blank=True, db_index=True)

    # -------------------------------------------------------------------------
    # Usage limits
    # -------------------------------------------------------------------------
    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Global maximum number of times this promotion can be used. Null = unlimited.",
    )
    usage_limit_per_customer = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Per-customer maximum. Null = unlimited.",
    )
    current_usage_count = models.PositiveIntegerField(
        default=0,
        help_text="Current number of APPLIED usages. Only incremented via service (select_for_update).",
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    is_active = models.BooleanField(default=False, db_index=True)

    # -------------------------------------------------------------------------
    # Actors
    # -------------------------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="promotions_created",
    )

    class Meta:
        verbose_name = "Promotion"
        verbose_name_plural = "Promotions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["restaurant", "code"]),
            models.Index(fields=["promotion_type", "is_active"]),
            models.Index(fields=["start_at", "end_at"]),
            models.Index(fields=["is_active", "start_at", "end_at"]),
        ]

    def __str__(self):
        code_label = f" [{self.code}]" if self.code else ""
        return f"{self.name}{code_label} [{self.promotion_type}]"


# =============================================================================
# PromotionRule
# =============================================================================

class PromotionRule(TimestampedModel):
    """
    Eligibility rule for a promotion.

    Rules are evaluated server-side. Never trust frontend eligibility.
    Multiple rules per promotion are combined (all must pass).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.CASCADE,
        related_name="rules",
        db_index=True,
    )
    rule_type = models.CharField(
        max_length=30,
        choices=RULE_TYPE_CHOICES,
        db_index=True,
    )
    configuration = models.JSONField(
        default=dict,
        help_text=(
            "Rule-specific configuration. "
            "Examples: "
            'MIN_ORDER_VALUE: {"amount": "100.00"}, '
            'CUSTOMER_SEGMENT: {"segment_code": "VIP"}, '
            'DAY_OF_WEEK: {"days": [5, 6]}, '  # 0=Mon, 6=Sun
            'TIME_WINDOW: {"start": "18:00", "end": "22:00"}, '
            'FIRST_ORDER: {} (no config needed)'
        ),
    )
    priority = models.PositiveSmallIntegerField(
        default=10,
        help_text="Lower number = evaluated first. Rules are AND-combined.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Promotion Rule"
        verbose_name_plural = "Promotion Rules"
        ordering = ["priority", "created_at"]
        indexes = [
            models.Index(fields=["promotion", "is_active"]),
            models.Index(fields=["rule_type"]),
        ]

    def __str__(self):
        return f"Rule [{self.rule_type}] for {self.promotion.name}"


# =============================================================================
# PromotionUsage
# =============================================================================

class PromotionUsage(TimestampedModel):
    """
    Per-customer usage ledger for a promotion.

    Records are NEVER edited. Use status transitions:
        RESERVED → APPLIED (on bill finalization)
        RESERVED → CANCELLED (if order/bill cancelled before finalization)
        APPLIED → REVERSED (on bill/payment reversal)

    Idempotency: (promotion, customer, order) must be unique for APPLIED/RESERVED.
    Only APPLIED usages count toward current_usage_count.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.PROTECT,
        related_name="usages",
        db_index=True,
    )
    customer = models.ForeignKey(
        "crm.Customer",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promotion_usages",
        db_index=True,
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promotion_usages",
        db_index=True,
    )
    bill = models.ForeignKey(
        "billing.Bill",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="promotion_usages",
        db_index=True,
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="Actual discount amount applied (authoritative: from Billing service).",
    )
    used_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=USAGE_STATUS_CHOICES,
        default=USAGE_RESERVED,
        db_index=True,
    )

    class Meta:
        verbose_name = "Promotion Usage"
        verbose_name_plural = "Promotion Usages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["promotion", "status"]),
            models.Index(fields=["promotion", "customer"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["promotion", "customer", "status"]),
            models.Index(fields=["order"]),
            models.Index(fields=["bill"]),
        ]

    def __str__(self):
        cust = self.customer.customer_number if self.customer else "anonymous"
        return f"Usage [{self.status}] promo={self.promotion.name} customer={cust}"


# =============================================================================
# CampaignChannel
# =============================================================================

class CampaignChannel(TimestampedModel):
    """
    Channel configuration for a campaign.

    Marketing does NOT implement provider delivery — it delegates to
    Phase 16 NotificationService.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.PROTECT,
        related_name="channels",
        db_index=True,
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        db_index=True,
    )
    enabled = models.BooleanField(default=True)
    template_id = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional reference to a NotificationTemplate from Phase 16.",
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Campaign Channel"
        verbose_name_plural = "Campaign Channels"
        ordering = ["channel"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "channel"],
                name="unique_channel_per_campaign",
            ),
        ]
        indexes = [
            models.Index(fields=["campaign", "enabled"]),
        ]

    def __str__(self):
        return f"{self.channel} for {self.campaign.code}"


# =============================================================================
# CampaignMessage
# =============================================================================

class CampaignMessage(TimestampedModel):
    """
    Message content for a campaign channel.

    Safe placeholders only — never eval(). Supported:
        {{customer_name}}, {{restaurant_name}},
        {{promotion_code}}, {{reward_name}},
        {{expiry_date}}
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.PROTECT,
        related_name="messages",
        db_index=True,
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        db_index=True,
    )
    subject = models.CharField(
        max_length=200,
        blank=True,
        help_text="Email subject line. Supports safe placeholders.",
    )
    body = models.TextField(
        help_text="Message body. Supports safe placeholders.",
    )
    template_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Default values for template placeholders.",
    )

    class Meta:
        verbose_name = "Campaign Message"
        verbose_name_plural = "Campaign Messages"
        ordering = ["channel"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "channel"],
                name="unique_message_per_campaign_channel",
            ),
        ]
        indexes = [
            models.Index(fields=["campaign", "channel"]),
        ]

    def __str__(self):
        return f"Message [{self.channel}] for {self.campaign.code}"


# =============================================================================
# CampaignDelivery
# =============================================================================

class CampaignDelivery(TimestampedModel):
    """
    Marketing-level delivery tracking per customer per channel.

    This is the marketing view of delivery.
    Authoritative notification delivery state remains in
    notifications.NotificationDelivery.

    Idempotency: (campaign, customer, channel) must be unique for PENDING/QUEUED/SENT.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.PROTECT,
        related_name="deliveries",
        db_index=True,
    )
    customer = models.ForeignKey(
        "crm.Customer",
        on_delete=models.PROTECT,
        related_name="campaign_deliveries",
        db_index=True,
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        db_index=True,
    )
    # Link to the actual Notification created in Phase 16
    notification_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the created Notification record in notifications app.",
    )
    status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default=DELIVERY_PENDING,
        db_index=True,
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Campaign Delivery"
        verbose_name_plural = "Campaign Deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "status"]),
            models.Index(fields=["campaign", "customer"]),
            models.Index(fields=["campaign", "channel", "status"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["campaign", "customer", "channel"]),
        ]

    def __str__(self):
        return (
            f"Delivery [{self.channel}/{self.status}] "
            f"campaign={self.campaign.code} customer={self.customer.customer_number}"
        )


# =============================================================================
# CampaignConversion
# =============================================================================

class CampaignConversion(TimestampedModel):
    """
    Conversion / attribution record.

    A conversion is recorded when a customer who received a campaign
    subsequently takes a qualifying action (places order, redeems promotion, etc.).

    Attribution is DIRECT only — we never claim causal attribution.
    All conversions should be labeled DIRECTLY_ATTRIBUTED in reporting.

    Idempotency: (campaign, customer, order, conversion_type) is unique.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.PROTECT,
        related_name="conversions",
        db_index=True,
    )
    customer = models.ForeignKey(
        "crm.Customer",
        on_delete=models.PROTECT,
        related_name="campaign_conversions",
        db_index=True,
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="campaign_conversions",
        db_index=True,
    )
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="conversions",
        db_index=True,
    )
    conversion_type = models.CharField(
        max_length=30,
        choices=CONVERSION_TYPE_CHOICES,
        db_index=True,
    )
    conversion_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="Order amount or discount amount at time of conversion.",
    )
    converted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Campaign Conversion"
        verbose_name_plural = "Campaign Conversions"
        ordering = ["-converted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "customer", "order", "conversion_type"],
                condition=models.Q(order__isnull=False),
                name="unique_campaign_conversion_with_order",
            ),
        ]
        indexes = [
            models.Index(fields=["campaign", "conversion_type"]),
            models.Index(fields=["campaign", "customer"]),
            models.Index(fields=["customer", "converted_at"]),
            models.Index(fields=["campaign", "converted_at"]),
        ]

    def __str__(self):
        return (
            f"Conversion [{self.conversion_type}] "
            f"campaign={self.campaign.code} customer={self.customer.customer_number}"
        )


# =============================================================================
# CampaignEvent
# =============================================================================

class CampaignEvent(TimestampedModel):
    """
    Append-only event timeline for a campaign.

    Every significant event in the campaign lifecycle is recorded here.
    These records are IMMUTABLE — save() guard prevents updates.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.PROTECT,
        related_name="events",
        db_index=True,
    )
    customer = models.ForeignKey(
        "crm.Customer",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="campaign_events",
        db_index=True,
    )
    event_type = models.CharField(
        max_length=40,
        choices=EVENT_TYPE_CHOICES,
        db_index=True,
    )
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Campaign Event"
        verbose_name_plural = "Campaign Events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["campaign", "event_type"]),
            models.Index(fields=["campaign", "created_at"]),
            models.Index(fields=["campaign", "customer"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"Event [{self.event_type}] for {self.campaign.code}"

    def save(self, *args, **kwargs):
        if self.pk and CampaignEvent.objects.filter(pk=self.pk).exists():
            raise ValueError("CampaignEvent records are immutable — they cannot be updated.")
        super().save(*args, **kwargs)


# =============================================================================
# MarketingSettings
# =============================================================================

class MarketingSettings(TimestampedModel):
    """
    Restaurant-level marketing configuration.

    One record per restaurant. Created on first access.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.OneToOneField(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="marketing_settings",
    )
    default_currency = models.CharField(max_length=10, blank=True, default="INR")
    max_discount_without_approval = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Max discount value before approval is required. Null = no threshold.",
    )
    default_campaign_timezone = models.CharField(
        max_length=100,
        blank=True,
        default="Asia/Kolkata",
    )
    frequency_limit_enabled = models.BooleanField(default=True)
    default_daily_contact_limit = models.PositiveSmallIntegerField(default=3)
    default_weekly_contact_limit = models.PositiveSmallIntegerField(default=10)

    class Meta:
        verbose_name = "Marketing Settings"
        verbose_name_plural = "Marketing Settings"

    def __str__(self):
        return f"MarketingSettings for {self.restaurant.name}"


# =============================================================================
# MarketingContactPolicy
# =============================================================================

class MarketingContactPolicy(TimestampedModel):
    """
    Per-channel frequency control policy.

    Prevents customer spam by limiting how many marketing messages
    a customer can receive per day/week.

    This ONLY applies to marketing campaign messages.
    Transactional notifications are NOT subject to this policy.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="marketing_contact_policies",
        db_index=True,
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        db_index=True,
    )
    max_messages_per_day = models.PositiveSmallIntegerField(default=3)
    max_messages_per_week = models.PositiveSmallIntegerField(default=10)
    cooldown_hours = models.PositiveSmallIntegerField(
        default=0,
        help_text="Minimum hours between any two marketing messages for same customer/channel.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Marketing Contact Policy"
        verbose_name_plural = "Marketing Contact Policies"
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "channel"],
                name="unique_contact_policy_per_channel",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
        ]

    def __str__(self):
        return f"ContactPolicy [{self.channel}] for {self.restaurant.name}"


# =============================================================================
# MarketingAuditLog
# =============================================================================

class MarketingAuditLog(TimestampedModel):
    """
    Append-only audit trail for all marketing actions.

    Every significant action (campaign state change, promotion activation,
    delivery failures, consent blocks) is recorded here.

    Records are IMMUTABLE — save() guard prevents updates.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketing_audit_logs",
    )
    action = models.CharField(
        max_length=60,
        choices=AUDIT_EVENT_CHOICES,
        db_index=True,
    )
    entity_type = models.CharField(max_length=50, db_index=True)
    entity_id = models.CharField(max_length=100, db_index=True)
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketing_audit_logs",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="marketing_audit_logs",
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "Marketing Audit Log"
        verbose_name_plural = "Marketing Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["restaurant", "created_at"]),
            models.Index(fields=["actor", "created_at"]),
        ]

    def __str__(self):
        return f"[{self.action}] {self.entity_type}:{self.entity_id}"

    def save(self, *args, **kwargs):
        if self.pk and MarketingAuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError("MarketingAuditLog records are immutable — they cannot be updated.")
        super().save(*args, **kwargs)
