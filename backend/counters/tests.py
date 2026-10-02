# =============================================================================
# RestaurantFlow — Counter Tests
# Phase 4
#
# Run with:  python manage.py test counters
#
# Coverage:
#   Counter model (CRUD, status, code uniqueness)
#   CounterAssignment (scope validation, history preservation)
#   CounterSession (open, close, force-close, concurrency, cash reconciliation)
#   API security (scope isolation, privilege escalation)
# =============================================================================

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import Permission, Role, UserRoleAssignment, UserProfile
from counters import services
from counters.models import (
    Counter,
    CounterAssignment,
    CounterSession,
    CounterStatus,
    SessionStatus,
    Shift,
)
from organizations.models import Branch, Organization, Restaurant

User = get_user_model()


# =============================================================================
# Base test helper
# =============================================================================

class BaseCounterTest(TestCase):
    """Sets up a minimal org/restaurant/branch/counter hierarchy and demo users."""

    def setUp(self):
        # Organization
        self.org = Organization.objects.create(
            name="Test Org", slug="test-org", currency="INR", timezone="Asia/Kolkata"
        )
        # Restaurant
        self.restaurant = Restaurant.objects.create(
            organization=self.org,
            name="Test Restaurant",
            code="TEST-001",
        )
        # Two branches
        self.branch_a = Branch.objects.create(
            restaurant=self.restaurant,
            name="Branch A",
            code="BR-A",
        )
        self.branch_b = Branch.objects.create(
            restaurant=self.restaurant,
            name="Branch B",
            code="BR-B",
        )

        # Permissions
        self._ensure_counter_permissions()

        # Roles
        self.role_manager = Role.objects.get_or_create(
            code="RESTAURANT_MANAGER",
            defaults={
                "name": "Restaurant Manager",
                "scope": Role.SCOPE_BRANCH,
                "is_system_role": True,
            },
        )[0]
        self.role_cashier = Role.objects.get_or_create(
            code="CASHIER",
            defaults={
                "name": "Cashier",
                "scope": Role.SCOPE_BRANCH,
                "is_system_role": True,
            },
        )[0]
        self.role_company_head = Role.objects.get_or_create(
            code="COMPANY_HEAD",
            defaults={
                "name": "Company Head",
                "scope": Role.SCOPE_ORGANIZATION,
                "is_system_role": True,
            },
        )[0]

        # Assign permissions to roles
        manager_perms = Permission.objects.filter(
            code__in=[
                "counter.view", "counter.create", "counter.update", "counter.disable",
                "counter.assign", "counter.unassign",
                "counter.session.view", "counter.session.open",
                "counter.session.close", "counter.session.force_close",
                "counter.reconcile", "shift.view", "shift.manage",
            ]
        )
        cashier_perms = Permission.objects.filter(
            code__in=[
                "counter.view",
                "counter.session.view", "counter.session.open", "counter.session.close",
            ]
        )
        company_head_perms = Permission.objects.filter(
            code__startswith="counter."
        ) | Permission.objects.filter(code__startswith="shift.")

        self.role_manager.permissions.set(manager_perms)
        self.role_cashier.permissions.set(cashier_perms)
        self.role_company_head.permissions.set(company_head_perms)

        # Users
        self.manager_user = User.objects.create_user(
            email="manager@test.com",
            password="Test@1234",
            first_name="Manager",
            last_name="User",
        )
        UserRoleAssignment.objects.create(
            user=self.manager_user,
            role=self.role_manager,
            organization=self.org,
            restaurant=self.restaurant,
            branch=self.branch_a,
            is_active=True,
        )

        self.cashier_user = User.objects.create_user(
            email="cashier@test.com",
            password="Test@1234",
            first_name="Cashier",
            last_name="User",
        )
        UserRoleAssignment.objects.create(
            user=self.cashier_user,
            role=self.role_cashier,
            organization=self.org,
            restaurant=self.restaurant,
            branch=self.branch_a,
            is_active=True,
        )

        self.company_head = User.objects.create_user(
            email="head@test.com",
            password="Test@1234",
            first_name="Company",
            last_name="Head",
        )
        UserRoleAssignment.objects.create(
            user=self.company_head,
            role=self.role_company_head,
            organization=self.org,
            is_active=True,
        )

        # Counters
        self.counter_a1 = Counter.objects.create(
            branch=self.branch_a, name="Main Billing", code="C01",
        )
        self.counter_a2 = Counter.objects.create(
            branch=self.branch_a, name="Takeaway", code="C02",
        )
        self.counter_b1 = Counter.objects.create(
            branch=self.branch_b, name="Main Billing", code="C01",  # same code, different branch — valid
        )

    def _ensure_counter_permissions(self):
        """Create counter permissions if they don't exist."""
        counter_perms = [
            ("counter.view", "View Counters", "counter", "view"),
            ("counter.create", "Create Counter", "counter", "create"),
            ("counter.update", "Update Counter", "counter", "update"),
            ("counter.disable", "Disable Counter", "counter", "disable"),
            ("counter.assign", "Assign Counter", "counter", "assign"),
            ("counter.unassign", "Unassign Counter", "counter", "unassign"),
            ("counter.session.view", "View Counter Sessions", "counter", "session.view"),
            ("counter.session.open", "Open Counter Session", "counter", "session.open"),
            ("counter.session.close", "Close Counter Session", "counter", "session.close"),
            ("counter.session.force_close", "Force-Close Counter Session", "counter", "session.force_close"),
            ("counter.reconcile", "Reconcile Counter Cash", "counter", "reconcile"),
            ("shift.view", "View Shifts", "shift", "view"),
            ("shift.manage", "Manage Shifts", "shift", "manage"),
        ]
        for code, name, module, action in counter_perms:
            Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "module": module, "action": action, "is_active": True},
            )


# =============================================================================
# Counter Model Tests
# =============================================================================

class CounterModelTests(BaseCounterTest):

    def test_counter_code_uppercased_on_save(self):
        c = Counter.objects.create(branch=self.branch_a, name="Drive Through", code="c03")
        self.assertEqual(c.code, "C03")

    def test_counter_is_active_synced_with_status_active(self):
        c = Counter.objects.create(branch=self.branch_a, name="X", code="C04", status=CounterStatus.ACTIVE)
        self.assertTrue(c.is_active)

    def test_counter_is_active_false_when_inactive(self):
        c = Counter.objects.create(branch=self.branch_a, name="X", code="C05", status=CounterStatus.INACTIVE)
        self.assertFalse(c.is_active)

    def test_counter_is_active_false_when_maintenance(self):
        c = Counter.objects.create(branch=self.branch_a, name="X", code="C06", status=CounterStatus.MAINTENANCE)
        self.assertFalse(c.is_active)

    def test_unique_code_within_branch_enforced(self):
        with self.assertRaises(Exception):  # IntegrityError or ValidationError
            Counter.objects.create(branch=self.branch_a, name="Duplicate", code="C01")

    def test_same_code_in_different_branches_allowed(self):
        """C01 already exists in branch_a and branch_b — both valid."""
        count = Counter.objects.filter(code="C01").count()
        self.assertEqual(count, 2)

    def test_str_representation(self):
        self.assertIn("C01", str(self.counter_a1))
        self.assertIn("Branch A", str(self.counter_a1))

    def test_can_open_session_property_active(self):
        self.assertTrue(self.counter_a1.can_open_session)

    def test_can_open_session_property_inactive(self):
        self.counter_a1.status = CounterStatus.INACTIVE
        self.counter_a1.save()
        self.assertFalse(self.counter_a1.can_open_session)

    def test_can_open_session_property_maintenance(self):
        self.counter_a1.status = CounterStatus.MAINTENANCE
        self.counter_a1.save()
        self.assertFalse(self.counter_a1.can_open_session)


# =============================================================================
# Counter Assignment Tests
# =============================================================================

class CounterAssignmentTests(BaseCounterTest):

    def test_assign_user_to_counter_in_their_branch(self):
        assignment = services.assign_counter(
            self.manager_user,
            counter=self.counter_a1,
            user=self.cashier_user,
        )
        self.assertIsNotNone(assignment.pk)
        self.assertTrue(assignment.is_active)
        self.assertEqual(assignment.user, self.cashier_user)
        self.assertEqual(assignment.counter, self.counter_a1)

    def test_assignment_history_preserved(self):
        """Deactivating an assignment keeps its DB record."""
        assignment = services.assign_counter(
            self.manager_user,
            counter=self.counter_a1,
            user=self.cashier_user,
        )
        services.deactivate_assignment(self.manager_user, assignment=assignment)
        # Record still exists with is_active=False
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertTrue(CounterAssignment.objects.filter(pk=assignment.pk).exists())

    def test_cross_branch_assignment_rejected(self):
        """Cashier from branch_a cannot be assigned to a counter in branch_b."""
        from rest_framework.exceptions import ValidationError
        with self.assertRaises((ValidationError, Exception)):
            services.assign_counter(
                self.manager_user,
                counter=self.counter_b1,  # branch_b counter
                user=self.cashier_user,   # only has branch_a access
            )

    def test_unauthorized_user_cannot_assign(self):
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.assign_counter(
                self.cashier_user,  # cashier lacks counter.assign
                counter=self.counter_a1,
                user=self.cashier_user,
            )

    def test_multiple_historical_assignments_preserved(self):
        a1 = services.assign_counter(
            self.manager_user, counter=self.counter_a1, user=self.cashier_user
        )
        services.deactivate_assignment(self.manager_user, assignment=a1)
        a2 = services.assign_counter(
            self.manager_user, counter=self.counter_a1, user=self.cashier_user
        )
        # Both records exist
        count = CounterAssignment.objects.filter(
            counter=self.counter_a1, user=self.cashier_user
        ).count()
        self.assertEqual(count, 2)


# =============================================================================
# Counter Session Tests
# =============================================================================

class CounterSessionTests(BaseCounterTest):

    def test_open_session_success(self):
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        self.assertEqual(session.status, SessionStatus.OPEN)
        self.assertEqual(session.opening_cash, Decimal("5000.00"))
        self.assertEqual(session.expected_cash, Decimal("5000.00"))
        self.assertEqual(session.opened_by, self.cashier_user)
        self.assertIsNone(session.actual_cash)

    def test_opening_cash_validates_non_negative(self):
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            services.open_session(
                self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("-1.00")
            )

    def test_cannot_open_session_on_inactive_counter(self):
        self.counter_a1.status = CounterStatus.INACTIVE
        self.counter_a1.save()
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            services.open_session(
                self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("1000.00")
            )

    def test_cannot_open_session_on_maintenance_counter(self):
        self.counter_a1.status = CounterStatus.MAINTENANCE
        self.counter_a1.save()
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            services.open_session(
                self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("1000.00")
            )

    def test_cannot_open_second_session_on_same_counter(self):
        services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.open_session(
                self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
            )
        self.assertIn("COUNTER_SESSION_ALREADY_OPEN", str(ctx.exception.detail))

    def test_close_session_calculates_difference(self):
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("10000.00")
        )
        session = services.close_session(
            self.cashier_user, session=session, actual_cash=Decimal("9850.00")
        )
        self.assertEqual(session.status, SessionStatus.CLOSED)
        self.assertEqual(session.actual_cash, Decimal("9850.00"))
        self.assertEqual(session.cash_difference, Decimal("-150.00"))

    def test_close_session_positive_difference(self):
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("10000.00")
        )
        session = services.close_session(
            self.cashier_user, session=session, actual_cash=Decimal("10200.00")
        )
        self.assertEqual(session.cash_difference, Decimal("200.00"))

    def test_close_session_zero_difference(self):
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        session = services.close_session(
            self.cashier_user, session=session, actual_cash=Decimal("5000.00")
        )
        self.assertEqual(session.cash_difference, Decimal("0.00"))

    def test_cannot_close_already_closed_session(self):
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        services.close_session(self.cashier_user, session=session, actual_cash=Decimal("5000.00"))
        session.refresh_from_db()

        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError) as ctx:
            services.close_session(self.cashier_user, session=session, actual_cash=Decimal("5000.00"))
        self.assertIn("COUNTER_SESSION_NOT_OPEN", str(ctx.exception.detail))

    def test_actual_cash_cannot_be_negative_on_close(self):
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            services.close_session(
                self.cashier_user, session=session, actual_cash=Decimal("-100.00")
            )

    def test_force_close_requires_permission(self):
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.force_close_session(
                self.cashier_user,  # cashier lacks counter.session.force_close
                session=session,
                reason="Testing",
            )

    def test_force_close_by_manager_succeeds(self):
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        session = services.force_close_session(
            self.manager_user,
            session=session,
            actual_cash=Decimal("4900.00"),
            reason="Cashier left unexpectedly",
        )
        self.assertEqual(session.status, SessionStatus.FORCE_CLOSED)
        self.assertEqual(session.closed_by, self.manager_user)
        self.assertEqual(session.cash_difference, Decimal("-100.00"))
        self.assertEqual(session.closing_note, "Cashier left unexpectedly")

    def test_force_close_without_actual_cash(self):
        """Force close is valid with no actual cash provided."""
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        session = services.force_close_session(
            self.manager_user,
            session=session,
            actual_cash=None,
            reason="Emergency",
        )
        self.assertEqual(session.status, SessionStatus.FORCE_CLOSED)
        self.assertIsNone(session.actual_cash)

    def test_closed_session_allows_new_session(self):
        """After closing, a new session can be opened on the same counter."""
        session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("5000.00")
        )
        services.close_session(self.cashier_user, session=session, actual_cash=Decimal("5000.00"))

        new_session = services.open_session(
            self.cashier_user, counter=self.counter_a1, opening_cash=Decimal("3000.00")
        )
        self.assertEqual(new_session.status, SessionStatus.OPEN)


# =============================================================================
# Concurrency Tests
# =============================================================================

class CounterSessionConcurrencyTests(BaseCounterTest):

    def test_db_constraint_prevents_two_open_sessions(self):
        """
        Verify the DB-level partial unique constraint blocks a second OPEN session.
        """
        CounterSession.objects.create(
            counter=self.counter_a1,
            opened_by=self.cashier_user,
            opening_cash=Decimal("5000.00"),
            expected_cash=Decimal("5000.00"),
            status=SessionStatus.OPEN,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CounterSession.objects.create(
                    counter=self.counter_a1,
                    opened_by=self.manager_user,
                    opening_cash=Decimal("1000.00"),
                    expected_cash=Decimal("1000.00"),
                    status=SessionStatus.OPEN,
                )


# =============================================================================
# Counter Disable / Reactivate Tests
# =============================================================================

class CounterLifecycleTests(BaseCounterTest):

    def test_disable_counter(self):
        counter = services.disable_counter(self.manager_user, counter=self.counter_a1)
        self.assertEqual(counter.status, CounterStatus.INACTIVE)
        self.assertFalse(counter.is_active)

    def test_reactivate_counter(self):
        self.counter_a1.status = CounterStatus.INACTIVE
        self.counter_a1.is_active = False
        self.counter_a1.save(update_fields=["status", "is_active", "updated_at"])

        counter = services.reactivate_counter(self.manager_user, counter=self.counter_a1)
        self.assertEqual(counter.status, CounterStatus.ACTIVE)
        self.assertTrue(counter.is_active)

    def test_unauthorized_cannot_disable(self):
        from rest_framework.exceptions import PermissionDenied
        with self.assertRaises(PermissionDenied):
            services.disable_counter(self.cashier_user, counter=self.counter_a1)


# =============================================================================
# API Security Tests (APITestCase)
# =============================================================================

class CounterAPISecurityTests(APITestCase):
    """Tests that verify scoped queryset isolation via the HTTP API."""

    def setUp(self):
        # Minimal re-setup for API tests
        self.base = BaseCounterTest()
        self.base.setUp()

        self.manager_token = self._get_token(self.base.manager_user)
        self.cashier_token = self._get_token(self.base.cashier_user)
        self.head_token = self._get_token(self.base.company_head)

    def _get_token(self, user):
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def _auth(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # ------------------------------------------------------------------ #
    # Counter list scoping                                                  #
    # ------------------------------------------------------------------ #

    def test_cashier_sees_only_their_branch_counters(self):
        self._auth(self.cashier_token)
        response = self.client.get("/api/counters/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {c["id"] for c in response.data["results"]}
        # Should see branch_a counters (C01, C02) but not branch_b
        self.assertIn(str(self.base.counter_a1.id), ids)
        self.assertIn(str(self.base.counter_a2.id), ids)
        self.assertNotIn(str(self.base.counter_b1.id), ids)

    def test_company_head_sees_all_counters(self):
        self._auth(self.head_token)
        response = self.client.get("/api/counters/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = {c["id"] for c in response.data["results"]}
        self.assertIn(str(self.base.counter_a1.id), ids)
        self.assertIn(str(self.base.counter_b1.id), ids)

    def test_cashier_cannot_access_other_branch_counter_detail(self):
        self._auth(self.cashier_token)
        response = self.client.get(f"/api/counters/{self.base.counter_b1.id}/")
        # Should get 404, not 403 — prevents UUID enumeration
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_denied(self):
        response = self.client.get("/api/counters/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # ------------------------------------------------------------------ #
    # Session open/close via API                                            #
    # ------------------------------------------------------------------ #

    def test_api_open_session(self):
        self._auth(self.cashier_token)
        response = self.client.post(
            f"/api/counters/{self.base.counter_a1.id}/sessions/open/",
            {"opening_cash": "5000.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "OPEN")
        self.assertEqual(response.data["opening_cash"], "5000.00")

    def test_api_open_session_duplicate_rejected(self):
        self._auth(self.cashier_token)
        self.client.post(
            f"/api/counters/{self.base.counter_a1.id}/sessions/open/",
            {"opening_cash": "5000.00"},
            format="json",
        )
        response = self.client.post(
            f"/api/counters/{self.base.counter_a1.id}/sessions/open/",
            {"opening_cash": "5000.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"]["code"], "COUNTER_SESSION_ALREADY_OPEN")

    def test_api_close_session(self):
        self._auth(self.cashier_token)
        open_resp = self.client.post(
            f"/api/counters/{self.base.counter_a1.id}/sessions/open/",
            {"opening_cash": "10000.00"},
            format="json",
        )
        session_id = open_resp.data["id"]

        close_resp = self.client.post(
            f"/api/counter-sessions/{session_id}/close/",
            {"actual_cash": "9850.00", "closing_note": "Normal close"},
            format="json",
        )
        self.assertEqual(close_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(close_resp.data["status"], "CLOSED")
        self.assertEqual(close_resp.data["cash_difference"], "-150.00")

    def test_api_force_close_by_cashier_rejected(self):
        """Cashier does not have counter.session.force_close."""
        self._auth(self.cashier_token)
        open_resp = self.client.post(
            f"/api/counters/{self.base.counter_a1.id}/sessions/open/",
            {"opening_cash": "5000.00"},
            format="json",
        )
        session_id = open_resp.data["id"]

        force_resp = self.client.post(
            f"/api/counter-sessions/{session_id}/force-close/",
            {"reason": "Testing"},
            format="json",
        )
        self.assertEqual(force_resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_force_close_by_manager(self):
        # Open with cashier
        self._auth(self.cashier_token)
        open_resp = self.client.post(
            f"/api/counters/{self.base.counter_a1.id}/sessions/open/",
            {"opening_cash": "5000.00"},
            format="json",
        )
        session_id = open_resp.data["id"]

        # Force-close with manager
        self._auth(self.manager_token)
        force_resp = self.client.post(
            f"/api/counter-sessions/{session_id}/force-close/",
            {"reason": "Emergency closure", "actual_cash": "4800.00"},
            format="json",
        )
        self.assertEqual(force_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(force_resp.data["status"], "FORCE_CLOSED")

    def test_api_open_session_negative_cash_rejected(self):
        self._auth(self.cashier_token)
        response = self.client.post(
            f"/api/counters/{self.base.counter_a1.id}/sessions/open/",
            {"opening_cash": "-500.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_api_counter_create(self):
        self._auth(self.manager_token)
        response = self.client.post(
            "/api/counters/",
            {
                "branch": str(self.base.branch_a.id),
                "name": "Drive Through",
                "code": "C10",
                "counter_type": "DRIVE_THROUGH",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["code"], "C10")

    def test_api_cashier_cannot_create_counter(self):
        """Cashier lacks counter.create."""
        self._auth(self.cashier_token)
        response = self.client.post(
            "/api/counters/",
            {"branch": str(self.base.branch_a.id), "name": "New", "code": "C99"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_api_dashboard(self):
        self._auth(self.manager_token)
        response = self.client.get(f"/api/counter-dashboard/?branch={self.base.branch_a.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("counters", response.data)
        self.assertIn("summary", response.data)

    def test_api_health_still_works(self):
        """Health endpoint must always respond — regression test."""
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ok")


# =============================================================================
# Shift Tests
# =============================================================================

class ShiftTests(BaseCounterTest):

    def test_create_shift(self):
        shift = Shift.objects.create(
            branch=self.branch_a,
            name="Morning",
            start_time="08:00:00",
            end_time="16:00:00",
        )
        self.assertEqual(shift.name, "Morning")
        self.assertTrue(shift.is_active)

    def test_shift_str(self):
        shift = Shift.objects.create(
            branch=self.branch_a,
            name="Evening",
            start_time="16:00:00",
            end_time="00:00:00",
        )
        self.assertIn("Evening", str(shift))
        self.assertIn("Branch A", str(shift))

    def test_open_session_with_shift(self):
        shift = Shift.objects.create(
            branch=self.branch_a,
            name="Morning",
            start_time="08:00:00",
            end_time="16:00:00",
        )
        session = services.open_session(
            self.cashier_user,
            counter=self.counter_a1,
            opening_cash=Decimal("5000.00"),
            shift=shift,
        )
        self.assertEqual(session.shift, shift)
