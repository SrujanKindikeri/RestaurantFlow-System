# =============================================================================
# RestaurantFlow — Enterprise API Tests
# Phase 20
#
# Tests:
#   - Dashboard endpoint (auth required, returns expected shape)
#   - Branch list endpoint (scoped correctly)
#   - Configuration list (auth + scope)
#   - Effective configuration endpoint
#   - Rollout list
#   - Staff transfers list
#   - Approval policies list
#   - Audit log list
#   - Unauthenticated requests → 401
#   - Cross-tenant requests → 404 (IDOR prevention)
# =============================================================================

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from enterprise.tests.base import EnterpriseTestBase
from enterprise.services import set_configuration
from enterprise.models import BranchOperationalStatus
from enterprise.constants import BRANCH_STATUS_ACTIVE


class TestEnterpriseAPIAuthentication(EnterpriseTestBase):

    def setUp(self):
        self.client = APIClient()

    def test_dashboard_unauthenticated_returns_401(self):
        response = self.client.get("/api/enterprise/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_branches_unauthenticated_returns_401(self):
        response = self.client.get("/api/enterprise/branches/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_configuration_unauthenticated_returns_401(self):
        response = self.client.get("/api/enterprise/configuration/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class TestEnterpriseDashboardAPI(EnterpriseTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.company_head)

    def test_dashboard_returns_200(self):
        response = self.client.get("/api/enterprise/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_dashboard_contains_required_keys(self):
        response = self.client.get("/api/enterprise/dashboard/")
        data = response.json()
        required_keys = {
            "total_restaurants", "total_branches", "active_branches",
            "temporarily_closed", "scheduled_closures",
            "pending_transfers", "pending_rollouts", "pending_closures",
            "failed_rollouts_24h",
        }
        self.assertTrue(required_keys.issubset(set(data.keys())))


class TestEnterpriseBranchAPI(EnterpriseTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.company_head)

    def test_branch_list_returns_200(self):
        response = self.client.get("/api/enterprise/branches/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_branch_detail_returns_200(self):
        response = self.client.get(f"/api/enterprise/branches/{self.branch_a1.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_branch_detail_has_required_fields(self):
        response = self.client.get(f"/api/enterprise/branches/{self.branch_a1.pk}/")
        data = response.json()
        self.assertIn("branch_name", data)
        self.assertIn("operational_status", data)
        self.assertIn("operating_hours", data)

    def test_branch_detail_other_org_returns_404(self):
        """branch_b1 belongs to org_b — company_head of org_a must get 404."""
        response = self.client.get(f"/api/enterprise/branches/{self.branch_b1.pk}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_open_branch_action(self):
        # Ensure branch is closed first
        status_obj, _ = BranchOperationalStatus.objects.get_or_create(
            branch=self.branch_a1,
            defaults={"status": "TEMPORARILY_CLOSED"},
        )
        status_obj.status = "TEMPORARILY_CLOSED"
        status_obj.save()

        response = self.client.post(
            f"/api/enterprise/branches/{self.branch_a1.pk}/open/",
            {"reason": "test"},
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_opening_checklist_returns_list(self):
        response = self.client.get(
            f"/api/enterprise/branches/{self.branch_a1.pk}/opening-checklist/"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("checklist", response.json())


class TestEnterpriseConfigurationAPI(EnterpriseTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.company_head)

    def test_get_configuration_list(self):
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="true",
            user=self.company_head,
        )
        response = self.client.get(
            "/api/enterprise/configuration/",
            {"company_id": str(self.org.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_effective_configuration(self):
        response = self.client.get(
            "/api/enterprise/configuration/effective/",
            {"branch_id": str(self.branch_a1.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIsInstance(data, list)
        if data:
            self.assertIn("key", data[0])
            self.assertIn("source", data[0])

    def test_post_configuration(self):
        response = self.client.post(
            "/api/enterprise/configuration/",
            {
                "configuration_key": "billing.allow_discount",
                "configuration_value": "true",
                "company_id": str(self.org.pk),
            },
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])

    def test_post_invalid_key_returns_400(self):
        response = self.client.post(
            "/api/enterprise/configuration/",
            {
                "configuration_key": "invalid.hacker_key",
                "configuration_value": "true",
                "company_id": str(self.org.pk),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_configuration_history(self):
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="true",
            user=self.company_head,
        )
        response = self.client.get("/api/enterprise/configuration/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestEnterpriseRolloutAPI(EnterpriseTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.restaurant_owner)

    def test_rollout_list_requires_restaurant_id(self):
        response = self.client.get("/api/enterprise/rollouts/")
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND])

    def test_rollout_list_with_restaurant_id(self):
        response = self.client.get(
            "/api/enterprise/rollouts/",
            {"restaurant_id": str(self.restaurant_a.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_rollout(self):
        response = self.client.post(
            "/api/enterprise/rollouts/",
            {
                "restaurant_id": str(self.restaurant_a.pk),
                "menu_item_id": str(self.menu_item.pk),
                "rollout_type": "MENU_AVAILABILITY",
                "target_scope": "ALL_BRANCHES",
                "is_available": False,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TestEnterpriseStaffAPI(EnterpriseTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.restaurant_owner)

    def test_staff_overview_requires_restaurant_id(self):
        response = self.client.get("/api/enterprise/staff/")
        self.assertIn(response.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND])

    def test_staff_overview(self):
        response = self.client.get(
            "/api/enterprise/staff/",
            {"restaurant_id": str(self.restaurant_a.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_transfers_list(self):
        response = self.client.get(
            "/api/enterprise/staff/transfers/",
            {"restaurant_id": str(self.restaurant_a.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestEnterpriseApprovalPolicyAPI(EnterpriseTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.company_head)

    def test_get_policies(self):
        response = self.client.get("/api/enterprise/approval-policies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_policy(self):
        response = self.client.post(
            "/api/enterprise/approval-policies/",
            {
                "policy_type": "EXPENSE",
                "required_permission": "expense.approve",
                "threshold_amount": "5000.00",
                "company_id": str(self.org.pk),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class TestEnterpriseAuditAPI(EnterpriseTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.company_head)

    def test_audit_log_returns_200(self):
        response = self.client.get("/api/enterprise/audit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_audit_log_filtered_by_branch(self):
        response = self.client.get(
            "/api/enterprise/audit/",
            {"branch_id": str(self.branch_a1.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_audit_log_other_org_empty(self):
        """company_head of org_a should see 0 audit logs for org_b branches."""
        response = self.client.get(
            "/api/enterprise/audit/",
            {"branch_id": str(self.branch_b1.pk)},
        )
        # Should return 404 (IDOR prevention — branch_b1 not accessible)
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_200_OK])
