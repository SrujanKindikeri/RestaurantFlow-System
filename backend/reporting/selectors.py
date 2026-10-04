# =============================================================================
# RestaurantFlow — Reporting Selectors (Read Layer)
# Phase 14
#
# Selectors combine access-control scoping with aggregation functions.
# Views call selectors; selectors call aggregations.
# Selectors validate scope and apply filters. They never modify data.
# =============================================================================

import logging
from datetime import date, timedelta
from typing import Optional

from reporting import access as r_access, aggregations as agg
from reporting.validators import validate_date_range

logger = logging.getLogger("reporting")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _default_dates():
    today = date.today()
    return today - timedelta(days=29), today


def _resolve_scope(user, restaurant_id=None, branch_id=None):
    return r_access.resolve_report_scope(user, restaurant_id=restaurant_id, branch_id=branch_id)


# ---------------------------------------------------------------------------
# Sales Selectors
# ---------------------------------------------------------------------------

def select_sales_summary(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_sales_summary(accessible, date_from, date_to, branch)


def select_sales_trend(user, date_from, date_to, granularity="daily",
                        restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_sales_trend(accessible, date_from, date_to, granularity, branch)


def select_hourly_sales(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_hourly_sales(accessible, date_from, date_to, branch)


# ---------------------------------------------------------------------------
# Order Selectors
# ---------------------------------------------------------------------------

def select_orders_summary(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_orders_summary(accessible, date_from, date_to, branch)


def select_orders_by_type(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_orders_by_type(accessible, date_from, date_to, branch)


# ---------------------------------------------------------------------------
# Menu Selectors
# ---------------------------------------------------------------------------

def select_menu_items(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_menu_items(accessible, date_from, date_to, branch)


def select_top_selling_items(user, date_from, date_to, limit=10, sort_by="revenue",
                              restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_top_selling_items(accessible, date_from, date_to, limit, sort_by, branch)


def select_category_performance(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_category_performance(accessible, date_from, date_to, branch)


def select_menu_profitability(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_menu_profitability(accessible, date_from, date_to, branch)


# ---------------------------------------------------------------------------
# Branch / Counter Selectors
# ---------------------------------------------------------------------------

def select_branch_performance(user, date_from, date_to, restaurant_id=None):
    if restaurant_id:
        restaurant, _ = _resolve_scope(user, restaurant_id=restaurant_id)
    else:
        restaurant = None
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_branch_performance(accessible, date_from, date_to)


def select_counter_performance(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_counter_performance(accessible, date_from, date_to)


# ---------------------------------------------------------------------------
# Payment Selectors
# ---------------------------------------------------------------------------

def select_payment_summary(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_payment_summary(accessible, date_from, date_to, branch)


def select_payment_methods(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_payment_methods(accessible, date_from, date_to, branch)


def select_refunds(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_refunds(accessible, date_from, date_to, branch)


def select_discounts(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_discounts(accessible, date_from, date_to, branch)


# ---------------------------------------------------------------------------
# Kitchen Selectors
# ---------------------------------------------------------------------------

def select_kitchen_performance(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_kitchen_performance(accessible, date_from, date_to, branch)


def select_kitchen_items(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_kitchen_items(accessible, date_from, date_to, branch)


# ---------------------------------------------------------------------------
# Staff Selectors
# ---------------------------------------------------------------------------

def select_waiter_performance(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_waiter_performance(accessible, date_from, date_to)


def select_cashier_performance(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_cashier_performance(accessible, date_from, date_to)


# ---------------------------------------------------------------------------
# Inventory Selectors
# ---------------------------------------------------------------------------

def select_inventory_summary(user, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    if branch:
        accessible = accessible.filter(pk=branch.pk)
    return agg.aggregate_inventory_summary(accessible)


def select_inventory_consumption(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_inventory_consumption(accessible, date_from, date_to, branch)


def select_wastage(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_wastage(accessible, date_from, date_to, branch)


# ---------------------------------------------------------------------------
# Purchase / Supplier Selectors
# ---------------------------------------------------------------------------

def select_purchases(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_purchases(accessible, date_from, date_to)


def select_suppliers(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_suppliers(accessible, date_from, date_to)


# ---------------------------------------------------------------------------
# Expense / Payable Selectors
# ---------------------------------------------------------------------------

def select_expenses(user, date_from, date_to, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    return agg.aggregate_expenses(accessible, date_from, date_to, branch)


def select_payables(user, restaurant_id=None, branch_id=None):
    restaurant, branch = _resolve_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    if branch:
        accessible = accessible.filter(pk=branch.pk)
    today = date.today()
    return agg.aggregate_payables(accessible, today - timedelta(days=365), today)


# ---------------------------------------------------------------------------
# Financial Summary Selector (delegates to Phase 13 accounting selectors)
# ---------------------------------------------------------------------------

def select_financial_summary(user, restaurant_id=None, date_from=None, date_to=None):
    """
    Financial summary using Phase 13 accounting selectors as source of truth.
    Only POSTED journal entries are used.
    """
    from accounting.selectors import get_profit_and_loss, get_balance_sheet
    from accounts import access as acl

    accessible_restaurants = acl.get_accessible_restaurants(user)
    if restaurant_id:
        try:
            restaurant = accessible_restaurants.get(pk=restaurant_id)
        except Exception:
            from reporting.exceptions import ReportScopeError
            raise ReportScopeError("Restaurant not in scope.")
    else:
        # Use first accessible restaurant, or summarize
        restaurant = accessible_restaurants.first()

    if not restaurant:
        return {
            "revenue": None, "discounts": None, "taxes": None,
            "cogs": None, "gross_profit": None,
            "operating_expenses": None, "operating_profit": None,
            "assets": None, "liabilities": None, "equity": None,
        }

    pl = get_profit_and_loss(restaurant, date_from=date_from, date_to=date_to)
    bs = get_balance_sheet(restaurant, as_of_date=date_to)

    # Operational sales for comparison (from finalized bills)
    op_accessible = r_access.get_accessible_branches(user).filter(restaurant=restaurant)
    today = date.today()
    op_date_from = date_from or (today - timedelta(days=29))
    op_date_to = date_to or today
    op = agg.aggregate_sales_summary(op_accessible, op_date_from, op_date_to)

    return {
        # Accounting source (POSTED journals) — authoritative
        "accounting_revenue": pl["total_revenue"],
        "accounting_cogs": pl["total_cogs"],
        "accounting_gross_profit": pl["gross_profit"],
        "accounting_operating_expenses": pl["total_operating_expenses"],
        "accounting_operating_profit": pl["operating_profit"],
        "assets": bs["total_assets"],
        "liabilities": bs["total_liabilities"],
        "equity": bs["total_equity"],
        "balance_sheet_balanced": bs["is_balanced"],
        # Operational source (finalized bills) — for day-to-day tracking
        "operational_net_sales": op["net_sales"],
        "operational_discounts": op["discount_amount"],
        "operational_taxes": op["tax_amount"],
        "operational_bill_count": op["number_of_bills"],
        "source_note": (
            "accounting_* values come from POSTED journal entries (Phase 13). "
            "operational_* values come from finalized bills. "
            "Differences may arise from accounting adjustments or timing."
        ),
    }
