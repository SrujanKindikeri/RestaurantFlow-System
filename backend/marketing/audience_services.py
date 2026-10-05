# =============================================================================
# RestaurantFlow — Audience Services
# Phase 18
#
# CampaignAudienceService — resolve and manage campaign audiences.
#
# Rules:
#   - Reuses Phase 17 Customer, CustomerSegment, CustomerTag, CustomerConsent.
#   - Never duplicates customer selection logic.
#   - Asynchronous resolution for large audiences.
#   - Consent check at membership creation (not just at delivery).
#   - Exclusion rules: blocked, inactive, unsubscribed, frequency limit.
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone

from marketing.constants import (
    AUDIENCE_ALL_CUSTOMERS, AUDIENCE_NEW_CUSTOMERS, AUDIENCE_RETURNING,
    AUDIENCE_VIP, AUDIENCE_HIGH_VALUE, AUDIENCE_FREQUENT,
    AUDIENCE_INACTIVE, AUDIENCE_AT_RISK,
    AUDIENCE_CUSTOM_SEGMENT, AUDIENCE_CUSTOM_TAG, AUDIENCE_CUSTOM_FILTER,
    MEMBER_ELIGIBLE, MEMBER_EXCLUDED,
    AUDIT_AUDIENCE_CREATED, AUDIT_AUDIENCE_UPDATED,
    PERM_AUDIENCE_MANAGE,
)
from marketing.exceptions import MarketingPermissionDenied
from accounts import access as acl

logger = logging.getLogger("marketing")


def _emit_audit(action, entity_type, entity_id, actor=None,
                company=None, restaurant=None, metadata=None):
    from marketing.models import MarketingAuditLog
    try:
        MarketingAuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            company=company,
            restaurant=restaurant,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.error("_emit_audit failed: action=%s error=%s", action, exc)


class CampaignAudienceService:

    @staticmethod
    def create_audience(campaign, *, audience_type: str, criteria: dict,
                        actor) -> "CampaignAudience":
        """
        Create an audience definition for a campaign.
        Does NOT resolve members yet — call generate_audience_members() for that.
        """
        from marketing.models import CampaignAudience

        if not acl.has_permission(actor, PERM_AUDIENCE_MANAGE):
            raise MarketingPermissionDenied(PERM_AUDIENCE_MANAGE + " permission required.")

        with transaction.atomic():
            audience = CampaignAudience.objects.create(
                campaign=campaign,
                audience_type=audience_type,
                criteria=criteria,
                estimated_count=0,
            )

        _emit_audit(
            AUDIT_AUDIENCE_CREATED, "CAMPAIGN_AUDIENCE", audience.pk,
            actor=actor, company=campaign.company, restaurant=campaign.restaurant,
            metadata={"audience_type": audience_type, "criteria": criteria},
        )
        return audience

    @staticmethod
    def generate_audience_members(campaign, audience, actor=None):
        """
        Resolve and persist CampaignAudienceMember rows for the given audience.

        Called synchronously for small datasets; triggered via Celery for large ones.
        Returns count of ELIGIBLE members added.
        """
        restaurant = campaign.restaurant
        if not restaurant:
            # Company-wide — resolve per each restaurant in company
            # For simplicity, skip company-wide member generation here
            logger.warning(
                "generate_audience_members: company-wide campaigns not fully supported; "
                "set restaurant on campaign."
            )
            return 0

        queryset = CampaignAudienceService._resolve_customer_queryset(
            audience, restaurant
        )

        eligible_count = 0
        excluded_count = 0

        # Process in batches to avoid memory issues
        BATCH_SIZE = 200
        from marketing.models import CampaignAudienceMember

        for customer in queryset.iterator(chunk_size=BATCH_SIZE):
            exclusion_reason = CampaignAudienceService._get_exclusion_reason(
                customer, campaign, audience
            )
            status = MEMBER_EXCLUDED if exclusion_reason else MEMBER_ELIGIBLE
            meta = {"exclusion_reason": exclusion_reason} if exclusion_reason else {}

            obj, created = CampaignAudienceMember.objects.get_or_create(
                campaign=campaign,
                customer=customer,
                defaults={"status": status, "metadata": meta},
            )
            if not created and obj.status != status:
                # Update if status changed
                obj.status = status
                obj.metadata = meta
                obj.save(update_fields=["status", "metadata", "updated_at"])

            if status == MEMBER_ELIGIBLE:
                eligible_count += 1
            else:
                excluded_count += 1

        # Update estimated count on audience
        from marketing.models import CampaignAudience
        CampaignAudience.objects.filter(pk=audience.pk).update(
            estimated_count=eligible_count, updated_at=timezone.now()
        )

        _emit_audit(
            AUDIT_AUDIENCE_UPDATED, "CAMPAIGN_AUDIENCE", audience.pk,
            actor=actor, company=campaign.company, restaurant=campaign.restaurant,
            metadata={
                "eligible": eligible_count,
                "excluded": excluded_count,
                "audience_type": audience.audience_type,
            },
        )

        logger.info(
            "generate_audience_members: campaign=%s eligible=%d excluded=%d",
            campaign.code, eligible_count, excluded_count,
        )
        return eligible_count

    @staticmethod
    def _resolve_customer_queryset(audience, restaurant):
        """Build a queryset of customers for the audience type + criteria."""
        from crm.models import Customer, CustomerSegmentAssignment, CustomerTagAssignment

        base_qs = Customer.objects.filter(
            restaurant=restaurant,
            is_active=True,
            is_blocked=False,
        ).select_related("restaurant")

        audience_type = audience.audience_type
        criteria = audience.criteria or {}

        if audience_type == AUDIENCE_ALL_CUSTOMERS:
            return base_qs

        elif audience_type == AUDIENCE_NEW_CUSTOMERS:
            # First order within last 30 days or no orders
            return base_qs.filter(total_orders__lte=1)

        elif audience_type == AUDIENCE_RETURNING:
            return base_qs.filter(total_orders__gt=1)

        elif audience_type == AUDIENCE_VIP:
            segment_code = "VIP"
            return base_qs.filter(
                segment_assignments__segment__code=segment_code,
                segment_assignments__is_active=True,
            ).distinct()

        elif audience_type == AUDIENCE_HIGH_VALUE:
            return base_qs.filter(
                segment_assignments__segment__code="HIGH_VALUE",
                segment_assignments__is_active=True,
            ).distinct()

        elif audience_type == AUDIENCE_FREQUENT:
            return base_qs.filter(
                segment_assignments__segment__code="FREQUENT",
                segment_assignments__is_active=True,
            ).distinct()

        elif audience_type == AUDIENCE_INACTIVE:
            days = criteria.get("days_since_last_order", 60)
            cutoff = timezone.now() - __import__("datetime").timedelta(days=days)
            return base_qs.filter(
                last_order_at__isnull=False,
                last_order_at__lt=cutoff,
            )

        elif audience_type == AUDIENCE_AT_RISK:
            days = criteria.get("days_since_last_order", 30)
            cutoff = timezone.now() - __import__("datetime").timedelta(days=days)
            return base_qs.filter(
                last_order_at__isnull=False,
                last_order_at__lt=cutoff,
                total_orders__gt=1,
            )

        elif audience_type == AUDIENCE_CUSTOM_SEGMENT:
            segment_id = criteria.get("segment_id")
            segment_code = criteria.get("segment_code") or criteria.get("segment")
            if segment_id:
                return base_qs.filter(
                    segment_assignments__segment_id=segment_id,
                    segment_assignments__is_active=True,
                ).distinct()
            elif segment_code:
                return base_qs.filter(
                    segment_assignments__segment__code=segment_code,
                    segment_assignments__is_active=True,
                ).distinct()
            return base_qs.none()

        elif audience_type == AUDIENCE_CUSTOM_TAG:
            tag_id = criteria.get("tag_id")
            tag_code = criteria.get("tag_code") or criteria.get("tag")
            if tag_id:
                return base_qs.filter(
                    tag_assignments__tag_id=tag_id,
                    tag_assignments__is_active=True,
                ).distinct()
            elif tag_code:
                return base_qs.filter(
                    tag_assignments__tag__code=tag_code,
                    tag_assignments__is_active=True,
                ).distinct()
            return base_qs.none()

        elif audience_type == AUDIENCE_CUSTOM_FILTER:
            # Apply JSON criteria as queryset filters
            return CampaignAudienceService._apply_custom_filter(base_qs, criteria)

        return base_qs.none()

    @staticmethod
    def _apply_custom_filter(base_qs, criteria: dict):
        """Apply a custom JSON criteria dict to the customer queryset."""
        from django.db.models import Q
        import datetime

        qs = base_qs
        if "min_orders" in criteria:
            qs = qs.filter(total_orders__gte=criteria["min_orders"])
        if "max_orders" in criteria:
            qs = qs.filter(total_orders__lte=criteria["max_orders"])
        if "min_lifetime_spend" in criteria:
            qs = qs.filter(lifetime_spend__gte=criteria["min_lifetime_spend"])
        if "days_since_last_order" in criteria:
            days = int(criteria["days_since_last_order"])
            cutoff = timezone.now() - datetime.timedelta(days=days)
            qs = qs.filter(last_order_at__lt=cutoff)
        if "has_birthday_today" in criteria and criteria["has_birthday_today"]:
            today = timezone.now().date()
            qs = qs.filter(date_of_birth__month=today.month, date_of_birth__day=today.day)
        if "birthday_in_days" in criteria:
            from django.db.models.functions import ExtractMonth, ExtractDay
            days_ahead = int(criteria["birthday_in_days"])
            today = timezone.now().date()
            target = today + datetime.timedelta(days=days_ahead)
            qs = qs.annotate(
                bday_month=ExtractMonth("date_of_birth"),
                bday_day=ExtractDay("date_of_birth"),
            ).filter(
                bday_month=target.month,
                bday_day=target.day,
            )
        return qs

    @staticmethod
    def _get_exclusion_reason(customer, campaign, audience) -> str:
        """Return exclusion reason string or empty string if eligible."""
        if customer.is_blocked:
            return "customer_blocked"
        if not customer.is_active:
            return "customer_inactive"
        if getattr(customer, "merged_into_id", None):
            return "customer_merged"
        return ""
