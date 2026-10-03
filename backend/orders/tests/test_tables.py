# =============================================================================
# RestaurantFlow — Orders Tests: DiningTable + TableSession
# Phase 6
# =============================================================================

from django.test import TestCase
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.db import IntegrityError

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch
from orders.models import DiningTable, TableSession, TableStatus, TableSessionStatus
from orders import services


# =============================================================================
# Helpers / Fixtures
# =============================================================================

def make_org(name="Test Org"):
    return Organization.objects.create(name=name, slug=name.lower().replace(" ", "-"))


def make_restaurant(org, name="Test Restaurant"):
    return Restaurant.objects.create(
        organization=org, name=name, code=name[:10].upper().replace(" ", "")
    )


def make_branch(restaurant, name="Main Branch", code="MAIN"):
    return Branch.objects.create(restaurant=restaurant, name=name, code=code)


def make_user(email="user@test.com", password="testpass123"):
    return User.objects.create_user(email=email, password=password,
                                     first_name="Test", last_name="User")


def make_permission(code, name=None, module="table", action="view"):
    perm, _ = Permission.objects.get_or_create(
        code=code,
        defaults={"name": name or code, "module": module, "action": action},
    )
    return perm


def make_role(code, scope="branch", permissions=None):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={"name": code, "scope": scope},
    )
    if permissions:
        role.permissions.add(*permissions)
    return role


def assign_role(user, role, branch=None, restaurant=None, organization=None):
    return UserRoleAssignment.objects.create(
        user=user,
        role=role,
        organization=organization or (branch.restaurant.organization if branch else restaurant.organization if restaurant else None),
        restaurant=restaurant or (branch.restaurant if branch else None),
        branch=branch,
        is_active=True,
    )


def make_table(branch, number="T01", capacity=4, section="Indoor"):
    return DiningTable.objects.create(
        branch=branch,
        table_number=number,
        capacity=capacity,
        section=section,
        status=TableStatus.ACTIVE,
    )


def make_waiter_user(branch, email="waiter@test.com"):
    """Create a user with table permissions assigned to the given branch."""
    user = make_user(email=email)
    perms = [
        make_permission("table.view", module="table", action="view"),
        make_permission("table.create", module="table", action="create"),
        make_permission("table.update", module="table", action="update"),
        make_permission("table.disable", module="table", action="disable"),
        make_permission("table.session.open", module="table", action="session.open"),
        make_permission("table.session.close", module="table", action="session.close"),
        make_permission("table.session.view", module="table", action="session.view"),
        make_permission("order.view.branch", module="order", action="view.branch"),
        make_permission("order.create.dine_in", module="order", action="create.dine_in"),
        make_permission("order.create.counter", module="order", action="create.counter"),
        make_permission("order.create.takeaway", module="order", action="create.takeaway"),
        make_permission("order.confirm", module="order", action="confirm"),
        make_permission("order.cancel", module="order", action="cancel"),
        make_permission("order.cancel.confirmed", module="order", action="cancel.confirmed"),
        make_permission("order.update", module="order", action="update"),
        make_permission("order.item.add", module="order", action="item.add"),
        make_permission("order.item.update", module="order", action="item.update"),
        make_permission("order.item.remove", module="order", action="item.remove"),
        make_permission("order.reassign_waiter", module="order", action="reassign_waiter"),
    ]
    role = make_role("WAITER_FULL", permissions=perms)
    assign_role(user, role, branch=branch)
    return user


# =============================================================================
# DiningTable Model Tests
# =============================================================================

class DiningTableModelTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)

    def test_create_table(self):
        table = DiningTable.objects.create(
            branch=self.branch,
            table_number="T01",
            capacity=4,
            section="Indoor",
            status=TableStatus.ACTIVE,
        )
        self.assertEqual(table.table_number, "T01")
        self.assertEqual(table.capacity, 4)
        self.assertEqual(table.status, TableStatus.ACTIVE)
        self.assertTrue(table.is_active)

    def test_duplicate_table_number_same_branch_rejected(self):
        make_table(self.branch, number="T01")
        with self.assertRaises(IntegrityError):
            make_table(self.branch, number="T01")

    def test_same_table_number_different_branches_allowed(self):
        branch2 = make_branch(self.restaurant, name="Branch 2", code="BR2")
        t1 = make_table(self.branch, number="T01")
        t2 = make_table(branch2, number="T01")
        self.assertNotEqual(t1.pk, t2.pk)
        self.assertEqual(t1.table_number, t2.table_number)

    def test_is_occupied_property_false_when_no_session(self):
        table = make_table(self.branch)
        self.assertFalse(table.is_occupied)

    def test_is_occupied_property_true_when_session_open(self):
        table = make_table(self.branch)
        user = make_user()
        TableSession.objects.create(
            table=table,
            opened_by=user,
            status=TableSessionStatus.OPEN,
            guest_count=2,
        )
        # Reload from DB
        table.refresh_from_db()
        self.assertTrue(table.is_occupied)

    def test_current_session_property(self):
        table = make_table(self.branch)
        user = make_user()
        self.assertIsNone(table.current_session)
        session = TableSession.objects.create(
            table=table,
            opened_by=user,
            status=TableSessionStatus.OPEN,
            guest_count=2,
        )
        self.assertEqual(table.current_session, session)

    def test_inactive_table_flag(self):
        table = make_table(self.branch)
        table.status = TableStatus.INACTIVE
        table.save()
        self.assertFalse(table.is_active)


# =============================================================================
# TableSession Model Tests
# =============================================================================

class TableSessionModelTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.table = make_table(self.branch)
        self.user = make_user()

    def test_open_session_created(self):
        session = TableSession.objects.create(
            table=self.table,
            opened_by=self.user,
            status=TableSessionStatus.OPEN,
            guest_count=3,
        )
        self.assertEqual(session.status, TableSessionStatus.OPEN)
        self.assertEqual(session.guest_count, 3)
        self.assertIsNone(session.closed_at)

    def test_only_one_open_session_per_table_db_constraint(self):
        TableSession.objects.create(
            table=self.table,
            opened_by=self.user,
            status=TableSessionStatus.OPEN,
            guest_count=2,
        )
        with self.assertRaises(IntegrityError):
            TableSession.objects.create(
                table=self.table,
                opened_by=self.user,
                status=TableSessionStatus.OPEN,
                guest_count=3,
            )

    def test_multiple_closed_sessions_allowed(self):
        s1 = TableSession.objects.create(
            table=self.table,
            opened_by=self.user,
            status=TableSessionStatus.CLOSED,
            guest_count=2,
        )
        s2 = TableSession.objects.create(
            table=self.table,
            opened_by=self.user,
            status=TableSessionStatus.CLOSED,
            guest_count=3,
        )
        self.assertNotEqual(s1.pk, s2.pk)

    def test_historical_sessions_preserved(self):
        TableSession.objects.create(
            table=self.table,
            opened_by=self.user,
            status=TableSessionStatus.CLOSED,
            guest_count=2,
        )
        TableSession.objects.create(
            table=self.table,
            opened_by=self.user,
            status=TableSessionStatus.CLOSED,
            guest_count=3,
        )
        self.assertEqual(self.table.sessions.count(), 2)


# =============================================================================
# Table Service Tests
# =============================================================================

class TableServiceTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.table = make_table(self.branch)
        self.actor = make_waiter_user(self.branch, email="actor@test.com")

    def test_open_table_session_via_service(self):
        session = services.open_table_session(
            self.actor, table=self.table, guest_count=2
        )
        self.assertEqual(session.status, TableSessionStatus.OPEN)
        self.assertEqual(session.opened_by, self.actor)
        self.assertEqual(session.guest_count, 2)

    def test_cannot_open_second_session_on_same_table(self):
        services.open_table_session(self.actor, table=self.table, guest_count=2)
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.open_table_session(self.actor, table=self.table, guest_count=3)
        self.assertEqual(ctx.exception.detail["code"], "TABLE_SESSION_ALREADY_OPEN")

    def test_cannot_open_session_on_inactive_table(self):
        self.table.status = TableStatus.INACTIVE
        self.table.save()
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.open_table_session(self.actor, table=self.table, guest_count=2)
        self.assertEqual(ctx.exception.detail["code"], "TABLE_INACTIVE")

    def test_close_table_session(self):
        session = services.open_table_session(self.actor, table=self.table, guest_count=2)
        closed = services.close_table_session(self.actor, session=session)
        self.assertEqual(closed.status, TableSessionStatus.CLOSED)
        self.assertEqual(closed.closed_by, self.actor)
        self.assertIsNotNone(closed.closed_at)

    def test_cannot_close_already_closed_session(self):
        session = services.open_table_session(self.actor, table=self.table, guest_count=2)
        services.close_table_session(self.actor, session=session)
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.close_table_session(self.actor, session=session)
        self.assertIn("not open", str(ctx.exception.detail).lower())

    def test_unauthorized_user_cannot_open_session(self):
        # User without table.session.open permission
        unauth_user = make_user(email="unauth@test.com")
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.open_table_session(unauth_user, table=self.table, guest_count=2)

    def test_cross_branch_user_cannot_open_session(self):
        # User assigned to a different branch
        other_branch = make_branch(self.restaurant, name="Other Branch", code="OTH")
        other_user = make_waiter_user(other_branch, email="other@test.com")
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.open_table_session(other_user, table=self.table, guest_count=2)


# =============================================================================
# Table API Tests
# =============================================================================

class DiningTableAPITests(APITestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.actor = make_waiter_user(self.branch, email="api_actor@test.com")

        # Get token
        response = self.client.post(
            "/api/auth/token/",
            {"email": "api_actor@test.com", "password": "testpass123"},
            format="json",
        )
        self.token = response.data.get("access", "")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_list_tables_authenticated(self):
        make_table(self.branch, number="T01")
        make_table(self.branch, number="T02")
        response = self.client.get("/api/tables/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_create_table(self):
        response = self.client.post(
            "/api/tables/",
            {
                "branch": str(self.branch.pk),
                "table_number": "T01",
                "capacity": 4,
                "section": "Indoor",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["table_number"], "T01")

    def test_duplicate_table_number_rejected(self):
        make_table(self.branch, number="T01")
        response = self.client.post(
            "/api/tables/",
            {
                "branch": str(self.branch.pk),
                "table_number": "T01",
                "capacity": 4,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_retrieve_table(self):
        table = make_table(self.branch, number="T05")
        response = self.client.get(f"/api/tables/{table.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["table_number"], "T05")

    def test_unknown_table_returns_404(self):
        import uuid
        response = self.client.get(f"/api/tables/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_branch_table_returns_404(self):
        """A table from another branch should return 404 not 403 — IDOR protection."""
        other_org = make_org("Other Org")
        other_rest = make_restaurant(other_org, "Other Rest")
        other_branch = make_branch(other_rest, "Other Branch", "OTH")
        other_table = make_table(other_branch, number="T01")
        response = self.client.get(f"/api/tables/{other_table.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_open_table_session_api(self):
        table = make_table(self.branch, number="T01")
        response = self.client.post(
            f"/api/tables/{table.pk}/sessions/open/",
            {"guest_count": 3},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "OPEN")
        self.assertEqual(response.data["guest_count"], 3)

    def test_open_session_twice_rejected(self):
        table = make_table(self.branch, number="T01")
        self.client.post(
            f"/api/tables/{table.pk}/sessions/open/",
            {"guest_count": 2},
            format="json",
        )
        response = self.client.post(
            f"/api/tables/{table.pk}/sessions/open/",
            {"guest_count": 3},
            format="json",
        )
        self.assertIn(response.status_code, [400, 409])

    def test_disable_table(self):
        table = make_table(self.branch, number="T01")
        response = self.client.post(f"/api/tables/{table.pk}/disable/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "INACTIVE")

    def test_unauthenticated_request_rejected(self):
        self.client.credentials()
        response = self.client.get("/api/tables/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
