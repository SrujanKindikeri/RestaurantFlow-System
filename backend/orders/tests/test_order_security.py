# =============================================================================
# RestaurantFlow — Orders Security Tests
# Phase 6
#
# Tests IDOR protection, cross-restaurant isolation, permission enforcement,
# and scope boundaries.
# =============================================================================

import uuid
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models import User
from organizations.models import Organization, Restaurant, Branch
from counters.models import Counter, CounterSession, CounterStatus, SessionStatus
from orders.models import DiningTable, TableSession, Order, TableStatus, TableSessionStatus, OrderType
from orders import services
from orders.tests.test_tables import (
    make_org, make_restaurant, make_branch, make_user,
    make_permission, make_role, assign_role, make_table, make_waiter_user,
)
from orders.tests.test_orders import (
    make_counter, make_counter_session, make_tax_rate,
    make_category, make_menu_item, make_branch_price, make_branch_availability,
)
from decimal import Decimal


def get_token(client, email, password="testpass123"):
    resp = client.post(
        "/api/auth/token/",
        {"email": email, "password": password},
        format="json",
    )
    return resp.data.get("access", "")


# =============================================================================
# Cross-Restaurant Isolation
# =============================================================================

class CrossRestaurantIsolationTests(APITestCase):
    """
    User from Restaurant A should never be able to access or modify
    resources from Restaurant B.
    """

    def setUp(self):
        # Restaurant A
        self.org_a = make_org("Org A")
        self.rest_a = make_restaurant(self.org_a, "Rest A")
        self.branch_a = make_branch(self.rest_a, "Branch A", "BA")
        self.user_a = make_waiter_user(self.branch_a, email="user_a@test.com")

        # Restaurant B (completely separate)
        self.org_b = make_org("Org B")
        self.rest_b = make_restaurant(self.org_b, "Rest B")
        self.branch_b = make_branch(self.rest_b, "Branch B", "BB")
        self.user_b = make_waiter_user(self.branch_b, email="user_b@test.com")

        # Tables in each restaurant
        self.table_a = make_table(self.branch_a, number="T01")
        self.table_b = make_table(self.branch_b, number="T01")

        # Tokens
        self.token_a = get_token(self.client, "user_a@test.com")
        self.token_b = get_token(self.client, "user_b@test.com")

    def test_user_a_cannot_see_branch_b_tables(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(f"/api/tables/{self.table_b.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_see_branch_a_tables(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        response = self.client.get(f"/api/tables/{self.table_a.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cannot_open_session_on_branch_b_table(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(
            f"/api/tables/{self.table_b.pk}/sessions/open/",
            {"guest_count": 2},
            format="json",
        )
        # Should be 404 (not found) since the table is not accessible
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cannot_list_branch_b_orders(self):
        # Create an order for branch B
        session_b = services.open_table_session(
            self.user_b, table=self.table_b, guest_count=2
        )
        services.create_order(
            self.user_b,
            branch=self.branch_b,
            order_type=OrderType.DINE_IN,
            table=self.table_b,
            table_session=session_b,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # User A should see 0 orders (all belong to branch B)
        self.assertEqual(response.data["count"], 0)

    def test_user_a_cannot_access_branch_b_order_by_uuid(self):
        session_b = services.open_table_session(
            self.user_b, table=self.table_b, guest_count=2
        )
        order_b = services.create_order(
            self.user_b,
            branch=self.branch_b,
            order_type=OrderType.DINE_IN,
            table=self.table_b,
            table_session=session_b,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.get(f"/api/orders/{order_b.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_a_cannot_create_order_with_branch_b_uuid(self):
        """Direct UUID injection attack: user A sends branch B's UUID in request body."""
        session_a = services.open_table_session(
            self.user_a, table=self.table_a, guest_count=2
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(
            "/api/orders/",
            {
                "branch": str(self.branch_b.pk),  # attacker sends branch B
                "order_type": "DINE_IN",
                "table": str(self.table_a.pk),
                "table_session": str(session_a.pk),
            },
            format="json",
        )
        # Backend must reject because user A can't access branch B
        self.assertIn(response.status_code, [400, 403])

    def test_user_a_cannot_use_branch_b_menu_item(self):
        """Cross-restaurant menu item injection in order."""
        # Menu item from restaurant B
        cat_b = make_category(self.rest_b, name="Cat B")
        item_b = make_menu_item(self.rest_b, cat_b, name="Rest B Dish", sku="RBD")
        make_branch_price(item_b, self.branch_b)
        make_branch_availability(item_b, self.branch_b)

        # User A creates an order
        session_a = services.open_table_session(
            self.user_a, table=self.table_a, guest_count=2
        )
        order_a = services.create_order(
            self.user_a,
            branch=self.branch_a,
            order_type=OrderType.DINE_IN,
            table=self.table_a,
            table_session=session_a,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        response = self.client.post(
            f"/api/orders/{order_a.pk}/items/",
            {
                "menu_item": str(item_b.pk),  # wrong restaurant's item
                "quantity": "1",
            },
            format="json",
        )
        # Must be rejected
        self.assertIn(response.status_code, [400, 403])


# =============================================================================
# Permission Boundary Tests
# =============================================================================

class PermissionBoundaryTests(APITestCase):
    def setUp(self):
        self.org = make_org("Perm Org")
        self.restaurant = make_restaurant(self.org, "Perm Rest")
        self.branch = make_branch(self.restaurant, "Perm Branch", "PB")

        # Full-permission actor
        self.actor = make_waiter_user(self.branch, email="full_actor@test.com")
        self.token = get_token(self.client, "full_actor@test.com")

        # No-permission user (just created, no role assignments)
        self.no_perm_user = make_user(email="noperm@test.com")
        self.no_perm_token = get_token(self.client, "noperm@test.com")

    def test_unauthenticated_tables_rejected(self):
        response = self.client.get("/api/tables/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_unauthenticated_orders_rejected(self):
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_no_permission_user_cannot_create_table(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_perm_token}")
        response = self.client.post(
            "/api/tables/",
            {"branch": str(self.branch.pk), "table_number": "T01", "capacity": 4},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_user_cannot_list_orders(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_perm_token}")
        response = self.client.get("/api/orders/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_user_table_list_returns_empty(self):
        """User can authenticate but sees empty results (no access to any branch)."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_perm_token}")
        # They don't have table.view permission so this returns 403
        response = self.client.get("/api/tables/")
        self.assertIn(response.status_code, [200, 403])
        if response.status_code == 200:
            self.assertEqual(response.data["count"], 0)


# =============================================================================
# UUID Enumeration Protection (IDOR)
# =============================================================================

class IDORProtectionTests(APITestCase):
    def setUp(self):
        self.org = make_org("IDOR Org")
        self.restaurant = make_restaurant(self.org, "IDOR Rest")
        self.branch = make_branch(self.restaurant)
        self.actor = make_waiter_user(self.branch, email="idor_actor@test.com")
        self.token = get_token(self.client, "idor_actor@test.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_random_uuid_table_returns_404(self):
        response = self.client.get(f"/api/tables/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_random_uuid_order_returns_404(self):
        response = self.client.get(f"/api/orders/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_random_uuid_table_session_returns_404(self):
        response = self.client.get(f"/api/table-sessions/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_random_uuid_order_item_patch_returns_404(self):
        response = self.client.patch(
            f"/api/order-items/{uuid.uuid4()}/",
            {"quantity": "2"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_random_uuid_order_confirm_returns_404(self):
        response = self.client.post(f"/api/orders/{uuid.uuid4()}/confirm/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# =============================================================================
# Cross-Branch Counter Injection Tests
# =============================================================================

class CrossBranchCounterTests(TestCase):
    def setUp(self):
        self.org = make_org("Counter Org")
        self.restaurant = make_restaurant(self.org)
        self.branch_a = make_branch(self.restaurant, "Branch A", "BA")
        self.branch_b = make_branch(self.restaurant, "Branch B", "BB")
        self.actor_a = make_waiter_user(self.branch_a, email="cashier_a@test.com")
        self.counter_b = make_counter(self.branch_b, code="C01")
        self.session_b = make_counter_session(self.counter_b, make_waiter_user(
            self.branch_b, email="cashier_b@test.com"
        ))

    def test_user_from_branch_a_cannot_use_counter_from_branch_b(self):
        from rest_framework.exceptions import ValidationError, PermissionDenied
        with self.assertRaises((ValidationError, PermissionDenied)):
            services.create_order(
                self.actor_a,
                branch=self.branch_a,
                order_type=OrderType.COUNTER,
                counter=self.counter_b,       # belongs to branch B
                counter_session=self.session_b,
            )
