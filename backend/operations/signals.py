# =============================================================================
# RestaurantFlow — Operations Signals
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================
# Signals hook into existing domain events to update operational state.
# =============================================================================

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("operations")


@receiver(post_save, sender="orders.Order")
def sync_fulfillment_status_on_confirm(sender, instance, created, **kwargs):
    """
    When an Order is CONFIRMED, create an OrderFulfillmentStatus record.
    When an Order is CANCELLED, update existing fulfillment record.
    """
    from orders.models import OrderStatus
    from operations.models import OrderFulfillmentStatus
    from operations.constants import FULFILLMENT_CONFIRMED, FULFILLMENT_CANCELLED

    if instance.status == OrderStatus.CONFIRMED:
        OrderFulfillmentStatus.objects.get_or_create(
            order=instance,
            defaults={"status": FULFILLMENT_CONFIRMED},
        )
    elif instance.status == OrderStatus.CANCELLED:
        OrderFulfillmentStatus.objects.filter(order=instance).update(
            status=FULFILLMENT_CANCELLED,
        )


@receiver(post_save, sender="orders.DiningTable")
def ensure_table_operational_status(sender, instance, created, **kwargs):
    """
    When a new DiningTable is created, create a default TableOperationalStatus.
    """
    if created:
        from operations.models import TableOperationalStatus
        from operations.constants import TABLE_OP_AVAILABLE
        TableOperationalStatus.objects.get_or_create(
            table=instance,
            defaults={"status": TABLE_OP_AVAILABLE},
        )
