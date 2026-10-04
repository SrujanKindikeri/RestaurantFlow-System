# =============================================================================
# RestaurantFlow — Accounting Period Tests
# Phase 13
# =============================================================================

import uuid
from datetime import date, timedelta

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from accounting.tests.base import AccountingTestBase
from accounting.services import PeriodService
from accounting.exceptions import PeriodOverlapError, ClosedPeriodError, NoPeriodFoundError
from accounting.constants import PERIOD_OPEN, PERIOD_CLOSE_REQUESTED, PERIOD_CLOSED


class PeriodCreateTests(AccountingTestBase):

    def test_create_period_success(self):
        today = date.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        period = PeriodService.create_period(
            restaurant=self.restaurant,
            name="Next Month",
            start_date=next_month,
            end_date=next_month + timedelta(days=30),
            user=self.user,
        )
        self.assertEqual(period.status, PERIOD_OPEN)
        self.assertEqual(period.restaurant, self.restaurant)

    def test_overlapping_periods_rejected(self):
        """Cannot create a period that overlaps with an existing one."""
        today = date.today()
        with self.assertRaises(PeriodOverlapError):
            PeriodService.create_period(
                restaurant=self.restaurant,
                name="Overlapping",
                start_date=today,  # overlaps with cls.period
                end_date=today + timedelta(days=5),
                user=self.user,
            )

    def test_get_period_for_date_success(self):
        period = PeriodService.get_period_for_date(self.restaurant, date.today())
        self.assertEqual(period, self.period)

    def test_get_period_for_date_not_found(self):
        with self.assertRaises(NoPeriodFoundError):
            PeriodService.get_period_for_date(
                self.restaurant,
                date(1999, 1, 1),  # no period exists for this date
            )

    def test_start_date_must_be_before_end_date(self):
        with self.assertRaises((ValidationError, Exception)):
            PeriodService.create_period(
                restaurant=self.restaurant,
                name="Bad Dates",
                start_date=date(2030, 6, 30),
                end_date=date(2030, 6, 1),
                user=self.user,
            )


class PeriodCloseTests(AccountingTestBase):

    def test_request_period_close(self):
        today = date.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        period = PeriodService.create_period(
            restaurant=self.restaurant,
            name="To Close",
            start_date=next_month,
            end_date=next_month + timedelta(days=27),
            user=self.user,
        )
        period = PeriodService.request_period_close(period, self.user, "Ready to close")
        self.assertEqual(period.status, PERIOD_CLOSE_REQUESTED)

    def test_close_period_with_no_draft_entries(self):
        today = date.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        period = PeriodService.create_period(
            restaurant=self.restaurant,
            name="Clean Period",
            start_date=next_month,
            end_date=next_month + timedelta(days=27),
            user=self.user,
        )
        period = PeriodService.close_period(period, self.user, "Month end close")
        self.assertEqual(period.status, PERIOD_CLOSED)
        self.assertIsNotNone(period.closed_at)
        self.assertEqual(period.closed_by, self.user)

    def test_close_period_with_draft_entries_fails(self):
        """Cannot close a period that has unposted DRAFT journal entries."""
        # Create a DRAFT entry in cls.period
        self._make_journal_entry()
        with self.assertRaises(ValidationError):
            PeriodService.close_period(self.period, self.user)

    def test_reopen_closed_period(self):
        today = date.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        period = PeriodService.create_period(
            restaurant=self.restaurant,
            name="Will Reopen",
            start_date=next_month,
            end_date=next_month + timedelta(days=27),
            user=self.user,
        )
        period = PeriodService.close_period(period, self.user)
        self.assertEqual(period.status, PERIOD_CLOSED)

        period = PeriodService.reopen_period(period, self.user)
        self.assertEqual(period.status, PERIOD_OPEN)

    def test_cannot_reopen_open_period(self):
        today = date.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        period = PeriodService.create_period(
            restaurant=self.restaurant,
            name="Already Open",
            start_date=next_month,
            end_date=next_month + timedelta(days=27),
            user=self.user,
        )
        with self.assertRaises(ValidationError):
            PeriodService.reopen_period(period, self.user)

    def test_posting_to_closed_period_rejected(self):
        """Cannot post to a CLOSED period."""
        today = date.today()
        next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        period = PeriodService.create_period(
            restaurant=self.restaurant,
            name="Closed Period",
            start_date=next_month,
            end_date=next_month + timedelta(days=27),
            user=self.user,
        )
        PeriodService.close_period(period, self.user)

        from accounting.validators import validate_period_is_open
        with self.assertRaises(ClosedPeriodError):
            validate_period_is_open(period)
