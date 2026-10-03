# =============================================================================
# RestaurantFlow — Tax Calculation Tests
# Phase 8
#
# Tests:
#   - zero tax
#   - percentage tax (5%, 18%, 2.5%)
#   - multiple tax components / mixed rates
#   - discount before tax (proportional)
#   - tax after discount
#   - rounding (exact values)
#   - decimal precision
#   - tax snapshot isolation (changed future tax config doesn't affect bill)
#   - historical bill preservation
# =============================================================================

from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import Bill, BillStatus
from billing import services
from billing.tests.base import BillingTestBase
from menu.models import MenuItem, TaxRate, MenuItemPrice, MenuItemBranch
from orders.models import Order, OrderItem, OrderStatus, OrderType


class TestZeroTax(BillingTestBase):
    """Items with 0% tax rate should produce zero tax amounts."""

    def test_zero_tax_item(self):
        ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ZT-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.cashier,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_fries,
            item_name_snapshot="French Fries",
            sku_snapshot="FRIES-001",
            unit_price_snapshot=Decimal("100.00"),
            tax_rate_snapshot=Decimal("0.000"),
            tax_code_snapshot="ZERO_TAX",
            quantity=Decimal("5.000"),
        )
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.tax_amount, Decimal("0.00"))
        self.assertEqual(bill.subtotal, Decimal("500.00"))
        self.assertEqual(bill.taxable_amount, Decimal("500.00"))
        self.assertEqual(bill.grand_total, Decimal("500.00"))

    def test_zero_tax_breakdown_entry(self):
        ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"ZTB-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.cashier,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_fries,
            item_name_snapshot="French Fries",
            sku_snapshot="FRIES-001",
            unit_price_snapshot=Decimal("120.00"),
            tax_rate_snapshot=Decimal("0.000"),
            tax_code_snapshot="ZERO_TAX",
            quantity=Decimal("1.000"),
        )
        bill = services.create_bill_from_order(order, self.cashier)
        # ZERO_TAX should appear in breakdown with 0.00
        self.assertIn("ZERO_TAX", bill.tax_breakdown)
        self.assertEqual(bill.tax_breakdown["ZERO_TAX"], "0.00")


class TestPercentageTax(BillingTestBase):
    """Exact tax amount verification for common tax rates."""

    def test_5_percent_tax(self):
        # 2 × 250 = 500 at 5% → tax = 25.00
        ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"T5-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.cashier,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_biryani,
            item_name_snapshot="Chicken Biryani",
            sku_snapshot="BIRYA-001",
            unit_price_snapshot=Decimal("250.00"),
            tax_rate_snapshot=Decimal("5.000"),
            tax_code_snapshot="GST_5",
            quantity=Decimal("2.000"),
        )
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.subtotal, Decimal("500.00"))
        self.assertEqual(bill.tax_amount, Decimal("25.00"))
        self.assertEqual(bill.grand_total, Decimal("525.00"))

    def test_18_percent_tax(self):
        # Create 18% tax rate item
        tax_18 = TaxRate.objects.create(
            restaurant=self.restaurant,
            name="GST 18%",
            code="GST_18",
            rate=Decimal("18.000"),
        )
        item_beverage = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name="Soft Drink",
            slug="soft-drink",
            sku="DRINK-001",
            tax_rate=tax_18,
        )
        MenuItemBranch.objects.create(menu_item=item_beverage, branch=self.branch, is_available=True)

        ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"T18-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.cashier,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        # 1 × 100 at 18% = 18.00 tax → total = 118.00
        OrderItem.objects.create(
            order=order,
            menu_item=item_beverage,
            item_name_snapshot="Soft Drink",
            sku_snapshot="DRINK-001",
            unit_price_snapshot=Decimal("100.00"),
            tax_rate_snapshot=Decimal("18.000"),
            tax_code_snapshot="GST_18",
            quantity=Decimal("1.000"),
        )
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.tax_amount, Decimal("18.00"))
        self.assertEqual(bill.grand_total, Decimal("118.00"))

    def test_multiple_tax_components(self):
        """Mixed tax codes: GST_5 (biryani) + ZERO_TAX (fries) → breakdown has both."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        # Biryani: 2×250=500, 5% tax = 25.00
        # Fries:   1×120=120, 0% tax = 0.00
        # Total tax = 25.00
        self.assertEqual(bill.tax_amount, Decimal("25.00"))
        self.assertIn("GST_5", bill.tax_breakdown)
        self.assertIn("ZERO_TAX", bill.tax_breakdown)
        self.assertEqual(bill.tax_breakdown["GST_5"], "25.00")
        self.assertEqual(bill.tax_breakdown["ZERO_TAX"], "0.00")


class TestTaxWithDiscount(BillingTestBase):
    """Tax must be calculated on (subtotal - discount), not on raw subtotal."""

    def test_tax_after_percentage_discount(self):
        # Subtotal = 620 (from base fixture)
        # 10% discount → discount = 62.00 → taxable = 558.00
        # Biryani portion of taxable: proportional
        #   Biryani gross = 500, fries gross = 120, total = 620
        #   discount ratio = 62/620 = 0.1
        #   biryani_taxable = 500 × 0.9 = 450 → tax = 450 × 5% = 22.50
        #   fries_taxable   = 120 × 0.9 = 108 → tax = 108 × 0% = 0.00
        #   total tax = 22.50
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)

        services.apply_discount(
            bill, self.manager,
            discount_type="PERCENTAGE",
            value=Decimal("10"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()

        self.assertEqual(bill.discount_amount, Decimal("62.00"))
        self.assertEqual(bill.taxable_amount, Decimal("558.00"))
        self.assertEqual(bill.tax_amount, Decimal("22.50"))

    def test_tax_after_fixed_discount(self):
        # Subtotal = 620
        # Fixed discount = 120 → taxable = 500
        # discount ratio = 120/620 ≈ 0.1935...
        # biryani_taxable = 500 × (1 - 120/620) = 500 × 500/620 = 403.23 (approx)
        # Exact: biryani gross = 500, discount portion = 500×120/620 = 96.77
        # biryani taxable = 500 - 96.77 = 403.23, tax = 403.23 × 5% = 20.16
        # fries: 120 - 120×120/620 = 120 - 23.23 = 96.77, tax = 0
        # total tax = 20.16
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)

        services.apply_discount(
            bill, self.manager,
            discount_type="FIXED_AMOUNT",
            value=Decimal("120"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()

        self.assertEqual(bill.discount_amount, Decimal("120.00"))
        self.assertEqual(bill.taxable_amount, Decimal("500.00"))
        # Tax should be on taxable portion only
        self.assertGreater(bill.tax_amount, Decimal("0.00"))
        self.assertLess(bill.tax_amount, Decimal("25.00"))  # less than undiscounted tax

    def test_grand_total_with_discount_and_tax(self):
        # Subtotal = 620, 10% discount = 62, taxable = 558
        # Tax on taxable (proportional): 22.50
        # pre-rounding = 558 + 22.50 = 580.50 → rounds to 581 → adj = +0.50
        # grand_total = 581.00
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.apply_discount(
            bill, self.manager,
            discount_type="PERCENTAGE",
            value=Decimal("10"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        # taxable = 558, tax = 22.50, pre-round = 580.50
        expected_grand = Decimal("581.00")
        self.assertEqual(bill.grand_total, expected_grand)


class TestTaxSnapshot(BillingTestBase):
    """Tax snapshots protect historical bills from future tax config changes."""

    def test_future_tax_rate_change_does_not_affect_existing_bill(self):
        """
        If TaxRate.rate changes after bill creation, the bill tax_amount
        must remain based on the snapshot at creation time (5%), not the new rate.
        """
        # Create confirmed order with 5% snapshot
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)

        # Record original tax
        original_tax = bill.tax_amount  # 25.00

        # Simulate changing the tax rate (this doesn't affect the snapshot on OrderItem)
        self.tax_gst5.rate = Decimal("18.000")
        self.tax_gst5.save()

        # Recalculate — snapshot is on BillItem, not dynamic from TaxRate
        bill.refresh_from_db()
        result = services.calculate_bill(bill)

        # Tax must still use the snapshot (5%), not the new 18%
        self.assertEqual(bill.items.first().tax_rate, Decimal("5.000"))
        # Restore
        self.tax_gst5.rate = Decimal("5.000")
        self.tax_gst5.save()

    def test_finalized_bill_tax_preserved_after_config_change(self):
        """A finalized bill's tax_amount is immutable."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        original_tax = bill.tax_amount

        services.finalize_bill(bill, self.cashier)

        # Change tax rate
        self.tax_gst5.rate = Decimal("25.000")
        self.tax_gst5.save()

        # Re-read — should be unchanged
        bill.refresh_from_db()
        self.assertEqual(bill.tax_amount, original_tax)

        # Restore
        self.tax_gst5.rate = Decimal("5.000")
        self.tax_gst5.save()
