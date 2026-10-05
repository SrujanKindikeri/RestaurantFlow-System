# =============================================================================
# RestaurantFlow — CRM Validators
# Phase 17
# =============================================================================

import re
import logging
from django.core.exceptions import ValidationError

logger = logging.getLogger("crm")


# ---------------------------------------------------------------------------
# Phone normalization / validation
# ---------------------------------------------------------------------------

def normalize_phone(phone: str) -> str:
    """
    Normalize a phone number to a consistent format for matching.

    - Strip whitespace, dashes, dots, parentheses
    - Preserve leading + for international numbers
    Returns the cleaned string or empty string if input is blank.
    """
    if not phone:
        return ""
    cleaned = re.sub(r"[\s\-\.\(\)]", "", phone.strip())
    return cleaned


def validate_phone(phone: str) -> str:
    """
    Validate and normalize a phone number.
    Raises ValidationError if format is obviously invalid.
    Returns normalized phone.
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return ""
    # Must be digits (with optional leading +), min 7, max 15 digits
    digit_part = normalized.lstrip("+")
    if not digit_part.isdigit():
        raise ValidationError(f"Invalid phone number format: {phone!r}")
    if len(digit_part) < 7 or len(digit_part) > 15:
        raise ValidationError(
            f"Phone number must be between 7 and 15 digits: {phone!r}"
        )
    return normalized


# ---------------------------------------------------------------------------
# Email normalization / validation
# ---------------------------------------------------------------------------

def normalize_email(email: str) -> str:
    """
    Normalize an email address: strip whitespace, lowercase.
    Returns empty string if blank.
    """
    if not email:
        return ""
    return email.strip().lower()


def validate_email(email: str) -> str:
    """
    Validate and normalize an email address.
    Returns normalized email or raises ValidationError.
    """
    normalized = normalize_email(email)
    if not normalized:
        return ""
    # Basic RFC-style check
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, normalized):
        raise ValidationError(f"Invalid email address: {email!r}")
    return normalized


# ---------------------------------------------------------------------------
# Rating validation
# ---------------------------------------------------------------------------

def validate_rating(value, field_name: str = "rating"):
    """Validate that a rating is between 1 and 5 inclusive."""
    if value is None:
        return
    if not isinstance(value, int) or value < 1 or value > 5:
        raise ValidationError(
            f"{field_name} must be an integer between 1 and 5."
        )


# ---------------------------------------------------------------------------
# Loyalty point validation
# ---------------------------------------------------------------------------

def validate_positive_points(points: int, field_name: str = "points"):
    """Validate that points are a positive integer."""
    if not isinstance(points, int) or points <= 0:
        raise ValidationError(f"{field_name} must be a positive integer.")


def validate_non_negative_balance(balance: int):
    """Validate that a loyalty balance is non-negative."""
    if balance < 0:
        raise ValidationError("Loyalty points balance cannot be negative.")


# ---------------------------------------------------------------------------
# Customer field validation
# ---------------------------------------------------------------------------

def validate_customer_number_format(number: str):
    """Validate that a customer number matches CUS-NNNNNN format."""
    if not re.match(r"^CUS-\d{6,}$", number):
        raise ValidationError(
            f"Customer number must follow CUS-NNNNNN format: {number!r}"
        )


def validate_feedback_order_ownership(customer, order):
    """
    Validate that an order is associated with the customer before allowing feedback.
    Raises ValidationError if the order does not belong to the customer.
    """
    if order is None:
        return  # anonymous feedback, no order to check
    if order.customer_id and str(order.customer_id) != str(customer.pk):
        raise ValidationError(
            "This order is not associated with this customer."
        )


def validate_loyalty_balance_integrity(balance_before: int, points: int, balance_after: int):
    """
    Validate that: balance_before + points == balance_after.
    Raises ValidationError if the accounting is off.
    """
    expected = balance_before + points
    if expected != balance_after:
        raise ValidationError(
            f"Loyalty balance integrity error: "
            f"{balance_before} + {points} = {expected}, not {balance_after}."
        )
