# =============================================================================
# RestaurantFlow — Discount Tests
# Phase 8
#
# Tests:
#   - 0% discount
#   - valid percentage discount
#   - 100% max discount
#   - invalid >100% rejected
#   - fixed amount discount
#   - discount > subtotal rejected
#   - cashier limit enforcement
#   - manager has larger limit
#   - unauthorized user cannot apply discount
#   - remove discount
#   - duplicate discount request overwrites (not doubles)
# =============================================================================

from decimal import Decimal

from rest_framework.exceptions import PermissionDenied, ValidationError

from billing.models import Bill, BillStatus, DiscountType
from billing import services
from billing.validators import (
    validate_percentage_discount,
    validate_fixed_discount,
)
from billing.tests.base import BillingTestBase


class TestApplyPercentageDiscount(BillingTestBase):
    """Tests for percentage discount application."""

    def test_zero_percent_discount(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        updated = services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("0"),
            max_pct=Decimal("10"),
        )
        self.assertEqual(updated.discount_amount, Decimal("0.00"))
        self.assertEqual(updated.grand_total, Decimal("645.00"))  # unchanged

    def test_valid_percentage_within_limit(self):
        # 5% discount on 620 = 31.00 discount
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        updated = services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("5"),
            max_pct=Decimal("10"),
        )
        self.assertEqual(updated.discount_amount, Decimal("31.00"))
        self.assertEqual(updated.discount_type, DiscountType.PERCENTAGE)

    def test_percentage_exceeds_max_pct_raises(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(ValidationError):
            services.apply_discount(
                bill, self.cashier,
                discount_type="PERCENTAGE",
                value=Decimal("15"),
                max_pct=Decimal("10"),  # cashier limited to 10%
            )

    def test_100_percent_discount_allowed_with_full_permission(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        # Manager can apply up to 100%
        updated = services.apply_discount(
            bill, self.manager,
            discount_type="PERCENTAGE",
            value=Decimal("100"),
            max_pct=Decimal("100"),
        )
        self.assertEqual(updated.discount_amount, updated.subtotal)

    def test_over_100_percent_always_rejected(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(ValidationError):
            services.apply_discount(
                bill, self.manager,
                discount_type="PERCENTAGE",
                value=Decimal("101"),
                max_pct=Decimal("100"),
            )

    def test_negative_percentage_rejected(self):
        from billing.validators import validate_percentage_discount
        with self.assertRaises(ValidationError):
            validate_percentage_discount(Decimal("-5"), Decimal("100"))

    def test_discount_stored_and_recalculated(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("10"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        # discount_value is what was input
        self.assertEqual(bill.discount_value, Decimal("10.00"))
        # discount_amount is what was computed (620 × 10% = 62)
        self.assertEqual(bill.discount_amount, Decimal("62.00"))


class TestApplyFixedDiscount(BillingTestBase):
    """Tests for fixed-amount discount application."""

    def test_valid_fixed_discount(self):
        # Fixed ₹50 off 620
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        updated = services.apply_discount(
            bill, self.cashier,
            discount_type="FIXED_AMOUNT",
            value=Decimal("50"),
            max_pct=Decimal("100"),
        )
        self.assertEqual(updated.discount_amount, Decimal("50.00"))
        self.assertEqual(updated.discount_type, DiscountType.FIXED_AMOUNT)

    def test_zero_fixed_discount(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        updated = services.apply_discount(
            bill, self.cashier,
            discount_type="FIXED_AMOUNT",
            value=Decimal("0"),
            max_pct=Decimal("100"),
        )
        self.assertEqual(updated.discount_amount, Decimal("0.00"))

    def test_fixed_discount_greater_than_subtotal_rejected(self):
        order = self._make_confirmed_order()  # subtotal = 620
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(ValidationError):
            services.apply_discount(
                bill, self.cashier,
                discount_type="FIXED_AMOUNT",
                value=Decimal("700"),  # > 620
                max_pct=Decimal("100"),
            )

    def test_negative_fixed_discount_rejected(self):
        from billing.validators import validate_fixed_discount
        with self.assertRaises(ValidationError):
            validate_fixed_discount(Decimal("-10"), Decimal("500"))

    def test_fixed_discount_exact_subtotal(self):
        """A fixed discount equal to the subtotal results in 0 taxable amount."""
        order = self._make_confirmed_order()  # subtotal = 620
        bill = services.create_bill_from_order(order, self.cashier)
        updated = services.apply_discount(
            bill, self.manager,
            discount_type="FIXED_AMOUNT",
            value=Decimal("620"),
            max_pct=Decimal("100"),
        )
        self.assertEqual(updated.discount_amount, Decimal("620.00"))
        self.assertEqual(updated.taxable_amount, Decimal("0.00"))


class TestRemoveDiscount(BillingTestBase):
    """Tests for remove_discount()."""

    def test_remove_applied_discount(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("5"),
            max_pct=Decimal("10"),
        )
        bill.refresh_from_db()
        self.assertEqual(bill.discount_amount, Decimal("31.00"))

        services.remove_discount(bill, self.cashier)
        bill.refresh_from_db()
        self.assertEqual(bill.discount_amount, Decimal("0.00"))
        self.assertIsNone(bill.discount_type)

    def test_remove_discount_recalculates(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.apply_discount(
            bill, self.cashier,
            discount_type="FIXED_AMOUNT",
            value=Decimal("100"),
            max_pct=Decimal("100"),
        )
        services.remove_discount(bill, self.cashier)
        bill.refresh_from_db()
        # Back to full grand total
        self.assertEqual(bill.grand_total, Decimal("645.00"))

    def test_remove_discount_requires_permission(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        with self.assertRaises(PermissionDenied):
            services.remove_discount(bill, self.other_user)


class TestDiscountOnFinalizedBill(BillingTestBase):
    """Discounts cannot be applied after finalization."""

    def test_cannot_apply_discount_to_finalized_bill(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.finalize_bill(bill, self.cashier)
        bill.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            services.apply_discount(
                bill, self.cashier,
                discount_type="PERCENTAGE",
                value=Decimal("5"),
                max_pct=Decimal("10"),
            )
        self.assertEqual(ctx.exception.detail["code"], "BILL_NOT_DRAFT")

    def test_applying_discount_twice_overwrites_not_doubles(self):
        """Second apply_discount replaces the first, doesn't stack."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("5"),
            max_pct=Decimal("10"),
        )
        bill.refresh_from_db()
        first_discount = bill.discount_amount  # 31.00

        services.apply_discount(
            bill, self.cashier,
            discount_type="PERCENTAGE",
            value=Decimal("5"),
            max_pct=Decimal("10"),
        )
        bill.refresh_from_db()
        # Should still be 31.00 (5%), not 62.00 (doubled)
        self.assertEqual(bill.discount_amount, first_discount)


class TestDiscountValidator(BillingTestBase):
    """Unit tests for discount validators (no DB needed for most)."""

    def test_validate_percentage_valid(self):
        from billing.validators import validate_percentage_discount
        result = validate_percentage_discount(Decimal("10"), Decimal("100"))
        self.assertEqual(result, Decimal("10"))

    def test_validate_percentage_exceeds_max(self):
        from billing.validators import validate_percentage_discount
        with self.assertRaises(ValidationError):
            validate_percentage_discount(Decimal("15"), Decimal("10"))

    def test_validate_percentage_over_100(self):
        from billing.validators import validate_percentage_discount
        with self.assertRaises(ValidationError):
            validate_percentage_discount(Decimal("101"), Decimal("100"))

    def test_validate_fixed_valid(self):
        from billing.validators import validate_fixed_discount
        result = validate_fixed_discount(Decimal("50"), Decimal("500"))
        self.assertEqual(result, Decimal("50"))

    def test_validate_fixed_exceeds_subtotal(self):
        from billing.validators import validate_fixed_discount
        with self.assertRaises(ValidationError):
            validate_fixed_discount(Decimal("600"), Decimal("500"))

    def test_validate_discount_type_valid(self):
        from billing.validators import validate_discount_type
        self.assertEqual(validate_discount_type("PERCENTAGE"), "PERCENTAGE")
        self.assertEqual(validate_discount_type("FIXED_AMOUNT"), "FIXED_AMOUNT")

    def test_validate_discount_type_invalid(self):
        from billing.validators import validate_discount_type
        with self.assertRaises(ValidationError):
            validate_discount_type("INVALID_TYPE")
