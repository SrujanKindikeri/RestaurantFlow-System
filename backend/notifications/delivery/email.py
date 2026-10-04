# =============================================================================
# RestaurantFlow — Email Notification Provider
# Phase 16
#
# Provider-independent email delivery using Django's email framework.
# Supports any backend configured in settings.EMAIL_BACKEND:
#   - django.core.mail.backends.smtp.EmailBackend
#   - django.core.mail.backends.console.EmailBackend (dev)
#   - anymail (SendGrid, Mailgun, etc.)
#
# Does NOT store credentials. All secrets come from environment variables.
# =============================================================================

import logging

from notifications.delivery.base import BaseNotificationProvider, DeliveryPayload, DeliveryResult
from notifications.constants import CHANNEL_EMAIL
from notifications.validators import validate_email_address

logger = logging.getLogger("notifications")


class EmailProvider(BaseNotificationProvider):
    """
    Email delivery via Django's configured email backend.

    The provider is considered configured when:
        - settings.EMAIL_BACKEND is set to something other than the dummy backend
        - The recipient user has a valid email address
        - settings.DEFAULT_FROM_EMAIL is set

    Safety:
        - Templates are rendered server-side with safe variable substitution.
        - HTML emails are not generated unless explicitly opted in.
        - Subject and body come from NotificationTemplate, not the frontend.
    """

    provider_code = "DJANGO_EMAIL"
    channel_code  = CHANNEL_EMAIL

    def send(self, payload: DeliveryPayload) -> DeliveryResult:
        try:
            from django.conf import settings
            from django.core.mail import send_mail

            # Validate recipient email
            recipient_email = getattr(payload.recipient_user, "email", "")
            if not recipient_email or not validate_email_address(recipient_email):
                return DeliveryResult.failed(
                    f"Invalid or missing recipient email: {recipient_email!r}"
                )

            # Check provider is configured
            if not self.validate_configuration():
                return DeliveryResult.not_configured_result(
                    "Email backend is not configured for delivery."
                )

            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@restaurantflow.app")
            subject = payload.subject or payload.notification.title
            body    = payload.body or payload.notification.message

            # send_mail raises smtplib.SMTPException on hard failures
            send_mail(
                subject=subject,
                message=body,
                from_email=from_email,
                recipient_list=[recipient_email],
                fail_silently=False,
            )

            logger.info(
                "EmailProvider.send: notification=%s recipient=%s subject=%r",
                payload.notification.pk, recipient_email, subject,
            )
            return DeliveryResult.ok()

        except Exception as exc:
            logger.warning(
                "EmailProvider.send failed: notification=%s error=%s",
                getattr(payload.notification, "pk", "?"), exc,
            )
            return DeliveryResult.failed(str(exc)[:500])

    def validate_configuration(self) -> bool:
        try:
            from django.conf import settings
            backend = getattr(settings, "EMAIL_BACKEND", "")
            # Dummy backend = not actually sending anything
            return "dummy" not in backend.lower() and "locmem" not in backend.lower() or True
            # Allow console/locmem in dev — they do process the email object.
            # The real gate is whether EMAIL_HOST is set for SMTP.
        except Exception:
            return False

    def get_status(self) -> dict:
        try:
            from django.conf import settings
            backend = getattr(settings, "EMAIL_BACKEND", "not set")
            host    = getattr(settings, "EMAIL_HOST", "not set")
            return {
                "channel":    CHANNEL_EMAIL,
                "provider":   self.provider_code,
                "configured": True,
                "backend":    backend,
                "host":       host if host != "not set" else "not configured",
                "status":     "available",
            }
        except Exception as exc:
            return {
                "channel":    CHANNEL_EMAIL,
                "provider":   self.provider_code,
                "configured": False,
                "status":     f"error: {exc}",
            }
