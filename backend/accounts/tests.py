# =============================================================================
# RestaurantFlow — Accounts Security Tests
# Phase 3
#
# Tests cover:
#   1. Authentication (unauthenticated rejection, valid/invalid login)
#   2. Permission checks (with/without required permission)
#   3. Organization scope (cross-tenant access blocked)
#   4. Restaurant scope (cross-restaurant access blocked)
#   5. Branch scope (cross-branch access blocked)
#   6. Privilege escalation (cashier/manager/owner cannot grant themselves more)
#   7. Role assignment validation (invalid hierarchy rejected)
#   8. User disable / reactivate
# =============================================================================

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import Role, Permission, UserRoleAssignment, UserProfile
from organizations.models import Organization, Restaurant, Branch


# =============================================================================
# Test helpers
# =============================================================================

def make_user(email, password="TestPass@1", **kwargs):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.create_user(email=email, password=password, **kwargs)
    UserProfile.objects.get_or_create(user=user)
    return user


def make_org(name="Test Org", slug=None):
    from django.utils.text import slugify
    return Organization.objects.create(
        name=name,
        slug=slug or slugify(name) + "-test",
        currency="INR",
        timezone="Asia/Kolkata",
    )


def make_restaurant(org, name="Test Restaurant", code="TEST-001"):
    return Restaurant.objects.create(
        organization=org,
        name=name,
        code=code,
    )


def make_branch(restaurant, name="Test Branch", code="TB-001"):
    return Branch.objects.create(
        restaurant=restaurant,
        name=name,
        code=code,
    )


def get_or_create_role(code):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={
            "name": code,
            "scope": _role_scope(code),
            "is_system_role": True,
            "is_active": True,
        },
    )
    return role


def _role_scope(code):
    ORG_ROLES = {Role.CODE_COMPANY_HEAD, Role.CODE_CENTRAL_ADMIN}
    REST_ROLES = {Role.CODE_RESTAURANT_OWNER}
    if code in ORG_ROLES:
        return Role.SCOPE_ORGANIZATION
    if code in REST_ROLES:
        return Role.SCOPE_RESTAURANT
    return Role.SCOPE_BRANCH


def assign_role(user, role_code, org=None, restaurant=None, branch=None):
    role = get_or_create_role(role_code)
    assignment = UserRoleAssignment(
        user=user, role=role,
        organization=org, restaurant=restaurant, branch=branch,
        is_active=True,
    )
    assignment.full_clean()
    assignment.save()
    return assignment


def get_or_create_permission(code, module="test", action="view"):
    perm, _ = Permission.objects.get_or_create(
        code=code,
        defaults={"name": code, "module": module, "action": action, "is_active": True},
    )
    return perm


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# =============================================================================
# 1. Authentication tests
# =============================================================================

class AuthenticationTests(TestCase):

    def setUp(self):
        self.user = make_user("auth@test.dev", password="GoodPass@1")
        self.client = APIClient()

    def test_unauthenticated_me_rejected(self):
        resp = self.client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_login_returns_tokens(self):
        resp = self.client.post("/api/auth/login/", {
            "email": "auth@test.dev",
            "password": "GoodPass@1",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_invalid_login_rejected(self):
        resp = self.client.post("/api/auth/login/", {
            "email": "auth@test.dev",
            "password": "WrongPassword",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_me_returns_user(self):
        client = auth_client(self.user)
        resp = client.get("/api/auth/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["email"], self.user.email)

    def test_password_not_in_me_response(self):
        client = auth_client(self.user)
        resp = client.get("/api/auth/me/")
        resp_str = str(resp.data)
        self.assertNotIn("password", resp_str)
        self.assertNotIn("password_hash", resp_str)

    def test_register_creates_user(self):
        resp = self.client.post("/api/auth/register/", {
            "email": "new@test.dev",
            "first_name": "New",
            "last_name": "User",
            "password": "NewPass@123",
            "password_confirm": "NewPass@123",
        })
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_register_rejects_mismatched_passwords(self):
        resp = self.client.post("/api/auth/register/", {
            "email": "new2@test.dev",
            "first_name": "New",
            "last_name": "User",
            "password": "NewPass@123",
            "password_confirm": "DifferentPass@123",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# 2. Permission checks
# =============================================================================

class PermissionCheckTests(TestCase):

    def setUp(self):
        # Org A
        self.org_a = make_org("Org A", slug="org-a-test")
        self.rest_a = make_restaurant(self.org_a, code="A-001")

        # User with COMPANY_HEAD role (has all org permissions)
        self.head = make_user("head@test.dev")
        assign_role(self.head, Role.CODE_COMPANY_HEAD, org=self.org_a)

        # Give the role the user.view permission (needed for /api/users/)
        role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        perm = get_or_create_permission("user.view", module="user", action="view")
        role.permissions.add(perm)

        # Regular user with no role
        self.plain_user = make_user("plain@test.dev")

    def test_user_with_permission_can_access_user_list(self):
        client = auth_client(self.head)
        resp = client.get("/api/users/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_user_without_permission_denied_user_list(self):
        client = auth_client(self.plain_user)
        resp = client.get("/api/users/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_denied_user_list(self):
        resp = self.client.get("/api/users/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_list_requires_role_view_permission(self):
        client = auth_client(self.plain_user)
        resp = client.get("/api/roles/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission_list_requires_permission_view(self):
        client = auth_client(self.plain_user)
        resp = client.get("/api/permissions/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# =============================================================================
# 3. Organization scope — cross-tenant access blocked
# =============================================================================

class OrganizationScopeTests(TestCase):

    def setUp(self):
        # Two completely separate organizations
        self.org_a = make_org("Org A", slug="scope-org-a")
        self.org_b = make_org("Org B", slug="scope-org-b")
        self.rest_a = make_restaurant(self.org_a, name="Rest A", code="RA-001")
        self.rest_b = make_restaurant(self.org_b, name="Rest B", code="RB-001")

        # User belonging only to Org A
        self.user_a = make_user("user_a@test.dev")
        assign_role(self.user_a, Role.CODE_COMPANY_HEAD, org=self.org_a)

    def test_org_a_user_can_access_org_a(self):
        client = auth_client(self.user_a)
        resp = client.get(f"/api/organizations/{self.org_a.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_org_a_user_cannot_access_org_b(self):
        client = auth_client(self.user_a)
        resp = client.get(f"/api/organizations/{self.org_b.pk}/")
        # Must return 404, not 200 or 403 — no existence leakage
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_org_a_user_sees_only_org_a_in_list(self):
        client = auth_client(self.user_a)
        resp = client.get("/api/organizations/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [o["id"] for o in resp.data["results"]]
        self.assertIn(str(self.org_a.pk), ids)
        self.assertNotIn(str(self.org_b.pk), ids)

    def test_org_a_user_cannot_patch_org_b(self):
        client = auth_client(self.user_a)
        # Give user the organization.update permission
        role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        perm = get_or_create_permission("organization.update", module="organization", action="update")
        role.permissions.add(perm)
        resp = client.patch(f"/api/organizations/{self.org_b.pk}/", {"name": "Hacked"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 4. Restaurant scope
# =============================================================================

class RestaurantScopeTests(TestCase):

    def setUp(self):
        self.org = make_org("Shared Org", slug="shared-org-test")
        self.rest_a = make_restaurant(self.org, name="Restaurant A", code="RSA-001")
        self.rest_b = make_restaurant(self.org, name="Restaurant B", code="RSB-001")

        # Owner of restaurant A only
        self.owner_a = make_user("owner_a@test.dev")
        assign_role(
            self.owner_a, Role.CODE_RESTAURANT_OWNER,
            org=self.org, restaurant=self.rest_a,
        )

    def test_owner_a_can_see_restaurant_a(self):
        client = auth_client(self.owner_a)
        resp = client.get(f"/api/restaurants/{self.rest_a.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_owner_a_cannot_see_restaurant_b(self):
        client = auth_client(self.owner_a)
        resp = client.get(f"/api/restaurants/{self.rest_b.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_owner_a_list_excludes_restaurant_b(self):
        client = auth_client(self.owner_a)
        resp = client.get("/api/restaurants/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(str(self.rest_a.pk), ids)
        self.assertNotIn(str(self.rest_b.pk), ids)

    def test_owner_a_cannot_patch_restaurant_b(self):
        client = auth_client(self.owner_a)
        role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        perm = get_or_create_permission("restaurant.update", module="restaurant", action="update")
        role.permissions.add(perm)
        resp = client.patch(f"/api/restaurants/{self.rest_b.pk}/", {"name": "Hacked"})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# 5. Branch scope
# =============================================================================

class BranchScopeTests(TestCase):

    def setUp(self):
        self.org = make_org("Branch Org", slug="branch-org-test")
        self.restaurant = make_restaurant(self.org, code="BREST-001")
        self.branch_a = make_branch(self.restaurant, name="Branch A", code="BA-001")
        self.branch_b = make_branch(self.restaurant, name="Branch B", code="BB-001")

        # Manager assigned only to branch A
        self.manager_a = make_user("manager_a@test.dev")
        assign_role(
            self.manager_a, Role.CODE_RESTAURANT_MANAGER,
            org=self.org, restaurant=self.restaurant, branch=self.branch_a,
        )

    def test_manager_a_can_see_branch_a(self):
        client = auth_client(self.manager_a)
        resp = client.get(f"/api/branches/{self.branch_a.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_manager_a_cannot_see_branch_b(self):
        client = auth_client(self.manager_a)
        resp = client.get(f"/api/branches/{self.branch_b.pk}/")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_manager_a_list_excludes_branch_b(self):
        client = auth_client(self.manager_a)
        resp = client.get("/api/branches/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        ids = [b["id"] for b in resp.data["results"]]
        self.assertIn(str(self.branch_a.pk), ids)
        self.assertNotIn(str(self.branch_b.pk), ids)


# =============================================================================
# 6. Privilege escalation prevention
# =============================================================================

class PrivilegeEscalationTests(TestCase):

    def setUp(self):
        self.org = make_org("Escalation Org", slug="esc-org-test")
        self.restaurant = make_restaurant(self.org, code="ESC-001")
        self.branch = make_branch(self.restaurant, code="ESC-BR-001")

        # A cashier user
        self.cashier = make_user("cashier@test.dev")
        assign_role(
            self.cashier, Role.CODE_CASHIER,
            org=self.org, restaurant=self.restaurant, branch=self.branch,
        )

        # A manager
        self.manager = make_user("manager@test.dev")
        assign_role(
            self.manager, Role.CODE_RESTAURANT_MANAGER,
            org=self.org, restaurant=self.restaurant, branch=self.branch,
        )

        # A target user to try assigning roles to — must be in same scope so the view
        # can find them (otherwise 404 before the escalation check fires)
        self.target = make_user("target@test.dev")
        assign_role(
            self.target, Role.CODE_WAITER,
            org=self.org, restaurant=self.restaurant, branch=self.branch,
        )

        # Give role.manage permission to cashier/manager (they need it to
        # reach the endpoint, but the service still blocks escalation)
        role_manage_perm = get_or_create_permission("role.manage", module="role", action="manage")
        cashier_role = get_or_create_role(Role.CODE_CASHIER)
        cashier_role.permissions.add(role_manage_perm)
        manager_role = get_or_create_role(Role.CODE_RESTAURANT_MANAGER)
        manager_role.permissions.add(role_manage_perm)

    def test_cashier_cannot_assign_company_head(self):
        company_head_role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        client = auth_client(self.cashier)
        resp = client.post(f"/api/users/{self.target.pk}/roles/", {
            "role": str(company_head_role.pk),
            "organization": str(self.org.pk),
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_manager_cannot_assign_company_head(self):
        company_head_role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        client = auth_client(self.manager)
        resp = client.post(f"/api/users/{self.target.pk}/roles/", {
            "role": str(company_head_role.pk),
            "organization": str(self.org.pk),
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_cashier_cannot_create_users(self):
        # Cashier has no user.create permission
        client = auth_client(self.cashier)
        resp = client.post("/api/users/", {
            "email": "newuser@test.dev",
            "first_name": "New",
            "last_name": "User",
            "password": "NewPass@123",
        })
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_is_superuser_cannot_be_set_via_register(self):
        client = APIClient()
        resp = client.post("/api/auth/register/", {
            "email": "hacker@test.dev",
            "first_name": "Hacker",
            "last_name": "User",
            "password": "Hack@1234",
            "password_confirm": "Hack@1234",
            "is_superuser": True,
            "is_staff": True,
        })
        # Should succeed (registration is allowed) but superuser must not be set
        if resp.status_code == status.HTTP_201_CREATED:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(email="hacker@test.dev")
            self.assertFalse(user.is_superuser)
            self.assertFalse(user.is_staff)


# =============================================================================
# 7. Role assignment scope validation
# =============================================================================

class RoleAssignmentValidationTests(TestCase):

    def setUp(self):
        self.org_a = make_org("Val Org A", slug="val-org-a")
        self.org_b = make_org("Val Org B", slug="val-org-b")
        self.rest_a = make_restaurant(self.org_a, name="Val Rest A", code="VRA-001")
        self.rest_b = make_restaurant(self.org_b, name="Val Rest B", code="VRB-001")
        self.branch_a = make_branch(self.rest_a, name="Val Branch A", code="VBA-001")
        self.branch_b = make_branch(self.rest_b, name="Val Branch B", code="VBB-001")

    def test_branch_must_belong_to_restaurant(self):
        """branch_b is under rest_b — cannot assign with rest_a."""
        role = get_or_create_role(Role.CODE_RESTAURANT_MANAGER)
        user = make_user("bad_assign@test.dev")

        assignment = UserRoleAssignment(
            user=user, role=role,
            organization=self.org_a, restaurant=self.rest_a, branch=self.branch_b,
        )
        from django.core.exceptions import ValidationError as DjangoValidationError
        with self.assertRaises(DjangoValidationError):
            assignment.full_clean()

    def test_restaurant_must_belong_to_organization(self):
        """rest_b is under org_b — cannot assign with org_a."""
        role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        user = make_user("bad_assign2@test.dev")

        assignment = UserRoleAssignment(
            user=user, role=role,
            organization=self.org_a, restaurant=self.rest_b,
        )
        from django.core.exceptions import ValidationError as DjangoValidationError
        with self.assertRaises(DjangoValidationError):
            assignment.full_clean()

    def test_organization_scope_role_cannot_have_restaurant(self):
        """COMPANY_HEAD is organization-scoped — restaurant must be null."""
        role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        user = make_user("bad_assign3@test.dev")

        assignment = UserRoleAssignment(
            user=user, role=role,
            organization=self.org_a, restaurant=self.rest_a,
        )
        from django.core.exceptions import ValidationError as DjangoValidationError
        with self.assertRaises(DjangoValidationError):
            assignment.full_clean()

    def test_restaurant_scope_role_cannot_have_branch(self):
        """RESTAURANT_OWNER is restaurant-scoped — branch must be null."""
        role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        user = make_user("bad_assign4@test.dev")

        assignment = UserRoleAssignment(
            user=user, role=role,
            organization=self.org_a, restaurant=self.rest_a, branch=self.branch_a,
        )
        from django.core.exceptions import ValidationError as DjangoValidationError
        with self.assertRaises(DjangoValidationError):
            assignment.full_clean()

    def test_valid_branch_assignment_succeeds(self):
        role = get_or_create_role(Role.CODE_CASHIER)
        user = make_user("good_assign@test.dev")
        # Should not raise
        assignment = UserRoleAssignment(
            user=user, role=role,
            organization=self.org_a, restaurant=self.rest_a, branch=self.branch_a,
            is_active=True,
        )
        assignment.full_clean()
        assignment.save()
        self.assertTrue(UserRoleAssignment.objects.filter(pk=assignment.pk).exists())


# =============================================================================
# 8. User disable / reactivate
# =============================================================================

class UserStatusTests(TestCase):

    def setUp(self):
        self.org = make_org("Status Org", slug="status-org-test")

        # Head user who can manage others
        self.head = make_user("head_status@test.dev")
        assign_role(self.head, Role.CODE_COMPANY_HEAD, org=self.org)
        role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        for code, module, action in [
            ("user.view", "user", "view"),
            ("user.disable", "user", "disable"),
        ]:
            perm = get_or_create_permission(code, module=module, action=action)
            role.permissions.add(perm)

        # Target user in same org — simple manager-level assignment for testing disable/reactivate
        self.target = make_user("target_status@test.dev")
        # Assign as manager (branch-scoped role) with valid scope chain
        self.status_restaurant = make_restaurant(self.org, code="SR-001")
        self.status_branch = make_branch(self.status_restaurant, code="SB-001")
        assign_role(
            self.target, Role.CODE_RESTAURANT_MANAGER,
            org=self.org,
            restaurant=self.status_restaurant,
            branch=self.status_branch,
        )

    def test_head_can_disable_target(self):
        client = auth_client(self.head)
        resp = client.post(f"/api/users/{self.target.pk}/disable/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)

    def test_head_can_reactivate_target(self):
        self.target.is_active = False
        self.target.save()
        client = auth_client(self.head)
        resp = client.post(f"/api/users/{self.target.pk}/reactivate/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

    def test_user_cannot_disable_self(self):
        client = auth_client(self.head)
        resp = client.post(f"/api/users/{self.head.pk}/disable/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_plain_user_cannot_disable_others(self):
        plain = make_user("plain_status@test.dev")
        client = auth_client(plain)
        resp = client.post(f"/api/users/{self.target.pk}/disable/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
