# =============================================================================
# RestaurantFlow — Recipes DRF Permission Classes
# Phase 11
#
# All authorization logic delegates to recipes.access and accounts.access.
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

# Re-export HasPermission factory for convenience
from accounts.permissions import HasPermission  # noqa: F401

logger = logging.getLogger("recipes")


class HasRecipeAccess(BasePermission):
    """Object-level: user must be able to access this Recipe."""

    message = "You do not have access to this recipe."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from recipes.access import get_accessible_recipes
        return get_accessible_recipes(request.user).filter(pk=obj.pk).exists()


class HasConsumptionBatchAccess(BasePermission):
    """Object-level: user must be able to access this ConsumptionBatch."""

    message = "You do not have access to this consumption batch."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from recipes.access import get_accessible_consumption_batches
        return get_accessible_consumption_batches(request.user).filter(pk=obj.pk).exists()
