# =============================================================================
# RestaurantFlow — Kitchen App Configuration
# Phase 7: Kitchen Display System
# =============================================================================

from django.apps import AppConfig


class KitchenConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "kitchen"
    verbose_name = "Kitchen"

    def ready(self):
        import kitchen.signals  # noqa: F401 — register signal handlers
