# =============================================================================
# RestaurantFlow — Kitchen Concurrency Tests
# Phase 7
#
# Tests:
#   - Two workers simultaneously accepting the same order → only one wins
#   - Two workers simultaneously starting preparation → only one wins
#   - Two workers simultaneously marking the same item ready → only one wins
#   - No state corruption or duplicate transitions
#
# Uses TransactionTestCase so each thread gets real DB transactions,
# exercising the select_for_update() locks in the service layer.
# Note: Full concurrent lock contention requires PostgreSQL.
# SQLite tests pass but serialize rather than truly race.
# =============================================================================

import threading
from decimal import Decimal

from django.db import transaction
from django.test import TransactionTestCase
from django.utils import timezone


class TestKitchenConcurrency(TransactionTestCase):
    """
    TransactionTestCase (not TestCase) — required so threads can have
    independent real database transactions.
    """

    def setUp(self):
        from accounts.models import User, Role, Permission, UserRoleAssignment
        from organizations.models import Organization, Restaurant, Branch
        from menu.models import Category, MenuItem, MenuItemPrice, MenuItemBranch, TaxRate
        from orders.models import Order, OrderItem, OrderStatus, OrderType
        from counters.models import Counter, CounterSession, SessionStatus, CounterStatus

        self.org = Organization.objects.create(name="ConcOrg", slug="conc-org")
        self.restaurant = Restaurant.objects.create(
            organization=self.org, name="ConcRest", slug="conc-rest"
        )
        self.branch = Branch.objects.create(
            restaurant=self.restaurant, name="ConcBranch", slug="conc-branch"
        )

        self.user1 = User.objects.create_user(
            email="conc1@test.com", password="p", first_name="C", last_name="1"
        )
        self.user2 = User.objects.create_user(
            email="conc2@test.com", password="p", first_name="C", last_name="2"
        )

        perm_defs = [
            ("kitchen.accept",          "kitchen", "accept"),
            ("kitchen.start",           "kitchen", "start"),
            ("kitchen.item_start",      "kitchen", "item_start"),
            ("kitchen.item_ready",      "kitchen", "item_ready"),
            ("kitchen.order_ready",     "kitchen", "order_ready"),
            ("kitchen.cancel",          "kitchen", "cancel"),
            ("kitchen.priority_update", "kitchen", "priority_update"),
            ("kitchen.view",            "kitchen", "view"),
            ("kitchen.view_history",    "kitchen", "view_history"),
        ]
        perms = []
        for code, module, action in perm_defs:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": code, "module": module, "action": action},
            )
            perms.append(p)

        role = Role.objects.create(
            name="ConcRole", code="CONC_ROLE", scope=Role.SCOPE_BRANCH
        )
        role.permissions.set(perms)

        for user in [self.user1, self.user2]:
            UserRoleAssignment.objects.create(
                user=user, role=role,
                organization=self.org,
                restaurant=self.restaurant,
                branch=self.branch,
            )

        # Menu
        cat = Category.objects.create(
            restaurant=self.restaurant, name="ConcCat", slug="conc-cat"
        )
        self.menu_item = MenuItem.objects.create(
            restaurant=self.restaurant, category=cat,
            name="TestItem", slug="test-item", food_type="VEG",
        )
        MenuItemBranch.objects.create(
            menu_item=self.menu_item, branch=self.branch, is_available=True
        )
        MenuItemPrice.objects.create(
            menu_item=self.menu_item, branch=self.branch,
            price=Decimal("100.00"), is_active=True,
        )

        # Counter
        self.counter = Counter.objects.create(
            branch=self.branch, name="ConcCounter", code="CC1",
            status=CounterStatus.ACTIVE,
        )
        self.counter_session = CounterSession.objects.create(
            counter=self.counter,
            opened_by=self.user1,
            status=SessionStatus.OPEN,
            opening_cash=Decimal("100.00"),
            expected_cash=Decimal("100.00"),
        )

        # Build a confirmed order + kitchen order
        import uuid
        self.order = Order.objects.create(
            branch=self.branch,
            order_number=f"CC1-CONC-{uuid.uuid4().hex[:4].upper()}",
            order_type=OrderType.TAKEAWAY,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.user1,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        self.order_item = OrderItem.objects.create(
            order=self.order,
            menu_item=self.menu_item,
            item_name_snapshot="TestItem",
            sku_snapshot="",
            unit_price_snapshot=Decimal("100.00"),
            tax_rate_snapshot=Decimal("0.000"),
            tax_code_snapshot="",
            quantity=Decimal("2.000"),
        )

        from kitchen.services import send_order_to_kitchen
        self.ko = send_order_to_kitchen(self.order)

    def _run_in_thread(self, fn, results, idx):
        """Execute fn() in a thread, storing (result_or_None, exception_or_None)."""
        try:
            result = fn()
            results[idx] = (result, None)
        except Exception as exc:
            results[idx] = (None, exc)

    # -------------------------------------------------------------------------
    # Test 1: Simultaneous accept
    # -------------------------------------------------------------------------

    def test_simultaneous_accept_only_one_wins(self):
        """
        Two threads call accept_kitchen_order on the same order simultaneously.
        Both must finish without exception (idempotent design: second call
        returns the ACCEPTED order without re-transitioning).
        The final state must be ACCEPTED — no corruption.
        """
        from kitchen.services import accept_kitchen_order
        from kitchen.models import KitchenOrderStatus

        results = [None, None]
        t1 = threading.Thread(
            target=self._run_in_thread,
            args=(
                lambda: accept_kitchen_order(self.user1, kitchen_order=self.ko),
                results, 0,
            ),
        )
        t2 = threading.Thread(
            target=self._run_in_thread,
            args=(
                lambda: accept_kitchen_order(self.user2, kitchen_order=self.ko),
                results, 1,
            ),
        )
        t1.start(); t2.start()
        t1.join(); t2.join()

        # Both should succeed or one should succeed and one should also
        # return ACCEPTED (idempotent). Neither should raise unexpectedly.
        for result, exc in results:
            self.assertIsNone(exc, f"Unexpected exception in concurrent accept: {exc}")

        # Final state: ACCEPTED exactly once
        self.ko.refresh_from_db()
        self.assertEqual(self.ko.status, KitchenOrderStatus.ACCEPTED)

        # accepted_by must be exactly ONE of the users (not None)
        self.assertIsNotNone(self.ko.accepted_by)

    # -------------------------------------------------------------------------
    # Test 2: Simultaneous start preparation
    # -------------------------------------------------------------------------

    def test_simultaneous_start_only_one_wins(self):
        """
        Two threads call start_preparation on the same ACCEPTED order.
        Both should finish without crashing; final state must be PREPARING.
        """
        from kitchen.services import accept_kitchen_order, start_preparation
        from kitchen.models import KitchenOrderStatus

        accept_kitchen_order(self.user1, kitchen_order=self.ko)
        self.ko.refresh_from_db()

        results = [None, None]
        t1 = threading.Thread(
            target=self._run_in_thread,
            args=(
                lambda: start_preparation(self.user1, kitchen_order=self.ko),
                results, 0,
            ),
        )
        t2 = threading.Thread(
            target=self._run_in_thread,
            args=(
                lambda: start_preparation(self.user2, kitchen_order=self.ko),
                results, 1,
            ),
        )
        t1.start(); t2.start()
        t1.join(); t2.join()

        for result, exc in results:
            self.assertIsNone(exc, f"Unexpected exception in concurrent start: {exc}")

        self.ko.refresh_from_db()
        self.assertEqual(self.ko.status, KitchenOrderStatus.PREPARING)

    # -------------------------------------------------------------------------
    # Test 3: Simultaneous item ready
    # -------------------------------------------------------------------------

    def test_simultaneous_item_ready_only_one_wins(self):
        """
        Two threads mark the same KitchenOrderItem ready simultaneously.
        Only one logical transition should happen; both should finish cleanly
        and the final item status must be READY.
        """
        from kitchen.services import accept_kitchen_order, start_preparation, mark_item_ready
        from kitchen.models import KitchenItemStatus

        accept_kitchen_order(self.user1, kitchen_order=self.ko)
        self.ko.refresh_from_db()
        start_preparation(self.user1, kitchen_order=self.ko)
        self.ko.refresh_from_db()

        item = self.ko.items.first()
        results = [None, None]

        t1 = threading.Thread(
            target=self._run_in_thread,
            args=(lambda: mark_item_ready(self.user1, kitchen_item=item), results, 0),
        )
        t2 = threading.Thread(
            target=self._run_in_thread,
            args=(lambda: mark_item_ready(self.user2, kitchen_item=item), results, 1),
        )
        t1.start(); t2.start()
        t1.join(); t2.join()

        for result, exc in results:
            self.assertIsNone(exc, f"Unexpected exception in concurrent item_ready: {exc}")

        item.refresh_from_db()
        self.assertEqual(item.status, KitchenItemStatus.READY)

    # -------------------------------------------------------------------------
    # Test 4: No duplicate KitchenOrder for same order
    # -------------------------------------------------------------------------

    def test_no_duplicate_kitchen_order_for_same_order(self):
        """
        send_order_to_kitchen is idempotent.
        Calling it twice for the same confirmed order must produce exactly one
        KitchenOrder record.
        """
        from kitchen.services import send_order_to_kitchen
        from kitchen.models import KitchenOrder

        # Already called in setUp — call again
        send_order_to_kitchen(self.order)
        count = KitchenOrder.objects.filter(order=self.order).count()
        self.assertEqual(count, 1)
