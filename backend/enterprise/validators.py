# =============================================================================
# RestaurantFlow — Enterprise Validators
# Phase 20
#
# Pure validation functions — no DB access, no side effects.
# Called from model.clean(), serializers, and service functions.
# =============================================================================

import json
import logging
from decimal import Decimal, InvalidOperation

from enterprise.constants import (
    VALUE_TYPE_STRING,
    VALUE_TYPE_INTEGER,
    VALUE_TYPE_DECIMAL,
    VALUE_TYPE_BOOLEAN,
    VALUE_TYPE_JSON,
    ALLOWED_CONFIGURATION_KEYS,
)
from enterprise.exceptions import (
    ConfigurationKeyNotAllowedError,
    ConfigurationValueTypeError,
)

logger = logging.getLogger("enterprise")

# ---------------------------------------------------------------------------
# Configuration key validation
# ---------------------------------------------------------------------------

def validate_configuration_key(key: str) -> None:
    """
    Raise ConfigurationKeyNotAllowedError if the key is not in the allow-list.
    """
    if key not in ALLOWED_CONFIGURATION_KEYS:
        raise ConfigurationKeyNotAllowedError(
            f"Configuration key '{key}' is not permitted. "
            f"Allowed keys: {sorted(ALLOWED_CONFIGURATION_KEYS.keys())}",
        )


# ---------------------------------------------------------------------------
# Configuration value type validation
# ---------------------------------------------------------------------------

def validate_configuration_value(value: str, value_type: str) -> None:
    """
    Verify that `value` (a string) is parseable as `value_type`.

    Does NOT return the parsed value — just validates correctness.
    Raises ConfigurationValueTypeError if the value cannot be parsed.
    """
    if value_type == VALUE_TYPE_STRING:
        # Any string is valid
        return

    if value_type == VALUE_TYPE_INTEGER:
        try:
            int(value)
        except (ValueError, TypeError):
            raise ConfigurationValueTypeError(
                f"Value '{value}' cannot be parsed as INTEGER."
            )
        return

    if value_type == VALUE_TYPE_DECIMAL:
        try:
            Decimal(value)
        except (InvalidOperation, TypeError):
            raise ConfigurationValueTypeError(
                f"Value '{value}' cannot be parsed as DECIMAL."
            )
        return

    if value_type == VALUE_TYPE_BOOLEAN:
        if value.lower() not in {"true", "false", "1", "0", "yes", "no"}:
            raise ConfigurationValueTypeError(
                f"Value '{value}' cannot be parsed as BOOLEAN. "
                "Accepted: true, false, 1, 0, yes, no."
            )
        return

    if value_type == VALUE_TYPE_JSON:
        try:
            json.loads(value)
        except (json.JSONDecodeError, TypeError):
            raise ConfigurationValueTypeError(
                f"Value '{value}' is not valid JSON."
            )
        return

    raise ConfigurationValueTypeError(
        f"Unknown value_type '{value_type}'."
    )


def cast_configuration_value(value: str, value_type: str):
    """
    Parse and return `value` cast to the appropriate Python type.

    Returns:
        str, int, Decimal, bool, or parsed JSON (dict/list).
    Raises:
        ConfigurationValueTypeError if parsing fails.
    """
    if value_type == VALUE_TYPE_STRING:
        return value

    if value_type == VALUE_TYPE_INTEGER:
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ConfigurationValueTypeError(
                f"Cannot cast '{value}' to INTEGER."
            )

    if value_type == VALUE_TYPE_DECIMAL:
        try:
            return Decimal(value)
        except (InvalidOperation, TypeError):
            raise ConfigurationValueTypeError(
                f"Cannot cast '{value}' to DECIMAL."
            )

    if value_type == VALUE_TYPE_BOOLEAN:
        return value.lower() in {"true", "1", "yes"}

    if value_type == VALUE_TYPE_JSON:
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            raise ConfigurationValueTypeError(
                f"Cannot parse '{value}' as JSON."
            )

    raise ConfigurationValueTypeError(f"Unknown value_type '{value_type}'.")


# ---------------------------------------------------------------------------
# Operating hour validation
# ---------------------------------------------------------------------------

def validate_operating_hours(
    branch_id,
    day_of_week: str,
    opening_time,
    closing_time,
    is_closed: bool,
    exclude_pk=None,
) -> None:
    """
    Validate that operating hours for (branch, day_of_week) do not conflict.

    Since each (branch, day_of_week) pair is enforced as unique via DB
    constraint, this validator only checks logical consistency:
    - If is_closed=False, both opening and closing times are required.
    - opening_time != closing_time (unless intentionally all-day).
    """
    if is_closed:
        return

    if not opening_time:
        raise ValueError("Opening time is required when branch is open on this day.")
    if not closing_time:
        raise ValueError("Closing time is required when branch is open on this day.")
    if opening_time == closing_time:
        raise ValueError("Opening and closing times cannot be identical.")


# ---------------------------------------------------------------------------
# Closure schedule overlap detection
# ---------------------------------------------------------------------------

def validate_no_closure_overlap(branch_id, start_datetime, end_datetime, exclude_pk=None) -> None:
    """
    Raise ValueError if the given datetime range overlaps with any approved
    or active closure for the branch.

    Excludes terminal statuses (COMPLETED, CANCELLED, REJECTED).
    """
    from enterprise.models import BranchClosure
    from enterprise.constants import (
        CLOSURE_STATUS_COMPLETED,
        CLOSURE_STATUS_CANCELLED,
        CLOSURE_STATUS_REJECTED,
    )

    qs = BranchClosure.objects.filter(
        branch_id=branch_id,
        start_datetime__lt=end_datetime,
        end_datetime__gt=start_datetime,
    ).exclude(
        status__in=[
            CLOSURE_STATUS_COMPLETED,
            CLOSURE_STATUS_CANCELLED,
            CLOSURE_STATUS_REJECTED,
        ]
    )
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)

    if qs.exists():
        overlap = qs.first()
        raise ValueError(
            f"This closure period overlaps with an existing closure: "
            f"{overlap.closure_type} "
            f"({overlap.start_datetime.strftime('%Y-%m-%d %H:%M')} → "
            f"{overlap.end_datetime.strftime('%Y-%m-%d %H:%M')})."
        )


# ---------------------------------------------------------------------------
# Price validation
# ---------------------------------------------------------------------------

def validate_price(price) -> None:
    """Raise ValueError if price is negative."""
    try:
        price = Decimal(str(price))
    except (InvalidOperation, TypeError):
        raise ValueError(f"Invalid price value: {price}.")
    if price < 0:
        raise ValueError("Price cannot be negative.")


# ---------------------------------------------------------------------------
# Transfer scope validation
# ---------------------------------------------------------------------------

def validate_transfer_scope(source_branch, destination_branch, user) -> None:
    """
    Raise appropriate errors if a staff transfer is cross-restaurant or
    the branches are the same.
    """
    from enterprise.exceptions import StaffTransferScopeError

    if source_branch.pk == destination_branch.pk:
        raise StaffTransferScopeError(
            "Source and destination branches must be different.",
            code="TRANSFER_SAME_BRANCH",
        )

    if str(source_branch.restaurant_id) != str(destination_branch.restaurant_id):
        raise StaffTransferScopeError(
            "Staff transfers must be within the same restaurant. "
            "Cross-restaurant transfers are not permitted.",
            code="TRANSFER_CROSS_RESTAURANT",
        )
