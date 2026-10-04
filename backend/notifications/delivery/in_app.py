# =============================================================================
# RestaurantFlow — In-App Notification Provider
# Phase 16
#
# In-app delivery is always available. It simply marks the recipient record
# as DELIVERED. The actual display is handled by the REST API + frontend.
# =============================================================================

import logging

from notifications.delivery.base import BaseNotificationProvider, DeliveryPayload, DeliveryResult
from notifications.constants import CHANNEL_IN_APP, DELIVERY_DELIVERED

logger = logging.getLogger("notifications")


class InAppProvider(BaseNotificationProvider):
    """
    In-app delivery provider.

    Always succeeds — the notification is already persisted in the database,
    so "delivery" means the recipient record is marked DELIVERED.
    No external calls are made.
    """

    provider_code = "IN_APP"
    channel_code  = CHANNEL_IN_APP

    def send(self, payload: DeliveryPayload) -> DeliveryResult:
        # The notification is already in the DB; in-app delivery is instant.
        logger.debug(
            "InAppProvider.send: notification=%s user=%s",
            payload.notification.pk,
            payload.recipient_user.pk,
        )
        return DeliveryResult(
            success=True,
            status=DELIVERY_DELIVERED,
            provider_message_id="",
        )

    def validate_configuration(self) -> bool:
        return True

    def get_status(self) -> dict:
        return {
            "channel": CHANNEL_IN_APP,
            "provider": self.provider_code,
            "configured": True,
            "status": "available",
        }
