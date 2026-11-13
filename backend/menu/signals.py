# =============================================================================
# RestaurantFlow — Menu Signals
# Phase 22
#
# Invalidates menu catalog cache on model changes.
# Registered via apps.py MenuConfig.ready().
# =============================================================================

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from common.caching.invalidation import invalidate_menu_catalog

logger = logging.getLogger("menu")


def _get_branch_ids_for_item(instance):
    """Return a list of branch IDs associated with a menu item."""
    from menu.models import MenuItemBranch
    return list(
        MenuItemBranch.objects.filter(menu_item=instance).values_list("branch_id", flat=True)
    )


@receiver([post_save, post_delete], sender="menu.MenuItem")
def on_menu_item_change(sender, instance, **kwargs):
    """Invalidate menu catalog for all branches that carry this item."""
    branch_ids = _get_branch_ids_for_item(instance)
    for branch_id in branch_ids:
        invalidate_menu_catalog(branch_id)


@receiver([post_save, post_delete], sender="menu.MenuItemPrice")
def on_menu_item_price_change(sender, instance, **kwargs):
    """Invalidate menu catalog for the branch whose price changed."""
    if instance.branch_id:
        invalidate_menu_catalog(instance.branch_id)


@receiver([post_save, post_delete], sender="menu.MenuItemBranch")
def on_menu_item_branch_change(sender, instance, **kwargs):
    """Invalidate menu catalog for the branch whose availability changed."""
    if instance.branch_id:
        invalidate_menu_catalog(instance.branch_id)
