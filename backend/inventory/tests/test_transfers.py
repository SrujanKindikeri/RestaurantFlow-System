# =============================================================================
# RestaurantFlow — Stock Transfer Tests
# Phase 10
#
# Tests:
#   - Create transfer (DRAFT)
#   - Request transfer: DRAFT → REQUESTED
#   - Approve transfer: REQUESTED → APPROVED
#   - Complete transfer: stock moves atomically
#   - Transfer scenario: A=100 KG, B=20 KG, transfer 30 → A=70, B=50
#   - TRANSFER_OUT + TRANSFER_IN movements created
#   - Cannot transfer more than available
#   - Source == Destination raises
#   - Cancel transfer
#   - No permission raises
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from inventory import services
from inventory.models import StockBalance, StockMovement
from inventory.constants import (
    TRANSFER_DRAFT, TRANSFER_REQUESTED, TRANSFER_APPROVED,
    TRANSFER_COMPLETED, TRANSFER_CANCELLED,
    MOVEMENT_TRANSFER_IN, MOVEMENT_TRANSFER_OUT,
)
from inventory.tests.base import InventoryTestBase


class TestStockTransferCreation(InventoryTestBase):
    """Tests for services.create_stock_transfer()."""

    def test_creates_draft_transfer(self):
        transfer = services.create_stock_transfer(
            restaurant=self.restaurant,
            source_location=self.main_store,
            destination_location=self.kitchen_store,
            items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": "30", "unit": "KG"}],
            user=self.manager,
        )
        self.assertEqual(transfer.status, TRANSFER_DRAFT)
        self.assertEqual(transfer.source_location, self.main_store)
        self.assertEqual(transfer.destination_location, self.kitchen_store)

    def test_transfer_number_format(self):
        transfer = services.create_stock_transfer(
            restaurant=self.restaurant,
            source_location=self.main_store,
            destination_location=self.kitchen_store,
            items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": "10", "unit": "KG"}],
            user=self.manager,
        )
        self.assertTrue(transfer.transfer_number.startswith("TR-"))

    def test_same_source_destination_raises(self):
        with self.assertRaises(ValidationError) as ctx:
            services.create_stock_transfer(
                restaurant=self.restaurant,
                source_location=self.main_store,
                destination_location=self.main_store,  # same!
                items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": "10", "unit": "KG"}],
                user=self.manager,
            )
        self.assertEqual(ctx.exception.detail["code"], "SAME_LOCATION")

    def test_no_permission_raises(self):
        with self.assertRaises(PermissionDenied):
            services.create_stock_transfer(
                restaurant=self.restaurant,
                source_location=self.main_store,
                destination_location=self.kitchen_store,
                items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": "10", "unit": "KG"}],
                user=self.other_user,
            )

    def test_empty_items_raises(self):
        with self.assertRaises(ValidationError):
            services.create_stock_transfer(
                restaurant=self.restaurant,
                source_location=self.main_store,
                destination_location=self.kitchen_store,
                items=[],
                user=self.manager,
            )


class TestStockTransferWorkflow(InventoryTestBase):
    """Tests for transfer state machine and stock movement."""

    def _make_transfer(self, qty="30"):
        return services.create_stock_transfer(
            restaurant=self.restaurant,
            source_location=self.main_store,
            destination_location=self.kitchen_store,
            items=[{"inventory_item_id": str(self.item_rice.pk), "quantity": qty, "unit": "KG"}],
            user=self.manager,
        )

    def test_request_draft(self):
        t = self._make_transfer()
        t = services.request_stock_transfer(t, self.manager)
        self.assertEqual(t.status, TRANSFER_REQUESTED)

    def test_approve_requested(self):
        t = self._make_transfer()
        t = services.request_stock_transfer(t, self.manager)
        t = services.approve_stock_transfer(t, self.manager)
        self.assertEqual(t.status, TRANSFER_APPROVED)
        self.assertEqual(t.approved_by, self.manager)

    def test_cannot_approve_draft(self):
        t = self._make_transfer()
        with self.assertRaises(ValidationError) as ctx:
            services.approve_stock_transfer(t, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_STATUS_TRANSITION")

    def test_complete_transfer_moves_stock(self):
        """
        The canonical spec scenario:
        Location A (main_store): 100 KG
        Location B (kitchen_store): 20 KG
        Transfer: 30 KG
        Expected: A = 70 KG, B = 50 KG
        """
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        self._seed_balance(self.item_rice, self.kitchen_store, Decimal("20.000"), Decimal("50.00"))

        t = self._make_transfer("30")
        t = services.request_stock_transfer(t, self.manager)
        t = services.approve_stock_transfer(t, self.manager)
        t = services.complete_stock_transfer(t, self.manager)

        self.assertEqual(t.status, TRANSFER_COMPLETED)

        src_balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        dst_balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.kitchen_store)

        self.assertEqual(src_balance.quantity, Decimal("70.000"))
        self.assertEqual(dst_balance.quantity, Decimal("50.000"))

    def test_complete_creates_transfer_out_movement(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        t = self._make_transfer("30")
        t = services.request_stock_transfer(t, self.manager)
        t = services.approve_stock_transfer(t, self.manager)
        services.complete_stock_transfer(t, self.manager)

        out_movement = StockMovement.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            movement_type=MOVEMENT_TRANSFER_OUT,
        )
        self.assertEqual(out_movement.quantity, Decimal("30.000"))

    def test_complete_creates_transfer_in_movement(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        t = self._make_transfer("30")
        t = services.request_stock_transfer(t, self.manager)
        t = services.approve_stock_transfer(t, self.manager)
        services.complete_stock_transfer(t, self.manager)

        in_movement = StockMovement.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.kitchen_store,
            movement_type=MOVEMENT_TRANSFER_IN,
        )
        self.assertEqual(in_movement.quantity, Decimal("30.000"))

    def test_insufficient_stock_fails_complete(self):
        """Completing with insufficient source stock must fail."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("20.000"), Decimal("50.00"))
        # Transfer asks for 30 but only 20 available
        t = self._make_transfer("30")
        t = services.request_stock_transfer(t, self.manager)
        t = services.approve_stock_transfer(t, self.manager)
        with self.assertRaises(ValidationError) as ctx:
            services.complete_stock_transfer(t, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "INSUFFICIENT_STOCK")

    def test_cancel_transfer(self):
        t = self._make_transfer()
        t = services.cancel_stock_transfer(t, self.manager)
        self.assertEqual(t.status, TRANSFER_CANCELLED)

    def test_cannot_cancel_completed(self):
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        t = self._make_transfer("30")
        t = services.request_stock_transfer(t, self.manager)
        t = services.approve_stock_transfer(t, self.manager)
        t = services.complete_stock_transfer(t, self.manager)
        with self.assertRaises(ValidationError):
            services.cancel_stock_transfer(t, self.manager)

    def test_stock_not_moved_on_draft(self):
        """Creating a transfer does NOT move any stock."""
        self._seed_balance(self.item_rice, self.main_store, Decimal("100.000"), Decimal("50.00"))
        self._make_transfer("30")
        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.quantity, Decimal("100.000"))

    def test_no_approve_permission_raises(self):
        t = self._make_transfer()
        t = services.request_stock_transfer(t, self.manager)
        with self.assertRaises(PermissionDenied):
            services.approve_stock_transfer(t, self.inventory_staff)
