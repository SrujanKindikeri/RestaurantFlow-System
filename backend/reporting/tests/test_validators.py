# =============================================================================
# RestaurantFlow — Reporting Validator Tests
# Phase 14
# =============================================================================

from datetime import date, timedelta
from django.test import TestCase

from reporting.validators import validate_date_range, validate_top_n
from reporting.exceptions import InvalidDateRangeError, InvalidFilterError, DateRangeTooLargeError
from reporting.filters import ReportFilterParams


class DateRangeValidatorTests(TestCase):

    def test_valid_range_passes(self):
        d_from = date.today() - timedelta(days=7)
        d_to = date.today()
        result_from, result_to = validate_date_range(d_from, d_to)
        self.assertEqual(result_from, d_from)
        self.assertEqual(result_to, d_to)

    def test_same_day_range_passes(self):
        today = date.today()
        validate_date_range(today, today)  # should not raise

    def test_inverted_range_raises(self):
        with self.assertRaises(InvalidDateRangeError):
            validate_date_range(date.today(), date.today() - timedelta(days=1))

    def test_none_none_returns_defaults(self):
        d_from, d_to = validate_date_range(None, None)
        self.assertIsNotNone(d_from)
        self.assertIsNotNone(d_to)
        self.assertLessEqual(d_from, d_to)

    def test_too_large_range_raises(self):
        with self.assertRaises(DateRangeTooLargeError):
            validate_date_range(
                date.today() - timedelta(days=800),
                date.today(),
            )


class TopNValidatorTests(TestCase):

    def test_valid_n(self):
        self.assertEqual(validate_top_n(10), 10)

    def test_default_when_none(self):
        self.assertEqual(validate_top_n(None, default=10), 10)

    def test_clamp_to_max(self):
        result = validate_top_n(9999, max_value=100)
        self.assertEqual(result, 100)

    def test_invalid_value_raises(self):
        with self.assertRaises(InvalidFilterError):
            validate_top_n("abc")

    def test_zero_raises(self):
        with self.assertRaises(InvalidFilterError):
            validate_top_n(0)


class ReportFilterParamsTests(TestCase):

    def _mock_request(self, params):
        from unittest.mock import MagicMock
        req = MagicMock()
        req.query_params = params
        return req

    def test_defaults_applied(self):
        req = self._mock_request({})
        params = ReportFilterParams.from_request(req)
        self.assertIsNotNone(params.date_from)
        self.assertIsNotNone(params.date_to)
        self.assertEqual(params.granularity, "daily")
        self.assertEqual(params.limit, 10)

    def test_date_parsing(self):
        req = self._mock_request({
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        })
        params = ReportFilterParams.from_request(req)
        self.assertEqual(params.date_from, date(2026, 1, 1))
        self.assertEqual(params.date_to, date(2026, 1, 31))

    def test_invalid_date_raises(self):
        req = self._mock_request({"date_from": "not-a-date"})
        with self.assertRaises(InvalidFilterError):
            ReportFilterParams.from_request(req)

    def test_invalid_uuid_raises(self):
        req = self._mock_request({"branch_id": "not-a-uuid"})
        with self.assertRaises(InvalidFilterError):
            ReportFilterParams.from_request(req)

    def test_to_dict_serializable(self):
        req = self._mock_request({
            "date_from": "2026-01-01",
            "date_to": "2026-01-31",
        })
        params = ReportFilterParams.from_request(req)
        d = params.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("date_from", d)
        # All values should be strings for JSON serialisation
        for v in d.values():
            self.assertIsInstance(v, (str, int, float, type(None)))
