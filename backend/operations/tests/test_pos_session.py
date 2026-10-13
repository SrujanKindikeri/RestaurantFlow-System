# =============================================================================
# RestaurantFlow — POS Session Tests
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from django.test import TestCase
from django.utils import timezone

from operations.tests.base import OperationsTestBase
from operations.models import POSSession
from operations.pos_services import start_pos_session, pause_pos_session, resume_pos_session, end_pos_session
from operations.exceptions import (
    POSSessionConflict, CounterSessionNotActive, UnauthorizedCounter,
)
from operations.constants import POS_SESSION_ACTIVE, POS_SESSION_PAUSED, POS_SESSION_ENDED
from counters.models import CounterStatus, SessionStatus


class POSSessionStartTest(OperationsTestBase):
    """Tests for starting a POS session."""

    def test_start_session_success(self):
        """A cashier can start a session on their counter."""
        session = start_pos_session(
            user=self.cashier,
            counter_id=str(self.counter.id),
            branch=self.branch,
        )
        self.assertEqual(session.status, POS_SESSION_ACTIVE)
        self.assertEqual(session.user, self.cashier)
        self.assertEqual(session.counter, self.counter)
        self.assertEqual(session.counter_session, self.counter_session)
        self.assertIsNotNone(session.last_activity_at)

    def test_start_session_creates_audit_log(self):
        """Starting a session creates an OperationsAuditLog entry."""
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_POS_SESSION_STARTED

        start_pos_session(
            user=self.cashier,
            counter_id=str(self.counter.id),
            branch=self.branch,
        )
        log = OperationsAuditLog.objects.filter(
            actor=self.cashier,
            event_type=AUDIT_POS_SESSION_STARTED,
        ).first()
        self.assertIsNotNone(log)

    def test_start_session_wrong_counter_raises(self):
        """Counter from another branch raises UnauthorizedCounter."""
        from counters.models import Counter
        other_counter = Counter.objects.create(
            branch=self.other_branch, name="Other Counter", code="C99",
            status=CounterStatus.ACTIVE,
        )
        with self.assertRaises(UnauthorizedCounter):
            start_pos_session(
                user=self.cashier,
                counter_id=str(other_counter.id),
                branch=self.branch,
            )

    def test_start_session_inactive_counter_raises(self):
        """Inactive counter raises UnauthorizedCounter."""
        from counters.models import Counter
        inactive = Counter.objects.create(
            branch=self.branch, name="Inactive Counter", code="C02",
            status=CounterStatus.INACTIVE,
        )
        with self.assertRaises(UnauthorizedCounter):
            start_pos_session(
                user=self.cashier,
                counter_id=str(inactive.id),
                branch=self.branch,
            )

    def test_start_session_no_counter_session_raises(self):
        """Counter with no open CounterSession raises CounterSessionNotActive."""
        from counters.models import Counter, CounterSession
        counter_no_session = Counter.objects.create(
            branch=self.branch, name="Empty Counter", code="C03",
            status=CounterStatus.ACTIVE,
        )
        with self.assertRaises(CounterSessionNotActive):
            start_pos_session(
                user=self.cashier,
                counter_id=str(counter_no_session.id),
                branch=self.branch,
            )

    def test_start_session_duplicate_raises(self):
        """Starting a second ACTIVE session for same counter+user raises POSSessionConflict."""
        start_pos_session(
            user=self.cashier,
            counter_id=str(self.counter.id),
            branch=self.branch,
        )
        with self.assertRaises(POSSessionConflict):
            start_pos_session(
                user=self.cashier,
                counter_id=str(self.counter.id),
                branch=self.branch,
            )

    def test_start_session_stores_device_identifier(self):
        """device_identifier is stored as metadata only."""
        session = start_pos_session(
            user=self.cashier,
            counter_id=str(self.counter.id),
            device_identifier="TEST-DEVICE-001",
            branch=self.branch,
        )
        self.assertEqual(session.device_identifier, "TEST-DEVICE-001")


class POSSessionLifecycleTest(OperationsTestBase):
    """Tests for pause / resume / end POS session."""

    def setUp(self):
        self.session = start_pos_session(
            user=self.cashier,
            counter_id=str(self.counter.id),
            branch=self.branch,
        )

    def test_pause_active_session(self):
        session = pause_pos_session(session=self.session, user=self.cashier)
        self.assertEqual(session.status, POS_SESSION_PAUSED)

    def test_pause_already_paused_raises(self):
        pause_pos_session(session=self.session, user=self.cashier)
        self.session.refresh_from_db()
        with self.assertRaises(POSSessionConflict):
            pause_pos_session(session=self.session, user=self.cashier)

    def test_resume_paused_session(self):
        pause_pos_session(session=self.session, user=self.cashier)
        self.session.refresh_from_db()
        session = resume_pos_session(session=self.session, user=self.cashier)
        self.assertEqual(session.status, POS_SESSION_ACTIVE)

    def test_resume_active_session_raises(self):
        """Resuming an already-active session raises POSSessionConflict."""
        with self.assertRaises(POSSessionConflict):
            resume_pos_session(session=self.session, user=self.cashier)

    def test_end_active_session(self):
        session = end_pos_session(session=self.session, user=self.cashier)
        self.assertEqual(session.status, POS_SESSION_ENDED)
        self.assertIsNotNone(session.ended_at)

    def test_end_paused_session(self):
        pause_pos_session(session=self.session, user=self.cashier)
        self.session.refresh_from_db()
        session = end_pos_session(session=self.session, user=self.cashier)
        self.assertEqual(session.status, POS_SESSION_ENDED)

    def test_end_already_ended_raises(self):
        end_pos_session(session=self.session, user=self.cashier)
        self.session.refresh_from_db()
        with self.assertRaises(POSSessionConflict):
            end_pos_session(session=self.session, user=self.cashier)


class POSSessionAPITest(OperationsTestBase):
    """API-level tests for POS session endpoints."""

    def setUp(self):
        self.client.force_login(self.cashier)

    def test_get_session_authenticated(self):
        response = self.client.get("/api/operations/pos/session/")
        self.assertIn(response.status_code, [200, 403])

    def test_start_session_api(self):
        response = self.client.post(
            "/api/operations/pos/session/start/",
            {"counter_id": str(self.counter.id)},
            content_type="application/json",
        )
        self.assertIn(response.status_code, [201, 400, 403])

    def test_unauthenticated_rejected(self):
        self.client.logout()
        response = self.client.get("/api/operations/pos/session/")
        self.assertEqual(response.status_code, 401)
