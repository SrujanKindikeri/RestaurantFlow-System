# =============================================================================
# RestaurantFlow — Recipes Access Control
# Phase 11
#
# Single source of truth for recipes authorization decisions.
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("recipes")


def get_accessible_recipes(user):
    """Return recipes accessible to this user (scoped by restaurant)."""
    from recipes.models import Recipe
    if not user or not user.is_authenticated or not user.is_active:
        return Recipe.objects.none()
    if user.is_superuser or user.is_staff:
        return Recipe.objects.all()
    accessible_restaurants = acl.get_accessible_restaurants(user)
    return Recipe.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_consumption_batches(user):
    """Return consumption batches accessible to this user (scoped by branch)."""
    from recipes.models import ConsumptionBatch
    if not user or not user.is_authenticated or not user.is_active:
        return ConsumptionBatch.objects.none()
    if user.is_superuser or user.is_staff:
        return ConsumptionBatch.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return ConsumptionBatch.objects.filter(branch__in=accessible_branches)


def get_accessible_stock_consumptions(user):
    """Return stock consumptions accessible to this user (scoped by branch)."""
    from recipes.models import StockConsumption
    if not user or not user.is_authenticated or not user.is_active:
        return StockConsumption.objects.none()
    if user.is_superuser or user.is_staff:
        return StockConsumption.objects.all()
    accessible_branches = acl.get_accessible_branches(user)
    return StockConsumption.objects.filter(branch__in=accessible_branches)
