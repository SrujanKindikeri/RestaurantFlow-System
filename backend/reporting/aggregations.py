# =============================================================================
# RestaurantFlow — Reporting Aggregations
# Phase 14
#
# Core database aggregation helpers.
# All heavy lifting is done inside PostgreSQL — no Python loops over large sets.
# =============================================================================

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from django.db.models import (
    Sum, Count, Avg, Min, Max, F, Q,
    DecimalField, IntegerField, ExpressionWrapper, DurationField,
)
from django.db.models.functions import (
    TruncDate, TruncWeek, TruncMonth, Coalesce, ExtractHour,
)
from django.utils import timezone

from reporting.constants import ZERO, HUNDRED

logger = logging.getLogger("reporting")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _coalesce_sum(field, filter=None):
    if filter is not None:
        return Coalesce(Sum(field, filter=filter), ZERO, output_field=DecimalField(max_digits=16, decimal_places=2))
    return Coalesce(Sum(field), ZERO, output_field=DecimalField(max_digits=16, decimal_places=2))


def _safe_div(num, denom):
    if not denom:
        return None
    try:
        return round(Decimal(str(num)) / Decimal(str(denom)), 2)
    except Exception:
        return None


def growth_pct(current, previous):
    if previous is None or previous == ZERO or previous == 0:
        return None
    try:
        c = Decimal(str(current or 0))
        p = Decimal(str(previous))
        return round(((c - p) / p) * HUNDRED, 2)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Sales — source: billing.Bill / BillItem
# ---------------------------------------------------------------------------

def _base_bill_qs(accessible_branches, date_from, date_to, branch=None):
    from billing.models import Bill, BillStatus
    qs = Bill.objects.filter(
        branch__in=accessible_branches,
        status=BillStatus.FINALIZED,
        finalized_at__date__gte=date_from,
        finalized_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    return qs


def aggregate_sales_summary(accessible_branches, date_from, date_to, branch=None):
    qs = _base_bill_qs(accessible_branches, date_from, date_to, branch)
    agg = qs.aggregate(
        gross_sales=_coalesce_sum("subtotal"),
        discount_amount=_coalesce_sum("discount_amount"),
        taxable_amount=_coalesce_sum("taxable_amount"),
        tax_amount=_coalesce_sum("tax_amount"),
        rounding_amount=_coalesce_sum("rounding_amount"),
        net_sales=_coalesce_sum("grand_total"),
        number_of_bills=Count("id"),
    )
    n = agg["number_of_bills"] or 0
    agg["average_bill_value"] = _safe_div(agg["net_sales"], n)
    return agg


def aggregate_sales_trend(accessible_branches, date_from, date_to, granularity="daily", branch=None):
    from billing.models import Bill, BillStatus
    qs = Bill.objects.filter(
        branch__in=accessible_branches,
        status=BillStatus.FINALIZED,
        finalized_at__date__gte=date_from,
        finalized_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    trunc_map = {"daily": TruncDate, "weekly": TruncWeek, "monthly": TruncMonth}
    TruncFn = trunc_map.get(granularity, TruncDate)
    rows = qs.annotate(period=TruncFn("finalized_at")).values("period").annotate(
        gross_sales=_coalesce_sum("subtotal"),
        discounts=_coalesce_sum("discount_amount"),
        tax=_coalesce_sum("tax_amount"),
        net_sales=_coalesce_sum("grand_total"),
        bill_count=Count("id"),
        order_count=Count("order", distinct=True),
    ).order_by("period")
    result = []
    for r in rows:
        n = r["bill_count"] or 0
        period_val = r["period"]
        if hasattr(period_val, "date"):
            period_val = period_val.date()
        result.append({
            "date": period_val,
            "gross_sales": r["gross_sales"],
            "discounts": r["discounts"],
            "tax": r["tax"],
            "net_sales": r["net_sales"],
            "bill_count": n,
            "order_count": r["order_count"],
            "average_bill_value": _safe_div(r["net_sales"], n),
        })
    return result


def aggregate_hourly_sales(accessible_branches, date_from, date_to, branch=None):
    from billing.models import Bill, BillStatus
    qs = Bill.objects.filter(
        branch__in=accessible_branches,
        status=BillStatus.FINALIZED,
        finalized_at__date__gte=date_from,
        finalized_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    rows = qs.annotate(hour=ExtractHour("finalized_at")).values("hour").annotate(
        sales=_coalesce_sum("grand_total"),
        bill_count=Count("id"),
        order_count=Count("order", distinct=True),
    ).order_by("hour")
    hour_map = {r["hour"]: r for r in rows}
    return [
        {
            "hour": h,
            "sales": hour_map.get(h, {}).get("sales", ZERO),
            "bill_count": hour_map.get(h, {}).get("bill_count", 0),
            "order_count": hour_map.get(h, {}).get("order_count", 0),
        }
        for h in range(24)
    ]


# ---------------------------------------------------------------------------
# Orders — source: orders.Order
# ---------------------------------------------------------------------------

def aggregate_orders_summary(accessible_branches, date_from, date_to, branch=None):
    from orders.models import Order, OrderStatus, OrderType
    from billing.models import Bill, BillStatus
    qs = Order.objects.filter(
        branch__in=accessible_branches,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    agg = qs.aggregate(
        total_orders=Count("id"),
        confirmed_orders=Count("id", filter=Q(status=OrderStatus.CONFIRMED)),
        cancelled_orders=Count("id", filter=Q(status=OrderStatus.CANCELLED)),
        dine_in_orders=Count("id", filter=Q(order_type=OrderType.DINE_IN)),
        takeaway_orders=Count("id", filter=Q(order_type=OrderType.TAKEAWAY)),
        counter_orders=Count("id", filter=Q(order_type=OrderType.COUNTER)),
    )
    bill_agg = Bill.objects.filter(
        branch__in=accessible_branches,
        status=BillStatus.FINALIZED,
        finalized_at__date__gte=date_from,
        finalized_at__date__lte=date_to,
    )
    if branch:
        bill_agg = bill_agg.filter(branch=branch)
    b = bill_agg.aggregate(
        avg_order_value=Coalesce(
            Avg("grand_total"), ZERO, output_field=DecimalField()
        )
    )
    return {
        "total_orders": agg["total_orders"] or 0,
        "confirmed_orders": agg["confirmed_orders"] or 0,
        "cancelled_orders": agg["cancelled_orders"] or 0,
        "dine_in_orders": agg["dine_in_orders"] or 0,
        "takeaway_orders": agg["takeaway_orders"] or 0,
        "counter_orders": agg["counter_orders"] or 0,
        "average_order_value": b["avg_order_value"],
    }


def aggregate_orders_by_type(accessible_branches, date_from, date_to, branch=None):
    from billing.models import Bill, BillStatus
    qs = Bill.objects.filter(
        branch__in=accessible_branches,
        status=BillStatus.FINALIZED,
        finalized_at__date__gte=date_from,
        finalized_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    rows = list(qs.values("order__order_type").annotate(
        order_count=Count("id"),
        sales=_coalesce_sum("grand_total"),
    ).order_by("-sales"))
    total = sum(r["order_count"] for r in rows) or 1
    return [
        {
            "order_type": r["order__order_type"] or "UNKNOWN",
            "order_count": r["order_count"],
            "sales": r["sales"],
            "percentage_of_orders": round((r["order_count"] / total) * 100, 2),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Menu — source: billing.BillItem
# ---------------------------------------------------------------------------

def _base_billitem_qs(accessible_branches, date_from, date_to, branch=None):
    from billing.models import BillItem, BillStatus
    qs = BillItem.objects.filter(
        bill__branch__in=accessible_branches,
        bill__status=BillStatus.FINALIZED,
        bill__finalized_at__date__gte=date_from,
        bill__finalized_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(bill__branch=branch)
    return qs


def aggregate_menu_items(accessible_branches, date_from, date_to, branch=None):
    qs = _base_billitem_qs(accessible_branches, date_from, date_to, branch)
    rows = list(qs.values(
        "menu_item_id", "menu_item__name", "menu_item__category__name",
    ).annotate(
        quantity_sold=_coalesce_sum("quantity"),
        gross_revenue=_coalesce_sum("gross_amount"),
        discount_amount=_coalesce_sum("discount_amount"),
        net_revenue=_coalesce_sum("total_amount"),
        number_of_orders=Count("bill__order", distinct=True),
    ).order_by("-net_revenue"))
    total_net = sum(r["net_revenue"] for r in rows) or Decimal("1")
    result = []
    for r in rows:
        qty = r["quantity_sold"] or Decimal("0")
        result.append({
            "menu_item_id": str(r["menu_item_id"]),
            "menu_item_name": r["menu_item__name"],
            "category": r["menu_item__category__name"],
            "quantity_sold": qty,
            "gross_revenue": r["gross_revenue"],
            "discount_amount": r["discount_amount"],
            "net_revenue": r["net_revenue"],
            "average_selling_price": _safe_div(r["net_revenue"], qty),
            "number_of_orders": r["number_of_orders"],
            "percentage_of_sales": round((r["net_revenue"] / total_net) * HUNDRED, 2),
        })
    return result


def aggregate_top_selling_items(accessible_branches, date_from, date_to,
                                 limit=10, sort_by="revenue", branch=None):
    qs = _base_billitem_qs(accessible_branches, date_from, date_to, branch)
    rows = qs.values("menu_item_id", "menu_item__name", "menu_item__category__name").annotate(
        quantity_sold=_coalesce_sum("quantity"),
        net_revenue=_coalesce_sum("total_amount"),
        number_of_orders=Count("bill__order", distinct=True),
    )
    sort_map = {"quantity": "-quantity_sold", "revenue": "-net_revenue", "orders": "-number_of_orders"}
    rows = rows.order_by(sort_map.get(sort_by, "-net_revenue"))[:limit]
    return [
        {
            "rank": i + 1,
            "menu_item_id": str(r["menu_item_id"]),
            "menu_item_name": r["menu_item__name"],
            "category": r["menu_item__category__name"],
            "quantity_sold": r["quantity_sold"],
            "net_revenue": r["net_revenue"],
            "number_of_orders": r["number_of_orders"],
        }
        for i, r in enumerate(rows)
    ]


def aggregate_category_performance(accessible_branches, date_from, date_to, branch=None):
    qs = _base_billitem_qs(accessible_branches, date_from, date_to, branch)
    rows = list(qs.values(
        "menu_item__category_id", "menu_item__category__name",
    ).annotate(
        quantity_sold=_coalesce_sum("quantity"),
        gross_revenue=_coalesce_sum("gross_amount"),
        net_revenue=_coalesce_sum("total_amount"),
    ).order_by("-net_revenue"))
    total_net = sum(r["net_revenue"] for r in rows) or Decimal("1")
    return [
        {
            "category_id": str(r["menu_item__category_id"]) if r["menu_item__category_id"] else None,
            "category": r["menu_item__category__name"] or "Uncategorised",
            "quantity_sold": r["quantity_sold"],
            "gross_revenue": r["gross_revenue"],
            "net_revenue": r["net_revenue"],
            "sales_percentage": round((r["net_revenue"] / total_net) * HUNDRED, 2),
            "average_item_value": _safe_div(r["net_revenue"], r["quantity_sold"] or Decimal("1")),
        }
        for r in rows
    ]


def aggregate_menu_profitability(accessible_branches, date_from, date_to, branch=None):
    """
    Revenue from BillItem + ingredient cost from COMPLETED StockConsumption.
    Never uses current recipe cost for historical sales.
    If no consumption data is available, ingredient_cost is None.
    """
    from billing.models import BillItem, BillStatus
    from recipes.models import StockConsumption
    from recipes.constants import CONSUMPTION_CONSUMED

    # Revenue per menu item
    bill_rows = list(
        BillItem.objects.filter(
            bill__branch__in=accessible_branches,
            bill__status=BillStatus.FINALIZED,
            bill__finalized_at__date__gte=date_from,
            bill__finalized_at__date__lte=date_to,
        )
        .filter(*([Q(bill__branch=branch)] if branch else []))
        .values("menu_item_id", "menu_item__name")
        .annotate(
            quantity_sold=_coalesce_sum("quantity"),
            revenue=_coalesce_sum("total_amount"),
        )
        .order_by("-revenue")
    )

    # Consumption cost per menu item via order_item → bill_item → menu_item
    # StockConsumption links order_item → which links to menu_item
    consumption_rows = list(
        StockConsumption.objects.filter(
            branch__in=accessible_branches,
            status=CONSUMPTION_CONSUMED,
            consumed_at__date__gte=date_from,
            consumed_at__date__lte=date_to,
        )
        .filter(*([Q(branch=branch)] if branch else []))
        .values("order_item__menu_item_id")
        .annotate(ingredient_cost=_coalesce_sum("total_cost"))
    )
    cost_map = {
        str(r["order_item__menu_item_id"]): r["ingredient_cost"]
        for r in consumption_rows
        if r["order_item__menu_item_id"]
    }

    result = []
    for r in bill_rows:
        mid = str(r["menu_item_id"])
        revenue = r["revenue"]
        ingredient_cost = cost_map.get(mid)  # None if unavailable
        if ingredient_cost is not None and revenue:
            gross_profit = revenue - ingredient_cost
            gross_margin = _safe_div(gross_profit * HUNDRED, revenue)
        else:
            gross_profit = None
            gross_margin = None
        result.append({
            "menu_item_id": mid,
            "menu_item_name": r["menu_item__name"],
            "quantity_sold": r["quantity_sold"],
            "revenue": revenue,
            "ingredient_cost": ingredient_cost,
            "gross_profit": gross_profit,
            "gross_margin_percentage": gross_margin,
        })
    return result


# ---------------------------------------------------------------------------
# Branch Performance — source: Bill + Payment + StockConsumption
# ---------------------------------------------------------------------------

def aggregate_branch_performance(accessible_branches, date_from, date_to):
    from billing.models import Bill, BillStatus
    from payments.models import Payment, PaymentStatus, PaymentRefund, RefundStatus

    bill_rows = list(
        Bill.objects.filter(
            branch__in=accessible_branches,
            status=BillStatus.FINALIZED,
            finalized_at__date__gte=date_from,
            finalized_at__date__lte=date_to,
        )
        .values("branch_id", "branch__name")
        .annotate(
            bill_count=Count("id"),
            order_count=Count("order", distinct=True),
            revenue=_coalesce_sum("grand_total"),
            discounts=_coalesce_sum("discount_amount"),
            taxes=_coalesce_sum("tax_amount"),
        )
        .order_by("-revenue")
    )

    payment_rows = list(
        Payment.objects.filter(
            branch__in=accessible_branches,
            status=PaymentStatus.COMPLETED,
            completed_at__date__gte=date_from,
            completed_at__date__lte=date_to,
        )
        .values("branch_id")
        .annotate(payments=_coalesce_sum("amount"))
    )
    payment_map = {str(r["branch_id"]): r["payments"] for r in payment_rows}

    refund_rows = list(
        PaymentRefund.objects.filter(
            payment__branch__in=accessible_branches,
            status=RefundStatus.PROCESSED,
            processed_at__date__gte=date_from,
            processed_at__date__lte=date_to,
        )
        .values("payment__branch_id")
        .annotate(refunds=_coalesce_sum("amount"))
    )
    refund_map = {str(r["payment__branch_id"]): r["refunds"] for r in refund_rows}

    from recipes.models import StockConsumption
    from recipes.constants import CONSUMPTION_CONSUMED
    consumption_rows = list(
        StockConsumption.objects.filter(
            branch__in=accessible_branches,
            status=CONSUMPTION_CONSUMED,
            consumed_at__date__gte=date_from,
            consumed_at__date__lte=date_to,
        )
        .values("branch_id")
        .annotate(ingredient_cost=_coalesce_sum("total_cost"))
    )
    cost_map = {str(r["branch_id"]): r["ingredient_cost"] for r in consumption_rows}

    result = []
    for r in bill_rows:
        bid = str(r["branch_id"])
        revenue = r["revenue"]
        ing_cost = cost_map.get(bid, ZERO)
        gross_profit = revenue - ing_cost if revenue else None
        gross_margin = _safe_div(gross_profit * HUNDRED, revenue) if gross_profit and revenue else None
        n_bills = r["bill_count"] or 1
        result.append({
            "branch_id": bid,
            "branch_name": r["branch__name"],
            "orders": r["order_count"],
            "bills": r["bill_count"],
            "revenue": revenue,
            "payments": payment_map.get(bid, ZERO),
            "refunds": refund_map.get(bid, ZERO),
            "discounts": r["discounts"],
            "taxes": r["taxes"],
            "average_bill_value": _safe_div(revenue, n_bills),
            "average_order_value": _safe_div(revenue, r["order_count"] or 1),
            "ingredient_cost": cost_map.get(bid),
            "gross_profit": gross_profit,
            "gross_margin": gross_margin,
        })
    return result


# ---------------------------------------------------------------------------
# Counter Performance
# ---------------------------------------------------------------------------

def aggregate_counter_performance(accessible_branches, date_from, date_to):
    from billing.models import Bill, BillStatus
    from payments.models import Payment, PaymentStatus, PaymentMethod, PaymentRefund, RefundStatus

    bill_rows = list(
        Bill.objects.filter(
            branch__in=accessible_branches,
            status=BillStatus.FINALIZED,
            finalized_at__date__gte=date_from,
            finalized_at__date__lte=date_to,
            order__counter__isnull=False,
        )
        .values("order__counter_id", "order__counter__name")
        .annotate(
            bill_count=Count("id"),
            order_count=Count("order", distinct=True),
            sales=_coalesce_sum("grand_total"),
        )
        .order_by("-sales")
    )

    # Payment breakdown by counter + method
    pay_rows = list(
        Payment.objects.filter(
            branch__in=accessible_branches,
            status=PaymentStatus.COMPLETED,
            counter__isnull=False,
            completed_at__date__gte=date_from,
            completed_at__date__lte=date_to,
        )
        .values("counter_id", "payment_method")
        .annotate(total=_coalesce_sum("amount"), cnt=Count("id"))
    )

    # Build payment map: counter_id -> {method: amount}
    pay_map = {}
    for p in pay_rows:
        cid = str(p["counter_id"])
        pay_map.setdefault(cid, {})
        pay_map[cid][p["payment_method"]] = p["total"]

    # Refunds by counter
    refund_rows = list(
        PaymentRefund.objects.filter(
            payment__branch__in=accessible_branches,
            status=RefundStatus.PROCESSED,
            payment__counter__isnull=False,
            processed_at__date__gte=date_from,
            processed_at__date__lte=date_to,
        )
        .values("payment__counter_id")
        .annotate(refunds=_coalesce_sum("amount"))
    )
    refund_map = {str(r["payment__counter_id"]): r["refunds"] for r in refund_rows}

    result = []
    for r in bill_rows:
        cid = str(r["order__counter_id"])
        pm = pay_map.get(cid, {})
        result.append({
            "counter_id": cid,
            "counter_name": r["order__counter__name"],
            "orders": r["order_count"],
            "bills": r["bill_count"],
            "sales": r["sales"],
            "payments": sum(pm.values(), ZERO),
            "cash_sales": pm.get(PaymentMethod.CASH, ZERO),
            "upi_sales": pm.get(PaymentMethod.UPI, ZERO),
            "card_sales": pm.get(PaymentMethod.CARD, ZERO),
            "refunds": refund_map.get(cid, ZERO),
            "average_bill_value": _safe_div(r["sales"], r["bill_count"] or 1),
        })
    return result


# ---------------------------------------------------------------------------
# Payment Aggregations
# ---------------------------------------------------------------------------

def aggregate_payment_summary(accessible_branches, date_from, date_to, branch=None):
    from payments.models import Payment, PaymentStatus, PaymentMethod, PaymentRefund, RefundStatus
    qs = Payment.objects.filter(
        branch__in=accessible_branches,
        status=PaymentStatus.COMPLETED,
        completed_at__date__gte=date_from,
        completed_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    agg = qs.aggregate(
        total_paid=_coalesce_sum("amount"),
        cash=_coalesce_sum("amount", filter=Q(payment_method=PaymentMethod.CASH)),
        upi=_coalesce_sum("amount", filter=Q(payment_method=PaymentMethod.UPI)),
        card=_coalesce_sum("amount", filter=Q(payment_method=PaymentMethod.CARD)),
        other=_coalesce_sum("amount", filter=~Q(payment_method__in=[PaymentMethod.CASH, PaymentMethod.UPI, PaymentMethod.CARD])),
        payment_count=Count("id"),
    )

    refund_qs = PaymentRefund.objects.filter(
        payment__branch__in=accessible_branches,
        status=RefundStatus.PROCESSED,
        processed_at__date__gte=date_from,
        processed_at__date__lte=date_to,
    )
    if branch:
        refund_qs = refund_qs.filter(payment__branch=branch)
    r_agg = refund_qs.aggregate(
        refund_amount=_coalesce_sum("amount"),
        refund_count=Count("id"),
    )
    return {**agg, **r_agg}


def aggregate_payment_methods(accessible_branches, date_from, date_to, branch=None):
    from payments.models import Payment, PaymentStatus
    qs = Payment.objects.filter(
        branch__in=accessible_branches,
        status=PaymentStatus.COMPLETED,
        completed_at__date__gte=date_from,
        completed_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    rows = list(qs.values("payment_method").annotate(
        total=_coalesce_sum("amount"),
        count=Count("id"),
    ).order_by("-total"))
    grand_total = sum(r["total"] for r in rows) or Decimal("1")
    return [
        {
            "payment_method": r["payment_method"],
            "total": r["total"],
            "count": r["count"],
            "percentage": round((r["total"] / grand_total) * HUNDRED, 2),
        }
        for r in rows
    ]


def aggregate_refunds(accessible_branches, date_from, date_to, branch=None):
    from payments.models import PaymentRefund, RefundStatus, Payment, PaymentStatus
    qs = PaymentRefund.objects.filter(
        payment__branch__in=accessible_branches,
        status=RefundStatus.PROCESSED,
        processed_at__date__gte=date_from,
        processed_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(payment__branch=branch)

    agg = qs.aggregate(
        refund_count=Count("id"),
        refund_amount=_coalesce_sum("amount"),
    )

    # Net sales for percentage calc
    from billing.models import Bill, BillStatus
    net_sales = Bill.objects.filter(
        branch__in=accessible_branches,
        status=BillStatus.FINALIZED,
        finalized_at__date__gte=date_from,
        finalized_at__date__lte=date_to,
    )
    if branch:
        net_sales = net_sales.filter(branch=branch)
    net = net_sales.aggregate(t=_coalesce_sum("grand_total"))["t"] or Decimal("1")

    # By method
    method_rows = list(qs.values("payment__payment_method").annotate(
        amount=_coalesce_sum("amount"), count=Count("id"),
    ))
    # By branch
    branch_rows = list(qs.values("payment__branch__name").annotate(
        amount=_coalesce_sum("amount"), count=Count("id"),
    ).order_by("-amount"))
    # By day
    day_rows = list(qs.annotate(day=TruncDate("processed_at")).values("day").annotate(
        amount=_coalesce_sum("amount"), count=Count("id"),
    ).order_by("day"))

    return {
        "refund_count": agg["refund_count"] or 0,
        "refund_amount": agg["refund_amount"],
        "percentage_of_sales": _safe_div(agg["refund_amount"] * HUNDRED, net),
        "refunds_by_method": [
            {"payment_method": r["payment__payment_method"], "amount": r["amount"], "count": r["count"]}
            for r in method_rows
        ],
        "refunds_by_branch": [
            {"branch": r["payment__branch__name"], "amount": r["amount"], "count": r["count"]}
            for r in branch_rows
        ],
        "refunds_by_day": [
            {"date": r["day"], "amount": r["amount"], "count": r["count"]}
            for r in day_rows
        ],
    }


def aggregate_discounts(accessible_branches, date_from, date_to, branch=None):
    from billing.models import Bill, BillStatus
    qs = Bill.objects.filter(
        branch__in=accessible_branches,
        status=BillStatus.FINALIZED,
        finalized_at__date__gte=date_from,
        finalized_at__date__lte=date_to,
        discount_amount__gt=0,
    )
    if branch:
        qs = qs.filter(branch=branch)
    agg = qs.aggregate(
        discount_amount=_coalesce_sum("discount_amount"),
        discounted_bill_count=Count("id"),
        net_sales=_coalesce_sum("grand_total"),
    )
    net = agg["net_sales"] or Decimal("1")
    agg["discount_percentage_of_sales"] = _safe_div(agg["discount_amount"] * HUNDRED, net)

    branch_rows = list(qs.values("branch__name").annotate(
        amount=_coalesce_sum("discount_amount"), count=Count("id"),
    ).order_by("-amount"))
    agg["discount_by_branch"] = [
        {"branch": r["branch__name"], "amount": r["amount"], "count": r["count"]}
        for r in branch_rows
    ]
    return agg


# ---------------------------------------------------------------------------
# Kitchen Performance
# ---------------------------------------------------------------------------

def aggregate_kitchen_performance(accessible_branches, date_from, date_to, branch=None):
    from kitchen.models import KitchenOrder, KitchenOrderStatus
    qs = KitchenOrder.objects.filter(
        branch__in=accessible_branches,
        received_at__date__gte=date_from,
        received_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)

    agg = qs.aggregate(
        orders_received=Count("id"),
        orders_ready=Count("id", filter=Q(status=KitchenOrderStatus.READY)),
        orders_cancelled=Count("id", filter=Q(status=KitchenOrderStatus.CANCELLED)),
        orders_pending=Count("id", filter=Q(status__in=[
            KitchenOrderStatus.NEW, KitchenOrderStatus.ACCEPTED, KitchenOrderStatus.PREPARING
        ])),
    )

    # Avg preparation time — only where both started_at and ready_at are set
    completed_qs = qs.filter(started_at__isnull=False, ready_at__isnull=False)
    prep_times = list(
        completed_qs.annotate(
            duration=ExpressionWrapper(
                F("ready_at") - F("started_at"), output_field=DurationField()
            )
        ).values_list("duration", flat=True)
    )
    if prep_times:
        avg_secs = sum(d.total_seconds() for d in prep_times) / len(prep_times)
        max_secs = max(d.total_seconds() for d in prep_times)
        sorted_times = sorted(d.total_seconds() for d in prep_times)
        n = len(sorted_times)
        median_secs = (
            sorted_times[n // 2] if n % 2 else
            (sorted_times[n // 2 - 1] + sorted_times[n // 2]) / 2
        )
    else:
        avg_secs = max_secs = median_secs = None

    return {
        "orders_received": agg["orders_received"] or 0,
        "orders_ready": agg["orders_ready"] or 0,
        "orders_cancelled": agg["orders_cancelled"] or 0,
        "orders_pending": agg["orders_pending"] or 0,
        "average_preparation_time_seconds": round(avg_secs, 1) if avg_secs is not None else None,
        "median_preparation_time_seconds": round(median_secs, 1) if median_secs is not None else None,
        "maximum_preparation_time_seconds": round(max_secs, 1) if max_secs is not None else None,
    }


def aggregate_kitchen_items(accessible_branches, date_from, date_to, branch=None):
    from kitchen.models import KitchenOrderItem, KitchenItemStatus
    qs = KitchenOrderItem.objects.filter(
        kitchen_order__branch__in=accessible_branches,
        kitchen_order__received_at__date__gte=date_from,
        kitchen_order__received_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(kitchen_order__branch=branch)

    rows = list(qs.values("menu_item_id", "menu_item__name").annotate(
        quantity_prepared=_coalesce_sum("quantity"),
        ready_count=Count("id", filter=Q(status=KitchenItemStatus.READY)),
        cancelled_count=Count("id", filter=Q(status=KitchenItemStatus.CANCELLED)),
    ).order_by("-quantity_prepared"))

    result = []
    for r in rows:
        # Calc prep time only for items with both timestamps
        prep_qs = qs.filter(
            menu_item_id=r["menu_item_id"],
            started_at__isnull=False,
            ready_at__isnull=False,
        ).annotate(
            duration=ExpressionWrapper(
                F("ready_at") - F("started_at"), output_field=DurationField()
            )
        ).values_list("duration", flat=True)
        times = [d.total_seconds() for d in prep_qs if d]
        result.append({
            "menu_item_id": str(r["menu_item_id"]),
            "menu_item_name": r["menu_item__name"],
            "quantity_prepared": r["quantity_prepared"],
            "average_preparation_time_seconds": round(sum(times) / len(times), 1) if times else None,
            "max_preparation_time_seconds": round(max(times), 1) if times else None,
            "ready_count": r["ready_count"],
            "cancelled_count": r["cancelled_count"],
        })
    return result


# ---------------------------------------------------------------------------
# Staff Performance
# ---------------------------------------------------------------------------

def aggregate_waiter_performance(accessible_branches, date_from, date_to):
    from billing.models import Bill, BillStatus
    from orders.models import Order, OrderStatus

    rows = list(
        Bill.objects.filter(
            branch__in=accessible_branches,
            status=BillStatus.FINALIZED,
            finalized_at__date__gte=date_from,
            finalized_at__date__lte=date_to,
            order__assigned_waiter__isnull=False,
        )
        .values("order__assigned_waiter_id", "order__assigned_waiter__first_name",
                "order__assigned_waiter__last_name", "order__assigned_waiter__email")
        .annotate(
            order_count=Count("order", distinct=True),
            sales=_coalesce_sum("grand_total"),
        )
        .order_by("-sales")
    )

    # Cancellations
    cancel_rows = list(
        Order.objects.filter(
            branch__in=accessible_branches,
            status=OrderStatus.CANCELLED,
            created_at__date__gte=date_from,
            created_at__date__lte=date_to,
            assigned_waiter__isnull=False,
        )
        .values("assigned_waiter_id")
        .annotate(cancel_count=Count("id"))
    )
    cancel_map = {str(r["assigned_waiter_id"]): r["cancel_count"] for r in cancel_rows}

    result = []
    for r in rows:
        wid = str(r["order__assigned_waiter_id"])
        n = r["order_count"] or 1
        fn = r["order__assigned_waiter__first_name"] or ""
        ln = r["order__assigned_waiter__last_name"] or ""
        name = f"{fn} {ln}".strip() or r["order__assigned_waiter__email"]
        result.append({
            "waiter_id": wid,
            "waiter_name": name,
            "order_count": r["order_count"],
            "sales": r["sales"],
            "average_order_value": _safe_div(r["sales"], n),
            "cancellation_count": cancel_map.get(wid, 0),
        })
    return result


def aggregate_cashier_performance(accessible_branches, date_from, date_to):
    from payments.models import Payment, PaymentStatus, PaymentMethod, PaymentRefund, RefundStatus
    rows = list(
        Payment.objects.filter(
            branch__in=accessible_branches,
            status=PaymentStatus.COMPLETED,
            completed_at__date__gte=date_from,
            completed_at__date__lte=date_to,
        )
        .values("initiated_by_id", "initiated_by__first_name",
                "initiated_by__last_name", "initiated_by__email")
        .annotate(
            payment_count=Count("id"),
            collected_amount=_coalesce_sum("amount"),
            cash_collected=_coalesce_sum("amount", filter=Q(payment_method=PaymentMethod.CASH)),
            upi_collected=_coalesce_sum("amount", filter=Q(payment_method=PaymentMethod.UPI)),
            card_collected=_coalesce_sum("amount", filter=Q(payment_method=PaymentMethod.CARD)),
        )
        .order_by("-collected_amount")
    )
    refund_rows = list(
        PaymentRefund.objects.filter(
            payment__branch__in=accessible_branches,
            status=RefundStatus.PROCESSED,
            processed_at__date__gte=date_from,
            processed_at__date__lte=date_to,
        )
        .values("payment__initiated_by_id")
        .annotate(refund_count=Count("id"))
    )
    refund_map = {str(r["payment__initiated_by_id"]): r["refund_count"] for r in refund_rows}

    result = []
    for r in rows:
        uid = str(r["initiated_by_id"])
        fn = r["initiated_by__first_name"] or ""
        ln = r["initiated_by__last_name"] or ""
        name = f"{fn} {ln}".strip() or r["initiated_by__email"]
        result.append({
            "cashier_id": uid,
            "cashier_name": name,
            "payment_count": r["payment_count"],
            "collected_amount": r["collected_amount"],
            "cash_collected": r["cash_collected"],
            "upi_collected": r["upi_collected"],
            "card_collected": r["card_collected"],
            "refund_count": refund_map.get(uid, 0),
        })
    return result


# ---------------------------------------------------------------------------
# Inventory Aggregations
# ---------------------------------------------------------------------------

def aggregate_inventory_summary(accessible_branches):
    from inventory.models import StockBalance, InventoryItem
    from inventory.constants import ZERO as INV_ZERO

    locations = __import__("inventory.models", fromlist=["StorageLocation"]).StorageLocation.objects.filter(
        branch__in=accessible_branches, is_active=True
    )
    balances = StockBalance.objects.filter(storage_location__in=locations).select_related(
        "inventory_item", "storage_location"
    )

    total_items = set()
    low_stock = set()
    out_of_stock = set()
    stock_value = ZERO
    for b in balances:
        item = b.inventory_item
        total_items.add(item.pk)
        avail = b.available_quantity
        if avail <= INV_ZERO:
            out_of_stock.add(item.pk)
        elif avail <= item.reorder_level:
            low_stock.add(item.pk)
        stock_value += b.quantity * b.average_cost

    return {
        "total_inventory_items": len(total_items),
        "low_stock_items": len(low_stock),
        "out_of_stock_items": len(out_of_stock),
        "stock_value_estimate": round(stock_value, 2),
    }


def aggregate_inventory_consumption(accessible_branches, date_from, date_to, branch=None):
    from recipes.models import StockConsumption
    from recipes.constants import CONSUMPTION_CONSUMED
    qs = StockConsumption.objects.filter(
        branch__in=accessible_branches,
        status=CONSUMPTION_CONSUMED,
        consumed_at__date__gte=date_from,
        consumed_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    rows = list(qs.values(
        "inventory_item_id", "inventory_item__name", "inventory_item__default_unit",
    ).annotate(
        quantity_consumed=_coalesce_sum("quantity"),
        consumption_cost=_coalesce_sum("total_cost"),
    ).order_by("-consumption_cost"))
    return [
        {
            "inventory_item_id": str(r["inventory_item_id"]),
            "inventory_item": r["inventory_item__name"],
            "unit": r["inventory_item__default_unit"],
            "quantity_consumed": r["quantity_consumed"],
            "consumption_cost": r["consumption_cost"],
        }
        for r in rows
    ]


def aggregate_wastage(accessible_branches, date_from, date_to, branch=None):
    """
    Aggregate wastage data.
    StockWastage links to storage_location (not branch directly).
    We filter via storage_location__branch__in=accessible_branches.
    Cost field is estimated_cost (set at approval time).
    """
    from inventory.models import StockWastage
    from inventory.constants import WASTAGE_APPROVED, WASTAGE_RECORDED
    qs = StockWastage.objects.filter(
        storage_location__branch__in=accessible_branches,
        status__in=[WASTAGE_APPROVED, WASTAGE_RECORDED],
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    if branch:
        qs = qs.filter(storage_location__branch=branch)

    agg = qs.aggregate(
        total_wastage_cost=_coalesce_sum("estimated_cost"),
        wastage_quantity=_coalesce_sum("quantity"),
    )

    by_type = list(qs.values("wastage_type").annotate(
        cost=_coalesce_sum("estimated_cost"), qty=_coalesce_sum("quantity"), count=Count("id"),
    ).order_by("-cost"))

    by_item = list(qs.values(
        "inventory_item__name", "inventory_item_id",
    ).annotate(
        cost=_coalesce_sum("estimated_cost"), qty=_coalesce_sum("quantity"),
    ).order_by("-cost")[:20])

    by_branch = list(qs.values("storage_location__branch__name").annotate(
        cost=_coalesce_sum("estimated_cost"),
    ).order_by("-cost"))

    trend = list(qs.annotate(day=TruncDate("created_at")).values("day").annotate(
        cost=_coalesce_sum("estimated_cost"), qty=_coalesce_sum("quantity"),
    ).order_by("day"))

    return {
        "total_wastage_cost": agg["total_wastage_cost"],
        "wastage_quantity": agg["wastage_quantity"],
        "wastage_by_type": [
            {"type": r["wastage_type"], "cost": r["cost"], "quantity": r["qty"], "count": r["count"]}
            for r in by_type
        ],
        "wastage_by_item": [
            {"item_id": str(r["inventory_item_id"]), "item": r["inventory_item__name"],
             "cost": r["cost"], "quantity": r["qty"]}
            for r in by_item
        ],
        "wastage_by_branch": [
            {"branch": r["storage_location__branch__name"], "cost": r["cost"]} for r in by_branch
        ],
        "wastage_trend": [
            {"date": r["day"], "cost": r["cost"], "quantity": r["qty"]} for r in trend
        ],
    }


# ---------------------------------------------------------------------------
# Purchase & Supplier Aggregations
# ---------------------------------------------------------------------------

def aggregate_purchases(accessible_branches, date_from, date_to):
    from inventory.models import PurchaseOrder
    from inventory.constants import PO_RECEIVED, PO_APPROVED, PO_PARTIALLY_RECEIVED, PO_DRAFT, PO_SUBMITTED

    qs = PurchaseOrder.objects.filter(
        branch__in=accessible_branches,
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    )
    agg = qs.aggregate(
        purchase_order_count=Count("id"),
        purchase_value=_coalesce_sum("total_amount"),
        pending_count=Count("id", filter=Q(status__in=[PO_DRAFT, PO_SUBMITTED, PO_APPROVED])),
    )

    received_qs = qs.filter(status__in=[PO_RECEIVED, PO_PARTIALLY_RECEIVED])
    received_agg = received_qs.aggregate(received_value=_coalesce_sum("total_amount"))

    by_supplier = list(qs.values("supplier__name", "supplier_id").annotate(
        count=Count("id"), value=_coalesce_sum("total_amount"),
    ).order_by("-value")[:20])

    by_branch = list(qs.values("branch__name").annotate(
        count=Count("id"), value=_coalesce_sum("total_amount"),
    ).order_by("-value"))

    return {
        "purchase_order_count": agg["purchase_order_count"] or 0,
        "purchase_value": agg["purchase_value"],
        "received_value": received_agg["received_value"],
        "pending_purchase_orders": agg["pending_count"] or 0,
        "supplier_summary": [
            {"supplier_id": str(r["supplier_id"]), "supplier": r["supplier__name"],
             "count": r["count"], "value": r["value"]}
            for r in by_supplier
        ],
        "branch_summary": [
            {"branch": r["branch__name"], "count": r["count"], "value": r["value"]}
            for r in by_branch
        ],
    }


def aggregate_suppliers(accessible_branches, date_from, date_to):
    from inventory.models import Supplier, PurchaseOrder
    from financials.models import SupplierInvoice, Payable
    from financials.constants import PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID, PAYABLE_OVERDUE

    # Restrict to suppliers of accessible restaurants
    accessible_restaurants = accessible_branches.values("restaurant_id").distinct()
    suppliers = Supplier.objects.filter(restaurant__branches__in=accessible_branches, is_active=True).distinct()

    po_rows = list(
        PurchaseOrder.objects.filter(branch__in=accessible_branches)
        .values("supplier_id")
        .annotate(po_value=_coalesce_sum("total_amount"))
    )
    po_map = {str(r["supplier_id"]): r["po_value"] for r in po_rows}

    sinv_rows = list(
        SupplierInvoice.objects.filter(branch__in=accessible_branches)
        .values("supplier_id")
        .annotate(inv_value=_coalesce_sum("total_amount"))
    )
    sinv_map = {str(r["supplier_id"]): r["inv_value"] for r in sinv_rows}

    payable_rows = list(
        Payable.objects.filter(
            branch__in=accessible_branches,
            status__in=[PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID],
        )
        .values("supplier_invoice__supplier_id")
        .annotate(outstanding=_coalesce_sum("remaining_amount"))
    )
    outstanding_map = {str(r["supplier_invoice__supplier_id"]): r["outstanding"] for r in payable_rows}

    overdue_rows = list(
        Payable.objects.filter(
            branch__in=accessible_branches,
            status=PAYABLE_OVERDUE,
        )
        .values("supplier_invoice__supplier_id")
        .annotate(overdue=_coalesce_sum("remaining_amount"))
    )
    overdue_map = {str(r["supplier_invoice__supplier_id"]): r["overdue"] for r in overdue_rows}

    result = []
    for s in suppliers:
        sid = str(s.pk)
        result.append({
            "supplier_id": sid,
            "supplier_name": s.name,
            "supplier_code": s.code,
            "purchase_value": po_map.get(sid, ZERO),
            "invoice_value": sinv_map.get(sid, ZERO),
            "outstanding_payable": outstanding_map.get(sid, ZERO),
            "overdue_payable": overdue_map.get(sid, ZERO),
        })
    result.sort(key=lambda x: x["purchase_value"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# Expense & Payable Aggregations
# ---------------------------------------------------------------------------

def aggregate_expenses(accessible_branches, date_from, date_to, branch=None):
    from financials.models import Expense
    from financials.constants import (
        EXPENSE_APPROVED, EXPENSE_SUBMITTED, EXPENSE_DRAFT,
        EXPENSE_REJECTED, EXPENSE_CANCELLED,
        PAYMENT_STATUS_UNPAID, PAYMENT_STATUS_PARTIALLY_PAID, PAYMENT_STATUS_PAID,
    )
    qs = Expense.objects.filter(
        branch__in=accessible_branches,
        expense_date__gte=date_from,
        expense_date__lte=date_to,
    )
    if branch:
        qs = qs.filter(branch=branch)
    agg = qs.aggregate(
        total_expenses=_coalesce_sum("total_amount"),
        approved_expenses=_coalesce_sum("total_amount", filter=Q(status=EXPENSE_APPROVED)),
        pending_expenses=_coalesce_sum("total_amount", filter=Q(status=EXPENSE_SUBMITTED)),
        unpaid_expenses=_coalesce_sum("total_amount",
            filter=Q(status=EXPENSE_APPROVED, payment_status=PAYMENT_STATUS_UNPAID)),
        paid_expenses=_coalesce_sum("total_amount",
            filter=Q(status=EXPENSE_APPROVED, payment_status=PAYMENT_STATUS_PAID)),
        overdue_count=Count("id", filter=Q(status=EXPENSE_APPROVED,
            payment_status__in=[PAYMENT_STATUS_UNPAID, PAYMENT_STATUS_PARTIALLY_PAID],
            due_date__lt=date.today())),
    )

    by_category = list(qs.filter(status=EXPENSE_APPROVED).values(
        "category__name", "category_id",
    ).annotate(amount=_coalesce_sum("total_amount")).order_by("-amount"))

    by_branch = list(qs.filter(status=EXPENSE_APPROVED).values("branch__name").annotate(
        amount=_coalesce_sum("total_amount"),
    ).order_by("-amount"))

    return {
        **agg,
        "category_breakdown": [
            {"category_id": str(r["category_id"]), "category": r["category__name"],
             "amount": r["amount"],
             "percentage": _safe_div(r["amount"] * HUNDRED, agg["approved_expenses"] or Decimal("1"))}
            for r in by_category
        ],
        "branch_breakdown": [
            {"branch": r["branch__name"], "amount": r["amount"]} for r in by_branch
        ],
    }


def aggregate_payables(accessible_branches, date_from, date_to):
    from financials.models import Payable
    from financials.constants import (
        PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID, PAYABLE_PAID,
        PAYABLE_OVERDUE, PAYABLE_CANCELLED,
    )
    qs = Payable.objects.filter(branch__in=accessible_branches)

    agg = qs.aggregate(
        total_payables=_coalesce_sum("amount"),
        outstanding_payables=_coalesce_sum("remaining_amount",
            filter=Q(status__in=[PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID])),
        overdue_payables=_coalesce_sum("remaining_amount", filter=Q(status=PAYABLE_OVERDUE)),
        partially_paid=_coalesce_sum("paid_amount", filter=Q(status=PAYABLE_PARTIALLY_PAID)),
        paid=_coalesce_sum("paid_amount", filter=Q(status=PAYABLE_PAID)),
    )

    by_supplier = list(
        qs.filter(status__in=[PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID, PAYABLE_OVERDUE])
        .values("supplier_invoice__supplier__name", "supplier_invoice__supplier_id")
        .annotate(outstanding=_coalesce_sum("remaining_amount"))
        .order_by("-outstanding")[:20]
    )
    by_branch = list(
        qs.filter(status__in=[PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID, PAYABLE_OVERDUE])
        .values("branch__name")
        .annotate(outstanding=_coalesce_sum("remaining_amount"))
        .order_by("-outstanding")
    )
    by_due_date = list(
        qs.filter(status__in=[PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID, PAYABLE_OVERDUE])
        .values("due_date")
        .annotate(outstanding=_coalesce_sum("remaining_amount"))
        .order_by("due_date")[:30]
    )

    return {
        **agg,
        "payable_by_supplier": [
            {"supplier_id": str(r["supplier_invoice__supplier_id"]),
             "supplier": r["supplier_invoice__supplier__name"],
             "outstanding": r["outstanding"]}
            for r in by_supplier
        ],
        "payable_by_branch": [
            {"branch": r["branch__name"], "outstanding": r["outstanding"]} for r in by_branch
        ],
        "payable_by_due_date": [
            {"due_date": r["due_date"], "outstanding": r["outstanding"]} for r in by_due_date
        ],
    }
