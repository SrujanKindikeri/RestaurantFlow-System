# =============================================================================
# RestaurantFlow — Dashboard Services
# Phase 14
#
# Assembles the KPI dashboard from multiple aggregation sources.
# Uses Redis caching with scope-aware keys.
# =============================================================================

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache

from reporting import aggregations as agg
from reporting import access as r_access
from reporting.aggregations import growth_pct, _safe_div
from reporting.constants import (
    CACHE_TTL_DASHBOARD, CACHE_TTL_TOP_ITEMS,
    ZERO,
)

logger = logging.getLogger("reporting")


def _cache_key(user, restaurant, branch, suffix="dashboard"):
    """Build a scope-aware cache key that never leaks cross-restaurant data."""
    parts = [
        "reporting",
        suffix,
        f"user:{user.pk}",
        f"restaurant:{restaurant.pk if restaurant else 'all'}",
        f"branch:{branch.pk if branch else 'all'}",
    ]
    return ":".join(parts)


def get_dashboard_kpis(user, restaurant_id=None, branch_id=None):
    """
    Assemble the main dashboard KPI payload.

    Returns a single JSON-serialisable dict covering:
      - Today's sales vs yesterday
      - Orders today
      - Payment breakdown
      - Top-selling item
      - Kitchen summary
      - Inventory alerts
      - Outstanding payables
    """
    from reporting.access import resolve_report_scope

    restaurant, branch = resolve_report_scope(user, restaurant_id, branch_id)
    accessible = r_access.get_accessible_branches(user)
    if restaurant:
        accessible = accessible.filter(restaurant=restaurant)
    if branch:
        accessible = accessible.filter(pk=branch.pk)

    cache_key = _cache_key(user, restaurant, branch, "dashboard_kpis")
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    today = date.today()
    yesterday = today - timedelta(days=1)
    week_start = today - timedelta(days=today.weekday())
    prev_week_start = week_start - timedelta(weeks=1)
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    # --- Today sales ---
    today_sales = agg.aggregate_sales_summary(accessible, today, today, branch)
    yesterday_sales = agg.aggregate_sales_summary(accessible, yesterday, yesterday, branch)

    # --- This week / prev week ---
    week_sales = agg.aggregate_sales_summary(accessible, week_start, today, branch)
    prev_week_sales = agg.aggregate_sales_summary(accessible, prev_week_start, week_start - timedelta(days=1), branch)

    # --- This month / prev month ---
    month_sales = agg.aggregate_sales_summary(accessible, month_start, today, branch)
    prev_month_sales = agg.aggregate_sales_summary(accessible, prev_month_start, prev_month_end, branch)

    # --- Orders today ---
    today_orders = agg.aggregate_orders_summary(accessible, today, today, branch)

    # --- Top-selling item (today) ---
    top_items = agg.aggregate_top_selling_items(accessible, today, today, limit=1, sort_by="revenue", branch=branch)
    top_revenue_item = top_items[0] if top_items else None

    top_qty = agg.aggregate_top_selling_items(accessible, today, today, limit=1, sort_by="quantity", branch=branch)
    top_quantity_item = top_qty[0] if top_qty else None

    # --- Category top (today) ---
    categories = agg.aggregate_category_performance(accessible, today, today, branch)
    top_category = categories[0] if categories else None

    # --- Payments today ---
    today_payments = agg.aggregate_payment_summary(accessible, today, today, branch)

    # --- Kitchen (today) ---
    kitchen_today = agg.aggregate_kitchen_performance(accessible, today, today, branch)

    # --- Inventory alerts ---
    inv_summary = agg.aggregate_inventory_summary(accessible)

    # --- Payables (outstanding) ---
    try:
        payables_data = agg.aggregate_payables(
            accessible, today - timedelta(days=365), today
        )
        outstanding_payables = payables_data["outstanding_payables"]
        overdue_payables = payables_data["overdue_payables"]
    except Exception:
        outstanding_payables = overdue_payables = None

    # --- Expenses (last 30 days) ---
    try:
        expenses_data = agg.aggregate_expenses(accessible, month_start, today, branch)
        monthly_expenses = expenses_data["approved_expenses"]
    except Exception:
        monthly_expenses = None

    result = {
        "period": {
            "date_from": today.isoformat(),
            "date_to": today.isoformat(),
            "today": today.isoformat(),
        },
        "sales": {
            "today_net_sales": today_sales["net_sales"],
            "today_gross_sales": today_sales["gross_sales"],
            "today_bill_count": today_sales["number_of_bills"],
            "today_average_bill_value": today_sales["average_bill_value"],
            "yesterday_net_sales": yesterday_sales["net_sales"],
            "yesterday_bill_count": yesterday_sales["number_of_bills"],
            "today_vs_yesterday_growth": growth_pct(
                today_sales["net_sales"], yesterday_sales["net_sales"]
            ),
            "week_net_sales": week_sales["net_sales"],
            "week_bill_count": week_sales["number_of_bills"],
            "prev_week_net_sales": prev_week_sales["net_sales"],
            "week_vs_prev_week_growth": growth_pct(
                week_sales["net_sales"], prev_week_sales["net_sales"]
            ),
            "month_net_sales": month_sales["net_sales"],
            "month_bill_count": month_sales["number_of_bills"],
            "prev_month_net_sales": prev_month_sales["net_sales"],
            "month_vs_prev_month_growth": growth_pct(
                month_sales["net_sales"], prev_month_sales["net_sales"]
            ),
        },
        "orders": {
            "today_total_orders": today_orders["total_orders"],
            "today_confirmed_orders": today_orders["confirmed_orders"],
            "today_cancelled_orders": today_orders["cancelled_orders"],
            "today_average_order_value": today_orders["average_order_value"],
        },
        "products": {
            "top_revenue_item": top_revenue_item,
            "top_quantity_item": top_quantity_item,
            "top_category": top_category,
        },
        "payments": {
            "today_total_collected": today_payments["total_paid"],
            "today_cash": today_payments["cash"],
            "today_upi": today_payments["upi"],
            "today_card": today_payments["card"],
            "today_other": today_payments["other"],
            "today_refund_amount": today_payments["refund_amount"],
            "today_refund_count": today_payments["refund_count"],
        },
        "kitchen": {
            "today_orders_received": kitchen_today["orders_received"],
            "today_orders_ready": kitchen_today["orders_ready"],
            "today_orders_pending": kitchen_today["orders_pending"],
            "today_avg_prep_time_seconds": kitchen_today["average_preparation_time_seconds"],
        },
        "inventory": {
            "total_items": inv_summary["total_inventory_items"],
            "low_stock_count": inv_summary["low_stock_items"],
            "out_of_stock_count": inv_summary["out_of_stock_items"],
            "stock_value_estimate": inv_summary["stock_value_estimate"],
        },
        "financials": {
            "monthly_expenses": monthly_expenses,
            "outstanding_payables": outstanding_payables,
            "overdue_payables": overdue_payables,
        },
    }

    cache.set(cache_key, result, CACHE_TTL_DASHBOARD)
    return result
