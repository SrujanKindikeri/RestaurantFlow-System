# =============================================================================
# RestaurantFlow — Accounts Signals
# Phase 22
#
# Signal handlers for the accounts app.
# Registered via apps.py AccountsConfig.ready().
# =============================================================================

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from common.caching.invalidation import invalidate_user_permissions

logger = logging.getLogger("accounts")


@receiver(post_save, sender="accounts.UserRoleAssignment")
def on_user_role_assignment_change(sender, instance, **kwargs):
    """Invalidate user permissions cache when a role assignment is saved."""
    if instance.user_id:
        invalidate_user_permissions(user_id=instance.user_id)
