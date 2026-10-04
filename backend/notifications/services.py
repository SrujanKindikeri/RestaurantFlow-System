# =============================================================================
# RestaurantFlow — Notification Service
# Phase 16
#
# All business logic for creating and delivering notifications.
#
# Architecture:
#   Business event → create_and_dispatch() → NotificationService.create_notification()
#                  → RecipientResolver.resolve() → queue_delivery() (Celery)
#                  → DeliveryProvider.send() → mark_delivered() / mark_failed()
#
# Transaction boundaries:
#   Notification creation is committed BEFORE Celery tasks are queued.
#   External delivery (email, SMS) happens OUTSIDE any DB transaction.
#   A failed email NEVER rolls back a successful payment/order.
#
# Idempotency:
#   (company, notification_type, source_type, source_id) uniqueness is checked
#   before creating a new Notification. Duplicate events → one notification.
# =============================================================================

import logging
from datetime import timedelta
from typing import Optional

from django.db import transaction
from django.utils import timezone

from notifications.constants import (
    CHANNEL_IN_APP, CHANNEL_WEBSOCKET, CHANNEL_EMAIL,
    CHANNEL_SMS, CHANNEL_WHATSAPP, CHANNEL_TELEGRAM,
    DELIVERY_PENDING, DELIVERY_DELIVERED, DELIVERY_FAILED,
    DELIVERY_NOT_CONFIGURED, DELIVERY_CANCELLED,
    RECIPIENT_PENDING, RECIPIENT_DELIVERED, RECIPIENT_FAILED,
    RECIPIENT_READ, RECIPIENT_ACKNOWLEDGED,
    SEVERITY_INFO, SEVERITY_LOW, SEVERITY_MEDIUM, SEVERITY_HIGH, SEVERITY_CRITICAL,
    SEVERITY_ORDER, MAX_DELIVERY_ATTEMPTS, RETRY_DELAYS_SECONDS,
    COOLDOWN_LOW_STOCK_SECONDS, COOLDOWN_PAYMENT_FAILED_SECONDS,
    COOLDOWN_NOTIFICATION_TYPES, CRITICAL_NOTIFICATION_TYPES,
    CACHE_KEY_COOLDOWN, CACHE_KEY_PROVIDER_FAIL,
    COOLDOWN_PROVIDER_FAILURE_ALERT, PROVIDER_FAILURE_THRESHOLD,
    AUDIT_NOTIFICATION_CREATED, AUDIT_NOTIFICATION_DELIVERED,
    AUDIT_NOTIFICATION_FAILED, AUDIT_NOTIFICATION_READ,
    AUDIT_NOTIFICATION_ACKNOWLEDGED, AUDIT_NOTIFICATION_PREF_UPDATED,
    WS_GROUP_USER,
    NOTIF_NOTIFICATION_PROVIDER_FAILURE,
    SOURCE_SYSTEM,
)
from notifications.exceptions import (
    NotificationNotFoundError,
    NotificationPermissionError,
    NotificationRateLimited,
    NotificationDuplicateError,
)
from notifications.selectors import (
    get_notification_recipient,
    is_channel_enabled_for_user,
    invalidate_unread_count_cache,
    get_templates_for_type_channel,
)
from notifications.validators import render_template, validate_action_url

logger = logging.getLogger("notifications")


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

def _get_provider(channel: str):
    """Return the provider instance for the given channel."""
    from notifications.delivery.in_app    import InAppProvider
    from notifications.delivery.websocket import WebSocketProvider
    from notifications.delivery.email     import EmailProvider
    from notifications.delivery.sms       import SMSProvider
    from notifications.delivery.whatsapp  import WhatsAppProvider
    from notifications.delivery.telegram  import TelegramProvider

    providers = {
        CHANNEL_IN_APP:    InAppProvider,
        CHANNEL_WEBSOCKET: WebSocketProvider,
        CHANNEL_EMAIL:     EmailProvider,
        CHANNEL_SMS:       SMSProvider,
        CHANNEL_WHATSAPP:  WhatsAppProvider,
        CHANNEL_TELEGRAM:  TelegramProvider,
    }
    cls = providers.get(channel)
    return cls() if cls else None


# ---------------------------------------------------------------------------
# Channel priority mapping by severity
# ---------------------------------------------------------------------------

def _channels_for_severity(severity: str) -> list[str]:
    """Return which channels should be used based on notification severity."""
    if severity in (SEVERITY_INFO, SEVERITY_LOW):
        return [CHANNEL_IN_APP]
    elif severity == SEVERITY_MEDIUM:
        return [CHANNEL_IN_APP, CHANNEL_WEBSOCKET]
    elif severity == SEVERITY_HIGH:
        return [CHANNEL_IN_APP, CHANNEL_WEBSOCKET, CHANNEL_EMAIL]
    else:  # CRITICAL
        return [CHANNEL_IN_APP, CHANNEL_WEBSOCKET, CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_WHATSAPP, CHANNEL_TELEGRAM]


# ---------------------------------------------------------------------------
# Cooldown helpers
# ---------------------------------------------------------------------------

def _cooldown_key(notification_type: str, company_id, source_id: str = "") -> str:
    scope = f"{company_id}:{source_id}" if source_id else str(company_id)
    return CACHE_KEY_COOLDOWN.format(notif_type=notification_type, scope_key=scope)


def _is_within_cooldown(notification_type: str, company_id, source_id: str = "") -> bool:
    """Returns True if this notification is suppressed by cooldown."""
    if notification_type in CRITICAL_NOTIFICATION_TYPES:
        return False  # Never suppress critical
    if notification_type not in COOLDOWN_NOTIFICATION_TYPES:
        return False

    from django.core.cache import cache
    key = _cooldown_key(notification_type, company_id, source_id)
    return bool(cache.get(key))


def _set_cooldown(notification_type: str, company_id, source_id: str = ""):
    """Set the cooldown window for this notification type."""
    from django.core.cache import cache
    from notifications.constants import (
        NOTIF_INVENTORY_LOW_STOCK, NOTIF_INVENTORY_OUT_OF_STOCK,
        NOTIF_PAYMENT_FAILED, NOTIF_KITCHEN_BACKLOG, NOTIF_KITCHEN_ORDER_DELAYED,
    )
    ttl_map = {
        NOTIF_INVENTORY_LOW_STOCK:    COOLDOWN_LOW_STOCK_SECONDS,
        NOTIF_INVENTORY_OUT_OF_STOCK: COOLDOWN_LOW_STOCK_SECONDS,
        NOTIF_PAYMENT_FAILED:         COOLDOWN_PAYMENT_FAILED_SECONDS,
        NOTIF_KITCHEN_BACKLOG:        COOLDOWN_PAYMENT_FAILED_SECONDS,
        NOTIF_KITCHEN_ORDER_DELAYED:  COOLDOWN_PAYMENT_FAILED_SECONDS,
    }
    ttl = ttl_map.get(notification_type, 300)
    key = _cooldown_key(notification_type, company_id, source_id)
    cache.set(key, True, ttl)


# ---------------------------------------------------------------------------
# Core NotificationService
# ---------------------------------------------------------------------------

class NotificationService:

    @staticmethod
    def create_notification(
        *,
        company,
        notification_type: str,
        severity: str,
        title: str,
        message: str,
        source_type: str,
        source_id: str = "",
        restaurant=None,
        branch=None,
        action_url: str = "",
        metadata: dict = None,
        expires_at=None,
        bypass_cooldown: bool = False,
    ) -> Optional[object]:
        """
        Create a Notification and enqueue delivery to resolved recipients.

        Returns:
            The Notification instance if created (or existing duplicate).
            None if suppressed by cooldown or rate limiting.

        Idempotency:
            An existing notification with the same
            (company, notification_type, source_type, source_id)
            created within the last 24 hours is returned without creating a duplicate.

        Transaction:
            Notification row is committed, then Celery tasks are queued
            via transaction.on_commit() to guarantee no task fires before
            the row is visible.
        """
        from notifications.models import Notification

        if metadata is None:
            metadata = {}

        # Validate action URL safety
        action_url = validate_action_url(action_url)

        # Cooldown check (non-critical informational spam prevention)
        if not bypass_cooldown and _is_within_cooldown(
            notification_type, company.pk, source_id
        ):
            logger.debug(
                "NotificationService.create_notification: suppressed by cooldown "
                "type=%s company=%s source_id=%s",
                notification_type, company.pk, source_id,
            )
            return None

        # Idempotency — check for recent duplicate
        if source_id:
            cutoff = timezone.now() - timedelta(hours=24)
            existing = Notification.objects.filter(
                company=company,
                notification_type=notification_type,
                source_type=source_type,
                source_id=source_id,
                created_at__gte=cutoff,
            ).first()
            if existing:
                logger.debug(
                    "NotificationService.create_notification: idempotent duplicate "
                    "type=%s source_id=%s existing=%s",
                    notification_type, source_id, existing.pk,
                )
                return existing

        with transaction.atomic():
            notification = Notification.objects.create(
                company=company,
                restaurant=restaurant,
                branch=branch,
                notification_type=notification_type,
                severity=severity,
                title=title,
                message=message,
                source_type=source_type,
                source_id=source_id,
                action_url=action_url,
                metadata=metadata,
                expires_at=expires_at,
            )
            notif_id = notification.pk

            # Set cooldown after successful creation
            _set_cooldown(notification_type, company.pk, source_id)

            # Queue recipient resolution + delivery after commit
            transaction.on_commit(
                lambda: NotificationService._dispatch_after_commit(notif_id)
            )

        logger.info(
            "NotificationService.create_notification: created type=%s severity=%s "
            "company=%s notification=%s",
            notification_type, severity, company.pk, notification.pk,
        )
        return notification

    @staticmethod
    def _dispatch_after_commit(notification_id):
        """
        Called after the notification is committed.
        Resolves recipients and queues delivery tasks.
        Errors here must NOT propagate to the caller.
        """
        try:
            from notifications.tasks import dispatch_notification
            dispatch_notification.delay(str(notification_id))
        except Exception as exc:
            logger.error(
                "NotificationService._dispatch_after_commit failed: "
                "notification=%s error=%s",
                notification_id, exc,
            )

    @staticmethod
    def resolve_and_create_recipients(notification) -> list:
        """
        Run RecipientResolver for the notification and persist NotificationRecipient rows.
        Returns list of created recipient instances.
        """
        from notifications.models import NotificationRecipient
        from notifications.recipient_resolver import RecipientResolver

        resolver = RecipientResolver(notification)
        users    = resolver.resolve()

        recipients = []
        for user in users:
            recipient, created = NotificationRecipient.objects.get_or_create(
                notification=notification,
                user=user,
                defaults={"delivery_status": RECIPIENT_PENDING},
            )
            recipients.append(recipient)

        logger.debug(
            "NotificationService.resolve_and_create_recipients: "
            "notification=%s resolved=%d created=%d",
            notification.pk, len(users), sum(1 for r in recipients),
        )
        return recipients

    @staticmethod
    def queue_delivery(recipient, channels: list[str] = None):
        """
        Create NotificationDelivery rows for each channel and queue Celery tasks.
        Respects user preferences.
        """
        from notifications.models import NotificationDelivery
        from notifications.tasks import deliver_notification_channel

        notification = recipient.notification
        severity     = notification.severity
        user         = recipient.user

        if channels is None:
            channels = _channels_for_severity(severity)

        for channel in channels:
            # Check user preference
            if not is_channel_enabled_for_user(user, notification.notification_type, channel):
                logger.debug(
                    "queue_delivery: channel=%s disabled by user preference "
                    "user=%s notification=%s",
                    channel, user.pk, notification.pk,
                )
                continue

            # Avoid creating duplicate delivery records for the same attempt
            existing = NotificationDelivery.objects.filter(
                notification=notification,
                recipient=recipient,
                channel=channel,
            ).exclude(status__in=[DELIVERY_FAILED, DELIVERY_CANCELLED]).first()

            if existing:
                continue  # already queued or delivered

            delivery = NotificationDelivery.objects.create(
                notification=notification,
                recipient=recipient,
                channel=channel,
                status=DELIVERY_PENDING,
                queued_at=timezone.now(),
            )

            # For instant channels (in-app, websocket) fire inline via Celery
            deliver_notification_channel.delay(str(delivery.pk))

    @staticmethod
    def deliver_channel(delivery_id: str):
        """
        Execute one delivery attempt for a NotificationDelivery row.
        Called by the Celery task.
        """
        from notifications.models import NotificationDelivery
        from notifications.delivery.base import DeliveryPayload

        try:
            delivery = NotificationDelivery.objects.select_related(
                "notification", "notification__company",
                "recipient", "recipient__user"
            ).get(pk=delivery_id)
        except NotificationDelivery.DoesNotExist:
            logger.warning("deliver_channel: delivery %s not found", delivery_id)
            return

        if delivery.status in (DELIVERY_DELIVERED, DELIVERY_CANCELLED):
            return  # Already terminal

        notification = delivery.notification
        user         = delivery.recipient.user
        channel      = delivery.channel

        # Build payload
        subject, body = NotificationService._render_content(notification, channel)
        payload = DeliveryPayload(
            recipient_user=user,
            notification=notification,
            subject=subject,
            body=body,
            metadata=notification.metadata,
        )

        provider = _get_provider(channel)
        if provider is None:
            NotificationService.mark_failed(
                delivery, f"No provider registered for channel: {channel}"
            )
            return

        delivery.attempt_count += 1
        delivery.save(update_fields=["attempt_count", "updated_at"])

        result = provider.send(payload)

        if result.not_configured:
            NotificationService._mark_not_configured(delivery, result.failure_reason)
        elif result.success:
            NotificationService.mark_delivered(delivery, result.provider_message_id)
        else:
            if delivery.attempt_count >= MAX_DELIVERY_ATTEMPTS:
                NotificationService.mark_failed(delivery, result.failure_reason)
            else:
                # Schedule retry
                delay = RETRY_DELAYS_SECONDS[
                    min(delivery.attempt_count, len(RETRY_DELAYS_SECONDS) - 1)
                ]
                delivery.status       = DELIVERY_PENDING
                delivery.next_retry_at = timezone.now() + timedelta(seconds=delay)
                delivery.failure_reason = result.failure_reason
                delivery.save(update_fields=["status", "next_retry_at", "failure_reason", "updated_at"])

        # Track provider failures for Central Control alerting
        if not result.success and not result.not_configured and channel not in (CHANNEL_IN_APP, CHANNEL_WEBSOCKET):
            NotificationService._track_provider_failure(channel, notification.company)

    @staticmethod
    def _render_content(notification, channel: str) -> tuple[str, str]:
        """Render subject + body using a template if available, else raw notification fields."""
        template = get_templates_for_type_channel(
            notification.notification_type, channel, notification.company
        )
        if not template:
            return notification.title, notification.message

        context = {
            "title":           notification.title,
            "branch_name":     notification.branch.name if notification.branch else "",
            "restaurant_name": notification.restaurant.name if notification.restaurant else "",
            "company_name":    notification.company.name,
            **notification.metadata,
        }
        try:
            subject = render_template(template.subject_template or "", context)
            body    = render_template(template.body_template, context)
            return subject or notification.title, body or notification.message
        except Exception as exc:
            logger.warning(
                "_render_content: template render error notification=%s channel=%s: %s",
                notification.pk, channel, exc,
            )
            return notification.title, notification.message

    @staticmethod
    def mark_delivered(delivery, provider_message_id: str = ""):
        from notifications.constants import DELIVERY_DELIVERED
        delivery.status             = DELIVERY_DELIVERED
        delivery.sent_at            = timezone.now()
        delivery.provider_message_id = provider_message_id
        delivery.next_retry_at      = None
        delivery.save(update_fields=[
            "status", "sent_at", "provider_message_id", "next_retry_at", "updated_at"
        ])
        # Update recipient status to DELIVERED for in-app channel
        if delivery.channel == CHANNEL_IN_APP:
            NotificationService._update_recipient_delivered(delivery.recipient)

    @staticmethod
    def _mark_not_configured(delivery, reason: str):
        delivery.status         = DELIVERY_NOT_CONFIGURED
        delivery.failure_reason = reason
        delivery.failed_at      = timezone.now()
        delivery.next_retry_at  = None
        delivery.save(update_fields=["status", "failure_reason", "failed_at", "next_retry_at", "updated_at"])

    @staticmethod
    def mark_failed(delivery, reason: str):
        delivery.status         = DELIVERY_FAILED
        delivery.failure_reason = reason
        delivery.failed_at      = timezone.now()
        delivery.next_retry_at  = None
        delivery.save(update_fields=["status", "failure_reason", "failed_at", "next_retry_at", "updated_at"])
        # Update recipient state
        NotificationService._update_recipient_failed(delivery.recipient)

    @staticmethod
    def _update_recipient_delivered(recipient):
        if recipient.delivery_status == RECIPIENT_PENDING:
            recipient.delivery_status = RECIPIENT_DELIVERED
            recipient.delivered_at    = timezone.now()
            recipient.save(update_fields=["delivery_status", "delivered_at", "updated_at"])
        invalidate_unread_count_cache(recipient.user)

    @staticmethod
    def _update_recipient_failed(recipient):
        # Only mark FAILED if no delivery channel succeeded
        from notifications.models import NotificationDelivery
        has_success = NotificationDelivery.objects.filter(
            recipient=recipient,
            status=DELIVERY_DELIVERED,
        ).exists()
        if not has_success and recipient.delivery_status == RECIPIENT_PENDING:
            recipient.delivery_status = RECIPIENT_FAILED
            recipient.failed_at       = timezone.now()
            recipient.save(update_fields=["delivery_status", "failed_at", "updated_at"])

    @staticmethod
    def mark_read(notification_id: str, user) -> object:
        """
        Mark a notification as read for the given user.
        Returns the updated NotificationRecipient.
        """
        recipient = get_notification_recipient(notification_id, user)
        if not recipient:
            raise NotificationNotFoundError(
                f"Notification {notification_id} not found for user {user.pk}."
            )

        if recipient.read_at is None:
            recipient.read_at         = timezone.now()
            recipient.delivery_status = RECIPIENT_READ
            recipient.save(update_fields=["read_at", "delivery_status", "updated_at"])
            invalidate_unread_count_cache(user)

            # Push ws update
            NotificationService._push_ws_read_event(user, notification_id)

        return recipient

    @staticmethod
    def mark_all_read(user):
        """Mark all unread notifications as read for this user."""
        from notifications.models import NotificationRecipient
        now = timezone.now()
        updated = NotificationRecipient.objects.filter(
            user=user, read_at__isnull=True
        ).update(read_at=now, delivery_status=RECIPIENT_READ, updated_at=now)
        invalidate_unread_count_cache(user)
        logger.info("mark_all_read: user=%s updated=%d", user.pk, updated)
        return updated

    @staticmethod
    def acknowledge(notification_id: str, user) -> object:
        """
        Acknowledge a notification for the given user.
        Returns the updated NotificationRecipient.
        """
        recipient = get_notification_recipient(notification_id, user)
        if not recipient:
            raise NotificationNotFoundError(
                f"Notification {notification_id} not found for user {user.pk}."
            )

        if recipient.acknowledged_at is None:
            now = timezone.now()
            recipient.acknowledged_at = now
            recipient.delivery_status  = RECIPIENT_ACKNOWLEDGED
            if recipient.read_at is None:
                recipient.read_at = now
            recipient.save(update_fields=[
                "acknowledged_at", "delivery_status", "read_at", "updated_at"
            ])
            invalidate_unread_count_cache(user)

        return recipient

    @staticmethod
    def retry_delivery(delivery_id: str):
        """Manually trigger a retry for a specific delivery record."""
        from notifications.models import NotificationDelivery
        from notifications.constants import DELIVERY_FAILED, DELIVERY_PENDING
        try:
            delivery = NotificationDelivery.objects.get(pk=delivery_id)
        except NotificationDelivery.DoesNotExist:
            raise NotificationNotFoundError(f"Delivery {delivery_id} not found.")

        if delivery.attempt_count >= MAX_DELIVERY_ATTEMPTS:
            logger.warning(
                "retry_delivery: delivery=%s already at max attempts (%d)",
                delivery_id, MAX_DELIVERY_ATTEMPTS,
            )
            return

        delivery.status        = DELIVERY_PENDING
        delivery.next_retry_at = timezone.now()
        delivery.save(update_fields=["status", "next_retry_at", "updated_at"])

        from notifications.tasks import deliver_notification_channel
        deliver_notification_channel.delay(str(delivery_id))

    # -------------------------------------------------------------------------
    # Provider failure tracking (Central Control integration)
    # -------------------------------------------------------------------------

    @staticmethod
    def _track_provider_failure(channel: str, company):
        """
        Track external provider failures. After PROVIDER_FAILURE_THRESHOLD
        failures within the cooldown window, create a Central Control alert.
        """
        from django.core.cache import cache

        key   = CACHE_KEY_PROVIDER_FAIL.format(channel=channel, company_id=str(company.pk))
        count = cache.get(key, 0) + 1
        cache.set(key, count, COOLDOWN_PROVIDER_FAILURE_ALERT)

        if count >= PROVIDER_FAILURE_THRESHOLD:
            # Reset counter so we don't spam
            cache.delete(key)
            NotificationService._create_provider_failure_alert(channel, company, count)

    @staticmethod
    def _create_provider_failure_alert(channel: str, company, failure_count: int):
        """Create a notification about provider failures (routed to Central Control)."""
        try:
            NotificationService.create_notification(
                company=company,
                notification_type=NOTIF_NOTIFICATION_PROVIDER_FAILURE,
                severity=SEVERITY_HIGH,
                title=f"Notification Provider Failure: {channel}",
                message=(
                    f"{failure_count} delivery failures detected for the "
                    f"{channel} channel in the last {COOLDOWN_PROVIDER_FAILURE_ALERT // 60} minutes."
                ),
                source_type=SOURCE_SYSTEM,
                source_id=f"provider_failure_{channel}_{company.pk}",
                metadata={
                    "channel":       channel,
                    "failure_count": failure_count,
                    "provider_name": channel,
                },
                bypass_cooldown=True,
            )
        except Exception as exc:
            logger.error("_create_provider_failure_alert failed: %s", exc)

    # -------------------------------------------------------------------------
    # WebSocket push helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _push_ws_read_event(user, notification_id: str):
        """Push a notification.read event to the user's WebSocket group."""
        try:
            from asgiref.sync import async_to_sync
            from channels.layers import get_channel_layer
            from notifications.constants import WS_NOTIFICATION_READ

            channel_layer = get_channel_layer()
            if channel_layer is None:
                return

            group = WS_GROUP_USER.format(user_id=str(user.pk))
            async_to_sync(channel_layer.group_send)(
                group,
                {
                    "type": "notification_event",
                    "payload": {
                        "type":            WS_NOTIFICATION_READ,
                        "notification_id": str(notification_id),
                    },
                },
            )
        except Exception as exc:
            logger.debug("_push_ws_read_event failed (non-critical): %s", exc)


# ---------------------------------------------------------------------------
# Convenience entry-point used by event handlers
# ---------------------------------------------------------------------------

def create_and_dispatch(
    *,
    company,
    notification_type: str,
    severity: str,
    title: str,
    message: str,
    source_type: str,
    source_id: str = "",
    restaurant=None,
    branch=None,
    action_url: str = "",
    metadata: dict = None,
    expires_at=None,
    bypass_cooldown: bool = False,
) -> Optional[object]:
    """
    Top-level convenience function for creating + dispatching a notification.

    Called from event_handlers.py (signals) using transaction.on_commit() so
    it always runs AFTER the triggering business transaction commits.
    """
    try:
        return NotificationService.create_notification(
            company=company,
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            source_type=source_type,
            source_id=source_id,
            restaurant=restaurant,
            branch=branch,
            action_url=action_url,
            metadata=metadata or {},
            expires_at=expires_at,
            bypass_cooldown=bypass_cooldown,
        )
    except Exception as exc:
        logger.error(
            "create_and_dispatch failed: type=%s source_id=%s error=%s",
            notification_type, source_id, exc,
        )
        return None
