# =============================================================================
# RestaurantFlow — Operations Security & Isolation Tests
# Phase 19: Advanced POS & Restaurant Operations
#
# Tests cross-company, cross-restaurant, cross-branch isolation.
# Ensures no IDOR vulnerabilities in operations endpoints.
# =============================================================================

from decimal import Decimal
from django.test import TestCase, Client

from operations.tests.base import OperationsTestBase
from operations.access import (
    get_accessible_pos_sessions,
    get_accessible_shifts,
    get_accessible_bill_splits,
    get_accessible_modifier_groups,
    get_accessible_change_requests,
)
from operations.pos_services import start_pos_session
from operations.shift_services import open_shift
from operations.constants import SHIFT_MORNING


class CrossBranchIsolationTest(OperationsTestBase):
    """Tests that users cannot access data from other branches."""

    def setUp(self):
        # Start a POS session as the main branch cashier
        self.session = start_pos_session(
            user=self.cashier,
            counter_id=str(self.counter.id),
            branch=self.branch,
        )

    def test_cashier_cannot_see_other_branch_pos_sessions(self):
        """other_user is scoped to other_branch — cannot see main branch sessions."""
        sessions = get_accessible_pos_sessions(self.other_user)
        session_ids = list(sessions.values_list("id", flat=True))
        self.assertNotIn(self.session.id, session_ids)

    def test_cashier_can_see_own_branch_pos_sessions(self):
        """Main cashier can see their own session."""
        sessions = get_accessible_pos_sessions(self.cashier)
        session_ids = list(sessions.values_list("id", flat=True))
        self.assertIn(self.session.id, session_ids)

    def test_other_branch_user_cannot_access_shifts(self):
        shift = open_shift(
            branch=self.branch,
            shift_type=SHIFT_MORNING,
            opened_by=self.manager,
        )
        shifts = get_accessible_shifts(self.other_user)
        shift_ids = list(shifts.values_list("id", flat=True))
        self.assertNotIn(shift.id, shift_ids)

    def test_manager_can_access_own_branch_shifts(self):
        shift = open_shift(
            branch=self.branch,
            shift_type=SHIFT_MORNING,
            opened_by=self.manager,
        )
        shifts = get_accessible_shifts(self.manager)
        shift_ids = list(shifts.values_list("id", flat=True))
        self.assertIn(shift.id, shift_ids)

    def test_other_branch_user_cannot_access_bill_splits(self):
        """Bill splits from main branch are invisible to other_branch user."""
        splits = get_accessible_bill_splits(self.other_user)
        # Should be empty — other_user has no main branch access
        order = self._make_confirmed_order()
        # Manually create a bill split to check isolation
        from billing.models import Bill, BillStatus
        from operations.models import BillSplit
        from operations.constants import SPLIT_EQUAL, SPLIT_DRAFT
        bill = Bill.objects.create(
            order=order, branch=self.branch,
            bill_number=f"B-2026-SEC-{Bill.objects.count():04d}",
            status=BillStatus.FINALIZED,
            subtotal=Decimal("350.00"), grand_total=Decimal("367.50"),
            created_by=self.cashier,
        )
        split = BillSplit.objects.create(
            bill=bill, split_number=1, split_type=SPLIT_EQUAL,
            amount=Decimal("183.75"), status=SPLIT_DRAFT,
            created_by=self.cashier,
        )
        splits = get_accessible_bill_splits(self.other_user)
        self.assertNotIn(split.id, list(splits.values_list("id", flat=True)))

    def test_change_requests_scoped_to_branch(self):
        """Change requests are only visible within the correct branch scope."""
        order = self._make_confirmed_order()
        from operations.order_services import create_order_change_request
        req = create_order_change_request(
            order=order, requested_by=self.cashier,
            change_type="CHANGE_NOTE", reason="Test",
            requested_data={},
        )
        requests = get_accessible_change_requests(self.other_user)
        self.assertNotIn(req.id, list(requests.values_list("id", flat=True)))


class APIAuthenticationTest(OperationsTestBase):
    """Tests that all operations endpoints require authentication."""

    def test_pos_session_requires_auth(self):
        c = Client()
        r = c.get("/api/operations/pos/session/")
        self.assertEqual(r.status_code, 401)

    def test_tables_requires_auth(self):
        c = Client()
        r = c.get("/api/operations/tables/")
        self.assertEqual(r.status_code, 401)

    def test_shifts_requires_auth(self):
        c = Client()
        r = c.get("/api/operations/shifts/")
        self.assertEqual(r.status_code, 401)

    def test_dashboard_requires_auth(self):
        c = Client()
        r = c.get("/api/operations/dashboard/")
        self.assertEqual(r.status_code, 401)

    def test_bill_split_requires_auth(self):
        c = Client()
        r = c.post("/api/operations/bills/00000000-0000-0000-0000-000000000000/split/", {})
        self.assertEqual(r.status_code, 401)

    def test_receipt_print_requires_auth(self):
        c = Client()
        r = c.post(
            "/api/operations/bills/00000000-0000-0000-0000-000000000000/receipt/print/", {}
        )
        self.assertEqual(r.status_code, 401)

    def test_scan_requires_auth(self):
        c = Client()
        r = c.post("/api/operations/pos/scan/", {"barcode_or_sku": "SKU-TEST"})
        self.assertEqual(r.status_code, 401)


class APIPermissionTest(OperationsTestBase):
    """Tests that endpoints enforce permissions."""

    def setUp(self):
        self.client = Client()

    def test_waiter_cannot_start_pos_session(self):
        """Waiter role does not have pos.session.start permission."""
        self.client.force_login(self.waiter)
        r = self.client.post(
            "/api/operations/pos/session/start/",
            {"counter_id": str(self.counter.id)},
            content_type="application/json",
        )
        # Waiter has no pos.session.start — should be 403
        self.assertEqual(r.status_code, 403)

    def test_cashier_can_access_dashboard(self):
        """Cashier has operations.dashboard.view permission."""
        self.client.force_login(self.cashier)
        r = self.client.get("/api/operations/dashboard/")
        self.assertIn(r.status_code, [200, 400])  # 400 if no branch accessible

    def test_cross_branch_pos_session_blocked(self):
        """Cashier cannot start session at another branch's counter."""
        from counters.models import Counter, CounterSession, CounterStatus, SessionStatus
        other_counter = Counter.objects.create(
            branch=self.other_branch, name="Other Counter",
            code="X01", status=CounterStatus.ACTIVE,
        )
        CounterSession.objects.create(
            counter=other_counter, opened_by=self.other_user,
            opening_cash=Decimal("0.00"), status=SessionStatus.OPEN,
        )
        self.client.force_login(self.cashier)
        r = self.client.post(
            "/api/operations/pos/session/start/",
            {"counter_id": str(other_counter.id)},
            content_type="application/json",
        )
        # Backend verifies branch scope — other branch counter should fail
        self.assertIn(r.status_code, [400, 403, 404])

    def test_operations_404_on_nonexistent_resources(self):
        """Non-existent resource IDs return 404 — no data leakage."""
        self.client.force_login(self.manager)
        fake_id = "00000000-0000-0000-0000-000000000099"
        r = self.client.get(f"/api/operations/shifts/{fake_id}/handover/")
        self.assertEqual(r.status_code, 404)


class AuditLogImmutabilityTest(OperationsTestBase):
    """Tests that audit logs cannot be edited after creation."""

    def test_operations_audit_log_immutable(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_POS_SESSION_STARTED

        log = OperationsAuditLog.objects.create(
            actor=self.cashier,
            event_type=AUDIT_POS_SESSION_STARTED,
            branch=self.branch,
        )
        log.new_value = "tampered"
        with self.assertRaises(ValueError):
            log.save()

    def test_receipt_print_log_immutable(self):
        from operations.models import ReceiptPrintLog
        from billing.models import Bill, BillStatus
        order = self._make_confirmed_order()
        bill = Bill.objects.create(
            order=order, branch=self.branch,
            bill_number=f"B-2026-IMMUT-{Bill.objects.count():04d}",
            status=BillStatus.FINALIZED,
            subtotal=Decimal("350.00"), grand_total=Decimal("367.50"),
            created_by=self.cashier,
        )
        log = ReceiptPrintLog.objects.create(
            bill=bill, printed_by=self.cashier,
            print_type="ORIGINAL",
        )
        log.reason = "tampering attempt"
        with self.assertRaises(ValueError):
            log.save()


class POSSessionSecurityTest(OperationsTestBase):
    """Tests that POS session security invariants hold."""

    def test_device_identifier_not_used_for_auth(self):
        """Two users at same counter with same device_identifier get separate sessions."""
        from operations.pos_services import start_pos_session
        session1 = start_pos_session(
            user=self.cashier,
            counter_id=str(self.counter.id),
            device_identifier="DEVICE-ABC",
            branch=self.branch,
        )
        # End first session so the unique constraint doesn't block second user
        from operations.pos_services import end_pos_session
        end_pos_session(session=session1, user=self.cashier)

        session2 = start_pos_session(
            user=self.manager,
            counter_id=str(self.counter.id),
            device_identifier="DEVICE-ABC",  # same device ID — different user is OK
            branch=self.branch,
        )
        self.assertNotEqual(session1.user, session2.user)
        self.assertEqual(session1.device_identifier, session2.device_identifier)

    def test_pos_session_linked_to_counter_session(self):
        """POS session always references an open CounterSession."""
        session = start_pos_session(
            user=self.cashier,
            counter_id=str(self.counter.id),
            branch=self.branch,
        )
        self.assertEqual(session.counter_session, self.counter_session)
        self.assertIsNotNone(session.counter_session_id)
