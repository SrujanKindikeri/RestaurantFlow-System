# =============================================================================
# RestaurantFlow — Enterprise Signals
# Phase 20 / Phase 22
#
# Signal handlers for the enterprise app.
# Registered via apps.py EnterpriseConfig.ready().
# =============================================================================

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from common.caching.invalidation import invalidate_branch_config

logger = logging.getLogger("enterprise")


@receiver(post_save, sender="enterprise.EnterpriseConfiguration")
def on_enterprise_configuration_change(sender, instance, **kwargs):
    """Invalidate branch config cache when an EnterpriseConfiguration is saved."""
    branch_id = instance.branch_id
    key = instance.configuration_key
    if branch_id:
        invalidate_branch_config(branch_id=branch_id, key=key)
    # Also invalidate restaurant-level and company-level config patterns
    # by clearing without a specific key when there's no branch scope.
    elif instance.restaurant_id:
        invalidate_branch_config(branch_id=instance.restaurant_id, key=key)
