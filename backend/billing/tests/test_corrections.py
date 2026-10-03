# =============================================================================
# RestaurantFlow — Bill Correction Tests
# Phase 8
#
# Tests:
#   - correction request on finalized bill
#   - correction request on non-finalized bill rejected
#   - correction approval
#   - correction rejection
#   - self-approval prevention
#   - unauthorized approval rejected
#   - requester can cancel their own request
#   - non-requester cannot cancel without approval permission
#   - correction type choices validated
#   - reason required (min length)
#   - approved CANCELLATION correction voids the bill
#   - original bill financial history preserved (snapshot in requested_data)
#   - multiple pending corrections allowed (no limit)
# =============================================================================

from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from billing.models import (
    Bill, BillStatus, BillCorrectionRequest,
    CorrectionStatus, CorrectionType,
)
from billing import services
from billing.tests.base import BillingTestBase


class TestRequestCorrection(BillingTestBase):
    """Tests for request_bill_correction()."""

    def _make_finalized_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        return services.finalize_bill(bill, self.cashier)

    def test_request_correction_on_finalized_bill(self):
        bill = self._make_finalized_bill()
        bill.refresh_from_db()
        correction = services.request_bill_correction(
            bill, self.cashier,
            correction_type=CorrectionType.ITEM_CORRECTION,
            reason="Wrong quantity was entered for Biryani item.",
        )
        self.assertIsNotNone(correction)
        self.assertEqual(correction.status, CorrectionStatus.PENDING)
        self.assertEqual(correction.correction_type, CorrectionType.ITEM_CORRECTION)
        self.assertEqual(correction.requested_by, self.cashier)

    def test_request_correction_on_draft_bill_rejected(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        # Draft bill — not finalized
        with self.assertRaises(ValidationError) as ctx:
            services.request_bill_correction(
                bill, self.cashier,
                correction_type=CorrectionType.ITEM_CORRECTION,
                reason="Some reason that is long enough.",
            )
        self.assertEqual(ctx.exception.detail["code"], "BILL_NOT_FINALIZED")

    def test_reason_required(self):
        bill = self._make_finalized_bill()
        bill.refresh_from_db()
        with self.assertRaises(ValidationError):
            services.request_bill_correction(
                bill, self.cashier,
                correction_type=CorrectionType.DISCOUNT_CORRECTION,
                reason="short",  # too short
            )

    def test_blank_reason_rejected(self):
        bill = self._make_finalized_bill()
        bill.refresh_from_db()
        with self.assertRaises(ValidationError):
            services.request_bill_correction(
                bill, self.cashier,
                correction_type=CorrectionType.TAX_CORRECTION,
                reason="",
            )

    def test_no_permission_raises(self):
        bill = self._make_finalized_bill()
        bill.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            services.request_bill_correction(
                bill, self.other_user,
                correction_type=CorrectionType.ITEM_CORRECTION,
                reason="This should not be allowed for this user.",
            )

    def test_snapshot_stored_in_requested_data(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()

        correction = services.request_bill_correction(
            bill, self.cashier,
            correction_type=CorrectionType.ITEM_CORRECTION,
            reason="Incorrect item was billed, needs correction review.",
        )
        # Snapshot must contain key financial data
        self.assertIn("bill_number", correction.requested_data)
        self.assertIn("grand_total", correction.requested_data)
        self.assertIn("items", correction.requested_data)
        self.assertEqual(correction.requested_data["bill_number"], bill.bill_number)

    def test_invalid_correction_type_rejected(self):
        bill = self._make_finalized_bill()
        bill.refresh_from_db()
        with self.assertRaises(ValidationError):
            services.request_bill_correction(
                bill, self.cashier,
                correction_type="INVALID_TYPE",
                reason="Some reason that is long enough to pass.",
            )

    def test_all_correction_types_accepted(self):
        for ctype in CorrectionType.values:
            bill = self._make_finalized_bill()
            bill.refresh_from_db()
            correction = services.request_bill_correction(
                bill, self.cashier,
                correction_type=ctype,
                reason=f"Testing correction type {ctype} with sufficient reason.",
            )
            self.assertEqual(correction.correction_type, ctype)


class TestApproveCorrection(BillingTestBase):
    """Tests for approve_bill_correction()."""

    def _make_pending_correction(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        return services.request_bill_correction(
            bill, self.cashier,
            correction_type=CorrectionType.ITEM_CORRECTION,
            reason="Wrong item quantity submitted for correction by cashier.",
        )

    def test_manager_approves_correction(self):
        correction = self._make_pending_correction()
        approved = services.approve_bill_correction(
            correction, self.manager, note="Verified — approved."
        )
        self.assertEqual(approved.status, CorrectionStatus.APPROVED)
        self.assertEqual(approved.reviewed_by, self.manager)
        self.assertIsNotNone(approved.reviewed_at)

    def test_self_approval_prevented(self):
        """Cashier cannot approve their own correction request."""
        correction = self._make_pending_correction()
        with self.assertRaises(ValidationError):
            services.approve_bill_correction(
                correction, self.cashier,  # same as requested_by
                note="Self-approval attempt.",
            )

    def test_no_approval_permission_raises(self):
        correction = self._make_pending_correction()
        with self.assertRaises(PermissionDenied):
            services.approve_bill_correction(
                correction, self.other_user,
                note="Unauthorized.",
            )

    def test_cannot_approve_non_pending_correction(self):
        correction = self._make_pending_correction()
        # Reject it first
        services.reject_bill_correction(
            correction, self.manager, note="Rejecting first."
        )
        correction.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            services.approve_bill_correction(
                correction, self.manager, note="Trying to approve rejected."
            )
        self.assertEqual(ctx.exception.detail["code"], "CORRECTION_NOT_PENDING")

    def test_cancellation_type_voids_bill(self):
        """Approving a CANCELLATION correction should void the bill."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        correction = services.request_bill_correction(
            bill, self.cashier,
            correction_type=CorrectionType.CANCELLATION,
            reason="Customer disputes the entire bill, requesting full cancellation.",
        )
        services.approve_bill_correction(
            correction, self.manager, note="Approved for full cancellation."
        )
        bill.refresh_from_db()
        self.assertEqual(bill.status, BillStatus.VOID)

    def test_item_correction_approval_does_not_change_bill_status(self):
        """Non-cancellation approvals do not change the bill status."""
        correction = self._make_pending_correction()
        services.approve_bill_correction(
            correction, self.manager, note="Item count corrected."
        )
        correction.refresh_from_db()
        bill = correction.bill
        bill.refresh_from_db()
        self.assertEqual(bill.status, BillStatus.FINALIZED)  # unchanged


class TestRejectCorrection(BillingTestBase):
    """Tests for reject_bill_correction()."""

    def _make_pending_correction(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        return services.request_bill_correction(
            bill, self.cashier,
            correction_type=CorrectionType.DISCOUNT_CORRECTION,
            reason="Discount was applied incorrectly to the bill.",
        )

    def test_manager_rejects_correction(self):
        correction = self._make_pending_correction()
        rejected = services.reject_bill_correction(
            correction, self.manager,
            note="Discount was correctly applied per policy.",
        )
        self.assertEqual(rejected.status, CorrectionStatus.REJECTED)
        self.assertEqual(rejected.reviewed_by, self.manager)
        self.assertEqual(rejected.review_note, "Discount was correctly applied per policy.")

    def test_reject_requires_note(self):
        correction = self._make_pending_correction()
        with self.assertRaises(ValidationError):
            services.reject_bill_correction(
                correction, self.manager, note=""
            )

    def test_self_rejection_prevented(self):
        correction = self._make_pending_correction()
        with self.assertRaises(ValidationError):
            services.reject_bill_correction(
                correction, self.cashier,  # same as requester
                note="Self rejection attempt.",
            )

    def test_no_permission_raises(self):
        correction = self._make_pending_correction()
        with self.assertRaises(PermissionDenied):
            services.reject_bill_correction(
                correction, self.other_user, note="No permission."
            )

    def test_bill_status_unchanged_after_rejection(self):
        correction = self._make_pending_correction()
        services.reject_bill_correction(
            correction, self.manager, note="Rejection note."
        )
        correction.refresh_from_db()
        bill = correction.bill
        bill.refresh_from_db()
        self.assertEqual(bill.status, BillStatus.FINALIZED)


class TestCancelCorrection(BillingTestBase):
    """Tests for cancel_bill_correction()."""

    def _make_pending_correction(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        return services.request_bill_correction(
            bill, self.cashier,
            correction_type=CorrectionType.TAX_CORRECTION,
            reason="Tax code was incorrect on the finalized bill.",
        )

    def test_requester_can_cancel(self):
        correction = self._make_pending_correction()
        cancelled = services.cancel_bill_correction(correction, self.cashier)
        self.assertEqual(cancelled.status, CorrectionStatus.CANCELLED)

    def test_approver_can_cancel_others_request(self):
        correction = self._make_pending_correction()
        cancelled = services.cancel_bill_correction(correction, self.manager)
        self.assertEqual(cancelled.status, CorrectionStatus.CANCELLED)

    def test_non_requester_without_permission_cannot_cancel(self):
        correction = self._make_pending_correction()
        with self.assertRaises(PermissionDenied):
            services.cancel_bill_correction(correction, self.other_user)

    def test_cannot_cancel_approved_correction(self):
        correction = self._make_pending_correction()
        services.approve_bill_correction(correction, self.manager, note="Approved.")
        correction.refresh_from_db()
        with self.assertRaises(ValidationError):
            services.cancel_bill_correction(correction, self.cashier)


class TestCorrectionOriginalHistory(BillingTestBase):
    """Verify original financial history is preserved through corrections."""

    def test_original_bill_values_in_snapshot(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()

        original_grand_total = bill.grand_total  # 645.00
        original_tax_amount = bill.tax_amount    # 25.00

        correction = services.request_bill_correction(
            bill, self.cashier,
            correction_type=CorrectionType.ITEM_CORRECTION,
            reason="Item was entered with wrong quantity for Biryani.",
        )

        # Original values are in the snapshot
        snapshot = correction.requested_data
        self.assertEqual(Decimal(snapshot["grand_total"]), original_grand_total)
        self.assertEqual(Decimal(snapshot["tax_amount"]), original_tax_amount)

    def test_approving_non_cancellation_preserves_bill_amounts(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        original_total = bill.grand_total

        correction = services.request_bill_correction(
            bill, self.cashier,
            correction_type=CorrectionType.ITEM_CORRECTION,
            reason="Correction request for review and approval process.",
        )
        services.approve_bill_correction(correction, self.manager, note="Noted.")

        # Bill amounts unchanged
        bill.refresh_from_db()
        self.assertEqual(bill.grand_total, original_total)
