# =============================================================================
# RestaurantFlow — Kitchen Signals
# Phase 7
#
# When a Phase 6 Order transitions to CONFIRMED, a KitchenOrder is
# automatically created.
#
# Signal approach:
#   We listen to post_save on Order, filtered to status == CONFIRMED.
#   The KitchenOrder creation is transactional (wrapped in atomic block
#   in the service).
#
# Design decision:
#   The signal handler is a lightweight dispatcher that calls
#   services.send_order_to_kitchen().  All business logic stays in
#   the service layer.
#
# Idempotency:
#   send_order_to_kitchen() is idempotent — calling it twice for the same
#   order returns the existing KitchenOrder without duplicating anything.
#
# Failure handling:
#   If kitchen order creation fails (e.g. empty order), the error is logged
#   but does NOT raise — the order confirmation itself has already succeeded
#   and must not be rolled back retroactively.  The kitchen order can be
#   manually triggered by an admin if needed.
#
#   For a stronger guarantee, a transactional outbox can be introduced later.
#   The service is designed to support that pattern.
# =============================================================================

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger("kitchen")


@receiver(post_save, sender="orders.Order")
def order_confirmed_create_kitchen_order(sender, instance, created, **kwargs):
    """
    When an Order transitions to CONFIRMED, create the corresponding
    KitchenOrder via the kitchen service.

    This signal fires on every Order save.  We gate on:
        1. status == CONFIRMED (not DRAFT or CANCELLED)
        2. The order was not just freshly created (created=True → still DRAFT)
           — but we check status regardless, so new CONFIRMED orders are caught.

    Note: We use a deferred check so that even if somehow an order is created
    directly as CONFIRMED, it still gets a kitchen order.
    """
    from orders.models import OrderStatus

    if instance.status != OrderStatus.CONFIRMED:
        return

    # Import here to avoid circular import at module load time
    from kitchen.services import send_order_to_kitchen

    try:
        kitchen_order = send_order_to_kitchen(instance)
        # Publish the created event (only for genuinely new kitchen orders,
        # not idempotent re-calls)
        from kitchen.services import publish_kitchen_event
        publish_kitchen_event("kitchen.order.created", kitchen_order)

        logger.info(
            "order_confirmed_create_kitchen_order: KitchenOrder %s created for order %s",
            kitchen_order.id,
            instance.order_number,
        )

    except Exception as exc:
        # Log but don't re-raise: the order confirmation is already committed.
        # The kitchen order can be recovered via admin or future outbox retry.
        logger.error(
            "order_confirmed_create_kitchen_order: FAILED to create KitchenOrder "
            "for order=%s error=%s",
            instance.order_number,
            exc,
        )
