# =============================================================================
# RestaurantFlow — Wastage Tests
# Phase 10
#
# Tests:
#   - Create wastage (PENDING — no stock change)
#   - Approve wastage → stock decreases, RECORDED
#   - Reject wastage → no stock change, REJECTED
#   - estimated_cost calculated at approval time
#   - Cannot approve non-PENDING wastage
#   - WASTAGE movement created on approval
#   - Spec scenario: 100 KG → 5 KG wastage → 95 KG
#   - No permission raises
# =============================================================================

from decimal import Decimal

from rest_framework.exceptions import PermissionDenied, ValidationError

from inventory import services
from inventory.models import StockBalance, StockMovement
from inventory.constants import WASTAGE_PENDING, WASTAGE_RECORDED, WASTAGE_REJECTED, MOVEMENT_WASTAGE
from inventory.tests.base import InventoryTestBase


class TestWastageCreation(InventoryTestBase):
    """Tests for services.create_wastage()."""

    def test_creates_pending_wastage(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        wastage = services.create_wastage(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            quantity=Decimal("5.000"),
            unit="KG",
            wastage_type="SPOILED",
            reason="Found mouldy bags during inspection",
            user=self.inventory_staff,
        )
        self.assertEqual(wastage.status, WASTAGE_PENDING)
        self.assertEqual(wastage.quantity, Decimal("5.000"))
        self.assertEqual(wastage.recorded_by, self.inventory_staff)

    def test_creating_wastage_does_not_change_stock(self):
        """PENDING wastage must NOT reduce stock."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        services.create_wastage(
            inventory_item=self.item_rice, storage_location=self.main_store,
            quantity=Decimal("5.000"), unit="KG",
            wastage_type="SPOILED", reason="Mouldy bags inspection",
            user=self.inventory_staff,
        )
        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.quantity, Decimal("100.000"))

    def test_estimated_cost_set_at_creation(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        wastage = services.create_wastage(
            inventory_item=self.item_rice, storage_location=self.main_store,
            quantity=Decimal("5.000"), unit="KG",
            wastage_type="SPOILED", reason="Quality check failed daily",
            user=self.inventory_staff,
        )
        # 5 × 50.00 = 250.00
        self.assertEqual(wastage.estimated_cost, Decimal("250.00"))

    def test_no_permission_raises(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        with self.assertRaises(PermissionDenied):
            services.create_wastage(
                inventory_item=self.item_rice, storage_location=self.main_store,
                quantity=Decimal("5.000"), unit="KG",
                wastage_type="SPOILED", reason="No permission test scenario",
                user=self.other_user,
            )

    def test_empty_reason_raises(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        with self.assertRaises(ValidationError):
            services.create_wastage(
                inventory_item=self.item_rice, storage_location=self.main_store,
                quantity=Decimal("5.000"), unit="KG",
                wastage_type="SPOILED", reason="",  # empty reason
                user=self.inventory_staff,
            )


class TestWastageApproval(InventoryTestBase):
    """Tests for services.approve_wastage()."""

    def _make_wastage(self, qty=Decimal("5.000")):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        return services.create_wastage(
            inventory_item=self.item_rice, storage_location=self.main_store,
            quantity=qty, unit="KG",
            wastage_type="SPOILED", reason="Quality check failed monthly audit",
            user=self.inventory_staff,
        )

    def test_approve_decreases_stock(self):
        """
        Spec scenario: Stock 100 KG → Wastage 5 KG → Result 95 KG
        """
        wastage = self._make_wastage(Decimal("5.000"))
        services.approve_wastage(wastage, self.manager)
        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.quantity, Decimal("95.000"))

    def test_approve_sets_recorded_status(self):
        wastage = self._make_wastage()
        wastage = services.approve_wastage(wastage, self.manager)
        self.assertEqual(wastage.status, WASTAGE_RECORDED)
        self.assertEqual(wastage.approved_by, self.manager)
        self.assertIsNotNone(wastage.approved_at)

    def test_approve_creates_wastage_movement(self):
        wastage = self._make_wastage(Decimal("5.000"))
        services.approve_wastage(wastage, self.manager)
        movement = StockMovement.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            movement_type=MOVEMENT_WASTAGE,
        )
        self.assertEqual(movement.quantity, Decimal("5.000"))

    def test_cannot_approve_already_recorded(self):
        wastage = self._make_wastage()
        services.approve_wastage(wastage, self.manager)
        wastage.refresh_from_db()
        with self.assertRaises(ValidationError) as ctx:
            services.approve_wastage(wastage, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "WASTAGE_NOT_PENDING")

    def test_no_approve_permission_raises(self):
        wastage = self._make_wastage()
        with self.assertRaises(PermissionDenied):
            services.approve_wastage(wastage, self.inventory_staff)

    def test_reject_wastage_no_stock_change(self):
        wastage = self._make_wastage()
        services.reject_wastage(wastage, self.manager, rejection_reason="Not enough evidence provided")
        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.quantity, Decimal("100.000"))
        wastage.refresh_from_db()
        self.assertEqual(wastage.status, WASTAGE_REJECTED)

    def test_reject_sets_rejection_reason(self):
        wastage = self._make_wastage()
        reason = "Insufficient documentation submitted"
        services.reject_wastage(wastage, self.manager, rejection_reason=reason)
        wastage.refresh_from_db()
        self.assertEqual(wastage.rejection_reason, reason)

    def test_reject_empty_reason_raises(self):
        wastage = self._make_wastage()
        with self.assertRaises(ValidationError):
            services.reject_wastage(wastage, self.manager, rejection_reason="")
