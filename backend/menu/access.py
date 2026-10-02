# =============================================================================
# RestaurantFlow — Menu Access Control
# Phase 5
#
# Single source of truth for menu-related authorization decisions.
# Delegates org/restaurant/branch scope to accounts.access.
#
# Public API:
#   get_accessible_categories(user)           → QuerySet[Category]
#   get_accessible_menu_items(user)           → QuerySet[MenuItem]
#   get_accessible_prices(user)               → QuerySet[MenuItemPrice]
#   get_accessible_branch_availability(user)  → QuerySet[MenuItemBranch]
#   get_accessible_tax_rates(user)            → QuerySet[TaxRate]
#   can_access_restaurant_menu(user, restaurant) → bool
#   can_access_branch_menu(user, branch)         → bool
# =============================================================================

import logging

from accounts import access as acl

logger = logging.getLogger("menu")


def _accessible_restaurant_ids(user):
    """Return a flat list of restaurant PKs the user can access."""
    return acl.get_accessible_restaurants(user).values_list("pk", flat=True)


def _accessible_branch_ids(user):
    """Return a flat list of branch PKs the user can access."""
    return acl.get_accessible_branches(user).values_list("pk", flat=True)


# ---------------------------------------------------------------------------
# TaxRate
# ---------------------------------------------------------------------------

def get_accessible_tax_rates(user):
    from menu.models import TaxRate

    if not user or not user.is_authenticated or not user.is_active:
        return TaxRate.objects.none()

    if user.is_superuser or user.is_staff:
        return TaxRate.objects.select_related("restaurant__organization")

    return TaxRate.objects.filter(
        restaurant_id__in=_accessible_restaurant_ids(user)
    ).select_related("restaurant__organization")


# ---------------------------------------------------------------------------
# Category
# ---------------------------------------------------------------------------

def get_accessible_categories(user):
    from menu.models import Category

    if not user or not user.is_authenticated or not user.is_active:
        return Category.objects.none()

    if user.is_superuser or user.is_staff:
        return Category.objects.select_related("restaurant__organization")

    return Category.objects.filter(
        restaurant_id__in=_accessible_restaurant_ids(user)
    ).select_related("restaurant__organization")


# ---------------------------------------------------------------------------
# MenuItem
# ---------------------------------------------------------------------------

def get_accessible_menu_items(user):
    from menu.models import MenuItem

    if not user or not user.is_authenticated or not user.is_active:
        return MenuItem.objects.none()

    if user.is_superuser or user.is_staff:
        return MenuItem.objects.select_related(
            "restaurant__organization",
            "category",
            "tax_rate",
        )

    return MenuItem.objects.filter(
        restaurant_id__in=_accessible_restaurant_ids(user)
    ).select_related(
        "restaurant__organization",
        "category",
        "tax_rate",
    )


# ---------------------------------------------------------------------------
# MenuItemPrice
# ---------------------------------------------------------------------------

def get_accessible_prices(user):
    from menu.models import MenuItemPrice

    if not user or not user.is_authenticated or not user.is_active:
        return MenuItemPrice.objects.none()

    if user.is_superuser or user.is_staff:
        return MenuItemPrice.objects.select_related(
            "menu_item__restaurant__organization",
            "menu_item__category",
            "branch__restaurant",
        )

    return MenuItemPrice.objects.filter(
        menu_item__restaurant_id__in=_accessible_restaurant_ids(user)
    ).select_related(
        "menu_item__restaurant__organization",
        "menu_item__category",
        "branch__restaurant",
    )


# ---------------------------------------------------------------------------
# MenuItemBranch (availability)
# ---------------------------------------------------------------------------

def get_accessible_branch_availability(user):
    from menu.models import MenuItemBranch

    if not user or not user.is_authenticated or not user.is_active:
        return MenuItemBranch.objects.none()

    if user.is_superuser or user.is_staff:
        return MenuItemBranch.objects.select_related(
            "menu_item__restaurant__organization",
            "menu_item__category",
            "branch__restaurant",
        )

    return MenuItemBranch.objects.filter(
        menu_item__restaurant_id__in=_accessible_restaurant_ids(user)
    ).select_related(
        "menu_item__restaurant__organization",
        "menu_item__category",
        "branch__restaurant",
    )


# ---------------------------------------------------------------------------
# Resource-level checks
# ---------------------------------------------------------------------------

def can_access_restaurant_menu(user, restaurant) -> bool:
    """True if the user can access menu data for this restaurant."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_restaurant(user, restaurant)


def can_access_branch_menu(user, branch) -> bool:
    """True if the user can access menu data for this branch."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_branch(user, branch)
