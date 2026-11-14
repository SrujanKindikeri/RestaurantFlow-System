# =============================================================================
# RestaurantFlow — Organization Creation Permission Regression Tests
#
# Regression for: POST /api/organizations/ returning 403 when
# organization.create permission was not seeded in the DB.
#
# Run:
#   python manage.py test organizations.tests_permission_regression --verbosity=2
#
# Coverage:
#   - POST /api/organizations/ returns 201 for a user with organization.create
#   - POST /api/organizations/ returns 403 for a user without organization.create
#   - Created organization is saved in the database
#   - GET /api/organizations/ returns 200 and includes the created org
#   - GET /api/organizations/stats/ returns 200 with updated counts
# =============================================================================

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import Permission, Role, UserRoleAssignment
from organizations.models import Organization

User = get_user_model()

ORG_PAYLOAD = {
    "name": "Regression Test Org",
    "legal_name": "Regression Test Org Ltd",
    "email": "regression@example.com",
    "phone": "+1234567890",
    "address": "123 Main St",
    "city": "Test City",
    "state": "TS",
    "country": "US",
    "postal_code": "12345",
    "tax_id": "TAX123",
    "currency": "USD",
    "timezone": "UTC",
}


def _make_user(email, password="testpass123"):
    return User.objects.create_user(
        email=email, password=password, first_name="Test", last_name="User"
    )


def _auth_client(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
    return client


def _seed_permission_and_role():
    """Create the organization.create permission and a role that holds it."""
    perm, _ = Permission.objects.get_or_create(
        code="organization.create",
        defaults={
            "name": "Create Organization",
            "module": "organization",
            "action": "create",
            "is_active": True,
        },
    )
    role, _ = Role.objects.get_or_create(
        code="COMPANY_HEAD",
        defaults={
            "name": "Company Head",
            "scope": Role.SCOPE_ORGANIZATION,
            "is_system_role": True,
            "is_active": True,
        },
    )
    role.permissions.add(perm)
    return perm, role


class OrganizationCreatePermissionTests(TestCase):
    """
    Regression: POST /api/organizations/ must return 201 for authorized users
    and 403 for users lacking organization.create.
    """

    def setUp(self):
        self.perm, self.role = _seed_permission_and_role()

        # Authorized user: has COMPANY_HEAD role with organization.create
        self.authorized_user = _make_user("authorized@test.com")
        self.demo_org = Organization.objects.create(
            name="Demo Org",
            slug="demo-org-perm-test",
            currency="USD",
            timezone="UTC",
        )
        UserRoleAssignment.objects.create(
            user=self.authorized_user,
            role=self.role,
            organization=self.demo_org,
            is_active=True,
        )
        self.authorized_client = _auth_client(self.authorized_user)

        # Unauthorized user: no role assignment, no permissions
        self.unauthorized_user = _make_user("unauthorized@test.com")
        self.unauthorized_client = _auth_client(self.unauthorized_user)

    # ------------------------------------------------------------------
    # Core 403 regression
    # ------------------------------------------------------------------

    def test_authorized_user_can_create_organization(self):
        """User with organization.create permission receives 201."""
        url = reverse("organization-list-create")
        response = self.authorized_client.post(url, ORG_PAYLOAD, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            msg=f"Expected 201, got {response.status_code}: {response.data}",
        )
        self.assertEqual(response.data["name"], "Regression Test Org")
        self.assertIn("id", response.data)
        self.assertIn("slug", response.data)

    def test_unauthorized_user_cannot_create_organization(self):
        """User without organization.create permission receives 403."""
        url = reverse("organization-list-create")
        response = self.unauthorized_client.post(url, ORG_PAYLOAD, format="json")
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            msg=f"Expected 403, got {response.status_code}: {response.data}",
        )

    def test_unauthenticated_request_is_rejected(self):
        """Unauthenticated POST receives 401."""
        url = reverse("organization-list-create")
        anon = APIClient()
        response = anon.post(url, ORG_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    def test_created_organization_is_saved_in_database(self):
        """After a successful 201, the organization exists in the database."""
        url = reverse("organization-list-create")
        response = self.authorized_client.post(url, ORG_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        org_id = response.data["id"]
        self.assertTrue(
            Organization.objects.filter(pk=org_id).exists(),
            msg=f"Organization {org_id} not found in database after 201.",
        )
        org = Organization.objects.get(pk=org_id)
        self.assertEqual(org.name, "Regression Test Org")
        self.assertEqual(org.currency, "USD")
        self.assertTrue(org.is_active)

    # ------------------------------------------------------------------
    # GET list includes created org
    # ------------------------------------------------------------------

    def test_created_org_appears_in_list(self):
        """After creation, a staff/superuser GET includes the new org in the unscoped list."""
        # Create the org as the authorized user
        create_url = reverse("organization-list-create")
        create_response = self.authorized_client.post(create_url, ORG_PAYLOAD, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        new_org_id = str(create_response.data["id"])

        # Verify it exists in the DB regardless of scope
        self.assertTrue(Organization.objects.filter(pk=new_org_id).exists())

        # A staff user can see all organizations
        staff_user = _make_user("staff_list@test.com")
        staff_user.is_staff = True
        staff_user.save()
        staff_client = _auth_client(staff_user)

        list_url = reverse("organization-list-create")
        list_response = staff_client.get(list_url)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        returned_ids = {str(o["id"]) for o in list_response.data.get("results", [])}
        self.assertIn(new_org_id, returned_ids)

    # ------------------------------------------------------------------
    # Stats update
    # ------------------------------------------------------------------

    def test_stats_reflect_created_org(self):
        """After creation, a staff user sees the updated count in stats."""
        # Staff user sees all orgs (unscoped)
        staff_user = _make_user("staff_stats@test.com")
        staff_user.is_staff = True
        staff_user.save()
        staff_client = _auth_client(staff_user)

        stats_url = reverse("organization-stats")
        before = staff_client.get(stats_url)
        self.assertEqual(before.status_code, status.HTTP_200_OK)
        count_before = before.data["total_organizations"]

        create_url = reverse("organization-list-create")
        self.authorized_client.post(create_url, ORG_PAYLOAD, format="json")

        after = staff_client.get(stats_url)
        self.assertEqual(after.status_code, status.HTTP_200_OK)
        self.assertEqual(after.data["total_organizations"], count_before + 1)

    # ------------------------------------------------------------------
    # Permission code presence
    # ------------------------------------------------------------------

    def test_organization_create_permission_exists_in_db(self):
        """The organization.create Permission row must exist and be active."""
        perm = Permission.objects.filter(code="organization.create").first()
        self.assertIsNotNone(perm, "organization.create permission not found in DB.")
        self.assertTrue(perm.is_active)

    def test_company_head_role_has_organization_create(self):
        """The COMPANY_HEAD role must have organization.create in its permissions M2M."""
        role = Role.objects.filter(code="COMPANY_HEAD").first()
        self.assertIsNotNone(role, "COMPANY_HEAD role not found in DB.")
        self.assertTrue(
            role.permissions.filter(code="organization.create").exists(),
            "COMPANY_HEAD role does not have organization.create permission.",
        )

    def test_inactive_role_assignment_does_not_grant_access(self):
        """An inactive UserRoleAssignment must not grant organization.create."""
        # Create user with inactive assignment
        user = _make_user("inactive_assign@test.com")
        UserRoleAssignment.objects.create(
            user=user,
            role=self.role,
            organization=self.demo_org,
            is_active=False,  # Inactive
        )
        client = _auth_client(user)
        url = reverse("organization-list-create")
        response = client.post(url, ORG_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_role_does_not_grant_access(self):
        """A role with is_active=False must not grant permissions even if assigned."""
        inactive_role = Role.objects.create(
            name="Inactive Role",
            code="INACTIVE_TEST_ROLE",
            scope=Role.SCOPE_ORGANIZATION,
            is_active=False,
        )
        inactive_role.permissions.add(self.perm)

        user = _make_user("inactive_role@test.com")
        UserRoleAssignment.objects.create(
            user=user,
            role=inactive_role,
            organization=self.demo_org,
            is_active=True,
        )
        client = _auth_client(user)
        url = reverse("organization-list-create")
        response = client.post(url, ORG_PAYLOAD, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
