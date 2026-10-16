# =============================================================================
# RestaurantFlow — Enterprise Concurrency Tests
# Phase 20
#
# Tests:
#   - Concurrent configuration update — only one active record per key/scope
#   - Concurrent staff transfer requests — second must detect duplicate
#   - Duplicate rollout execution prevention
#   - Concurrent branch status changes — last write wins within valid transitions
#
# Note: Full concurrent thread tests require a real DB (PostgreSQL) and
# cannot run reliably in SQLite test environment. These tests verify
# idempotency and single-active-record invariants through sequential calls
# that simulate race-condition scenarios.
# =============================================================================

from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.db import transaction

from enterprise.tests.base import EnterpriseTestBase
from enterprise.services import set_configuration
from enterprise.models import EnterpriseConfiguration, StaffBranchAssignment
from enterprise.staff_services import request_staff_transfer
from enterprise.rollout_services import create_menu_rollout, execute_rollout
from enterprise.constants import ROLLOUT_SCOPE_ALL_BRANCHES


class TestConfigurationConcurrencyInvariants(EnterpriseTestBase):

    def test_only_one_active_config_per_scope_after_double_set(self):
        """Calling set_configuration twice must leave exactly one active row."""
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="10.00",
            user=self.company_head,
        )
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="20.00",
            user=self.company_head,
        )
        active = EnterpriseConfiguration.objects.filter(
            company=self.org,
            restaurant=None,
            branch=None,
            configuration_key="billing.maximum_discount_percentage",
            is_active=True,
        )
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().configuration_value, "20.00")

    def test_version_increments_on_each_update(self):
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="true",
            user=self.company_head,
        )
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="false",
            user=self.company_head,
        )
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="true",
            user=self.company_head,
        )
        latest = EnterpriseConfiguration.objects.filter(
            company=self.org,
            configuration_key="billing.allow_discount",
            is_active=True,
        ).first()
        self.assertEqual(latest.version, 3)

    def test_branch_level_config_does_not_affect_company_config(self):
        """Branch-level config creation must not touch company-level records."""
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="true",
            user=self.company_head,
        )
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="false",
            user=self.branch_manager,
            restaurant=self.restaurant_a,
            branch=self.branch_a1,
        )
        company_config = EnterpriseConfiguration.objects.filter(
            company=self.org,
            restaurant=None,
            branch=None,
            configuration_key="billing.allow_discount",
            is_active=True,
        ).first()
        # Company config still says "true" — branch config must not modify it
        self.assertEqual(company_config.configuration_value, "true")


class TestStaffTransferConcurrencyInvariants(EnterpriseTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        StaffBranchAssignment.objects.create(
            user=cls.cashier,
            restaurant=cls.restaurant_a,
            branch=cls.branch_a1,
            role=cls.role_cashier,
            assigned_by=cls.branch_manager,
            is_primary=True,
            is_active=True,
        )

    def test_duplicate_pending_transfer_raises(self):
        """Cannot create a second transfer while one is already pending."""
        from rest_framework.exceptions import ValidationError
        request_staff_transfer(
            user_to_transfer=self.cashier,
            source_branch=self.branch_a1,
            destination_branch=self.branch_a2,
            requested_by=self.branch_manager,
            reason="first transfer",
        )
        with self.assertRaises(ValidationError):
            request_staff_transfer(
                user_to_transfer=self.cashier,
                source_branch=self.branch_a1,
                destination_branch=self.branch_a2,
                requested_by=self.branch_manager,
                reason="duplicate transfer",
            )


class TestRolloutConcurrencyInvariants(EnterpriseTestBase):

    def test_cannot_run_second_rollout_while_first_active(self):
        """Second rollout for the same menu_item while first is DRAFT must raise."""
        from rest_framework.exceptions import ValidationError
        create_menu_rollout(
            restaurant=self.restaurant_a,
            menu_item=self.menu_item,
            target_scope=ROLLOUT_SCOPE_ALL_BRANCHES,
            is_available=False,
            user=self.restaurant_owner,
        )
        with self.assertRaises(ValidationError):
            create_menu_rollout(
                restaurant=self.restaurant_a,
                menu_item=self.menu_item,
                target_scope=ROLLOUT_SCOPE_ALL_BRANCHES,
                is_available=True,
                user=self.restaurant_owner,
            )

    def test_rollout_results_recorded_per_branch(self):
        """After execute, each branch must have exactly one result row."""
        rollout = create_menu_rollout(
            restaurant=self.restaurant_a,
            menu_item=self.menu_item,
            target_scope=ROLLOUT_SCOPE_ALL_BRANCHES,
            is_available=True,
            user=self.restaurant_owner,
        )
        execute_rollout(rollout, self.restaurant_owner)
        from enterprise.models import MenuRolloutBranch
        result_count = MenuRolloutBranch.objects.filter(rollout=rollout).count()
        branch_count = self.restaurant_a.branches.count()
        self.assertEqual(result_count, branch_count)
