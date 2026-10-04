# =============================================================================
# RestaurantFlow — Reporting Filters
# Phase 14
#
# Reusable filter parameter parsers for reporting views.
# These parse and validate query-string parameters, returning clean Python
# objects ready for use in selectors and aggregations.
#
# Usage in views:
#   params = ReportFilterParams.from_request(request)
# =============================================================================

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from reporting.validators import validate_date_range, validate_top_n
from reporting.exceptions import InvalidFilterError

logger = logging.getLogger("reporting")


def _parse_date(value: str, param_name: str) -> Optional[date]:
    """Parse a date string (YYYY-MM-DD). Returns None if value is None/empty."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise InvalidFilterError(
            f"'{param_name}' must be a valid date in YYYY-MM-DD format. Got: {value}"
        )


def _parse_uuid(value: str, param_name: str) -> Optional[str]:
    """Parse a UUID string. Returns None if empty. Does not query DB."""
    if not value:
        return None
    import uuid as _uuid
    try:
        return str(_uuid.UUID(str(value)))
    except (ValueError, AttributeError):
        raise InvalidFilterError(
            f"'{param_name}' must be a valid UUID. Got: {value}"
        )


@dataclass
class ReportFilterParams:
    """
    Parsed and validated filter parameters for any reporting endpoint.

    All date fields are date objects (not strings).
    All ID fields are UUID strings (not model instances — resolution happens
    in the access layer).
    """
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    restaurant_id: Optional[str] = None
    branch_id: Optional[str] = None
    counter_id: Optional[str] = None
    order_type: Optional[str] = None
    payment_method: Optional[str] = None
    menu_category_id: Optional[str] = None
    menu_item_id: Optional[str] = None
    waiter_id: Optional[str] = None
    cashier_id: Optional[str] = None
    expense_category_id: Optional[str] = None
    supplier_id: Optional[str] = None
    inventory_item_id: Optional[str] = None
    granularity: str = "daily"
    limit: int = 10
    sort_by: str = "revenue"

    @classmethod
    def from_request(cls, request) -> "ReportFilterParams":
        """
        Parse query parameters from a DRF request object.
        Validates types and ranges but does NOT validate business scope here
        (scope validation happens in the access layer per request).
        """
        qp = request.query_params

        # Date range
        date_from = _parse_date(qp.get("date_from"), "date_from")
        date_to   = _parse_date(qp.get("date_to"), "date_to")

        # Apply default range if neither is provided
        if date_from is None and date_to is None:
            date_to   = date.today()
            date_from = date_to - timedelta(days=29)

        date_from, date_to = validate_date_range(date_from, date_to)

        # Scope IDs — validated for format only here
        restaurant_id     = _parse_uuid(qp.get("restaurant_id"), "restaurant_id")
        branch_id         = _parse_uuid(qp.get("branch_id"), "branch_id")
        counter_id        = _parse_uuid(qp.get("counter_id"), "counter_id")
        menu_category_id  = _parse_uuid(qp.get("menu_category_id"), "menu_category_id")
        menu_item_id      = _parse_uuid(qp.get("menu_item_id"), "menu_item_id")
        waiter_id         = _parse_uuid(qp.get("waiter_id"), "waiter_id")
        cashier_id        = _parse_uuid(qp.get("cashier_id"), "cashier_id")
        expense_category_id = _parse_uuid(qp.get("expense_category_id"), "expense_category_id")
        supplier_id       = _parse_uuid(qp.get("supplier_id"), "supplier_id")
        inventory_item_id = _parse_uuid(qp.get("inventory_item_id"), "inventory_item_id")

        # Enum filters — format-only validation; value validation is in selectors
        order_type     = qp.get("order_type") or None
        payment_method = qp.get("payment_method") or None

        # Granularity
        granularity = qp.get("granularity", "daily").lower()

        # Top-N limit
        limit = validate_top_n(qp.get("limit", 10), max_value=200, default=10)

        # Sort by
        sort_by = qp.get("sort_by", "revenue")

        return cls(
            date_from=date_from,
            date_to=date_to,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
            counter_id=counter_id,
            order_type=order_type,
            payment_method=payment_method,
            menu_category_id=menu_category_id,
            menu_item_id=menu_item_id,
            waiter_id=waiter_id,
            cashier_id=cashier_id,
            expense_category_id=expense_category_id,
            supplier_id=supplier_id,
            inventory_item_id=inventory_item_id,
            granularity=granularity,
            limit=limit,
            sort_by=sort_by,
        )

    def to_dict(self) -> dict:
        """Return a sanitised dict for audit/cache key purposes."""
        return {
            k: (v.isoformat() if isinstance(v, date) else v)
            for k, v in self.__dict__.items()
            if v is not None
        }
