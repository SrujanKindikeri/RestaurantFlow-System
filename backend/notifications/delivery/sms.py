# =============================================================================
# RestaurantFlow — SMS Notification Provider
# Phase 16
#
# Architecture stub — provider-independent SMS delivery interface.
# Does NOT integrate any paid provider. Returns NOT_CONFIGURED until a real
# provider (Twilio, Vonage, etc.) is wired in via settings.
#
# To integrate a real provider:
#   1. Set SMS_PROVIDER=TWILIO (or VONAGE) in .env
#   2. Set SMS_API_KEY, SMS_API_SECRET, SMS_FROM_NUMBER (never in database)
#   3. Implement the _send_via_twilio() or equivalent helper below.
# =============================================================================

import logging
import os

from notifications.delivery.base import BaseNotificationProvider, DeliveryPayload, DeliveryResult
from notifications.constants import CHANNEL_SMS
from notifications.validators import validate_phone_number

logger = logging.getLogger("notifications")


class SMSProvider(BaseNotificationProvider):
    """
    SMS delivery provider.

    Currently returns NOT_CONFIGURED unless a real provider is configured
    via environment variables. Never falsely reports success.
    """

    provider_code = "SMS"
    channel_code  = CHANNEL_SMS

    def send(self, payload: DeliveryPayload) -> DeliveryResult:
        if not self.validate_configuration():
            logger.debug(
                "SMSProvider.send: provider not configured, skipping notification=%s",
                getattr(payload.notification, "pk", "?"),
            )
            return DeliveryResult.not_configured_result(
                "SMS provider is not configured. Set SMS_PROVIDER in environment."
            )

        # Validate phone number
        phone = getattr(getattr(payload.recipient_user, "profile", None), "phone", "") or \
                getattr(payload.recipient_user, "phone", "")
        if not validate_phone_number(phone):
            return DeliveryResult.failed(
                f"Invalid or missing phone number for user {payload.recipient_user.pk}."
            )

        provider = os.getenv("SMS_PROVIDER", "").upper()

        try:
            if provider == "TWILIO":
                return self._send_via_twilio(payload, phone)
            elif provider == "VONAGE":
                return self._send_via_vonage(payload, phone)
            else:
                return DeliveryResult.not_configured_result(
                    f"Unknown SMS provider: {provider!r}"
                )
        except Exception as exc:
            logger.warning("SMSProvider.send failed: %s", exc)
            return DeliveryResult.failed(str(exc)[:500])

    def _send_via_twilio(self, payload: DeliveryPayload, phone: str) -> DeliveryResult:
        """Twilio SMS delivery (requires twilio package installed + env vars)."""
        try:
            from twilio.rest import Client  # type: ignore
        except ImportError:
            return DeliveryResult.not_configured_result(
                "Twilio package not installed. Run: pip install twilio"
            )

        account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        auth_token  = os.getenv("TWILIO_AUTH_TOKEN", "")
        from_number = os.getenv("TWILIO_FROM_NUMBER", "")

        if not all([account_sid, auth_token, from_number]):
            return DeliveryResult.not_configured_result(
                "Twilio credentials not fully configured in environment."
            )

        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=payload.body or payload.notification.message,
            from_=from_number,
            to=phone,
        )
        return DeliveryResult.ok(provider_message_id=message.sid)

    def _send_via_vonage(self, payload: DeliveryPayload, phone: str) -> DeliveryResult:
        """Vonage (Nexmo) SMS delivery (requires vonage package + env vars)."""
        try:
            import vonage  # type: ignore
        except ImportError:
            return DeliveryResult.not_configured_result(
                "Vonage package not installed. Run: pip install vonage"
            )

        api_key    = os.getenv("VONAGE_API_KEY", "")
        api_secret = os.getenv("VONAGE_API_SECRET", "")
        from_name  = os.getenv("VONAGE_FROM_NAME", "RestaurantFlow")

        if not all([api_key, api_secret]):
            return DeliveryResult.not_configured_result(
                "Vonage credentials not fully configured in environment."
            )

        client = vonage.Client(key=api_key, secret=api_secret)
        sms    = vonage.Sms(client)
        response = sms.send_message({
            "from": from_name,
            "to":   phone.lstrip("+"),
            "text": payload.body or payload.notification.message,
        })
        if response["messages"][0]["status"] == "0":
            return DeliveryResult.ok(
                provider_message_id=response["messages"][0].get("message-id", "")
            )
        return DeliveryResult.failed(
            response["messages"][0].get("error-text", "Unknown Vonage error")
        )

    def validate_configuration(self) -> bool:
        provider = os.getenv("SMS_PROVIDER", "")
        return bool(provider)

    def get_status(self) -> dict:
        provider = os.getenv("SMS_PROVIDER", "")
        return {
            "channel":    CHANNEL_SMS,
            "provider":   provider or "none",
            "configured": bool(provider),
            "status":     "available" if provider else "not configured — set SMS_PROVIDER in environment",
        }
