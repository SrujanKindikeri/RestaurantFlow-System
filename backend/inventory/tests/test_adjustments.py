# =============================================================================
# RestaurantFlow — Stock Adjustment Tests
# Phase 10
#
# Tests:
#   - Adjustment IN: physical > system → ADJUSTMENT_IN movement
#   - Adjustment OUT: physical < system → ADJUSTMENT_OUT movement
#   - Zero difference: record created, no movement
#   - StockAdjustment linked to created movement
#   - Adjustment requires reason
#   - No permission raises
# =============================================================================

from decimal import Decimal

from rest_framework.exceptions import PermissionDenied, ValidationError

from inventory import services
from inventory.models import StockBalance, StockMovement, StockAdjustment
from inventory.constants import MOVEMENT_ADJUSTMENT_IN, MOVEMENT_ADJUSTMENT_OUT
from inventory.tests.base import InventoryTestBase


class TestStockAdjustment(InventoryTestBase):
    """Tests for services.create_stock_adjustment()."""

    def setUp(self):
        """Seed 100 KG before each test."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))

    def test_adjustment_in_increases_stock(self):
        """
        System: 100 KG, Physical: 105 KG → difference +5 → ADJUSTMENT_IN
        """
        adj = services.create_stock_adjustment(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            physical_quantity=Decimal("105.000"),
            unit="KG",
            reason="Monthly physical count audit",
            user=self.manager,
        )
        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.quantity, Decimal("105.000"))
        self.assertEqual(adj.quantity_difference, Decimal("5.000"))
        self.assertEqual(adj.quantity_before, Decimal("100.000"))
        self.assertEqual(adj.quantity_physical, Decimal("105.000"))

    def test_adjustment_out_decreases_stock(self):
        """
        System: 100 KG, Physical: 95 KG → difference -5 → ADJUSTMENT_OUT
        """
        adj = services.create_stock_adjustment(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            physical_quantity=Decimal("95.000"),
            unit="KG",
            reason="Quarterly physical count variance",
            user=self.manager,
        )
        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.quantity, Decimal("95.000"))
        self.assertEqual(adj.quantity_difference, Decimal("-5.000"))

    def test_adjustment_in_creates_movement(self):
        services.create_stock_adjustment(
            inventory_item=self.item_rice, storage_location=self.main_store,
            physical_quantity=Decimal("110.000"), unit="KG",
            reason="Year-end audit physical count check",
            user=self.manager,
        )
        self.assertTrue(
            StockMovement.objects.filter(
                inventory_item=self.item_rice,
                storage_location=self.main_store,
                movement_type=MOVEMENT_ADJUSTMENT_IN,
            ).exists()
        )

    def test_adjustment_out_creates_movement(self):
        services.create_stock_adjustment(
            inventory_item=self.item_rice, storage_location=self.main_store,
            physical_quantity=Decimal("90.000"), unit="KG",
            reason="Mid-year physical stock count reconciliation",
            user=self.manager,
        )
        self.assertTrue(
            StockMovement.objects.filter(
                inventory_item=self.item_rice,
                storage_location=self.main_store,
                movement_type=MOVEMENT_ADJUSTMENT_OUT,
            ).exists()
        )

    def test_zero_difference_records_without_movement(self):
        """System == Physical → no stock change, but audit record created."""
        adj = services.create_stock_adjustment(
            inventory_item=self.item_rice, storage_location=self.main_store,
            physical_quantity=Decimal("100.000"), unit="KG",
            reason="Verification count no discrepancy found",
            user=self.manager,
        )
        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.quantity, Decimal("100.000"))
        self.assertEqual(adj.quantity_difference, Decimal("0.000"))
        self.assertIsNone(adj.stock_movement)

    def test_adjustment_linked_to_movement(self):
        adj = services.create_stock_adjustment(
            inventory_item=self.item_rice, storage_location=self.main_store,
            physical_quantity=Decimal("120.000"), unit="KG",
            reason="Manual count during scheduled audit day",
            user=self.manager,
        )
        self.assertIsNotNone(adj.stock_movement)
        self.assertEqual(adj.stock_movement.movement_type, MOVEMENT_ADJUSTMENT_IN)

    def test_empty_reason_raises(self):
        with self.assertRaises(ValidationError):
            services.create_stock_adjustment(
                inventory_item=self.item_rice, storage_location=self.main_store,
                physical_quantity=Decimal("95.000"), unit="KG",
                reason="",  # empty
                user=self.manager,
            )

    def test_negative_physical_raises(self):
        with self.assertRaises(ValidationError):
            services.create_stock_adjustment(
                inventory_item=self.item_rice, storage_location=self.main_store,
                physical_quantity=Decimal("-1.000"), unit="KG",
                reason="Invalid negative count audit",
                user=self.manager,
            )

    def test_no_permission_raises(self):
        with self.assertRaises(PermissionDenied):
            services.create_stock_adjustment(
                inventory_item=self.item_rice, storage_location=self.main_store,
                physical_quantity=Decimal("95.000"), unit="KG",
                reason="Unauthorized adjustment attempt by staff",
                user=self.other_user,
            )
