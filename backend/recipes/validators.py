# =============================================================================
# RestaurantFlow — Recipe Validators
# Phase 11
#
# Pure validation functions — raise ValidationError on failure.
# Called from services before mutating state.
# =============================================================================

from decimal import Decimal

from rest_framework.exceptions import ValidationError

from inventory.constants import (
    are_units_compatible,
    get_conversion_factor,
    UNIT_CHOICES,
)
from recipes.constants import (
    RECIPE_ACTIVATABLE_STATUSES,
    RECIPE_ARCHIVABLE_STATUSES,
    ZERO,
    MAX_PREPARATION_LOSS_PCT,
    MIN_PREPARATION_LOSS_PCT,
)


VALID_UNITS = {code for code, _ in UNIT_CHOICES}


# ---------------------------------------------------------------------------
# Recipe-level validators
# ---------------------------------------------------------------------------

def validate_recipe_belongs_to_restaurant(recipe, restaurant):
    """Ensure recipe is owned by the expected restaurant."""
    if str(recipe.restaurant_id) != str(restaurant.pk):
        raise ValidationError({
            "code": "CROSS_RESTAURANT_RECIPE",
            "message": "Recipe does not belong to this restaurant.",
        })


def validate_recipe_activatable(recipe):
    """Ensure recipe is in a status that allows activation."""
    if recipe.status not in RECIPE_ACTIVATABLE_STATUSES:
        raise ValidationError({
            "code": "RECIPE_NOT_ACTIVATABLE",
            "message": (
                f"Recipe with status '{recipe.status}' cannot be activated. "
                f"Only {', '.join(RECIPE_ACTIVATABLE_STATUSES)} recipes can be activated."
            ),
        })


def validate_recipe_archivable(recipe):
    """Ensure recipe is in a status that allows archiving."""
    if recipe.status not in RECIPE_ARCHIVABLE_STATUSES:
        raise ValidationError({
            "code": "RECIPE_NOT_ARCHIVABLE",
            "message": (
                f"Recipe with status '{recipe.status}' cannot be archived."
            ),
        })


def validate_recipe_has_ingredients(recipe):
    """Ensure recipe has at least one active ingredient before activation."""
    if not recipe.items.exists():
        raise ValidationError({
            "code": "RECIPE_NO_INGREDIENTS",
            "message": "Recipe must have at least one ingredient before it can be activated.",
        })


def validate_no_duplicate_active_recipe(menu_item, exclude_recipe_id=None):
    """
    Ensure there is no other ACTIVE recipe for this menu_item.
    Used before activating a recipe.
    """
    from recipes.models import Recipe
    from recipes.constants import RECIPE_ACTIVE

    qs = Recipe.objects.filter(menu_item=menu_item, status=RECIPE_ACTIVE)
    if exclude_recipe_id:
        qs = qs.exclude(pk=exclude_recipe_id)
    if qs.exists():
        raise ValidationError({
            "code": "DUPLICATE_ACTIVE_RECIPE",
            "message": (
                f"Menu item '{menu_item.name}' already has an ACTIVE recipe. "
                "Archive or deactivate it before activating another."
            ),
        })


# ---------------------------------------------------------------------------
# RecipeItem validators
# ---------------------------------------------------------------------------

def validate_recipe_item_quantity(quantity):
    """Quantity must be strictly positive."""
    if quantity is None or Decimal(str(quantity)) <= ZERO:
        raise ValidationError({
            "code": "INVALID_QUANTITY",
            "message": "Recipe ingredient quantity must be greater than 0.",
        })


def validate_recipe_item_unit(unit):
    """Unit must be a known unit from inventory constants."""
    if unit not in VALID_UNITS:
        raise ValidationError({
            "code": "INVALID_UNIT",
            "message": f"'{unit}' is not a valid unit. Valid units: {', '.join(sorted(VALID_UNITS))}.",
        })


def validate_unit_compatibility(recipe_unit: str, inventory_unit: str, item_name: str):
    """
    Recipe ingredient unit must be compatible (same family) with the
    InventoryItem's default_unit.
    """
    if not are_units_compatible(recipe_unit, inventory_unit):
        raise ValidationError({
            "code": "INCOMPATIBLE_UNITS",
            "message": (
                f"Unit '{recipe_unit}' is not compatible with inventory item "
                f"'{item_name}' which uses '{inventory_unit}'. "
                "Units must be in the same measurement family (weight/volume/count)."
            ),
        })


def validate_unit_conversion_exists(recipe_unit: str, inventory_unit: str, item_name: str):
    """
    Ensure a conversion factor exists between recipe_unit and inventory_unit.
    """
    if recipe_unit == inventory_unit:
        return  # no conversion needed
    factor = get_conversion_factor(recipe_unit, inventory_unit)
    if factor is None:
        raise ValidationError({
            "code": "NO_CONVERSION_PATH",
            "message": (
                f"No conversion path found from '{recipe_unit}' to '{inventory_unit}' "
                f"for inventory item '{item_name}'. "
                "Please ensure units are compatible or update the conversion table."
            ),
        })


def validate_preparation_loss(loss_pct):
    """Preparation loss must be between 0 and 100 (exclusive of 100)."""
    loss = Decimal(str(loss_pct))
    if loss < MIN_PREPARATION_LOSS_PCT or loss >= MAX_PREPARATION_LOSS_PCT:
        raise ValidationError({
            "code": "INVALID_PREPARATION_LOSS",
            "message": (
                f"Preparation loss percentage must be between "
                f"{MIN_PREPARATION_LOSS_PCT} and {MAX_PREPARATION_LOSS_PCT} (exclusive)."
            ),
        })


def validate_inventory_item_active(inventory_item):
    """Inventory item must be active to be used in a recipe."""
    if not inventory_item.is_active:
        raise ValidationError({
            "code": "INACTIVE_INVENTORY_ITEM",
            "message": (
                f"Inventory item '{inventory_item.name}' is inactive and cannot "
                "be used as a recipe ingredient."
            ),
        })


def validate_cross_restaurant_ingredient(recipe, inventory_item):
    """Recipe and its ingredient inventory items must belong to the same restaurant."""
    if str(recipe.restaurant_id) != str(inventory_item.restaurant_id):
        raise ValidationError({
            "code": "CROSS_RESTAURANT_INGREDIENT",
            "message": (
                f"Inventory item '{inventory_item.name}' belongs to a different restaurant "
                "than this recipe. Cross-restaurant ingredients are not allowed."
            ),
        })


# ---------------------------------------------------------------------------
# Consumption validators
# ---------------------------------------------------------------------------

def validate_order_confirmed(order):
    """Order must be CONFIRMED for consumption to proceed."""
    from orders.models import OrderStatus
    if order.status != OrderStatus.CONFIRMED:
        raise ValidationError({
            "code": "ORDER_NOT_CONFIRMED",
            "message": (
                f"Order {order.order_number} has status '{order.status}'. "
                "Only CONFIRMED orders can trigger inventory consumption."
            ),
        })


def validate_kitchen_order_ready(kitchen_order):
    """KitchenOrder must be READY for KITCHEN_COMPLETED trigger."""
    from kitchen.models import KitchenOrderStatus
    if kitchen_order.status != KitchenOrderStatus.READY:
        raise ValidationError({
            "code": "KITCHEN_ORDER_NOT_READY",
            "message": (
                f"Kitchen order has status '{kitchen_order.status}'. "
                "Consumption requires the kitchen order to be READY."
            ),
        })


def validate_sufficient_stock_for_consumption(
    inventory_item,
    storage_location,
    required_quantity: Decimal,
):
    """
    Check stock balance without modifying it.
    Raises ValidationError with INSUFFICIENT_STOCK if unavailable.
    """
    from inventory.models import StockBalance
    from inventory.constants import ZERO as INV_ZERO

    try:
        balance = StockBalance.objects.get(
            inventory_item=inventory_item,
            storage_location=storage_location,
        )
        available = balance.available_quantity
    except StockBalance.DoesNotExist:
        available = INV_ZERO

    if available < required_quantity:
        raise ValidationError({
            "code": "INSUFFICIENT_STOCK",
            "message": (
                f"Insufficient stock for '{inventory_item.name}' at "
                f"'{storage_location.name}'. "
                f"Required: {required_quantity} {inventory_item.default_unit}, "
                f"Available: {available} {inventory_item.default_unit}."
            ),
        })
