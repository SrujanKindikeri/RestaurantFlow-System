# =============================================================================
# RestaurantFlow — Notifications App Config
# Phase 16
# =============================================================================

from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications"
    verbose_name = "Notifications"

    def ready(self):
        # Wire up all event handlers (signals that trigger notification creation)
        import notifications.event_handlers  # noqa: F401
