# =============================================================================
# RestaurantFlow — Central Control Center Health Services
# Phase 15
#
# Two health service classes:
#   RestaurantHealthService  — per-restaurant health status (HEALTHY/WARNING/CRITICAL)
#   SystemHealthService      — application infrastructure health checks
#
# Design:
#   - Health status is DERIVED from explicit rules, not an arbitrary score.
#   - SystemHealthService uses lightweight checks with timeouts.
#   - No infrastructure secrets are ever exposed.
#   - Services are read-only; they detect and report — they do not fix.
# =============================================================================

import logging
import time

from django.core.cache import cache
from django.utils import timezone

from central_control.constants import (
    HEALTH_HEALTHY, HEALTH_WARNING, HEALTH_CRITICAL, HEALTH_OFFLINE, HEALTH_UNKNOWN,
    COMPONENT_HEALTHY, COMPONENT_DEGRADED, COMPONENT_UNAVAILABLE, COMPONENT_UNKNOWN,
    CACHE_TTL_HEALTH, CACHE_KEY_SYSTEM_HEALTH,
    ALERT_ACTIVE_STATUSES,
    SEVERITY_CRITICAL, SEVERITY_HIGH,
    ALERT_TYPE_OUT_OF_STOCK,
)

logger = logging.getLogger("central_control")


# ---------------------------------------------------------------------------
# RestaurantHealthService
# ---------------------------------------------------------------------------

class RestaurantHealthService:
    """
    Computes health status for each restaurant visible to the requesting user.

    Health rule engine:
        OFFLINE  → restaurant is_active=False OR all branches inactive
        CRITICAL → any unresolved CRITICAL alert exists
                   OR > 50% of branches inactive
                   OR kitchen has excessive delayed orders
        WARNING  → low stock threshold exceeded
                   OR high number of pending issues
                   OR any HIGH severity unresolved alert
        HEALTHY  → none of the above conditions met
    """

    def __init__(self, organization):
        self.organization = organization
        self.today = timezone.now().date()

    def compute_for_restaurant(self, restaurant):
        """
        Compute health data for a single restaurant.
        Returns a dict with health_status and supporting metrics.
        """
        from organizations.models import Branch
        from kitchen.models import KitchenOrder, KitchenOrderStatus
        from inventory.models import StockBalance
        from financials.models import Expense, Payable
        from financials.constants import EXPENSE_SUBMITTED, PAYABLE_OVERDUE
        from central_control.models import CentralAlert, CentralIssue
        from central_control.constants import (
            ALERT_OPEN, ALERT_ACKNOWLEDGED, ISSUE_ACTIVE_STATUSES,
            SEVERITY_CRITICAL, SEVERITY_HIGH,
        )
        from billing.models import Bill, BillStatus
        from orders.models import Order
        from django.db.models import Count, Sum, Q
        from decimal import Decimal

        # ---- Branch counts ----
        branches = Branch.objects.filter(restaurant=restaurant)
        branch_count = branches.count()
        active_branch_count = branches.filter(is_active=True).count()
        inactive_branch_count = branch_count - active_branch_count

        # ---- Today's operations ----
        try:
            today_bills = Bill.objects.filter(
                branch__restaurant=restaurant,
                status=BillStatus.FINALIZED,
                created_at__date=self.today,
            ).aggregate(
                count=Count("id"),
                revenue=Sum("grand_total"),
            )
            orders_today = today_bills["count"] or 0
            sales_today = today_bills["revenue"] or Decimal("0.00")
        except Exception:
            orders_today = 0
            sales_today = Decimal("0.00")

        # ---- Kitchen ----
        active_kitchen_statuses = [
            KitchenOrderStatus.NEW,
            KitchenOrderStatus.ACCEPTED,
            KitchenOrderStatus.PREPARING,
        ]
        pending_kitchen_count = KitchenOrder.objects.filter(
            branch__restaurant=restaurant,
            status__in=active_kitchen_statuses,
        ).count()

        # Delayed kitchen orders (using default threshold if settings unavailable)
        try:
            settings_obj = self.organization.central_control_settings
            delay_minutes = settings_obj.kitchen_delay_minutes
        except Exception:
            from central_control.constants import DEFAULT_KITCHEN_DELAY_MINUTES
            delay_minutes = DEFAULT_KITCHEN_DELAY_MINUTES

        from datetime import timedelta
        delay_cutoff = timezone.now() - timedelta(minutes=delay_minutes)
        delayed_kitchen_count = KitchenOrder.objects.filter(
            branch__restaurant=restaurant,
            status=KitchenOrderStatus.PREPARING,
            started_at__lt=delay_cutoff,
        ).count()

        # ---- Inventory ----
        low_stock_items = 0
        out_of_stock_items = 0
        try:
            from decimal import Decimal as D
            from inventory.models import InventoryItem
            items = InventoryItem.objects.filter(
                restaurant=restaurant, is_active=True
            ).prefetch_related("stock_balances")
            for item in items:
                total_avail = sum(
                    sb.available_quantity for sb in item.stock_balances.all()
                )
                if total_avail <= D("0.000"):
                    out_of_stock_items += 1
                elif total_avail <= item.reorder_level:
                    low_stock_items += 1
        except Exception:
            pass

        # ---- Financial ----
        pending_expenses = Expense.objects.filter(
            restaurant=restaurant,
            status=EXPENSE_SUBMITTED,
        ).count()

        overdue_payables = Payable.objects.filter(
            restaurant=restaurant,
            status=PAYABLE_OVERDUE,
        ).count()

        # ---- Alerts ----
        active_statuses = list(ALERT_ACTIVE_STATUSES)
        unresolved_alerts = CentralAlert.objects.filter(
            restaurant=restaurant,
            status__in=active_statuses,
        ).count()

        unresolved_critical_alerts = CentralAlert.objects.filter(
            restaurant=restaurant,
            status__in=active_statuses,
            severity=SEVERITY_CRITICAL,
        ).count()

        unresolved_high_alerts = CentralAlert.objects.filter(
            restaurant=restaurant,
            status__in=active_statuses,
            severity=SEVERITY_HIGH,
        ).count()

        # ---- Issues ----
        open_issues = CentralIssue.objects.filter(
            restaurant=restaurant,
            status__in=list(ISSUE_ACTIVE_STATUSES),
        ).count()

        critical_issues = CentralIssue.objects.filter(
            restaurant=restaurant,
            status__in=list(ISSUE_ACTIVE_STATUSES),
            severity=SEVERITY_CRITICAL,
        ).count()

        # ---- Health rule engine ----
        health_status = self._compute_health_status(
            restaurant=restaurant,
            branch_count=branch_count,
            active_branch_count=active_branch_count,
            unresolved_critical_alerts=unresolved_critical_alerts,
            unresolved_high_alerts=unresolved_high_alerts,
            delayed_kitchen_count=delayed_kitchen_count,
            low_stock_items=low_stock_items,
            out_of_stock_items=out_of_stock_items,
            overdue_payables=overdue_payables,
            open_issues=open_issues,
        )

        return {
            "restaurant_id": str(restaurant.pk),
            "restaurant_name": restaurant.name,
            "is_active": restaurant.is_active,
            "branch_count": branch_count,
            "active_branch_count": active_branch_count,
            "orders_today": orders_today,
            "sales_today": str(sales_today),
            "pending_kitchen_orders": pending_kitchen_count,
            "delayed_kitchen_orders": delayed_kitchen_count,
            "low_stock_items": low_stock_items,
            "out_of_stock_items": out_of_stock_items,
            "pending_expenses": pending_expenses,
            "overdue_payables": overdue_payables,
            "unresolved_alerts": unresolved_alerts,
            "unresolved_critical_alerts": unresolved_critical_alerts,
            "open_issues": open_issues,
            "critical_issues": critical_issues,
            "health_status": health_status,
        }

    def _compute_health_status(
        self,
        *,
        restaurant,
        branch_count,
        active_branch_count,
        unresolved_critical_alerts,
        unresolved_high_alerts,
        delayed_kitchen_count,
        low_stock_items,
        out_of_stock_items,
        overdue_payables,
        open_issues,
    ) -> str:
        """
        Apply explicit health rules to determine status.
        Rules are evaluated in order from most severe to least severe.
        """
        # OFFLINE: restaurant is inactive
        if not restaurant.is_active:
            return HEALTH_OFFLINE

        # OFFLINE: all branches are inactive
        if branch_count > 0 and active_branch_count == 0:
            return HEALTH_OFFLINE

        # CRITICAL: any unresolved CRITICAL alert
        if unresolved_critical_alerts > 0:
            return HEALTH_CRITICAL

        # CRITICAL: more than half of branches are inactive
        if branch_count > 1 and active_branch_count < branch_count // 2:
            return HEALTH_CRITICAL

        # CRITICAL: severely delayed kitchen (more than 5 delayed orders)
        if delayed_kitchen_count > 5:
            return HEALTH_CRITICAL

        # WARNING: any HIGH severity unresolved alert
        if unresolved_high_alerts > 0:
            return HEALTH_WARNING

        # WARNING: any out-of-stock items
        if out_of_stock_items > 0:
            return HEALTH_WARNING

        # WARNING: more than 5 low-stock items
        if low_stock_items > 5:
            return HEALTH_WARNING

        # WARNING: any overdue payables
        if overdue_payables > 0:
            return HEALTH_WARNING

        # WARNING: more than 3 open issues
        if open_issues > 3:
            return HEALTH_WARNING

        # WARNING: delayed kitchen orders present
        if delayed_kitchen_count > 0:
            return HEALTH_WARNING

        return HEALTH_HEALTHY

    def compute_for_organization(self, accessible_restaurants):
        """
        Compute health for all restaurants in the queryset.
        Returns a list of health dicts.
        """
        results = []
        for restaurant in accessible_restaurants.select_related("organization"):
            try:
                result = self.compute_for_restaurant(restaurant)
                results.append(result)
            except Exception as exc:
                logger.error(
                    "RestaurantHealthService: error computing health for restaurant=%s: %s",
                    restaurant.pk, exc, exc_info=True,
                )
                results.append({
                    "restaurant_id": str(restaurant.pk),
                    "restaurant_name": restaurant.name,
                    "health_status": HEALTH_UNKNOWN,
                    "error": str(exc),
                })
        return results


# ---------------------------------------------------------------------------
# SystemHealthService
# ---------------------------------------------------------------------------

class SystemHealthService:
    """
    Performs lightweight application-level health checks.

    IMPORTANT security rules:
        - Never expose database URLs, Redis URLs, passwords, or secrets.
        - Never expose stack traces to end users.
        - Use try/except with timeouts to prevent hanging.
        - Return DEGRADED rather than crashing on partial failures.
    """

    TIMEOUT_SECONDS = 5  # Maximum time for any single check

    def check_all(self) -> dict:
        """
        Run all health checks and return a summary dict.
        Cached for CACHE_TTL_HEALTH seconds.
        """
        cached = cache.get(CACHE_KEY_SYSTEM_HEALTH)
        if cached is not None:
            return cached

        result = {
            "api": COMPONENT_HEALTHY,       # If this runs, the API is up
            "database": self._check_database(),
            "redis": self._check_redis(),
            "workers": self._check_workers(),
            "websocket": self._check_websocket(),
            "checked_at": timezone.now().isoformat(),
        }

        cache.set(CACHE_KEY_SYSTEM_HEALTH, result, CACHE_TTL_HEALTH)
        return result

    def _check_database(self) -> str:
        """Verify database connectivity with a minimal query."""
        try:
            start = time.monotonic()
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            if elapsed_ms > 3000:
                return COMPONENT_DEGRADED
            return COMPONENT_HEALTHY
        except Exception as exc:
            logger.error("SystemHealthService: database check failed: %s", exc)
            return COMPONENT_UNAVAILABLE

    def _check_redis(self) -> str:
        """Verify Redis connectivity via the Django cache backend."""
        try:
            start = time.monotonic()
            test_key = "_cc_health_check_"
            cache.set(test_key, "ok", 10)
            val = cache.get(test_key)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            if val != "ok":
                return COMPONENT_DEGRADED
            if elapsed_ms > 2000:
                return COMPONENT_DEGRADED
            return COMPONENT_HEALTHY
        except Exception as exc:
            logger.error("SystemHealthService: Redis check failed: %s", exc)
            return COMPONENT_UNAVAILABLE

    def _check_workers(self) -> str:
        """
        Check for Celery worker availability.
        Returns UNKNOWN if Celery is not configured/active (as in this project).
        Returns HEALTHY if workers respond, DEGRADED/UNAVAILABLE if not.
        """
        try:
            # Check if Celery app exists and workers are active
            from config.celery import app as celery_app
            inspect = celery_app.control.inspect(timeout=2)
            active = inspect.active()
            if active:
                return COMPONENT_HEALTHY
            return COMPONENT_DEGRADED
        except ImportError:
            # Celery not yet wired — this is expected in the current project state
            return COMPONENT_UNKNOWN
        except Exception as exc:
            logger.warning("SystemHealthService: worker check failed: %s", exc)
            return COMPONENT_UNKNOWN

    def _check_websocket(self) -> str:
        """
        Verify Django Channels / Redis channel layer availability.
        We check if the channel layer backend is reachable.
        """
        try:
            from channels.layers import get_channel_layer
            import asyncio

            channel_layer = get_channel_layer()
            if channel_layer is None:
                return COMPONENT_UNAVAILABLE

            # Try a lightweight channel layer operation
            # We use a synchronous wrapper to avoid async context issues
            async def _ping():
                await channel_layer.group_add("_health_check_group_", "_health_check_channel_")
                await channel_layer.group_discard("_health_check_group_", "_health_check_channel_")

            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(asyncio.wait_for(_ping(), timeout=3))
            except asyncio.TimeoutError:
                return COMPONENT_DEGRADED
            except RuntimeError:
                # Already in an event loop (e.g. during async requests) — skip
                return COMPONENT_HEALTHY

            return COMPONENT_HEALTHY
        except Exception as exc:
            logger.warning("SystemHealthService: WebSocket check failed: %s", exc)
            return COMPONENT_UNKNOWN

    def get_overall_status(self, health_dict: dict) -> str:
        """
        Derive an overall system status from individual component statuses.
        """
        statuses = [
            v for k, v in health_dict.items()
            if k not in ("checked_at", "overall")
        ]
        if COMPONENT_UNAVAILABLE in statuses:
            return HEALTH_CRITICAL
        if COMPONENT_DEGRADED in statuses:
            return HEALTH_WARNING
        if all(s in (COMPONENT_HEALTHY, COMPONENT_UNKNOWN) for s in statuses):
            return HEALTH_HEALTHY
        return HEALTH_UNKNOWN
