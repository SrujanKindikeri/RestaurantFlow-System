# =============================================================================
# RestaurantFlow — Notifications Selectors
# Phase 16
#
# Pure read-only queryset helpers.  Views and serializers call these;
# no business logic lives here.
# =============================================================================

from django.db.models import QuerySet
from django.utils import timezone


def get_notification_recipients_for_user(
    user,
    *,
    unread_only: bool = False,
    notification_type: str = None,
    severity: str = None,
    date_from=None,
    date_to=None,
    include_expired: bool = False,
) -> QuerySet:
    """
    Return NotificationRecipient queryset for the given user.

    Filters:
        unread_only       — exclude already-read notifications
        notification_type — exact match on notification.notification_type
        severity          — exact match on notification.severity
        date_from/date_to — filter on notification.created_at
        include_expired   — include notifications past their expires_at
    """
    from notifications.models import NotificationRecipient

    qs = (
        NotificationRecipient.objects
        .filter(user=user)
        .select_related("notification", "notification__company",
                        "notification__restaurant", "notification__branch")
        .order_by("-notification__created_at")
    )

    if unread_only:
        qs = qs.filter(read_at__isnull=True)

    if notification_type:
        qs = qs.filter(notification__notification_type=notification_type)

    if severity:
        qs = qs.filter(notification__severity=severity)

    if date_from:
        qs = qs.filter(notification__created_at__gte=date_from)

    if date_to:
        qs = qs.filter(notification__created_at__lte=date_to)

    if not include_expired:
        qs = qs.filter(
            notification__expires_at__isnull=True
        ) | NotificationRecipient.objects.filter(
            user=user,
            notification__expires_at__gt=timezone.now(),
        )
        # Use a cleaner approach with Q objects
        from django.db.models import Q
        qs = (
            NotificationRecipient.objects
            .filter(user=user)
            .filter(
                Q(notification__expires_at__isnull=True) |
                Q(notification__expires_at__gt=timezone.now())
            )
            .select_related("notification", "notification__company",
                            "notification__restaurant", "notification__branch")
            .order_by("-notification__created_at")
        )
        if unread_only:
            qs = qs.filter(read_at__isnull=True)
        if notification_type:
            qs = qs.filter(notification__notification_type=notification_type)
        if severity:
            qs = qs.filter(notification__severity=severity)
        if date_from:
            qs = qs.filter(notification__created_at__gte=date_from)
        if date_to:
            qs = qs.filter(notification__created_at__lte=date_to)

    return qs


def get_unread_count_for_user(user) -> int:
    """Return the count of unread notifications for a user (cache-aware)."""
    from django.core.cache import cache
    from notifications.constants import CACHE_KEY_UNREAD_COUNT, CACHE_TTL_UNREAD_COUNT

    cache_key = CACHE_KEY_UNREAD_COUNT.format(user_id=user.pk)
    count = cache.get(cache_key)
    if count is None:
        from notifications.models import NotificationRecipient
        from django.db.models import Q
        count = NotificationRecipient.objects.filter(
            user=user,
            read_at__isnull=True,
        ).filter(
            Q(notification__expires_at__isnull=True) |
            Q(notification__expires_at__gt=timezone.now())
        ).count()
        cache.set(cache_key, count, CACHE_TTL_UNREAD_COUNT)
    return count


def invalidate_unread_count_cache(user):
    """Invalidate the unread count cache for a user after read/new notification."""
    from django.core.cache import cache
    from notifications.constants import CACHE_KEY_UNREAD_COUNT
    cache.delete(CACHE_KEY_UNREAD_COUNT.format(user_id=user.pk))


def get_notification_recipient(notification_id: str, user) -> object:
    """
    Get a single NotificationRecipient for the given notification + user.
    Returns None if not found.
    """
    from notifications.models import NotificationRecipient
    try:
        return NotificationRecipient.objects.select_related(
            "notification", "notification__company"
        ).get(notification_id=notification_id, user=user)
    except NotificationRecipient.DoesNotExist:
        return None


def get_user_preferences(user) -> QuerySet:
    """Return all NotificationPreference rows for a user."""
    from notifications.models import NotificationPreference
    return NotificationPreference.objects.filter(user=user).order_by(
        "notification_type", "channel"
    )


def is_channel_enabled_for_user(user, notification_type: str, channel: str) -> bool:
    """
    Check whether a specific channel is enabled for a user for a notification type.
    Falls back to DEFAULT_CHANNEL_PREFS if no explicit preference row exists.
    """
    from notifications.models import NotificationPreference
    from notifications.constants import DEFAULT_CHANNEL_PREFS

    try:
        pref = NotificationPreference.objects.get(
            user=user,
            notification_type=notification_type,
            channel=channel,
        )
        return pref.enabled
    except NotificationPreference.DoesNotExist:
        # Fall back to system defaults
        defaults = DEFAULT_CHANNEL_PREFS.get(notification_type, {})
        return defaults.get(channel, False)


def get_deliveries_for_admin(
    *,
    company,
    channel: str = None,
    status: str = None,
    date_from=None,
    date_to=None,
) -> QuerySet:
    """
    Return NotificationDelivery queryset scoped to a company.
    Used by admin delivery monitoring endpoints.
    """
    from notifications.models import NotificationDelivery
    qs = (
        NotificationDelivery.objects
        .filter(notification__company=company)
        .select_related(
            "notification", "recipient", "recipient__user"
        )
        .order_by("-created_at")
    )
    if channel:
        qs = qs.filter(channel=channel)
    if status:
        qs = qs.filter(status=status)
    if date_from:
        qs = qs.filter(created_at__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__lte=date_to)
    return qs


def get_pending_retries() -> QuerySet:
    """
    Return NotificationDelivery rows that are due for retry.
    Used by the Celery retry task.
    """
    from notifications.models import NotificationDelivery
    from notifications.constants import DELIVERY_PENDING, DELIVERY_FAILED, MAX_DELIVERY_ATTEMPTS
    return (
        NotificationDelivery.objects
        .filter(status=DELIVERY_PENDING, next_retry_at__lte=timezone.now())
        .filter(attempt_count__lt=MAX_DELIVERY_ATTEMPTS)
        .select_related("notification", "recipient", "recipient__user",
                        "notification__company")
        .order_by("next_retry_at")
    )


def get_templates_for_type_channel(
    notification_type: str,
    channel: str,
    company=None,
) -> object:
    """
    Return the most-specific active template for a notification type + channel.

    Priority: company-specific template > global template > None
    """
    from notifications.models import NotificationTemplate
    # Company-specific first
    if company:
        tmpl = NotificationTemplate.objects.filter(
            notification_type=notification_type,
            channel=channel,
            is_active=True,
            company=company,
        ).first()
        if tmpl:
            return tmpl
    # Global fallback
    return NotificationTemplate.objects.filter(
        notification_type=notification_type,
        channel=channel,
        is_active=True,
        company__isnull=True,
    ).first()


def get_provider_config(company, channel: str) -> object:
    """
    Return the NotificationProviderConfig for a company + channel, or None.
    """
    from notifications.models import NotificationProviderConfig
    try:
        return NotificationProviderConfig.objects.get(
            company=company, channel=channel
        )
    except NotificationProviderConfig.DoesNotExist:
        return None
