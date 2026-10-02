# =============================================================================
# RestaurantFlow — Organizations App Config
# Phase 2: Company / Restaurant / Branch hierarchy
# =============================================================================

from django.apps import AppConfig


class OrganizationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "organizations"
    verbose_name = "Organizations"

    def ready(self):
        pass  # Signal handlers can be registered here in future phases
