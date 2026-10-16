# =============================================================================
# RestaurantFlow — Enterprise App Configuration
# Phase 20
# =============================================================================

from django.apps import AppConfig


class EnterpriseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "enterprise"
    verbose_name = "Enterprise Operations"

    def ready(self):
        import enterprise.signals  # noqa: F401 — register signal handlers
