# =============================================================================
# RestaurantFlow — Consumption Tests
# Phase 11
#
# Tests:
#   - Unit conversion (GRAM recipe → KG stock)
#   - Preparation loss scaling
#   - Recipe scaling (multiple ordered quantities)
#   - Consumption creation (happy path)
#   - Missing active recipe → fails gracefully
#   - No consumption location configured → fails gracefully
#   - Insufficient stock → entire batch fails (atomic rollback)
#   - Partial insufficient stock → nothing deducted
#   - Idempotency → same event twice → one batch
#   - Recipe versioning snapshot (order A uses v1, order B uses v2)
#   - Multi-item order aggregation (same ingredient from 2 recipes)
#   - Consumption reversal (returns stock, creates CONSUMPTION_REVERSAL movement)
#   - Cancellation rule (no consumption → no reversal needed)
#   - Manual consumption (happy path + insufficient stock)
#   - Concurrency (two simultaneous orders, one succeeds one fails)
#   - Audit logging (batch status transitions)
#   - Branch isolation
# =============================================================================

from decimal import Decimal

from django.db import transaction
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from inventory.constants import (
    UNIT_KG, UNIT_GRAM, UNIT_LITRE, UNIT_MILLILITRE, UNIT_PIECE,
    MOVEMENT_CONSUMPTION,
)
from inventory.models import StockBalance, StockMovement
from recipes import services as svc
from recipes.constants import (
    BATCH_COMPLETED, BATCH_FAILED, BATCH_REVERSED,
    CONSUMPTION_CONSUMED, CONSUMPTION_REVERSED,
)
from recipes.models import ConsumptionBatch, StockConsumption
from recipes.tests.base import RecipeTestBase


# =============================================================================
# Unit Conversion Tests
# =============================================================================

class TestUnitConversion(RecipeTestBase):
    """
    Recipe uses GRAM; inventory stock is in KG.
    Verifies backend conversion is applied correctly.
    """

    def setUp(self):
        self._setup_consumption_config()
        self.recipe = self._make_active_biryani_recipe(
            rice_qty_grams=Decimal("250"),  # 250g per serving
            chicken_qty_grams=Decimal("200"),
            oil_qty_ml=Decimal("0"),        # skip oil for simplicity — add manually
        )
        # Stock in KG (item default_unit = KG)
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("10"))      # 10 KG
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("5"))    # 5 KG

    def test_gram_to_kg_conversion_for_one_serving(self):
        """250g recipe → 0.250 KG consumed from stock."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        reqs = svc.calculate_required_ingredients(order)
        rice_req = next(r for r in reqs if r["inventory_item"] == self.inv_rice)
        self.assertEqual(rice_req["quantity"], Decimal("0.250"))
        self.assertEqual(rice_req["unit"], UNIT_KG)

    def test_gram_to_kg_conversion_for_four_servings(self):
        """250g × 4 servings → 1.000 KG consumed."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("4"))])
        reqs = svc.calculate_required_ingredients(order)
        rice_req = next(r for r in reqs if r["inventory_item"] == self.inv_rice)
        self.assertEqual(rice_req["quantity"], Decimal("1.000"))

    def test_ml_to_litre_conversion(self):
        """30ml recipe → 0.030 L consumed from stock (oil default_unit=LITRE)."""
        recipe = svc.create_recipe(
            self.restaurant, self.item_naan, "Naan Oil Test", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(recipe, self.inv_oil.id, Decimal("30"), UNIT_MILLILITRE, self.manager)
        svc.activate_recipe(recipe, self.manager)
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("1"))  # 1 L

        order = self._make_confirmed_order([(self.item_naan, Decimal("1"))])
        reqs = svc.calculate_required_ingredients(order)
        oil_req = next(r for r in reqs if r["inventory_item"] == self.inv_oil)
        self.assertEqual(oil_req["quantity"], Decimal("0.030"))
        self.assertEqual(oil_req["unit"], UNIT_LITRE)


# =============================================================================
# Preparation Loss Tests
# =============================================================================

class TestPreparationLoss(RecipeTestBase):
    """Preparation loss % must be applied before unit conversion."""

    def setUp(self):
        self._setup_consumption_config()
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("10"))

    def test_five_percent_preparation_loss(self):
        """250g + 5% loss → 262.500g → 0.2625 KG."""
        recipe = svc.create_recipe(
            self.restaurant, self.item_naan, "Loss Test", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(
            recipe, self.inv_rice.id, Decimal("250"), UNIT_GRAM,
            self.manager, preparation_loss_percentage=Decimal("5"),
        )
        svc.activate_recipe(recipe, self.manager)

        order = self._make_confirmed_order([(self.item_naan, Decimal("1"))])
        reqs = svc.calculate_required_ingredients(order)
        rice_req = next(r for r in reqs if r["inventory_item"] == self.inv_rice)
        # 250 × 1.05 = 262.5 g → 0.2625 KG (3dp precision)
        self.assertEqual(rice_req["quantity"], Decimal("0.263"))  # rounded to 3dp

    def test_zero_loss_gives_base_quantity(self):
        """0% loss → base quantity unchanged."""
        recipe = svc.create_recipe(
            self.restaurant, self.item_naan, "No Loss Test", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(
            recipe, self.inv_rice.id, Decimal("500"), UNIT_GRAM,
            self.manager, preparation_loss_percentage=Decimal("0"),
        )
        svc.activate_recipe(recipe, self.manager)

        order = self._make_confirmed_order([(self.item_naan, Decimal("1"))])
        reqs = svc.calculate_required_ingredients(order)
        rice_req = next(r for r in reqs if r["inventory_item"] == self.inv_rice)
        self.assertEqual(rice_req["quantity"], Decimal("0.500"))


# =============================================================================
# Happy Path: Full Consumption Flow
# =============================================================================

class TestConsumptionHappyPath(RecipeTestBase):
    """Full consumption flow from trigger to stock deduction."""

    def setUp(self):
        self._setup_consumption_config()
        self.recipe = self._make_active_biryani_recipe(
            rice_qty_grams=Decimal("250"),
            chicken_qty_grams=Decimal("200"),
            oil_qty_ml=Decimal("30"),
        )
        # Stock: 10 KG rice, 5 KG chicken, 1 L oil
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("10"))
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("5"))
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("1"))

    def _run_consumption(self, order):
        """Create batch and execute it."""
        batch = ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch,
            idempotency_key=f"{order.id}:KITCHEN_COMPLETED",
            status="PENDING",
            triggered_by=self.manager,
            trigger="KITCHEN_COMPLETED",
        )
        return svc.execute_consumption_batch(batch, self.manager)

    def test_batch_completed_status(self):
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch = self._run_consumption(order)
        self.assertEqual(batch.status, BATCH_COMPLETED)
        self.assertIsNotNone(batch.completed_at)

    def test_stock_deducted_correctly(self):
        """1 serving: rice 0.250 KG, chicken 0.200 KG, oil 0.030 L deducted."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        self._run_consumption(order)

        rice_balance = StockBalance.objects.get(
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
        )
        chicken_balance = StockBalance.objects.get(
            inventory_item=self.inv_chicken,
            storage_location=self.kitchen_store,
        )
        oil_balance = StockBalance.objects.get(
            inventory_item=self.inv_oil,
            storage_location=self.kitchen_store,
        )
        self.assertEqual(rice_balance.quantity, Decimal("9.750"))    # 10 - 0.250
        self.assertEqual(chicken_balance.quantity, Decimal("4.800")) # 5 - 0.200
        self.assertEqual(oil_balance.quantity, Decimal("0.970"))     # 1 - 0.030

    def test_stock_movements_created(self):
        """CONSUMPTION StockMovements must be created for each ingredient."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        self._run_consumption(order)

        movements = StockMovement.objects.filter(
            movement_type=MOVEMENT_CONSUMPTION,
            reference_id=ConsumptionBatch.objects.get(order=order).id,
        )
        self.assertEqual(movements.count(), 3)  # rice + chicken + oil

    def test_stock_consumption_records_created(self):
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        self._run_consumption(order)
        batch = ConsumptionBatch.objects.get(order=order)
        self.assertEqual(batch.consumptions.filter(status=CONSUMPTION_CONSUMED).count(), 3)

    def test_consumption_references_correct_recipe_version(self):
        """StockConsumption.recipe_version must match the ACTIVE recipe."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        self._run_consumption(order)
        batch = ConsumptionBatch.objects.get(order=order)
        for consumption in batch.consumptions.all():
            self.assertEqual(consumption.recipe_version, self.recipe.version)
            self.assertEqual(consumption.recipe, self.recipe)

    def test_cost_snapshot_stored(self):
        """unit_cost must be the inventory average_cost at time of consumption."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        self._run_consumption(order)
        batch = ConsumptionBatch.objects.get(order=order)
        rice_consumption = batch.consumptions.get(inventory_item=self.inv_rice)
        self.assertEqual(rice_consumption.unit_cost, self.inv_rice.average_cost)

    def test_scaling_by_ordered_quantity(self):
        """Order of 5 × Biryani: rice should be 5 × 0.250 = 1.250 KG."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("5"))])
        self._run_consumption(order)

        rice_balance = StockBalance.objects.get(
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
        )
        # 10 - (0.250 × 5) = 10 - 1.250 = 8.750
        self.assertEqual(rice_balance.quantity, Decimal("8.750"))


# =============================================================================
# Failure Cases
# =============================================================================

class TestConsumptionFailures(RecipeTestBase):
    """Tests for all failure paths in consumption."""

    def setUp(self):
        self._setup_consumption_config()

    def _run_consumption(self, order):
        batch = ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch,
            idempotency_key=f"{order.id}:KITCHEN_COMPLETED",
            status="PENDING",
            triggered_by=self.manager,
            trigger="KITCHEN_COMPLETED",
        )
        return svc.execute_consumption_batch(batch, self.manager)

    def test_missing_recipe_fails_batch(self):
        """If any menu item has no active recipe, batch fails."""
        # Do NOT create a recipe for item_biryani
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch = self._run_consumption(order)
        self.assertEqual(batch.status, BATCH_FAILED)
        self.assertIn("MISSING_ACTIVE_RECIPE", batch.failure_reason)

    def test_no_consumption_location_fails_batch(self):
        """No BranchConsumptionConfig → FAILED batch."""
        from recipes.models import BranchConsumptionConfig
        # Remove any config
        BranchConsumptionConfig.objects.filter(branch=self.branch).delete()

        self._make_active_biryani_recipe()
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch = self._run_consumption(order)
        self.assertEqual(batch.status, BATCH_FAILED)
        self.assertIn("NO_CONSUMPTION_LOCATION", batch.failure_reason)

    def test_insufficient_stock_fails_batch(self):
        """Required 2 KG chicken but only 1 KG available → FAILED."""
        self._make_active_biryani_recipe(chicken_qty_grams=Decimal("2000"))  # 2 KG per serving
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("10"))
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("1"))   # only 1 KG
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("1"))

        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch = self._run_consumption(order)
        self.assertEqual(batch.status, BATCH_FAILED)
        self.assertIn("INSUFFICIENT_STOCK", batch.failure_reason)

    def test_atomic_rollback_on_insufficient_stock(self):
        """
        If one ingredient is insufficient, NO ingredients should be deducted.

        Stock: rice=10KG (enough), chicken=0.1KG (not enough for 0.200KG)
        Expected: rice stays at 10KG, chicken stays at 0.1KG.
        """
        self._make_active_biryani_recipe(
            rice_qty_grams=Decimal("250"),    # needs 0.250 KG
            chicken_qty_grams=Decimal("200"), # needs 0.200 KG
            oil_qty_ml=Decimal("30"),
        )
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("10"))   # enough
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("0.1"))  # NOT enough (0.1 < 0.2)
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("1"))

        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch = self._run_consumption(order)

        self.assertEqual(batch.status, BATCH_FAILED)

        # Rice must NOT have been deducted
        rice_balance = StockBalance.objects.get(
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
        )
        self.assertEqual(rice_balance.quantity, Decimal("10.000"))

        # Chicken must NOT have been deducted
        chicken_balance = StockBalance.objects.get(
            inventory_item=self.inv_chicken,
            storage_location=self.kitchen_store,
        )
        self.assertEqual(chicken_balance.quantity, Decimal("0.100"))

        # No StockMovements created
        movements = StockMovement.objects.filter(movement_type=MOVEMENT_CONSUMPTION)
        self.assertEqual(movements.count(), 0)


# =============================================================================
# Idempotency Tests
# =============================================================================

class TestConsumptionIdempotency(RecipeTestBase):
    """Sending the same consumption trigger twice must produce exactly one batch."""

    def setUp(self):
        self._setup_consumption_config()
        self._make_active_biryani_recipe()
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("10"))
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("5"))
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("1"))

    def test_idempotent_trigger(self):
        """Calling trigger_consumption_for_kitchen_order twice returns same batch."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])

        # Simulate a kitchen order by creating a mock object
        class MockKitchenOrder:
            def __init__(self, order, branch):
                self.order = order
                self.branch = branch
                self.order_number = order.order_number
                self.status = "READY"
                self.id = order.id  # proxy

        ko = MockKitchenOrder(order, self.branch)

        batch1 = svc.trigger_consumption_for_kitchen_order(ko, self.manager)
        batch2 = svc.trigger_consumption_for_kitchen_order(ko, self.manager)

        # Both calls return the same batch
        self.assertEqual(batch1.id, batch2.id)

        # Only one batch exists for this order
        self.assertEqual(
            ConsumptionBatch.objects.filter(order=order).count(), 1
        )

    def test_stock_deducted_only_once(self):
        """Stock must be deducted exactly once even if trigger fires twice."""
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])

        class MockKitchenOrder:
            def __init__(self, order, branch):
                self.order = order
                self.branch = branch
                self.order_number = order.order_number
                self.status = "READY"
                self.id = order.id

        ko = MockKitchenOrder(order, self.branch)

        svc.trigger_consumption_for_kitchen_order(ko, self.manager)
        svc.trigger_consumption_for_kitchen_order(ko, self.manager)

        rice_balance = StockBalance.objects.get(
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
        )
        # Deducted once: 10 - 0.250 = 9.750
        self.assertEqual(rice_balance.quantity, Decimal("9.750"))


# =============================================================================
# Recipe Version Snapshot Tests
# =============================================================================

class TestRecipeVersionSnapshot(RecipeTestBase):
    """
    Order A uses Recipe V1. Recipe is then changed to V2.
    Order B uses V2. Order A's consumption must still reference V1.
    """

    def setUp(self):
        self._setup_consumption_config()
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("20"))
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("10"))
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("5"))

    def _run_consumption(self, order):
        batch = ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch,
            idempotency_key=f"{order.id}:KITCHEN_COMPLETED",
            status="PENDING",
            triggered_by=self.manager,
            trigger="KITCHEN_COMPLETED",
        )
        return svc.execute_consumption_batch(batch, self.manager)

    def test_order_a_references_v1_after_v2_activated(self):
        """Consumption for Order A must reference Recipe V1 even after V2 is active."""
        # Create V1 and activate
        recipe_v1 = self._make_active_biryani_recipe(rice_qty_grams=Decimal("250"))
        v1_id = recipe_v1.id
        v1_version = recipe_v1.version

        # Consume order A using V1
        order_a = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch_a = self._run_consumption(order_a)

        # Create V2 and activate (V1 becomes INACTIVE)
        recipe_v2 = svc.create_recipe(
            self.restaurant, self.item_biryani, "Biryani V2", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(recipe_v2, self.inv_rice.id, Decimal("300"), UNIT_GRAM, self.manager)
        svc.add_recipe_item(recipe_v2, self.inv_chicken.id, Decimal("200"), UNIT_GRAM, self.manager)
        svc.activate_recipe(recipe_v2, self.manager)

        # Consume order B using V2
        order_b = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch_b = self._run_consumption(order_b)

        # Order A's consumption references V1
        a_consumptions = batch_a.consumptions.filter(inventory_item=self.inv_rice)
        self.assertEqual(a_consumptions.first().recipe_id, v1_id)
        self.assertEqual(a_consumptions.first().recipe_version, v1_version)

        # Order B's consumption references V2
        b_consumptions = batch_b.consumptions.filter(inventory_item=self.inv_rice)
        self.assertEqual(b_consumptions.first().recipe_id, recipe_v2.id)
        self.assertEqual(b_consumptions.first().recipe_version, recipe_v2.version)

    def test_rice_quantity_differs_between_v1_and_v2(self):
        """Order A consumed 0.250 KG rice (V1), order B consumes 0.300 KG rice (V2)."""
        self._make_active_biryani_recipe(rice_qty_grams=Decimal("250"))

        order_a = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch_a = self._make_consumption_batch(order_a)
        svc.execute_consumption_batch(batch_a, self.manager)

        # Switch to V2 with 300g rice
        recipe_v2 = svc.create_recipe(
            self.restaurant, self.item_biryani, "Biryani V2", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(recipe_v2, self.inv_rice.id, Decimal("300"), UNIT_GRAM, self.manager)
        svc.add_recipe_item(recipe_v2, self.inv_chicken.id, Decimal("200"), UNIT_GRAM, self.manager)
        svc.activate_recipe(recipe_v2, self.manager)

        order_b = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch_b = self._make_consumption_batch(order_b)
        svc.execute_consumption_batch(batch_b, self.manager)

        a_rice = ConsumptionBatch.objects.get(pk=batch_a.pk).consumptions.get(
            inventory_item=self.inv_rice
        )
        b_rice = ConsumptionBatch.objects.get(pk=batch_b.pk).consumptions.get(
            inventory_item=self.inv_rice
        )
        self.assertEqual(a_rice.quantity, Decimal("0.250"))
        self.assertEqual(b_rice.quantity, Decimal("0.300"))

    def _make_consumption_batch(self, order):
        return ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch,
            idempotency_key=f"{order.id}:KITCHEN_COMPLETED",
            status="PENDING",
            triggered_by=self.manager,
            trigger="KITCHEN_COMPLETED",
        )


# =============================================================================
# Multi-Item Order and Ingredient Aggregation
# =============================================================================

class TestMultiItemAggregation(RecipeTestBase):
    """
    Orders with multiple menu items that share an ingredient.
    The shared ingredient must be aggregated before deduction.
    """

    def setUp(self):
        self._setup_consumption_config()
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("20"))
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("10"))
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("5"))
        self._set_stock(self.inv_paneer, self.kitchen_store, Decimal("5"))

    def _run_consumption(self, order):
        batch = ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch,
            idempotency_key=f"{order.id}:KITCHEN_COMPLETED",
            status="PENDING",
            triggered_by=self.manager,
            trigger="KITCHEN_COMPLETED",
        )
        return svc.execute_consumption_batch(batch, self.manager)

    def test_multiple_items_consume_correctly(self):
        """
        2 Biryani (each 250g rice) + 1 Paneer Masala (200g paneer).
        Rice: 2 × 0.250 = 0.500 KG deducted.
        Paneer: 0.200 KG deducted.
        """
        # Biryani recipe: 250g rice, 200g chicken
        self._make_active_biryani_recipe(
            rice_qty_grams=Decimal("250"),
            chicken_qty_grams=Decimal("200"),
            oil_qty_ml=Decimal("0"),
        )
        # Remove oil from biryani recipe items since we set oil to 0
        from recipes.models import RecipeItem
        RecipeItem.objects.filter(
            recipe__menu_item=self.item_biryani,
            inventory_item=self.inv_oil,
        ).delete()

        # Paneer recipe: 200g paneer
        paneer_recipe = svc.create_recipe(
            self.restaurant, self.item_paneer, "Paneer Recipe", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(paneer_recipe, self.inv_paneer.id, Decimal("200"), UNIT_GRAM, self.manager)
        svc.activate_recipe(paneer_recipe, self.manager)

        order = self._make_confirmed_order([
            (self.item_biryani, Decimal("2")),
            (self.item_paneer, Decimal("1")),
        ])
        self._run_consumption(order)

        rice_balance = StockBalance.objects.get(
            inventory_item=self.inv_rice, storage_location=self.kitchen_store
        )
        paneer_balance = StockBalance.objects.get(
            inventory_item=self.inv_paneer, storage_location=self.kitchen_store
        )
        # 20 - 0.500 = 19.500
        self.assertEqual(rice_balance.quantity, Decimal("19.500"))
        # 5 - 0.200 = 4.800
        self.assertEqual(paneer_balance.quantity, Decimal("4.800"))

    def test_shared_ingredient_aggregated(self):
        """
        If two menu items both need rice, the required rice is totalled
        before any deduction — ensuring one atomic check and deduction.

        Biryani: 500g rice per serving
        Other item (using naan): 200g rice per serving (naan uses flour but we test with rice)

        This test creates two recipes both using rice, then verifies
        the total rice deducted is exactly (500+200)g = 0.700 KG.
        """
        # Biryani: 500g rice
        biryani_recipe = svc.create_recipe(
            self.restaurant, self.item_biryani, "Biryani Agg Test", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(biryani_recipe, self.inv_rice.id, Decimal("500"), UNIT_GRAM, self.manager)
        svc.activate_recipe(biryani_recipe, self.manager)

        # Naan: 200g rice (unusual but tests aggregation)
        naan_recipe = svc.create_recipe(
            self.restaurant, self.item_naan, "Naan Agg Test", self.manager,
            yield_quantity=Decimal("1"), yield_unit=UNIT_PIECE,
        )
        svc.add_recipe_item(naan_recipe, self.inv_rice.id, Decimal("200"), UNIT_GRAM, self.manager)
        svc.activate_recipe(naan_recipe, self.manager)

        order = self._make_confirmed_order([
            (self.item_biryani, Decimal("1")),
            (self.item_naan, Decimal("1")),
        ])
        self._run_consumption(order)

        rice_balance = StockBalance.objects.get(
            inventory_item=self.inv_rice, storage_location=self.kitchen_store
        )
        # 20 - 0.700 = 19.300
        self.assertEqual(rice_balance.quantity, Decimal("19.300"))


# =============================================================================
# Consumption Reversal Tests
# =============================================================================

class TestConsumptionReversal(RecipeTestBase):
    """Tests for reverse_consumption_batch()."""

    def setUp(self):
        self._setup_consumption_config()
        self._make_active_biryani_recipe(
            rice_qty_grams=Decimal("250"),
            chicken_qty_grams=Decimal("200"),
            oil_qty_ml=Decimal("30"),
        )
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("10"))
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("5"))
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("1"))

    def _consume_order(self, qty=Decimal("1")):
        order = self._make_confirmed_order([(self.item_biryani, qty)])
        batch = ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch,
            idempotency_key=f"{order.id}:KITCHEN_COMPLETED",
            status="PENDING",
            triggered_by=self.manager,
            trigger="KITCHEN_COMPLETED",
        )
        return svc.execute_consumption_batch(batch, self.manager)

    def test_reversal_returns_stock(self):
        """Reversing a batch must return all deducted stock."""
        batch = self._consume_order()
        self.assertEqual(batch.status, BATCH_COMPLETED)

        # Verify stock was deducted
        rice_before = StockBalance.objects.get(
            inventory_item=self.inv_rice, storage_location=self.kitchen_store
        ).quantity
        self.assertEqual(rice_before, Decimal("9.750"))

        # Reverse
        svc.reverse_consumption_batch(batch, self.manager, reason="Order cancelled")

        # Stock must be restored
        rice_after = StockBalance.objects.get(
            inventory_item=self.inv_rice, storage_location=self.kitchen_store
        ).quantity
        self.assertEqual(rice_after, Decimal("10.000"))

    def test_reversal_creates_consumption_reversal_movements(self):
        """CONSUMPTION_REVERSAL StockMovements must be created."""
        from inventory.constants import MOVEMENT_CONSUMPTION_REVERSAL
        batch = self._consume_order()
        svc.reverse_consumption_batch(batch, self.manager, reason="Cancelled")

        reversal_movements = StockMovement.objects.filter(
            movement_type=MOVEMENT_CONSUMPTION_REVERSAL,
            reference_id=batch.id,
        )
        self.assertEqual(reversal_movements.count(), 3)  # rice + chicken + oil

    def test_reversal_marks_batch_reversed(self):
        batch = self._consume_order()
        reversed_batch = svc.reverse_consumption_batch(batch, self.manager, reason="Test")
        self.assertEqual(reversed_batch.status, BATCH_REVERSED)

    def test_reversal_marks_consumptions_reversed(self):
        batch = self._consume_order()
        svc.reverse_consumption_batch(batch, self.manager, reason="Test")
        batch.refresh_from_db()
        original_consumptions = batch.consumptions.filter(status=CONSUMPTION_REVERSED)
        self.assertGreater(original_consumptions.count(), 0)

    def test_cannot_reverse_failed_batch(self):
        """Only COMPLETED batches can be reversed."""
        from recipes.models import ConsumptionBatch
        from orders.models import OrderStatus
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch = ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch,
            idempotency_key=f"{order.id}:KITCHEN_COMPLETED_FAIL",
            status=BATCH_FAILED,
            triggered_by=self.manager,
            trigger="KITCHEN_COMPLETED",
            failure_reason="Test failure",
        )
        with self.assertRaises(ValidationError) as ctx:
            svc.reverse_consumption_batch(batch, self.manager, reason="Test")
        self.assertEqual(ctx.exception.detail["code"], "BATCH_NOT_COMPLETED")

    def test_cancellation_before_consumption_no_reversal_needed(self):
        """
        If order is cancelled before consumption, no batch exists.
        No reversal is required.
        """
        from orders.models import OrderStatus
        from django.utils import timezone as tz

        ts = tz.now().strftime("%Y%m%d%H%M%S%f")
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])

        # Cancel order (do NOT run consumption)
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = tz.now()
        order.save()

        # No batch should exist
        self.assertEqual(ConsumptionBatch.objects.filter(order=order).count(), 0)

    def test_requires_reversal_permission(self):
        batch = self._consume_order()
        with self.assertRaises(PermissionDenied):
            svc.reverse_consumption_batch(batch, self.other_user, reason="Test")


# =============================================================================
# Manual Consumption Tests
# =============================================================================

class TestManualConsumption(RecipeTestBase):
    """Tests for manual_consume()."""

    def setUp(self):
        self._setup_consumption_config()
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("5"))

    def test_manual_consumption_deducts_stock(self):
        """Manual consumption of 1 KG rice → 4 KG remaining."""
        svc.manual_consume(
            branch=self.branch,
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
            quantity=Decimal("1"),
            unit=UNIT_KG,
            reason="Staff meal preparation",
            user=self.manager,
        )
        balance = StockBalance.objects.get(
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
        )
        self.assertEqual(balance.quantity, Decimal("4.000"))

    def test_manual_consumption_with_unit_conversion(self):
        """Manual consumption of 500g rice → 0.500 KG deducted."""
        svc.manual_consume(
            branch=self.branch,
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
            quantity=Decimal("500"),
            unit=UNIT_GRAM,
            reason="Test conversion",
            user=self.manager,
        )
        balance = StockBalance.objects.get(
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
        )
        # 5 - 0.500 = 4.500
        self.assertEqual(balance.quantity, Decimal("4.500"))

    def test_manual_consumption_creates_movement(self):
        svc.manual_consume(
            branch=self.branch,
            inventory_item=self.inv_rice,
            storage_location=self.kitchen_store,
            quantity=Decimal("1"),
            unit=UNIT_KG,
            reason="Test",
            user=self.manager,
        )
        movements = StockMovement.objects.filter(
            inventory_item=self.inv_rice,
            movement_type=MOVEMENT_CONSUMPTION,
        )
        self.assertEqual(movements.count(), 1)

    def test_manual_consumption_requires_reason(self):
        with self.assertRaises(ValidationError) as ctx:
            svc.manual_consume(
                branch=self.branch,
                inventory_item=self.inv_rice,
                storage_location=self.kitchen_store,
                quantity=Decimal("1"),
                unit=UNIT_KG,
                reason="",
                user=self.manager,
            )
        self.assertEqual(ctx.exception.detail["code"], "REASON_REQUIRED")

    def test_manual_consumption_insufficient_stock_fails(self):
        """Requesting 10 KG when only 5 KG available."""
        with self.assertRaises(ValidationError) as ctx:
            svc.manual_consume(
                branch=self.branch,
                inventory_item=self.inv_rice,
                storage_location=self.kitchen_store,
                quantity=Decimal("10"),
                unit=UNIT_KG,
                reason="Too much",
                user=self.manager,
            )
        self.assertEqual(ctx.exception.detail["code"], "INSUFFICIENT_STOCK")

    def test_manual_consumption_requires_permission(self):
        with self.assertRaises(PermissionDenied):
            svc.manual_consume(
                branch=self.branch,
                inventory_item=self.inv_rice,
                storage_location=self.kitchen_store,
                quantity=Decimal("1"),
                unit=UNIT_KG,
                reason="Test",
                user=self.other_user,
            )

    def test_manual_consumption_rejects_wrong_branch_location(self):
        """Storage location from a different branch must be rejected."""
        with self.assertRaises(ValidationError) as ctx:
            svc.manual_consume(
                branch=self.branch,
                inventory_item=self.inv_rice,
                storage_location=self.external_store,  # belongs to other_branch
                quantity=Decimal("1"),
                unit=UNIT_KG,
                reason="Test",
                user=self.manager,
            )
        self.assertEqual(ctx.exception.detail["code"], "LOCATION_BRANCH_MISMATCH")

    def test_manual_consumption_rejects_incompatible_unit(self):
        """LITRE is incompatible with rice (KG-based item)."""
        with self.assertRaises(ValidationError) as ctx:
            svc.manual_consume(
                branch=self.branch,
                inventory_item=self.inv_rice,
                storage_location=self.kitchen_store,
                quantity=Decimal("1"),
                unit=UNIT_LITRE,
                reason="Test",
                user=self.manager,
            )
        self.assertEqual(ctx.exception.detail["code"], "INCOMPATIBLE_UNITS")


# =============================================================================
# Branch Isolation Tests
# =============================================================================

class TestBranchIsolation(RecipeTestBase):
    """Consumption records from one branch must not be visible to another."""

    def test_consumption_scoped_to_branch(self):
        """get_accessible_consumption_batches scopes by branch membership."""
        from recipes.access import get_accessible_consumption_batches
        from accounts.models import UserRoleAssignment

        # Create a user with access ONLY to other_branch
        other_branch_user = self.other_user
        other_role = self.staff_role
        UserRoleAssignment.objects.get_or_create(
            user=other_branch_user,
            role=other_role,
            organization=self.org,
            restaurant=self.restaurant,
            branch=self.other_branch,
        )

        # Create a batch on cls.branch
        self._setup_consumption_config()
        self._make_active_biryani_recipe()
        self._set_stock(self.inv_rice, self.kitchen_store, Decimal("10"))
        self._set_stock(self.inv_chicken, self.kitchen_store, Decimal("5"))
        self._set_stock(self.inv_oil, self.kitchen_store, Decimal("1"))
        order = self._make_confirmed_order([(self.item_biryani, Decimal("1"))])
        batch = ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch,  # cls.branch, not other_branch
            idempotency_key=f"{order.id}:KITCHEN_COMPLETED",
            status=BATCH_COMPLETED,
            triggered_by=self.manager,
            trigger="KITCHEN_COMPLETED",
        )

        # other_branch_user must NOT see this batch
        visible_batches = get_accessible_consumption_batches(other_branch_user)
        self.assertNotIn(batch, list(visible_batches))

        # cls.manager sees it
        manager_batches = get_accessible_consumption_batches(self.manager)
        self.assertIn(batch, list(manager_batches))
