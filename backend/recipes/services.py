# =============================================================================
# RestaurantFlow — Recipe Services
# Phase 11: Recipe and Ingredient Consumption
#
# Public API:
#   create_recipe(restaurant, menu_item, name, user, **kwargs) → Recipe
#   update_recipe(recipe, user, **kwargs) → Recipe
#   add_recipe_item(recipe, inventory_item_id, quantity, unit, user, **kwargs) → RecipeItem
#   remove_recipe_item(recipe_item, user) → None
#   activate_recipe(recipe, user) → Recipe
#   archive_recipe(recipe, user) → Recipe
#   calculate_recipe_cost(recipe) → dict
#   trigger_consumption_for_kitchen_order(kitchen_order, actor) → ConsumptionBatch | None
#   execute_consumption_batch(batch, actor) → ConsumptionBatch
#   reverse_consumption_batch(batch, user, reason) → ConsumptionBatch
#   manual_consume(branch, inventory_item, storage_location, quantity, unit, reason, user) → StockConsumption
#   get_or_create_branch_config(branch, **kwargs) → BranchConsumptionConfig
#
# Concurrency:
#   execute_consumption_batch uses select_for_update on all StockBalance rows
#   before any deduction — all-or-nothing atomicity.
#
# Security:
#   All mutating functions validate auth + permissions.
# =============================================================================

import logging
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from inventory.constants import (
    get_conversion_factor,
    are_units_compatible,
    DECIMAL_QTY as INV_DECIMAL_QTY,
    DECIMAL_COST as INV_DECIMAL_COST,
    ZERO as INV_ZERO,
    MOVEMENT_CONSUMPTION_REVERSAL as INV_MOVEMENT_CONSUMPTION_REVERSAL,
)
from recipes.constants import (
    RECIPE_DRAFT, RECIPE_ACTIVE, RECIPE_INACTIVE, RECIPE_ARCHIVED,
    BATCH_PENDING, BATCH_PROCESSING, BATCH_COMPLETED, BATCH_FAILED, BATCH_REVERSED,
    CONSUMPTION_CONSUMED, CONSUMPTION_REVERSED,
    REF_KITCHEN_ORDER, REF_MANUAL_CONSUMPTION, REF_CONSUMPTION_BATCH,
    MOVEMENT_CONSUMPTION, MOVEMENT_CONSUMPTION_REVERSAL,
    DECIMAL_QTY, DECIMAL_COST, ZERO,
    AUDIT_RECIPE_CREATED, AUDIT_RECIPE_UPDATED, AUDIT_RECIPE_ACTIVATED, AUDIT_RECIPE_ARCHIVED,
    AUDIT_CONSUMPTION_COMPLETED, AUDIT_CONSUMPTION_FAILED, AUDIT_CONSUMPTION_REVERSED,
    AUDIT_MANUAL_CONSUMPTION,
    DEFAULT_CONSUMPTION_TRIGGER, TRIGGER_KITCHEN_COMPLETED, TRIGGER_KITCHEN_STARTED,
)
from recipes.validators import (
    validate_recipe_belongs_to_restaurant,
    validate_recipe_activatable,
    validate_recipe_archivable,
    validate_recipe_has_ingredients,
    validate_no_duplicate_active_recipe,
    validate_recipe_item_quantity,
    validate_recipe_item_unit,
    validate_unit_compatibility,
    validate_unit_conversion_exists,
    validate_preparation_loss,
    validate_inventory_item_active,
    validate_cross_restaurant_ingredient,
    validate_order_confirmed,
    validate_sufficient_stock_for_consumption,
)
from recipes.selectors import (
    get_active_recipe_for_menu_item,
    get_existing_batch_for_order,
    get_default_consumption_location,
    get_consumption_trigger_for_branch,
)

logger = logging.getLogger("recipes")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_auth(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


def _qty(value) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_QTY, rounding=ROUND_HALF_UP)


def _cost(value) -> Decimal:
    return Decimal(str(value)).quantize(DECIMAL_COST, rounding=ROUND_HALF_UP)


def _convert_quantity(quantity: Decimal, from_unit: str, to_unit: str, item_name: str) -> Decimal:
    """
    Convert quantity from from_unit to to_unit.
    Raises ValidationError if no conversion path exists.
    """
    if from_unit == to_unit:
        return _qty(quantity)
    factor = get_conversion_factor(from_unit, to_unit)
    if factor is None:
        raise ValidationError({
            "code": "NO_CONVERSION_PATH",
            "message": (
                f"Cannot convert '{from_unit}' to '{to_unit}' for item '{item_name}'."
            ),
        })
    return _qty(quantity * factor)


def _log_recipe_event(action: str, recipe, actor, metadata: dict = None):
    """Simple structured audit log via Python logger (extend to DB model if needed)."""
    logger.info(
        "RECIPE_AUDIT action=%s recipe=%s version=%s status=%s actor=%s metadata=%s",
        action, recipe.id, recipe.version, recipe.status,
        getattr(actor, "email", "system"), metadata or {},
    )


def _log_consumption_event(action: str, batch, actor, metadata: dict = None):
    logger.info(
        "CONSUMPTION_AUDIT action=%s batch=%s order=%s status=%s actor=%s metadata=%s",
        action, batch.id, batch.order.order_number, batch.status,
        getattr(actor, "email", "system"), metadata or {},
    )


# =============================================================================
# 1. Recipe CRUD
# =============================================================================

def create_recipe(
    restaurant,
    menu_item,
    name: str,
    user,
    *,
    yield_quantity: Decimal = Decimal("1.000"),
    yield_unit: str = "PIECE",
    preparation_notes: str = "",
    effective_from=None,
    effective_to=None,
) -> "Recipe":
    """
    Create a new DRAFT recipe for a menu item.

    Auto-increments version per menu_item.
    Permission required: recipe.create
    """
    from recipes.models import Recipe

    _require_auth(user)
    if not acl.has_permission(user, "recipe.create"):
        raise PermissionDenied("You do not have permission to create recipes.")

    if not acl.can_access_restaurant(user, restaurant):
        raise PermissionDenied("You do not have access to this restaurant.")

    # Validate menu_item belongs to restaurant
    if str(menu_item.restaurant_id) != str(restaurant.pk):
        raise ValidationError({
            "code": "CROSS_RESTAURANT_MENU_ITEM",
            "message": "Menu item does not belong to this restaurant.",
        })

    if not menu_item.is_active:
        raise ValidationError({
            "code": "INACTIVE_MENU_ITEM",
            "message": f"Menu item '{menu_item.name}' is inactive.",
        })

    with transaction.atomic():
        # Determine next version — use select_for_update to prevent race
        from django.db.models import Max
        existing = Recipe.objects.filter(menu_item=menu_item).select_for_update().aggregate(
            max_version=Max("version")
        )
        next_version = (existing["max_version"] or 0) + 1

        recipe = Recipe.objects.create(
            restaurant=restaurant,
            menu_item=menu_item,
            name=name.strip(),
            version=next_version,
            status=RECIPE_DRAFT,
            yield_quantity=_qty(yield_quantity),
            yield_unit=yield_unit,
            preparation_notes=preparation_notes,
            effective_from=effective_from,
            effective_to=effective_to,
            created_by=user,
        )

    _log_recipe_event(AUDIT_RECIPE_CREATED, recipe, user)
    logger.info(
        "create_recipe: created recipe=%s v%s for menu_item=%s by user=%s",
        recipe.id, next_version, menu_item.name, user.email,
    )
    return recipe


def update_recipe(recipe, user, **kwargs) -> "Recipe":
    """
    Update a DRAFT recipe's metadata.
    Only DRAFT recipes can be edited.
    Permission required: recipe.update
    """
    _require_auth(user)
    if not acl.has_permission(user, "recipe.update"):
        raise PermissionDenied("You do not have permission to update recipes.")

    if recipe.status != RECIPE_DRAFT:
        raise ValidationError({
            "code": "RECIPE_NOT_DRAFT",
            "message": f"Only DRAFT recipes can be edited. This recipe is '{recipe.status}'.",
        })

    if not acl.can_access_restaurant(user, recipe.restaurant):
        raise PermissionDenied("You do not have access to this recipe's restaurant.")

    allowed_fields = {
        "name", "yield_quantity", "yield_unit",
        "preparation_notes", "effective_from", "effective_to",
    }
    changed = False
    for field, value in kwargs.items():
        if field in allowed_fields and value is not None:
            if field == "yield_quantity":
                value = _qty(value)
            if field == "name":
                value = value.strip()
            setattr(recipe, field, value)
            changed = True

    if changed:
        recipe.save()
        _log_recipe_event(AUDIT_RECIPE_UPDATED, recipe, user)

    return recipe


# =============================================================================
# 2. Recipe Items
# =============================================================================

def add_recipe_item(
    recipe,
    inventory_item_id,
    quantity,
    unit: str,
    user,
    *,
    preparation_loss_percentage: Decimal = Decimal("0"),
    notes: str = "",
    display_order: int = 0,
) -> "RecipeItem":
    """
    Add an ingredient to a DRAFT recipe.

    Validates:
        - recipe is DRAFT
        - inventory item exists, is active, belongs to same restaurant
        - quantity > 0
        - unit is valid and compatible with item's default_unit
        - no duplicate ingredient in this recipe

    Permission required: recipe.update
    """
    from recipes.models import RecipeItem
    from inventory.models import InventoryItem

    _require_auth(user)
    if not acl.has_permission(user, "recipe.update"):
        raise PermissionDenied("You do not have permission to update recipes.")

    if recipe.status != RECIPE_DRAFT:
        raise ValidationError({
            "code": "RECIPE_NOT_DRAFT",
            "message": "Ingredients can only be added to DRAFT recipes.",
        })

    # Resolve inventory item
    try:
        inventory_item = InventoryItem.objects.get(pk=inventory_item_id)
    except InventoryItem.DoesNotExist:
        raise ValidationError({
            "code": "INVENTORY_ITEM_NOT_FOUND",
            "message": f"Inventory item '{inventory_item_id}' not found.",
        })

    validate_inventory_item_active(inventory_item)
    validate_cross_restaurant_ingredient(recipe, inventory_item)
    validate_recipe_item_quantity(quantity)
    validate_recipe_item_unit(unit)
    validate_unit_compatibility(unit, inventory_item.default_unit, inventory_item.name)
    validate_unit_conversion_exists(unit, inventory_item.default_unit, inventory_item.name)
    validate_preparation_loss(preparation_loss_percentage)

    # Check for duplicate
    if RecipeItem.objects.filter(recipe=recipe, inventory_item=inventory_item).exists():
        raise ValidationError({
            "code": "DUPLICATE_INGREDIENT",
            "message": (
                f"Ingredient '{inventory_item.name}' already exists in this recipe. "
                "Use update to change its quantity."
            ),
        })

    recipe_item = RecipeItem.objects.create(
        recipe=recipe,
        inventory_item=inventory_item,
        quantity=_qty(quantity),
        unit=unit,
        preparation_loss_percentage=Decimal(str(preparation_loss_percentage)),
        notes=notes,
        display_order=display_order,
    )

    logger.info(
        "add_recipe_item: item=%s qty=%s %s added to recipe=%s by user=%s",
        inventory_item.name, quantity, unit, recipe.id, user.email,
    )
    return recipe_item


def remove_recipe_item(recipe_item, user) -> None:
    """
    Remove an ingredient from a DRAFT recipe.
    Permission required: recipe.update
    """
    _require_auth(user)
    if not acl.has_permission(user, "recipe.update"):
        raise PermissionDenied("You do not have permission to update recipes.")

    if recipe_item.recipe.status != RECIPE_DRAFT:
        raise ValidationError({
            "code": "RECIPE_NOT_DRAFT",
            "message": "Ingredients can only be removed from DRAFT recipes.",
        })

    recipe_item.delete()
    logger.info("remove_recipe_item: removed from recipe=%s by user=%s", recipe_item.recipe_id, user.email)


def update_recipe_item(
    recipe_item,
    user,
    *,
    quantity=None,
    unit=None,
    preparation_loss_percentage=None,
    notes=None,
    display_order=None,
) -> "RecipeItem":
    """
    Update a recipe ingredient line. Recipe must be DRAFT.
    Permission required: recipe.update
    """
    _require_auth(user)
    if not acl.has_permission(user, "recipe.update"):
        raise PermissionDenied("You do not have permission to update recipes.")

    if recipe_item.recipe.status != RECIPE_DRAFT:
        raise ValidationError({
            "code": "RECIPE_NOT_DRAFT",
            "message": "Ingredients can only be updated on DRAFT recipes.",
        })

    if quantity is not None:
        validate_recipe_item_quantity(quantity)
        recipe_item.quantity = _qty(quantity)

    if unit is not None:
        validate_recipe_item_unit(unit)
        validate_unit_compatibility(unit, recipe_item.inventory_item.default_unit, recipe_item.inventory_item.name)
        validate_unit_conversion_exists(unit, recipe_item.inventory_item.default_unit, recipe_item.inventory_item.name)
        recipe_item.unit = unit

    if preparation_loss_percentage is not None:
        validate_preparation_loss(preparation_loss_percentage)
        recipe_item.preparation_loss_percentage = Decimal(str(preparation_loss_percentage))

    if notes is not None:
        recipe_item.notes = notes

    if display_order is not None:
        recipe_item.display_order = display_order

    recipe_item.save()
    return recipe_item


# =============================================================================
# 3. Recipe Workflow
# =============================================================================

def activate_recipe(recipe, user) -> "Recipe":
    """
    Transition a DRAFT recipe to ACTIVE.

    Validates all ingredients, deactivates any previously active recipe
    for the same menu_item (within the same restaurant), and sets activation
    metadata.

    Permission required: recipe.activate
    """
    from recipes.models import Recipe

    _require_auth(user)
    if not acl.has_permission(user, "recipe.activate"):
        raise PermissionDenied("You do not have permission to activate recipes.")

    validate_recipe_activatable(recipe)
    validate_recipe_has_ingredients(recipe)

    # Validate all ingredients are still active and valid
    for item in recipe.items.select_related("inventory_item").all():
        validate_inventory_item_active(item.inventory_item)
        validate_cross_restaurant_ingredient(recipe, item.inventory_item)
        validate_unit_compatibility(item.unit, item.inventory_item.default_unit, item.inventory_item.name)
        validate_unit_conversion_exists(item.unit, item.inventory_item.default_unit, item.inventory_item.name)
        validate_recipe_item_quantity(item.quantity)

    with transaction.atomic():
        # Lock and check for existing active recipe
        existing_active = Recipe.objects.filter(
            menu_item=recipe.menu_item,
            status=RECIPE_ACTIVE,
        ).select_for_update().exclude(pk=recipe.pk).first()

        if existing_active:
            # Deactivate previous active recipe
            existing_active.status = RECIPE_INACTIVE
            existing_active.save(update_fields=["status", "updated_at"])
            logger.info(
                "activate_recipe: deactivated previous recipe=%s v%s for menu_item=%s",
                existing_active.id, existing_active.version, recipe.menu_item.name,
            )

        # Lock target recipe and activate
        locked = Recipe.objects.select_for_update().get(pk=recipe.pk)
        if locked.status != RECIPE_DRAFT:
            raise ValidationError({
                "code": "RECIPE_NOT_DRAFT",
                "message": "Recipe is no longer in DRAFT status.",
            })

        locked.status = RECIPE_ACTIVE
        locked.approved_by = user
        locked.approved_at = timezone.now()
        if not locked.effective_from:
            locked.effective_from = timezone.now()
        locked.save(update_fields=[
            "status", "approved_by", "approved_at", "effective_from", "updated_at"
        ])

    _log_recipe_event(AUDIT_RECIPE_ACTIVATED, locked, user)
    logger.info(
        "activate_recipe: recipe=%s v%s ACTIVE for menu_item=%s by user=%s",
        locked.id, locked.version, recipe.menu_item.name, user.email,
    )
    return locked


def archive_recipe(recipe, user) -> "Recipe":
    """
    Archive a recipe (DRAFT/ACTIVE/INACTIVE → ARCHIVED).
    ARCHIVED recipes are read-only historical records.
    Permission required: recipe.archive
    """
    _require_auth(user)
    if not acl.has_permission(user, "recipe.archive"):
        raise PermissionDenied("You do not have permission to archive recipes.")

    validate_recipe_archivable(recipe)

    with transaction.atomic():
        locked = recipe.__class__.objects.select_for_update().get(pk=recipe.pk)
        if locked.status not in ("DRAFT", "ACTIVE", "INACTIVE"):
            raise ValidationError({
                "code": "RECIPE_NOT_ARCHIVABLE",
                "message": f"Recipe cannot be archived from status '{locked.status}'.",
            })
        locked.status = RECIPE_ARCHIVED
        if locked.effective_to is None and locked.status != RECIPE_DRAFT:
            locked.effective_to = timezone.now()
        locked.save(update_fields=["status", "effective_to", "updated_at"])

    _log_recipe_event(AUDIT_RECIPE_ARCHIVED, locked, user)
    return locked


# =============================================================================
# 4. Recipe Cost Calculation
# =============================================================================

def calculate_recipe_cost(recipe) -> dict:
    """
    Calculate the estimated cost of producing one yield unit of this recipe.

    Returns:
        {
            "recipe_id": ...,
            "recipe_name": ...,
            "version": ...,
            "yield_quantity": ...,
            "yield_unit": ...,
            "total_cost": Decimal,
            "ingredients": [
                {
                    "inventory_item_id": ...,
                    "inventory_item_name": ...,
                    "recipe_quantity": ...,
                    "recipe_unit": ...,
                    "converted_quantity": ...,  # in item's default_unit
                    "item_unit": ...,
                    "effective_quantity": ...,  # after loss
                    "unit_cost": ...,
                    "line_cost": ...,
                },
                ...
            ]
        }

    Uses current InventoryItem.average_cost — does not modify any records.
    """
    ingredients = []
    total_cost = Decimal("0.00")

    for item in recipe.items.select_related("inventory_item").order_by("display_order"):
        inv_item = item.inventory_item
        effective_qty = item.effective_quantity  # includes loss %

        # Convert to item's default_unit
        converted_qty = _convert_quantity(
            effective_qty, item.unit, inv_item.default_unit, inv_item.name
        )

        unit_cost = _cost(inv_item.average_cost)
        line_cost = _cost(converted_qty * unit_cost)
        total_cost += line_cost

        ingredients.append({
            "inventory_item_id": str(inv_item.id),
            "inventory_item_name": inv_item.name,
            "recipe_quantity": str(item.quantity),
            "recipe_unit": item.unit,
            "preparation_loss_percentage": str(item.preparation_loss_percentage),
            "effective_quantity": str(effective_qty),
            "converted_quantity": str(converted_qty),
            "item_unit": inv_item.default_unit,
            "unit_cost": str(unit_cost),
            "line_cost": str(_cost(line_cost)),
        })

    return {
        "recipe_id": str(recipe.id),
        "recipe_name": recipe.name,
        "version": recipe.version,
        "status": recipe.status,
        "yield_quantity": str(recipe.yield_quantity),
        "yield_unit": recipe.yield_unit,
        "total_cost": str(_cost(total_cost)),
        "ingredients": ingredients,
    }


# =============================================================================
# 5. Consumption Calculation (scaling)
# =============================================================================

def calculate_required_ingredients(order) -> list[dict]:
    """
    Calculate total ingredient requirements for all items in an order.

    For each OrderItem:
        1. Find active Recipe for the menu_item
        2. For each RecipeItem:
            required = recipe_item.effective_quantity × order_item.quantity / recipe.yield_quantity
        3. Convert to inventory_item.default_unit
        4. Aggregate by (inventory_item, storage_location)

    Returns a list of dicts:
        [
            {
                "inventory_item": InventoryItem instance,
                "storage_location": StorageLocation instance,
                "quantity": Decimal (in item's default_unit),
                "unit": str (item's default_unit),
                "unit_cost": Decimal,
                "recipe": Recipe instance,
                "recipe_version": int,
                "order_item": OrderItem instance (first item contributing),
                "contributing_items": list of order_item references,
            },
            ...
        ]

    Raises ValidationError if:
        - Any menu_item has no active recipe
        - Any unit conversion fails
        - No consumption location is configured
    """
    from orders.models import OrderItem

    branch = order.branch
    storage_location = get_default_consumption_location(branch)

    if storage_location is None:
        raise ValidationError({
            "code": "NO_CONSUMPTION_LOCATION",
            "message": (
                f"Branch '{branch.name}' has no default consumption location configured. "
                "Please configure a default consumption location in branch settings."
            ),
        })

    if not storage_location.is_active:
        raise ValidationError({
            "code": "CONSUMPTION_LOCATION_INACTIVE",
            "message": (
                f"The default consumption location '{storage_location.name}' is inactive."
            ),
        })

    order_items = list(
        order.items.select_related("menu_item").all()
    )

    # Aggregation key: (inventory_item_id, storage_location_id)
    aggregated: dict[tuple, dict] = {}

    missing_recipes = []

    for order_item in order_items:
        menu_item = order_item.menu_item
        recipe = get_active_recipe_for_menu_item(menu_item)

        if recipe is None:
            missing_recipes.append(menu_item.name)
            continue

        order_qty = _qty(order_item.quantity)
        yield_qty = _qty(recipe.yield_quantity)

        for recipe_item in recipe.items.select_related("inventory_item").all():
            inv_item = recipe_item.inventory_item

            if not inv_item.is_active:
                raise ValidationError({
                    "code": "INACTIVE_INGREDIENT",
                    "message": (
                        f"Ingredient '{inv_item.name}' in recipe for '{menu_item.name}' "
                        "is inactive. Cannot process consumption."
                    ),
                })

            # scale: effective_qty_per_yield × order_qty / yield_qty
            effective_per_yield = recipe_item.effective_quantity
            scaled_qty = _qty(effective_per_yield * order_qty / yield_qty)

            # Convert to inventory item's default_unit
            converted_qty = _convert_quantity(
                scaled_qty, recipe_item.unit, inv_item.default_unit, inv_item.name
            )

            key = (str(inv_item.id), str(storage_location.id))
            if key in aggregated:
                aggregated[key]["quantity"] = _qty(aggregated[key]["quantity"] + converted_qty)
                aggregated[key]["contributing_items"].append(order_item)
            else:
                aggregated[key] = {
                    "inventory_item": inv_item,
                    "storage_location": storage_location,
                    "quantity": converted_qty,
                    "unit": inv_item.default_unit,
                    "unit_cost": _cost(inv_item.average_cost),
                    "recipe": recipe,
                    "recipe_version": recipe.version,
                    "order_item": order_item,
                    "contributing_items": [order_item],
                }

    if missing_recipes:
        raise ValidationError({
            "code": "MISSING_ACTIVE_RECIPE",
            "message": (
                f"No active recipe found for: {', '.join(missing_recipes)}. "
                "All menu items in the order must have an active recipe before "
                "inventory consumption can proceed."
            ),
        })

    return list(aggregated.values())


# =============================================================================
# 6. Consumption Execution
# =============================================================================

def trigger_consumption_for_kitchen_order(kitchen_order, actor) -> "ConsumptionBatch | None":
    """
    Entry point called by the kitchen service when a KitchenOrder reaches
    the configured trigger status (READY for KITCHEN_COMPLETED).

    Idempotent: if a batch already exists for this order+trigger, returns it.

    Does NOT raise if consumption fails — records failure reason on batch.
    Returns the ConsumptionBatch (completed or failed).
    """
    from recipes.models import ConsumptionBatch

    order = kitchen_order.order
    branch = kitchen_order.branch
    trigger = get_consumption_trigger_for_branch(branch)

    # Verify this event matches the configured trigger
    from kitchen.models import KitchenOrderStatus
    trigger_status_map = {
        TRIGGER_KITCHEN_COMPLETED: KitchenOrderStatus.READY,
        TRIGGER_KITCHEN_STARTED:   KitchenOrderStatus.PREPARING,
    }
    expected_status = trigger_status_map.get(trigger)
    if expected_status and kitchen_order.status != expected_status:
        logger.debug(
            "trigger_consumption: kitchen_order=%s status=%s does not match trigger=%s — skipping",
            kitchen_order.order_number, kitchen_order.status, trigger,
        )
        return None

    # Idempotency: check for existing batch
    existing = get_existing_batch_for_order(order, trigger)
    if existing:
        logger.info(
            "trigger_consumption: idempotent — batch=%s already exists for order=%s trigger=%s",
            existing.id, order.order_number, trigger,
        )
        return existing

    # Create batch in PENDING state
    idempotency_key = f"{order.id}:{trigger}"
    try:
        with transaction.atomic():
            batch = ConsumptionBatch.objects.create(
                order=order,
                branch=branch,
                idempotency_key=idempotency_key,
                status=BATCH_PENDING,
                triggered_by=actor,
                triggered_at=timezone.now(),
                trigger=trigger,
            )
    except IntegrityError:
        # Race: another process created this batch concurrently
        existing = get_existing_batch_for_order(order, trigger)
        if existing:
            return existing
        raise

    logger.info(
        "trigger_consumption: created batch=%s for order=%s trigger=%s",
        batch.id, order.order_number, trigger,
    )

    # Execute consumption
    return execute_consumption_batch(batch, actor)


def execute_consumption_batch(batch, actor) -> "ConsumptionBatch":
    """
    Execute all ingredient consumptions for a ConsumptionBatch.

    Algorithm:
        1. Lock the batch record
        2. Calculate all required ingredients (aggregated)
        3. Lock all StockBalance rows
        4. Validate sufficient stock for ALL ingredients
        5. Deduct stock + create StockMovement for each ingredient
        6. Create StockConsumption records
        7. Mark batch COMPLETED
        8. On any failure: rollback entire transaction, mark batch FAILED

    This is fully atomic — all deductions or none.
    """
    from recipes.models import ConsumptionBatch, StockConsumption
    from inventory.models import StockBalance, StockMovement
    from inventory.services import decrease_stock
    from inventory.constants import MOVEMENT_CONSUMPTION as INV_MOVEMENT_CONSUMPTION

    order = batch.order

    try:
        with transaction.atomic():
            # Lock the batch
            locked_batch = ConsumptionBatch.objects.select_for_update().get(pk=batch.pk)

            # Guard: already processed
            if locked_batch.status in (BATCH_COMPLETED, BATCH_REVERSED):
                return locked_batch

            if locked_batch.status == BATCH_PROCESSING:
                logger.warning(
                    "execute_consumption_batch: batch=%s already PROCESSING — concurrent call?",
                    batch.id,
                )
                return locked_batch

            locked_batch.status = BATCH_PROCESSING
            locked_batch.save(update_fields=["status", "updated_at"])

            # Calculate requirements
            requirements = calculate_required_ingredients(order)

            if not requirements:
                locked_batch.status = BATCH_COMPLETED
                locked_batch.completed_at = timezone.now()
                locked_batch.save(update_fields=["status", "completed_at", "updated_at"])
                logger.info(
                    "execute_consumption_batch: no requirements for batch=%s (all items may lack recipes)",
                    batch.id,
                )
                return locked_batch

            # Lock ALL StockBalance rows (sorted to prevent deadlock)
            inv_item_ids = sorted(str(r["inventory_item"].id) for r in requirements)
            loc_ids = sorted(str(r["storage_location"].id) for r in requirements)

            # Lock in consistent order
            balances_locked = {}
            for req in sorted(requirements, key=lambda r: str(r["inventory_item"].id)):
                inv_item = req["inventory_item"]
                loc = req["storage_location"]
                key = (str(inv_item.id), str(loc.id))

                balance, _ = StockBalance.objects.get_or_create(
                    inventory_item=inv_item,
                    storage_location=loc,
                )
                # Re-lock
                balance = StockBalance.objects.select_for_update().get(
                    inventory_item=inv_item,
                    storage_location=loc,
                )
                balances_locked[key] = balance

            # Validate ALL before deducting ANY
            for req in requirements:
                key = (str(req["inventory_item"].id), str(req["storage_location"].id))
                balance = balances_locked[key]
                available = balance.available_quantity
                required = req["quantity"]
                if available < required:
                    raise ValidationError({
                        "code": "INSUFFICIENT_STOCK",
                        "message": (
                            f"Insufficient stock for '{req['inventory_item'].name}' at "
                            f"'{req['storage_location'].name}'. "
                            f"Required: {required} {req['unit']}, "
                            f"Available: {available} {req['unit']}."
                        ),
                    })

            # All stock OK — deduct + create movements + create consumption records
            now = timezone.now()
            consumption_records = []

            for req in requirements:
                inv_item = req["inventory_item"]
                loc = req["storage_location"]
                qty = req["quantity"]
                unit_cost = _cost(inv_item.average_cost)

                # Deduct stock via the existing service
                movement = decrease_stock(
                    inventory_item=inv_item,
                    storage_location=loc,
                    quantity=qty,
                    movement_type=INV_MOVEMENT_CONSUMPTION,
                    performed_by=actor,
                    reference_type=REF_CONSUMPTION_BATCH,
                    reference_id=batch.id,
                    reason=f"Consumption for order {order.order_number}",
                    unit_cost=unit_cost,
                )

                consumption = StockConsumption(
                    batch=locked_batch,
                    order=order,
                    order_item=req["order_item"],
                    restaurant=order.branch.restaurant,
                    branch=order.branch,
                    recipe=req["recipe"],
                    recipe_version=req["recipe_version"],
                    inventory_item=inv_item,
                    storage_location=loc,
                    quantity=qty,
                    unit=inv_item.default_unit,
                    unit_cost=unit_cost,
                    total_cost=_cost(qty * unit_cost),
                    status=CONSUMPTION_CONSUMED,
                    consumed_at=now,
                    consumed_by=actor,
                    reference_type=REF_KITCHEN_ORDER,
                    reference_id=kitchen_order_id_from_batch(batch),
                    stock_movement=movement,
                )
                consumption_records.append(consumption)

            StockConsumption.objects.bulk_create(consumption_records)

            locked_batch.status = BATCH_COMPLETED
            locked_batch.completed_at = now
            locked_batch.save(update_fields=["status", "completed_at", "updated_at"])

    except ValidationError as exc:
        _mark_batch_failed(batch, str(exc.detail))
        _log_consumption_event(AUDIT_CONSUMPTION_FAILED, batch, actor, {"error": str(exc.detail)})
        logger.error(
            "execute_consumption_batch: batch=%s FAILED order=%s error=%s",
            batch.id, order.order_number, exc.detail,
        )
        # Re-fetch to return updated state
        batch.refresh_from_db()
        return batch
    except Exception as exc:
        _mark_batch_failed(batch, str(exc))
        logger.exception(
            "execute_consumption_batch: batch=%s FAILED order=%s unexpected error=%s",
            batch.id, order.order_number, exc,
        )
        batch.refresh_from_db()
        return batch

    _log_consumption_event(AUDIT_CONSUMPTION_COMPLETED, locked_batch, actor)
    logger.info(
        "execute_consumption_batch: batch=%s COMPLETED order=%s items=%d",
        locked_batch.id, order.order_number, len(consumption_records),
    )
    return locked_batch


def kitchen_order_id_from_batch(batch) -> "uuid.UUID | None":
    """Helper: get the kitchen_order UUID from a batch's order."""
    try:
        return batch.order.kitchen_order.id
    except Exception:
        return None


def _mark_batch_failed(batch, reason: str) -> None:
    """Mark a batch as FAILED outside the main transaction (separate atomic)."""
    try:
        with transaction.atomic():
            ConsumptionBatch = batch.__class__
            ConsumptionBatch.objects.filter(pk=batch.pk).update(
                status=BATCH_FAILED,
                failure_reason=reason[:2000],
                updated_at=timezone.now(),
            )
    except Exception:
        pass


# =============================================================================
# 7. Consumption Reversal
# =============================================================================

def reverse_consumption_batch(batch, user, reason: str = "") -> "ConsumptionBatch":
    """
    Reverse a completed consumption batch.

    Creates:
        - New StockConsumption records with status=REVERSED
        - CONSUMPTION_REVERSAL StockMovement records (increases stock)
        - Marks batch status=REVERSED

    Only COMPLETED batches can be reversed.
    Permission required: inventory.consumption.reverse
    """
    from recipes.models import ConsumptionBatch, StockConsumption
    from inventory.services import increase_stock

    _require_auth(user)
    if not acl.has_permission(user, "inventory.consumption.reverse"):
        raise PermissionDenied("You do not have permission to reverse inventory consumption.")

    if batch.status != BATCH_COMPLETED:
        raise ValidationError({
            "code": "BATCH_NOT_COMPLETED",
            "message": f"Only COMPLETED batches can be reversed. Batch status: '{batch.status}'.",
        })

    with transaction.atomic():
        locked = ConsumptionBatch.objects.select_for_update().get(pk=batch.pk)

        if locked.status != BATCH_COMPLETED:
            raise ValidationError({
                "code": "BATCH_NOT_COMPLETED",
                "message": "Batch is no longer COMPLETED.",
            })

        now = timezone.now()
        reversal_records = []

        for consumption in locked.consumptions.filter(status=CONSUMPTION_CONSUMED).select_related(
            "inventory_item", "storage_location"
        ).all():
            # Return stock
            movement = increase_stock(
                inventory_item=consumption.inventory_item,
                storage_location=consumption.storage_location,
                quantity=consumption.quantity,
                unit_cost=consumption.unit_cost,
                movement_type=INV_MOVEMENT_CONSUMPTION_REVERSAL,
                performed_by=user,
                reference_type=REF_CONSUMPTION_BATCH,
                reference_id=batch.id,
                reason=reason or f"Reversal of consumption batch {batch.id}",
            )

            reversal_records.append(StockConsumption(
                batch=locked,
                order=consumption.order,
                order_item=consumption.order_item,
                restaurant=consumption.restaurant,
                branch=consumption.branch,
                recipe=consumption.recipe,
                recipe_version=consumption.recipe_version,
                inventory_item=consumption.inventory_item,
                storage_location=consumption.storage_location,
                quantity=consumption.quantity,
                unit=consumption.unit,
                unit_cost=consumption.unit_cost,
                total_cost=consumption.total_cost,
                status=CONSUMPTION_REVERSED,
                consumed_at=now,
                consumed_by=user,
                reference_type="CONSUMPTION_REVERSAL",
                reference_id=batch.id,
                stock_movement=movement,
            ))

        StockConsumption.objects.bulk_create(reversal_records)

        # Mark original consumptions as reversed
        locked.consumptions.filter(status=CONSUMPTION_CONSUMED).update(
            status=CONSUMPTION_REVERSED, updated_at=now
        )

        locked.status = BATCH_REVERSED
        locked.save(update_fields=["status", "updated_at"])

    _log_consumption_event(AUDIT_CONSUMPTION_REVERSED, locked, user, {"reason": reason})
    logger.info(
        "reverse_consumption_batch: batch=%s REVERSED by user=%s reason='%s'",
        batch.id, user.email, reason,
    )
    return locked


# =============================================================================
# 8. Manual Consumption
# =============================================================================

def manual_consume(
    branch,
    inventory_item,
    storage_location,
    quantity: Decimal,
    unit: str,
    reason: str,
    user,
) -> "StockConsumption":
    """
    Perform a controlled manual inventory consumption.

    Creates:
        - A standalone ConsumptionBatch
        - One StockConsumption record
        - A CONSUMPTION StockMovement

    Permission required: inventory.consumption.manual
    """
    from recipes.models import ConsumptionBatch, StockConsumption
    from inventory.services import decrease_stock
    from inventory.constants import MOVEMENT_CONSUMPTION as INV_MOVEMENT_CONSUMPTION

    _require_auth(user)
    if not acl.has_permission(user, "inventory.consumption.manual"):
        raise PermissionDenied("You do not have permission to perform manual consumption.")

    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    if not reason or not reason.strip():
        raise ValidationError({
            "code": "REASON_REQUIRED",
            "message": "A reason is required for manual consumption.",
        })

    validate_recipe_item_quantity(quantity)
    validate_recipe_item_unit(unit)
    validate_unit_compatibility(unit, inventory_item.default_unit, inventory_item.name)
    validate_unit_conversion_exists(unit, inventory_item.default_unit, inventory_item.name)
    validate_inventory_item_active(inventory_item)

    # Convert to item's default_unit
    converted_qty = _convert_quantity(quantity, unit, inventory_item.default_unit, inventory_item.name)

    if not storage_location.is_active:
        raise ValidationError({
            "code": "INACTIVE_STORAGE_LOCATION",
            "message": f"Storage location '{storage_location.name}' is inactive.",
        })

    if str(storage_location.branch_id) != str(branch.pk):
        raise ValidationError({
            "code": "LOCATION_BRANCH_MISMATCH",
            "message": "Storage location does not belong to this branch.",
        })

    now = timezone.now()

    with transaction.atomic():
        validate_sufficient_stock_for_consumption(inventory_item, storage_location, converted_qty)

        unit_cost = _cost(inventory_item.average_cost)

        movement = decrease_stock(
            inventory_item=inventory_item,
            storage_location=storage_location,
            quantity=converted_qty,
            movement_type=INV_MOVEMENT_CONSUMPTION,
            performed_by=user,
            reference_type=REF_MANUAL_CONSUMPTION,
            reason=reason.strip(),
            unit_cost=unit_cost,
        )

        # Create a batch for grouping (no order FK — use a dummy batch)
        batch = ConsumptionBatch.objects.create(
            order=None,
            branch=branch,
            idempotency_key=f"manual:{user.id}:{now.isoformat()}:{inventory_item.id}",
            status=BATCH_COMPLETED,
            triggered_by=user,
            triggered_at=now,
            completed_at=now,
            trigger="MANUAL",
        )

        consumption = StockConsumption.objects.create(
            batch=batch,
            order=None,
            restaurant=branch.restaurant,
            branch=branch,
            inventory_item=inventory_item,
            storage_location=storage_location,
            quantity=converted_qty,
            unit=inventory_item.default_unit,
            unit_cost=unit_cost,
            total_cost=_cost(converted_qty * unit_cost),
            status=CONSUMPTION_CONSUMED,
            consumed_at=now,
            consumed_by=user,
            reference_type=REF_MANUAL_CONSUMPTION,
            stock_movement=movement,
        )

    _log_consumption_event(AUDIT_MANUAL_CONSUMPTION, batch, user, {"reason": reason, "item": inventory_item.name})
    logger.info(
        "manual_consume: item=%s qty=%s %s by user=%s reason='%s'",
        inventory_item.name, converted_qty, inventory_item.default_unit, user.email, reason,
    )
    return consumption


# =============================================================================
# 9. Branch Config
# =============================================================================

def get_or_create_branch_config(branch, user, *, consumption_trigger=None, default_consumption_location=None):
    """
    Create or update a branch consumption config.
    Permission required: inventory.update (reusing existing inventory permission)
    """
    from recipes.models import BranchConsumptionConfig

    _require_auth(user)
    if not acl.has_permission(user, "inventory.update"):
        raise PermissionDenied("You do not have permission to configure branch consumption.")

    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    config, created = BranchConsumptionConfig.objects.get_or_create(branch=branch)

    changed = False
    if consumption_trigger is not None:
        from recipes.constants import CONSUMPTION_TRIGGER_CHOICES
        valid_triggers = {code for code, _ in CONSUMPTION_TRIGGER_CHOICES}
        if consumption_trigger not in valid_triggers:
            raise ValidationError({
                "code": "INVALID_TRIGGER",
                "message": f"Invalid consumption trigger. Valid options: {', '.join(valid_triggers)}.",
            })
        config.consumption_trigger = consumption_trigger
        changed = True

    if default_consumption_location is not None:
        from inventory.models import StorageLocation
        if str(default_consumption_location.branch_id) != str(branch.pk):
            raise ValidationError({
                "code": "LOCATION_BRANCH_MISMATCH",
                "message": "Storage location does not belong to this branch.",
            })
        if not default_consumption_location.is_active:
            raise ValidationError({
                "code": "INACTIVE_LOCATION",
                "message": "Consumption location must be active.",
            })
        config.default_consumption_location = default_consumption_location
        changed = True

    if changed or created:
        config.save()

    return config
