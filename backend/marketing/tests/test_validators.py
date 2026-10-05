# =============================================================================
# RestaurantFlow — Marketing Validator Tests
# Phase 18
# =============================================================================

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from marketing.validators import (
    validate_campaign_code,
    validate_promotion_code,
    validate_message_body,
    render_message,
    validate_promotion_type_fields,
)
from marketing.constants import (
    PROMO_PERCENTAGE_DISCOUNT, PROMO_FIXED_DISCOUNT,
    PROMO_FREE_ITEM, PROMO_LOYALTY_BONUS,
    DISCOUNT_PERCENTAGE,
)


class CampaignCodeValidatorTests(TestCase):

    def test_valid_code_normalized(self):
        self.assertEqual(validate_campaign_code("  summer24  "), "SUMMER24")

    def test_valid_alphanumeric_underscore(self):
        self.assertEqual(validate_campaign_code("MY_CAMPAIGN_01"), "MY_CAMPAIGN_01")

    def test_empty_code_raises(self):
        with self.assertRaises(ValidationError):
            validate_campaign_code("")

    def test_code_with_spaces_raises(self):
        with self.assertRaises(ValidationError):
            validate_campaign_code("MY CAMPAIGN")

    def test_code_too_long_raises(self):
        with self.assertRaises(ValidationError):
            validate_campaign_code("A" * 51)

    def test_special_chars_raises(self):
        with self.assertRaises(ValidationError):
            validate_campaign_code("CAMP@!")


class PromotionCodeValidatorTests(TestCase):

    def test_valid_promo_code(self):
        self.assertEqual(validate_promotion_code("welcome10"), "WELCOME10")

    def test_empty_code_returns_empty(self):
        self.assertEqual(validate_promotion_code(""), "")

    def test_code_too_long_raises(self):
        with self.assertRaises(ValidationError):
            validate_promotion_code("P" * 51)


class MessageBodyValidatorTests(TestCase):

    def test_safe_placeholders_allowed(self):
        body = "Hello {{customer_name}}, your promo code is {{promotion_code}}."
        result = validate_message_body(body)
        self.assertEqual(result, body)

    def test_template_tags_blocked(self):
        with self.assertRaises(ValidationError):
            validate_message_body("Hello {% if user %} world {% endif %}")

    def test_arbitrary_expression_blocked(self):
        with self.assertRaises(ValidationError):
            validate_message_body("{{user.password}}")


class RenderMessageTests(TestCase):

    def test_renders_customer_name(self):
        result = render_message(
            "Hello {{customer_name}}!",
            {"customer_name": "Alice"},
        )
        self.assertEqual(result, "Hello Alice!")

    def test_renders_promotion_code(self):
        result = render_message(
            "Use code {{promotion_code}} for discount",
            {"promotion_code": "SAVE10"},
        )
        self.assertEqual(result, "Use code SAVE10 for discount")

    def test_unknown_placeholder_left_as_is(self):
        result = render_message("Hello {{unknown_key}}!", {})
        self.assertEqual(result, "Hello {{unknown_key}}!")

    def test_all_placeholders_rendered(self):
        result = render_message(
            "{{customer_name}} — {{restaurant_name}} — {{promotion_code}} — {{reward_name}} — {{expiry_date}}",
            {
                "customer_name": "Alice",
                "restaurant_name": "Biryani House",
                "promotion_code": "SAVE10",
                "reward_name": "Free Dessert",
                "expiry_date": "2026-12-31",
            }
        )
        self.assertEqual(result, "Alice — Biryani House — SAVE10 — Free Dessert — 2026-12-31")


class PromotionTypeFieldsValidatorTests(TestCase):

    def test_percentage_discount_requires_value_and_type(self):
        with self.assertRaises(ValidationError):
            validate_promotion_type_fields({
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
            })

    def test_percentage_over_100_raises(self):
        with self.assertRaises(ValidationError):
            validate_promotion_type_fields({
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": 150,
            })

    def test_free_item_requires_item(self):
        with self.assertRaises(ValidationError):
            validate_promotion_type_fields({
                "promotion_type": PROMO_FREE_ITEM,
            })

    def test_loyalty_bonus_requires_multiplier(self):
        with self.assertRaises(ValidationError):
            validate_promotion_type_fields({
                "promotion_type": PROMO_LOYALTY_BONUS,
            })

    def test_valid_percentage_passes(self):
        # Should not raise
        validate_promotion_type_fields({
            "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
            "discount_type": DISCOUNT_PERCENTAGE,
            "discount_value": 10,
        })
