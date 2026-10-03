# =============================================================================
# RestaurantFlow — Stock Service Tests
# Phase 10
#
# Tests:
#   - increase_stock: balance created, quantity updated, movement created
#   - increase_stock: weighted-average cost calculation
#   - decrease_stock: balance decremented, movement created
#   - decrease_stock: insufficient stock raises INSUFFICIENT_STOCK
#   - decrease_stock: exact available quantity succeeds
#   - decrease_stock: zero quantity raises
#   - No negative stock allowed (default)
#   - Weighted-average cost formula correctness
#   - generate_purchase_number: format, uniqueness, sequential
#   - generate_transfer_number: format, uniqueness
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from inventory import services
from inventory.models import StockBalance, StockMovement
from inventory.constants import MOVEMENT_PURCHASE, MOVEMENT_WASTAGE, MOVEMENT_ADJUSTMENT_IN
from inventory.tests.base import InventoryTestBase


class TestIncreaseStock(InventoryTestBase):
    """Tests for services.increase_stock()."""

    def test_creates_balance_if_not_exists(self):
        movement = services.increase_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("50.000"),
            unit_cost=Decimal("50.00"),
            movement_type=MOVEMENT_PURCHASE,
            performed_by=self.manager,
            reason="Initial stock",
        )
        balance = StockBalance.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
        )
        self.assertEqual(balance.quantity, Decimal("50.000"))
        self.assertIsNotNone(movement.pk)

    def test_increases_existing_balance(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        services.increase_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("50.000"),
            unit_cost=Decimal("60.00"),
            movement_type=MOVEMENT_PURCHASE,
            performed_by=self.manager,
        )
        balance = StockBalance.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
        )
        self.assertEqual(balance.quantity, Decimal("150.000"))

    def test_creates_stock_movement_record(self):
        services.increase_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("30.000"),
            unit_cost=Decimal("50.00"),
            movement_type=MOVEMENT_PURCHASE,
            performed_by=self.manager,
        )
        movement = StockMovement.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            movement_type=MOVEMENT_PURCHASE,
        )
        self.assertEqual(movement.quantity, Decimal("30.000"))
        self.assertEqual(movement.unit_cost, Decimal("50.00"))
        self.assertEqual(movement.total_cost, Decimal("1500.00"))
        self.assertEqual(movement.performed_by, self.manager)

    def test_weighted_average_cost_calculation(self):
        """
        Existing: 100 KG × ₹50
        New:       50 KG × ₹60
        Expected avg: (100×50 + 50×60) / 150 = 8000/150 = 53.33
        """
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        services.increase_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("50.000"),
            unit_cost=Decimal("60.00"),
            movement_type=MOVEMENT_PURCHASE,
            performed_by=self.manager,
        )
        balance = StockBalance.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
        )
        # (100*50 + 50*60) / 150 = 8000/150 = 53.333... → rounds to 53.33
        self.assertEqual(balance.average_cost, Decimal("53.33"))

    def test_zero_quantity_raises(self):
        with self.assertRaises(ValidationError):
            services.increase_stock(
                inventory_item=self.item_rice,
                storage_location=self.main_store,
                quantity=Decimal("0.000"),
                unit_cost=Decimal("50.00"),
                movement_type=MOVEMENT_PURCHASE,
                performed_by=self.manager,
            )

    def test_movement_performer_recorded(self):
        services.increase_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("10.000"),
            unit_cost=Decimal("50.00"),
            movement_type=MOVEMENT_PURCHASE,
            performed_by=self.inventory_staff,
        )
        m = StockMovement.objects.filter(
            inventory_item=self.item_rice,
            movement_type=MOVEMENT_PURCHASE,
        ).latest("created_at")
        self.assertEqual(m.performed_by, self.inventory_staff)


class TestDecreaseStock(InventoryTestBase):
    """Tests for services.decrease_stock()."""

    def setUp(self):
        """Seed 100 KG for each test."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))

    def test_decreases_balance(self):
        services.decrease_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("30.000"),
            movement_type=MOVEMENT_WASTAGE,
            performed_by=self.manager,
        )
        balance = StockBalance.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
        )
        self.assertEqual(balance.quantity, Decimal("70.000"))

    def test_creates_movement_record(self):
        services.decrease_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("5.000"),
            movement_type=MOVEMENT_WASTAGE,
            performed_by=self.manager,
        )
        m = StockMovement.objects.filter(
            inventory_item=self.item_rice,
            movement_type=MOVEMENT_WASTAGE,
        ).latest("created_at")
        self.assertEqual(m.quantity, Decimal("5.000"))

    def test_exact_available_quantity_succeeds(self):
        """Decreasing exactly the available quantity is allowed."""
        services.decrease_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("100.000"),
            movement_type=MOVEMENT_WASTAGE,
            performed_by=self.manager,
        )
        balance = StockBalance.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
        )
        self.assertEqual(balance.quantity, Decimal("0.000"))

    def test_insufficient_stock_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            services.decrease_stock(
                inventory_item=self.item_rice,
                storage_location=self.main_store,
                quantity=Decimal("101.000"),  # 1 more than available
                movement_type=MOVEMENT_WASTAGE,
                performed_by=self.manager,
            )
        self.assertEqual(ctx.exception.detail["code"], "INSUFFICIENT_STOCK")

    def test_no_negative_stock_default(self):
        """Stock never goes below zero."""
        services.decrease_stock(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("100.000"),
            movement_type=MOVEMENT_WASTAGE,
            performed_by=self.manager,
        )
        balance = StockBalance.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
        )
        self.assertEqual(balance.quantity, Decimal("0.000"))
        # Cannot go further
        with self.assertRaises(ValidationError) as ctx:
            services.decrease_stock(
                inventory_item=self.item_rice,
                storage_location=self.main_store,
                quantity=Decimal("1.000"),
                movement_type=MOVEMENT_WASTAGE,
                performed_by=self.manager,
            )
        self.assertEqual(ctx.exception.detail["code"], "INSUFFICIENT_STOCK")

    def test_zero_quantity_raises(self):
        with self.assertRaises(ValidationError):
            services.decrease_stock(
                inventory_item=self.item_rice,
                storage_location=self.main_store,
                quantity=Decimal("0.000"),
                movement_type=MOVEMENT_WASTAGE,
                performed_by=self.manager,
            )

    def test_no_balance_raises_insufficient(self):
        """No existing balance → INSUFFICIENT_STOCK."""
        with self.assertRaises(ValidationError) as ctx:
            services.decrease_stock(
                inventory_item=self.item_milk,
                storage_location=self.main_store,
                quantity=Decimal("10.000"),
                movement_type=MOVEMENT_WASTAGE,
                performed_by=self.manager,
            )
        self.assertEqual(ctx.exception.detail["code"], "INSUFFICIENT_STOCK")


class TestWeightedAverageCost(TestCase):
    """Pure unit tests for calculate_weighted_average_cost()."""

    def test_basic_formula(self):
        """(100×50 + 50×60) / 150 = 53.33"""
        result = services.calculate_weighted_average_cost(
            old_qty=Decimal("100"),
            old_cost=Decimal("50.00"),
            new_qty=Decimal("50"),
            new_cost=Decimal("60.00"),
        )
        self.assertEqual(result, Decimal("53.33"))

    def test_equal_quantities(self):
        """(10×40 + 10×60) / 20 = 50.00"""
        result = services.calculate_weighted_average_cost(
            old_qty=Decimal("10"),
            old_cost=Decimal("40.00"),
            new_qty=Decimal("10"),
            new_cost=Decimal("60.00"),
        )
        self.assertEqual(result, Decimal("50.00"))

    def test_zero_existing_stock(self):
        """Starting from 0 → new cost is the average."""
        result = services.calculate_weighted_average_cost(
            old_qty=Decimal("0"),
            old_cost=Decimal("0.00"),
            new_qty=Decimal("50"),
            new_cost=Decimal("75.00"),
        )
        self.assertEqual(result, Decimal("75.00"))

    def test_zero_total_returns_zero(self):
        result = services.calculate_weighted_average_cost(
            old_qty=Decimal("0"),
            old_cost=Decimal("0.00"),
            new_qty=Decimal("0"),
            new_cost=Decimal("0.00"),
        )
        self.assertEqual(result, Decimal("0.00"))


class TestPurchaseNumberGeneration(InventoryTestBase):
    """Tests for generate_purchase_number()."""

    def test_format(self):
        from django.db import transaction
        with transaction.atomic():
            number = services.generate_purchase_number(self.restaurant)
        self.assertTrue(number.startswith("PO-"))
        parts = number.split("-")
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[1]), 6)

    def test_sequential(self):
        from django.db import transaction
        with transaction.atomic():
            n1 = services.generate_purchase_number(self.restaurant)
        with transaction.atomic():
            n2 = services.generate_purchase_number(self.restaurant)
        seq1 = int(n1.split("-")[1])
        seq2 = int(n2.split("-")[1])
        self.assertEqual(seq2, seq1 + 1)

    def test_unique_across_calls(self):
        from django.db import transaction
        numbers = set()
        for _ in range(5):
            with transaction.atomic():
                numbers.add(services.generate_purchase_number(self.restaurant))
        self.assertEqual(len(numbers), 5)


class TestTransferNumberGeneration(InventoryTestBase):
    """Tests for generate_transfer_number()."""

    def test_format(self):
        from django.db import transaction
        with transaction.atomic():
            number = services.generate_transfer_number(self.restaurant)
        self.assertTrue(number.startswith("TR-"))

    def test_sequential(self):
        from django.db import transaction
        with transaction.atomic():
            n1 = services.generate_transfer_number(self.restaurant)
        with transaction.atomic():
            n2 = services.generate_transfer_number(self.restaurant)
        self.assertNotEqual(n1, n2)
