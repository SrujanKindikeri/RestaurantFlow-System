# =============================================================================
# RestaurantFlow — Reporting Validators
# Phase 14
# =============================================================================

import logging
from datetime import date, timedelta
from decimal import Decimal

from reporting.exceptions import (
    InvalidDateRangeError,
    InvalidFilterError,
    DateRangeTooLargeError,
    ReportScopeError,
)

logger = logging.getLogger("reporting")

# Maximum date range allowed (2 years)
MAX_DATE_RANGE_DAYS = 730


def validate_date_range(date_from, date_to):
    """
    Validate that date_from <= date_to and the range is within bounds.

    Both may be None; if so, this is a no-op.
    Returns (date_from, date_to) after validation.
    """
    if date_from is None and date_to is None:
        return date_from, date_to

    today = date.today()

    if date_from is None:
        date_from = today - timedelta(days=30)

    if date_to is None:
        date_to = today

    if date_from > date_to:
        raise InvalidDateRangeError(
            f"date_from ({date_from}) must be before or equal to date_to ({date_to})."
        )

    delta = (date_to - date_from).days
    if delta > MAX_DATE_RANGE_DAYS:
        raise DateRangeTooLargeError(
            f"Date range spans {delta} days. Maximum allowed is {MAX_DATE_RANGE_DAYS} days."
        )

    return date_from, date_to


def validate_top_n(value, max_value=100, default=10):
    """
    Validate and clamp a 'top N' limit parameter.
    Returns a clean integer.
    """
    if value is None:
        return default
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise InvalidFilterError(f"'limit' must be a positive integer, got: {value}")
    if n < 1:
        raise InvalidFilterError("'limit' must be at least 1.")
    return min(n, max_value)


def validate_branch_in_scope(branch, accessible_branches):
    """
    Validate that the requested branch is within the user's accessible branches.
    Raises ReportScopeError if not.
    """
    if branch is not None:
        if not accessible_branches.filter(pk=branch.pk).exists():
            raise ReportScopeError(
                "The requested branch is not within your authorized scope."
            )


def validate_restaurant_in_scope(restaurant, accessible_restaurants):
    """
    Validate that the requested restaurant is within the user's accessible restaurants.
    """
    if restaurant is not None:
        if not accessible_restaurants.filter(pk=restaurant.pk).exists():
            raise ReportScopeError(
                "The requested restaurant is not within your authorized scope."
            )


def validate_granularity(granularity):
    """Validate trend granularity parameter."""
    from reporting.constants import TREND_DAILY, TREND_WEEKLY, TREND_MONTHLY
    valid = {TREND_DAILY, TREND_WEEKLY, TREND_MONTHLY}
    if granularity not in valid:
        raise InvalidFilterError(
            f"Invalid granularity '{granularity}'. Must be one of: {', '.join(sorted(valid))}."
        )
