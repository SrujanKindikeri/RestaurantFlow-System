# =============================================================================
# RestaurantFlow — Kitchen Validators
# Phase 7
#
# Standalone validation functions used by services and serializers.
# Keeps validation logic separate from view and model layers.
# =============================================================================

from rest_framework.exceptions import ValidationError

from kitchen.models import (
    KitchenOrderStatus,
    KitchenItemStatus,
    KitchenPriority,
    KITCHEN_ORDER_TRANSITIONS,
    KITCHEN_ITEM_TRANSITIONS,
)


def validate_kitchen_order_transition(current_status: str, target_status: str) -> None:
    """
    Validate that a KitchenOrder state transition is allowed.

    Raises ValidationError with a clear message if the transition is forbidden.
    """
    allowed = KITCHEN_ORDER_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        if not allowed:
            raise ValidationError(
                {
                    "code": "INVALID_KITCHEN_TRANSITION",
                    "message": (
                        f"Kitchen order is in terminal state '{current_status}' "
                        "and cannot be transitioned further."
                    ),
                }
            )
        raise ValidationError(
            {
                "code": "INVALID_KITCHEN_TRANSITION",
                "message": (
                    f"Cannot transition kitchen order from '{current_status}' to '{target_status}'. "
                    f"Allowed next states: {', '.join(allowed)}."
                ),
            }
        )


def validate_kitchen_item_transition(current_status: str, target_status: str) -> None:
    """
    Validate that a KitchenOrderItem state transition is allowed.

    Raises ValidationError with a clear message if the transition is forbidden.
    """
    allowed = KITCHEN_ITEM_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        if not allowed:
            raise ValidationError(
                {
                    "code": "INVALID_ITEM_TRANSITION",
                    "message": (
                        f"Kitchen item is in terminal state '{current_status}' "
                        "and cannot be transitioned further."
                    ),
                }
            )
        raise ValidationError(
            {
                "code": "INVALID_ITEM_TRANSITION",
                "message": (
                    f"Cannot transition kitchen item from '{current_status}' to '{target_status}'. "
                    f"Allowed next states: {', '.join(allowed)}."
                ),
            }
        )


def validate_priority_value(priority: str) -> None:
    """Validate that a given priority string is a valid KitchenPriority choice."""
    if priority not in KitchenPriority.values:
        raise ValidationError(
            {
                "code": "INVALID_PRIORITY",
                "message": (
                    f"'{priority}' is not a valid priority. "
                    f"Choose from: {', '.join(KitchenPriority.values)}."
                ),
            }
        )


def validate_kitchen_order_not_terminal(kitchen_order) -> None:
    """
    Validate that a KitchenOrder is not in a terminal state (READY or CANCELLED).

    Used before performing any mutation that requires an active order.
    """
    if kitchen_order.status in (KitchenOrderStatus.READY, KitchenOrderStatus.CANCELLED):
        raise ValidationError(
            {
                "code": "KITCHEN_ORDER_TERMINAL",
                "message": (
                    f"This kitchen order is in a terminal state ({kitchen_order.status}) "
                    "and cannot be modified."
                ),
            }
        )


def validate_order_is_confirmed(order) -> None:
    """
    Validate that an Order is CONFIRMED before sending to kitchen.

    Raises ValidationError for DRAFT or CANCELLED orders.
    """
    from orders.models import OrderStatus

    if order.status == OrderStatus.DRAFT:
        raise ValidationError(
            {
                "code": "ORDER_NOT_CONFIRMED",
                "message": (
                    f"Order {order.order_number} is still DRAFT. "
                    "Confirm the order before sending to kitchen."
                ),
            }
        )
    if order.status == OrderStatus.CANCELLED:
        raise ValidationError(
            {
                "code": "ORDER_CANCELLED",
                "message": (
                    f"Order {order.order_number} is CANCELLED and cannot enter the kitchen."
                ),
            }
        )
