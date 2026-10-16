# =============================================================================
# RestaurantFlow — Enterprise Staff Tests
# Phase 20
#
# Tests:
#   - Branch assignment
#   - Only one active primary per restaurant
#   - Transfer request → approve → complete
#   - Transfer rejection
#   - Cross-restaurant transfer prevention
#   - Same-branch transfer prevention
#   - Historical transactions preserved (no cascade)
# =============================================================================

from django.test import TestCase
from rest_framework.exceptions import ValidationError, PermissionDenied

from enterprise.tests.base import EnterpriseTestBase
from enterprise.staff_services import (
    assign_staff_to_branch,
    request_staff_transfer,
    approve_staff_transfer,
    reject_staff_transfer,
    complete_staff_transfer,
    cancel_staff_transfer,
)
from enterprise.models import StaffBranchAssignment, StaffTransfer
from enterprise.constants import (
    TRANSFER_STATUS_REQUESTED, TRANSFER_STATUS_APPROVED,
    TRANSFER_STATUS_COMPLETED, TRANSFER_STATUS_REJECTED,
    TRANSFER_STATUS_CANCELLED,
)
from enterprise.exceptions import StaffTransferScopeError


class TestStaffBranchAssignment(EnterpriseTestBase):

    def test_assign_staff_creates_assignment(self):
        assignment = assign_staff_to_branch(
            user_to_assign=self.cashier,
            branch=self.branch_a2,
            role=self.role_cashier,
            assigned_by=self.branch_manager,
            is_primary=False,
        )
        self.assertIsNotNone(assignment.pk)
        self.assertFalse(assignment.is_primary)
        self.assertTrue(assignment.is_active)

    def test_primary_assignment_deactivates_previous(self):
        """Only one active primary assignment per user per restaurant."""
        assign_staff_to_branch(
            user_to_assign=self.cashier,
            branch=self.branch_a1,
            role=self.role_cashier,
            assigned_by=self.branch_manager,
            is_primary=True,
        )
        # Assign to a different branch as primary — old primary must deactivate
        assign_staff_to_branch(
            user_to_assign=self.cashier,
            branch=self.branch_a2,
            role=self.role_cashier,
            assigned_by=self.branch_manager,
            is_primary=True,
        )
        active_primary = StaffBranchAssignment.objects.filter(
            user=self.cashier,
            restaurant=self.restaurant_a,
            is_primary=True,
            is_active=True,
        )
        self.assertEqual(active_primary.count(), 1)
        self.assertEqual(active_primary.first().branch, self.branch_a2)

    def test_cross_org_assignment_raises(self):
        """Cannot assign a user from a different organization."""
        with self.assertRaises(ValidationError):
            assign_staff_to_branch(
                user_to_assign=self.other_org_user,
                branch=self.branch_a1,
                role=self.role_cashier,
                assigned_by=self.branch_manager,
            )

    def test_no_permission_raises(self):
        with self.assertRaises(PermissionDenied):
            assign_staff_to_branch(
                user_to_assign=self.cashier,
                branch=self.branch_a1,
                role=self.role_cashier,
                assigned_by=self.other_org_user,
            )


class TestStaffTransfer(EnterpriseTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Give cashier an active primary assignment at branch_a1
        cls.cashier_assignment = StaffBranchAssignment.objects.create(
            user=cls.cashier,
            restaurant=cls.restaurant_a,
            branch=cls.branch_a1,
            role=cls.role_cashier,
            assigned_by=cls.branch_manager,
            is_primary=True,
            is_active=True,
        )

    def test_request_transfer(self):
        transfer = request_staff_transfer(
            user_to_transfer=self.cashier,
            source_branch=self.branch_a1,
            destination_branch=self.branch_a2,
            requested_by=self.branch_manager,
            reason="Operational requirement",
        )
        self.assertEqual(transfer.status, TRANSFER_STATUS_REQUESTED)
        self.assertEqual(transfer.user, self.cashier)

    def test_approve_transfer(self):
        transfer = request_staff_transfer(
            user_to_transfer=self.cashier,
            source_branch=self.branch_a1,
            destination_branch=self.branch_a2,
            requested_by=self.branch_manager,
            reason="Test approval",
        )
        approved = approve_staff_transfer(transfer, self.restaurant_owner)
        self.assertEqual(approved.status, TRANSFER_STATUS_APPROVED)
        self.assertEqual(approved.approved_by, self.restaurant_owner)

    def test_reject_transfer(self):
        transfer = request_staff_transfer(
            user_to_transfer=self.cashier,
            source_branch=self.branch_a1,
            destination_branch=self.branch_a2,
            requested_by=self.branch_manager,
            reason="Test rejection",
        )
        rejected = reject_staff_transfer(transfer, self.restaurant_owner, "Not needed")
        self.assertEqual(rejected.status, TRANSFER_STATUS_REJECTED)
        self.assertEqual(rejected.rejection_reason, "Not needed")

    def test_complete_transfer_updates_assignment(self):
        transfer = request_staff_transfer(
            user_to_transfer=self.cashier,
            source_branch=self.branch_a1,
            destination_branch=self.branch_a2,
            requested_by=self.branch_manager,
            reason="Complete test",
        )
        approve_staff_transfer(transfer, self.restaurant_owner)
        completed = complete_staff_transfer(transfer, self.restaurant_owner)
        self.assertEqual(completed.status, TRANSFER_STATUS_COMPLETED)

        # Old assignment at branch_a1 should be inactive
        old_assignment = StaffBranchAssignment.objects.filter(
            user=self.cashier,
            branch=self.branch_a1,
            is_primary=True,
            is_active=True,
        )
        self.assertEqual(old_assignment.count(), 0)

        # New assignment at branch_a2 should be active
        new_assignment = StaffBranchAssignment.objects.filter(
            user=self.cashier,
            branch=self.branch_a2,
            is_primary=True,
            is_active=True,
        )
        self.assertEqual(new_assignment.count(), 1)

    def test_cross_restaurant_transfer_raises(self):
        """Transfer to a branch in a different restaurant must raise."""
        StaffBranchAssignment.objects.get_or_create(
            user=self.cashier,
            restaurant=self.restaurant_a,
            branch=self.branch_a1,
            role=self.role_cashier,
            assigned_by=self.branch_manager,
            is_primary=True,
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            request_staff_transfer(
                user_to_transfer=self.cashier,
                source_branch=self.branch_a1,
                destination_branch=self.branch_b1,  # different org!
                requested_by=self.branch_manager,
                reason="cross-restaurant attempt",
            )

    def test_same_branch_transfer_raises(self):
        with self.assertRaises(ValidationError):
            request_staff_transfer(
                user_to_transfer=self.cashier,
                source_branch=self.branch_a1,
                destination_branch=self.branch_a1,
                requested_by=self.branch_manager,
                reason="same branch",
            )

    def test_no_source_assignment_raises(self):
        """Transfer must fail if user has no assignment at source branch."""
        with self.assertRaises(ValidationError):
            request_staff_transfer(
                user_to_transfer=self.restaurant_owner,  # owner has no branch assignment
                source_branch=self.branch_a1,
                destination_branch=self.branch_a2,
                requested_by=self.branch_manager,
                reason="no assignment",
            )

    def test_cancel_transfer(self):
        transfer = request_staff_transfer(
            user_to_transfer=self.cashier,
            source_branch=self.branch_a1,
            destination_branch=self.branch_a2,
            requested_by=self.branch_manager,
            reason="cancel test",
        )
        cancelled = cancel_staff_transfer(transfer, self.branch_manager)
        self.assertEqual(cancelled.status, TRANSFER_STATUS_CANCELLED)
