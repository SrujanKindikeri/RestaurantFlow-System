# =============================================================================
# RestaurantFlow — Base Notification Provider
# Phase 16
#
# All channel providers implement this interface.
# This guarantees that providers can be swapped without touching the service layer.
# =============================================================================

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DeliveryResult:
    """
    Returned by every provider's send() method.

    success          — True if the message was accepted for delivery.
    status           — one of the DELIVERY_* constants.
    provider_message_id — external provider reference (e.g. email message ID).
    failure_reason   — human-readable error detail (never expose secrets).
    not_configured   — True when the provider has no configuration; caller
                        should record NOT_CONFIGURED status, not FAILED.
    """
    success: bool
    status: str
    provider_message_id: str = ""
    failure_reason: str = ""
    not_configured: bool = False

    @classmethod
    def ok(cls, provider_message_id: str = "") -> "DeliveryResult":
        from notifications.constants import DELIVERY_SENT
        return cls(success=True, status=DELIVERY_SENT, provider_message_id=provider_message_id)

    @classmethod
    def not_configured_result(cls, reason: str = "Provider not configured.") -> "DeliveryResult":
        from notifications.constants import DELIVERY_NOT_CONFIGURED
        return cls(success=False, status=DELIVERY_NOT_CONFIGURED,
                   failure_reason=reason, not_configured=True)

    @classmethod
    def failed(cls, reason: str) -> "DeliveryResult":
        from notifications.constants import DELIVERY_FAILED
        return cls(success=False, status=DELIVERY_FAILED, failure_reason=reason)


@dataclass
class DeliveryPayload:
    """
    Channel-agnostic delivery payload passed to every provider.

    recipient_user   — the User ORM instance receiving this notification.
    notification     — the Notification ORM instance.
    subject          — rendered subject (email) or empty string.
    body             — rendered body text.
    metadata         — arbitrary extra data from notification.metadata.
    """
    recipient_user: object          # accounts.User instance
    notification: object            # notifications.Notification instance
    subject: str = ""
    body: str = ""
    metadata: dict = field(default_factory=dict)


class BaseNotificationProvider(ABC):
    """
    Abstract base class for all notification channel providers.

    Subclasses must implement:
        send()                  — deliver the payload.
        validate_configuration() — check the provider is correctly configured.
        get_status()            — return a human-readable status dict.
    """

    #: Provider identifier string — must match a PROVIDER_* constant.
    provider_code: str = ""

    #: Channel this provider handles — must match a CHANNEL_* constant.
    channel_code: str = ""

    @abstractmethod
    def send(self, payload: DeliveryPayload) -> DeliveryResult:
        """
        Attempt to deliver the notification via this channel.

        Must be idempotent — calling it twice with the same payload must not
        create duplicate messages (use provider_message_id for dedup where
        the provider supports it).

        Must never raise — catch all exceptions internally and return
        DeliveryResult.failed(reason).
        """

    @abstractmethod
    def validate_configuration(self) -> bool:
        """
        Check that the provider has sufficient configuration to attempt delivery.
        Returns True if configured, False otherwise.
        """

    @abstractmethod
    def get_status(self) -> dict:
        """
        Return a dict describing the provider's current configuration status.
        Must never expose raw secrets.
        """
