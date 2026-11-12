# =============================================================================
# RestaurantFlow — Central Control Center Tests: Health Services
# Phase 15
# =============================================================================

from django.test import TestCase
from django.contrib.auth import get_user_model

from organizations.models import Organization, Restaurant, Branch
from central_control.health_services import RestaurantHealthService
from central_control.constants import (
    HEALTH_HEALTHY, HEALTH_WARNING, HEALTH_CRITICAL, HEALTH_OFFLINE,
)

User = get_user_model()


def _org(n="Health Org"):
    return Organization.objects.create(name=n, slug=n.replace(" ", "-").lower())


def _rest(org, active=True):
    r = Restaurant.objects.create(organization=org, name="TestRest", code="HR1")
    if not active:
        r.is_active = False
        r.save()
    return r


def _branch(restaurant, active=True):
    b = Branch.objects.create(restaurant=restaurant, name="TestBranch", code="HB1")
    if not active:
        b.is_active = False
        b.save()
    return b


class RestaurantHealthRuleTests(TestCase):

    def setUp(self):
        self.org = _org()

    def test_inactive_restaurant_is_offline(self):
        restaurant = _rest(self.org, active=False)
        svc = RestaurantHealthService(organization=self.org)
        result = svc.compute_for_restaurant(restaurant)
        self.assertEqual(result["health_status"], HEALTH_OFFLINE)

    def test_healthy_restaurant(self):
        restaurant = _rest(self.org)
        _branch(restaurant)
        svc = RestaurantHealthService(organization=self.org)
        result = svc.compute_for_restaurant(restaurant)
        # With no alerts, issues, or stock problems it should be HEALTHY
        self.assertEqual(result["health_status"], HEALTH_HEALTHY)

    def test_critical_alert_makes_restaurant_critical(self):
        from django.utils import timezone
        from central_control.models import CentralAlert
        from central_control.constants import (
            SEVERITY_CRITICAL, ALERT_OPEN, ALERT_TYPE_KITCHEN_DELAY,
            SOURCE_TYPE_KITCHEN_ORDER,
        )
        from central_control.alert_rules import _build_fingerprint

        restaurant = _rest(self.org)
        _branch(restaurant)

        # Create an unresolved CRITICAL alert for this restaurant
        CentralAlert.objects.create(
            organization=self.org,
            restaurant=restaurant,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_CRITICAL,
            title="Critical kitchen issue",
            message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-crit",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "ko-crit", self.org.pk, restaurant.pk,
            ),
            status=ALERT_OPEN,
            detected_at=timezone.now(),
        )

        svc = RestaurantHealthService(organization=self.org)
        result = svc.compute_for_restaurant(restaurant)
        self.assertEqual(result["health_status"], HEALTH_CRITICAL)

    def test_high_alert_makes_restaurant_warning(self):
        from django.utils import timezone
        from central_control.models import CentralAlert
        from central_control.constants import (
            SEVERITY_HIGH, ALERT_OPEN, ALERT_TYPE_KITCHEN_DELAY,
            SOURCE_TYPE_KITCHEN_ORDER,
        )
        from central_control.alert_rules import _build_fingerprint

        restaurant = _rest(self.org)
        _branch(restaurant)

        CentralAlert.objects.create(
            organization=self.org,
            restaurant=restaurant,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            title="High severity alert",
            message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-high",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "ko-high", self.org.pk, restaurant.pk,
            ),
            status=ALERT_OPEN,
            detected_at=timezone.now(),
        )

        svc = RestaurantHealthService(organization=self.org)
        result = svc.compute_for_restaurant(restaurant)
        self.assertEqual(result["health_status"], HEALTH_WARNING)

    def test_all_branches_inactive_is_offline(self):
        restaurant = _rest(self.org)
        _branch(restaurant, active=False)  # Only branch is inactive
        svc = RestaurantHealthService(organization=self.org)
        result = svc.compute_for_restaurant(restaurant)
        self.assertEqual(result["health_status"], HEALTH_OFFLINE)

    def test_health_fields_present(self):
        restaurant = _rest(self.org)
        _branch(restaurant)
        svc = RestaurantHealthService(organization=self.org)
        result = svc.compute_for_restaurant(restaurant)
        required_fields = [
            "restaurant_id", "restaurant_name", "is_active",
            "branch_count", "active_branch_count",
            "orders_today", "sales_today",
            "pending_kitchen_orders", "delayed_kitchen_orders",
            "low_stock_items", "out_of_stock_items",
            "pending_expenses", "overdue_payables",
            "unresolved_alerts", "unresolved_critical_alerts",
            "open_issues", "critical_issues",
            "health_status",
        ]
        for field in required_fields:
            self.assertIn(field, result, f"Missing field: {field}")


class SystemHealthTests(TestCase):

    def test_system_health_returns_safe_dict(self):
        from central_control.health_services import SystemHealthService
        svc = SystemHealthService()
        health = svc.check_all()
        self.assertIn("api", health)
        self.assertIn("database", health)
        self.assertIn("redis", health)
        self.assertIn("workers", health)
        self.assertIn("websocket", health)
        self.assertIn("checked_at", health)

    def test_system_health_does_not_expose_credentials(self):
        from central_control.health_services import SystemHealthService
        import json
        svc = SystemHealthService()
        health = svc.check_all()
        serialized = json.dumps(health).lower()
        self.assertNotIn("password", serialized)
        self.assertNotIn("secret", serialized)
        self.assertNotIn("redis://", serialized)
        self.assertNotIn("postgresql://", serialized)

    def test_overall_status_healthy(self):
        from central_control.health_services import SystemHealthService
        from central_control.constants import COMPONENT_HEALTHY, HEALTH_HEALTHY
        svc = SystemHealthService()
        all_healthy = {
            "api": COMPONENT_HEALTHY,
            "database": COMPONENT_HEALTHY,
            "redis": COMPONENT_HEALTHY,
            "workers": COMPONENT_HEALTHY,
            "websocket": COMPONENT_HEALTHY,
        }
        self.assertEqual(svc.get_overall_status(all_healthy), HEALTH_HEALTHY)

    def test_overall_status_critical_when_unavailable(self):
        from central_control.health_services import SystemHealthService
        from central_control.constants import COMPONENT_UNAVAILABLE, HEALTH_CRITICAL
        svc = SystemHealthService()
        data = {"database": COMPONENT_UNAVAILABLE, "api": "HEALTHY"}
        self.assertEqual(svc.get_overall_status(data), HEALTH_CRITICAL)
