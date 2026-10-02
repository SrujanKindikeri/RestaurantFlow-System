# =============================================================================
# RestaurantFlow — Menu DRF Permission Classes
# Phase 5
#
# Mirrors the pattern in accounts/permissions.py and counters/permissions.py.
# All authorization delegates to menu.access or accounts.access.
#
# Object-level permissions:
#   HasMenuItemAccess       — for MenuItem instances
#   HasCategoryAccess       — for Category instances
#   HasMenuPriceAccess      — for MenuItemPrice instances
#   HasAvailabilityAccess   — for MenuItemBranch instances
#   HasTaxRateAccess        — for TaxRate instances
#
# Use together with the HasPermission() factory from accounts.permissions:
#   permission_classes = [IsAuthenticated, HasPermission("menu.view"), HasMenuItemAccess()]
# =============================================================================

import logging
from rest_framework.permissions import BasePermission

from menu import access as menu_acl

logger = logging.getLogger("menu")


class HasMenuItemAccess(BasePermission):
    """Object-level permission: user must have access to the MenuItem's restaurant."""

    message = "You do not have access to this menu item."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from menu.models import MenuItem
        if not isinstance(obj, MenuItem):
            return False
        result = menu_acl.can_access_restaurant_menu(request.user, obj.restaurant)
        if not result:
            logger.warning(
                "MenuItem access denied: user=%s item=%s",
                request.user.email, obj.pk,
            )
        return result


class HasCategoryAccess(BasePermission):
    """Object-level permission: user must have access to the Category's restaurant."""

    message = "You do not have access to this category."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from menu.models import Category
        if not isinstance(obj, Category):
            return False
        result = menu_acl.can_access_restaurant_menu(request.user, obj.restaurant)
        if not result:
            logger.warning(
                "Category access denied: user=%s category=%s",
                request.user.email, obj.pk,
            )
        return result


class HasMenuPriceAccess(BasePermission):
    """Object-level permission: user must have access to the price's restaurant."""

    message = "You do not have access to this menu price."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from menu.models import MenuItemPrice
        if not isinstance(obj, MenuItemPrice):
            return False
        result = menu_acl.can_access_restaurant_menu(
            request.user, obj.menu_item.restaurant
        )
        if not result:
            logger.warning(
                "MenuItemPrice access denied: user=%s price=%s",
                request.user.email, obj.pk,
            )
        return result


class HasAvailabilityAccess(BasePermission):
    """Object-level permission: user must have access to the availability record's restaurant."""

    message = "You do not have access to this availability record."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from menu.models import MenuItemBranch
        if not isinstance(obj, MenuItemBranch):
            return False
        result = menu_acl.can_access_restaurant_menu(
            request.user, obj.menu_item.restaurant
        )
        if not result:
            logger.warning(
                "MenuItemBranch access denied: user=%s record=%s",
                request.user.email, obj.pk,
            )
        return result


class HasTaxRateAccess(BasePermission):
    """Object-level permission: user must have access to the TaxRate's restaurant."""

    message = "You do not have access to this tax rate."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from menu.models import TaxRate
        if not isinstance(obj, TaxRate):
            return False
        result = menu_acl.can_access_restaurant_menu(request.user, obj.restaurant)
        if not result:
            logger.warning(
                "TaxRate access denied: user=%s rate=%s",
                request.user.email, obj.pk,
            )
        return result
