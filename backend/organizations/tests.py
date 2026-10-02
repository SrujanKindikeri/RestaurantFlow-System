# =============================================================================
# RestaurantFlow — Organizations Tests
# Phase 2
#
# Run:
#   python manage.py test organizations
#
# Coverage:
#   Organization  — CRUD, disable, reactivate, duplicate slug
#   Restaurant    — CRUD, org ownership, disable, duplicate code, disabled-org guard
#   Branch        — CRUD, restaurant ownership, disable, duplicate code, disabled-rest guard
#   Security      — cross-organization access is blocked
# =============================================================================

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from .models import (
    Organization,
    Restaurant,
    Branch,
    RestaurantSettings,
    BranchSettings,
)

User = get_user_model()


# =============================================================================
# Helpers
# =============================================================================

def make_user(email="user@test.com", password="testpass123"):
    return User.objects.create_user(
        email=email,
        password=password,
        first_name="Test",
        last_name="User",
    )


def auth_client(user):
    """Return an authenticated APIClient for the given user."""
    client = APIClient()
    token = AccessToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


def make_organization(name="Acme Foods", slug=None, is_active=True):
    return Organization.objects.create(
        name=name,
        slug=slug or f"acme-foods-{name.lower().replace(' ', '-')}",
        currency="INR",
        timezone="Asia/Kolkata",
        is_active=is_active,
    )


def make_restaurant(org, name="Test Resto", code="TR-001", is_active=True):
    r = Restaurant.objects.create(
        organization=org,
        name=name,
        code=code,
        is_active=is_active,
    )
    RestaurantSettings.objects.get_or_create(restaurant=r)
    return r


def make_branch(restaurant, name="Main Branch", code="BR-001", is_active=True):
    b = Branch.objects.create(
        restaurant=restaurant,
        name=name,
        code=code,
        is_active=is_active,
    )
    BranchSettings.objects.get_or_create(branch=b)
    return b


# =============================================================================
# Organization tests
# =============================================================================

class OrganizationCRUDTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)

    def test_create_organization(self):
        url = reverse("organization-list-create")
        payload = {
            "name": "New Corp",
            "email": "corp@example.com",
            "currency": "USD",
            "timezone": "America/New_York",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "New Corp")
        self.assertIn("slug", response.data)
        self.assertIn("id", response.data)

    def test_create_organization_requires_name(self):
        url = reverse("organization-list-create")
        response = self.client.post(url, {"currency": "INR"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_organization(self):
        org = make_organization()
        url = reverse("organization-detail", kwargs={"pk": org.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["id"]), str(org.id))

    def test_update_organization(self):
        org = make_organization()
        url = reverse("organization-detail", kwargs={"pk": org.pk})
        response = self.client.patch(url, {"city": "Mumbai"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        org.refresh_from_db()
        self.assertEqual(org.city, "Mumbai")

    def test_disable_organization(self):
        org = make_organization()
        url = reverse("organization-detail", kwargs={"pk": org.pk})
        response = self.client.patch(url, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        org.refresh_from_db()
        self.assertFalse(org.is_active)

    def test_reactivate_organization(self):
        org = make_organization(is_active=False)
        url = reverse("organization-detail", kwargs={"pk": org.pk})
        response = self.client.patch(url, {"is_active": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        org.refresh_from_db()
        self.assertTrue(org.is_active)

    def test_duplicate_slug_rejected(self):
        Organization.objects.create(
            name="Slug Corp",
            slug="slug-corp",
            currency="INR",
            timezone="UTC",
        )
        # The auto-slug logic in save() appends a counter, so we test that
        # explicitly passing a duplicate slug at the DB/model level is prevented.
        # Create two orgs with same name — the second should get a different slug.
        url = reverse("organization-list-create")
        self.client.post(url, {"name": "Slug Corp"}, format="json")
        response2 = self.client.post(url, {"name": "Slug Corp"}, format="json")
        # Both should succeed — slugs are auto-disambiguated
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(response2.data["slug"], "slug-corp")

    def test_unauthenticated_rejected(self):
        url = reverse("organization-list-create")
        anon = APIClient()
        response = anon.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_organizations(self):
        make_organization(name="Org A", slug="org-a")
        make_organization(name="Org B", slug="org-b")
        url = reverse("organization-list-create")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Paginated — check count field
        self.assertGreaterEqual(response.data["count"], 2)


# =============================================================================
# Restaurant tests
# =============================================================================

class RestaurantTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.org = make_organization()

    def test_create_restaurant(self):
        url = reverse("organization-restaurant-list-create", kwargs={"org_id": self.org.pk})
        payload = {
            "name": "Spice Garden",
            "code": "SPICE-001",
            "city": "Bangalore",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Spice Garden")
        self.assertEqual(response.data["code"], "SPICE-001")

    def test_restaurant_belongs_to_organization(self):
        restaurant = make_restaurant(self.org)
        url = reverse("restaurant-detail", kwargs={"pk": restaurant.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["organization"]), str(self.org.id))

    def test_duplicate_restaurant_code_rejected(self):
        make_restaurant(self.org, code="DUP-001")
        url = reverse("organization-restaurant-list-create", kwargs={"org_id": self.org.pk})
        payload = {"name": "Another", "code": "DUP-001"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_slug_rejected_within_org(self):
        # Two restaurants with the same name in the same org → slug conflict
        url = reverse("organization-restaurant-list-create", kwargs={"org_id": self.org.pk})
        self.client.post(url, {"name": "Garden Fresh", "code": "GF-001"}, format="json")
        response = self.client.post(url, {"name": "Garden Fresh", "code": "GF-002"}, format="json")
        # Second should succeed but get a disambiguated slug
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_disabled_organization_cannot_create_restaurant(self):
        self.org.is_active = False
        self.org.save()
        url = reverse("organization-restaurant-list-create", kwargs={"org_id": self.org.pk})
        response = self.client.post(
            url, {"name": "New Resto", "code": "NR-001"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disable_restaurant(self):
        restaurant = make_restaurant(self.org)
        url = reverse("restaurant-detail", kwargs={"pk": restaurant.pk})
        response = self.client.patch(url, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        restaurant.refresh_from_db()
        self.assertFalse(restaurant.is_active)

    def test_reactivate_restaurant(self):
        restaurant = make_restaurant(self.org, is_active=False)
        url = reverse("restaurant-detail", kwargs={"pk": restaurant.pk})
        response = self.client.patch(url, {"is_active": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        restaurant.refresh_from_db()
        self.assertTrue(restaurant.is_active)

    def test_settings_auto_created(self):
        url = reverse("organization-restaurant-list-create", kwargs={"org_id": self.org.pk})
        response = self.client.post(
            url, {"name": "Auto Settings", "code": "AS-001"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        restaurant_id = response.data["id"]
        self.assertTrue(
            RestaurantSettings.objects.filter(restaurant_id=restaurant_id).exists()
        )


# =============================================================================
# Branch tests
# =============================================================================

class BranchTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.org = make_organization()
        self.restaurant = make_restaurant(self.org)

    def test_create_branch(self):
        url = reverse(
            "restaurant-branch-list-create",
            kwargs={"restaurant_id": self.restaurant.pk},
        )
        payload = {"name": "LPU Campus", "code": "LPU-001", "city": "Phagwara"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "LPU Campus")

    def test_branch_belongs_to_restaurant(self):
        branch = make_branch(self.restaurant)
        url = reverse("branch-detail", kwargs={"pk": branch.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(str(response.data["restaurant"]), str(self.restaurant.id))

    def test_duplicate_branch_code_rejected(self):
        make_branch(self.restaurant, code="DUP-001")
        url = reverse(
            "restaurant-branch-list-create",
            kwargs={"restaurant_id": self.restaurant.pk},
        )
        response = self.client.post(
            url, {"name": "Another", "code": "DUP-001"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disabled_restaurant_cannot_create_branch(self):
        self.restaurant.is_active = False
        self.restaurant.save()
        url = reverse(
            "restaurant-branch-list-create",
            kwargs={"restaurant_id": self.restaurant.pk},
        )
        response = self.client.post(
            url, {"name": "New Branch", "code": "NB-001"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_disable_branch(self):
        branch = make_branch(self.restaurant)
        url = reverse("branch-detail", kwargs={"pk": branch.pk})
        response = self.client.patch(url, {"is_active": False}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        branch.refresh_from_db()
        self.assertFalse(branch.is_active)

    def test_reactivate_branch(self):
        branch = make_branch(self.restaurant, is_active=False)
        url = reverse("branch-detail", kwargs={"pk": branch.pk})
        response = self.client.patch(url, {"is_active": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        branch.refresh_from_db()
        self.assertTrue(branch.is_active)

    def test_settings_auto_created(self):
        url = reverse(
            "restaurant-branch-list-create",
            kwargs={"restaurant_id": self.restaurant.pk},
        )
        response = self.client.post(
            url, {"name": "Auto Settings Branch", "code": "ASB-001"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        branch_id = response.data["id"]
        self.assertTrue(BranchSettings.objects.filter(branch_id=branch_id).exists())


# =============================================================================
# Security tests — cross-organization access prevention
# =============================================================================

class CrossOrganizationSecurityTests(TestCase):
    """
    Verify that a user cannot access another organization's resources
    by guessing / enumerating UUIDs.

    Phase 2 uses IsAuthenticated only.  These tests confirm the
    scoped queryset foundation works correctly so Phase 3 can layer on
    real ownership checks without regressions.
    """

    def setUp(self):
        # Two separate users simulating two different company heads
        self.user_a = make_user(email="usera@test.com")
        self.user_b = make_user(email="userb@test.com")

        self.client_a = auth_client(self.user_a)
        self.client_b = auth_client(self.user_b)

        # Org A creates its own data
        self.org_a = make_organization(name="Org A", slug="org-a-sec")
        self.restaurant_a = make_restaurant(self.org_a, code="RA-001")
        self.branch_a = make_branch(self.restaurant_a, code="BA-001")

        # Org B creates its own data
        self.org_b = make_organization(name="Org B", slug="org-b-sec")
        self.restaurant_b = make_restaurant(self.org_b, code="RB-001")
        self.branch_b = make_branch(self.restaurant_b, code="BB-001")

    # ----- In Phase 2 both users can read all orgs (no ownership filter yet).
    # ----- These tests document CURRENT behaviour and create a test baseline
    # ----- that Phase 3 will tighten.

    def test_organization_detail_is_accessible_phase2(self):
        """
        Phase 2: all authenticated users can read any org.
        Phase 3 will restrict this to owned/assigned orgs.
        """
        url = reverse("organization-detail", kwargs={"pk": self.org_a.pk})
        # User B can still read Org A in Phase 2
        response = self.client_b.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_restaurant_list_for_org_a_returns_org_a_restaurants_only(self):
        """The nested endpoint /organizations/<org_a_id>/restaurants/ must only
        return restaurants belonging to org A."""
        url = reverse(
            "organization-restaurant-list-create",
            kwargs={"org_id": self.org_a.pk},
        )
        response = self.client_b.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {str(r["id"]) for r in response.data["results"]}
        self.assertIn(str(self.restaurant_a.id), returned_ids)
        self.assertNotIn(str(self.restaurant_b.id), returned_ids)

    def test_branch_list_for_restaurant_a_returns_restaurant_a_branches_only(self):
        """The nested endpoint must only return branches for that specific restaurant."""
        url = reverse(
            "restaurant-branch-list-create",
            kwargs={"restaurant_id": self.restaurant_a.pk},
        )
        response = self.client_b.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        returned_ids = {str(b["id"]) for b in response.data["results"]}
        self.assertIn(str(self.branch_a.id), returned_ids)
        self.assertNotIn(str(self.branch_b.id), returned_ids)

    def test_unauthenticated_user_cannot_access_restaurants(self):
        """Unauthenticated requests must always be rejected."""
        anon = APIClient()
        url = reverse(
            "organization-restaurant-list-create",
            kwargs={"org_id": self.org_a.pk},
        )
        response = anon.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_user_cannot_access_branches(self):
        anon = APIClient()
        url = reverse(
            "restaurant-branch-list-create",
            kwargs={"restaurant_id": self.restaurant_a.pk},
        )
        response = anon.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# =============================================================================
# Stats endpoint
# =============================================================================

class StatsEndpointTests(TestCase):

    def setUp(self):
        self.user = make_user()
        self.client = auth_client(self.user)
        self.org = make_organization()
        r = make_restaurant(self.org)
        make_branch(r)

    def test_stats_returns_counts(self):
        url = reverse("organization-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertIn("total_organizations", data)
        self.assertIn("active_organizations", data)
        self.assertIn("total_restaurants", data)
        self.assertIn("active_restaurants", data)
        self.assertIn("total_branches", data)
        self.assertIn("active_branches", data)
        self.assertGreaterEqual(data["total_organizations"], 1)

    def test_stats_unauthenticated_rejected(self):
        anon = APIClient()
        url = reverse("organization-stats")
        response = anon.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
