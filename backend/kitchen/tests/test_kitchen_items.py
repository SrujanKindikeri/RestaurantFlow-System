# =============================================================================
# RestaurantFlow — Kitchen Item Tests
# Phase 7
#
# Tests:
#   - item start preparation (NEW → PREPARING)
#   - item mark ready (PREPARING → READY)
#   - partial completion: one item READY, others PREPARING
#   - auto-advance order to READY when all items done
#   - order NOT advanced if one item still PREPARING
#   - cancelled item does not block order READY
#   - notes preserved on KitchenOrderItem
#   - food_type available on KitchenOrderItem
#   - item transitions rejected when terminal
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from kitchen.models import KitchenOrderStatus, KitchenItemStatus
from kitchen.services import (
    send_order_to_kitchen,
    accept_kitchen_order,
    start_preparation,
    mark_order_ready,
    start_item_preparation,
    mark_item_ready,
)

from kitchen.tests.test_kitchen import KitchenTestBase


class TestKitchenOrderItems(KitchenTestBase):

    def setUp(self):
        self.order = self._make_confirmed_order(extra_item=True)
        self.ko = send_order_to_kitchen(self.order)
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()

    def _get_item_by_name(self, name):
        return self.ko.items.get(item_name_snapshot=name)

    def test_notes_preserved(self):
        biryani = self._get_item_by_name("Chicken Biryani")
        self.assertEqual(biryani.notes, "Less spicy")

    def test_food_type_available(self):
        biryani = self._get_item_by_name("Chicken Biryani")
        coffee = self._get_item_by_name("Cold Coffee")
        self.assertEqual(biryani.food_type, "NON_VEG")
        self.assertEqual(coffee.food_type, "VEG")

    def test_prep_time_snapshotted(self):
        biryani = self._get_item_by_name("Chicken Biryani")
        self.assertEqual(biryani.preparation_time_minutes, 20)
        coffee = self._get_item_by_name("Cold Coffee")
        self.assertEqual(coffee.preparation_time_minutes, 5)

    def test_item_start_preparation(self):
        biryani = self._get_item_by_name("Chicken Biryani")
        # After start_preparation on the order, items are already PREPARING
        self.assertEqual(biryani.status, KitchenItemStatus.PREPARING)

    def test_mark_item_ready(self):
        biryani = self._get_item_by_name("Chicken Biryani")
        item = mark_item_ready(self.kitchen_user, kitchen_item=biryani)
        self.assertEqual(item.status, KitchenItemStatus.READY)
        self.assertIsNotNone(item.ready_at)

    def test_partial_completion_order_stays_preparing(self):
        """One item READY, one still PREPARING → order stays PREPARING."""
        biryani = self._get_item_by_name("Chicken Biryani")
        mark_item_ready(self.kitchen_user, kitchen_item=biryani)
        self.ko.refresh_from_db()
        self.assertEqual(self.ko.status, KitchenOrderStatus.PREPARING)

    def test_all_items_ready_auto_advances_order(self):
        """All items READY → order automatically advances to READY."""
        biryani = self._get_item_by_name("Chicken Biryani")
        coffee = self._get_item_by_name("Cold Coffee")
        mark_item_ready(self.kitchen_user, kitchen_item=biryani)
        mark_item_ready(self.kitchen_user, kitchen_item=coffee)
        self.ko.refresh_from_db()
        self.assertEqual(self.ko.status, KitchenOrderStatus.READY)
        self.assertIsNotNone(self.ko.ready_at)

    def test_cancelled_item_does_not_block_order_ready(self):
        """
        If one item is CANCELLED and the other is READY,
        the order should auto-advance to READY.
        """
        biryani = self._get_item_by_name("Chicken Biryani")
        coffee = self._get_item_by_name("Cold Coffee")

        # Cancel the coffee item
        coffee.status = KitchenItemStatus.CANCELLED
        coffee.cancelled_at = timezone.now()
        coffee.save()

        # Mark biryani ready — should trigger order READY
        mark_item_ready(self.kitchen_user, kitchen_item=biryani)
        self.ko.refresh_from_db()
        self.assertEqual(self.ko.status, KitchenOrderStatus.READY)

    def test_item_ready_invalid_transition_from_new(self):
        """Item cannot go directly from NEW to READY."""
        # Reset item to NEW for this test
        biryani = self._get_item_by_name("Chicken Biryani")
        biryani.status = KitchenItemStatus.NEW
        biryani.save()
        with self.assertRaises(ValidationError) as ctx:
            mark_item_ready(self.kitchen_user, kitchen_item=biryani)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_ITEM_TRANSITION")

    def test_item_ready_terminal_idempotent(self):
        """Calling mark_item_ready twice returns READY without error."""
        biryani = self._get_item_by_name("Chicken Biryani")
        mark_item_ready(self.kitchen_user, kitchen_item=biryani)
        biryani.refresh_from_db()
        # Second call — idempotent
        item = mark_item_ready(self.kitchen_user, kitchen_item=biryani)
        self.assertEqual(item.status, KitchenItemStatus.READY)

    def test_item_start_then_ready_full_cycle(self):
        """Full item lifecycle: PREPARING → READY."""
        biryani = self._get_item_by_name("Chicken Biryani")
        # Item is already PREPARING after start_preparation on order
        item = mark_item_ready(self.kitchen_user, kitchen_item=biryani)
        self.assertEqual(item.status, KitchenItemStatus.READY)

    def test_start_item_preparation_from_new(self):
        """start_item_preparation works on a NEW item (individual control)."""
        # Reset item to NEW for this test
        coffee = self._get_item_by_name("Cold Coffee")
        coffee.status = KitchenItemStatus.NEW
        coffee.started_at = None
        coffee.save()

        item = start_item_preparation(self.kitchen_user, kitchen_item=coffee)
        self.assertEqual(item.status, KitchenItemStatus.PREPARING)
        self.assertIsNotNone(item.started_at)

    def test_item_cancelled_state_is_terminal(self):
        """Cannot start a CANCELLED item."""
        biryani = self._get_item_by_name("Chicken Biryani")
        biryani.status = KitchenItemStatus.CANCELLED
        biryani.save()
        with self.assertRaises(ValidationError) as ctx:
            start_item_preparation(self.kitchen_user, kitchen_item=biryani)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_ITEM_TRANSITION")

    def test_order_not_ready_if_item_still_preparing(self):
        """mark_order_ready raises if an item is still PREPARING."""
        # biryani is PREPARING, coffee is PREPARING
        with self.assertRaises(ValidationError) as ctx:
            mark_order_ready(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ctx.exception.detail["code"], "ITEMS_NOT_READY")
