# =============================================================================
# RestaurantFlow — Menu App Configuration
# Phase 5
# =============================================================================

from django.apps import AppConfig


class MenuConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "menu"
    verbose_name = "Menu"

    def ready(self):
        import menu.signals  # noqa: F401 — register signal handlers
