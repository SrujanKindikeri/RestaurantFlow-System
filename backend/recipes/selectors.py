# =============================================================================
# RestaurantFlow — Recipe Selectors
# Phase 11
#
# Read-only query helpers for the recipes domain.
# Views and services import from here for all queryset access.
# =============================================================================

import logging
from django.utils import timezone

logger = logging.getLogger("recipes")


# ---------------------------------------------------------------------------
# Recipe selectors
# ---------------------------------------------------------------------------

def get_recipe_by_id(recipe_id, *, user=None):
    """Fetch a Recipe by UUID. Returns None if not found."""
    from recipes.models import Recipe
    try:
        return Recipe.objects.select_related(
            "menu_item", "restaurant", "created_by", "approved_by"
        ).prefetch_related("items__inventory_item").get(pk=recipe_id)
    except Recipe.DoesNotExist:
        return None


def get_recipes_for_restaurant(restaurant, *, status=None, menu_item=None):
    """Return all recipes for a restaurant, optionally filtered."""
    from recipes.models import Recipe
    qs = Recipe.objects.filter(restaurant=restaurant).select_related(
        "menu_item", "created_by", "approved_by"
    ).prefetch_related("items__inventory_item")
    if status:
        if isinstance(status, (list, tuple)):
            qs = qs.filter(status__in=status)
        else:
            qs = qs.filter(status=status)
    if menu_item:
        qs = qs.filter(menu_item=menu_item)
    return qs.order_by("menu_item__name", "-version")


def get_active_recipe_for_menu_item(menu_item, *, at_time=None):
    """
    Return the ACTIVE recipe for a menu_item at the given time.

    Resolves effective_from / effective_to if set.
    Falls back to any ACTIVE recipe if no time-based filtering narrows it down.
    Returns None if no active recipe exists.
    """
    from recipes.models import Recipe
    from recipes.constants import RECIPE_ACTIVE

    at_time = at_time or timezone.now()

    qs = Recipe.objects.filter(
        menu_item=menu_item,
        status=RECIPE_ACTIVE,
    ).prefetch_related("items__inventory_item")

    # Prefer recipes with valid effective date window
    dated = qs.filter(
        effective_from__lte=at_time,
    ).filter(
        effective_to__isnull=True
    ) | qs.filter(
        effective_from__lte=at_time,
        effective_to__gte=at_time,
    ) | qs.filter(
        effective_from__isnull=True,
        effective_to__isnull=True,
    )

    # If any dated match, return the most recently activated
    recipe = dated.order_by("-version").first()
    if recipe:
        return recipe

    # Fallback: any ACTIVE recipe for this menu item
    return qs.order_by("-version").first()


def get_recipe_versions_for_menu_item(menu_item):
    """Return all recipe versions for a menu item, newest first."""
    from recipes.models import Recipe
    return Recipe.objects.filter(menu_item=menu_item).order_by("-version").select_related(
        "created_by", "approved_by"
    ).prefetch_related("items__inventory_item")


# ---------------------------------------------------------------------------
# Consumption selectors
# ---------------------------------------------------------------------------

def get_consumption_batch_by_id(batch_id, *, user=None):
    from recipes.models import ConsumptionBatch
    try:
        return ConsumptionBatch.objects.select_related(
            "order", "branch", "triggered_by"
        ).prefetch_related("consumptions__inventory_item", "consumptions__storage_location").get(pk=batch_id)
    except ConsumptionBatch.DoesNotExist:
        return None


def get_consumption_batches_for_order(order):
    """Return all consumption batches for an order."""
    from recipes.models import ConsumptionBatch
    return ConsumptionBatch.objects.filter(order=order).select_related(
        "branch", "triggered_by"
    ).prefetch_related("consumptions__inventory_item").order_by("-triggered_at")


def get_consumption_batches_for_branch(branch, *, status=None, date=None):
    """Return consumption batches for a branch, optionally filtered."""
    from recipes.models import ConsumptionBatch
    qs = ConsumptionBatch.objects.filter(branch=branch).select_related(
        "order", "triggered_by"
    ).order_by("-triggered_at")
    if status:
        qs = qs.filter(status=status)
    if date:
        qs = qs.filter(triggered_at__date=date)
    return qs


def get_stock_consumptions_for_order(order):
    """Return all stock consumption records for an order."""
    from recipes.models import StockConsumption
    return StockConsumption.objects.filter(order=order).select_related(
        "inventory_item", "storage_location", "recipe", "order_item"
    ).order_by("created_at")


def get_existing_batch_for_order(order, trigger: str):
    """
    Return existing ConsumptionBatch for order+trigger idempotency check.
    Returns None if not found.
    """
    from recipes.models import ConsumptionBatch
    key = f"{order.id}:{trigger}"
    try:
        return ConsumptionBatch.objects.get(idempotency_key=key)
    except ConsumptionBatch.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Config selectors
# ---------------------------------------------------------------------------

def get_branch_consumption_config(branch):
    """
    Return the BranchConsumptionConfig for a branch, or None if not configured.
    """
    from recipes.models import BranchConsumptionConfig
    try:
        return BranchConsumptionConfig.objects.select_related(
            "default_consumption_location"
        ).get(branch=branch)
    except BranchConsumptionConfig.DoesNotExist:
        return None


def get_default_consumption_location(branch):
    """
    Return the default StorageLocation for consumption at this branch.
    Returns None if not configured.
    """
    config = get_branch_consumption_config(branch)
    if config and config.default_consumption_location_id:
        return config.default_consumption_location
    return None


def get_consumption_trigger_for_branch(branch) -> str:
    """
    Return the configured consumption trigger for this branch.
    Falls back to DEFAULT_CONSUMPTION_TRIGGER if not configured.
    """
    from recipes.constants import DEFAULT_CONSUMPTION_TRIGGER
    config = get_branch_consumption_config(branch)
    if config:
        return config.consumption_trigger
    return DEFAULT_CONSUMPTION_TRIGGER
