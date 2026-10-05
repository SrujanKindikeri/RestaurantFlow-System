# =============================================================================
# RestaurantFlow — Marketing Validators
# Phase 18
# =============================================================================

import re
from decimal import Decimal
from rest_framework.exceptions import ValidationError

from marketing.constants import (
    PROMO_PERCENTAGE_DISCOUNT, PROMO_FIXED_DISCOUNT,
    PROMO_FREE_ITEM, PROMO_BUY_X_GET_Y, PROMO_LOYALTY_BONUS,
    PROMO_CODE_MAX_LENGTH, CAMPAIGN_CODE_MAX_LENGTH,
)

SAFE_PLACEHOLDER_RE = re.compile(
    r"\{\{(customer_name|restaurant_name|promotion_code|reward_name|expiry_date)\}\}"
)
UNSAFE_TEMPLATE_RE = re.compile(r"\{%|%\}|\{\{(?!customer_name|restaurant_name|promotion_code|reward_name|expiry_date).*?\}\}")


def validate_campaign_code(code: str) -> str:
    """Normalize and validate a campaign code."""
    normalized = code.strip().upper()
    if not normalized:
        raise ValidationError({"code": "Campaign code cannot be empty."})
    if len(normalized) > CAMPAIGN_CODE_MAX_LENGTH:
        raise ValidationError(
            {"code": f"Campaign code must not exceed {CAMPAIGN_CODE_MAX_LENGTH} characters."}
        )
    if not re.match(r"^[A-Z0-9_\-]+$", normalized):
        raise ValidationError(
            {"code": "Campaign code may only contain letters, digits, underscores, and hyphens."}
        )
    return normalized


def validate_promotion_code(code: str) -> str:
    """Normalize and validate a promotion code."""
    if not code:
        return ""
    normalized = code.strip().upper()
    if len(normalized) > PROMO_CODE_MAX_LENGTH:
        raise ValidationError(
            {"code": f"Promotion code must not exceed {PROMO_CODE_MAX_LENGTH} characters."}
        )
    if not re.match(r"^[A-Z0-9_\-]+$", normalized):
        raise ValidationError(
            {"code": "Promotion code may only contain letters, digits, underscores, and hyphens."}
        )
    return normalized


def validate_message_body(body: str) -> str:
    """
    Validate that a message body contains only safe placeholders.

    Blocks: template tags, exec(), eval(), and arbitrary expressions.
    Allows: {{customer_name}}, {{restaurant_name}}, {{promotion_code}},
            {{reward_name}}, {{expiry_date}}
    """
    if UNSAFE_TEMPLATE_RE.search(body):
        raise ValidationError(
            {"body": "Message body contains unsafe template expressions."}
        )
    return body


def render_message(body: str, context: dict) -> str:
    """
    Safely render a message template with the given context.

    Only safe keys are substituted. Unknown placeholders are left as-is.
    Never uses eval() or exec().
    """
    safe_keys = {
        "customer_name", "restaurant_name",
        "promotion_code", "reward_name", "expiry_date",
    }
    result = body
    for key in safe_keys:
        value = context.get(key, f"{{{{{key}}}}}")
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


def validate_promotion_type_fields(data: dict):
    """Validate that promotion type-specific required fields are present."""
    promo_type = data.get("promotion_type")

    if promo_type in (PROMO_PERCENTAGE_DISCOUNT, PROMO_FIXED_DISCOUNT):
        if not data.get("discount_value"):
            raise ValidationError({"discount_value": "Required for this promotion type."})
        if not data.get("discount_type"):
            raise ValidationError({"discount_type": "Required for this promotion type."})
        dv = Decimal(str(data["discount_value"]))
        if dv <= 0:
            raise ValidationError({"discount_value": "Must be greater than zero."})
        if promo_type == PROMO_PERCENTAGE_DISCOUNT and dv > 100:
            raise ValidationError({"discount_value": "Percentage discount cannot exceed 100."})

    elif promo_type == PROMO_FREE_ITEM:
        if not data.get("free_item_id"):
            raise ValidationError({"free_item": "A free menu item must be specified."})

    elif promo_type == PROMO_BUY_X_GET_Y:
        if not data.get("buy_quantity") or not data.get("get_quantity"):
            raise ValidationError(
                {"buy_quantity": "buy_quantity and get_quantity are required for BUY_X_GET_Y."}
            )

    elif promo_type == PROMO_LOYALTY_BONUS:
        if not data.get("loyalty_bonus_multiplier"):
            raise ValidationError(
                {"loyalty_bonus_multiplier": "A multiplier is required for LOYALTY_BONUS."}
            )
        m = Decimal(str(data["loyalty_bonus_multiplier"]))
        if m < Decimal("1.00"):
            raise ValidationError(
                {"loyalty_bonus_multiplier": "Multiplier must be at least 1.0."}
            )
