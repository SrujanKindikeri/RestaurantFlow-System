# =============================================================================
# RestaurantFlow — Billing Utils Tests
# Phase 8
#
# Tests every utility function in billing/utils.py with exact expected values.
# No database access — pure Decimal arithmetic tests.
# =============================================================================

from decimal import Decimal
from django.test import SimpleTestCase

from billing.utils import (
    money, rate, compute_gross, compute_tax,
    compute_percentage_discount, compute_fixed_discount,
    compute_rounding, build_tax_breakdown, format_money,
    ZERO, ONE_HUNDRED,
)


class TestMoneyHelper(SimpleTestCase):
    """money() — convert to Decimal(2dp) with ROUND_HALF_UP."""

    def test_integer_string(self):
        self.assertEqual(money("250"), Decimal("250.00"))

    def test_decimal_string(self):
        self.assertEqual(money("99.999"), Decimal("100.00"))  # rounds up

    def test_exact_two_dp(self):
        self.assertEqual(money("10.50"), Decimal("10.50"))

    def test_int(self):
        self.assertEqual(money(5), Decimal("5.00"))

    def test_zero(self):
        self.assertEqual(money(0), Decimal("0.00"))

    def test_negative(self):
        self.assertEqual(money("-0.30"), Decimal("-0.30"))

    def test_already_decimal(self):
        d = Decimal("123.456")
        self.assertEqual(money(d), Decimal("123.46"))

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            money("not_a_number")

    def test_rounding_half_up_005(self):
        # 0.005 should round to 0.01 (ROUND_HALF_UP)
        self.assertEqual(money("0.005"), Decimal("0.01"))

    def test_rounding_half_up_0049(self):
        # 0.0049 should round down to 0.00
        self.assertEqual(money("0.0049"), Decimal("0.00"))


class TestRateHelper(SimpleTestCase):
    """rate() — convert to Decimal(3dp)."""

    def test_integer(self):
        self.assertEqual(rate("5"), Decimal("5.000"))

    def test_float_string(self):
        self.assertEqual(rate("12.5"), Decimal("12.500"))

    def test_zero(self):
        self.assertEqual(rate(0), Decimal("0.000"))

    def test_already_3dp(self):
        self.assertEqual(rate("18.000"), Decimal("18.000"))

    def test_rounding(self):
        self.assertEqual(rate("9.9999"), Decimal("10.000"))


class TestComputeGross(SimpleTestCase):
    """compute_gross(qty, unit_price) = qty × unit_price (2dp)."""

    def test_basic(self):
        self.assertEqual(
            compute_gross(Decimal("2"), Decimal("250.00")),
            Decimal("500.00"),
        )

    def test_fractional_qty(self):
        self.assertEqual(
            compute_gross(Decimal("1.500"), Decimal("100.00")),
            Decimal("150.00"),
        )

    def test_zero_price(self):
        self.assertEqual(
            compute_gross(Decimal("3"), Decimal("0.00")),
            Decimal("0.00"),
        )

    def test_rounding(self):
        # 3 × 33.33 = 99.99
        self.assertEqual(
            compute_gross(Decimal("3"), Decimal("33.33")),
            Decimal("99.99"),
        )

    def test_one_unit(self):
        self.assertEqual(
            compute_gross(Decimal("1"), Decimal("120.00")),
            Decimal("120.00"),
        )

    def test_large_amount(self):
        self.assertEqual(
            compute_gross(Decimal("100"), Decimal("9999.99")),
            Decimal("999999.00"),
        )


class TestComputeTax(SimpleTestCase):
    """compute_tax(taxable, rate%) = taxable × rate / 100 (2dp, ROUND_HALF_UP)."""

    def test_5_percent(self):
        self.assertEqual(
            compute_tax(Decimal("1000.00"), Decimal("5.000")),
            Decimal("50.00"),
        )

    def test_zero_rate(self):
        self.assertEqual(
            compute_tax(Decimal("1000.00"), Decimal("0.000")),
            Decimal("0.00"),
        )

    def test_18_percent(self):
        self.assertEqual(
            compute_tax(Decimal("100.00"), Decimal("18.000")),
            Decimal("18.00"),
        )

    def test_rounding_case(self):
        # 333.33 × 9% = 29.9997 → rounds to 30.00
        self.assertEqual(
            compute_tax(Decimal("333.33"), Decimal("9.000")),
            Decimal("30.00"),
        )

    def test_zero_taxable(self):
        self.assertEqual(
            compute_tax(Decimal("0.00"), Decimal("5.000")),
            Decimal("0.00"),
        )

    def test_fractional_rate(self):
        # 200 × 2.5% = 5.00
        self.assertEqual(
            compute_tax(Decimal("200.00"), Decimal("2.500")),
            Decimal("5.00"),
        )

    def test_small_amount_rounding(self):
        # 1.00 × 5% = 0.05
        self.assertEqual(
            compute_tax(Decimal("1.00"), Decimal("5.000")),
            Decimal("0.05"),
        )

    def test_0_01_amount(self):
        # 0.01 × 18% = 0.0018 → rounds to 0.00
        self.assertEqual(
            compute_tax(Decimal("0.01"), Decimal("18.000")),
            Decimal("0.00"),
        )


class TestPercentageDiscount(SimpleTestCase):
    """compute_percentage_discount(subtotal, pct)."""

    def test_10_percent(self):
        self.assertEqual(
            compute_percentage_discount(Decimal("1000.00"), Decimal("10.00")),
            Decimal("100.00"),
        )

    def test_zero_percent(self):
        self.assertEqual(
            compute_percentage_discount(Decimal("1000.00"), Decimal("0.00")),
            Decimal("0.00"),
        )

    def test_100_percent(self):
        self.assertEqual(
            compute_percentage_discount(Decimal("500.00"), Decimal("100.00")),
            Decimal("500.00"),
        )

    def test_capped_at_subtotal(self):
        # Even if somehow > 100 passes through, cap at subtotal
        self.assertEqual(
            compute_percentage_discount(Decimal("100.00"), Decimal("150.00")),
            Decimal("100.00"),
        )

    def test_rounding(self):
        # 710 × 7.777% = 55.2167 → 55.22
        result = compute_percentage_discount(Decimal("710.00"), Decimal("7.777"))
        self.assertEqual(result, Decimal("55.22"))

    def test_zero_subtotal(self):
        self.assertEqual(
            compute_percentage_discount(Decimal("0.00"), Decimal("10.00")),
            Decimal("0.00"),
        )


class TestFixedDiscount(SimpleTestCase):
    """compute_fixed_discount(subtotal, fixed)."""

    def test_basic(self):
        self.assertEqual(
            compute_fixed_discount(Decimal("1000.00"), Decimal("50.00")),
            Decimal("50.00"),
        )

    def test_zero(self):
        self.assertEqual(
            compute_fixed_discount(Decimal("1000.00"), Decimal("0.00")),
            Decimal("0.00"),
        )

    def test_capped_at_subtotal(self):
        self.assertEqual(
            compute_fixed_discount(Decimal("100.00"), Decimal("200.00")),
            Decimal("100.00"),
        )

    def test_exact_subtotal(self):
        self.assertEqual(
            compute_fixed_discount(Decimal("250.00"), Decimal("250.00")),
            Decimal("250.00"),
        )


class TestComputeRounding(SimpleTestCase):
    """compute_rounding(pre_rounding_total) → adjustment to nearest integer."""

    def test_exact_integer(self):
        self.assertEqual(compute_rounding(Decimal("1050.00")), Decimal("0.00"))

    def test_round_down(self):
        # 1050.30 → nearest int = 1050 → adj = -0.30
        self.assertEqual(compute_rounding(Decimal("1050.30")), Decimal("-0.30"))

    def test_round_up(self):
        # 1050.60 → nearest int = 1051 → adj = +0.40
        self.assertEqual(compute_rounding(Decimal("1050.60")), Decimal("0.40"))

    def test_exactly_half(self):
        # 1050.50 → ROUND_HALF_UP → 1051 → adj = +0.50
        self.assertEqual(compute_rounding(Decimal("1050.50")), Decimal("0.50"))

    def test_zero(self):
        self.assertEqual(compute_rounding(Decimal("0.00")), Decimal("0.00"))

    def test_negative_adjustment_small(self):
        result = compute_rounding(Decimal("99.99"))
        # 99.99 → nearest = 100 → adj = 0.01
        self.assertEqual(result, Decimal("0.01"))

    def test_rounding_within_range(self):
        """Rounding adjustment must be in (-0.50, +0.50]."""
        for cents in range(0, 100):
            val = Decimal(f"100.{cents:02d}")
            adj = compute_rounding(val)
            self.assertGreaterEqual(adj, Decimal("-0.50"))
            self.assertLessEqual(adj, Decimal("0.50"))


class TestBuildTaxBreakdown(SimpleTestCase):
    """build_tax_breakdown(items) → dict of code: amount_str."""

    def test_single_code(self):
        items = [
            {"tax_code": "GST_STANDARD", "tax_amount": Decimal("50.00")},
            {"tax_code": "GST_STANDARD", "tax_amount": Decimal("25.00")},
        ]
        result = build_tax_breakdown(items)
        self.assertEqual(result, {"GST_STANDARD": "75.00"})

    def test_multiple_codes(self):
        items = [
            {"tax_code": "GST_STANDARD", "tax_amount": Decimal("50.00")},
            {"tax_code": "CESS", "tax_amount": Decimal("5.00")},
        ]
        result = build_tax_breakdown(items)
        self.assertEqual(result["GST_STANDARD"], "50.00")
        self.assertEqual(result["CESS"], "5.00")

    def test_empty_code_grouped_as_no_tax(self):
        items = [
            {"tax_code": "", "tax_amount": Decimal("0.00")},
        ]
        result = build_tax_breakdown(items)
        self.assertIn("NO_TAX", result)

    def test_zero_tax(self):
        items = [
            {"tax_code": "ZERO_TAX", "tax_amount": Decimal("0.00")},
        ]
        result = build_tax_breakdown(items)
        self.assertEqual(result["ZERO_TAX"], "0.00")

    def test_empty_list(self):
        result = build_tax_breakdown([])
        self.assertEqual(result, {})

    def test_string_tax_amount_converted(self):
        items = [
            {"tax_code": "GST", "tax_amount": "10.00"},
        ]
        result = build_tax_breakdown(items)
        self.assertEqual(result["GST"], "10.00")


class TestFormatMoney(SimpleTestCase):
    def test_basic(self):
        self.assertEqual(format_money(Decimal("1050.00")), "₹1,050.00")

    def test_zero(self):
        self.assertEqual(format_money(Decimal("0.00")), "₹0.00")

    def test_custom_symbol(self):
        self.assertEqual(format_money(Decimal("500.00"), "USD "), "USD 500.00")

    def test_negative(self):
        self.assertEqual(format_money(Decimal("-50.00")), "-₹50.00")
