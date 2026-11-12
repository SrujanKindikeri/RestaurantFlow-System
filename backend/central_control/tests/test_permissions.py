# =============================================================================
# RestaurantFlow — Central Control Center Tests: Permissions & Scope
# Phase 15
# =============================================================================

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from organizations.models import Organization, Restaurant, Branch
from accounts.models import Role, Permission, UserRoleAssignment

User = get_user_model()

BASE_URL = "/api/central-control/"


def _make_org(name):
    return Organization.objects.create(name=name, slug=name.replace(" ", "-").lower())


def _make_restaurant(org):
    return Restaurant.objects.create(organization=org, name="R", code="R1")


def _make_central_user(org, email, permissions=None):
    """Create a user with COMPANY_HEAD role + specified permissions."""
    role, _ = Role.objects.get_or_create(
        code=Role.CODE_COMPANY_HEAD,
        defaults={"name": "Company Head", "scope": Role.SCOPE_ORGANIZATION},
    )
    if permissions:
        for code in permissions:
            parts = code.split(".")
            perm, _ = Permission.objects.get_or_create(
                code=code,
                defaults={
                    "name": code,
                    "module": "central_control",
                    "action": ".".join(parts[2:]) if len(parts) > 2 else parts[-1],
                },
            )
            role.permissions.add(perm)
    user = User.objects.create_user(email=email, password="pass", first_name="CC", last_name="U")
    UserRoleAssignment.objects.create(user=user, role=role, organization=org, is_active=True)
    return user


class UnauthenticatedAccessTests(TestCase):

    def test_all_endpoints_require_authentication(self):
        client = APIClient()
        endpoints = [
            "dashboard/", "restaurants/", "restaurants/health/",
            "branches/", "alerts/", "issues/", "events/",
            "system-health/", "settings/", "audit/", "users/",
        ]
        for path in endpoints:
            resp = client.get(f"{BASE_URL}{path}")
            self.assertIn(
                resp.status_code, [401, 403],
                f"Expected 401/403 for unauthenticated GET {path}, got {resp.status_code}"
            )


class CompanyIsolationTests(TestCase):
    """Verify Company A user cannot see Company B data."""

    def setUp(self):
        self.org_a = _make_org("Company Alpha")
        self.org_b = _make_org("Company Beta")
        self.user_a = _make_central_user(
            self.org_a, "alpha@test.com",
            ["central_control.dashboard.view", "central_control.alert.view"]
        )
        self.user_b = _make_central_user(
            self.org_b, "beta@test.com",
            ["central_control.dashboard.view", "central_control.alert.view"]
        )

    def test_dashboard_returns_own_org(self):
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        resp = client.get(f"{BASE_URL}dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["organization_name"], self.org_a.name)

    def test_user_b_sees_own_org_dashboard(self):
        client = APIClient()
        client.force_authenticate(user=self.user_b)
        resp = client.get(f"{BASE_URL}dashboard/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["organization_name"], self.org_b.name)

    def test_user_a_cannot_access_org_b_via_param(self):
        """Passing org_b's ID in the query param should not leak org_b data to user_a."""
        client = APIClient()
        client.force_authenticate(user=self.user_a)
        resp = client.get(f"{BASE_URL}dashboard/", {"organization_id": str(self.org_b.pk)})
        # Should either return 403 or fall back to user_a's own org
        if resp.status_code == 200:
            # If it returns 200, it must be user_a's org
            self.assertEqual(resp.json()["organization_name"], self.org_a.name)
        else:
            self.assertIn(resp.status_code, [403, 404])


class PermissionEnforcementTests(TestCase):

    def setUp(self):
        self.org = _make_org("Perm Test Org")
        # User WITH dashboard.view but WITHOUT alert.resolve
        self.viewer = _make_central_user(
            self.org, "viewer@test.com",
            ["central_control.dashboard.view", "central_control.alert.view"]
        )

    def test_viewer_can_list_alerts(self):
        client = APIClient()
        client.force_authenticate(user=self.viewer)
        resp = client.get(f"{BASE_URL}alerts/")
        self.assertEqual(resp.status_code, 200)

    def test_viewer_cannot_resolve_alerts(self):
        """Without alert.resolve permission, POST to resolve should be 403."""
        from django.utils import timezone
        from central_control.models import CentralAlert
        from central_control.constants import ALERT_OPEN, ALERT_TYPE_KITCHEN_DELAY, SEVERITY_HIGH, SOURCE_TYPE_KITCHEN_ORDER
        from central_control.alert_rules import _build_fingerprint

        alert = CentralAlert.objects.create(
            organization=self.org,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            title="Need resolve permission",
            message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-perm",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "ko-perm", self.org.pk,
            ),
            status=ALERT_OPEN,
            detected_at=timezone.now(),
        )
        client = APIClient()
        client.force_authenticate(user=self.viewer)
        resp = client.post(
            f"{BASE_URL}alerts/{alert.pk}/resolve/",
            {"resolution_note": "test"},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)


class AuditLogTests(TestCase):

    def test_audit_entries_created_on_alert_actions(self):
        from django.utils import timezone
        from central_control.models import CentralAlert, CentralControlAuditLog
        from central_control.constants import (
            ALERT_OPEN, ALERT_TYPE_KITCHEN_DELAY, SEVERITY_HIGH,
            SOURCE_TYPE_KITCHEN_ORDER,
        )
        from central_control.alert_rules import _build_fingerprint
        from central_control.services import AlertService

        org = _make_org("Audit Org")
        actor = _make_central_user(org, "audit_actor@test.com")

        alert = CentralAlert.objects.create(
            organization=org,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            title="Audit test",
            message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-audit",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "ko-audit", org.pk,
            ),
            status=ALERT_OPEN,
            detected_at=timezone.now(),
        )

        AlertService.acknowledge_alert(actor=actor, alert_id=alert.pk, organization=org)

        audit_count = CentralControlAuditLog.objects.filter(
            entity_id=alert.pk,
            action="CENTRAL_ALERT_ACKNOWLEDGED",
        ).count()
        self.assertEqual(audit_count, 1)

    def test_audit_log_is_immutable(self):
        from central_control.models import CentralControlAuditLog
        org = _make_org("Immutable Audit Org")
        actor = _make_central_user(org, "imm_actor@test.com")
        entry = CentralControlAuditLog.objects.create(
            actor=actor,
            action="CENTRAL_ISSUE_CREATED",
            entity_type="ISSUE",
            organization=org,
        )
        with self.assertRaises(ValueError):
            entry.action = "CENTRAL_ISSUE_RESOLVED"
            entry.save()
