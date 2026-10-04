# =============================================================================
# RestaurantFlow — Reporting Isolation Tests
# Phase 14
#
# Verifies that data from one restaurant/company never leaks to another.
# =============================================================================

from decimal import Decimal
from datetime import date

from reporting.tests.base import ReportingTestBase
from reporting.selectors import (
    select_sales_summary,
    select_menu_items,
    select_orders_summary,
    select_payment_summary,
    select_kitchen_performance,
    select_inventory_summary,
)


class OrganisationIsolationTests(ReportingTestBase):

    def test_sales_org_a_invisible_to_org_b(self):
        # Create data in Org A
        self._make_finalized_bill()
        # Query as manager_b (Org B)
        result = select_sales_summary(self.manager_b, date.today(), date.today())
        self.assertEqual(result["number_of_bills"], 0)
        self.assertEqual(result["net_sales"], Decimal("0.00"))

    def test_menu_items_org_a_invisible_to_org_b(self):
        self._make_finalized_bill()
        result = select_menu_items(self.manager_b, date.today(), date.today())
        self.assertEqual(result, [])

    def test_orders_org_a_invisible_to_org_b(self):
        self._make_order()
        result = select_orders_summary(self.manager_b, date.today(), date.today())
        self.assertEqual(result["total_orders"], 0)

    def test_payments_org_a_invisible_to_org_b(self):
        bill = self._make_finalized_bill()
        self._make_payment(bill)
        result = select_payment_summary(self.manager_b, date.today(), date.today())
        self.assertEqual(result["payment_count"], 0)

    def test_kitchen_org_a_invisible_to_org_b(self):
        from kitchen.models import KitchenOrder, KitchenOrderStatus
        from django.utils import timezone as tz
        order = self._make_order()
        KitchenOrder.objects.create(
            order=order, branch=self.branch_a1,
            status=KitchenOrderStatus.READY, received_at=tz.now(),
        )
        result = select_kitchen_performance(self.manager_b, date.today(), date.today())
        self.assertEqual(result["orders_received"], 0)

    def test_inventory_org_a_invisible_to_org_b(self):
        from inventory.models import (
            InventoryCategory, InventoryItem, StorageLocation, StockBalance
        )
        cat = InventoryCategory.objects.create(restaurant=self.restaurant_a, name="Dairy")
        item = InventoryItem.objects.create(
            restaurant=self.restaurant_a, category=cat,
            name="Milk", sku="MILK-001", default_unit="LITRE",
            average_cost=Decimal("30.00"),
        )
        loc = StorageLocation.objects.create(
            branch=self.branch_a1, name="Cold Store", code="COLD", location_type="COLD_STORAGE",
        )
        StockBalance.objects.create(
            inventory_item=item, storage_location=loc,
            quantity=Decimal("10.000"), average_cost=Decimal("30.00"),
        )
        result = select_inventory_summary(self.manager_b)
        self.assertEqual(result["total_inventory_items"], 0)

    def test_owner_a_only_sees_restaurant_a(self):
        """owner_a should see A1+A2 but never Branch B1."""
        bill_a = self._make_finalized_bill()  # Branch A1
        result = select_sales_summary(
            self.owner_a, date.today(), date.today(),
            restaurant_id=str(self.restaurant_a.pk),
        )
        self.assertEqual(result["number_of_bills"], 1)

    def test_invalid_restaurant_id_raises_scope_error(self):
        from reporting.exceptions import ReportScopeError
        with self.assertRaises(ReportScopeError):
            select_sales_summary(
                self.manager_b,
                date.today(), date.today(),
                restaurant_id=str(self.restaurant_a.pk),  # wrong org
            )
