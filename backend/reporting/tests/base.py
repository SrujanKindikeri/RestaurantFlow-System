# =============================================================================
# RestaurantFlow — Reporting Test Base
# Phase 14
#
# Shared fixture stack for all reporting integration tests.
# Builds a complete two-restaurant / two-branch setup to test scope isolation.
#
# Hierarchy:
#   Org A → Restaurant A → Branch A1 (main), Branch A2 (secondary)
#   Org B → Restaurant B → Branch B1 (another org — for isolation tests)
#
# Users:
#   manager_a     — MANAGER scope for Branch A1
#   owner_a       — OWNER scope for Restaurant A (sees A1 + A2)
#   manager_b     — MANAGER scope for Branch B1 (different org — should NOT see Org A data)
#   superuser     — sees everything
#
# Financial data (created per-test, not in setUpTestData, to avoid mutation issues):
#   Finalized bills, COMPLETED payments, CONFIRMED orders — all for Branch A1
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
from menu.models import Category, MenuItem, MenuItemPrice, MenuItemBranch, TaxRate
from counters.models import Counter, CounterSession, SessionStatus, CounterStatus
from orders.models import Order, OrderItem, OrderStatus, OrderType


class ReportingTestBase(TestCase):
    """
    Base class for all Phase 14 reporting tests.

    setUpTestData is CLASS-LEVEL and shared — do NOT mutate these fixtures.
    Create transactional data (Bills, Payments, etc.) inside individual test
    methods using the _make_* helpers.
    """

    @classmethod
    def setUpTestData(cls):
        # ---------------------------------------------------------------
        # Organisation A (primary)
        # ---------------------------------------------------------------
        cls.org_a = Organization.objects.create(
            name="Org A", slug="org-a", currency="INR", timezone="Asia/Kolkata"
        )
        cls.restaurant_a = Restaurant.objects.create(
            organization=cls.org_a, name="Restaurant A",
            slug="restaurant-a", code="RA",
        )
        RestaurantSettings.objects.create(restaurant=cls.restaurant_a)

        cls.branch_a1 = Branch.objects.create(
            restaurant=cls.restaurant_a, name="Branch A1", code="A1"
        )
        cls.branch_a2 = Branch.objects.create(
            restaurant=cls.restaurant_a, name="Branch A2", code="A2"
        )
        BranchSettings.objects.create(branch=cls.branch_a1)
        BranchSettings.objects.create(branch=cls.branch_a2)

        # ---------------------------------------------------------------
        # Organisation B (isolation)
        # ---------------------------------------------------------------
        cls.org_b = Organization.objects.create(
            name="Org B", slug="org-b", currency="INR"
        )
        cls.restaurant_b = Restaurant.objects.create(
            organization=cls.org_b, name="Restaurant B",
            slug="restaurant-b", code="RB",
        )
        RestaurantSettings.objects.create(restaurant=cls.restaurant_b)
        cls.branch_b1 = Branch.objects.create(
            restaurant=cls.restaurant_b, name="Branch B1", code="B1"
        )
        BranchSettings.objects.create(branch=cls.branch_b1)

        # ---------------------------------------------------------------
        # Permissions
        # ---------------------------------------------------------------
        def _perm(code, module="reporting", action="view"):
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": code, "description": "", "module": module, "action": action},
            )
            return p

        from reporting.constants import ALL_REPORTING_PERMISSIONS
        cls.reporting_perms = {}
        for code, name, module, action in ALL_REPORTING_PERMISSIONS:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "description": "", "module": module, "action": action},
            )
            cls.reporting_perms[code] = p

        # ---------------------------------------------------------------
        # Roles
        # ---------------------------------------------------------------
        cls.manager_role = Role.objects.create(
            name="Report Manager", code="REPORT_MANAGER", scope=Role.SCOPE_BRANCH,
        )
        cls.manager_role.permissions.set(list(cls.reporting_perms.values()))

        cls.owner_role = Role.objects.create(
            name="Report Owner", code="REPORT_OWNER", scope=Role.SCOPE_RESTAURANT,
        )
        cls.owner_role.permissions.set(list(cls.reporting_perms.values()))

        # ---------------------------------------------------------------
        # Users
        # ---------------------------------------------------------------
        cls.manager_a = User.objects.create_user(
            email="manager_a@test.com", password="pass123",
            first_name="Manager", last_name="A",
        )
        cls.owner_a = User.objects.create_user(
            email="owner_a@test.com", password="pass123",
            first_name="Owner", last_name="A",
        )
        cls.manager_b = User.objects.create_user(
            email="manager_b@test.com", password="pass123",
            first_name="Manager", last_name="B",
        )
        cls.superuser = User.objects.create_superuser(
            email="super@test.com", password="pass123",
        )

        # Role assignments
        UserRoleAssignment.objects.create(
            user=cls.manager_a, role=cls.manager_role,
            organization=cls.org_a, restaurant=cls.restaurant_a, branch=cls.branch_a1,
        )
        UserRoleAssignment.objects.create(
            user=cls.owner_a, role=cls.owner_role,
            organization=cls.org_a, restaurant=cls.restaurant_a,
        )
        UserRoleAssignment.objects.create(
            user=cls.manager_b, role=cls.manager_role,
            organization=cls.org_b, restaurant=cls.restaurant_b, branch=cls.branch_b1,
        )

        # ---------------------------------------------------------------
        # Menu for Branch A1
        # ---------------------------------------------------------------
        cls.tax_gst5 = TaxRate.objects.create(
            restaurant=cls.restaurant_a, name="GST 5%", code="GST_5",
            rate=Decimal("5.000"),
        )
        cls.category = Category.objects.create(
            restaurant=cls.restaurant_a, name="Main Course", slug="main-course",
        )
        cls.item_biryani = MenuItem.objects.create(
            restaurant=cls.restaurant_a, category=cls.category,
            name="Chicken Biryani", slug="chicken-biryani", sku="BIR-001",
            tax_rate=cls.tax_gst5,
        )
        cls.item_fries = MenuItem.objects.create(
            restaurant=cls.restaurant_a, category=cls.category,
            name="French Fries", slug="french-fries", sku="FRY-001",
        )
        for item in [cls.item_biryani, cls.item_fries]:
            MenuItemBranch.objects.create(
                menu_item=item, branch=cls.branch_a1, is_available=True
            )
            MenuItemPrice.objects.create(
                menu_item=item, branch=cls.branch_a1,
                price=Decimal("250.00"), is_active=True,
            )

        # ---------------------------------------------------------------
        # Counter for Branch A1
        # ---------------------------------------------------------------
        cls.counter = Counter.objects.create(
            branch=cls.branch_a1, name="Counter 01", code="C01",
            status=CounterStatus.ACTIVE,
        )
        cls.counter_session = CounterSession.objects.create(
            counter=cls.counter, opened_by=cls.manager_a,
            opening_cash=Decimal("1000.00"), status=SessionStatus.OPEN,
        )

    # -------------------------------------------------------------------
    # Helpers — create finalized bills and completed payments per test
    # -------------------------------------------------------------------

    def _make_order(self, branch=None, status=OrderStatus.CONFIRMED,
                    order_type=OrderType.COUNTER, user=None):
        branch = branch or self.branch_a1
        user = user or self.manager_a
        ts = timezone.now().strftime("%Y%m%d%H%M%S%f")
        order = Order.objects.create(
            branch=branch,
            order_number=f"ORD-{ts}",
            order_type=order_type,
            counter=self.counter if branch == self.branch_a1 else None,
            counter_session=self.counter_session if branch == self.branch_a1 else None,
            created_by=user,
            status=status,
            confirmed_at=timezone.now() if status == OrderStatus.CONFIRMED else None,
        )
        OrderItem.objects.create(
            order=order,
            menu_item=self.item_biryani,
            item_name_snapshot="Chicken Biryani",
            sku_snapshot="BIR-001",
            unit_price_snapshot=Decimal("250.00"),
            tax_rate_snapshot=Decimal("5.000"),
            tax_code_snapshot="GST_5",
            quantity=Decimal("2.000"),
        )
        return order

    def _make_finalized_bill(self, order=None, grand_total=None,
                              discount_amount=None, branch=None,
                              finalized_at=None):
        from billing.models import Bill, BillItem, BillStatus
        from django.utils import timezone as tz
        order = order or self._make_order(branch=branch)
        gt = grand_total or Decimal("525.00")
        da = discount_amount or Decimal("0.00")
        ts = tz.now().strftime("%Y%m%d%H%M%S%f")
        bill = Bill.objects.create(
            order=order,
            branch=order.branch,
            bill_number=f"B-{ts}",
            status=BillStatus.FINALIZED,
            subtotal=Decimal("500.00"),
            discount_amount=da,
            taxable_amount=Decimal("500.00") - da,
            tax_amount=Decimal("25.00"),
            rounding_amount=Decimal("0.00"),
            grand_total=gt,
            created_by=self.manager_a,
            finalized_by=self.manager_a,
            finalized_at=finalized_at or tz.now(),
        )
        BillItem.objects.create(
            bill=bill,
            order_item=order.items.first(),
            menu_item=self.item_biryani,
            item_name_snapshot="Chicken Biryani",
            sku_snapshot="BIR-001",
            quantity=Decimal("2.000"),
            unit_price=Decimal("250.00"),
            gross_amount=Decimal("500.00"),
            discount_amount=Decimal("0.00"),
            taxable_amount=Decimal("500.00"),
            tax_rate=Decimal("5.000"),
            tax_code="GST_5",
            tax_amount=Decimal("25.00"),
            total_amount=Decimal("525.00"),
        )
        return bill

    def _make_draft_bill(self, order=None):
        from billing.models import Bill, BillStatus
        from django.utils import timezone as tz
        order = order or self._make_order()
        ts = tz.now().strftime("%Y%m%d%H%M%S%f")
        return Bill.objects.create(
            order=order,
            branch=order.branch,
            bill_number=f"DRAFT-{ts}",
            status=BillStatus.DRAFT,
            subtotal=Decimal("500.00"),
            grand_total=Decimal("525.00"),
            created_by=self.manager_a,
        )

    def _make_cancelled_bill(self, order=None):
        from billing.models import Bill, BillStatus
        from django.utils import timezone as tz
        order = order or self._make_order()
        ts = tz.now().strftime("%Y%m%d%H%M%S%f")
        return Bill.objects.create(
            order=order,
            branch=order.branch,
            bill_number=f"CANC-{ts}",
            status=BillStatus.CANCELLED,
            subtotal=Decimal("500.00"),
            grand_total=Decimal("525.00"),
            created_by=self.manager_a,
            cancelled_by=self.manager_a,
            cancelled_at=tz.now(),
        )

    def _make_payment(self, bill, amount=None, method="CASH", status="COMPLETED"):
        from payments.models import Payment, PaymentStatus
        from django.utils import timezone as tz
        ts = tz.now().strftime("%Y%m%d%H%M%S%f")
        return Payment.objects.create(
            bill=bill,
            branch=bill.branch,
            payment_number=f"PAY-{ts}",
            amount=amount or bill.grand_total,
            payment_method=method,
            status=status,
            initiated_by=self.manager_a,
            completed_by=self.manager_a if status == "COMPLETED" else None,
            completed_at=tz.now() if status == "COMPLETED" else None,
        )
