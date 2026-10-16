# =============================================================================
# RestaurantFlow — Enterprise Branch Status Tests
# Phase 20
#
# Tests:
#   - Open / close / reopen branch
#   - Invalid status transitions
#   - Operational blocker prevention
#   - Opening checklist
# =============================================================================

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from enterprise.tests.base import EnterpriseTestBase
from enterprise.branch_services import (
    open_branch, close_branch, reopen_branch, set_branch_status,
    get_or_create_operational_status, get_opening_checklist,
)
from enterprise.models import BranchOperationalStatus
from enterprise.constants import (
    BRANCH_STATUS_ACTIVE,
    BRANCH_STATUS_TEMPORARILY_CLOSED,
    BRANCH_STATUS_MAINTENANCE,
    BRANCH_STATUS_INACTIVE,
)
from enterprise.exceptions import BranchStatusTransitionError


class TestBranchStatusTransitions(EnterpriseTestBase):

    def _ensure_active(self, branch):
        """Ensure branch starts as ACTIVE for each test."""
        status_obj, _ = BranchOperationalStatus.objects.get_or_create(
            branch=branch,
            defaults={"status": BRANCH_STATUS_ACTIVE},
        )
        if status_obj.status != BRANCH_STATUS_ACTIVE:
            status_obj.status = BRANCH_STATUS_ACTIVE
            status_obj.save()
        return status_obj

    def test_open_branch_from_closed(self):
        status_obj, _ = BranchOperationalStatus.objects.get_or_create(
            branch=self.branch_a1,
            defaults={"status": BRANCH_STATUS_TEMPORARILY_CLOSED},
        )
        status_obj.status = BRANCH_STATUS_TEMPORARILY_CLOSED
        status_obj.save()

        result = open_branch(self.branch_a1, self.branch_manager, reason="test open")
        self.assertEqual(result.status, BRANCH_STATUS_ACTIVE)
        self.assertEqual(result.status_changed_by, self.branch_manager)

    def test_close_branch_from_active(self):
        self._ensure_active(self.branch_a1)
        result = close_branch(
            self.branch_a1, self.branch_manager, reason="test close", force=True
        )
        self.assertEqual(result.status, BRANCH_STATUS_TEMPORARILY_CLOSED)

    def test_reopen_branch(self):
        self._ensure_active(self.branch_a1)
        close_branch(self.branch_a1, self.branch_manager, "closing", force=True)
        result = reopen_branch(self.branch_a1, self.branch_manager, "reopening")
        self.assertEqual(result.status, BRANCH_STATUS_ACTIVE)

    def test_invalid_transition_raises(self):
        """Cannot go from INACTIVE directly to TEMPORARILY_CLOSED."""
        status_obj, _ = BranchOperationalStatus.objects.get_or_create(
            branch=self.branch_a1,
            defaults={"status": BRANCH_STATUS_INACTIVE},
        )
        status_obj.status = BRANCH_STATUS_INACTIVE
        status_obj.save()

        with self.assertRaises(ValidationError):
            close_branch(self.branch_a1, self.branch_manager, "test", force=True)

    def test_set_maintenance_status(self):
        self._ensure_active(self.branch_a1)
        result = set_branch_status(
            self.branch_a1, BRANCH_STATUS_MAINTENANCE,
            self.branch_manager, reason="maintenance"
        )
        self.assertEqual(result.status, BRANCH_STATUS_MAINTENANCE)

    def test_no_permission_raises(self):
        """Cashier without enterprise.branch.close permission must be denied."""
        self._ensure_active(self.branch_a1)
        with self.assertRaises(PermissionDenied):
            close_branch(self.branch_a1, self.cashier, "test", force=True)

    def test_cross_branch_access_denied(self):
        """branch_manager for branch_a1 cannot close branch_b1 (different org)."""
        with self.assertRaises(PermissionDenied):
            close_branch(self.branch_b1, self.branch_manager, "test", force=True)


class TestOpeningChecklist(EnterpriseTestBase):

    def test_checklist_returns_correct_types(self):
        """Opening checklist must return entries for all expected check types."""
        from enterprise.constants import (
            CHECKLIST_COUNTER_READY, CHECKLIST_KITCHEN_READY,
            CHECKLIST_INVENTORY_READY, CHECKLIST_STAFF_READY,
            CHECKLIST_PAYMENT_METHODS_READY, CHECKLIST_POS_READY,
        )
        checklist = get_opening_checklist(self.branch_a1, self.branch_manager)
        types = {item["type"] for item in checklist}
        expected = {
            CHECKLIST_COUNTER_READY, CHECKLIST_KITCHEN_READY,
            CHECKLIST_INVENTORY_READY, CHECKLIST_STAFF_READY,
            CHECKLIST_PAYMENT_METHODS_READY, CHECKLIST_POS_READY,
        }
        self.assertEqual(types, expected)

    def test_checklist_denied_for_unauthorized_user(self):
        """User without branch access cannot see checklist."""
        with self.assertRaises(PermissionDenied):
            get_opening_checklist(self.branch_a1, self.other_org_user)

    def test_checklist_items_have_required_fields(self):
        checklist = get_opening_checklist(self.branch_a1, self.branch_manager)
        for item in checklist:
            self.assertIn("type", item)
            self.assertIn("label", item)
            self.assertIn("status", item)
            self.assertIn("detail", item)
            self.assertIn(item["status"], {"READY", "WARNING", "BLOCKED"})
