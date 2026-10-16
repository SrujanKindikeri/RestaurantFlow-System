# =============================================================================
# RestaurantFlow — Enterprise Schedule Tests
# Phase 20
#
# Tests:
#   - Normal operating hour upsert
#   - Overnight schedule (closing < opening)
#   - Closed day
#   - Overlapping closure detection
#   - Closure approval / rejection / cancellation workflow
# =============================================================================

from datetime import time
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
import datetime

from enterprise.tests.base import EnterpriseTestBase
from enterprise.schedule_services import (
    upsert_operating_hour, bulk_upsert_operating_hours,
    create_branch_closure, approve_branch_closure,
    reject_branch_closure, cancel_branch_closure,
)
from enterprise.models import BranchOperatingHour, BranchClosure
from enterprise.constants import (
    DAY_MONDAY, DAY_TUESDAY, DAY_SUNDAY,
    CLOSURE_TYPE_HOLIDAY, CLOSURE_STATUS_APPROVED,
    CLOSURE_STATUS_REJECTED, CLOSURE_STATUS_CANCELLED,
)


class TestOperatingHours(EnterpriseTestBase):

    def test_create_normal_schedule(self):
        hour = upsert_operating_hour(
            branch=self.branch_a1,
            day_of_week=DAY_MONDAY,
            opening_time=time(9, 0),
            closing_time=time(22, 0),
            is_closed=False,
            user=self.branch_manager,
        )
        self.assertFalse(hour.is_overnight)
        self.assertEqual(hour.opening_time, time(9, 0))

    def test_overnight_schedule(self):
        """18:00 → 02:00 should be detected as overnight."""
        hour = upsert_operating_hour(
            branch=self.branch_a1,
            day_of_week=DAY_SUNDAY,
            opening_time=time(18, 0),
            closing_time=time(2, 0),
            is_closed=False,
            user=self.branch_manager,
        )
        self.assertTrue(hour.is_overnight)

    def test_closed_day(self):
        hour = upsert_operating_hour(
            branch=self.branch_a1,
            day_of_week=DAY_TUESDAY,
            opening_time=None,
            closing_time=None,
            is_closed=True,
            user=self.branch_manager,
        )
        self.assertTrue(hour.is_closed)

    def test_upsert_updates_existing(self):
        upsert_operating_hour(
            branch=self.branch_a1,
            day_of_week=DAY_MONDAY,
            opening_time=time(9, 0),
            closing_time=time(17, 0),
            is_closed=False,
            user=self.branch_manager,
        )
        updated = upsert_operating_hour(
            branch=self.branch_a1,
            day_of_week=DAY_MONDAY,
            opening_time=time(10, 0),
            closing_time=time(20, 0),
            is_closed=False,
            user=self.branch_manager,
        )
        self.assertEqual(updated.opening_time, time(10, 0))
        # Only one row per day
        self.assertEqual(
            BranchOperatingHour.objects.filter(
                branch=self.branch_a1, day_of_week=DAY_MONDAY
            ).count(),
            1,
        )

    def test_missing_opening_time_raises(self):
        with self.assertRaises(ValidationError):
            upsert_operating_hour(
                branch=self.branch_a1,
                day_of_week=DAY_MONDAY,
                opening_time=None,
                closing_time=time(18, 0),
                is_closed=False,
                user=self.branch_manager,
            )

    def test_unauthorized_user_raises(self):
        with self.assertRaises(PermissionDenied):
            upsert_operating_hour(
                branch=self.branch_a1,
                day_of_week=DAY_MONDAY,
                opening_time=time(9, 0),
                closing_time=time(18, 0),
                is_closed=False,
                user=self.other_org_user,
            )

    def test_bulk_upsert_creates_all_days(self):
        from enterprise.constants import (
            DAY_WEDNESDAY, DAY_THURSDAY, DAY_FRIDAY, DAY_SATURDAY
        )
        days = [DAY_MONDAY, DAY_TUESDAY, DAY_WEDNESDAY, DAY_THURSDAY, DAY_FRIDAY]
        hours_data = [
            {"day_of_week": d, "opening_time": time(9, 0), "closing_time": time(21, 0), "is_closed": False}
            for d in days
        ]
        results = bulk_upsert_operating_hours(self.branch_a1, hours_data, self.branch_manager)
        self.assertEqual(len(results), len(days))


class TestBranchClosure(EnterpriseTestBase):

    def _future_range(self, days_from_now=7, duration_days=2):
        now = timezone.now()
        start = now + datetime.timedelta(days=days_from_now)
        end = start + datetime.timedelta(days=duration_days)
        return start, end

    def test_create_closure(self):
        start, end = self._future_range()
        closure = create_branch_closure(
            branch=self.branch_a1,
            closure_type=CLOSURE_TYPE_HOLIDAY,
            start_datetime=start,
            end_datetime=end,
            reason="Diwali holiday",
            user=self.branch_manager,
        )
        self.assertIsNotNone(closure.pk)
        self.assertEqual(closure.closure_type, CLOSURE_TYPE_HOLIDAY)

    def test_overlapping_closure_raises(self):
        start, end = self._future_range(days_from_now=10)
        create_branch_closure(
            branch=self.branch_a1,
            closure_type=CLOSURE_TYPE_HOLIDAY,
            start_datetime=start,
            end_datetime=end,
            reason="First closure",
            user=self.branch_manager,
            auto_approve=True,
        )
        # Overlapping range
        overlap_start = start + datetime.timedelta(days=1)
        overlap_end = end + datetime.timedelta(days=1)
        with self.assertRaises(ValidationError):
            create_branch_closure(
                branch=self.branch_a1,
                closure_type=CLOSURE_TYPE_HOLIDAY,
                start_datetime=overlap_start,
                end_datetime=overlap_end,
                reason="Overlapping closure",
                user=self.branch_manager,
            )

    def test_end_before_start_raises(self):
        now = timezone.now()
        with self.assertRaises(ValidationError):
            create_branch_closure(
                branch=self.branch_a1,
                closure_type=CLOSURE_TYPE_HOLIDAY,
                start_datetime=now + datetime.timedelta(days=5),
                end_datetime=now + datetime.timedelta(days=2),
                reason="invalid dates",
                user=self.branch_manager,
            )

    def test_approve_closure(self):
        start, end = self._future_range(days_from_now=20)
        closure = create_branch_closure(
            branch=self.branch_a1,
            closure_type=CLOSURE_TYPE_HOLIDAY,
            start_datetime=start,
            end_datetime=end,
            reason="approval test",
            user=self.branch_manager,
        )
        approved = approve_branch_closure(closure, self.restaurant_owner)
        self.assertEqual(approved.status, CLOSURE_STATUS_APPROVED)
        self.assertEqual(approved.approved_by, self.restaurant_owner)

    def test_reject_closure(self):
        start, end = self._future_range(days_from_now=30)
        closure = create_branch_closure(
            branch=self.branch_a1,
            closure_type=CLOSURE_TYPE_HOLIDAY,
            start_datetime=start,
            end_datetime=end,
            reason="rejection test",
            user=self.branch_manager,
        )
        rejected = reject_branch_closure(closure, self.restaurant_owner, "Not approved")
        self.assertEqual(rejected.status, CLOSURE_STATUS_REJECTED)
        self.assertEqual(rejected.rejection_reason, "Not approved")

    def test_cancel_closure(self):
        start, end = self._future_range(days_from_now=40)
        closure = create_branch_closure(
            branch=self.branch_a1,
            closure_type=CLOSURE_TYPE_HOLIDAY,
            start_datetime=start,
            end_datetime=end,
            reason="cancel test",
            user=self.branch_manager,
        )
        cancelled = cancel_branch_closure(closure, self.branch_manager)
        self.assertEqual(cancelled.status, CLOSURE_STATUS_CANCELLED)

    def test_closure_not_deleted_after_cancel(self):
        """Closures must be soft-cancelled, not deleted."""
        start, end = self._future_range(days_from_now=50)
        closure = create_branch_closure(
            branch=self.branch_a1,
            closure_type=CLOSURE_TYPE_HOLIDAY,
            start_datetime=start,
            end_datetime=end,
            reason="soft cancel test",
            user=self.branch_manager,
        )
        cancel_branch_closure(closure, self.branch_manager)
        self.assertTrue(BranchClosure.objects.filter(pk=closure.pk).exists())

    def test_unauthorized_create_raises(self):
        start, end = self._future_range(days_from_now=60)
        with self.assertRaises(PermissionDenied):
            create_branch_closure(
                branch=self.branch_a1,
                closure_type=CLOSURE_TYPE_HOLIDAY,
                start_datetime=start,
                end_datetime=end,
                reason="test",
                user=self.other_org_user,
            )
