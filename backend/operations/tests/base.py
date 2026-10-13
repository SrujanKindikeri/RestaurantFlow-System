# =============================================================================
# RestaurantFlow — Operations Test Base
# Phase 19: Advanced POS & Restaurant Operations
#
# Shared fixture stack for all operations integration tests.
# Extends the billing/orders fixture pattern used across the project.
#
# Fixture hierarchy:
#   Org → Restaurant → Branch (main + other_branch)
#   Users: cashier, manager, owner, waiter, other_user
#   Roles + Permissions: all Phase 19 operations permissions
#   Counter + CounterSession
#   DiningTable (table_a, table_b, table_c)
#   Menu: category, item_pizza, item_burger
#   TaxRate, MenuItemPrice
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
from counters.models import Counter, CounterSession, SessionStatus, CounterStatus
from orders.models import Order, OrderItem, OrderType, OrderStatus, DiningTable, TableSession
from menu.models import Category, MenuItem, MenuItemPrice, TaxRate


class OperationsTestBase(TestCase):
    """
    Base class for Phase 19 operations tests.
    setUpTestData runs once per test class.
    """

    @classmethod
    def setUpTestData(cls):
        # ------------------------------------------------------------------
        # Org / Restaurant / Branch
        # ------------------------------------------------------------------
        cls.org = Organization.objects.create(
            name="OpsTest Org", slug="opstest-org", currency="INR",
        )
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org, name="OpsTest Restaurant",
            slug="opstest-restaurant", code="OR01",
        )
        RestaurantSettings.objects.create(
            restaurant=cls.restaurant, currency="INR",
            tax_enabled=True, default_tax_rate=Decimal("5.00"),
        )
        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant, name="Main Branch", code="MB01",
        )
        BranchSettings.objects.create(branch=cls.branch)

        cls.other_branch = Branch.objects.create(
            restaurant=cls.restaurant, name="Other Branch", code="OB01",
        )

        # ------------------------------------------------------------------
        # Users
        # ------------------------------------------------------------------
        cls.cashier = User.objects.create_user(
            email="cashier@ops.test", password="pass123",
            first_name="Cashier", last_name="User",
        )
        cls.manager = User.objects.create_user(
            email="manager@ops.test", password="pass123",
            first_name="Manager", last_name="User",
        )
        cls.waiter = User.objects.create_user(
            email="waiter@ops.test", password="pass123",
            first_name="Waiter", last_name="User",
        )
        cls.owner = User.objects.create_user(
            email="owner@ops.test", password="pass123",
            first_name="Owner", last_name="User",
        )
        cls.other_user = User.objects.create_user(
            email="other@ops.test", password="pass123",
            first_name="Other", last_name="Branch",
        )

        # ------------------------------------------------------------------
        # Permissions
        # ------------------------------------------------------------------
        perm_defs = [
            # POS
            ("pos.access",                "pos",       "access"),
            ("pos.session.start",         "pos",       "session_start"),
            ("pos.session.pause",         "pos",       "session_pause"),
            ("pos.session.end",           "pos",       "session_end"),
            ("pos.order.create",          "pos",       "order_create"),
            ("pos.order.hold",            "pos",       "order_hold"),
            ("pos.order.resume",          "pos",       "order_resume"),
            ("pos.order.priority",        "pos",       "order_priority"),
            ("pos.order.priority.urgent", "pos",       "order_priority_urgent"),
            # Orders
            ("order.modifier.manage",     "order",     "modifier_manage"),
            ("order.change.request",      "order",     "change_request"),
            ("order.change.approve",      "order",     "change_approve"),
            ("order.waiter.assign",       "order",     "waiter_assign"),
            ("order.waiter.reassign",     "order",     "waiter_reassign"),
            ("order.merge",               "order",     "merge"),
            # Tables
            ("table.view",                "table",     "view"),
            ("table.manage",              "table",     "manage"),
            ("table.transfer",            "table",     "transfer"),
            ("table.merge",               "table",     "merge"),
            # Bills
            ("bill.split",                "bill",      "split"),
            # Receipts
            ("receipt.print",             "receipt",   "print"),
            ("receipt.reprint",           "receipt",   "reprint"),
            # Shifts
            ("shift.view",                "shift",     "view"),
            ("shift.create",              "shift",     "create"),
            ("shift.close",               "shift",     "close"),
            ("shift.handover.view",       "shift",     "handover_view"),
            # Dashboard
            ("operations.dashboard.view", "operations","dashboard_view"),
            # Existing order/billing perms needed
            ("order.view.branch",         "order",     "view_branch"),
            ("order.create.counter",      "order",     "create_counter"),
            ("bill.view",                 "billing",   "view"),
            ("bill.create",               "billing",   "create"),
            ("bill.finalize",             "billing",   "finalize"),
        ]
        cls.perms = {}
        for code, module, action in perm_defs:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": code, "description": "", "module": module, "action": action},
            )
            cls.perms[code] = p

        # ------------------------------------------------------------------
        # Roles
        # ------------------------------------------------------------------
        cls.cashier_role = Role.objects.create(
            name="Cashier Ops", code="CASHIER_OPS", scope=Role.SCOPE_BRANCH,
        )
        cashier_perms = [
            "pos.access", "pos.session.start", "pos.session.pause",
            "pos.session.end", "pos.order.create", "pos.order.hold",
            "pos.order.resume", "pos.order.priority",
            "order.modifier.manage", "order.change.request",
            "order.waiter.assign", "table.view", "table.manage",
            "table.transfer", "bill.split", "receipt.print",
            "receipt.reprint", "shift.view", "shift.create", "shift.close",
            "shift.handover.view", "operations.dashboard.view",
            "order.view.branch", "order.create.counter",
            "bill.view", "bill.create", "bill.finalize",
        ]
        cls.cashier_role.permissions.set([cls.perms[c] for c in cashier_perms])

        cls.manager_role = Role.objects.create(
            name="Manager Ops", code="MANAGER_OPS", scope=Role.SCOPE_BRANCH,
        )
        cls.manager_role.permissions.set(list(cls.perms.values()))

        cls.waiter_role = Role.objects.create(
            name="Waiter Ops", code="WAITER_OPS", scope=Role.SCOPE_BRANCH,
        )
        waiter_perms = [
            "table.view", "order.view.branch", "order.waiter.assign",
            "order.modifier.manage",
        ]
        cls.waiter_role.permissions.set([cls.perms[c] for c in waiter_perms])

        # ------------------------------------------------------------------
        # Role assignments
        # ------------------------------------------------------------------
        for user, role in [
            (cls.cashier, cls.cashier_role),
            (cls.manager, cls.manager_role),
            (cls.waiter, cls.waiter_role),
        ]:
            UserRoleAssignment.objects.create(
                user=user, role=role,
                organization=cls.org,
                restaurant=cls.restaurant,
                branch=cls.branch,
            )
        UserRoleAssignment.objects.create(
            user=cls.owner, role=cls.manager_role,
            organization=cls.org, restaurant=cls.restaurant,
        )
        UserRoleAssignment.objects.create(
            user=cls.other_user, role=cls.cashier_role,
            organization=cls.org, restaurant=cls.restaurant,
            branch=cls.other_branch,
        )

        # ------------------------------------------------------------------
        # Tax rate
        # ------------------------------------------------------------------
        cls.tax_gst5, _ = TaxRate.objects.get_or_create(
            code="GST_5", defaults={"name": "GST 5%", "rate": Decimal("5.000"), "is_active": True},
        )

        # ------------------------------------------------------------------
        # Menu
        # ------------------------------------------------------------------
        cls.category = Category.objects.create(
            restaurant=cls.restaurant, name="Mains", slug="mains",
        )
        cls.item_pizza = MenuItem.objects.create(
            restaurant=cls.restaurant, category=cls.category,
            name="Margherita Pizza", slug="margherita-pizza",
            sku="SKU-PIZZA", base_price=Decimal("350.00"),
            tax_rate=cls.tax_gst5, is_active=True,
        )
        cls.item_burger = MenuItem.objects.create(
            restaurant=cls.restaurant, category=cls.category,
            name="Classic Burger", slug="classic-burger",
            sku="SKU-BURGER", base_price=Decimal("250.00"),
            tax_rate=cls.tax_gst5, is_active=True,
        )

        # ------------------------------------------------------------------
        # Counter + CounterSession
        # ------------------------------------------------------------------
        cls.counter = Counter.objects.create(
            branch=cls.branch, name="Main Counter", code="C01",
            status=CounterStatus.ACTIVE,
        )
        cls.counter_session = CounterSession.objects.create(
            counter=cls.counter, opened_by=cls.cashier,
            opening_cash=Decimal("500.00"), status=SessionStatus.OPEN,
        )

        # ------------------------------------------------------------------
        # DiningTables
        # ------------------------------------------------------------------
        cls.table_a = DiningTable.objects.create(
            branch=cls.branch, table_number="T01", capacity=4, section="Indoor",
        )
        cls.table_b = DiningTable.objects.create(
            branch=cls.branch, table_number="T02", capacity=4, section="Indoor",
        )
        cls.table_c = DiningTable.objects.create(
            branch=cls.branch, table_number="T03", capacity=2, section="Outdoor",
        )

        # Other branch table — for isolation tests
        cls.other_table = DiningTable.objects.create(
            branch=cls.other_branch, table_number="T01", capacity=4,
        )

    def _make_order(self, status=None, order_type=None, table=None, counter=None, created_by=None):
        """Helper: create an Order with one OrderItem."""
        from django.utils import timezone as tz
        o = Order.objects.create(
            branch=self.branch,
            order_number=f"TEST-{Order.objects.count() + 1:04d}",
            order_type=order_type or OrderType.COUNTER,
            status=status or OrderStatus.DRAFT,
            counter=counter or self.counter,
            counter_session=self.counter_session,
            table=table,
            created_by=created_by or self.cashier,
        )
        OrderItem.objects.create(
            order=o,
            menu_item=self.item_pizza,
            item_name_snapshot=self.item_pizza.name,
            sku_snapshot=self.item_pizza.sku,
            unit_price_snapshot=Decimal("350.00"),
            tax_rate_snapshot=Decimal("5.000"),
            tax_code_snapshot="GST_5",
            quantity=Decimal("1"),
        )
        return o

    def _make_confirmed_order(self, **kwargs):
        """Helper: create a CONFIRMED order."""
        o = self._make_order(status=OrderStatus.CONFIRMED, **kwargs)
        o.confirmed_at = timezone.now()
        o.save(update_fields=["confirmed_at"])
        return o
