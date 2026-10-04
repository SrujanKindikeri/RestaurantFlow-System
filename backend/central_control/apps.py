# =============================================================================
# RestaurantFlow — Central Control Center App Config
# Phase 15
# =============================================================================

from django.apps import AppConfig


class CentralControlConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "central_control"
    verbose_name = "Central Control Center"

    def ready(self):
        # Import signals so they are connected on startup.
        pass  # signals defined inline in services; no separate signals module needed
