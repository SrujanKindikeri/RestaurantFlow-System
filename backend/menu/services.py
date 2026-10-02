# =============================================================================
# RestaurantFlow — Menu Services
# Phase 5
#
# Business logic for menu operations.
#
# Services:
#   is_menu_item_available(menu_item, branch, current_time) → bool
#   get_branch_catalog(branch, user)    → structured catalog dict
#   set_item_active(actor, item, is_active)   → MenuItem
#   set_category_active(actor, cat, is_active) → Category
#   set_tax_rate_active(actor, rate, is_active) → TaxRate
#   deactivate_price(actor, price)      → MenuItemPrice
# =============================================================================

import logging
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl

logger = logging.getLogger("menu")


# ---------------------------------------------------------------------------
# Availability
# ---------------------------------------------------------------------------

def is_menu_item_available(menu_item, branch, current_time=None) -> bool:
    """
    Determine whether a menu item is currently available at a branch.

    Checks (Phase 5):
        1. menu_item.is_active
        2. branch.is_active
        3. MenuItemBranch record exists and is_available=True
        4. If available_from / available_to set, current_time is within window
           (evaluated in the restaurant's/branch's timezone)

    Phase 7+ will add inventory checks.

    Args:
        menu_item: MenuItem instance
        branch: Branch instance
        current_time: datetime to check against (defaults to now() in UTC)

    Returns:
        bool — True if available, False otherwise
    """
    from menu.models import MenuItemBranch

    if not menu_item.is_active:
        return False

    if not branch.is_active:
        return False

    try:
        avail = MenuItemBranch.objects.get(menu_item=menu_item, branch=branch)
    except MenuItemBranch.DoesNotExist:
        # No branch availability record — treat as unavailable for that branch
        return False

    if not avail.is_available:
        return False

    # Time window check — if both are NULL, available all day
    if avail.available_from is None and avail.available_to is None:
        return True

    if current_time is None:
        current_time = timezone.now()

    # Convert to restaurant timezone for time-of-day comparison
    tz_name = _get_restaurant_timezone(branch)
    try:
        tz = ZoneInfo(tz_name)
        local_time = current_time.astimezone(tz).time()
    except (ZoneInfoNotFoundError, Exception):
        local_time = current_time.time()

    if avail.available_from and avail.available_to:
        if avail.available_from <= avail.available_to:
            # Normal window: 07:00 → 11:00
            return avail.available_from <= local_time <= avail.available_to
        else:
            # Overnight window: 22:00 → 02:00
            return local_time >= avail.available_from or local_time <= avail.available_to

    if avail.available_from:
        return local_time >= avail.available_from

    if avail.available_to:
        return local_time <= avail.available_to

    return True


def _get_restaurant_timezone(branch) -> str:
    """
    Return the effective timezone for a branch.

    Priority:
        1. Restaurant settings timezone (if set)
        2. Organization timezone
        3. Default: 'Asia/Kolkata'
    """
    try:
        settings_tz = branch.restaurant.settings.timezone
        if settings_tz:
            return settings_tz
    except Exception:
        pass
    try:
        return branch.restaurant.organization.timezone or "Asia/Kolkata"
    except Exception:
        return "Asia/Kolkata"


# ---------------------------------------------------------------------------
# Catalog builder (read-optimized for POS)
# ---------------------------------------------------------------------------

def get_branch_catalog(branch, user, current_time=None):
    """
    Build the branch catalog: all active + available menu items grouped by
    category, with branch-specific price and tax information.

    Returns a structured dict ready for BranchCatalogSerializer.
    """
    from menu.models import Category, MenuItem, MenuItemBranch, MenuItemPrice

    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    if current_time is None:
        current_time = timezone.now()

    restaurant = branch.restaurant

    # Fetch active categories ordered by display_order
    categories = Category.objects.filter(
        restaurant=restaurant,
        is_active=True,
    ).order_by("display_order", "name")

    # Fetch all active menu items for this restaurant in one query
    items_qs = MenuItem.objects.filter(
        restaurant=restaurant,
        is_active=True,
    ).select_related("category", "tax_rate").order_by("display_order", "name")

    # Fetch all branch availability records for this branch
    avail_map = {
        a.menu_item_id: a
        for a in MenuItemBranch.objects.filter(
            branch=branch,
            menu_item__restaurant=restaurant,
        ).select_related("menu_item")
    }

    # Fetch all active prices for this branch
    price_map = {
        p.menu_item_id: p
        for p in MenuItemPrice.objects.filter(
            branch=branch,
            is_active=True,
            menu_item__restaurant=restaurant,
        ).select_related("menu_item")
    }

    catalog_categories = []

    for category in categories:
        catalog_items = []

        for item in items_qs:
            if item.category_id != category.pk:
                continue

            # Check availability
            avail = avail_map.get(item.pk)
            if avail is None or not avail.is_available:
                continue

            # Time-window check
            if not _check_time_window(avail, current_time, branch):
                continue

            # Price lookup
            price_record = price_map.get(item.pk)
            price_value = price_record.price if price_record else None

            # Tax info
            tax_code = None
            tax_name = None
            tax_rate_val = None
            if item.tax_rate and item.tax_rate.is_active:
                tax_code = item.tax_rate.code
                tax_name = item.tax_rate.name
                tax_rate_val = item.tax_rate.rate

            catalog_items.append({
                "id": item.pk,
                "name": item.name,
                "slug": item.slug,
                "sku": item.sku,
                "short_description": item.short_description,
                "food_type": item.food_type,
                "image": item.image or None,
                "display_order": item.display_order,
                "preparation_time_minutes": item.preparation_time_minutes,
                "price": price_value,
                "tax_rate_code": tax_code,
                "tax_rate_name": tax_name,
                "tax_rate": tax_rate_val,
            })

        if catalog_items:
            catalog_categories.append({
                "id": category.pk,
                "name": category.name,
                "slug": category.slug,
                "display_order": category.display_order,
                "items": catalog_items,
            })

    return {
        "branch": {
            "id": str(branch.pk),
            "name": branch.name,
            "restaurant_id": str(restaurant.pk),
            "restaurant_name": restaurant.name,
        },
        "categories": catalog_categories,
    }


def _check_time_window(avail, current_time, branch) -> bool:
    """Return True if current_time is within the availability window."""
    if avail.available_from is None and avail.available_to is None:
        return True

    tz_name = _get_restaurant_timezone(branch)
    try:
        tz = ZoneInfo(tz_name)
        local_time = current_time.astimezone(tz).time()
    except (ZoneInfoNotFoundError, Exception):
        local_time = current_time.time()

    if avail.available_from and avail.available_to:
        if avail.available_from <= avail.available_to:
            return avail.available_from <= local_time <= avail.available_to
        else:
            return local_time >= avail.available_from or local_time <= avail.available_to

    if avail.available_from:
        return local_time >= avail.available_from

    if avail.available_to:
        return local_time <= avail.available_to

    return True


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------

def _require_auth(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")


def set_item_active(actor, item, is_active: bool):
    """Enable or disable a menu item."""
    _require_auth(actor)
    from menu.models import MenuItem
    item.is_active = is_active
    item.save(update_fields=["is_active", "updated_at"])
    logger.info(
        "MenuItem %s set is_active=%s by %s",
        item.pk, is_active, actor.email,
    )
    return item


def set_category_active(actor, category, is_active: bool):
    """Enable or disable a category."""
    _require_auth(actor)
    category.is_active = is_active
    category.save(update_fields=["is_active", "updated_at"])
    logger.info(
        "Category %s set is_active=%s by %s",
        category.pk, is_active, actor.email,
    )
    return category


def set_tax_rate_active(actor, tax_rate, is_active: bool):
    """Enable or disable a tax rate."""
    _require_auth(actor)
    tax_rate.is_active = is_active
    tax_rate.save(update_fields=["is_active", "updated_at"])
    logger.info(
        "TaxRate %s set is_active=%s by %s",
        tax_rate.pk, is_active, actor.email,
    )
    return tax_rate


def deactivate_price(actor, price):
    """Mark a price record as inactive (for price history purposes)."""
    _require_auth(actor)
    price.is_active = False
    price.save(update_fields=["is_active", "updated_at"])
    logger.info(
        "MenuItemPrice %s deactivated by %s",
        price.pk, actor.email,
    )
    return price
