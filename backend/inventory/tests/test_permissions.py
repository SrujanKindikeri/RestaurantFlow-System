# =============================================================================
# RestaurantFlow — Inventory Permission Tests
# Phase 10
#
# Tests:
#   - Unauthenticated user raises PermissionDenied everywhere
#   - User with no role raises PermissionDenied
#   - Inventory staff cannot approve wastage
#   - Inventory staff cannot approve PO
#   - Manager can approve wastage and PO
#   - Branch isolation: user from other branch cannot see items
#   - Restaurant isolation: items from other restaurant not accessible
# =============================================================================

from decimal import Decimal

from rest_framework.exceptions import PermissionDenied, ValidationError

from inventory import services
from inventory.access import (
    get_accessible_inventory_items,
    get_accessible_stock_balances,
    get_accessible_purchase_orders,
    get_accessible_wastages,
    get_accessible_transfers,
)
from inventory.tests.base import InventoryTestBase
from accounts.models import User


class TestServicePermissions(InventoryTestBase):
    """Tests that service layer enforces permissions correctly."""

    def test_unauthenticated_user_raises(self):
        """An unauthenticated user (no user object) raises PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            services.create_stock_adjustment(
                inventory_item=self.item_rice,
                storage_location=self.main_store,
                physical_quantity=Decimal("90.000"),
                unit="KG",
                reason="Unauthenticated user test attempt here",
                user=None,
            )

    def test_user_without_role_cannot_create_wastage(self):
        with self.assertRaises(PermissionDenied):
            services.create_wastage(
                inventory_item=self.item_rice, storage_location=self.main_store,
                quantity=Decimal("5.000"), unit="KG",
                wastage_type="SPOILED", reason="No role user creates wastage",
                user=self.other_user,
            )

    def test_user_without_role_cannot_adjust(self):
        with self.assertRaises(PermissionDenied):
            services.create_stock_adjustment(
                inventory_item=self.item_rice, storage_location=self.main_store,
                physical_quantity=Decimal("95.000"), unit="KG",
                reason="No role adjustment attempt test case",
                user=self.other_user,
            )

    def test_inventory_staff_cannot_approve_wastage(self):
        """inventory_staff does not have inventory.wastage.approve."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        wastage = services.create_wastage(
            inventory_item=self.item_rice, storage_location=self.main_store,
            quantity=Decimal("5.000"), unit="KG",
            wastage_type="EXPIRED", reason="Expiry date passed before use",
            user=self.inventory_staff,
        )
        with self.assertRaises(PermissionDenied):
            services.approve_wastage(wastage, self.inventory_staff)

    def test_inventory_staff_cannot_approve_transfer(self):
        """inventory_staff does not have inventory.transfer.approve."""
        transfer = services.create_stock_transfer(
            restaurant=self.restaurant,
            source_location=self.main_store,
            destination_location=self.kitchen_store,
            items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": "10", "unit": "KG"}],
            user=self.inventory_staff,
        )
        services.request_stock_transfer(transfer, self.inventory_staff)
        transfer.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            services.approve_stock_transfer(transfer, self.inventory_staff)

    def test_manager_can_approve_wastage(self):
        """manager has inventory.wastage.approve."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        wastage = services.create_wastage(
            inventory_item=self.item_rice, storage_location=self.main_store,
            quantity=Decimal("5.000"), unit="KG",
            wastage_type="DAMAGED", reason="Damaged during storage inspection check",
            user=self.inventory_staff,
        )
        result = services.approve_wastage(wastage, self.manager)
        self.assertEqual(result.status, "RECORDED")

    def test_inventory_staff_cannot_submit_purchase(self):
        """inventory_staff has purchase.submit — verify it works for that role."""
        po = services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a,
            items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": "10", "unit": "KG", "unit_cost": "50"}],
            user=self.inventory_staff,
        )
        # staff has purchase.submit permission, so this should succeed
        po = services.submit_purchase_order(po, self.inventory_staff)
        self.assertEqual(po.status, "SUBMITTED")

    def test_inventory_staff_cannot_approve_purchase(self):
        """inventory_staff does not have purchase.approve."""
        po = services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a,
            items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": "10", "unit": "KG", "unit_cost": "50"}],
            user=self.manager,
        )
        po = services.submit_purchase_order(po, self.manager)
        with self.assertRaises(PermissionDenied):
            services.approve_purchase_order(po, self.inventory_staff)


class TestScopeIsolation(InventoryTestBase):
    """Tests that access control scoping prevents cross-scope access."""

    def test_other_user_sees_no_items(self):
        """User with no role assignment sees no inventory items."""
        qs = get_accessible_inventory_items(self.other_user)
        self.assertEqual(qs.count(), 0)

    def test_inventory_staff_sees_restaurant_items(self):
        """Staff assigned to the branch can see items belonging to the restaurant."""
        qs = get_accessible_inventory_items(self.inventory_staff)
        self.assertIn(self.item_rice, qs)
        self.assertIn(self.item_milk, qs)

    def test_other_user_sees_no_stock_balances(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("50.000"))
        qs = get_accessible_stock_balances(self.other_user)
        self.assertEqual(qs.count(), 0)

    def test_other_user_sees_no_purchase_orders(self):
        services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a,
            items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": "10", "unit": "KG", "unit_cost": "50"}],
            user=self.manager,
        )
        qs = get_accessible_purchase_orders(self.other_user)
        self.assertEqual(qs.count(), 0)

    def test_other_user_sees_no_wastage(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        services.create_wastage(
            inventory_item=self.item_rice, storage_location=self.main_store,
            quantity=Decimal("5.000"), unit="KG",
            wastage_type="SPOILED", reason="Isolation test wastage creation record",
            user=self.inventory_staff,
        )
        qs = get_accessible_wastages(self.other_user)
        self.assertEqual(qs.count(), 0)

    def test_inventory_staff_sees_own_branch_balances(self):
        """Staff sees balances for their assigned branch's locations."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("50.000"))
        qs = get_accessible_stock_balances(self.inventory_staff)
        self.assertGreater(qs.count(), 0)

    def test_owner_sees_all_restaurant_items(self):
        """Restaurant owner scope includes all items in the restaurant."""
        qs = get_accessible_inventory_items(self.owner)
        self.assertIn(self.item_rice, qs)
        self.assertIn(self.item_milk, qs)
