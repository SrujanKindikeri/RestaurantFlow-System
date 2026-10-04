# =============================================================================
# RestaurantFlow — WhatsApp Notification Provider
# Phase 16
#
# Architecture stub — provider-independent WhatsApp delivery interface.
# Does NOT integrate unofficial WhatsApp automation.
# Does NOT store credentials in database.
# Returns NOT_CONFIGURED until WhatsApp Cloud API or equivalent is wired in.
#
# To integrate:
#   1. Set WHATSAPP_PROVIDER=WHATSAPP_CLOUD in .env
#   2. Set WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID (never in database)
#   3. Use official Meta WhatsApp Business Cloud API only.
# =============================================================================

import logging
import os

from notifications.delivery.base import BaseNotificationProvider, DeliveryPayload, DeliveryResult
from notifications.constants import CHANNEL_WHATSAPP
from notifications.validators import validate_phone_number

logger = logging.getLogger("notifications")


class WhatsAppProvider(BaseNotificationProvider):
    """
    WhatsApp delivery provider.

    Returns NOT_CONFIGURED unless a real provider is configured via environment.
    Never falsely reports success. Never uses unofficial automation tools.
    """

    provider_code = "WHATSAPP"
    channel_code  = CHANNEL_WHATSAPP

    def send(self, payload: DeliveryPayload) -> DeliveryResult:
        if not self.validate_configuration():
            logger.debug(
                "WhatsAppProvider.send: provider not configured, skipping notification=%s",
                getattr(payload.notification, "pk", "?"),
            )
            return DeliveryResult.not_configured_result(
                "WhatsApp provider is not configured. Set WHATSAPP_PROVIDER in environment."
            )

        # Validate phone number
        phone = getattr(getattr(payload.recipient_user, "profile", None), "phone", "") or \
                getattr(payload.recipient_user, "phone", "")
        if not validate_phone_number(phone):
            return DeliveryResult.failed(
                f"Invalid or missing phone number for user {payload.recipient_user.pk}."
            )

        provider = os.getenv("WHATSAPP_PROVIDER", "").upper()

        try:
            if provider == "WHATSAPP_CLOUD":
                return self._send_via_cloud_api(payload, phone)
            else:
                return DeliveryResult.not_configured_result(
                    f"Unknown WhatsApp provider: {provider!r}"
                )
        except Exception as exc:
            logger.warning("WhatsAppProvider.send failed: %s", exc)
            return DeliveryResult.failed(str(exc)[:500])

    def _send_via_cloud_api(self, payload: DeliveryPayload, phone: str) -> DeliveryResult:
        """Meta WhatsApp Business Cloud API delivery."""
        import urllib.request
        import json as json_lib

        access_token    = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

        if not all([access_token, phone_number_id]):
            return DeliveryResult.not_configured_result(
                "WhatsApp Cloud API credentials not fully configured in environment."
            )

        url = f"https://graph.facebook.com/v18.0/{phone_number_id}/messages"
        data = json_lib.dumps({
            "messaging_product": "whatsapp",
            "to": phone.lstrip("+"),
            "type": "text",
            "text": {"body": payload.body or payload.notification.message},
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json_lib.loads(resp.read())
            message_id = result.get("messages", [{}])[0].get("id", "")
            return DeliveryResult.ok(provider_message_id=message_id)

    def validate_configuration(self) -> bool:
        provider = os.getenv("WHATSAPP_PROVIDER", "")
        return bool(provider)

    def get_status(self) -> dict:
        provider = os.getenv("WHATSAPP_PROVIDER", "")
        return {
            "channel":    CHANNEL_WHATSAPP,
            "provider":   provider or "none",
            "configured": bool(provider),
            "status":     "available" if provider else "not configured — set WHATSAPP_PROVIDER in environment",
        }
