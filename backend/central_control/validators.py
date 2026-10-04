# =============================================================================
# RestaurantFlow — Central Control Center Validators
# Phase 15
# =============================================================================

from decimal import Decimal
from django.core.exceptions import ValidationError

from central_control.constants import (
    ALERT_VALID_TRANSITIONS,
    ISSUE_VALID_TRANSITIONS,
    ALERT_STATUS_CHOICES,
    ISSUE_STATUS_CHOICES,
    ISSUE_SEVERITY_CRITICAL,
)


def validate_alert_transition(current_status: str, new_status: str) -> None:
    """
    Validate that the given alert status transition is allowed.
    Raises ValidationError if invalid.
    """
    allowed = ALERT_VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition alert from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {allowed or 'none (terminal state)'}."
        )


def validate_issue_transition(current_status: str, new_status: str) -> None:
    """
    Validate that the given issue status transition is allowed.
    Raises ValidationError if invalid.
    """
    allowed = ISSUE_VALID_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition issue from '{current_status}' to '{new_status}'. "
            f"Allowed transitions: {allowed or 'none (terminal state)'}."
        )


def validate_resolution_note_for_critical(severity: str, resolution_note: str) -> None:
    """
    Critical issues must include a non-empty resolution note.
    Raises ValidationError if the condition is violated.
    """
    if severity == ISSUE_SEVERITY_CRITICAL:
        if not resolution_note or not resolution_note.strip():
            raise ValidationError(
                "A resolution note is required when resolving or closing a CRITICAL issue."
            )


def validate_kitchen_delay_minutes(value: int) -> None:
    """Kitchen delay threshold must be a positive integer (1–480 minutes)."""
    if not isinstance(value, int) or value < 1 or value > 480:
        raise ValidationError(
            "Kitchen delay threshold must be an integer between 1 and 480 minutes."
        )


def validate_backlog_threshold(value: int) -> None:
    """Kitchen backlog threshold must be 1–500 orders."""
    if not isinstance(value, int) or value < 1 or value > 500:
        raise ValidationError(
            "Kitchen backlog threshold must be an integer between 1 and 500."
        )


def validate_payment_failure_threshold(value: int) -> None:
    """Payment failure threshold must be 1–1000."""
    if not isinstance(value, int) or value < 1 or value > 1000:
        raise ValidationError(
            "Payment failure threshold must be an integer between 1 and 1000."
        )


def validate_non_negative_threshold(value, field_name: str = "value") -> None:
    """Generic validator for fields that must be >= 0."""
    if value is None:
        return
    try:
        dec = Decimal(str(value))
    except Exception:
        raise ValidationError(f"{field_name} must be a valid number.")
    if dec < Decimal("0"):
        raise ValidationError(f"{field_name} cannot be negative.")


def validate_settings_thresholds(data: dict) -> None:
    """
    Validate all CentralControlSettings fields in one pass.
    Raises ValidationError listing all problems found.
    """
    errors = {}

    kitchen_delay = data.get("kitchen_delay_minutes")
    if kitchen_delay is not None:
        try:
            validate_kitchen_delay_minutes(int(kitchen_delay))
        except (ValidationError, ValueError, TypeError) as exc:
            errors["kitchen_delay_minutes"] = str(exc)

    backlog = data.get("kitchen_backlog_threshold")
    if backlog is not None:
        try:
            validate_backlog_threshold(int(backlog))
        except (ValidationError, ValueError, TypeError) as exc:
            errors["kitchen_backlog_threshold"] = str(exc)

    failure_thresh = data.get("payment_failure_threshold")
    if failure_thresh is not None:
        try:
            validate_payment_failure_threshold(int(failure_thresh))
        except (ValidationError, ValueError, TypeError) as exc:
            errors["payment_failure_threshold"] = str(exc)

    if errors:
        raise ValidationError(errors)
