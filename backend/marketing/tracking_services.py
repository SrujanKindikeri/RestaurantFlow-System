# =============================================================================
# RestaurantFlow — Campaign Delivery & Conversion Tracking Services
# Phase 18
#
# CampaignDeliveryService   — create/update campaign delivery records.
# CampaignConversionService — record conversions (attributions).
# MarketingConsentService   — consent + frequency checks.
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone

from marketing.constants import (
    CHANNEL_IN_APP, CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_WHATSAPP, CHANNEL_TELEGRAM,
    CHANNEL_CONSENT_MAP,
    DELIVERY_PENDING, DELIVERY_QUEUED, DELIVERY_SENT,
    DELIVERY_DELIVERED, DELIVERY_FAILED, DELIVERY_SKIPPED, DELIVERY_UNSUBSCRIBED,
    CONVERSION_PROMOTION_REDEEMED, CONVERSION_ORDER_PLACED,
    MEMBER_CONTACTED, MEMBER_CONVERTED,
    AUDIT_CONSENT_BLOCKED, AUDIT_DELIVERY_FAILED,
    WS_DELIVERY_FAILED, WS_CONVERSION_CREATED,
    SOURCE_MARKETING_CAMPAIGN,
    CACHE_KEY_FREQUENCY_DAY, CACHE_KEY_FREQUENCY_WEEK,
)
from marketing.exceptions import (
    MarketingConsentRequired, FrequencyLimitExceeded,
)

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
        logger.error("_emit_audit failed: %s", exc)


# =============================================================================
# MarketingConsentService
# =============================================================================

class MarketingConsentService:

    @staticmethod
    def has_marketing_consent(customer, channel: str) -> bool:
        """
        Check if the customer has granted consent for this marketing channel.

        MARKETING_EMAIL / MARKETING_SMS / MARKETING_WHATSAPP / MARKETING_TELEGRAM
        must be GRANTED. IN_APP does not require explicit marketing consent.
        """
        if channel == CHANNEL_IN_APP:
            return True  # In-app follows notification preferences, not marketing consent

        consent_type = CHANNEL_CONSENT_MAP.get(channel)
        if not consent_type:
            return True

        from crm.models import CustomerConsent
        from crm.constants import CONSENT_GRANTED

        consent = CustomerConsent.objects.filter(
            customer=customer,
            consent_type=consent_type,
        ).first()

        if consent is None:
            return False  # No record = not consented
        return consent.status == CONSENT_GRANTED

    @staticmethod
    def check_frequency_limit(customer, campaign, channel: str) -> bool:
        """
        Return True if the customer is within frequency limits (can receive message).
        Return False if limit exceeded (skip delivery).
        """
        from django.core.cache import cache

        restaurant = campaign.restaurant
        if not restaurant:
            return True

        # Get contact policy for this channel
        policy = _get_contact_policy(restaurant, channel)
        if not policy or not policy.is_active:
            # Fallback to marketing settings
            try:
                mkt_settings = restaurant.marketing_settings
                if not mkt_settings.frequency_limit_enabled:
                    return True
                max_day = mkt_settings.default_daily_contact_limit
                max_week = mkt_settings.default_weekly_contact_limit
            except Exception:
                return True
        else:
            max_day = policy.max_messages_per_day
            max_week = policy.max_messages_per_week

        today = timezone.now().date()
        week_num = today.isocalendar()[1]

        day_key = CACHE_KEY_FREQUENCY_DAY.format(
            restaurant_id=restaurant.pk,
            customer_id=customer.pk,
            channel=channel,
            date=today.isoformat(),
        )
        week_key = CACHE_KEY_FREQUENCY_WEEK.format(
            restaurant_id=restaurant.pk,
            customer_id=customer.pk,
            channel=channel,
            week=f"{today.year}-W{week_num}",
        )

        day_count = int(cache.get(day_key, 0))
        week_count = int(cache.get(week_key, 0))

        if day_count >= max_day or week_count >= max_week:
            return False

        return True

    @staticmethod
    def record_contact(customer, campaign, channel: str):
        """Increment frequency counters after a message is sent."""
        from django.core.cache import cache

        restaurant = campaign.restaurant
        if not restaurant:
            return

        today = timezone.now().date()
        week_num = today.isocalendar()[1]

        day_key = CACHE_KEY_FREQUENCY_DAY.format(
            restaurant_id=restaurant.pk,
            customer_id=customer.pk,
            channel=channel,
            date=today.isoformat(),
        )
        week_key = CACHE_KEY_FREQUENCY_WEEK.format(
            restaurant_id=restaurant.pk,
            customer_id=customer.pk,
            channel=channel,
            week=f"{today.year}-W{week_num}",
        )

        # Increment with TTL
        cache.set(day_key, int(cache.get(day_key, 0)) + 1, timeout=86400)   # 24h
        cache.set(week_key, int(cache.get(week_key, 0)) + 1, timeout=604800) # 7d


def _get_contact_policy(restaurant, channel):
    from marketing.models import MarketingContactPolicy
    return MarketingContactPolicy.objects.filter(
        restaurant=restaurant, channel=channel, is_active=True
    ).first()


# =============================================================================
# CampaignDeliveryService
# =============================================================================

class CampaignDeliveryService:

    @staticmethod
    def create_delivery(campaign, customer, channel: str) -> "CampaignDelivery | None":
        """
        Create a CampaignDelivery record for a customer+channel.

        Idempotent: if a non-failed/non-skipped record already exists, return it.
        Returns None if consent check or frequency limit fails (delivery skipped).
        """
        from marketing.models import CampaignDelivery

        # Consent check
        if not MarketingConsentService.has_marketing_consent(customer, channel):
            _emit_audit(
                AUDIT_CONSENT_BLOCKED, "CAMPAIGN_DELIVERY", f"{campaign.pk}:{customer.pk}",
                company=campaign.company, restaurant=campaign.restaurant,
                metadata={
                    "customer": str(customer.pk),
                    "channel": channel,
                    "reason": "marketing_consent_not_granted",
                },
            )
            # Create UNSUBSCRIBED record so we know we tried
            CampaignDelivery.objects.get_or_create(
                campaign=campaign,
                customer=customer,
                channel=channel,
                defaults={"status": DELIVERY_UNSUBSCRIBED},
            )
            return None

        # Frequency limit check
        if not MarketingConsentService.check_frequency_limit(customer, campaign, channel):
            CampaignDelivery.objects.get_or_create(
                campaign=campaign,
                customer=customer,
                channel=channel,
                defaults={"status": DELIVERY_SKIPPED},
            )
            logger.debug(
                "create_delivery: frequency limit exceeded customer=%s channel=%s",
                customer.pk, channel,
            )
            return None

        # Idempotency: don't duplicate active deliveries
        existing = CampaignDelivery.objects.filter(
            campaign=campaign,
            customer=customer,
            channel=channel,
        ).exclude(status__in=[DELIVERY_FAILED, DELIVERY_SKIPPED, DELIVERY_UNSUBSCRIBED]).first()

        if existing:
            return existing

        with transaction.atomic():
            delivery = CampaignDelivery.objects.create(
                campaign=campaign,
                customer=customer,
                channel=channel,
                status=DELIVERY_PENDING,
            )

        return delivery

    @staticmethod
    def mark_sent(delivery, notification_id=None):
        """Mark a delivery as SENT after the notification is created."""
        from marketing.models import CampaignDelivery
        now = timezone.now()
        update_fields = ["status", "sent_at", "updated_at"]
        CampaignDelivery.objects.filter(pk=delivery.pk).update(
            status=DELIVERY_SENT,
            sent_at=now,
            **{"notification_id": notification_id} if notification_id else {},
        )
        # Update member status to CONTACTED
        CampaignDeliveryService._update_member_status(
            delivery.campaign, delivery.customer, MEMBER_CONTACTED
        )
        # Record frequency
        MarketingConsentService.record_contact(
            delivery.customer, delivery.campaign, delivery.channel
        )

    @staticmethod
    def mark_failed(delivery, reason: str = ""):
        """Mark a delivery as FAILED."""
        from marketing.models import CampaignDelivery
        now = timezone.now()
        CampaignDelivery.objects.filter(pk=delivery.pk).update(
            status=DELIVERY_FAILED,
            failed_at=now,
            failure_reason=reason,
            updated_at=now,
        )
        _emit_audit(
            AUDIT_DELIVERY_FAILED, "CAMPAIGN_DELIVERY", delivery.pk,
            company=delivery.campaign.company, restaurant=delivery.campaign.restaurant,
            metadata={"reason": reason, "channel": delivery.channel},
        )
        c_id = delivery.campaign.pk
        co_id = delivery.campaign.company_id
        transaction.on_commit(lambda: _emit_ws_failed(WS_DELIVERY_FAILED, c_id, co_id))

    @staticmethod
    def send_via_notification_service(delivery, message_body: str, subject: str = ""):
        """
        Dispatch campaign message via Phase 16 NotificationService.

        Marketing does NOT implement provider delivery. It delegates to
        the Notification Center.
        """
        from notifications.services import NotificationService
        from notifications.constants import (
            SEVERITY_INFO, CHANNEL_EMAIL, CHANNEL_SMS,
            CHANNEL_WHATSAPP, CHANNEL_TELEGRAM, CHANNEL_IN_APP,
        )
        from marketing.constants import NOTIF_CAMPAIGN_DELIVERY

        campaign = delivery.campaign
        customer = delivery.customer

        # Map marketing channel to notification channel constant
        channel_map = {
            CHANNEL_IN_APP:   "IN_APP",
            CHANNEL_EMAIL:    CHANNEL_EMAIL,
            CHANNEL_SMS:      CHANNEL_SMS,
            CHANNEL_WHATSAPP: CHANNEL_WHATSAPP,
            CHANNEL_TELEGRAM: CHANNEL_TELEGRAM,
        }
        notif_channel = channel_map.get(delivery.channel, "IN_APP")

        # Resolve a User that corresponds to this customer if possible
        # (Notifications are user-centric; we notify via user's linked account)
        user = _resolve_customer_user(customer)
        if not user and delivery.channel != CHANNEL_IN_APP:
            # External channels require a linked user account; skip gracefully
            logger.debug(
                "send_via_notification_service: no user for customer=%s, skipping channel=%s",
                customer.pk, delivery.channel,
            )
            CampaignDeliveryService.mark_failed(
                delivery, reason="no_linked_user_account"
            )
            return

        try:
            notification = NotificationService.create_notification(
                company=campaign.company,
                notification_type=NOTIF_CAMPAIGN_DELIVERY,
                severity=SEVERITY_INFO,
                title=subject or campaign.name,
                message=message_body,
                source_type=SOURCE_MARKETING_CAMPAIGN,
                source_id=str(campaign.pk),
                restaurant=campaign.restaurant,
                branch=campaign.branch,
                metadata={
                    "campaign_id": str(campaign.pk),
                    "campaign_code": campaign.code,
                    "customer_id": str(customer.pk),
                    "channel": delivery.channel,
                },
            )
            notif_id = notification.pk if notification else None
            CampaignDeliveryService.mark_sent(delivery, notification_id=notif_id)
        except Exception as exc:
            logger.error(
                "send_via_notification_service: failed campaign=%s customer=%s error=%s",
                campaign.code, customer.pk, exc,
            )
            CampaignDeliveryService.mark_failed(delivery, reason=str(exc))

    @staticmethod
    def _update_member_status(campaign, customer, new_status: str):
        from marketing.models import CampaignAudienceMember
        CampaignAudienceMember.objects.filter(
            campaign=campaign, customer=customer
        ).update(status=new_status, updated_at=timezone.now())


def _resolve_customer_user(customer):
    """Try to find a User linked to this customer by email or phone."""
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if customer.email:
            user = User.objects.filter(email=customer.email, is_active=True).first()
            if user:
                return user
        if customer.phone:
            user = User.objects.filter(phone=customer.phone, is_active=True).first()
            if user:
                return user
    except Exception:
        pass
    return None


def _emit_ws_failed(event_name, campaign_id, company_id):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"company_{company_id}",
                {"type": "marketing_event", "event": event_name, "campaign_id": str(campaign_id)},
            )
    except Exception as exc:
        logger.debug("_emit_ws_failed: %s", exc)


# =============================================================================
# CampaignConversionService
# =============================================================================

class CampaignConversionService:

    @staticmethod
    def record_conversion(campaign, customer, *, order=None, promotion=None,
                          conversion_type: str,
                          conversion_value=None) -> "CampaignConversion | None":
        """
        Record a conversion event for a campaign customer.

        Idempotent: (campaign, customer, order, conversion_type) unique constraint.
        Returns None if idempotent duplicate.
        """
        from marketing.models import CampaignConversion
        from django.db import IntegrityError

        value = conversion_value or 0
        try:
            with transaction.atomic():
                conversion = CampaignConversion.objects.create(
                    campaign=campaign,
                    customer=customer,
                    order=order,
                    promotion=promotion,
                    conversion_type=conversion_type,
                    conversion_value=value,
                )
        except IntegrityError:
            # Already recorded
            return None

        # Update audience member to CONVERTED
        from marketing.models import CampaignAudienceMember
        CampaignAudienceMember.objects.filter(
            campaign=campaign, customer=customer
        ).update(status=MEMBER_CONVERTED, updated_at=timezone.now())

        # Real-time event
        c_id = campaign.pk
        co_id = campaign.company_id
        transaction.on_commit(lambda: _emit_ws_conversion(WS_CONVERSION_CREATED, c_id, co_id))

        logger.info(
            "CampaignConversionService.record_conversion: campaign=%s customer=%s type=%s",
            campaign.code, customer.customer_number, conversion_type,
        )
        return conversion


def _emit_ws_conversion(event_name, campaign_id, company_id):
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"company_{company_id}",
                {"type": "marketing_event", "event": event_name, "campaign_id": str(campaign_id)},
            )
    except Exception as exc:
        logger.debug("_emit_ws_conversion: %s", exc)
