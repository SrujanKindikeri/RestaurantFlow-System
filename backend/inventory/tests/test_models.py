# =============================================================================
# RestaurantFlow — Inventory Model Tests
# Phase 10
#
# Tests:
#   - InventoryCategory uniqueness per restaurant
#   - InventoryItem SKU uniqueness per restaurant
#   - StorageLocation code uniqueness per branch
#   - StockBalance uniqueness constraint (item + location)
#   - StockBalance.available_quantity property
#   - StockBalance.get_stock_status() derivation
#   - InventoryItem default values
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from django.db import IntegrityError

from inventory.models import (
    InventoryCategory, InventoryItem, StorageLocation, StockBalance,
)
from inventory.tests.base import InventoryTestBase


class TestInventoryCategoryModel(InventoryTestBase):
    """Model-level tests for InventoryCategory."""

    def test_category_str(self):
        self.assertIn("Dry Goods", str(self.cat_dry))
        self.assertIn("Test Restaurant", str(self.cat_dry))

    def test_duplicate_category_name_same_restaurant_raises(self):
        with self.assertRaises(Exception):
            InventoryCategory.objects.create(
                restaurant=self.restaurant,
                name="Dry Goods",  # duplicate
            )

    def test_same_name_different_restaurant_allowed(self):
        """Two restaurants can have the same category name."""
        from organizations.models import Restaurant
        other_restaurant = Restaurant.objects.create(
            organization=self.org,
            name="Other Restaurant",
            slug="other-restaurant",
            code="OR01",
        )
        cat = InventoryCategory.objects.create(
            restaurant=other_restaurant,
            name="Dry Goods",  # same name, different restaurant
        )
        self.assertIsNotNone(cat.pk)

    def test_is_active_default_true(self):
        self.assertTrue(self.cat_dry.is_active)


class TestInventoryItemModel(InventoryTestBase):
    """Model-level tests for InventoryItem."""

    def test_item_str(self):
        s = str(self.item_rice)
        self.assertIn("Rice", s)
        self.assertIn("RICE-001", s)

    def test_duplicate_sku_same_restaurant_raises(self):
        with self.assertRaises(Exception):
            InventoryItem.objects.create(
                restaurant=self.restaurant,
                name="Rice Duplicate",
                sku="RICE-001",  # duplicate SKU
                default_unit="KG",
            )

    def test_decimal_fields_are_decimal(self):
        self.assertIsInstance(self.item_rice.minimum_stock, Decimal)
        self.assertIsInstance(self.item_rice.reorder_level, Decimal)
        self.assertIsInstance(self.item_rice.average_cost, Decimal)

    def test_is_active_default_true(self):
        self.assertTrue(self.item_rice.is_active)


class TestStorageLocationModel(InventoryTestBase):
    """Model-level tests for StorageLocation."""

    def test_location_str(self):
        s = str(self.main_store)
        self.assertIn("Main Store", s)
        self.assertIn("MAIN", s)

    def test_duplicate_code_same_branch_raises(self):
        with self.assertRaises(Exception):
            StorageLocation.objects.create(
                branch=self.branch,
                name="Another Main",
                code="MAIN",  # duplicate
                location_type="MAIN_STORE",
            )

    def test_same_code_different_branch_allowed(self):
        loc = StorageLocation.objects.create(
            branch=self.other_branch,
            name="Main Store",
            code="MAIN",  # same code, different branch
            location_type="MAIN_STORE",
        )
        self.assertIsNotNone(loc.pk)


class TestStockBalanceModel(InventoryTestBase):
    """Model-level tests for StockBalance."""

    def test_available_quantity_property(self):
        balance = self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"))
        balance.reserved_quantity = Decimal("10.000")
        balance.save(update_fields=["reserved_quantity", "updated_at"])
        balance.refresh_from_db()
        self.assertEqual(balance.available_quantity, Decimal("90.000"))

    def test_available_quantity_zero_reserved(self):
        balance = self._seed_balance(self.item_rice, self.main_store, Decimal("50.000"))
        self.assertEqual(balance.available_quantity, Decimal("50.000"))

    def test_stock_status_in_stock(self):
        """available > reorder_level → IN_STOCK"""
        # rice reorder_level = 10.000
        balance = self._seed_balance(self.item_rice, self.main_store, Decimal("50.000"))
        self.assertEqual(balance.get_stock_status(), "IN_STOCK")

    def test_stock_status_low_stock(self):
        """available <= reorder_level → LOW_STOCK"""
        # rice reorder_level = 10.000
        balance = self._seed_balance(self.item_rice, self.main_store, Decimal("10.000"))
        self.assertEqual(balance.get_stock_status(), "LOW_STOCK")

    def test_stock_status_out_of_stock(self):
        """available == 0 → OUT_OF_STOCK"""
        balance = self._seed_balance(self.item_rice, self.main_store, Decimal("0.000"))
        self.assertEqual(balance.get_stock_status(), "OUT_OF_STOCK")

    def test_uniqueness_constraint_item_location(self):
        """Two StockBalance rows for same (item, location) must raise."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"))
        with self.assertRaises(Exception):
            StockBalance.objects.create(
                inventory_item=self.item_rice,
                storage_location=self.main_store,
                quantity=Decimal("50.000"),
            )
