# =============================================================================
# RestaurantFlow — Inventory Signals
# Phase 22
#
# Signal handlers for the inventory app.
# Registered via apps.py InventoryConfig.ready().
# =============================================================================

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

from common.caching.invalidation import invalidate_inventory_availability

logger = logging.getLogger("inventory")


@receiver(post_save, sender="inventory.StockBalance")
def on_stock_balance_change(sender, instance, **kwargs):
    """Invalidate inventory availability cache when stock balance changes."""
    try:
        branch_id = instance.storage_location.branch_id
    except Exception:
        # storage_location may not be loaded; skip invalidation
        logger.warning(
            "Could not resolve branch_id for StockBalance %s; skipping cache invalidation.",
            instance.pk,
        )
        return
    item_id = instance.inventory_item_id
    if branch_id and item_id:
        invalidate_inventory_availability(branch_id=branch_id, item_id=item_id)
