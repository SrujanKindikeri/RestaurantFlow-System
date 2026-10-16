# =============================================================================
# RestaurantFlow — Enterprise Approval Policy Tests
# Phase 20
#
# Tests:
#   - Hierarchy resolution (branch → restaurant → company → system default)
#   - Threshold amount comparison
#   - Threshold percentage comparison
#   - Required permission/role extraction
#   - get_policy_summary dict shape
#   - No approval needed when no policy and amount below any threshold
# =============================================================================

from decimal import Decimal
from django.test import TestCase

from enterprise.tests.base import EnterpriseTestBase
from enterprise.approval_policy_resolver import ApprovalPolicyResolver
from enterprise.services import create_approval_policy
from enterprise.constants import (
    POLICY_TYPE_EXPENSE, POLICY_TYPE_DISCOUNT,
    CONFIG_SCOPE_COMPANY, CONFIG_SCOPE_RESTAURANT, CONFIG_SCOPE_BRANCH,
)


class TestApprovalPolicyResolver(EnterpriseTestBase):

    def test_no_policy_no_approval_required(self):
        resolver = ApprovalPolicyResolver(
            policy_type=POLICY_TYPE_EXPENSE,
            branch=self.branch_a1,
            amount=Decimal("500.00"),
        )
        self.assertFalse(resolver.requires_approval())

    def test_company_policy_applied_to_branch(self):
        create_approval_policy(
            company=self.org,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve",
            user=self.company_head,
            threshold_amount=Decimal("1000.00"),
        )
        # ₹1500 > ₹1000 threshold → approval required
        resolver = ApprovalPolicyResolver(
            policy_type=POLICY_TYPE_EXPENSE,
            branch=self.branch_a1,
            amount=Decimal("1500.00"),
        )
        self.assertTrue(resolver.requires_approval())
        self.assertEqual(resolver.get_required_permission(), "expense.approve")

    def test_company_policy_not_triggered_below_threshold(self):
        create_approval_policy(
            company=self.org,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve",
            user=self.company_head,
            threshold_amount=Decimal("10000.00"),
        )
        # ₹500 < ₹10000 → no approval
        resolver = ApprovalPolicyResolver(
            policy_type=POLICY_TYPE_EXPENSE,
            branch=self.branch_a1,
            amount=Decimal("500.00"),
        )
        self.assertFalse(resolver.requires_approval())

    def test_restaurant_policy_overrides_company(self):
        create_approval_policy(
            company=self.org,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve.company",
            user=self.company_head,
            threshold_amount=Decimal("10000.00"),
        )
        create_approval_policy(
            company=self.org,
            restaurant=self.restaurant_a,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve.manager",
            user=self.restaurant_owner,
            threshold_amount=Decimal("5000.00"),
        )
        resolver = ApprovalPolicyResolver(
            policy_type=POLICY_TYPE_EXPENSE,
            branch=self.branch_a1,
            amount=Decimal("7000.00"),
        )
        # Restaurant threshold is 5000 — 7000 > 5000 → triggered at restaurant level
        self.assertTrue(resolver.requires_approval())
        self.assertEqual(resolver.get_required_permission(), "expense.approve.manager")

    def test_branch_policy_most_specific(self):
        create_approval_policy(
            company=self.org,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve.company",
            user=self.company_head,
            threshold_amount=Decimal("10000.00"),
        )
        create_approval_policy(
            company=self.org,
            restaurant=self.restaurant_a,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve.manager",
            user=self.restaurant_owner,
            threshold_amount=Decimal("5000.00"),
        )
        create_approval_policy(
            company=self.org,
            restaurant=self.restaurant_a,
            branch=self.branch_a1,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve.branch_manager",
            user=self.branch_manager,
            threshold_amount=Decimal("2000.00"),
        )
        resolver = ApprovalPolicyResolver(
            policy_type=POLICY_TYPE_EXPENSE,
            branch=self.branch_a1,
            amount=Decimal("3000.00"),
        )
        # Branch threshold is ₹2000 → 3000 > 2000 → branch policy wins
        self.assertTrue(resolver.requires_approval())
        self.assertEqual(resolver.get_required_permission(), "expense.approve.branch_manager")

    def test_percentage_threshold(self):
        create_approval_policy(
            company=self.org,
            policy_type=POLICY_TYPE_DISCOUNT,
            required_permission="discount.approve",
            user=self.company_head,
            threshold_percentage=Decimal("20.00"),
        )
        resolver = ApprovalPolicyResolver(
            policy_type=POLICY_TYPE_DISCOUNT,
            branch=self.branch_a1,
            percentage=Decimal("25.00"),
        )
        self.assertTrue(resolver.requires_approval())

    def test_percentage_below_threshold(self):
        create_approval_policy(
            company=self.org,
            policy_type=POLICY_TYPE_DISCOUNT,
            required_permission="discount.approve",
            user=self.company_head,
            threshold_percentage=Decimal("20.00"),
        )
        resolver = ApprovalPolicyResolver(
            policy_type=POLICY_TYPE_DISCOUNT,
            branch=self.branch_a1,
            percentage=Decimal("15.00"),
        )
        self.assertFalse(resolver.requires_approval())

    def test_get_policy_summary_shape(self):
        create_approval_policy(
            company=self.org,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve",
            user=self.company_head,
            threshold_amount=Decimal("500.00"),
        )
        resolver = ApprovalPolicyResolver(
            policy_type=POLICY_TYPE_EXPENSE,
            branch=self.branch_a1,
            amount=Decimal("1000.00"),
        )
        summary = resolver.get_policy_summary()
        required_keys = {
            "requires_approval", "policy_found", "policy_scope",
            "required_permission", "required_role",
            "threshold_amount", "threshold_percentage",
        }
        self.assertEqual(set(summary.keys()), required_keys)
        self.assertTrue(summary["requires_approval"])
        self.assertEqual(summary["policy_scope"], "COMPANY")

    def test_class_check_method(self):
        create_approval_policy(
            company=self.org,
            policy_type=POLICY_TYPE_EXPENSE,
            required_permission="expense.approve",
            user=self.company_head,
            threshold_amount=Decimal("1000.00"),
        )
        result = ApprovalPolicyResolver.check(
            policy_type=POLICY_TYPE_EXPENSE,
            branch=self.branch_a1,
            amount=Decimal("1500.00"),
        )
        self.assertTrue(result)
