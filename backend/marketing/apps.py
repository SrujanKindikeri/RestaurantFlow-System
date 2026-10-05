# =============================================================================
# RestaurantFlow — Marketing App Config
# Phase 18
# =============================================================================

from django.apps import AppConfig


class MarketingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "marketing"
    verbose_name = "Marketing, Promotions & Campaigns"

    def ready(self):
        # Register marketing notification types with notifications app
        try:
            _register_notification_types()
        except Exception:
            pass  # Graceful — may fail during migrations before tables exist


def _register_notification_types():
    """
    Extend notifications.constants.NOTIFICATION_TYPE_CHOICES at runtime
    with marketing-specific types so the Notification model accepts them.
    """
    from notifications import constants as nc
    from marketing.constants import (
        NOTIF_CAMPAIGN_DELIVERY, NOTIF_PROMOTION_AVAILABLE, NOTIF_LOYALTY_BONUS,
        SOURCE_MARKETING_CAMPAIGN, SOURCE_MARKETING_PROMOTION,
    )

    marketing_types = [
        (NOTIF_CAMPAIGN_DELIVERY,   "Marketing Campaign Delivery"),
        (NOTIF_PROMOTION_AVAILABLE, "Marketing Promotion Available"),
        (NOTIF_LOYALTY_BONUS,       "Marketing Loyalty Bonus"),
    ]
    existing_codes = {code for code, _ in nc.NOTIFICATION_TYPE_CHOICES}
    for code, label in marketing_types:
        if code not in existing_codes:
            nc.NOTIFICATION_TYPE_CHOICES.append((code, label))

    marketing_sources = [
        (SOURCE_MARKETING_CAMPAIGN,  "Marketing Campaign"),
        (SOURCE_MARKETING_PROMOTION, "Marketing Promotion"),
    ]
    existing_sources = {code for code, _ in nc.SOURCE_TYPE_CHOICES}
    for code, label in marketing_sources:
        if code not in existing_sources:
            nc.SOURCE_TYPE_CHOICES.append((code, label))
