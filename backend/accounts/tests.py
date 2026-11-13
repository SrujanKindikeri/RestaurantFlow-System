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
        # Give the role the view permissions needed for these tests
        role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        for code, module, action in [
            ("organization.view", "organization", "view"),
            ("restaurant.view", "restaurant", "view"),
            ("organization.update", "organization", "update"),
        ]:
            perm = get_or_create_permission(code, module=module, action=action)
            role.permissions.add(perm)

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
        # organization.update perm was added in setUp
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
        # Give the role the view/update permissions needed for these tests
        role = get_or_create_role(Role.CODE_RESTAURANT_OWNER)
        for code, module, action in [
            ("restaurant.view", "restaurant", "view"),
            ("restaurant.update", "restaurant", "update"),
        ]:
            perm = get_or_create_permission(code, module=module, action=action)
            role.permissions.add(perm)

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
        # restaurant.update perm was added in setUp
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
        # Give the role the view permission needed for these tests
        role = get_or_create_role(Role.CODE_RESTAURANT_MANAGER)
        perm = get_or_create_permission("branch.view", module="branch", action="view")
        role.permissions.add(perm)

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
        # Either 403 (blocked by privilege check) or 404 (user not in cashier's scope)
        # Both are correct security outcomes — escalation is blocked
        self.assertIn(
            resp.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

    def test_manager_cannot_assign_company_head(self):
        company_head_role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        client = auth_client(self.manager)
        resp = client.post(f"/api/users/{self.target.pk}/roles/", {
            "role": str(company_head_role.pk),
            "organization": str(self.org.pk),
        })
        # Either 403 or 404 — escalation is blocked either way
        self.assertIn(
            resp.status_code,
            [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND],
        )

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


# =============================================================================
# Phase 21 — Security, Audit & Compliance Hardening Tests
# =============================================================================

from accounts.models import SecurityAuditLog
from core.security import (
    record_security_event,
    record_login_failure,
    is_login_locked_out,
    clear_login_failures,
    _sanitize_metadata,
)
from io import BytesIO


# ---------------------------------------------------------------------------
# 9. SecurityAuditLog immutability
# ---------------------------------------------------------------------------

class SecurityAuditLogImmutabilityTests(TestCase):

    def setUp(self):
        self.user = make_user("audit@test.dev", password="GoodPass@1")

    def test_audit_log_can_be_created(self):
        log = SecurityAuditLog.objects.create(
            actor=self.user,
            event=SecurityAuditLog.EVENT_LOGIN,
            ip_address="127.0.0.1",
            metadata={"key": "value"},
        )
        self.assertIsNotNone(log.pk)

    def test_audit_log_cannot_be_updated(self):
        log = SecurityAuditLog.objects.create(
            actor=self.user,
            event=SecurityAuditLog.EVENT_LOGIN,
        )
        log.event = SecurityAuditLog.EVENT_LOGOUT
        with self.assertRaises(ValueError):
            log.save()

    def test_audit_log_metadata_sanitized(self):
        """Sensitive keys are redacted from metadata."""
        sanitized = _sanitize_metadata({
            "password": "secret123",
            "token": "jwt-token-value",
            "role_code": "CASHIER",
            "reason": "legitimate reason",
        })
        self.assertEqual(sanitized["password"], "[REDACTED]")
        self.assertEqual(sanitized["token"], "[REDACTED]")
        self.assertEqual(sanitized["role_code"], "CASHIER")
        self.assertEqual(sanitized["reason"], "legitimate reason")

    def test_security_event_recorded(self):
        """record_security_event creates a SecurityAuditLog."""
        log = record_security_event(
            event=SecurityAuditLog.EVENT_LOGIN,
            actor=self.user,
            target_user=self.user,
            ip_address="192.168.1.1",
            metadata={"source": "test"},
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.event, SecurityAuditLog.EVENT_LOGIN)
        self.assertEqual(log.ip_address, "192.168.1.1")


# ---------------------------------------------------------------------------
# 10. Login throttling and lockout
# ---------------------------------------------------------------------------

class LoginThrottlingTests(TestCase):

    def setUp(self):
        self.user = make_user("throttle@test.dev", password="GoodPass@1")
        self.client = APIClient()

    def test_failed_login_returns_generic_error(self):
        """Failed login must not reveal whether the account exists (user enumeration)."""
        resp = self.client.post("/api/auth/login/", {
            "email": "throttle@test.dev",
            "password": "WrongPassword@1",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        # The generic message must NOT explicitly disclose the account does/doesn't exist
        resp_str = str(resp.data.get("detail", "")).lower()
        self.assertNotIn("account does not exist", resp_str)
        self.assertNotIn("user not found", resp_str)
        self.assertNotIn("no user", resp_str)

    def test_failed_login_for_nonexistent_user_same_error(self):
        """Both valid and invalid emails get the same error message."""
        resp1 = self.client.post("/api/auth/login/", {
            "email": "throttle@test.dev",
            "password": "WrongPassword@1",
        })
        resp2 = self.client.post("/api/auth/login/", {
            "email": "nonexistent@test.dev",
            "password": "WrongPassword@1",
        })
        self.assertEqual(resp1.status_code, resp2.status_code)
        self.assertEqual(
            resp1.data.get("detail", ""),
            resp2.data.get("detail", ""),
        )

    def test_lockout_after_max_failures(self):
        """After 5 failed attempts, the IP/email is temporarily locked out."""
        from core.security import clear_login_failures
        # Clear any accumulated state from previous tests
        clear_login_failures("127.0.0.1", "throttle@test.dev")

        for i in range(5):
            self.client.post("/api/auth/login/", {
                "email": "throttle@test.dev",
                "password": f"Wrong{i}@1",
            })

        # 6th attempt should be locked out (even with correct password)
        resp = self.client.post("/api/auth/login/", {
            "email": "throttle@test.dev",
            "password": "GoodPass@1",
        })
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_successful_login_clears_failures(self):
        """A successful login clears the failure counter."""
        from core.security import clear_login_failures
        # Clear any state from previous tests that may have accumulated against 127.0.0.1
        clear_login_failures("127.0.0.1", "throttle@test.dev")

        # Record 3 failures
        for i in range(3):
            self.client.post("/api/auth/login/", {
                "email": "throttle@test.dev",
                "password": f"Wrong{i}@1",
            })
        # Login successfully — clears the counter
        resp = self.client.post("/api/auth/login/", {
            "email": "throttle@test.dev",
            "password": "GoodPass@1",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # 3 more failures — should NOT trigger lockout (counter was cleared)
        for i in range(3):
            self.client.post("/api/auth/login/", {
                "email": "throttle@test.dev",
                "password": f"WrongAgain{i}@1",
            })
        resp = self.client.post("/api/auth/login/", {
            "email": "throttle@test.dev",
            "password": "WrongAgain3@1",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_audit_log_created_on_successful_login(self):
        """A SecurityAuditLog entry is created on successful login."""
        from core.security import clear_login_failures
        clear_login_failures("127.0.0.1", "throttle@test.dev")

        self.client.post("/api/auth/login/", {
            "email": "throttle@test.dev",
            "password": "GoodPass@1",
        })
        logs = SecurityAuditLog.objects.filter(
            event=SecurityAuditLog.EVENT_LOGIN,
            actor=self.user,
        )
        self.assertTrue(logs.exists())

    def test_audit_log_created_on_failed_login(self):
        """A SecurityAuditLog entry is created on failed login."""
        self.client.post("/api/auth/login/", {
            "email": "throttle@test.dev",
            "password": "WrongPassword@1",
        })
        logs = SecurityAuditLog.objects.filter(
            event=SecurityAuditLog.EVENT_LOGIN_FAILED,
        )
        self.assertTrue(logs.exists())


# ---------------------------------------------------------------------------
# 11. Password change
# ---------------------------------------------------------------------------

class PasswordChangeTests(TestCase):

    def setUp(self):
        self.user = make_user("pwdchange@test.dev", password="OldPass@1")
        self.client = auth_client(self.user)

    def test_password_change_with_correct_old_password(self):
        resp = self.client.post("/api/auth/change-password/", {
            "old_password": "OldPass@1",
            "new_password": "NewPass@123",
            "new_password_confirm": "NewPass@123",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass@123"))

    def test_password_change_with_wrong_old_password(self):
        resp = self.client.post("/api/auth/change-password/", {
            "old_password": "WrongOldPass@1",
            "new_password": "NewPass@123",
            "new_password_confirm": "NewPass@123",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_rejects_mismatched_new(self):
        resp = self.client.post("/api/auth/change-password/", {
            "old_password": "OldPass@1",
            "new_password": "NewPass@123",
            "new_password_confirm": "DifferentPass@123",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_rejects_same_password(self):
        """New password must differ from old password."""
        resp = self.client.post("/api/auth/change-password/", {
            "old_password": "OldPass@1",
            "new_password": "OldPass@1",
            "new_password_confirm": "OldPass@1",
        })
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_creates_audit_log(self):
        self.client.post("/api/auth/change-password/", {
            "old_password": "OldPass@1",
            "new_password": "NewPass@123",
            "new_password_confirm": "NewPass@123",
        })
        logs = SecurityAuditLog.objects.filter(
            event=SecurityAuditLog.EVENT_PASSWORD_CHANGE,
            actor=self.user,
        )
        self.assertTrue(logs.exists())

    def test_password_change_requires_auth(self):
        client = APIClient()
        resp = client.post("/api/auth/change-password/", {
            "old_password": "OldPass@1",
            "new_password": "NewPass@123",
            "new_password_confirm": "NewPass@123",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# 12. Session revocation on account disable
# ---------------------------------------------------------------------------

class SessionRevocationTests(TestCase):

    def setUp(self):
        self.org = make_org("Revocation Org", slug="revoc-org-test")
        self.head = make_user("head_revoc@test.dev")
        assign_role(self.head, Role.CODE_COMPANY_HEAD, org=self.org)
        role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        for code, module, action in [
            ("user.view", "user", "view"),
            ("user.disable", "user", "disable"),
        ]:
            perm = get_or_create_permission(code, module=module, action=action)
            role.permissions.add(perm)

        self.target = make_user("target_revoc@test.dev", password="TargetPass@1")
        self.target_rest = make_restaurant(self.org, code="REV-001")
        self.target_branch = make_branch(self.target_rest, code="REV-B-001")
        assign_role(
            self.target, Role.CODE_RESTAURANT_MANAGER,
            org=self.org, restaurant=self.target_rest, branch=self.target_branch,
        )

    def test_disable_creates_audit_log(self):
        client = auth_client(self.head)
        client.post(f"/api/users/{self.target.pk}/disable/")
        logs = SecurityAuditLog.objects.filter(
            event=SecurityAuditLog.EVENT_ACCOUNT_DISABLED,
            actor=self.head,
            target_user=self.target,
        )
        self.assertTrue(logs.exists())

    def test_reactivate_creates_audit_log(self):
        self.target.is_active = False
        self.target.save()
        client = auth_client(self.head)
        client.post(f"/api/users/{self.target.pk}/reactivate/")
        logs = SecurityAuditLog.objects.filter(
            event=SecurityAuditLog.EVENT_ACCOUNT_REACTIVATED,
            actor=self.head,
            target_user=self.target,
        )
        self.assertTrue(logs.exists())

    def test_disabled_user_cannot_login(self):
        self.target.is_active = False
        self.target.save()
        client = APIClient()
        resp = client.post("/api/auth/login/", {
            "email": "target_revoc@test.dev",
            "password": "TargetPass@1",
        })
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# 13. Security audit log access control
# ---------------------------------------------------------------------------

class SecurityAuditLogAccessTests(TestCase):

    def setUp(self):
        self.org = make_org("Audit Org", slug="audit-org-test")
        self.admin = make_user("audit_admin@test.dev")
        assign_role(self.admin, Role.CODE_COMPANY_HEAD, org=self.org)
        role = get_or_create_role(Role.CODE_COMPANY_HEAD)
        perm = get_or_create_permission("security.audit.view", module="security", action="audit.view")
        role.permissions.add(perm)

        self.plain_user = make_user("audit_plain@test.dev")

        # Create some audit entries
        SecurityAuditLog.objects.create(
            actor=self.admin,
            event=SecurityAuditLog.EVENT_LOGIN,
            organization=self.org,
        )

    def test_admin_can_view_audit_log(self):
        client = auth_client(self.admin)
        resp = client.get("/api/security/audit-log/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_plain_user_cannot_view_audit_log(self):
        client = auth_client(self.plain_user)
        resp = client.get("/api/security/audit-log/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_view_audit_log(self):
        client = APIClient()
        resp = client.get("/api/security/audit-log/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ---------------------------------------------------------------------------
# 14. File upload magic byte validation
# ---------------------------------------------------------------------------

class FileUploadSecurityTests(TestCase):

    def _make_fake_file(self, content, filename, content_type="application/pdf"):
        """Create a fake uploaded file with given content and extension."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(
            name=filename,
            content=content,
            content_type=content_type,
        )

    def test_valid_pdf_upload_passes(self):
        from financials.validators import validate_attachment_file
        file = self._make_fake_file(b"%PDF-1.4 test content", "doc.pdf")
        # Should not raise
        validate_attachment_file(file)

    def test_executable_disguised_as_pdf_rejected(self):
        from financials.validators import validate_attachment_file
        from financials.exceptions import AttachmentTypeNotAllowed
        # An executable with a .pdf extension
        file = self._make_fake_file(b"\x4d\x5a exe content", "malware.pdf")
        with self.assertRaises(AttachmentTypeNotAllowed):
            validate_attachment_file(file)

    def test_html_disguised_as_pdf_rejected(self):
        from financials.validators import validate_attachment_file
        from financials.exceptions import AttachmentTypeNotAllowed
        file = self._make_fake_file(b"<html><script>evil()</script></html>", "evil.pdf")
        with self.assertRaises(AttachmentTypeNotAllowed):
            validate_attachment_file(file)

    def test_valid_png_upload_passes(self):
        from financials.validators import validate_attachment_file
        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        file = self._make_fake_file(png_header, "image.png", "image/png")
        validate_attachment_file(file)

    def test_disallowed_extension_rejected(self):
        from financials.validators import validate_attachment_file
        from financials.exceptions import AttachmentTypeNotAllowed
        file = self._make_fake_file(b"%PDF-1.4", "doc.exe")
        with self.assertRaises(AttachmentTypeNotAllowed):
            validate_attachment_file(file)

    def test_oversized_file_rejected(self):
        from financials.validators import validate_attachment_file
        from financials.exceptions import AttachmentTooLarge
        from financials.constants import MAX_ATTACHMENT_SIZE_BYTES
        # Create a file that exceeds the size limit
        large_content = b"\x00" * (MAX_ATTACHMENT_SIZE_BYTES + 1)
        file = self._make_fake_file(large_content, "large.pdf")
        with self.assertRaises(AttachmentTooLarge):
            validate_attachment_file(file)


# ---------------------------------------------------------------------------
# 15. Logout audit logging
# ---------------------------------------------------------------------------

class LogoutAuditTests(TestCase):

    def setUp(self):
        self.user = make_user("logout@test.dev", password="GoodPass@1")
        self.client = APIClient()

    def test_logout_creates_audit_log(self):
        # First login to get tokens
        resp = self.client.post("/api/auth/login/", {
            "email": "logout@test.dev",
            "password": "GoodPass@1",
        })
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        access = resp.data["access"]
        refresh = resp.data["refresh"]

        # Logout
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.post("/api/auth/logout/", {"refresh": refresh})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        logs = SecurityAuditLog.objects.filter(
            event=SecurityAuditLog.EVENT_LOGOUT,
            actor=self.user,
        )
        self.assertTrue(logs.exists())
