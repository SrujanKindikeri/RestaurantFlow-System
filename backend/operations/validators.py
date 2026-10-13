# =============================================================================
# RestaurantFlow — Operations Validators
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from decimal import Decimal


def validate_modifier_selections(modifier_group, selected_option_ids):
    """
    Validate that the number of selected options satisfies group constraints.

    Raises ModifierValidationError if validation fails.
    """
    from operations.exceptions import ModifierValidationError

    count = len(selected_option_ids)

    if modifier_group.is_required and count < modifier_group.min_selections:
        raise ModifierValidationError(
            f"Modifier group '{modifier_group.name}' requires at least "
            f"{modifier_group.min_selections} selection(s). Got {count}."
        )

    if modifier_group.max_selections > 0 and count > modifier_group.max_selections:
        raise ModifierValidationError(
            f"Modifier group '{modifier_group.name}' allows at most "
            f"{modifier_group.max_selections} selection(s). Got {count}."
        )

    # Validate all selected options belong to this group and are active
    valid_ids = set(
        modifier_group.options.filter(is_active=True).values_list("id", flat=True)
    )
    invalid = set(str(i) for i in selected_option_ids) - set(str(i) for i in valid_ids)
    if invalid:
        raise ModifierValidationError(
            f"Invalid or inactive modifier option(s): {invalid}"
        )


def validate_split_amounts_sum_to_bill(bill, splits):
    """
    Validate that the sum of split amounts equals the bill's grand_total.
    """
    from operations.exceptions import BillSplitConflict

    total = sum(Decimal(str(s.amount)) for s in splits)
    if abs(total - bill.grand_total) > Decimal("0.01"):
        raise BillSplitConflict(
            f"Split amounts ({total}) do not sum to bill total "
            f"({bill.grand_total})."
        )


def validate_order_merge_compatibility(source_orders, destination_order):
    """
    Validate that orders can be merged.
    """
    from operations.exceptions import IncompatibleOrders

    disallowed_statuses = ("CANCELLED",)

    for order in source_orders:
        if order.pk == destination_order.pk:
            continue
        if order.status in disallowed_statuses:
            raise IncompatibleOrders(
                f"Order {order.order_number} has status '{order.status}' "
                "and cannot be merged."
            )
        if order.branch_id != destination_order.branch_id:
            raise IncompatibleOrders(
                f"Order {order.order_number} belongs to a different branch."
            )
        # Cannot merge if already has a bill
        if hasattr(order, "bill"):
            try:
                _ = order.bill
                raise IncompatibleOrders(
                    f"Order {order.order_number} already has a bill "
                    "and cannot be merged."
                )
            except Exception as e:
                if "IncompatibleOrders" in str(type(e)):
                    raise
