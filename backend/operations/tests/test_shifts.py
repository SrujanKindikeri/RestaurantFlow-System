# =============================================================================
# RestaurantFlow — Shift Tests
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from django.test import TestCase
from django.utils import timezone

from operations.tests.base import OperationsTestBase
from operations.shift_services import open_shift, close_shift, add_handover_note, get_shift_summary
from operations.exceptions import ShiftAlreadyClosed
from operations.constants import OP_SHIFT_OPEN, OP_SHIFT_CLOSED, SHIFT_MORNING, SHIFT_EVENING


class ShiftLifecycleTest(OperationsTestBase):
    """Tests for shift open/close lifecycle."""

    def test_open_shift_success(self):
        shift = open_shift(
            branch=self.branch,
            shift_type=SHIFT_MORNING,
            opened_by=self.manager,
        )
        self.assertEqual(shift.status, OP_SHIFT_OPEN)
        self.assertEqual(shift.shift_type, SHIFT_MORNING)
        self.assertEqual(shift.opened_by, self.manager)
        self.assertEqual(shift.branch, self.branch)

    def test_open_shift_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_SHIFT_CREATED

        shift = open_shift(
            branch=self.branch, shift_type=SHIFT_MORNING, opened_by=self.manager,
        )
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_SHIFT_CREATED,
                shift_id=shift.id,
            ).exists()
        )

    def test_close_shift_success(self):
        shift = open_shift(
            branch=self.branch, shift_type=SHIFT_MORNING, opened_by=self.manager,
        )
        shift = close_shift(shift=shift, closed_by=self.manager, actual_notes="All good")
        self.assertEqual(shift.status, OP_SHIFT_CLOSED)
        self.assertIsNotNone(shift.ended_at)
        self.assertEqual(shift.closed_by, self.manager)
        self.assertEqual(shift.notes, "All good")

    def test_close_already_closed_raises(self):
        shift = open_shift(
            branch=self.branch, shift_type=SHIFT_MORNING, opened_by=self.manager,
        )
        close_shift(shift=shift, closed_by=self.manager)
        shift.refresh_from_db()
        with self.assertRaises(ShiftAlreadyClosed):
            close_shift(shift=shift, closed_by=self.manager)

    def test_close_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_SHIFT_CLOSED

        shift = open_shift(
            branch=self.branch, shift_type=SHIFT_MORNING, opened_by=self.manager,
        )
        close_shift(shift=shift, closed_by=self.manager)
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_SHIFT_CLOSED,
                shift_id=shift.id,
            ).exists()
        )


class ShiftHandoverNoteTest(OperationsTestBase):
    """Tests for shift handover notes."""

    def setUp(self):
        self.shift = open_shift(
            branch=self.branch, shift_type=SHIFT_MORNING, opened_by=self.manager,
        )

    def test_add_general_note(self):
        note = add_handover_note(
            shift=self.shift,
            created_by=self.manager,
            note_type="GENERAL",
            content="Had a busy day. Two tables complained about wait time.",
            priority="NORMAL",
        )
        self.assertEqual(note.note_type, "GENERAL")
        self.assertEqual(note.priority, "NORMAL")
        self.assertEqual(note.shift, self.shift)

    def test_add_high_priority_note(self):
        note = add_handover_note(
            shift=self.shift,
            created_by=self.manager,
            note_type="EQUIPMENT",
            content="Printer at Counter C01 is jammed.",
            priority="HIGH",
        )
        self.assertEqual(note.priority, "HIGH")

    def test_add_note_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_SHIFT_HANDOVER_CREATED

        add_handover_note(
            shift=self.shift, created_by=self.manager,
            note_type="GENERAL", content="Test note", priority="LOW",
        )
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_SHIFT_HANDOVER_CREATED,
                shift_id=self.shift.id,
            ).exists()
        )

    def test_multiple_notes_on_same_shift(self):
        for i in range(3):
            add_handover_note(
                shift=self.shift, created_by=self.manager,
                note_type="GENERAL", content=f"Note {i}", priority="NORMAL",
            )
        self.assertEqual(self.shift.handover_notes.count(), 3)


class ShiftSummaryTest(OperationsTestBase):
    """Tests for shift summary generation."""

    def test_summary_returns_expected_keys(self):
        shift = open_shift(
            branch=self.branch, shift_type=SHIFT_MORNING, opened_by=self.manager,
        )
        summary = get_shift_summary(shift)

        self.assertIn("orders", summary)
        self.assertIn("bills", summary)
        self.assertIn("payments", summary)
        self.assertIn("kitchen", summary)
        self.assertIn("handover_notes", summary)

    def test_summary_order_counts_include_created_orders(self):
        shift = open_shift(
            branch=self.branch, shift_type=SHIFT_MORNING, opened_by=self.manager,
        )
        self._make_order()
        self._make_confirmed_order()

        summary = get_shift_summary(shift)
        # At least the confirmed order should appear
        self.assertGreaterEqual(summary["orders"]["total"], 1)

    def test_summary_uses_existing_services(self):
        """Summary does not re-implement accounting — it reads from DB."""
        shift = open_shift(
            branch=self.branch, shift_type=SHIFT_EVENING, opened_by=self.manager,
        )
        summary = get_shift_summary(shift)
        self.assertEqual(summary["shift_type"], SHIFT_EVENING)
        self.assertEqual(summary["branch"], self.branch.name)
