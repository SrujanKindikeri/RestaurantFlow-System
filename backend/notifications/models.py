# =============================================================================
# RestaurantFlow — Notifications Models
# Phase 16
#
# Model hierarchy:
#   Notification          — the event/message itself (company/restaurant/branch scoped)
#   NotificationRecipient — per-user read/delivery state for a Notification
#   NotificationDelivery  — per-channel delivery record (email, SMS, etc.)
#   NotificationPreference — user's channel opt-in/out per notification type
#   NotificationTemplate   — reusable message templates per type+channel
#   NotificationProviderConfig — provider configuration metadata (no raw secrets)
#
# Design principles:
#   - Notification state and recipient state are separate models.
#   - One Notification may have many NotificationRecipients.
#   - Company/restaurant/branch isolation is enforced at model level.
#   - No raw secrets stored in the database (provider config stores refs only).
# =============================================================================

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimestampedModel
from notifications.constants import (
    NOTIFICATION_TYPE_CHOICES,
    SEVERITY_CHOICES,
    SEVERITY_MEDIUM,
    CHANNEL_CHOICES,
    DELIVERY_STATUS_CHOICES,
    DELIVERY_PENDING,
    RECIPIENT_STATUS_CHOICES,
    RECIPIENT_PENDING,
    SOURCE_TYPE_CHOICES,
    PROVIDER_DJANGO_EMAIL,
)


# =============================================================================
# Notification
# =============================================================================

class Notification(TimestampedModel):
    """
    The canonical notification event/message.

    Represents a single event that happened in the system — e.g. a payment
    failed, an expense needs approval, a kitchen order is delayed.

    Scope:
        company   — required always
        restaurant — nullable; set when the event is restaurant-specific
        branch     — nullable; set when the event is branch-specific

    Idempotency:
        Use source_type + source_id + notification_type to detect duplicates
        before creating a new Notification.  The service enforces this.

    Expiration:
        expires_at = None  means the notification never expires.
        Expired notifications remain in the database (history is preserved)
        but may be hidden in the default UI filter.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Scope
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notifications",
        db_index=True,
    )

    # Type & severity
    notification_type = models.CharField(
        max_length=60,
        choices=NOTIFICATION_TYPE_CHOICES,
        db_index=True,
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_MEDIUM,
        db_index=True,
    )

    # Content
    title   = models.CharField(max_length=200)
    message = models.TextField()

    # Source reference — what triggered this notification
    source_type = models.CharField(
        max_length=60,
        choices=SOURCE_TYPE_CHOICES,
        db_index=True,
    )
    source_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="UUID/ID of the source object as a string.",
    )

    # Deep-link destination (e.g. /expenses/EXP-1023/)
    action_url = models.CharField(max_length=500, blank=True)

    # Arbitrary extra data for template rendering / frontend display
    metadata = models.JSONField(default=dict, blank=True)

    # Lifecycle
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "created_at"]),
            models.Index(fields=["company", "notification_type"]),
            models.Index(fields=["company", "severity"]),
            models.Index(fields=["restaurant", "created_at"]),
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["notification_type", "source_type", "source_id"]),
        ]

    def __str__(self):
        return f"[{self.notification_type}] {self.title}"

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at


# =============================================================================
# NotificationRecipient
# =============================================================================

class NotificationRecipient(TimestampedModel):
    """
    Per-user read/delivery state for a Notification.

    One Notification has many NotificationRecipients.
    Read state (read_at, acknowledged_at) lives here, NOT on Notification,
    so each user's state is tracked independently.

    Uniqueness:
        (notification, user) — one row per user per notification.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="recipients",
        db_index=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_recipients",
        db_index=True,
    )

    # Delivery / read state
    delivery_status = models.CharField(
        max_length=20,
        choices=RECIPIENT_STATUS_CHOICES,
        default=RECIPIENT_PENDING,
        db_index=True,
    )
    read_at         = models.DateTimeField(null=True, blank=True, db_index=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    delivered_at    = models.DateTimeField(null=True, blank=True)
    failed_at       = models.DateTimeField(null=True, blank=True)
    failure_reason  = models.TextField(blank=True)

    class Meta:
        verbose_name = "Notification Recipient"
        verbose_name_plural = "Notification Recipients"
        ordering = ["-created_at"]
        unique_together = [("notification", "user")]
        indexes = [
            models.Index(fields=["user", "delivery_status"]),
            models.Index(fields=["user", "notification"]),
            models.Index(fields=["notification", "delivery_status"]),
            models.Index(fields=["user", "read_at"]),
        ]

    def __str__(self):
        return f"{self.user.email} — {self.notification.notification_type}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    @property
    def is_acknowledged(self) -> bool:
        return self.acknowledged_at is not None


# =============================================================================
# NotificationDelivery
# =============================================================================

class NotificationDelivery(TimestampedModel):
    """
    Per-channel delivery record.

    Tracks the lifecycle of each delivery attempt for a specific channel
    (in-app, email, SMS, WhatsApp, Telegram, WebSocket).

    One NotificationRecipient can have many NotificationDelivery rows —
    one per channel, potentially multiple per channel if retried.

    Idempotency:
        The service enforces that (notification, recipient, channel) produces
        at most one active delivery record (non-FAILED/CANCELLED).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="deliveries",
        db_index=True,
    )
    recipient = models.ForeignKey(
        NotificationRecipient,
        on_delete=models.CASCADE,
        related_name="deliveries",
        db_index=True,
    )

    channel = models.CharField(
        max_length=20,
        choices=[
            ("IN_APP",    "In-App"),
            ("WEBSOCKET", "WebSocket"),
            ("EMAIL",     "Email"),
            ("SMS",       "SMS"),
            ("WHATSAPP",  "WhatsApp"),
            ("TELEGRAM",  "Telegram"),
        ],
        db_index=True,
    )
    provider = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Provider code, e.g. DJANGO_EMAIL, SENDGRID.",
    )
    status = models.CharField(
        max_length=20,
        choices=DELIVERY_STATUS_CHOICES,
        default=DELIVERY_PENDING,
        db_index=True,
    )

    attempt_count       = models.PositiveSmallIntegerField(default=0)
    provider_message_id = models.CharField(max_length=200, blank=True)

    queued_at    = models.DateTimeField(default=timezone.now)
    sent_at      = models.DateTimeField(null=True, blank=True)
    failed_at    = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True)
    next_retry_at  = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "Notification Delivery"
        verbose_name_plural = "Notification Deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["notification", "channel"]),
            models.Index(fields=["recipient", "channel"]),
            models.Index(fields=["status", "next_retry_at"]),
            models.Index(fields=["channel", "status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.channel} | {self.status} | "
            f"{self.recipient.user.email} | {self.notification.notification_type}"
        )


# =============================================================================
# NotificationPreference
# =============================================================================

class NotificationPreference(TimestampedModel):
    """
    User-specific channel opt-in/out per notification type.

    If no row exists for a (user, notification_type, channel) triplet, the
    system falls back to DEFAULT_CHANNEL_PREFS from constants.py.

    Uniqueness:
        (user, notification_type, channel) — one preference per combo.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        db_index=True,
    )
    notification_type = models.CharField(
        max_length=60,
        choices=NOTIFICATION_TYPE_CHOICES,
        db_index=True,
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        db_index=True,
    )
    enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
        unique_together = [("user", "notification_type", "channel")]
        ordering = ["notification_type", "channel"]
        indexes = [
            models.Index(fields=["user", "notification_type"]),
            models.Index(fields=["user", "channel"]),
        ]

    def __str__(self):
        state = "ON" if self.enabled else "OFF"
        return f"{self.user.email} | {self.notification_type} | {self.channel} | {state}"


# =============================================================================
# NotificationTemplate
# =============================================================================

class NotificationTemplate(TimestampedModel):
    """
    Reusable message template for a notification type + channel combination.

    Templates use a safe {{variable}} substitution — only variables in
    SAFE_TEMPLATE_VARS (constants.py) are allowed.

    Scope:
        company = None means the template is a global default.
        company = <org> means it overrides the global default for that company.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Company-specific override; NULL = global default
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notification_templates",
        db_index=True,
    )
    notification_type = models.CharField(
        max_length=60,
        choices=NOTIFICATION_TYPE_CHOICES,
        db_index=True,
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        db_index=True,
    )

    # Email-specific (blank for in-app/SMS)
    subject_template = models.CharField(max_length=300, blank=True)
    # The main notification body
    body_template = models.TextField()

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
        # Per company: one active template per type+channel
        ordering = ["notification_type", "channel"]
        indexes = [
            models.Index(fields=["notification_type", "channel", "is_active"]),
            models.Index(fields=["company", "notification_type", "channel"]),
        ]

    def __str__(self):
        scope = self.company.name if self.company_id else "Global"
        return f"[{scope}] {self.notification_type} | {self.channel}"


# =============================================================================
# NotificationProviderConfig
# =============================================================================

class NotificationProviderConfig(TimestampedModel):
    """
    Provider configuration metadata per company per channel.

    IMPORTANT:
        Do NOT store raw API keys, passwords, or tokens here.
        Store only non-secret metadata (provider name, enabled flag, config keys).
        Actual secrets must live in environment variables or a secret manager.

    Examples:
        channel=EMAIL, provider=SENDGRID, is_enabled=True
        channel=SMS, provider=TWILIO, is_enabled=False
        channel=TELEGRAM, provider=TELEGRAM_BOT, is_enabled=True
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notification_provider_configs",
        db_index=True,
    )
    channel = models.CharField(
        max_length=20,
        choices=CHANNEL_CHOICES,
        db_index=True,
    )
    provider = models.CharField(
        max_length=50,
        default=PROVIDER_DJANGO_EMAIL,
        help_text="Provider code (e.g. DJANGO_EMAIL, SENDGRID, TWILIO).",
    )
    is_enabled = models.BooleanField(default=False)

    # Non-secret configuration metadata (e.g. sender address, bot username)
    # Never store API keys or passwords here.
    configuration_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Non-secret provider metadata (sender email, from_name, etc.). "
            "Never store API keys or tokens here."
        ),
    )

    class Meta:
        verbose_name = "Notification Provider Config"
        verbose_name_plural = "Notification Provider Configs"
        unique_together = [("company", "channel")]
        indexes = [
            models.Index(fields=["company", "channel", "is_enabled"]),
        ]

    def __str__(self):
        state = "enabled" if self.is_enabled else "disabled"
        return f"{self.company.name} | {self.channel} | {self.provider} | {state}"
