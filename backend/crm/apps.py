# =============================================================================
# RestaurantFlow — CRM Application Config
# Phase 17
# =============================================================================

from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "crm"
    verbose_name = "CRM — Customer Management"

    def ready(self):
        import crm.signals  # noqa: F401 — connect signal handlers
