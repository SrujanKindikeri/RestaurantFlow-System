# =============================================================================
# RestaurantFlow — Central Control Center Dashboard Services
# Phase 15
#
# Assembles the organization-level Central Control dashboard.
# Reuses Phase 14 reporting services where possible.
# Adds exception visibility, health status, and alert/issue counts.
#
# Cache strategy:
#   - Cache keys scoped to organization_id — never shared across orgs.
#   - Critical alert counts cached at 15 seconds only.
#   - Heavy aggregations cached at 60 seconds.
# =============================================================================

import logging
from datetime import date
from decimal import Decimal

from django.core.cache import cache
from django.utils import timezone

from central_control.constants import (
    CACHE_TTL_DASHBOARD, CACHE_TTL_RESTAURANT, CACHE_TTL_ALERTS,
    CACHE_KEY_DASHBOARD, CACHE_KEY_RESTAURANT, CACHE_KEY_ALERT_COUNTS,
)

logger = logging.getLogger("central_control")


def _org_cache_key(template: str, org_id) -> str:
    """Build a scoped cache key for organization-level data."""
    return template.format(org_id=str(org_id))


def get_central_dashboard(user, *, organization_id=None):
    """
    Assemble the Central Control organization-level dashboard payload.

    Reuses Phase 14 reporting aggregations for operational metrics.
    Adds central-control-specific data: alerts, issues, health.

    Returns a JSON-serializable dict.
    """
    from accounts import access as acl
    from organizations.models import Organization, Restaurant, Branch

    # Resolve organization scope
    accessible_orgs = acl.get_accessible_organizations(user)
    if organization_id:
        try:
            org = accessible_orgs.get(pk=organization_id)
        except Organization.DoesNotExist:
            from central_control.exceptions import ScopeViolationError
            raise ScopeViolationError("Organization not accessible.")
    else:
        org = accessible_orgs.first()
        if org is None:
            return {}

    cache_key = _org_cache_key(CACHE_KEY_DASHBOARD, org.pk)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    accessible_restaurants = acl.get_accessible_restaurants(user).filter(organization=org)
    accessible_branches = acl.get_accessible_branches(user).filter(
        restaurant__organization=org
    )

    # ---- Restaurant / Branch counts ----
    total_restaurants = accessible_restaurants.count()
    active_restaurants = accessible_restaurants.filter(is_active=True).count()
    total_branches = accessible_branches.count()
    active_branches = accessible_branches.filter(is_active=True).count()

    # ---- Operations (reuse reporting aggregations) ----
    today = date.today()
    operations = _get_operations_summary(accessible_branches, today)

    # ---- Kitchen summary ----
    kitchen = _get_kitchen_summary(accessible_branches)

    # ---- Inventory alerts ----
    inventory = _get_inventory_summary(accessible_branches)

    # ---- Financial summary ----
    financial = _get_financial_summary(accessible_restaurants)

    # ---- Alert counts ----
    alert_counts = _get_alert_counts(org)

    # ---- Issue counts ----
    issue_counts = _get_issue_counts(org)

    result = {
        "organization_id": str(org.pk),
        "organization_name": org.name,
        "restaurants": {
            "total": total_restaurants,
            "active": active_restaurants,
            "inactive": total_restaurants - active_restaurants,
        },
        "branches": {
            "total": total_branches,
            "active": active_branches,
        },
        "operations": operations,
        "kitchen": kitchen,
        "inventory": inventory,
        "financial": financial,
        "alerts": alert_counts,
        "issues": issue_counts,
        "generated_at": timezone.now().isoformat(),
    }

    cache.set(cache_key, result, CACHE_TTL_DASHBOARD)
    return result


def _get_operations_summary(accessible_branches, today) -> dict:
    """Get today's orders, sales, open tables, open counters."""
    from billing.models import Bill, BillStatus
    from counters.models import CounterSession, SessionStatus
    from django.db.models import Count, Sum
    from django.db.models import Q

    try:
        from orders.models import Order
        open_tables = (
            Order.objects
            .filter(
                branch__in=accessible_branches,
                created_at__date=today,
            )
            .exclude(status__in=["CANCELLED", "CLOSED"])
            .count()
        )
    except Exception:
        open_tables = 0

    try:
        bills = Bill.objects.filter(
            branch__in=accessible_branches,
            status=BillStatus.FINALIZED,
            created_at__date=today,
        ).aggregate(
            order_count=Count("id"),
            revenue=Sum("grand_total"),
        )
        orders_today = bills["order_count"] or 0
        sales_today = bills["revenue"] or Decimal("0.00")
    except Exception:
        orders_today = 0
        sales_today = Decimal("0.00")

    try:
        open_counters = CounterSession.objects.filter(
            counter__branch__in=accessible_branches,
            status=SessionStatus.OPEN,
        ).count()
    except Exception:
        open_counters = 0

    return {
        "orders_today": orders_today,
        "sales_today": str(sales_today),
        "open_tables": open_tables,
        "open_counters": open_counters,
    }


def _get_kitchen_summary(accessible_branches) -> dict:
    """Get pending and delayed kitchen order counts."""
    from kitchen.models import KitchenOrder, KitchenOrderStatus
    from django.db.models import Count
    from datetime import timedelta

    try:
        active_statuses = [
            KitchenOrderStatus.NEW,
            KitchenOrderStatus.ACCEPTED,
            KitchenOrderStatus.PREPARING,
        ]
        pending = KitchenOrder.objects.filter(
            branch__in=accessible_branches,
            status__in=active_statuses,
        ).count()

        # Delayed = PREPARING and started_at older than 20 min (default threshold)
        delay_cutoff = timezone.now() - timedelta(minutes=20)
        delayed = KitchenOrder.objects.filter(
            branch__in=accessible_branches,
            status=KitchenOrderStatus.PREPARING,
            started_at__lt=delay_cutoff,
        ).count()

        return {"pending_orders": pending, "delayed_orders": delayed}
    except Exception as exc:
        logger.warning("_get_kitchen_summary error: %s", exc)
        return {"pending_orders": 0, "delayed_orders": 0}


def _get_inventory_summary(accessible_branches) -> dict:
    """Get low-stock and out-of-stock item counts across accessible branches."""
    from inventory.models import StockBalance
    from decimal import Decimal as D

    try:
        # Aggregate per inventory_item across all locations in accessible branches
        balances = (
            StockBalance.objects
            .filter(
                storage_location__branch__in=accessible_branches,
                inventory_item__is_active=True,
            )
            .select_related("inventory_item", "storage_location")
        )

        item_totals: dict = {}
        for sb in balances:
            iid = str(sb.inventory_item_id)
            if iid not in item_totals:
                item_totals[iid] = {
                    "available": D("0.000"),
                    "reorder_level": sb.inventory_item.reorder_level,
                }
            item_totals[iid]["available"] += sb.available_quantity

        low_stock = sum(
            1 for v in item_totals.values()
            if D("0.000") < v["available"] <= v["reorder_level"]
        )
        out_of_stock = sum(
            1 for v in item_totals.values()
            if v["available"] <= D("0.000")
        )
        return {"low_stock_items": low_stock, "out_of_stock_items": out_of_stock}
    except Exception as exc:
        logger.warning("_get_inventory_summary error: %s", exc)
        return {"low_stock_items": 0, "out_of_stock_items": 0}


def _get_financial_summary(accessible_restaurants) -> dict:
    """Get pending expenses and overdue payables counts."""
    from financials.models import Expense, Payable
    from financials.constants import EXPENSE_SUBMITTED, PAYABLE_OVERDUE

    try:
        pending_expenses = Expense.objects.filter(
            restaurant__in=accessible_restaurants,
            status=EXPENSE_SUBMITTED,
        ).count()
    except Exception:
        pending_expenses = 0

    try:
        overdue_payables = Payable.objects.filter(
            restaurant__in=accessible_restaurants,
            status=PAYABLE_OVERDUE,
        ).count()
    except Exception:
        overdue_payables = 0

    return {
        "pending_expenses": pending_expenses,
        "overdue_payables": overdue_payables,
    }


def _get_alert_counts(organization) -> dict:
    """Get alert counts by severity for the organization. Short TTL cache."""
    from central_control.models import CentralAlert
    from central_control.constants import (
        ALERT_ACTIVE_STATUSES,
        SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW,
    )
    from django.db.models import Count

    cache_key = _org_cache_key(CACHE_KEY_ALERT_COUNTS, organization.pk)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    counts = CentralAlert.objects.filter(
        organization=organization,
        status__in=list(ALERT_ACTIVE_STATUSES),
    ).values("severity").annotate(count=Count("id"))

    result = {
        SEVERITY_CRITICAL: 0,
        SEVERITY_HIGH: 0,
        SEVERITY_MEDIUM: 0,
        SEVERITY_LOW: 0,
        "info": 0,
    }
    severity_lower_map = {
        "CRITICAL": SEVERITY_CRITICAL,
        "HIGH": SEVERITY_HIGH,
        "MEDIUM": SEVERITY_MEDIUM,
        "LOW": SEVERITY_LOW,
        "INFO": "info",
    }
    for row in counts:
        key = severity_lower_map.get(row["severity"], row["severity"].lower())
        result[key] = row["count"]

    cache.set(cache_key, result, CACHE_TTL_ALERTS)
    return result


def _get_issue_counts(organization) -> dict:
    """Get issue counts for the organization."""
    from central_control.models import CentralIssue
    from central_control.constants import ISSUE_ACTIVE_STATUSES, ISSUE_SEVERITY_CRITICAL

    open_count = CentralIssue.objects.filter(
        organization=organization,
        status__in=list(ISSUE_ACTIVE_STATUSES),
    ).count()

    critical_count = CentralIssue.objects.filter(
        organization=organization,
        status__in=list(ISSUE_ACTIVE_STATUSES),
        severity=ISSUE_SEVERITY_CRITICAL,
    ).count()

    return {"open": open_count, "critical": critical_count}


def get_restaurant_health_list(user, *, organization_id=None):
    """
    Return a list of restaurant health dicts for the Central Control UI.
    Caches per-organization. Falls back to live data on cache miss.
    """
    from accounts import access as acl
    from organizations.models import Organization
    from central_control.health_services import RestaurantHealthService

    accessible_orgs = acl.get_accessible_organizations(user)
    if organization_id:
        try:
            org = accessible_orgs.get(pk=organization_id)
        except Organization.DoesNotExist:
            return []
    else:
        org = accessible_orgs.first()
        if org is None:
            return []

    cache_key = _org_cache_key(CACHE_KEY_RESTAURANT, org.pk)
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    accessible_restaurants = acl.get_accessible_restaurants(user).filter(organization=org)
    svc = RestaurantHealthService(organization=org)
    result = svc.compute_for_organization(accessible_restaurants)

    cache.set(cache_key, result, CACHE_TTL_RESTAURANT)
    return result


def get_system_health():
    """
    Return system component health status.
    Delegates entirely to SystemHealthService (which handles its own caching).
    """
    from central_control.health_services import SystemHealthService

    svc = SystemHealthService()
    health = svc.check_all()
    overall = svc.get_overall_status(health)
    return {"overall": overall, **health}


def invalidate_dashboard_cache(organization_id):
    """
    Invalidate all dashboard-related cache entries for an organization.
    Called after significant state changes (alert/issue creation, etc.).
    """
    cache.delete(_org_cache_key(CACHE_KEY_DASHBOARD, organization_id))
    cache.delete(_org_cache_key(CACHE_KEY_RESTAURANT, organization_id))
    cache.delete(_org_cache_key(CACHE_KEY_ALERT_COUNTS, organization_id))
