# =============================================================================
# RestaurantFlow — Marketing Access Control
# Phase 18
#
# Single source of truth for marketing authorization decisions.
# Views and services delegate here.
#
# Public API:
#   get_accessible_campaigns(user)   → QuerySet[MarketingCampaign]
#   get_accessible_promotions(user)  → QuerySet[Promotion]
#   can_access_campaign(user, obj)   → bool
#   can_access_promotion(user, obj)  → bool
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("marketing")


def get_accessible_campaigns(user):
    from marketing.models import MarketingCampaign

    if not user or not user.is_authenticated or not user.is_active:
        return MarketingCampaign.objects.none()

    if user.is_superuser or user.is_staff:
        return MarketingCampaign.objects.all()

    accessible_restaurants = acl.get_accessible_restaurants(user)
    accessible_orgs = acl.get_accessible_organizations(user)

    from django.db.models import Q
    return MarketingCampaign.objects.filter(
        Q(restaurant__in=accessible_restaurants) |
        Q(restaurant__isnull=True, company__in=accessible_orgs)
    )


def get_accessible_promotions(user):
    from marketing.models import Promotion

    if not user or not user.is_authenticated or not user.is_active:
        return Promotion.objects.none()

    if user.is_superuser or user.is_staff:
        return Promotion.objects.all()

    accessible_restaurants = acl.get_accessible_restaurants(user)
    accessible_orgs = acl.get_accessible_organizations(user)

    from django.db.models import Q
    return Promotion.objects.filter(
        Q(restaurant__in=accessible_restaurants) |
        Q(restaurant__isnull=True, company__in=accessible_orgs)
    )


def can_access_campaign(user, campaign) -> bool:
    return get_accessible_campaigns(user).filter(pk=campaign.pk).exists()


def can_access_promotion(user, promotion) -> bool:
    return get_accessible_promotions(user).filter(pk=promotion.pk).exists()
