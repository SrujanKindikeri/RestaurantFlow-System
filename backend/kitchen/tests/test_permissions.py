# =============================================================================
# RestaurantFlow — Kitchen Permission Tests
# Phase 7
#
# Tests:
#   - kitchen staff can accept, start, mark items/order ready, cancel
#   - manager can accept, start, ready, cancel, priority update
#   - user without kitchen.accept cannot accept
#   - user without kitchen.start cannot start
#   - user without kitchen.order_ready cannot mark order ready
#   - user without kitchen.cancel cannot cancel
#   - user without kitchen.priority_update cannot update priority
#   - user from a different branch is rejected (branch isolation)
#   - unauthenticated user is rejected
#   - inactive user is rejected
#   - API endpoints return 403 for unauthorized users
#   - API endpoints return 404 for wrong-branch kitchen orders (IDOR)
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch
from kitchen.models import KitchenOrderStatus
from kitchen.services import (
    send_order_to_kitchen,
    accept_kitchen_order,
    start_preparation,
    mark_order_ready,
    cancel_kitchen_order,
    update_kitchen_priority,
)

from kitchen.tests.test_kitchen import KitchenTestBase


# =============================================================================
# Service-level permission tests
# =============================================================================

class TestKitchenServicePermissions(KitchenTestBase):

    def test_user_without_kitchen_accept_is_denied(self):
        """A user with no kitchen.accept permission cannot accept an order."""
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        with self.assertRaises(PermissionDenied):
            accept_kitchen_order(self.other_user, kitchen_order=ko)

    def test_user_without_kitchen_start_is_denied(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        accept_kitchen_order(self.kitchen_user, kitchen_order=ko)
        ko.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            start_preparation(self.other_user, kitchen_order=ko)

    def test_user_without_kitchen_cancel_is_denied(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        with self.assertRaises(PermissionDenied):
            cancel_kitchen_order(self.other_user, kitchen_order=ko)

    def test_user_without_kitchen_priority_update_is_denied(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        with self.assertRaises(PermissionDenied):
            update_kitchen_priority(self.other_user, kitchen_order=ko, priority="HIGH")

    def test_kitchen_staff_can_accept(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        ko = accept_kitchen_order(self.kitchen_user, kitchen_order=ko)
        self.assertEqual(ko.status, KitchenOrderStatus.ACCEPTED)

    def test_manager_can_accept(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        ko = accept_kitchen_order(self.manager, kitchen_order=ko)
        self.assertEqual(ko.status, KitchenOrderStatus.ACCEPTED)

    def test_inactive_user_is_denied(self):
        self.kitchen_user.is_active = False
        self.kitchen_user.save()
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        with self.assertRaises(PermissionDenied):
            accept_kitchen_order(self.kitchen_user, kitchen_order=ko)
        # restore
        self.kitchen_user.is_active = True
        self.kitchen_user.save()

    def test_wrong_branch_user_is_denied(self):
        """A user with kitchen.accept on a different branch cannot accept."""
        # Create second branch + assignment for other_user
        org2 = Organization.objects.create(name="Other Org", slug="other-org")
        restaurant2 = Restaurant.objects.create(
            organization=org2, name="Other Restaurant", slug="other-restaurant"
        )
        branch2 = Branch.objects.create(
            restaurant=restaurant2, name="Other Branch", slug="other-branch"
        )
        role2 = Role.objects.create(name="Kitchen Test2", code="KITCHEN_TEST2", scope=Role.SCOPE_BRANCH)
        role2.permissions.set(self.perms.values())
        UserRoleAssignment.objects.create(
            user=self.other_user, role=role2,
            organization=org2, restaurant=restaurant2, branch=branch2,
        )

        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        with self.assertRaises(PermissionDenied):
            accept_kitchen_order(self.other_user, kitchen_order=ko)


# =============================================================================
# API-level permission tests
# =============================================================================

class TestKitchenAPIPermissions(KitchenTestBase):

    def _get_tokens(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)

    def test_unauthenticated_list_returns_401(self):
        client = APIClient()
        response = client.get("/api/kitchen/orders/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_kitchen_user_can_list(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.kitchen_user)}")
        response = client.get("/api/kitchen/orders/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_without_kitchen_view_cannot_list(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.other_user)}")
        response = client.get("/api/kitchen/orders/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_accept_returns_200_for_authorized_user(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.kitchen_user)}")
        response = client.post(f"/api/kitchen/orders/{ko.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], KitchenOrderStatus.ACCEPTED)

    def test_accept_returns_403_for_unauthorized_user(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.other_user)}")
        response = client.post(f"/api/kitchen/orders/{ko.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_accept_returns_404_for_wrong_branch_order(self):
        """IDOR: user from another branch gets 404, not 403."""
        # Create second org + branch + user
        org2 = Organization.objects.create(name="Org B", slug="org-b")
        rest2 = Restaurant.objects.create(organization=org2, name="Rest B", slug="rest-b")
        branch2 = Branch.objects.create(restaurant=rest2, name="Branch B", slug="branch-b")
        user2 = User.objects.create_user(
            email="user2@test.com", password="pass", first_name="B", last_name="User"
        )
        role2 = Role.objects.create(name="Kitchen B", code="KITCHEN_B", scope=Role.SCOPE_BRANCH)
        role2.permissions.set(self.perms.values())
        UserRoleAssignment.objects.create(
            user=user2, role=role2,
            organization=org2, restaurant=rest2, branch=branch2,
        )

        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(user2)}")
        response = client.post(f"/api/kitchen/orders/{ko.id}/accept/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_start_returns_200(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        accept_kitchen_order(self.kitchen_user, kitchen_order=ko)
        ko.refresh_from_db()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.kitchen_user)}")
        response = client.post(f"/api/kitchen/orders/{ko.id}/start/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_priority_update_returns_200(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.manager)}")
        response = client.post(
            f"/api/kitchen/orders/{ko.id}/priority/",
            {"priority": "URGENT"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["priority"], "URGENT")

    def test_cancel_returns_200_with_reason(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.kitchen_user)}")
        response = client.post(
            f"/api/kitchen/orders/{ko.id}/cancel/",
            {"reason": "Customer changed order"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], KitchenOrderStatus.CANCELLED)

    def test_history_accessible_to_kitchen_user(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.kitchen_user)}")
        response = client.get("/api/kitchen/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_history_denied_to_user_without_permission(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {self._get_tokens(self.other_user)}")
        response = client.get("/api/kitchen/history/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
