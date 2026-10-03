# =============================================================================
# RestaurantFlow — Purchase Order Tests
# Phase 10
#
# Tests:
#   - PO creation (DRAFT)
#   - PO number format and uniqueness
#   - Creating PO does NOT increase stock
#   - Submit PO: DRAFT → SUBMITTED
#   - Approve PO: SUBMITTED → APPROVED
#   - Cancel PO from DRAFT, SUBMITTED, APPROVED
#   - Cannot cancel RECEIVED PO
#   - Partial receiving: stock increases, PO → PARTIALLY_RECEIVED
#   - Full receiving: PO → RECEIVED
#   - Cannot receive more than ordered
#   - Receiving updates average cost
#   - No permission raises PermissionDenied
#   - Storage location must belong to correct branch
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError

from inventory import services
from inventory.models import (
    PurchaseOrder, StockBalance, StockMovement,
)
from inventory.constants import (
    PO_DRAFT, PO_SUBMITTED, PO_APPROVED,
    PO_PARTIALLY_RECEIVED, PO_RECEIVED, PO_CANCELLED,
    MOVEMENT_PURCHASE,
)
from inventory.tests.base import InventoryTestBase


def _make_items(item_rice, qty="100", unit_cost="50.00"):
    return [{
        "inventory_item_id": str(item_rice.pk),
        "quantity": qty,
        "unit": item_rice.default_unit,
        "unit_cost": unit_cost,
        "tax_rate": "0",
        "discount_amount": "0",
    }]


class TestPurchaseOrderCreation(InventoryTestBase):
    """Tests for services.create_purchase_order()."""

    def test_creates_draft_po(self):
        po = services.create_purchase_order(
            restaurant=self.restaurant,
            branch=self.branch,
            supplier=self.supplier_a,
            items=_make_items(self.item_rice),
            user=self.manager,
        )
        self.assertEqual(po.status, PO_DRAFT)
        self.assertEqual(po.restaurant, self.restaurant)
        self.assertEqual(po.supplier, self.supplier_a)

    def test_po_number_format(self):
        po = services.create_purchase_order(
            restaurant=self.restaurant,
            branch=self.branch,
            supplier=self.supplier_a,
            items=_make_items(self.item_rice),
            user=self.manager,
        )
        self.assertTrue(po.purchase_number.startswith("PO-"))
        self.assertEqual(len(po.purchase_number.split("-")[1]), 6)

    def test_po_number_unique(self):
        po1 = services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a, items=_make_items(self.item_rice), user=self.manager,
        )
        po2 = services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a, items=_make_items(self.item_rice), user=self.manager,
        )
        self.assertNotEqual(po1.purchase_number, po2.purchase_number)

    def test_creating_po_does_not_increase_stock(self):
        """Creating a PO must NOT touch StockBalance."""
        initial_count = StockBalance.objects.count()
        services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a, items=_make_items(self.item_rice), user=self.manager,
        )
        self.assertEqual(StockBalance.objects.count(), initial_count)

    def test_po_items_created(self):
        po = services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a, items=_make_items(self.item_rice, "100", "50.00"),
            user=self.manager,
        )
        self.assertEqual(po.items.count(), 1)

    def test_po_totals_calculated_by_backend(self):
        """total_amount is computed by backend, not taken from input."""
        po = services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a,
            items=_make_items(self.item_rice, "100", "50.00"),
            user=self.manager,
        )
        # 100 × 50 = 5000, tax=0, discount=0
        self.assertEqual(po.total_amount, Decimal("5000.00"))

    def test_no_permission_raises(self):
        with self.assertRaises(PermissionDenied):
            services.create_purchase_order(
                restaurant=self.restaurant, branch=self.branch,
                supplier=self.supplier_a, items=_make_items(self.item_rice),
                user=self.other_user,
            )

    def test_empty_items_raises(self):
        with self.assertRaises(ValidationError):
            services.create_purchase_order(
                restaurant=self.restaurant, branch=self.branch,
                supplier=self.supplier_a, items=[],
                user=self.manager,
            )


class TestPurchaseOrderWorkflow(InventoryTestBase):
    """Tests for PO submit/approve/cancel state machine."""

    def _make_po(self):
        return services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a, items=_make_items(self.item_rice, "50", "55.00"),
            user=self.manager,
        )

    def test_submit_draft_po(self):
        po = self._make_po()
        po = services.submit_purchase_order(po, self.manager)
        self.assertEqual(po.status, PO_SUBMITTED)

    def test_cannot_submit_already_submitted(self):
        po = self._make_po()
        po = services.submit_purchase_order(po, self.manager)
        with self.assertRaises(ValidationError) as ctx:
            services.submit_purchase_order(po, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_STATUS_TRANSITION")

    def test_approve_submitted_po(self):
        po = self._make_po()
        po = services.submit_purchase_order(po, self.manager)
        po = services.approve_purchase_order(po, self.manager)
        self.assertEqual(po.status, PO_APPROVED)
        self.assertEqual(po.approved_by, self.manager)
        self.assertIsNotNone(po.approved_at)

    def test_cannot_approve_draft_po(self):
        po = self._make_po()
        with self.assertRaises(ValidationError) as ctx:
            services.approve_purchase_order(po, self.manager)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_STATUS_TRANSITION")

    def test_cancel_from_draft(self):
        po = self._make_po()
        po = services.cancel_purchase_order(po, self.manager, reason="No longer needed")
        self.assertEqual(po.status, PO_CANCELLED)

    def test_cancel_from_submitted(self):
        po = self._make_po()
        po = services.submit_purchase_order(po, self.manager)
        po = services.cancel_purchase_order(po, self.manager)
        self.assertEqual(po.status, PO_CANCELLED)

    def test_cancel_from_approved(self):
        po = self._make_po()
        po = services.submit_purchase_order(po, self.manager)
        po = services.approve_purchase_order(po, self.manager)
        po = services.cancel_purchase_order(po, self.manager)
        self.assertEqual(po.status, PO_CANCELLED)

    def test_no_permission_submit_raises(self):
        po = self._make_po()
        with self.assertRaises(PermissionDenied):
            services.submit_purchase_order(po, self.other_user)

    def test_no_permission_approve_raises(self):
        po = self._make_po()
        po = services.submit_purchase_order(po, self.manager)
        with self.assertRaises(PermissionDenied):
            services.approve_purchase_order(po, self.other_user)


class TestGoodsReceiving(InventoryTestBase):
    """
    Tests for services.receive_purchase_order().

    The canonical Phase 10 scenario from the spec:
        Purchase: Rice 100 KG
        First receiving: 60 KG → PARTIALLY_RECEIVED, Stock = +60 KG
        Second receiving: 40 KG → RECEIVED, Stock = +40 KG
        Total: 100 KG
    """

    def _make_approved_po(self, qty="100", unit_cost="50.00"):
        po = services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a, items=_make_items(self.item_rice, qty, unit_cost),
            user=self.manager,
        )
        po = services.submit_purchase_order(po, self.manager)
        po = services.approve_purchase_order(po, self.manager)
        return po

    def test_partial_receiving_increases_stock(self):
        po = self._make_approved_po()
        po_item = po.items.first()

        services.receive_purchase_order(
            po=po,
            user=self.manager,
            storage_location=self.main_store,
            receipt_items=[{
                "purchase_order_item_id": str(po_item.pk),
                "quantity_received": "60",
            }],
        )

        balance = StockBalance.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
        )
        self.assertEqual(balance.quantity, Decimal("60.000"))

    def test_partial_receiving_sets_partially_received_status(self):
        po = self._make_approved_po()
        po_item = po.items.first()
        services.receive_purchase_order(
            po=po, user=self.manager, storage_location=self.main_store,
            receipt_items=[{"purchase_order_item_id": str(po_item.pk), "quantity_received": "60"}],
        )
        po.refresh_from_db()
        self.assertEqual(po.status, PO_PARTIALLY_RECEIVED)

    def test_full_receiving_sets_received_status(self):
        po = self._make_approved_po()
        po_item = po.items.first()
        services.receive_purchase_order(
            po=po, user=self.manager, storage_location=self.main_store,
            receipt_items=[{"purchase_order_item_id": str(po_item.pk), "quantity_received": "100"}],
        )
        po.refresh_from_db()
        self.assertEqual(po.status, PO_RECEIVED)

    def test_two_receipts_complete_po(self):
        """The canonical 60+40=100 KG scenario from the spec."""
        po = self._make_approved_po()
        po_item_id = str(po.items.first().pk)

        # First receipt: 60 KG
        services.receive_purchase_order(
            po=po, user=self.manager, storage_location=self.main_store,
            receipt_items=[{"purchase_order_item_id": po_item_id, "quantity_received": "60"}],
        )
        po.refresh_from_db()
        self.assertEqual(po.status, PO_PARTIALLY_RECEIVED)

        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.quantity, Decimal("60.000"))

        # Second receipt: 40 KG
        services.receive_purchase_order(
            po=po, user=self.manager, storage_location=self.main_store,
            receipt_items=[{"purchase_order_item_id": po_item_id, "quantity_received": "40"}],
        )
        po.refresh_from_db()
        self.assertEqual(po.status, PO_RECEIVED)

        balance.refresh_from_db()
        self.assertEqual(balance.quantity, Decimal("100.000"))

    def test_over_receiving_raises(self):
        po = self._make_approved_po()
        po_item = po.items.first()
        with self.assertRaises(ValidationError) as ctx:
            services.receive_purchase_order(
                po=po, user=self.manager, storage_location=self.main_store,
                receipt_items=[{
                    "purchase_order_item_id": str(po_item.pk),
                    "quantity_received": "101",  # 1 more than ordered
                }],
            )
        self.assertEqual(ctx.exception.detail["code"], "OVER_RECEIVING")

    def test_receiving_creates_purchase_movement(self):
        po = self._make_approved_po()
        po_item = po.items.first()
        services.receive_purchase_order(
            po=po, user=self.manager, storage_location=self.main_store,
            receipt_items=[{"purchase_order_item_id": str(po_item.pk), "quantity_received": "50"}],
        )
        movement = StockMovement.objects.get(
            inventory_item=self.item_rice,
            storage_location=self.main_store,
            movement_type=MOVEMENT_PURCHASE,
        )
        self.assertEqual(movement.quantity, Decimal("50.000"))
        self.assertEqual(movement.unit_cost, Decimal("50.00"))

    def test_receiving_updates_average_cost(self):
        """
        Start: 0 KG
        Receive: 100 KG × ₹50
        Expected avg: 50.00
        """
        po = self._make_approved_po(qty="100", unit_cost="50.00")
        po_item = po.items.first()
        services.receive_purchase_order(
            po=po, user=self.manager, storage_location=self.main_store,
            receipt_items=[{"purchase_order_item_id": str(po_item.pk), "quantity_received": "100"}],
        )
        balance = StockBalance.objects.get(inventory_item=self.item_rice, storage_location=self.main_store)
        self.assertEqual(balance.average_cost, Decimal("50.00"))

    def test_location_must_belong_to_branch(self):
        """Cannot receive into a location from a different branch."""
        po = self._make_approved_po()
        po_item = po.items.first()
        with self.assertRaises(ValidationError) as ctx:
            services.receive_purchase_order(
                po=po, user=self.manager,
                storage_location=self.other_store,  # belongs to other_branch
                receipt_items=[{"purchase_order_item_id": str(po_item.pk), "quantity_received": "10"}],
            )
        self.assertEqual(ctx.exception.detail["code"], "LOCATION_BRANCH_MISMATCH")

    def test_cannot_receive_draft_po(self):
        po = services.create_purchase_order(
            restaurant=self.restaurant, branch=self.branch,
            supplier=self.supplier_a, items=_make_items(self.item_rice),
            user=self.manager,
        )
        po_item = po.items.first()
        with self.assertRaises(ValidationError) as ctx:
            services.receive_purchase_order(
                po=po, user=self.manager, storage_location=self.main_store,
                receipt_items=[{"purchase_order_item_id": str(po_item.pk), "quantity_received": "10"}],
            )
        self.assertEqual(ctx.exception.detail["code"], "PO_NOT_RECEIVABLE")

    def test_no_permission_raises(self):
        po = self._make_approved_po()
        po_item = po.items.first()
        with self.assertRaises(PermissionDenied):
            services.receive_purchase_order(
                po=po, user=self.other_user, storage_location=self.main_store,
                receipt_items=[{"purchase_order_item_id": str(po_item.pk), "quantity_received": "10"}],
            )
