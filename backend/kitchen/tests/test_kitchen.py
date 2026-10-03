# =============================================================================
# RestaurantFlow — Kitchen Order Tests
# Phase 7
#
# Tests:
#   - confirmed order creates KitchenOrder
#   - draft order does NOT create KitchenOrder via service
#   - cancelled order does NOT create KitchenOrder via service
#   - correct branch relationship
#   - correct order type
#   - correct item snapshots
#   - KitchenOrder state machine: NEW→ACCEPTED→PREPARING→READY
#   - Invalid transitions rejected
#   - Cancel from each allowed state
#   - Priority update
#   - Idempotent duplicate send
# =============================================================================

import uuid
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch
from menu.models import Category, MenuItem, MenuItemPrice, MenuItemBranch, TaxRate
from orders.models import (
    Order, OrderItem, OrderStatus, OrderType,
    DiningTable, TableSession, TableSessionStatus,
)
from counters.models import Counter, CounterSession, SessionStatus, CounterStatus
from kitchen.models import (
    KitchenOrder, KitchenOrderItem,
    KitchenOrderStatus, KitchenItemStatus, KitchenPriority,
)
from kitchen.services import (
    send_order_to_kitchen,
    accept_kitchen_order,
    start_preparation,
    mark_order_ready,
    cancel_kitchen_order,
    update_kitchen_priority,
)


# =============================================================================
# Test Fixtures
# =============================================================================

class KitchenTestBase(TestCase):
    """Base class with full fixture setup for kitchen tests."""

    @classmethod
    def setUpTestData(cls):
        # Organization / restaurant / branch
        cls.org = Organization.objects.create(name="Test Org", slug="test-org")
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org, name="Test Restaurant", slug="test-restaurant"
        )
        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant, name="Main Branch", slug="main-branch"
        )

        # Users
        cls.kitchen_user = User.objects.create_user(
            email="kitchen@test.com", password="pass", first_name="Kitchen", last_name="Staff"
        )
        cls.manager = User.objects.create_user(
            email="manager@test.com", password="pass", first_name="Branch", last_name="Manager"
        )
        cls.cashier = User.objects.create_user(
            email="cashier@test.com", password="pass", first_name="Counter", last_name="Cashier"
        )
        cls.other_user = User.objects.create_user(
            email="other@test.com", password="pass", first_name="Other", last_name="User"
        )

        # Kitchen permissions
        perms_data = [
            ("kitchen.view",            "Kitchen", "View kitchen orders",           "kitchen", "view"),
            ("kitchen.view_history",    "Kitchen", "View kitchen history",          "kitchen", "view_history"),
            ("kitchen.accept",          "Kitchen", "Accept kitchen orders",         "kitchen", "accept"),
            ("kitchen.start",           "Kitchen", "Start kitchen preparation",     "kitchen", "start"),
            ("kitchen.item_start",      "Kitchen", "Start item preparation",        "kitchen", "item_start"),
            ("kitchen.item_ready",      "Kitchen", "Mark item ready",               "kitchen", "item_ready"),
            ("kitchen.order_ready",     "Kitchen", "Mark order ready",              "kitchen", "order_ready"),
            ("kitchen.cancel",          "Kitchen", "Cancel kitchen orders",         "kitchen", "cancel"),
            ("kitchen.priority_update", "Kitchen", "Update kitchen order priority", "kitchen", "priority_update"),
        ]
        cls.perms = {}
        for code, name, desc, module, action in perms_data:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": desc, "module": module, "action": action},
            )
            cls.perms[code] = p

        # Roles
        cls.kitchen_role = Role.objects.create(
            name="Kitchen Staff", code="KITCHEN_STAFF_TEST", scope=Role.SCOPE_BRANCH
        )
        cls.kitchen_role.permissions.set(cls.perms.values())

        cls.manager_role = Role.objects.create(
            name="Branch Manager Test", code="BRANCH_MANAGER_TEST", scope=Role.SCOPE_BRANCH
        )
        cls.manager_role.permissions.set(cls.perms.values())

        # Assign roles to users
        UserRoleAssignment.objects.create(
            user=cls.kitchen_user,
            role=cls.kitchen_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )
        UserRoleAssignment.objects.create(
            user=cls.manager,
            role=cls.manager_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )

        # Menu
        cls.category = Category.objects.create(
            restaurant=cls.restaurant, name="Food", slug="food"
        )
        cls.tax_rate = TaxRate.objects.create(
            restaurant=cls.restaurant, name="GST 5%", code="GST5", rate=Decimal("5.000")
        )
        cls.menu_item = MenuItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.category,
            name="Chicken Biryani",
            slug="chicken-biryani",
            food_type="NON_VEG",
            preparation_time_minutes=20,
            tax_rate=cls.tax_rate,
        )
        cls.menu_item2 = MenuItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.category,
            name="Cold Coffee",
            slug="cold-coffee",
            food_type="VEG",
            preparation_time_minutes=5,
        )
        MenuItemBranch.objects.create(
            menu_item=cls.menu_item, branch=cls.branch, is_available=True
        )
        MenuItemBranch.objects.create(
            menu_item=cls.menu_item2, branch=cls.branch, is_available=True
        )
        MenuItemPrice.objects.create(
            menu_item=cls.menu_item, branch=cls.branch, price=Decimal("180.00"), is_active=True
        )
        MenuItemPrice.objects.create(
            menu_item=cls.menu_item2, branch=cls.branch, price=Decimal("80.00"), is_active=True
        )

        # Counter setup (for TAKEAWAY/COUNTER orders)
        cls.counter = Counter.objects.create(
            branch=cls.branch, name="Counter 1", code="C01", status=CounterStatus.ACTIVE
        )
        cls.counter_session = CounterSession.objects.create(
            counter=cls.counter,
            opened_by=cls.cashier,
            status=SessionStatus.OPEN,
            opening_cash=Decimal("500.00"),
            expected_cash=Decimal("500.00"),
        )

    def _make_confirmed_order(self, order_type=OrderType.TAKEAWAY, extra_item=False):
        """Helper: create a confirmed order with at least one item."""
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"C01-TEST-{uuid.uuid4().hex[:6].upper()}",
            order_type=order_type,
            counter=self.counter if order_type != OrderType.DINE_IN else None,
            counter_session=self.counter_session if order_type != OrderType.DINE_IN else None,
            created_by=self.cashier,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.menu_item,
            item_name_snapshot="Chicken Biryani",
            sku_snapshot="",
            unit_price_snapshot=Decimal("180.00"),
            tax_rate_snapshot=Decimal("5.000"),
            tax_code_snapshot="GST5",
            quantity=Decimal("2.000"),
            notes="Less spicy",
        )
        if extra_item:
            OrderItem.objects.create(
                order=order,
                menu_item=self.menu_item2,
                item_name_snapshot="Cold Coffee",
                sku_snapshot="",
                unit_price_snapshot=Decimal("80.00"),
                tax_rate_snapshot=Decimal("0.000"),
                tax_code_snapshot="",
                quantity=Decimal("1.000"),
                notes="",
            )
        return order

    def _make_draft_order(self):
        order = Order.objects.create(
            branch=self.branch,
            order_number=f"C01-DRAFT-{uuid.uuid4().hex[:6].upper()}",
            order_type=OrderType.TAKEAWAY,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.cashier,
            status=OrderStatus.DRAFT,
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.menu_item,
            item_name_snapshot="Chicken Biryani",
            sku_snapshot="",
            unit_price_snapshot=Decimal("180.00"),
            tax_rate_snapshot=Decimal("5.000"),
            tax_code_snapshot="GST5",
            quantity=Decimal("1.000"),
        )
        return order

    def _make_cancelled_order(self):
        order = self._make_draft_order()
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = timezone.now()
        order.save(update_fields=["status", "cancelled_at", "updated_at"])
        return order


# =============================================================================
# Test: send_order_to_kitchen
# =============================================================================

class TestSendOrderToKitchen(KitchenTestBase):

    def test_confirmed_order_creates_kitchen_order(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)

        self.assertIsNotNone(ko)
        self.assertIsInstance(ko, KitchenOrder)
        self.assertEqual(ko.order_id, order.id)
        self.assertEqual(ko.branch_id, self.branch.id)
        self.assertEqual(ko.status, KitchenOrderStatus.NEW)
        self.assertEqual(ko.priority, KitchenPriority.NORMAL)

    def test_kitchen_items_created_with_snapshots(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)

        self.assertEqual(ko.items.count(), 1)
        item = ko.items.first()
        self.assertEqual(item.item_name_snapshot, "Chicken Biryani")
        self.assertEqual(item.quantity, Decimal("2.000"))
        self.assertEqual(item.notes, "Less spicy")
        self.assertEqual(item.food_type, "NON_VEG")
        self.assertEqual(item.preparation_time_minutes, 20)
        self.assertEqual(item.status, KitchenItemStatus.NEW)

    def test_multiple_items_all_created(self):
        order = self._make_confirmed_order(extra_item=True)
        ko = send_order_to_kitchen(order)
        self.assertEqual(ko.items.count(), 2)

    def test_kitchen_item_no_financial_data(self):
        """Kitchen items must NOT have unit_price, tax_rate, etc."""
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        item = ko.items.first()
        # KitchenOrderItem has no unit_price_snapshot field
        self.assertFalse(hasattr(item, "unit_price_snapshot"))
        self.assertFalse(hasattr(item, "tax_rate_snapshot"))

    def test_draft_order_raises_validation_error(self):
        order = self._make_draft_order()
        with self.assertRaises(ValidationError) as ctx:
            send_order_to_kitchen(order)
        self.assertEqual(ctx.exception.detail["code"], "ORDER_NOT_CONFIRMED")

    def test_cancelled_order_raises_validation_error(self):
        order = self._make_cancelled_order()
        with self.assertRaises(ValidationError) as ctx:
            send_order_to_kitchen(order)
        self.assertEqual(ctx.exception.detail["code"], "ORDER_NOT_CONFIRMED")

    def test_idempotent_duplicate_call_returns_existing(self):
        """Calling send_order_to_kitchen twice must not create a duplicate."""
        order = self._make_confirmed_order()
        ko1 = send_order_to_kitchen(order)
        ko2 = send_order_to_kitchen(order)
        self.assertEqual(ko1.id, ko2.id)
        self.assertEqual(KitchenOrder.objects.filter(order=order).count(), 1)

    def test_branch_matches_order_branch(self):
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        self.assertEqual(ko.branch_id, order.branch_id)

    def test_order_type_accessible_on_kitchen_order(self):
        order = self._make_confirmed_order(order_type=OrderType.TAKEAWAY)
        ko = send_order_to_kitchen(order)
        self.assertEqual(ko.order_type, OrderType.TAKEAWAY)

    def test_order_item_snapshot_not_financial(self):
        """Snapshot copies name/qty/notes from OrderItem, not price/tax."""
        order = self._make_confirmed_order()
        ko = send_order_to_kitchen(order)
        ki = ko.items.first()
        # These exist on OrderItem but must NOT be on KitchenOrderItem
        self.assertFalse(hasattr(ki, "unit_price_snapshot"))
        self.assertFalse(hasattr(ki, "sku_snapshot"))


# =============================================================================
# Test: State machine — KitchenOrder
# =============================================================================

class TestKitchenOrderStateMachine(KitchenTestBase):

    def setUp(self):
        self.order = self._make_confirmed_order()
        self.ko = send_order_to_kitchen(self.order)

    def test_new_to_accepted(self):
        ko = accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ko.status, KitchenOrderStatus.ACCEPTED)
        self.assertIsNotNone(ko.accepted_at)
        self.assertEqual(ko.accepted_by, self.kitchen_user)

    def test_accepted_to_preparing(self):
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        ko = start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ko.status, KitchenOrderStatus.PREPARING)
        self.assertIsNotNone(ko.started_at)
        self.assertEqual(ko.started_by, self.kitchen_user)

    def test_preparing_to_ready(self):
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        # Mark all items ready first
        for item in self.ko.items.all():
            item.status = KitchenItemStatus.READY
            item.ready_at = timezone.now()
            item.save()
        ko = mark_order_ready(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ko.status, KitchenOrderStatus.READY)
        self.assertIsNotNone(ko.ready_at)
        self.assertEqual(ko.completed_by, self.kitchen_user)

    def test_invalid_new_to_preparing(self):
        """Cannot skip ACCEPTED."""
        with self.assertRaises(ValidationError) as ctx:
            start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_KITCHEN_TRANSITION")

    def test_invalid_new_to_ready(self):
        with self.assertRaises(ValidationError) as ctx:
            mark_order_ready(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ctx.exception.detail["code"], "INVALID_KITCHEN_TRANSITION")

    def test_invalid_ready_to_any(self):
        """READY is terminal — no further transitions."""
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        for item in self.ko.items.all():
            item.status = KitchenItemStatus.READY
            item.ready_at = timezone.now()
            item.save()
        mark_order_ready(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()

        with self.assertRaises(ValidationError):
            accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)

    def test_invalid_cancelled_to_any(self):
        """CANCELLED is terminal."""
        cancel_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()

        with self.assertRaises(ValidationError):
            accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)

    def test_cancel_from_new(self):
        ko = cancel_kitchen_order(self.kitchen_user, kitchen_order=self.ko, reason="Wrong order")
        self.assertEqual(ko.status, KitchenOrderStatus.CANCELLED)
        self.assertIsNotNone(ko.cancelled_at)
        self.assertEqual(ko.cancelled_by, self.kitchen_user)
        self.assertEqual(ko.cancellation_reason, "Wrong order")

    def test_cancel_from_accepted(self):
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        ko = cancel_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ko.status, KitchenOrderStatus.CANCELLED)

    def test_cancel_from_preparing(self):
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        ko = cancel_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ko.status, KitchenOrderStatus.CANCELLED)

    def test_cancel_also_cancels_items(self):
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        cancel_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        for item in self.ko.items.all():
            self.assertEqual(item.status, KitchenItemStatus.CANCELLED)

    def test_ready_requires_all_items_ready(self):
        """mark_order_ready must fail if items are not yet READY."""
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        # Items are still PREPARING — do NOT mark them ready
        with self.assertRaises(ValidationError) as ctx:
            mark_order_ready(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ctx.exception.detail["code"], "ITEMS_NOT_READY")

    def test_can_transition_to_helper(self):
        self.assertTrue(self.ko.can_transition_to(KitchenOrderStatus.ACCEPTED))
        self.assertTrue(self.ko.can_transition_to(KitchenOrderStatus.CANCELLED))
        self.assertFalse(self.ko.can_transition_to(KitchenOrderStatus.PREPARING))
        self.assertFalse(self.ko.can_transition_to(KitchenOrderStatus.READY))

    def test_priority_update_normal_to_urgent(self):
        ko = update_kitchen_priority(
            self.manager, kitchen_order=self.ko, priority=KitchenPriority.URGENT
        )
        self.assertEqual(ko.priority, KitchenPriority.URGENT)

    def test_priority_update_on_ready_raises(self):
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        for item in self.ko.items.all():
            item.status = KitchenItemStatus.READY
            item.ready_at = timezone.now()
            item.save()
        mark_order_ready(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()

        with self.assertRaises(ValidationError) as ctx:
            update_kitchen_priority(self.manager, kitchen_order=self.ko, priority=KitchenPriority.HIGH)
        self.assertEqual(ctx.exception.detail["code"], "TERMINAL_STATUS")

    def test_idempotent_accept(self):
        """Calling accept twice must not error — returns existing ACCEPTED state."""
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        # Second call — idempotent
        ko2 = accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.assertEqual(ko2.status, KitchenOrderStatus.ACCEPTED)

    def test_start_preparation_transitions_items_to_preparing(self):
        accept_kitchen_order(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        start_preparation(self.kitchen_user, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        for item in self.ko.items.all():
            self.assertEqual(item.status, KitchenItemStatus.PREPARING)
            self.assertIsNotNone(item.started_at)
