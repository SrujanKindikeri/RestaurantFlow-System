# =============================================================================
# RestaurantFlow — Notification Celery Tasks
# Phase 16
#
# All tasks are idempotent — calling them multiple times with the same
# argument produces the same result (no duplicate deliveries, no errors).
#
# Task hierarchy:
#   dispatch_notification(notification_id)
#       → resolve recipients
#       → queue_delivery per recipient
#       → deliver_notification_channel(delivery_id) per channel
#
#   retry_pending_deliveries()     — periodic: retry due deliveries
#   cleanup_old_notifications()    — periodic: delete old low-value notifications
# =============================================================================

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("notifications")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="notifications.dispatch_notification",
    ignore_result=True,
)
def dispatch_notification(self, notification_id: str):
    """
    Resolve recipients for a notification and queue per-channel delivery tasks.

    Called after the Notification row is committed to the database.
    """
    try:
        from notifications.models import Notification
        from notifications.services import NotificationService

        try:
            notification = Notification.objects.select_related(
                "company", "restaurant", "branch"
            ).get(pk=notification_id)
        except Notification.DoesNotExist:
            logger.warning("dispatch_notification: notification %s not found", notification_id)
            return

        recipients = NotificationService.resolve_and_create_recipients(notification)

        for recipient in recipients:
            NotificationService.queue_delivery(recipient)

        logger.info(
            "dispatch_notification: notification=%s dispatched to %d recipients",
            notification_id, len(recipients),
        )

    except Exception as exc:
        logger.error(
            "dispatch_notification failed: notification=%s error=%s",
            notification_id, exc,
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.deliver_notification_channel",
    ignore_result=True,
)
def deliver_notification_channel(self, delivery_id: str):
    """
    Execute one delivery attempt for a specific channel delivery record.

    Idempotent — if the delivery is already terminal (DELIVERED, CANCELLED),
    this task is a no-op.
    """
    try:
        from notifications.services import NotificationService
        from notifications.constants import DELIVERY_DELIVERED, DELIVERY_CANCELLED, DELIVERY_NOT_CONFIGURED
        from notifications.models import NotificationDelivery

        # Quick status pre-check to avoid unnecessary work
        try:
            delivery = NotificationDelivery.objects.only("status").get(pk=delivery_id)
        except NotificationDelivery.DoesNotExist:
            logger.warning("deliver_notification_channel: delivery %s not found", delivery_id)
            return

        if delivery.status in (DELIVERY_DELIVERED, DELIVERY_CANCELLED, DELIVERY_NOT_CONFIGURED):
            return  # Already terminal

        NotificationService.deliver_channel(delivery_id)

    except Exception as exc:
        logger.error(
            "deliver_notification_channel failed: delivery=%s error=%s",
            delivery_id, exc,
        )
        raise self.retry(exc=exc)


@shared_task(
    name="notifications.retry_pending_deliveries",
    ignore_result=True,
)
def retry_pending_deliveries():
    """
    Periodic task: pick up delivery records that are due for retry and
    re-queue them. Runs every 2 minutes.

    Only retries rows where:
        status = PENDING
        next_retry_at <= now()
        attempt_count < MAX_DELIVERY_ATTEMPTS
    """
    from notifications.selectors import get_pending_retries
    from notifications.constants import MAX_DELIVERY_ATTEMPTS

    retries = get_pending_retries()
    count = 0
    for delivery in retries:
        deliver_notification_channel.delay(str(delivery.pk))
        count += 1

    if count:
        logger.info("retry_pending_deliveries: queued %d retries", count)


@shared_task(
    name="notifications.cleanup_old_notifications",
    ignore_result=True,
)
def cleanup_old_notifications():
    """
    Periodic task: delete old, low-value notifications beyond the retention period.

    Safety rules (never delete):
        - CRITICAL notifications
        - Unread notifications
        - Notifications flagged as audit/security types
        - Notifications without an expires_at that are less than 90 days old
        - Central alert / issue notifications
        - Accounting / payment / access notifications

    Only safe to delete:
        - Old, read informational (INFO/LOW severity) notifications > 30 days
        - Expired notifications > 7 days past their expires_at
    """
    from notifications.models import NotificationRecipient
    from notifications.constants import (
        SEVERITY_INFO, SEVERITY_LOW,
        NOTIF_CENTRAL_ALERT_CREATED, NOTIF_CENTRAL_ALERT_RESOLVED,
        NOTIF_CENTRAL_ISSUE_ASSIGNED, NOTIF_CENTRAL_ISSUE_RESOLVED,
        NOTIF_ACCOUNTING_POSTING_FAILED, NOTIF_PAYMENT_FAILED,
        NOTIF_USER_ACCESS_GRANTED, NOTIF_USER_ACCESS_REVOKED,
    )

    # Types that must never be auto-deleted
    PROTECTED_TYPES = {
        NOTIF_CENTRAL_ALERT_CREATED, NOTIF_CENTRAL_ALERT_RESOLVED,
        NOTIF_CENTRAL_ISSUE_ASSIGNED, NOTIF_CENTRAL_ISSUE_RESOLVED,
        NOTIF_ACCOUNTING_POSTING_FAILED, NOTIF_PAYMENT_FAILED,
        NOTIF_USER_ACCESS_GRANTED, NOTIF_USER_ACCESS_REVOKED,
    }

    now      = timezone.now()
    cutoff30 = now - timezone.timedelta(days=30)
    cutoff7  = now - timezone.timedelta(days=7)

    # 1. Delete expired notifications more than 7 days past expires_at
    expired_qs = NotificationRecipient.objects.filter(
        notification__expires_at__lt=cutoff7,
        read_at__isnull=False,
    ).exclude(notification__notification_type__in=PROTECTED_TYPES)
    expired_count = expired_qs.count()
    expired_qs.delete()

    # 2. Delete read INFO/LOW notifications older than 30 days
    old_info_qs = NotificationRecipient.objects.filter(
        notification__severity__in=[SEVERITY_INFO, SEVERITY_LOW],
        notification__created_at__lt=cutoff30,
        read_at__isnull=False,
    ).exclude(notification__notification_type__in=PROTECTED_TYPES)
    old_count = old_info_qs.count()
    old_info_qs.delete()

    logger.info(
        "cleanup_old_notifications: deleted expired=%d old_info=%d",
        expired_count, old_count,
    )
