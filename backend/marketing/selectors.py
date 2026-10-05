# =============================================================================
# RestaurantFlow — Marketing Selectors
# Phase 18
#
# Read-only queryset builders. No mutations here.
# =============================================================================

import logging
from django.db.models import Count, Sum, Q

from marketing.constants import (
    CAMPAIGN_RUNNING, CAMPAIGN_SCHEDULED, CAMPAIGN_COMPLETED,
    CAMPAIGN_DRAFT, CAMPAIGN_PENDING_APPROVAL, CAMPAIGN_PAUSED,
    USAGE_APPLIED,
    DELIVERY_SENT, DELIVERY_DELIVERED, DELIVERY_FAILED,
    MEMBER_CONVERTED, MEMBER_CONTACTED, MEMBER_ELIGIBLE,
    CONVERSION_PROMOTION_REDEEMED,
)

logger = logging.getLogger("marketing")


# ---------------------------------------------------------------------------
# Campaign selectors
# ---------------------------------------------------------------------------

def get_campaigns(user, company=None, restaurant=None, status=None,
                  campaign_type=None):
    from marketing.models import MarketingCampaign
    from marketing.access import get_accessible_campaigns

    qs = get_accessible_campaigns(user)
    if company:
        qs = qs.filter(company=company)
    if restaurant:
        qs = qs.filter(Q(restaurant=restaurant) | Q(restaurant__isnull=True))
    if status:
        qs = qs.filter(status=status)
    if campaign_type:
        qs = qs.filter(campaign_type=campaign_type)
    return qs.select_related("company", "restaurant", "branch", "created_by")


def get_campaign_by_id(user, campaign_id):
    from marketing.models import MarketingCampaign
    from marketing.access import get_accessible_campaigns

    qs = get_accessible_campaigns(user)
    try:
        return qs.select_related(
            "company", "restaurant", "branch", "created_by",
            "approved_by", "cancelled_by"
        ).get(pk=campaign_id)
    except MarketingCampaign.DoesNotExist:
        return None


def get_active_campaigns(restaurant):
    from marketing.models import MarketingCampaign
    from django.utils import timezone

    now = timezone.now()
    return MarketingCampaign.objects.filter(
        restaurant=restaurant,
        status=CAMPAIGN_RUNNING,
    ).filter(
        Q(end_at__isnull=True) | Q(end_at__gte=now)
    ).select_related("company", "restaurant")


def get_scheduled_campaigns_due():
    """Return SCHEDULED campaigns whose start_at has passed."""
    from marketing.models import MarketingCampaign
    from django.utils import timezone

    now = timezone.now()
    return MarketingCampaign.objects.filter(
        status=CAMPAIGN_SCHEDULED,
        start_at__lte=now,
    ).select_related("company", "restaurant")


def get_running_campaigns_expired():
    """Return RUNNING campaigns whose end_at has passed."""
    from marketing.models import MarketingCampaign
    from django.utils import timezone

    now = timezone.now()
    return MarketingCampaign.objects.filter(
        status=CAMPAIGN_RUNNING,
        end_at__isnull=False,
        end_at__lte=now,
    ).select_related("company", "restaurant")


# ---------------------------------------------------------------------------
# Promotion selectors
# ---------------------------------------------------------------------------

def get_promotions(user, company=None, restaurant=None, is_active=None):
    from marketing.models import Promotion
    from marketing.access import get_accessible_promotions

    qs = get_accessible_promotions(user)
    if company:
        qs = qs.filter(company=company)
    if restaurant:
        qs = qs.filter(
            Q(restaurant=restaurant) |
            Q(restaurant__isnull=True, company=restaurant.company)
        )
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs.select_related("company", "restaurant", "branch")


def get_promotion_by_id(user, promotion_id):
    from marketing.models import Promotion
    from marketing.access import get_accessible_promotions

    qs = get_accessible_promotions(user)
    try:
        return qs.select_related("company", "restaurant", "branch", "free_item").get(
            pk=promotion_id
        )
    except Promotion.DoesNotExist:
        return None


def get_promotion_by_code(code: str, restaurant=None, branch=None):
    """Case-insensitive promo code lookup."""
    from marketing.models import Promotion
    from django.utils import timezone
    from marketing.promotion_services import models_Q_start_end_filter, models_scope_filter

    normalized = (code or "").strip().upper()
    if not normalized:
        return None

    now = timezone.now()
    qs = Promotion.objects.filter(
        code=normalized,
        is_active=True,
    ).filter(models_Q_start_end_filter(now))

    if branch:
        qs = qs.filter(models_scope_filter(branch, branch.restaurant))
    elif restaurant:
        qs = qs.filter(
            Q(restaurant=restaurant) | Q(restaurant__isnull=True, company=restaurant.company)
        )

    return qs.select_related("restaurant", "branch", "free_item").first()


def get_expiring_promotions(hours_ahead: int = 24):
    """Return active promotions expiring within hours_ahead."""
    from marketing.models import Promotion
    from django.utils import timezone
    import datetime

    now = timezone.now()
    cutoff = now + datetime.timedelta(hours=hours_ahead)
    return Promotion.objects.filter(
        is_active=True,
        end_at__isnull=False,
        end_at__lte=cutoff,
        end_at__gte=now,
    ).select_related("restaurant")


# ---------------------------------------------------------------------------
# Analytics selectors
# ---------------------------------------------------------------------------

def get_campaign_analytics(campaign):
    """Aggregate delivery + conversion metrics for a campaign."""
    from marketing.models import CampaignDelivery, CampaignConversion, CampaignAudienceMember

    audience_total = CampaignAudienceMember.objects.filter(campaign=campaign).count()
    eligible = CampaignAudienceMember.objects.filter(
        campaign=campaign, status=MEMBER_ELIGIBLE
    ).count()
    contacted = CampaignAudienceMember.objects.filter(
        campaign=campaign, status=MEMBER_CONTACTED
    ).count()
    converted = CampaignAudienceMember.objects.filter(
        campaign=campaign, status=MEMBER_CONVERTED
    ).count()

    deliveries_sent = CampaignDelivery.objects.filter(
        campaign=campaign, status__in=[DELIVERY_SENT, DELIVERY_DELIVERED]
    ).count()
    deliveries_failed = CampaignDelivery.objects.filter(
        campaign=campaign, status=DELIVERY_FAILED
    ).count()

    conversions = CampaignConversion.objects.filter(campaign=campaign)
    conversion_value = conversions.aggregate(
        total=Sum("conversion_value")
    )["total"] or 0

    from marketing.models import PromotionUsage
    from decimal import Decimal
    discount_given = PromotionUsage.objects.filter(
        promotion__conversions__campaign=campaign,
        status=USAGE_APPLIED,
    ).aggregate(total=Sum("discount_amount"))["total"] or Decimal("0.00")

    delivery_rate = (
        round(deliveries_sent / audience_total * 100, 2) if audience_total else 0
    )
    conversion_rate = (
        round(converted / contacted * 100, 2) if contacted else 0
    )

    return {
        "campaign_id": str(campaign.pk),
        "campaign_code": campaign.code,
        "audience_total": audience_total,
        "eligible": eligible,
        "contacted": contacted,
        "converted": converted,
        "deliveries_sent": deliveries_sent,
        "deliveries_failed": deliveries_failed,
        "delivery_rate_pct": delivery_rate,
        "conversion_rate_pct": conversion_rate,
        "conversion_value": str(conversion_value),
        "discount_given": str(discount_given),
    }


def get_dashboard_stats(company, restaurant=None):
    """Aggregate marketing dashboard metrics."""
    from marketing.models import MarketingCampaign, PromotionUsage
    from django.db.models import Count, Sum
    from decimal import Decimal

    qs_filter = {"company": company}
    if restaurant:
        qs_filter["restaurant"] = restaurant

    campaigns = MarketingCampaign.objects.filter(**qs_filter)

    active_count = campaigns.filter(status=CAMPAIGN_RUNNING).count()
    scheduled_count = campaigns.filter(status=CAMPAIGN_SCHEDULED).count()
    draft_count = campaigns.filter(status=CAMPAIGN_DRAFT).count()
    pending_approval = campaigns.filter(status=CAMPAIGN_PENDING_APPROVAL).count()
    completed_count = campaigns.filter(status=CAMPAIGN_COMPLETED).count()

    from marketing.models import CampaignConversion
    conv_qs = CampaignConversion.objects.filter(campaign__company=company)
    if restaurant:
        conv_qs = conv_qs.filter(campaign__restaurant=restaurant)

    total_conversions = conv_qs.count()
    total_revenue = conv_qs.aggregate(
        total=Sum("conversion_value")
    )["total"] or Decimal("0.00")

    usage_qs = PromotionUsage.objects.filter(
        promotion__company=company, status=USAGE_APPLIED
    )
    if restaurant:
        usage_qs = usage_qs.filter(promotion__restaurant=restaurant)

    total_discount = usage_qs.aggregate(
        total=Sum("discount_amount")
    )["total"] or Decimal("0.00")
    total_promo_uses = usage_qs.count()

    return {
        "active_campaigns": active_count,
        "scheduled_campaigns": scheduled_count,
        "draft_campaigns": draft_count,
        "pending_approvals": pending_approval,
        "completed_campaigns": completed_count,
        "total_conversions": total_conversions,
        "total_revenue_attributed": str(total_revenue),
        "total_discount_given": str(total_discount),
        "total_promotion_uses": total_promo_uses,
    }
