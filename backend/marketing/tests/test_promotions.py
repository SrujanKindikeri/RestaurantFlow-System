# =============================================================================
# RestaurantFlow — Promotion Tests
# Phase 18
# =============================================================================

from decimal import Decimal
import threading
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from marketing.tests.base import MarketingTestBase
from marketing.promotion_services import (
    PromotionService, PromotionEligibilityService, PromotionUsageService,
)
from marketing.models import Promotion, PromotionRule, PromotionUsage
from marketing.constants import (
    PROMO_PERCENTAGE_DISCOUNT, PROMO_FIXED_DISCOUNT,
    PROMO_FREE_ITEM, PROMO_LOYALTY_BONUS, PROMO_BUY_X_GET_Y,
    DISCOUNT_PERCENTAGE, DISCOUNT_FIXED_AMOUNT,
    USAGE_RESERVED, USAGE_APPLIED, USAGE_REVERSED, USAGE_CANCELLED,
    RULE_MIN_ORDER_VALUE, RULE_CUSTOMER_SEGMENT, RULE_CUSTOMER_TAG,
    RULE_FIRST_ORDER, RULE_REPEAT_ORDER, RULE_DAY_OF_WEEK,
    RULE_TIME_WINDOW,
)
from marketing.exceptions import (
    MarketingPermissionDenied, PromotionUsageLimitReached, PromotionAlreadyUsed,
)


class PromotionCreateTests(MarketingTestBase):

    def test_create_percentage_promotion(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "10% Off",
                "code": "SAVE10",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
            },
            actor=self.marketer,
        )
        self.assertFalse(promo.is_active)  # Starts inactive
        self.assertEqual(promo.code, "SAVE10")
        self.assertEqual(promo.discount_value, Decimal("10.00"))

    def test_create_fixed_discount_promotion(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "₹50 Off",
                "code": "FLAT50",
                "promotion_type": PROMO_FIXED_DISCOUNT,
                "discount_type": DISCOUNT_FIXED_AMOUNT,
                "discount_value": Decimal("50.00"),
            },
            actor=self.marketer,
        )
        self.assertEqual(promo.promotion_type, PROMO_FIXED_DISCOUNT)

    def test_create_promotion_code_normalized(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Test",
                "code": "  save20  ",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("20.00"),
            },
            actor=self.marketer,
        )
        self.assertEqual(promo.code, "SAVE20")

    def test_create_promotion_without_permission_raises(self):
        with self.assertRaises(MarketingPermissionDenied):
            PromotionService.create_promotion(
                company=self.org,
                restaurant=self.restaurant,
                data={"name": "Bad", "promotion_type": PROMO_FIXED_DISCOUNT},
                actor=self.other_user,
            )

    def test_activate_and_deactivate(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Activate Test",
                "code": "ACTTEST",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("5.00"),
            },
            actor=self.marketer,
        )
        self.assertFalse(promo.is_active)

        PromotionService.activate(promo, self.marketer)
        promo.refresh_from_db()
        self.assertTrue(promo.is_active)

        PromotionService.deactivate(promo, self.marketer)
        promo.refresh_from_db()
        self.assertFalse(promo.is_active)

    def test_activate_already_active_raises(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Already Active",
                "code": "ACTACT",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("5.00"),
            },
            actor=self.marketer,
        )
        PromotionService.activate(promo, self.marketer)
        with self.assertRaises(ValidationError):
            PromotionService.activate(promo, self.marketer)


class PromotionEligibilityTests(MarketingTestBase):
    """Test eligibility validation rules."""

    def _make_active_promo(self, code, promo_type=PROMO_PERCENTAGE_DISCOUNT,
                           discount_value=Decimal("10.00"), **kwargs):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": f"Promo {code}",
                "code": code,
                "promotion_type": promo_type,
                "discount_type": DISCOUNT_PERCENTAGE if promo_type == PROMO_PERCENTAGE_DISCOUNT else DISCOUNT_FIXED_AMOUNT,
                "discount_value": discount_value,
                **kwargs,
            },
            actor=self.marketer,
        )
        PromotionService.activate(promo, self.marketer)
        return promo

    def test_basic_eligible(self):
        promo = self._make_active_promo("BASIC10")
        result = PromotionEligibilityService.validate(
            promotion=promo,
            order_subtotal=Decimal("200.00"),
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["estimated_discount"], Decimal("20.00"))

    def test_inactive_promotion_ineligible(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Inactive",
                "code": "INACTIVE",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
            },
            actor=self.marketer,
        )
        result = PromotionEligibilityService.validate(promotion=promo)
        self.assertFalse(result["eligible"])

    def test_expired_promotion_ineligible(self):
        promo = self._make_active_promo("EXPIRED01")
        # Set end_at to the past
        Promotion.objects.filter(pk=promo.pk).update(
            end_at=timezone.now() - timezone.timedelta(days=1)
        )
        promo.refresh_from_db()
        result = PromotionEligibilityService.validate(promotion=promo)
        self.assertFalse(result["eligible"])
        self.assertIn("expired", result["reason"])

    def test_minimum_order_value_rule(self):
        promo = self._make_active_promo("MINVAL")
        PromotionRule.objects.create(
            promotion=promo,
            rule_type=RULE_MIN_ORDER_VALUE,
            configuration={"amount": "500.00"},
        )
        # Below minimum
        result = PromotionEligibilityService.validate(
            promotion=promo, order_subtotal=Decimal("200.00")
        )
        self.assertFalse(result["eligible"])
        # At or above minimum
        result = PromotionEligibilityService.validate(
            promotion=promo, order_subtotal=Decimal("500.00")
        )
        self.assertTrue(result["eligible"])

    def test_customer_segment_rule(self):
        promo = self._make_active_promo("VIPSEG")
        PromotionRule.objects.create(
            promotion=promo,
            rule_type=RULE_CUSTOMER_SEGMENT,
            configuration={"segment_code": "VIP"},
        )
        # customer has VIP segment assignment
        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer
        )
        self.assertTrue(result["eligible"])

        # customer2 does not have VIP segment
        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer2
        )
        self.assertFalse(result["eligible"])

    def test_customer_tag_rule(self):
        promo = self._make_active_promo("FREQTAG")
        PromotionRule.objects.create(
            promotion=promo,
            rule_type=RULE_CUSTOMER_TAG,
            configuration={"tag_code": "FREQUENT"},
        )
        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer
        )
        self.assertTrue(result["eligible"])

        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer2
        )
        self.assertFalse(result["eligible"])

    def test_first_order_rule(self):
        promo = self._make_active_promo("FIRSTORD")
        PromotionRule.objects.create(
            promotion=promo,
            rule_type=RULE_FIRST_ORDER,
            configuration={},
        )
        # customer2 has 0 orders — should pass
        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer2
        )
        self.assertTrue(result["eligible"])

        # customer has 3 orders — should fail
        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer
        )
        self.assertFalse(result["eligible"])

    def test_repeat_order_rule(self):
        promo = self._make_active_promo("REPEATORD")
        PromotionRule.objects.create(
            promotion=promo,
            rule_type=RULE_REPEAT_ORDER,
            configuration={"min_orders": 2},
        )
        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer
        )
        self.assertTrue(result["eligible"])  # 3 orders

        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer2
        )
        self.assertFalse(result["eligible"])  # 0 orders

    def test_usage_limit_exceeded(self):
        promo = self._make_active_promo("USAGELIM")
        Promotion.objects.filter(pk=promo.pk).update(
            usage_limit=2, current_usage_count=2
        )
        promo.refresh_from_db()
        result = PromotionEligibilityService.validate(promotion=promo)
        self.assertFalse(result["eligible"])

    def test_per_customer_limit_exceeded(self):
        promo = self._make_active_promo("CUST_LIM")
        Promotion.objects.filter(pk=promo.pk).update(usage_limit_per_customer=1)
        promo.refresh_from_db()
        # Create an APPLIED usage for customer
        PromotionUsage.objects.create(
            promotion=promo,
            customer=self.customer,
            status=USAGE_APPLIED,
        )
        result = PromotionEligibilityService.validate(
            promotion=promo, customer=self.customer
        )
        self.assertFalse(result["eligible"])

    def test_estimated_discount_percentage(self):
        promo = self._make_active_promo("PCTESTIMATE")
        result = PromotionEligibilityService.validate(
            promotion=promo, order_subtotal=Decimal("300.00")
        )
        self.assertEqual(result["estimated_discount"], Decimal("30.00"))

    def test_estimated_discount_percentage_capped(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Capped 20%",
                "code": "CAPPED20",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("20.00"),
                "max_discount_amount": Decimal("50.00"),
            },
            actor=self.marketer,
        )
        PromotionService.activate(promo, self.marketer)
        result = PromotionEligibilityService.validate(
            promotion=promo, order_subtotal=Decimal("500.00")
        )
        # 20% of 500 = 100, capped at 50
        self.assertEqual(result["estimated_discount"], Decimal("50.00"))

    def test_promo_code_lookup(self):
        promo = self._make_active_promo("CODELOOKUP")
        result = PromotionEligibilityService.validate(
            promotion_code="CODELOOKUP",
            branch=self.branch,
            order_subtotal=Decimal("100.00"),
        )
        self.assertTrue(result["eligible"])
        self.assertEqual(result["promotion_id"], str(promo.pk))

    def test_promo_code_case_insensitive(self):
        promo = self._make_active_promo("CASECODE")
        result = PromotionEligibilityService.validate(
            promotion_code="casecode",
            branch=self.branch,
        )
        self.assertTrue(result["eligible"])


class PromotionUsageTests(MarketingTestBase):
    """Test usage lifecycle — reserve, apply, cancel, reverse."""

    def _make_active_promo(self, code):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": f"Usage {code}",
                "code": code,
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
                "usage_limit": 5,
                "usage_limit_per_customer": 2,
            },
            actor=self.marketer,
        )
        PromotionService.activate(promo, self.marketer)
        return promo

    def test_reserve_usage(self):
        promo = self._make_active_promo("RESV01")
        usage = PromotionUsageService.reserve_usage(
            promo, customer=self.customer
        )
        self.assertEqual(usage.status, USAGE_RESERVED)

    def test_cancel_reserved_usage(self):
        promo = self._make_active_promo("CANCEL01")
        usage = PromotionUsageService.reserve_usage(promo, customer=self.customer)
        usage = PromotionUsageService.cancel_usage(usage)
        self.assertEqual(usage.status, USAGE_CANCELLED)

    def test_usage_limit_enforced_concurrently(self):
        """Usage limit must not be exceeded under concurrent reservations."""
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Concurrent Limit",
                "code": "CONC01",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
                "usage_limit": 3,
            },
            actor=self.marketer,
        )
        PromotionService.activate(promo, self.marketer)

        successes = []
        failures = []

        def try_reserve():
            try:
                PromotionUsageService.reserve_usage(promo)
                successes.append(True)
            except PromotionUsageLimitReached:
                failures.append(True)

        threads = [threading.Thread(target=try_reserve) for _ in range(6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Must never exceed usage_limit=3
        self.assertLessEqual(len(successes), 3)

    def test_per_customer_limit_enforced(self):
        promo = self._make_active_promo("PERCUST01")
        PromotionUsageService.reserve_usage(promo, customer=self.customer)
        PromotionUsageService.reserve_usage(promo, customer=self.customer)
        with self.assertRaises(PromotionAlreadyUsed):
            PromotionUsageService.reserve_usage(promo, customer=self.customer)

    def test_reverse_applied_usage(self):
        promo = self._make_active_promo("REV01")
        usage = PromotionUsageService.reserve_usage(promo, customer=self.customer)
        # Apply it (without a real bill)
        from marketing.models import PromotionUsage as PU
        PU.objects.filter(pk=usage.pk).update(status=USAGE_APPLIED)
        usage.refresh_from_db()

        reversal = PromotionUsageService.reverse_usage(usage, reason="Refund")
        self.assertEqual(reversal.status, USAGE_REVERSED)
        self.assertLess(reversal.discount_amount, Decimal("0"))

    def test_cannot_cancel_applied_usage(self):
        promo = self._make_active_promo("NOCANCEL")
        usage = PromotionUsageService.reserve_usage(promo, customer=self.customer)
        from marketing.models import PromotionUsage as PU
        PU.objects.filter(pk=usage.pk).update(status=USAGE_APPLIED)
        usage.refresh_from_db()
        with self.assertRaises(ValidationError):
            PromotionUsageService.cancel_usage(usage)
