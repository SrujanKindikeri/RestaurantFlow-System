# =============================================================================
# RestaurantFlow — Campaign Scheduling Services
# Phase 18
#
# CampaignSchedulingService — schedule, start, complete campaigns.
#
# Rules:
#   - Uses existing Celery. No second scheduler introduced.
#   - Campaign scheduling is idempotent.
#   - A scheduled campaign must not start twice.
#   - Delegates actual delivery to CampaignDeliveryService.
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone

from accounts import access as acl
from marketing.constants import (
    CAMPAIGN_APPROVED, CAMPAIGN_SCHEDULED, CAMPAIGN_RUNNING,
    CAMPAIGN_PAUSED, CAMPAIGN_COMPLETED, CAMPAIGN_FAILED,
    PERM_CAMPAIGN_SCHEDULE,
)
from marketing.exceptions import MarketingPermissionDenied, CampaignInvalidTransition

logger = logging.getLogger("marketing")


class CampaignSchedulingService:

    @staticmethod
    def schedule(campaign, *, actor) -> "MarketingCampaign":
        """
        Transition a campaign from APPROVED to SCHEDULED.

        If start_at is in the past, move directly to RUNNING.
        Enqueues the Celery task to start the campaign at start_at.
        Idempotent: safe to call multiple times.
        """
        from marketing.campaign_services import CampaignService

        if campaign.status not in (CAMPAIGN_APPROVED, CAMPAIGN_SCHEDULED):
            raise CampaignInvalidTransition(
                f"Campaign must be APPROVED or SCHEDULED to schedule. Current: {campaign.status}"
            )

        now = timezone.now()
        start_at = campaign.start_at or now

        # If start is now or in the past, run immediately
        if start_at <= now:
            return CampaignSchedulingService.start(campaign, actor=actor)

        # Otherwise, schedule for the future
        CampaignService.transition_status(campaign, new_status=CAMPAIGN_SCHEDULED, actor=actor)

        # Enqueue Celery task
        CampaignSchedulingService._enqueue_start_task(campaign, eta=start_at)

        logger.info(
            "CampaignSchedulingService.schedule: campaign=%s scheduled for %s",
            campaign.code, start_at,
        )
        return campaign

    @staticmethod
    def start(campaign, *, actor=None) -> "MarketingCampaign":
        """
        Transition a campaign to RUNNING and enqueue delivery.

        Idempotent: if already RUNNING, return without error.
        """
        from marketing.campaign_services import CampaignService

        if campaign.status == CAMPAIGN_RUNNING:
            logger.info("CampaignSchedulingService.start: already RUNNING campaign=%s", campaign.code)
            return campaign

        if campaign.status not in (CAMPAIGN_APPROVED, CAMPAIGN_SCHEDULED):
            raise CampaignInvalidTransition(
                f"Cannot start campaign in status {campaign.status}."
            )

        CampaignService.transition_status(campaign, new_status=CAMPAIGN_RUNNING, actor=actor)

        # Enqueue batch delivery
        CampaignSchedulingService._enqueue_delivery(campaign)

        return campaign

    @staticmethod
    def complete_if_finished(campaign) -> bool:
        """
        Mark campaign COMPLETED if end_at has passed.
        Returns True if transitioned.
        """
        from marketing.campaign_services import CampaignService
        from marketing.models import MarketingCampaign

        if campaign.status != CAMPAIGN_RUNNING:
            return False

        now = timezone.now()
        if campaign.end_at and now > campaign.end_at:
            try:
                CampaignService.transition_status(
                    campaign, new_status=CAMPAIGN_COMPLETED, actor=None
                )
                return True
            except Exception as exc:
                logger.error(
                    "complete_if_finished: failed for campaign=%s error=%s",
                    campaign.code, exc,
                )
        return False

    @staticmethod
    def _enqueue_start_task(campaign, eta=None):
        """Queue the Celery task to start the campaign."""
        try:
            from marketing.tasks import start_scheduled_campaign
            kwargs = {"campaign_id": str(campaign.pk)}
            if eta:
                start_scheduled_campaign.apply_async(kwargs=kwargs, eta=eta)
            else:
                start_scheduled_campaign.delay(**kwargs)
        except Exception as exc:
            logger.error(
                "_enqueue_start_task: failed for campaign=%s error=%s",
                campaign.code, exc,
            )

    @staticmethod
    def _enqueue_delivery(campaign):
        """Queue the Celery task to send campaign messages."""
        try:
            from marketing.tasks import send_campaign_batch
            send_campaign_batch.delay(campaign_id=str(campaign.pk))
        except Exception as exc:
            logger.error(
                "_enqueue_delivery: failed for campaign=%s error=%s",
                campaign.code, exc,
            )
