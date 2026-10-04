# =============================================================================
# RestaurantFlow — Telegram Notification Provider
# Phase 16
#
# Architecture stub — provider-independent Telegram delivery interface.
# Does NOT store bot tokens in the database.
# Returns NOT_CONFIGURED until a Telegram bot is configured via environment.
#
# To integrate:
#   1. Set TELEGRAM_BOT_TOKEN in .env (never in database)
#   2. Users must have their Telegram chat_id stored in UserProfile
#      (add a telegram_chat_id field to UserProfile in accounts app if needed)
#   3. Use official Telegram Bot API only.
# =============================================================================

import logging
import os

from notifications.delivery.base import BaseNotificationProvider, DeliveryPayload, DeliveryResult
from notifications.constants import CHANNEL_TELEGRAM

logger = logging.getLogger("notifications")


class TelegramProvider(BaseNotificationProvider):
    """
    Telegram Bot API delivery provider.

    Returns NOT_CONFIGURED unless TELEGRAM_BOT_TOKEN is set in the environment
    and the recipient user has a telegram_chat_id configured.
    Never falsely reports success.
    """

    provider_code = "TELEGRAM_BOT"
    channel_code  = CHANNEL_TELEGRAM

    def send(self, payload: DeliveryPayload) -> DeliveryResult:
        if not self.validate_configuration():
            logger.debug(
                "TelegramProvider.send: provider not configured, skipping notification=%s",
                getattr(payload.notification, "pk", "?"),
            )
            return DeliveryResult.not_configured_result(
                "Telegram bot is not configured. Set TELEGRAM_BOT_TOKEN in environment."
            )

        # Get recipient's Telegram chat ID
        chat_id = self._get_chat_id(payload.recipient_user)
        if not chat_id:
            return DeliveryResult.failed(
                f"No Telegram chat_id configured for user {payload.recipient_user.pk}."
            )

        try:
            return self._send_message(chat_id, payload)
        except Exception as exc:
            logger.warning("TelegramProvider.send failed: %s", exc)
            return DeliveryResult.failed(str(exc)[:500])

    def _get_chat_id(self, user) -> str:
        """
        Retrieve the user's Telegram chat ID.
        Stored in UserProfile.telegram_chat_id if the field exists.
        """
        try:
            return getattr(user.profile, "telegram_chat_id", "") or ""
        except Exception:
            return ""

    def _send_message(self, chat_id: str, payload: DeliveryPayload) -> DeliveryResult:
        """Send a message via Telegram Bot API."""
        import urllib.request
        import json as json_lib

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

        text = f"*{payload.notification.title}*\n{payload.body or payload.notification.message}"

        data = json_lib.dumps({
            "chat_id":    chat_id,
            "text":       text,
            "parse_mode": "Markdown",
        }).encode("utf-8")

        req = urllib.request.Request(
            url, data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json_lib.loads(resp.read())
            if result.get("ok"):
                message_id = str(result.get("result", {}).get("message_id", ""))
                return DeliveryResult.ok(provider_message_id=message_id)
            return DeliveryResult.failed(result.get("description", "Telegram API error"))

    def validate_configuration(self) -> bool:
        return bool(os.getenv("TELEGRAM_BOT_TOKEN", ""))

    def get_status(self) -> dict:
        configured = self.validate_configuration()
        return {
            "channel":    CHANNEL_TELEGRAM,
            "provider":   self.provider_code,
            "configured": configured,
            "status":     "available" if configured else "not configured — set TELEGRAM_BOT_TOKEN in environment",
        }
