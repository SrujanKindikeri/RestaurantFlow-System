# =============================================================================
# RestaurantFlow — Operations App Configuration
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from django.apps import AppConfig


class OperationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "operations"
    verbose_name = "Operations"

    def ready(self):
        import operations.signals  # noqa: F401
