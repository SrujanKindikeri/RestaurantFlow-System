# =============================================================================
# RestaurantFlow — Order Operations Tests
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from operations.tests.base import OperationsTestBase
from operations.order_services import (
    hold_order, resume_order, set_order_priority,
    assign_waiter, create_order_change_request,
    approve_order_change_request, reject_order_change_request,
    add_item_modifier, remove_item_modifier,
    ORDER_STATUS_ON_HOLD,
)
from operations.exceptions import OrderStateConflict, ModifierValidationError
from orders.models import OrderStatus


class OrderHoldResumeTest(OperationsTestBase):
    """Tests for hold/resume order workflow."""

    def test_hold_draft_order(self):
        order = self._make_order()
        self.assertEqual(order.status, OrderStatus.DRAFT)

        order = hold_order(order=order, user=self.cashier)
        self.assertEqual(order.status, ORDER_STATUS_ON_HOLD)

    def test_hold_creates_audit_log(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_ORDER_HELD

        order = self._make_order()
        hold_order(order=order, user=self.cashier)
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_ORDER_HELD,
                order_id=order.id,
            ).exists()
        )

    def test_hold_confirmed_order_raises(self):
        order = self._make_confirmed_order()
        with self.assertRaises(OrderStateConflict):
            hold_order(order=order, user=self.cashier)

    def test_hold_cancelled_order_raises(self):
        order = self._make_order(status=OrderStatus.CANCELLED)
        with self.assertRaises(OrderStateConflict):
            hold_order(order=order, user=self.cashier)

    def test_resume_on_hold_order(self):
        order = self._make_order()
        order = hold_order(order=order, user=self.cashier)

        order = resume_order(order=order, user=self.cashier)
        self.assertEqual(order.status, OrderStatus.DRAFT)

    def test_resume_draft_raises(self):
        order = self._make_order()
        with self.assertRaises(OrderStateConflict):
            resume_order(order=order, user=self.cashier)

    def test_hold_preserves_items(self):
        """Held order preserves all items."""
        order = self._make_order()
        item_count_before = order.items.count()

        hold_order(order=order, user=self.cashier)
        order.refresh_from_db()

        self.assertEqual(order.items.count(), item_count_before)

    def test_hold_preserves_customer_table_waiter(self):
        """Held order preserves customer, table, waiter fields."""
        order = self._make_order(
            order_type='DINE_IN', table=self.table_a,
            counter=None,
        )
        order.assigned_waiter = self.waiter
        order.save(update_fields=['assigned_waiter'])

        hold_order(order=order, user=self.cashier)
        order.refresh_from_db()

        self.assertEqual(order.assigned_waiter, self.waiter)
        self.assertEqual(order.table, self.table_a)


class OrderPriorityTest(OperationsTestBase):
    """Tests for order priority changes."""

    def test_set_normal_priority(self):
        """Manager can set NORMAL priority on a confirmed order."""
        from kitchen.models import KitchenOrder, KitchenPriority, KitchenOrderStatus
        order = self._make_confirmed_order()
        # Create kitchen order
        KitchenOrder.objects.create(
            order=order, branch=self.branch,
            status=KitchenOrderStatus.NEW,
            priority=KitchenPriority.NORMAL,
        )
        set_order_priority(order=order, priority="HIGH", user=self.manager)
        order.kitchen_order.refresh_from_db()
        self.assertEqual(order.kitchen_order.priority, "HIGH")

    def test_set_priority_audit(self):
        from kitchen.models import KitchenOrder, KitchenPriority, KitchenOrderStatus
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_ORDER_PRIORITY_CHANGED

        order = self._make_confirmed_order()
        KitchenOrder.objects.create(
            order=order, branch=self.branch,
            status=KitchenOrderStatus.NEW,
            priority=KitchenPriority.NORMAL,
        )
        set_order_priority(order=order, priority="HIGH", user=self.manager)
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_ORDER_PRIORITY_CHANGED,
                order_id=order.id,
            ).exists()
        )

    def test_invalid_priority_raises(self):
        order = self._make_confirmed_order()
        with self.assertRaises(OrderStateConflict):
            set_order_priority(order=order, priority="CRITICAL", user=self.manager)


class WaiterAssignmentTest(OperationsTestBase):
    """Tests for waiter assignment."""

    def test_assign_waiter_to_order(self):
        order = self._make_order()
        order = assign_waiter(order=order, waiter=self.waiter, user=self.manager)
        self.assertEqual(order.assigned_waiter, self.waiter)

    def test_assign_waiter_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_WAITER_ASSIGNED

        order = self._make_order()
        assign_waiter(order=order, waiter=self.waiter, user=self.manager)
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_WAITER_ASSIGNED,
                order_id=order.id,
            ).exists()
        )

    def test_assign_wrong_branch_waiter_raises(self):
        """Assigning a waiter from another branch raises OrderStateConflict."""
        order = self._make_order()
        with self.assertRaises(OrderStateConflict):
            assign_waiter(order=order, waiter=self.other_user, user=self.manager)


class OrderChangeRequestTest(OperationsTestBase):
    """Tests for order change request workflow."""

    def test_create_change_request_for_confirmed_order(self):
        order = self._make_confirmed_order()
        req = create_order_change_request(
            order=order,
            requested_by=self.cashier,
            change_type="CHANGE_NOTE",
            reason="Customer requested update",
            requested_data={"notes": "No onion"},
        )
        self.assertEqual(req.status, "PENDING")
        self.assertEqual(req.order, order)
        self.assertEqual(req.requested_by, self.cashier)

    def test_create_change_request_for_draft_raises(self):
        """DRAFT orders should be edited directly — not via change request."""
        order = self._make_order()
        with self.assertRaises(OrderStateConflict):
            create_order_change_request(
                order=order,
                requested_by=self.cashier,
                change_type="CHANGE_NOTE",
                reason="test",
                requested_data={},
            )

    def test_approve_change_request(self):
        order = self._make_confirmed_order()
        req = create_order_change_request(
            order=order, requested_by=self.cashier,
            change_type="CHANGE_NOTE", reason="test",
            requested_data={"notes": "Extra spicy"},
        )
        req = approve_order_change_request(
            change_request=req, approver=self.manager, review_note="OK"
        )
        self.assertEqual(req.status, "APPROVED")
        self.assertEqual(req.approved_by, self.manager)

    def test_self_approval_raises(self):
        """A user cannot approve their own change request."""
        order = self._make_confirmed_order()
        req = create_order_change_request(
            order=order, requested_by=self.manager,
            change_type="CHANGE_NOTE", reason="test", requested_data={},
        )
        with self.assertRaises(OrderStateConflict):
            approve_order_change_request(change_request=req, approver=self.manager)

    def test_reject_change_request(self):
        order = self._make_confirmed_order()
        req = create_order_change_request(
            order=order, requested_by=self.cashier,
            change_type="CHANGE_NOTE", reason="test", requested_data={},
        )
        req = reject_order_change_request(
            change_request=req, reviewer=self.manager, review_note="Not needed"
        )
        self.assertEqual(req.status, "REJECTED")

    def test_approve_non_pending_raises(self):
        order = self._make_confirmed_order()
        req = create_order_change_request(
            order=order, requested_by=self.cashier,
            change_type="CHANGE_NOTE", reason="test", requested_data={},
        )
        reject_order_change_request(change_request=req, reviewer=self.manager)
        req.refresh_from_db()
        with self.assertRaises(OrderStateConflict):
            approve_order_change_request(change_request=req, approver=self.cashier)


class OrderModifierTest(OperationsTestBase):
    """Tests for order item modifiers."""

    def test_add_free_text_modifier(self):
        """Can add a modifier without a MenuModifierOption."""
        order = self._make_order()
        order_item = order.items.first()

        modifier = add_item_modifier(
            order_item=order_item,
            name="Spice Level",
            value="Less Spicy",
            user=self.cashier,
        )
        self.assertEqual(modifier.name, "Spice Level")
        self.assertEqual(modifier.value, "Less Spicy")
        self.assertEqual(modifier.price_adjustment, Decimal("0.00"))

    def test_add_option_modifier_resolves_price(self):
        """When option provided, price_adjustment comes from the option, not frontend."""
        from operations.models import MenuModifierGroup, MenuModifierOption

        group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant,
            name="Extra Cheese",
            is_required=False,
            max_selections=1,
        )
        option = MenuModifierOption.objects.create(
            modifier_group=group,
            name="Add Cheese",
            price_adjustment=Decimal("30.00"),
        )

        order = self._make_order()
        order_item = order.items.first()

        modifier = add_item_modifier(
            order_item=order_item,
            modifier_option_id=str(option.id),
            name="Cheese",
            value="Add",
            user=self.cashier,
        )
        # Price comes from DB — never from frontend
        self.assertEqual(modifier.price_adjustment, Decimal("30.00"))

    def test_add_inactive_option_raises(self):
        from operations.models import MenuModifierGroup, MenuModifierOption
        group = MenuModifierGroup.objects.create(
            restaurant=self.restaurant, name="Sauce",
        )
        inactive_opt = MenuModifierOption.objects.create(
            modifier_group=group, name="Ketchup",
            price_adjustment=Decimal("0.00"), is_active=False,
        )
        order = self._make_order()
        order_item = order.items.first()

        with self.assertRaises(ModifierValidationError):
            add_item_modifier(
                order_item=order_item,
                modifier_option_id=str(inactive_opt.id),
                name="Sauce", value="Ketchup",
                user=self.cashier,
            )

    def test_remove_modifier(self):
        order = self._make_order()
        order_item = order.items.first()
        modifier = add_item_modifier(
            order_item=order_item, name="Spice", value="Hot",
            user=self.cashier,
        )
        modifier_id = modifier.id
        remove_item_modifier(modifier=modifier, user=self.cashier)

        from operations.models import OrderItemModifier
        self.assertFalse(
            OrderItemModifier.objects.filter(pk=modifier_id).exists()
        )

    def test_remove_creates_audit(self):
        from operations.models import OperationsAuditLog
        from operations.constants import AUDIT_MODIFIER_REMOVED

        order = self._make_order()
        order_item = order.items.first()
        modifier = add_item_modifier(
            order_item=order_item, name="Extra", value="Yes",
            user=self.cashier,
        )
        remove_item_modifier(modifier=modifier, user=self.cashier)
        self.assertTrue(
            OperationsAuditLog.objects.filter(
                event_type=AUDIT_MODIFIER_REMOVED
            ).exists()
        )
