# =============================================================================
# RestaurantFlow — Notifications Validators
# Phase 16
# =============================================================================

import re
import logging

from notifications.constants import (
    NOTIFICATION_TYPE_CHOICES,
    SEVERITY_CHOICES,
    CHANNEL_CHOICES,
    SAFE_TEMPLATE_VARS,
)
from notifications.exceptions import (
    NotificationError,
    InvalidTemplateVariable,
)

logger = logging.getLogger("notifications")

# All valid values as sets for O(1) lookup
_VALID_TYPES    = {code for code, _ in NOTIFICATION_TYPE_CHOICES}
_VALID_SEVERITY = {code for code, _ in SEVERITY_CHOICES}
_VALID_CHANNELS = {code for code, _ in CHANNEL_CHOICES}

# Matches {{variable_name}} tokens in templates
_TEMPLATE_VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


def validate_notification_type(value: str) -> str:
    if value not in _VALID_TYPES:
        raise NotificationError(f"Invalid notification_type: {value!r}")
    return value


def validate_severity(value: str) -> str:
    if value not in _VALID_SEVERITY:
        raise NotificationError(f"Invalid severity: {value!r}")
    return value


def validate_channel(value: str) -> str:
    if value not in _VALID_CHANNELS:
        raise NotificationError(f"Invalid channel: {value!r}")
    return value


def validate_template_variables(template_text: str) -> list[str]:
    """
    Parse template_text for {{variable}} tokens.

    Returns the list of variable names found.
    Raises InvalidTemplateVariable if any variable is not in the allow-list.
    Never allows arbitrary Python or unsafe execution.
    """
    found = _TEMPLATE_VAR_RE.findall(template_text)
    for var in found:
        if var not in SAFE_TEMPLATE_VARS:
            raise InvalidTemplateVariable(
                f"Template variable '{var}' is not allowed. "
                f"Allowed variables: {sorted(SAFE_TEMPLATE_VARS)}"
            )
    return found


def render_template(template_text: str, context: dict) -> str:
    """
    Safely render a template by substituting {{variable}} tokens.

    Only variables that are in SAFE_TEMPLATE_VARS and present in context
    are substituted. Unknown variables are left as-is (not silently dropped).
    No eval() or arbitrary code execution.
    """
    validate_template_variables(template_text)

    def _replace(match):
        var = match.group(1).strip()
        val = context.get(var, match.group(0))  # leave {{var}} if not in context
        return str(val)

    return _TEMPLATE_VAR_RE.sub(_replace, template_text)


def validate_action_url(url: str) -> str:
    """
    Validate that an action_url is either empty, a relative path, or HTTPS.
    Rejects javascript: and data: URIs.
    """
    if not url:
        return url
    url = url.strip()
    lower = url.lower()
    if lower.startswith("javascript:") or lower.startswith("data:"):
        raise NotificationError(f"Unsafe action_url: {url!r}")
    return url


def validate_email_address(email: str) -> bool:
    """
    Basic email format validation.
    Returns True if the email looks valid, False otherwise.
    Does NOT perform DNS lookup.
    """
    pattern = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
    return bool(pattern.match(email.strip()))


def validate_phone_number(phone: str) -> bool:
    """
    Basic international phone number validation.
    Accepts E.164 format (+CountryCode + digits).
    Returns True if plausibly valid.
    """
    if not phone:
        return False
    pattern = re.compile(r"^\+?[1-9]\d{6,14}$")
    return bool(pattern.match(phone.strip().replace(" ", "").replace("-", "")))
