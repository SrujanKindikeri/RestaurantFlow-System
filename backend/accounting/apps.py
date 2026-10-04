# =============================================================================
# RestaurantFlow — Accounting App Configuration
# Phase 13: Accounting Ledger, Double-Entry Bookkeeping
# =============================================================================

from django.apps import AppConfig


class AccountingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounting"
    verbose_name = "Accounting"

    def ready(self):
        # Import signal handlers when the app is ready
        import accounting.signals  # noqa: F401
