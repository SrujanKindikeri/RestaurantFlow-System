# =============================================================================
# RestaurantFlow — Marketing Celery Tasks
# Phase 18
#
# All tasks are idempotent — safe to retry without duplicate side effects.
# Uses existing Celery (config/celery.py). No second scheduler.
#
# Tasks:
#   generate_campaign_audience      — resolve audience members asynchronously
#   start_scheduled_campaign        — transition SCHEDULED → RUNNING
#   send_campaign_batch             — send messages to eligible audience members
#   update_campaign_delivery_status — sync delivery status from notification system
#   calculate_campaign_metrics      — update analytics cache
#   expire_campaigns                — mark expired RUNNING campaigns COMPLETED
#   expire_promotions               — deactivate expired promotions
#   cleanup_campaign_data_if_configured — optional housekeeping
# =============================================================================

import logging
from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("marketing")


@shared_task(name="marketing.generate_campaign_audience", bind=True, max_retries=3)
def generate_campaign_audience(self, campaign_id: str, audience_id: str):
    """
    Asynchronously resolve audience members for a campaign.
    Idempotent: get_or_create on CampaignAudienceMember.
    """
    try:
        from marketing.models import MarketingCampaign, CampaignAudience
        from marketing.audience_services import CampaignAudienceService

        campaign = MarketingCampaign.objects.select_related(
            "company", "restaurant"
        ).get(pk=campaign_id)
        audience = CampaignAudience.objects.get(pk=audience_id, campaign=campaign)

        count = CampaignAudienceService.generate_audience_members(campaign, audience)
        logger.info(
            "generate_campaign_audience: campaign=%s eligible=%d",
            campaign.code, count,
        )
        return {"status": "ok", "eligible_count": count}

    except Exception as exc:
        logger.error(
            "generate_campaign_audience: failed campaign=%s error=%s",
            campaign_id, exc,
        )
        raise self.retry(exc=exc, countdown=60)


@shared_task(name="marketing.start_scheduled_campaign", bind=True, max_retries=3)
def start_scheduled_campaign(campaign_id: str):
    """
    Transition a SCHEDULED campaign to RUNNING.
    Idempotent: checks current status before transitioning.
    """
    try:
        from marketing.models import MarketingCampaign
        from marketing.constants import CAMPAIGN_SCHEDULED
        from marketing.scheduling_services import CampaignSchedulingService

        campaign = MarketingCampaign.objects.select_related(
            "company", "restaurant"
        ).get(pk=campaign_id)

        if campaign.status != CAMPAIGN_SCHEDULED:
            logger.info(
                "start_scheduled_campaign: campaign=%s already in status=%s, skipping",
                campaign.code, campaign.status,
            )
            return {"status": "skipped", "reason": f"already {campaign.status}"}

        CampaignSchedulingService.start(campaign, actor=None)
        logger.info("start_scheduled_campaign: started campaign=%s", campaign.code)
        return {"status": "ok"}

    except Exception as exc:
        logger.error("start_scheduled_campaign: error campaign=%s %s", campaign_id, exc)
        raise


@shared_task(name="marketing.send_campaign_batch", bind=True, max_retries=3)
def send_campaign_batch(self, campaign_id: str, batch_size: int = 50):
    """
    Send campaign messages to all ELIGIBLE audience members in batches.

    Idempotent: CampaignDeliveryService.create_delivery() is idempotent.
    A paused campaign will not send any new messages.
    """
    try:
        from marketing.models import (
            MarketingCampaign, CampaignAudienceMember, CampaignChannel, CampaignMessage
        )
        from marketing.constants import (
            CAMPAIGN_RUNNING, MEMBER_ELIGIBLE, MEMBER_CONTACTED,
        )
        from marketing.tracking_services import CampaignDeliveryService
        from marketing.validators import render_message

        campaign = MarketingCampaign.objects.select_related(
            "company", "restaurant", "branch"
        ).get(pk=campaign_id)

        if campaign.status != CAMPAIGN_RUNNING:
            logger.info(
                "send_campaign_batch: campaign=%s not RUNNING (status=%s), skipping",
                campaign.code, campaign.status,
            )
            return {"status": "skipped"}

        # Get enabled channels
        channels = list(
            CampaignChannel.objects.filter(campaign=campaign, enabled=True)
        )
        if not channels:
            logger.info("send_campaign_batch: campaign=%s has no enabled channels", campaign.code)
            return {"status": "no_channels"}

        # Get eligible members not yet contacted
        members = CampaignAudienceMember.objects.filter(
            campaign=campaign,
            status=MEMBER_ELIGIBLE,
        ).select_related("customer").iterator(chunk_size=batch_size)

        sent_count = 0
        failed_count = 0

        for member in members:
            customer = member.customer
            if not customer.is_active or customer.is_blocked:
                continue

            for ch in channels:
                # Build message context
                context = {
                    "customer_name": customer.effective_display_name,
                    "restaurant_name": campaign.restaurant.name if campaign.restaurant else "",
                    "promotion_code": "",
                }

                # Get message body for this channel
                msg_obj = CampaignMessage.objects.filter(
                    campaign=campaign, channel=ch.channel
                ).first()
                if not msg_obj:
                    continue

                body = render_message(msg_obj.body, context)
                subject = render_message(msg_obj.subject or campaign.name, context)

                delivery = CampaignDeliveryService.create_delivery(
                    campaign, customer, ch.channel
                )
                if delivery:
                    try:
                        CampaignDeliveryService.send_via_notification_service(
                            delivery, body, subject
                        )
                        sent_count += 1
                    except Exception as send_exc:
                        logger.error(
                            "send_campaign_batch: send failed customer=%s channel=%s error=%s",
                            customer.pk, ch.channel, send_exc,
                        )
                        failed_count += 1

        logger.info(
            "send_campaign_batch: campaign=%s sent=%d failed=%d",
            campaign.code, sent_count, failed_count,
        )
        return {"status": "ok", "sent": sent_count, "failed": failed_count}

    except Exception as exc:
        logger.error("send_campaign_batch: error campaign=%s %s", campaign_id, exc)
        raise self.retry(exc=exc, countdown=120)


@shared_task(name="marketing.update_campaign_delivery_status")
def update_campaign_delivery_status():
    """
    Sync CampaignDelivery status from NotificationDelivery records.

    Called periodically to reflect actual delivery outcomes from Phase 16.
    """
    try:
        from marketing.models import CampaignDelivery
        from marketing.constants import DELIVERY_SENT, DELIVERY_DELIVERED, DELIVERY_FAILED
        from notifications.models import Notification
        from notifications.constants import DELIVERY_DELIVERED as N_DELIVERED, DELIVERY_FAILED as N_FAILED

        # Find sent deliveries with notification_id that haven't been updated
        sent_deliveries = CampaignDelivery.objects.filter(
            status=DELIVERY_SENT,
            notification_id__isnull=False,
        ).values_list("id", "notification_id")[:500]

        updated = 0
        for delivery_id, notif_id in sent_deliveries:
            try:
                notif = Notification.objects.get(pk=notif_id)
                # Check if any delivery record is DELIVERED
                from notifications.models import NotificationDelivery
                delivered = NotificationDelivery.objects.filter(
                    notification=notif,
                    status=N_DELIVERED,
                ).exists()
                failed = NotificationDelivery.objects.filter(
                    notification=notif,
                    status=N_FAILED,
                ).count()
                total = NotificationDelivery.objects.filter(notification=notif).count()

                if delivered:
                    CampaignDelivery.objects.filter(pk=delivery_id).update(
                        status=DELIVERY_DELIVERED,
                        delivered_at=timezone.now(),
                        updated_at=timezone.now(),
                    )
                    updated += 1
                elif total > 0 and failed == total:
                    CampaignDelivery.objects.filter(pk=delivery_id).update(
                        status=DELIVERY_FAILED,
                        failed_at=timezone.now(),
                        updated_at=timezone.now(),
                    )
                    updated += 1
            except Exception:
                pass

        logger.info("update_campaign_delivery_status: updated=%d", updated)
        return {"updated": updated}

    except Exception as exc:
        logger.error("update_campaign_delivery_status: error %s", exc)


@shared_task(name="marketing.calculate_campaign_metrics")
def calculate_campaign_metrics():
    """
    Recalculate and cache campaign analytics for running campaigns.
    """
    try:
        from marketing.models import MarketingCampaign
        from marketing.constants import CAMPAIGN_RUNNING
        from marketing.selectors import get_campaign_analytics

        running = MarketingCampaign.objects.filter(status=CAMPAIGN_RUNNING)
        for campaign in running:
            try:
                get_campaign_analytics(campaign)
            except Exception as exc:
                logger.warning("calculate_campaign_metrics: campaign=%s error=%s", campaign.code, exc)

        logger.info("calculate_campaign_metrics: processed %d running campaigns", running.count())
    except Exception as exc:
        logger.error("calculate_campaign_metrics: error %s", exc)


@shared_task(name="marketing.expire_campaigns")
def expire_campaigns():
    """
    Mark RUNNING campaigns as COMPLETED if their end_at has passed.
    Idempotent: checks status before updating.
    """
    try:
        from marketing.selectors import get_running_campaigns_expired
        from marketing.scheduling_services import CampaignSchedulingService

        expired = get_running_campaigns_expired()
        count = 0
        for campaign in expired:
            try:
                transitioned = CampaignSchedulingService.complete_if_finished(campaign)
                if transitioned:
                    count += 1
            except Exception as exc:
                logger.error("expire_campaigns: failed for campaign=%s error=%s", campaign.code, exc)

        logger.info("expire_campaigns: completed %d campaigns", count)
        return {"completed": count}
    except Exception as exc:
        logger.error("expire_campaigns: error %s", exc)


@shared_task(name="marketing.expire_promotions")
def expire_promotions():
    """
    Deactivate promotions whose end_at has passed.
    Idempotent: only touches active promotions.
    """
    try:
        from marketing.models import Promotion
        now = timezone.now()
        expired = Promotion.objects.filter(
            is_active=True,
            end_at__isnull=False,
            end_at__lt=now,
        )
        count = expired.update(is_active=False, updated_at=now)
        if count:
            logger.info("expire_promotions: deactivated %d promotions", count)
        return {"deactivated": count}
    except Exception as exc:
        logger.error("expire_promotions: error %s", exc)


@shared_task(name="marketing.cleanup_campaign_data_if_configured")
def cleanup_campaign_data_if_configured():
    """
    Optional cleanup of old campaign event/delivery records.

    Only runs if MARKETING_DATA_RETENTION_DAYS is configured.
    Preserves: campaigns, promotions, usages, conversions (never deleted).
    Cleans: CampaignEvent records older than retention window.
    """
    try:
        from django.conf import settings
        retention_days = getattr(settings, "MARKETING_DATA_RETENTION_DAYS", None)
        if not retention_days:
            return {"skipped": "no retention policy configured"}

        import datetime
        from marketing.models import CampaignEvent
        cutoff = timezone.now() - datetime.timedelta(days=int(retention_days))
        deleted, _ = CampaignEvent.objects.filter(created_at__lt=cutoff).delete()
        logger.info("cleanup_campaign_data: deleted %d old events", deleted)
        return {"deleted_events": deleted}
    except Exception as exc:
        logger.error("cleanup_campaign_data: error %s", exc)
