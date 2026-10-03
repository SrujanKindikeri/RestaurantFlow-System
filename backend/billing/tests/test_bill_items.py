# =============================================================================
# RestaurantFlow — Bill Item Tests
# Phase 8
#
# Tests:
#   - BillItem snapshots match OrderItem snapshots exactly
#   - BillItem gross_amount = quantity × unit_price
#   - BillItem tax_amount computed correctly
#   - BillItem total_amount = taxable + tax
#   - price snapshot isolation (menu price change after billing)
#   - one BillItem per OrderItem (OneToOne constraint)
#   - BillItem count matches OrderItem count
#   - zero-quantity rejected (OrderItem level)
#   - BillItem discount_amount = 0 by default (bill-level discount only in P8)
# =============================================================================

from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from billing.models import Bill, BillItem, BillStatus
from billing import services
from billing.tests.base import BillingTestBase
from menu.models import MenuItem, MenuItemBranch, MenuItemPrice
from orders.models import Order, OrderItem, OrderStatus, OrderType


class TestBillItemSnapshots(BillingTestBase):
    """BillItem must mirror OrderItem snapshots exactly."""

    def test_bill_item_name_matches_snapshot(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        names = set(bill.items.values_list("item_name_snapshot", flat=True))
        self.assertIn("Chicken Biryani", names)
        self.assertIn("French Fries", names)

    def test_bill_item_sku_matches_snapshot(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.sku_snapshot, "BIRYA-001")

    def test_bill_item_unit_price_matches_order_item(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        order_item = order.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.unit_price, order_item.unit_price_snapshot)

    def test_bill_item_tax_rate_matches_order_item(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        order_item = order.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.tax_rate, order_item.tax_rate_snapshot)

    def test_bill_item_tax_code_matches_order_item(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.tax_code, "GST_5")

    def test_bill_item_quantity_matches_order_item(self):
        order = self._make_confirmed_order(biryani_qty=Decimal("3.000"))
        bill = services.create_bill_from_order(order, self.cashier)
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.quantity, Decimal("3.000"))


class TestBillItemCalculations(BillingTestBase):
    """BillItem computed fields must be exact."""

    def test_gross_amount(self):
        # Biryani: 2 × 250 = 500
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.gross_amount, Decimal("500.00"))

    def test_gross_amount_fries(self):
        # Fries: 1 × 120 = 120
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        fries = bill.items.get(item_name_snapshot="French Fries")
        self.assertEqual(fries.gross_amount, Decimal("120.00"))

    def test_tax_amount_biryani(self):
        # Biryani: 500 × 5% = 25.00
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.tax_amount, Decimal("25.00"))

    def test_tax_amount_fries_zero(self):
        # Fries: 120 × 0% = 0.00
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        fries = bill.items.get(item_name_snapshot="French Fries")
        self.assertEqual(fries.tax_amount, Decimal("0.00"))

    def test_total_amount_biryani(self):
        # Biryani: 500 (taxable) + 25 (tax) = 525
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.total_amount, Decimal("525.00"))

    def test_total_amount_fries(self):
        # Fries: 120 (taxable) + 0 (tax) = 120
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        fries = bill.items.get(item_name_snapshot="French Fries")
        self.assertEqual(fries.total_amount, Decimal("120.00"))

    def test_item_discount_zero_by_default(self):
        """Phase 8: discount is at bill level. BillItem.discount_amount = 0."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        for item in bill.items.all():
            self.assertEqual(item.discount_amount, Decimal("0.00"))

    def test_taxable_amount_equals_gross_when_no_discount(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        for item in bill.items.all():
            self.assertEqual(item.taxable_amount, item.gross_amount)

    def test_sum_of_bill_items_equals_bill_subtotal(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        items_gross_sum = sum(i.gross_amount for i in bill.items.all())
        self.assertEqual(items_gross_sum, bill.subtotal)


class TestBillItemAfterDiscount(BillingTestBase):
    """After a bill-level discount, BillItem proportional fields update."""

    def test_item_discount_applied_proportionally(self):
        # Subtotal = 620, 10% discount = 62
        # Biryani portion (500/620) discount = 50.00 (approx) 500*62/620 = 50.00
        # Fries portion (120/620) discount = 12.00 (approx) 120*62/620 = 12.00
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.apply_discount(
            bill, self.manager,
            discount_type="PERCENTAGE",
            value=Decimal("10"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        fries = bill.items.get(item_name_snapshot="French Fries")

        # After 10% discount on 500: discount = 50.00, taxable = 450.00
        self.assertEqual(biryani.discount_amount, Decimal("50.00"))
        self.assertEqual(biryani.taxable_amount, Decimal("450.00"))

        # After 10% discount on 120: discount = 12.00, taxable = 108.00
        self.assertEqual(fries.discount_amount, Decimal("12.00"))
        self.assertEqual(fries.taxable_amount, Decimal("108.00"))

    def test_item_tax_recalculated_after_discount(self):
        # Biryani taxable after 10% discount = 450, tax = 450 × 5% = 22.50
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        services.apply_discount(
            bill, self.manager,
            discount_type="PERCENTAGE",
            value=Decimal("10"),
            max_pct=Decimal("100"),
        )
        bill.refresh_from_db()
        biryani = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani.tax_amount, Decimal("22.50"))


class TestBillItemPriceSnapshot(BillingTestBase):
    """BillItem uses the price from OrderItem snapshot, not today's menu price."""

    def test_menu_price_change_does_not_affect_existing_bill(self):
        # Create a confirmed order (snapshots: biryani=250)
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)

        original_price = bill.items.get(
            item_name_snapshot="Chicken Biryani"
        ).unit_price  # 250.00

        # Simulate menu price change: biryani now 280
        MenuItemPrice.objects.filter(
            menu_item=self.item_biryani, branch=self.branch, is_active=True
        ).update(price=Decimal("280.00"))

        # Recalculate bill — should still use 250 from snapshot
        services.calculate_bill(bill)
        bill.refresh_from_db()
        biryani_item = bill.items.get(item_name_snapshot="Chicken Biryani")
        self.assertEqual(biryani_item.unit_price, Decimal("250.00"))
        # Restore
        MenuItemPrice.objects.filter(
            menu_item=self.item_biryani, branch=self.branch
        ).update(price=Decimal("250.00"))

    def test_bill_item_references_order_item(self):
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        for bill_item in bill.items.all():
            self.assertIsNotNone(bill_item.order_item_id)
            # OneToOne — can traverse back to the order item
            self.assertEqual(bill_item.order_item.order, order)


class TestBillItemCount(BillingTestBase):
    """BillItem count should match OrderItem count."""

    def test_bill_item_count_matches_order_items(self):
        order = self._make_confirmed_order()
        order_item_count = order.items.count()
        bill = services.create_bill_from_order(order, self.cashier)
        self.assertEqual(bill.items.count(), order_item_count)

    def test_one_bill_item_per_order_item(self):
        """OneToOne constraint: each OrderItem maps to at most one BillItem."""
        order = self._make_confirmed_order()
        bill = services.create_bill_from_order(order, self.cashier)
        for order_item in order.items.all():
            count = BillItem.objects.filter(order_item=order_item).count()
            self.assertEqual(count, 1)
