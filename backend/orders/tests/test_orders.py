# =============================================================================
# RestaurantFlow — Orders Tests: Order + OrderItem lifecycle
# Phase 6
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework.exceptions import ValidationError, PermissionDenied

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch
from counters.models import Counter, CounterSession, CounterStatus, SessionStatus
from menu.models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch
from orders.models import (
    DiningTable, TableSession, Order, OrderItem,
    TableStatus, TableSessionStatus, OrderStatus, OrderType,
)
from orders import services
from orders.tests.test_tables import (
    make_org, make_restaurant, make_branch, make_user,
    make_permission, make_role, assign_role,
    make_table, make_waiter_user,
)


# =============================================================================
# Additional helpers
# =============================================================================

def make_counter(branch, code="C01"):
    return Counter.objects.create(
        branch=branch,
        name=f"Counter {code}",
        code=code,
        status=CounterStatus.ACTIVE,
    )


def make_counter_session(counter, user):
    return CounterSession.objects.create(
        counter=counter,
        opened_by=user,
        opening_cash=Decimal("1000.00"),
        expected_cash=Decimal("1000.00"),
        status=SessionStatus.OPEN,
    )


def make_tax_rate(restaurant, code="GST5", rate="5.000"):
    return TaxRate.objects.create(
        restaurant=restaurant, name=f"Tax {code}", code=code, rate=Decimal(rate)
    )


def make_category(restaurant, name="Veg"):
    cat, _ = Category.objects.get_or_create(restaurant=restaurant, name=name)
    return cat


def make_menu_item(restaurant, category, name="Test Item", sku="TSKU"):
    return MenuItem.objects.create(
        restaurant=restaurant,
        category=category,
        name=name,
        sku=sku,
        is_active=True,
        is_available=True,
    )


def make_branch_price(menu_item, branch, price="100.00"):
    return MenuItemPrice.objects.create(
        menu_item=menu_item,
        branch=branch,
        price=Decimal(price),
        is_active=True,
    )


def make_branch_availability(menu_item, branch):
    avail, _ = MenuItemBranch.objects.get_or_create(
        menu_item=menu_item,
        branch=branch,
        defaults={"is_available": True},
    )
    return avail


def open_table_and_order(actor, branch, table_number="T01"):
    """Helper: create table, open session, return (table, session)."""
    table = make_table(branch, number=table_number)
    session = services.open_table_session(actor, table=table, guest_count=2)
    return table, session


# =============================================================================
# Order Number Generation Tests
# =============================================================================

class OrderNumberTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.counter = make_counter(self.branch)

    def test_dine_in_order_number_prefix(self):
        from django.db import transaction
        with transaction.atomic():
            num = services.generate_order_number(
                branch=self.branch, order_type="DINE_IN"
            )
        self.assertTrue(num.startswith("D-"), f"Expected D- prefix, got {num}")

    def test_counter_order_number_uses_counter_code(self):
        from django.db import transaction
        with transaction.atomic():
            num = services.generate_order_number(
                branch=self.branch,
                order_type="COUNTER",
                counter=self.counter,
            )
        self.assertTrue(
            num.startswith("C01-"), f"Expected C01- prefix, got {num}"
        )

    def test_order_numbers_increment_sequentially(self):
        from django.db import transaction
        with transaction.atomic():
            n1 = services.generate_order_number(branch=self.branch, order_type="DINE_IN")
        with transaction.atomic():
            n2 = services.generate_order_number(branch=self.branch, order_type="DINE_IN")
        # Extract sequence numbers
        seq1 = int(n1.split("-")[-1])
        seq2 = int(n2.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_dine_in_and_counter_sequences_independent(self):
        from django.db import transaction
        with transaction.atomic():
            d1 = services.generate_order_number(branch=self.branch, order_type="DINE_IN")
        with transaction.atomic():
            c1 = services.generate_order_number(
                branch=self.branch, order_type="COUNTER", counter=self.counter
            )
        # Both start at 0001
        self.assertEqual(d1.split("-")[-1], "0001")
        self.assertEqual(c1.split("-")[-1], "0001")


# =============================================================================
# Order Creation Tests
# =============================================================================

class DineInOrderTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.actor = make_waiter_user(self.branch, email="waiter@test.com")
        self.table = make_table(self.branch, number="T01")

    def test_create_dine_in_order(self):
        session = services.open_table_session(self.actor, table=self.table, guest_count=2)
        order = services.create_order(
            self.actor,
            branch=self.branch,
            order_type=OrderType.DINE_IN,
            table=self.table,
            table_session=session,
            guest_count=2,
        )
        self.assertEqual(order.order_type, OrderType.DINE_IN)
        self.assertEqual(order.status, OrderStatus.DRAFT)
        self.assertEqual(order.table, self.table)
        self.assertEqual(order.table_session, session)
        self.assertIsNotNone(order.order_number)
        self.assertTrue(order.order_number.startswith("D-"))

    def test_dine_in_requires_table(self):
        session = services.open_table_session(self.actor, table=self.table, guest_count=2)
        with self.assertRaises(ValidationError) as ctx:
            services.create_order(
                self.actor,
                branch=self.branch,
                order_type=OrderType.DINE_IN,
                table=None,
                table_session=session,
            )
        self.assertIn("table", str(ctx.exception.detail))

    def test_dine_in_requires_table_session(self):
        with self.assertRaises(ValidationError) as ctx:
            services.create_order(
                self.actor,
                branch=self.branch,
                order_type=OrderType.DINE_IN,
                table=self.table,
                table_session=None,
            )
        self.assertIn("table_session", str(ctx.exception.detail))

    def test_dine_in_rejects_cross_branch_table(self):
        other_branch = make_branch(self.restaurant, name="Other", code="OTH")
        other_table = make_table(other_branch, number="T01")
        other_actor = make_waiter_user(other_branch, email="other_waiter@test.com")
        # Open a session on the other branch's table
        other_session = services.open_table_session(
            other_actor, table=other_table, guest_count=2
        )
        with self.assertRaises((ValidationError, PermissionDenied)):
            services.create_order(
                self.actor,
                branch=self.branch,
                order_type=OrderType.DINE_IN,
                table=other_table,         # wrong branch!
                table_session=other_session,
            )

    def test_dine_in_cannot_have_counter_reference(self):
        session = services.open_table_session(self.actor, table=self.table, guest_count=2)
        counter = make_counter(self.branch)
        with self.assertRaises(ValidationError):
            services.create_order(
                self.actor,
                branch=self.branch,
                order_type=OrderType.DINE_IN,
                table=self.table,
                table_session=session,
                counter=counter,  # should be rejected
            )

    def test_inactive_table_cannot_receive_order(self):
        self.table.status = TableStatus.INACTIVE
        self.table.save()
        session = TableSession.objects.create(
            table=self.table, opened_by=self.actor, status=TableSessionStatus.OPEN
        )
        with self.assertRaises(ValidationError) as ctx:
            services.create_order(
                self.actor,
                branch=self.branch,
                order_type=OrderType.DINE_IN,
                table=self.table,
                table_session=session,
            )
        self.assertIn("inactive", str(ctx.exception.detail).lower())


class CounterOrderTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.actor = make_waiter_user(self.branch, email="cashier@test.com")
        self.counter = make_counter(self.branch)
        self.counter_session = make_counter_session(self.counter, self.actor)

    def test_create_counter_order(self):
        order = services.create_order(
            self.actor,
            branch=self.branch,
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
        )
        self.assertEqual(order.order_type, OrderType.COUNTER)
        self.assertEqual(order.status, OrderStatus.DRAFT)
        self.assertEqual(order.counter, self.counter)
        self.assertTrue(order.order_number.startswith("C01-"))

    def test_create_takeaway_order(self):
        order = services.create_order(
            self.actor,
            branch=self.branch,
            order_type=OrderType.TAKEAWAY,
            counter=self.counter,
            counter_session=self.counter_session,
        )
        self.assertEqual(order.order_type, OrderType.TAKEAWAY)

    def test_counter_order_rejects_cross_branch_counter(self):
        other_branch = make_branch(self.restaurant, name="OtherB", code="OTH")
        other_counter = make_counter(other_branch, code="C99")
        other_user = make_waiter_user(other_branch, email="other@test.com")
        other_session = make_counter_session(other_counter, other_user)
        with self.assertRaises((ValidationError, PermissionDenied)):
            services.create_order(
                self.actor,
                branch=self.branch,
                order_type=OrderType.COUNTER,
                counter=other_counter,  # wrong branch
                counter_session=other_session,
            )

    def test_counter_order_cannot_have_table_reference(self):
        table = make_table(self.branch, number="T01")
        with self.assertRaises(ValidationError):
            services.create_order(
                self.actor,
                branch=self.branch,
                order_type=OrderType.COUNTER,
                counter=self.counter,
                counter_session=self.counter_session,
                table=table,  # should be rejected
            )

    def test_closed_counter_session_rejected(self):
        self.counter_session.status = SessionStatus.CLOSED
        self.counter_session.save()
        with self.assertRaises(ValidationError) as ctx:
            services.create_order(
                self.actor,
                branch=self.branch,
                order_type=OrderType.COUNTER,
                counter=self.counter,
                counter_session=self.counter_session,
            )
        self.assertIn("not open", str(ctx.exception.detail).lower())

    def test_unauthorized_user_cannot_create_order(self):
        unauth = make_user(email="unauth2@test.com")
        with self.assertRaises(PermissionDenied):
            services.create_order(
                unauth,
                branch=self.branch,
                order_type=OrderType.COUNTER,
                counter=self.counter,
                counter_session=self.counter_session,
            )


# =============================================================================
# Order Confirm / Cancel Tests
# =============================================================================

class OrderLifecycleTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.actor = make_waiter_user(self.branch, email="lifecycle@test.com")
        self.table = make_table(self.branch, number="T01")
        self.session = services.open_table_session(
            self.actor, table=self.table, guest_count=2
        )
        self.order = services.create_order(
            self.actor,
            branch=self.branch,
            order_type=OrderType.DINE_IN,
            table=self.table,
            table_session=self.session,
            guest_count=2,
        )
        # Setup menu item for adding items
        self.tax_rate = make_tax_rate(self.restaurant)
        self.category = make_category(self.restaurant)
        self.menu_item = make_menu_item(self.restaurant, self.category)
        make_branch_price(self.menu_item, self.branch)
        make_branch_availability(self.menu_item, self.branch)

    def test_draft_order_allows_adding_items(self):
        item = services.add_order_item(
            self.actor,
            order=self.order,
            menu_item_id=self.menu_item.pk,
            quantity=Decimal("2"),
        )
        self.assertEqual(item.quantity, Decimal("2"))
        self.assertEqual(item.order, self.order)

    def test_confirm_order_with_items(self):
        services.add_order_item(
            self.actor, order=self.order,
            menu_item_id=self.menu_item.pk, quantity=Decimal("1")
        )
        confirmed = services.confirm_order(self.actor, order=self.order)
        self.assertEqual(confirmed.status, OrderStatus.CONFIRMED)
        self.assertIsNotNone(confirmed.confirmed_at)

    def test_cannot_confirm_empty_order(self):
        with self.assertRaises(ValidationError) as ctx:
            services.confirm_order(self.actor, order=self.order)
        self.assertEqual(ctx.exception.detail["code"], "ORDER_EMPTY")

    def test_cannot_confirm_already_confirmed_order(self):
        services.add_order_item(
            self.actor, order=self.order,
            menu_item_id=self.menu_item.pk, quantity=Decimal("1")
        )
        services.confirm_order(self.actor, order=self.order)
        with self.assertRaises(ValidationError) as ctx:
            services.confirm_order(self.actor, order=self.order)
        self.assertEqual(ctx.exception.detail["code"], "ORDER_NOT_DRAFT")

    def test_cancel_draft_order(self):
        cancelled = services.cancel_order(
            self.actor, order=self.order, reason="Changed mind"
        )
        self.assertEqual(cancelled.status, OrderStatus.CANCELLED)
        self.assertIsNotNone(cancelled.cancelled_at)
        self.assertEqual(cancelled.cancellation_reason, "Changed mind")

    def test_cancel_confirmed_order_requires_stronger_permission(self):
        services.add_order_item(
            self.actor, order=self.order,
            menu_item_id=self.menu_item.pk, quantity=Decimal("1")
        )
        services.confirm_order(self.actor, order=self.order)
        # Actor has order.cancel.confirmed permission (via make_waiter_user)
        cancelled = services.cancel_order(
            self.actor, order=self.order, reason="Kitchen error"
        )
        self.assertEqual(cancelled.status, OrderStatus.CANCELLED)

    def test_cannot_cancel_already_cancelled_order(self):
        services.cancel_order(self.actor, order=self.order)
        with self.assertRaises(ValidationError) as ctx:
            services.cancel_order(self.actor, order=self.order)
        self.assertEqual(ctx.exception.detail["code"], "ORDER_ALREADY_CANCELLED")

    def test_order_not_physically_deleted_after_cancel(self):
        services.cancel_order(self.actor, order=self.order)
        # Order still exists in DB
        self.assertTrue(Order.objects.filter(pk=self.order.pk).exists())

    def test_assign_waiter(self):
        waiter2 = make_waiter_user(self.branch, email="waiter2@test.com")
        updated = services.assign_waiter(
            self.actor, order=self.order, waiter=waiter2
        )
        self.assertEqual(updated.assigned_waiter, waiter2)

    def test_assign_waiter_from_another_branch_rejected(self):
        other_branch = make_branch(self.restaurant, name="OtherB", code="OB2")
        other_waiter = make_waiter_user(other_branch, email="ow@test.com")
        with self.assertRaises(ValidationError):
            services.assign_waiter(self.actor, order=self.order, waiter=other_waiter)


# =============================================================================
# OrderItem Tests
# =============================================================================

class OrderItemTests(TestCase):
    def setUp(self):
        self.org = make_org()
        self.restaurant = make_restaurant(self.org)
        self.branch = make_branch(self.restaurant)
        self.actor = make_waiter_user(self.branch, email="oi_actor@test.com")
        self.table = make_table(self.branch, number="T01")
        self.session = services.open_table_session(
            self.actor, table=self.table, guest_count=2
        )
        self.order = services.create_order(
            self.actor,
            branch=self.branch,
            order_type=OrderType.DINE_IN,
            table=self.table,
            table_session=self.session,
        )
        self.tax_rate = make_tax_rate(self.restaurant, code="GST_STD", rate="5.000")
        self.category = make_category(self.restaurant)
        self.menu_item = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name="Biryani",
            sku="BIR-001",
            tax_rate=self.tax_rate,
            is_active=True,
            is_available=True,
        )
        make_branch_price(self.menu_item, self.branch, price="250.00")
        make_branch_availability(self.menu_item, self.branch)

    def test_add_item_snapshots_price_and_tax(self):
        item = services.add_order_item(
            self.actor,
            order=self.order,
            menu_item_id=self.menu_item.pk,
            quantity=Decimal("2"),
        )
        self.assertEqual(item.item_name_snapshot, "Biryani")
        self.assertEqual(item.sku_snapshot, "BIR-001")
        self.assertEqual(item.unit_price_snapshot, Decimal("250.00"))
        self.assertEqual(item.tax_rate_snapshot, Decimal("5.000"))
        self.assertEqual(item.tax_code_snapshot, "GST_STD")
        self.assertEqual(item.quantity, Decimal("2"))

    def test_price_snapshot_immutable_after_price_change(self):
        item = services.add_order_item(
            self.actor, order=self.order,
            menu_item_id=self.menu_item.pk, quantity=Decimal("1")
        )
        original_snapshot = item.unit_price_snapshot

        # Change the branch price
        MenuItemPrice.objects.filter(
            menu_item=self.menu_item, branch=self.branch, is_active=True
        ).update(price=Decimal("999.00"))

        # Reload item — snapshot must remain unchanged
        item.refresh_from_db()
        self.assertEqual(item.unit_price_snapshot, original_snapshot)
        self.assertNotEqual(item.unit_price_snapshot, Decimal("999.00"))

    def test_inactive_item_rejected(self):
        self.menu_item.is_active = False
        self.menu_item.save()
        with self.assertRaises(ValidationError) as ctx:
            services.add_order_item(
                self.actor, order=self.order,
                menu_item_id=self.menu_item.pk, quantity=Decimal("1")
            )
        self.assertIn("not active", str(ctx.exception.detail).lower())

    def test_unavailable_item_rejected(self):
        self.menu_item.is_available = False
        self.menu_item.save()
        with self.assertRaises(ValidationError):
            services.add_order_item(
                self.actor, order=self.order,
                menu_item_id=self.menu_item.pk, quantity=Decimal("1")
            )

    def test_wrong_restaurant_item_rejected(self):
        other_org = make_org("Other Org 2")
        other_rest = make_restaurant(other_org, "Other Rest 2")
        other_cat = make_category(other_rest, name="Other Cat")
        other_item = make_menu_item(other_rest, other_cat, name="Foreign Item", sku="FRN")
        make_branch_availability(other_item, self.branch)
        with self.assertRaises(ValidationError) as ctx:
            services.add_order_item(
                self.actor, order=self.order,
                menu_item_id=other_item.pk, quantity=Decimal("1")
            )
        self.assertIn("restaurant", str(ctx.exception.detail).lower())

    def test_no_branch_price_rejected(self):
        item_no_price = MenuItem.objects.create(
            restaurant=self.restaurant,
            category=self.category,
            name="No Price Item",
            sku="NP1",
            is_active=True,
            is_available=True,
        )
        make_branch_availability(item_no_price, self.branch)
        with self.assertRaises(ValidationError) as ctx:
            services.add_order_item(
                self.actor, order=self.order,
                menu_item_id=item_no_price.pk, quantity=Decimal("1")
            )
        self.assertIn("price", str(ctx.exception.detail).lower())

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_order_item(
                self.actor, order=self.order,
                menu_item_id=self.menu_item.pk, quantity=Decimal("0")
            )

    def test_negative_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            services.add_order_item(
                self.actor, order=self.order,
                menu_item_id=self.menu_item.pk, quantity=Decimal("-1")
            )

    def test_update_order_item_quantity(self):
        item = services.add_order_item(
            self.actor, order=self.order,
            menu_item_id=self.menu_item.pk, quantity=Decimal("1")
        )
        updated = services.update_order_item(self.actor, item=item, quantity=Decimal("3"))
        self.assertEqual(updated.quantity, Decimal("3"))

    def test_remove_order_item(self):
        item = services.add_order_item(
            self.actor, order=self.order,
            menu_item_id=self.menu_item.pk, quantity=Decimal("1")
        )
        item_pk = item.pk
        services.remove_order_item(self.actor, item=item)
        self.assertFalse(OrderItem.objects.filter(pk=item_pk).exists())

    def test_cannot_add_item_to_confirmed_order(self):
        services.add_order_item(
            self.actor, order=self.order,
            menu_item_id=self.menu_item.pk, quantity=Decimal("1")
        )
        services.confirm_order(self.actor, order=self.order)
        with self.assertRaises(ValidationError) as ctx:
            services.add_order_item(
                self.actor, order=self.order,
                menu_item_id=self.menu_item.pk, quantity=Decimal("1")
            )
        self.assertEqual(ctx.exception.detail["code"], "ORDER_NOT_DRAFT")

    def test_line_total_calculation(self):
        item = services.add_order_item(
            self.actor, order=self.order,
            menu_item_id=self.menu_item.pk, quantity=Decimal("3")
        )
        expected = Decimal("3") * Decimal("250.00")
        self.assertEqual(item.line_total, expected)
