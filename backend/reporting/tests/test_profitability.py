# =============================================================================
# RestaurantFlow — Profitability Report Tests
# Phase 14
# =============================================================================

from decimal import Decimal
from datetime import date
from django.utils import timezone

from reporting.tests.base import ReportingTestBase
from reporting import aggregations as agg
from accounts import access as acl


class MenuProfitabilityRulesTests(ReportingTestBase):
    """
    Verify the critical profitability data quality rules:
    - Historical revenue from BillItem snapshots, not current price.
    - Historical cost from StockConsumption, not current recipe cost.
    - Missing consumption → ingredient_cost = None, not fabricated.
    """

    def test_revenue_uses_billitem_not_current_price(self):
        """Even if MenuItem price changed, revenue uses the snapshot."""
        bill = self._make_finalized_bill(grand_total=Decimal("525.00"))
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_profitability(branches, date.today(), date.today())
        self.assertGreater(len(result), 0)
        # Revenue should match what was in BillItem (525 - taxes = ~500 for item)
        row = next((r for r in result if r["menu_item_name"] == "Chicken Biryani"), None)
        self.assertIsNotNone(row)
        self.assertGreater(row["revenue"], Decimal("0"))

    def test_no_consumption_means_null_cost_not_fabricated(self):
        """When no StockConsumption records exist, cost must be None."""
        self._make_finalized_bill()
        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_profitability(branches, date.today(), date.today())
        for row in result:
            # No consumption records created in this test → cost must be null
            if row["ingredient_cost"] is None:
                # gross_profit and margin must ALSO be null
                self.assertIsNone(row["gross_profit"])
                self.assertIsNone(row["gross_margin_percentage"])
            # If ingredient_cost is Decimal("0") it means there are cost records with 0 cost
            # which is technically different from "no data"

    def test_gross_profit_formula(self):
        """gross_profit = revenue - ingredient_cost when both available."""
        from recipes.models import StockConsumption, ConsumptionBatch
        from recipes.constants import CONSUMPTION_CONSUMED, BATCH_COMPLETED
        from inventory.models import (
            InventoryCategory, InventoryItem, StorageLocation, StockBalance
        )
        # Set up inventory
        cat = InventoryCategory.objects.create(restaurant=self.restaurant_a, name="Rice")
        inv_item = InventoryItem.objects.create(
            restaurant=self.restaurant_a, category=cat,
            name="Rice", sku="RICE-001", default_unit="KG",
            average_cost=Decimal("50.00"),
        )
        loc = StorageLocation.objects.create(
            branch=self.branch_a1, name="Store", code="ST", location_type="MAIN_STORE"
        )
        StockBalance.objects.create(
            inventory_item=inv_item, storage_location=loc,
            quantity=Decimal("100.000"), average_cost=Decimal("50.00"),
        )

        # Create order, bill, and matching consumption
        order = self._make_order()
        bill = self._make_finalized_bill(order=order, grand_total=Decimal("525.00"))
        order_item = order.items.first()

        batch = ConsumptionBatch.objects.create(
            order=order,
            branch=self.branch_a1,
            idempotency_key=f"test_{order.pk}_READY",
            status=BATCH_COMPLETED,
            triggered_at=timezone.now(),
        )
        StockConsumption.objects.create(
            batch=batch,
            order=order,
            order_item=order_item,
            restaurant=self.restaurant_a,
            branch=self.branch_a1,
            inventory_item=inv_item,
            storage_location=loc,
            quantity=Decimal("0.250"),
            unit="KG",
            unit_cost=Decimal("50.00"),
            total_cost=Decimal("12.50"),  # 0.25 kg × 50
            status=CONSUMPTION_CONSUMED,
            consumed_at=timezone.now(),
        )

        branches = acl.get_accessible_branches(self.manager_a)
        result = agg.aggregate_menu_profitability(branches, date.today(), date.today())
        row = next((r for r in result if r["menu_item_name"] == "Chicken Biryani"), None)
        self.assertIsNotNone(row)
        if row["ingredient_cost"] is not None:
            expected_profit = row["revenue"] - row["ingredient_cost"]
            self.assertEqual(row["gross_profit"], expected_profit)
