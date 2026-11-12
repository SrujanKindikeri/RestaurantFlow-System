# =============================================================================
# RestaurantFlow — Central Control Center Tests: Dashboard
# Phase 15
# =============================================================================

from django.test import TestCase
from django.contrib.auth import get_user_model

from organizations.models import Organization, Restaurant, Branch
from accounts.models import Role, Permission, UserRoleAssignment
from central_control.models import CentralControlSettings, CentralAlert, CentralIssue

User = get_user_model()


def make_org(name="Test Corp"):
    return Organization.objects.create(name=name, slug=f"test-corp-{name.lower().replace(' ','-')}")


def make_restaurant(org, name="Spice Garden"):
    return Restaurant.objects.create(organization=org, name=name, code=f"SG{name[:3].upper()}")


def make_branch(restaurant, name="Main Branch"):
    return Branch.objects.create(restaurant=restaurant, name=name, code=f"B{name[:3].upper()}")


def make_central_user(org, email="cc@test.com"):
    """Create a user with COMPANY_HEAD role assignment."""
    role, _ = Role.objects.get_or_create(
        code=Role.CODE_COMPANY_HEAD,
        defaults={"name": "Company Head", "scope": Role.SCOPE_ORGANIZATION},
    )
    perm, _ = Permission.objects.get_or_create(
        code="central_control.dashboard.view",
        defaults={"name": "View CC Dashboard", "module": "central_control", "action": "dashboard.view"},
    )
    role.permissions.add(perm)
    user = User.objects.create_user(email=email, password="pass", first_name="CC", last_name="Admin")
    UserRoleAssignment.objects.create(user=user, role=role, organization=org, is_active=True)
    return user


class DashboardTests(TestCase):

    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.user = make_central_user(self.org)
        self.client.force_login(self.user)

    def test_dashboard_requires_authentication(self):
        from django.test import Client
        c = Client()
        resp = c.get("/api/central-control/dashboard/")
        self.assertIn(resp.status_code, [401, 403])

    def test_dashboard_returns_200_for_authorized_user(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.get("/api/central-control/dashboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("restaurants", data)
        self.assertIn("alerts", data)
        self.assertIn("issues", data)

    def test_dashboard_org_isolation(self):
        """A user in Org A must not see Org B data."""
        org_b = make_org("Org B")
        user_b = make_central_user(org_b, email="cc_b@test.com")

        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=user_b)
        resp = client.get("/api/central-control/dashboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # org_b user sees their own org
        self.assertEqual(data.get("organization_name"), org_b.name)

    def test_dashboard_restaurant_counts_correct(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.user)
        resp = client.get("/api/central-control/dashboard/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["restaurants"]["total"], 1)
        self.assertGreaterEqual(data["branches"]["total"], 1)


class DashboardPermissionTests(TestCase):

    def setUp(self):
        self.org = make_org("Perm Org")
        self.restaurant = make_restaurant(self.org)

    def test_restaurant_manager_cannot_access_dashboard(self):
        """Restaurant Manager must not have central_control.dashboard.view by default."""
        role, _ = Role.objects.get_or_create(
            code=Role.CODE_RESTAURANT_MANAGER,
            defaults={"name": "Restaurant Manager", "scope": Role.SCOPE_RESTAURANT},
        )
        user = User.objects.create_user(email="mgr@test.com", password="pass", first_name="M", last_name="G")
        UserRoleAssignment.objects.create(
            user=user, role=role,
            organization=self.org, restaurant=self.restaurant,
            is_active=True,
        )
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.get("/api/central-control/dashboard/")
        # Should get 403 — no central_control.dashboard.view permission
        self.assertEqual(resp.status_code, 403)
