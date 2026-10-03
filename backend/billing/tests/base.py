# =============================================================================
# RestaurantFlow — Billing Test Base
# Phase 8
#
# Shared fixture setup for all billing integration tests.
# All test classes that need DB access should inherit from BillingTestBase.
#
# Fixture hierarchy:
#   Organization → Restaurant (with settings) → Branch (with settings)
#   Users: cashier, manager, owner, other_branch_user
#   Permissions: all billing permissions
#   Roles: CASHIER_ROLE (limited), MANAGER_ROLE (elevated), OWNER_ROLE
#   Tax rates: GST_5 (5%), ZERO_TAX (0%)
#   Menu: category, item_biryani (taxed), item_fries (zero tax)
#   Counter: counter_c01, counter_session
#   Confirmed order with 2 order items
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
from menu.models import Category, MenuItem, MenuItemPrice, MenuItemBranch, TaxRate
from orders.models import (
    Order, OrderItem, OrderStatus, OrderType,
    DiningTable, TableSession, TableSessionStatus,
)
from counters.models import Counter, CounterSession, SessionStatus, CounterStatus


class BillingTestBase(TestCase):
    """
    Base test class providing a full fixture stack for billing tests.

    setUpTestData runs ONCE per test class — expensive operations like
    user/org/menu setup are shared; individual tests must not mutate these.
    """

    @classmethod
    def setUpTestData(cls):
        # -----------------------------------------------------------------
        # Organization / Restaurant / Branch
        # -----------------------------------------------------------------
        cls.org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            currency="INR",
            tax_id="GSTIN12345",
        )
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Test Restaurant",
            slug="test-restaurant",
            code="TR01",
        )
        cls.r_settings = RestaurantSettings.objects.create(
            restaurant=cls.restaurant,
            currency="INR",
            tax_enabled=True,
            default_tax_rate=Decimal("5.00"),
            receipt_header="Welcome to Test Restaurant",
            receipt_footer="Thank you for visiting!",
        )
        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Main Branch",
            code="MB01",
            address="123 Main Street",
            city="Test City",
            state="Test State",
            postal_code="110001",
            phone="9999999999",
        )
        cls.b_settings = BranchSettings.objects.create(
            branch=cls.branch,
        )

        # Second branch (for isolation/IDOR tests)
        cls.other_branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Other Branch",
            code="OB01",
        )

        # -----------------------------------------------------------------
        # Users
        # -----------------------------------------------------------------
        cls.cashier = User.objects.create_user(
            email="cashier@test.com",
            password="pass123",
            first_name="Counter",
            last_name="Cashier",
        )
        cls.manager = User.objects.create_user(
            email="manager@test.com",
            password="pass123",
            first_name="Branch",
            last_name="Manager",
        )
        cls.owner = User.objects.create_user(
            email="owner@test.com",
            password="pass123",
            first_name="Restaurant",
            last_name="Owner",
        )
        cls.other_user = User.objects.create_user(
            email="other@test.com",
            password="pass123",
            first_name="Other",
            last_name="User",
        )

        # -----------------------------------------------------------------
        # Permissions
        # -----------------------------------------------------------------
        perm_data = [
            ("bill.view",                 "Billing", "View bills",                     "billing", "view"),
            ("bill.create",               "Billing", "Create bills",                   "billing", "create"),
            ("bill.finalize",             "Billing", "Finalize bills",                 "billing", "finalize"),
            ("bill.print",                "Billing", "Print/view receipt",             "billing", "print"),
            ("bill.cancel",               "Billing", "Cancel bills",                   "billing", "cancel"),
            ("bill.void",                 "Billing", "Void bills",                     "billing", "void"),
            ("discount.apply",            "Billing", "Apply discounts",                "billing", "discount_apply"),
            ("discount.apply_large",      "Billing", "Apply large discounts",          "billing", "discount_large"),
            ("discount.approve",          "Billing", "Approve discounts",              "billing", "discount_approve"),
            ("bill.correction.request",   "Billing", "Request bill corrections",       "billing", "correction_request"),
            ("bill.correction.approve",   "Billing", "Approve bill corrections",       "billing", "correction_approve"),
            ("tax.view",                  "Billing", "View tax configuration",         "billing", "tax_view"),
            # Order permissions needed by views
            ("order.view",                "Orders",  "View orders",                    "orders",  "view"),
            ("order.create",              "Orders",  "Create orders",                  "orders",  "create"),
            ("order.confirm",             "Orders",  "Confirm orders",                 "orders",  "confirm"),
            ("table.view",                "Orders",  "View tables",                    "orders",  "table_view"),
            ("table.session.open",        "Orders",  "Open table session",             "orders",  "table_session_open"),
            ("table.session.close",       "Orders",  "Close table session",            "orders",  "table_session_close"),
        ]
        cls.perms = {}
        for code, name, desc, module, action in perm_data:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": desc, "module": module, "action": action},
            )
            cls.perms[code] = p

        # -----------------------------------------------------------------
        # Roles
        # -----------------------------------------------------------------
        # Cashier: basic billing + limited discount
        cls.cashier_role = Role.objects.create(
            name="Cashier Test",
            code="CASHIER_TEST",
            scope=Role.SCOPE_BRANCH,
        )
        cashier_perm_codes = [
            "bill.view", "bill.create", "bill.finalize", "bill.print",
            "bill.cancel", "discount.apply",
            "bill.correction.request", "tax.view",
            "order.view", "order.create", "order.confirm",
            "table.view", "table.session.open", "table.session.close",
        ]
        cls.cashier_role.permissions.set([cls.perms[c] for c in cashier_perm_codes])

        # Manager: all billing + large discount + correction approval
        cls.manager_role = Role.objects.create(
            name="Manager Test",
            code="MANAGER_TEST",
            scope=Role.SCOPE_BRANCH,
        )
        cls.manager_role.permissions.set(list(cls.perms.values()))

        # Owner: restaurant scope
        cls.owner_role = Role.objects.create(
            name="Owner Test",
            code="OWNER_TEST",
            scope=Role.SCOPE_RESTAURANT,
        )
        cls.owner_role.permissions.set(list(cls.perms.values()))

        # -----------------------------------------------------------------
        # Role assignments
        # -----------------------------------------------------------------
        UserRoleAssignment.objects.create(
            user=cls.cashier,
            role=cls.cashier_role,
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
        UserRoleAssignment.objects.create(
            user=cls.owner,
            role=cls.owner_role,
            organization=cls.org,
            restaurant=cls.restaurant,
        )
        # other_user has NO role assignment for cls.branch

        # -----------------------------------------------------------------
        # Tax rates
        # -----------------------------------------------------------------
        cls.tax_gst5 = TaxRate.objects.create(
            restaurant=cls.restaurant,
            name="GST 5%",
            code="GST_5",
            rate=Decimal("5.000"),
        )
        cls.tax_zero = TaxRate.objects.create(
            restaurant=cls.restaurant,
            name="Zero Tax",
            code="ZERO_TAX",
            rate=Decimal("0.000"),
        )

        # -----------------------------------------------------------------
        # Menu
        # -----------------------------------------------------------------
        cls.category = Category.objects.create(
            restaurant=cls.restaurant,
            name="Main Course",
            slug="main-course",
        )
        cls.item_biryani = MenuItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.category,
            name="Chicken Biryani",
            slug="chicken-biryani",
            sku="BIRYA-001",
            tax_rate=cls.tax_gst5,
        )
        cls.item_fries = MenuItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.category,
            name="French Fries",
            slug="french-fries",
            sku="FRIES-001",
            tax_rate=cls.tax_zero,
        )
        MenuItemBranch.objects.create(
            menu_item=cls.item_biryani, branch=cls.branch, is_available=True
        )
        MenuItemBranch.objects.create(
            menu_item=cls.item_fries, branch=cls.branch, is_available=True
        )
        MenuItemPrice.objects.create(
            menu_item=cls.item_biryani, branch=cls.branch,
            price=Decimal("250.00"), is_active=True,
        )
        MenuItemPrice.objects.create(
            menu_item=cls.item_fries, branch=cls.branch,
            price=Decimal("120.00"), is_active=True,
        )

        # -----------------------------------------------------------------
        # Counter + Counter Session
        # -----------------------------------------------------------------
        cls.counter = Counter.objects.create(
            branch=cls.branch,
            name="Counter 01",
            code="C01",
            status=CounterStatus.ACTIVE,
        )
        cls.counter_session = CounterSession.objects.create(
            counter=cls.counter,
            opened_by=cls.cashier,
            opening_cash=Decimal("1000.00"),
            status=SessionStatus.OPEN,
        )

    # ------------------------------------------------------------------
    # Helper: build a confirmed COUNTER order (fresh each test)
    # ------------------------------------------------------------------
    def _make_confirmed_order(
        self,
        biryani_qty=Decimal("2.000"),
        fries_qty=Decimal("1.000"),
        order_type=OrderType.COUNTER,
    ):
        """
        Create and return a CONFIRMED order with two line items.
        Each call creates a unique order number to avoid collisions.
        """
        from django.utils import timezone as tz_mod
        from orders.models import OrderSequence

        # Generate a unique order number without relying on the full service
        ts = tz_mod.now().strftime("%Y%m%d%H%M%S%f")
        order_number = f"TEST-{ts}"

        order = Order.objects.create(
            branch=self.branch,
            order_number=order_number,
            order_type=order_type,
            counter=self.counter if order_type in (OrderType.COUNTER, OrderType.TAKEAWAY) else None,
            counter_session=self.counter_session if order_type in (OrderType.COUNTER, OrderType.TAKEAWAY) else None,
            created_by=self.cashier,
            status=OrderStatus.CONFIRMED,
            confirmed_at=timezone.now(),
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_biryani,
            item_name_snapshot="Chicken Biryani",
            sku_snapshot="BIRYA-001",
            unit_price_snapshot=Decimal("250.00"),
            tax_rate_snapshot=Decimal("5.000"),
            tax_code_snapshot="GST_5",
            quantity=biryani_qty,
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_fries,
            item_name_snapshot="French Fries",
            sku_snapshot="FRIES-001",
            unit_price_snapshot=Decimal("120.00"),
            tax_rate_snapshot=Decimal("0.000"),
            tax_code_snapshot="ZERO_TAX",
            quantity=fries_qty,
        )
        return order

    def _make_draft_order(self):
        from django.utils import timezone as tz_mod
        ts = tz_mod.now().strftime("%Y%m%d%H%M%S%f")
        return Order.objects.create(
            branch=self.branch,
            order_number=f"DRAFT-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.cashier,
            status=OrderStatus.DRAFT,
        )

    def _make_cancelled_order(self):
        from django.utils import timezone as tz_mod
        ts = tz_mod.now().strftime("%Y%m%d%H%M%S%f")
        return Order.objects.create(
            branch=self.branch,
            order_number=f"CANC-{ts}",
            order_type=OrderType.COUNTER,
            counter=self.counter,
            counter_session=self.counter_session,
            created_by=self.cashier,
            status=OrderStatus.CANCELLED,
            cancelled_at=timezone.now(),
        )
