# =============================================================================
# RestaurantFlow — Inventory Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date

from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from accounts import access as acl


class InventorySummaryTests(ReportingTestBase):

    def _make_inventory_fixtures(self):
        from inventory.models import (
            InventoryCategory, InventoryItem, StorageLocation, StockBalance,
        )
        category = InventoryCategory.objects.create(
            restaurant=self.restaurant_a, name="Grains",
        )
        item = InventoryItem.objects.create(
            restaurant=self.restaurant_a, category=category,
            name="Rice", sku="RICE-001", default_unit="KG",
            minimum_stock=Decimal("5.000"),
            reorder_level=Decimal("10.000"),
            average_cost=Decimal("50.00"),
        )
        location = StorageLocation.objects.create(
            branch=self.branch_a1, name="Main Store", code="MAIN",
            location_type="MAIN_STORE",
        )
        balance = StockBalance.objects.create(
            inventory_item=item,
            storage_location=location,
            quantity=Decimal("20.000"),
            average_cost=Decimal("50.00"),
        )
        return item, location, balance

    def test_inventory_summary_counts_items(self):
        self._make_inventory_fixtures()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_inventory_summary(branches)
        self.assertGreaterEqual(result["total_inventory_items"], 1)

    def test_stock_value_estimate_calculated(self):
        item, location, balance = self._make_inventory_fixtures()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_inventory_summary(branches)
        # 20 kg × 50/kg = 1000
        self.assertGreaterEqual(result["stock_value_estimate"], Decimal("1000.00"))

    def test_low_stock_detection(self):
        from inventory.models import (
            InventoryCategory, InventoryItem, StorageLocation, StockBalance
        )
        category = InventoryCategory.objects.create(
            restaurant=self.restaurant_a, name="Spices"
        )
        item = InventoryItem.objects.create(
            restaurant=self.restaurant_a, category=category,
            name="Salt", sku="SALT-001", default_unit="KG",
            reorder_level=Decimal("5.000"),
            average_cost=Decimal("10.00"),
        )
        location = StorageLocation.objects.create(
            branch=self.branch_a1, name="Spice Store", code="SPICE",
            location_type="OTHER",
        )
        # Quantity = 3, which is below reorder_level = 5 → LOW_STOCK
        StockBalance.objects.create(
            inventory_item=item,
            storage_location=location,
            quantity=Decimal("3.000"),
            average_cost=Decimal("10.00"),
        )
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_inventory_summary(branches)
        self.assertGreaterEqual(result["low_stock_items"], 1)

    def test_out_of_stock_detection(self):
        from inventory.models import (
            InventoryCategory, InventoryItem, StorageLocation, StockBalance
        )
        category = InventoryCategory.objects.create(
            restaurant=self.restaurant_a, name="Zero Stock Category"
        )
        item = InventoryItem.objects.create(
            restaurant=self.restaurant_a, category=category,
            name="Missing Item", sku="MISS-001", default_unit="PIECE",
            average_cost=Decimal("5.00"),
        )
        location = StorageLocation.objects.create(
            branch=self.branch_a1, name="Empty Store", code="EMPTY",
            location_type="OTHER",
        )
        StockBalance.objects.create(
            inventory_item=item,
            storage_location=location,
            quantity=Decimal("0.000"),
            average_cost=Decimal("5.00"),
        )
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_inventory_summary(branches)
        self.assertGreaterEqual(result["out_of_stock_items"], 1)

    def test_isolation_branch_b_sees_nothing(self):
        self._make_inventory_fixtures()
        branches_b = acl.get_accessible_branches(self.manager_b)
        result = agg.aggregate_inventory_summary(branches_b)
        self.assertEqual(result["total_inventory_items"], 0)
