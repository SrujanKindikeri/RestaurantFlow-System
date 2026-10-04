# =============================================================================
# RestaurantFlow — Reporting Services
# Phase 14
#
# High-level service functions called by views.
# Orchestrates selectors + access control + caching.
# =============================================================================

import logging
from datetime import date, timedelta

from django.core.cache import cache

from reporting import selectors, access as r_access
from reporting.constants import (
    CACHE_TTL_TREND, CACHE_TTL_TOP_ITEMS, CACHE_TTL_BRANCH,
    CACHE_TTL_FINANCIAL, CACHE_TTL_DASHBOARD,
)

logger = logging.getLogger("reporting")


def _scope_key(user, restaurant_id, branch_id):
    return f"u{user.pk}:r{restaurant_id or 'x'}:b{branch_id or 'x'}"


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

def get_sales_summary(user, filters):
    return selectors.select_sales_summary(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_sales_trend(user, filters):
    from reporting.validators import validate_granularity
    validate_granularity(filters.granularity)
    key = f"reporting:trend:{_scope_key(user, filters.restaurant_id, filters.branch_id)}:{filters.date_from}:{filters.date_to}:{filters.granularity}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = selectors.select_sales_trend(
        user, filters.date_from, filters.date_to, filters.granularity,
        filters.restaurant_id, filters.branch_id,
    )
    cache.set(key, result, CACHE_TTL_TREND)
    return result


def get_hourly_sales(user, filters):
    return selectors.select_hourly_sales(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

def get_orders_summary(user, filters):
    return selectors.select_orders_summary(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_orders_by_type(user, filters):
    return selectors.select_orders_by_type(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

def get_menu_items(user, filters):
    return selectors.select_menu_items(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_top_selling_items(user, filters):
    key = f"reporting:top:{_scope_key(user, filters.restaurant_id, filters.branch_id)}:{filters.date_from}:{filters.date_to}:{filters.limit}:{filters.sort_by}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = selectors.select_top_selling_items(
        user, filters.date_from, filters.date_to,
        filters.limit, filters.sort_by,
        filters.restaurant_id, filters.branch_id,
    )
    cache.set(key, result, CACHE_TTL_TOP_ITEMS)
    return result


def get_category_performance(user, filters):
    return selectors.select_category_performance(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_menu_profitability(user, filters):
    return selectors.select_menu_profitability(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Branch / Counter
# ---------------------------------------------------------------------------

def get_branch_performance(user, filters):
    key = f"reporting:branch:{_scope_key(user, filters.restaurant_id, None)}:{filters.date_from}:{filters.date_to}"
    cached = cache.get(key)
    if cached is not None:
        return cached
    result = selectors.select_branch_performance(
        user, filters.date_from, filters.date_to, filters.restaurant_id,
    )
    cache.set(key, result, CACHE_TTL_BRANCH)
    return result


def get_counter_performance(user, filters):
    return selectors.select_counter_performance(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Payments / Refunds / Discounts
# ---------------------------------------------------------------------------

def get_payment_summary(user, filters):
    return selectors.select_payment_summary(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_payment_methods(user, filters):
    return selectors.select_payment_methods(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_refunds(user, filters):
    return selectors.select_refunds(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_discounts(user, filters):
    return selectors.select_discounts(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Kitchen
# ---------------------------------------------------------------------------

def get_kitchen_performance(user, filters):
    return selectors.select_kitchen_performance(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_kitchen_items(user, filters):
    return selectors.select_kitchen_items(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

def get_waiter_performance(user, filters):
    return selectors.select_waiter_performance(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_cashier_performance(user, filters):
    return selectors.select_cashier_performance(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

def get_inventory_summary(user, filters):
    return selectors.select_inventory_summary(
        user, filters.restaurant_id, filters.branch_id,
    )


def get_inventory_consumption(user, filters):
    return selectors.select_inventory_consumption(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_wastage(user, filters):
    return selectors.select_wastage(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Purchases / Suppliers
# ---------------------------------------------------------------------------

def get_purchases(user, filters):
    return selectors.select_purchases(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_suppliers(user, filters):
    return selectors.select_suppliers(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Expenses / Payables
# ---------------------------------------------------------------------------

def get_expenses(user, filters):
    return selectors.select_expenses(
        user, filters.date_from, filters.date_to,
        filters.restaurant_id, filters.branch_id,
    )


def get_payables(user, filters):
    return selectors.select_payables(
        user, filters.restaurant_id, filters.branch_id,
    )


# ---------------------------------------------------------------------------
# Financial Summary (delegates to Phase 13)
# ---------------------------------------------------------------------------

def get_financial_summary(user, filters):
    return selectors.select_financial_summary(
        user, filters.restaurant_id, filters.date_from, filters.date_to,
    )
