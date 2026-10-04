# =============================================================================
# RestaurantFlow — Financials Test Base
# Phase 12
#
# Provides a reusable test fixture factory that creates a minimal but complete
# object graph (Organization → Restaurant → Branch → Users → Roles →
# ExpenseCategory) so individual test modules don't repeat boilerplate.
# =============================================================================

from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient


class FinancialTestBase(TestCase):
    """
    Base class that sets up a complete organization hierarchy and a set of
    users covering the roles needed for financial operation tests.

    Subclass and call super().setUp() to get:

        self.org          — Organization
        self.restaurant   — Restaurant (under org)
        self.branch       — Branch (under restaurant)
        self.other_restaurant — a second restaurant (isolation tests)

        self.owner        — RESTAURANT_OWNER for self.restaurant
        self.manager      — RESTAURANT_MANAGER for self.restaurant
        self.accountant   — ACCOUNTANT for self.restaurant
        self.cashier      — CASHIER (no financial approvals)
        self.other_user   — user scoped to self.other_restaurant

        self.category     — ExpenseCategory for self.restaurant
        self.other_category — category for self.other_restaurant

        self.owner_client, self.manager_client, self.accountant_client,
        self.cashier_client, self.other_client — pre-authed APIClient instances
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls._build_fixture()

    @classmethod
    def _build_fixture(cls):
        from organizations.models import Organization, Restaurant, Branch
        from accounts.models import User, Role, Permission, UserRoleAssignment
        from financials.models import ExpenseCategory
        from financials.permissions import ALL_FINANCIAL_PERMISSIONS

        # ------------------------------------------------------------------ #
        # Organization / Restaurant / Branch                                  #
        # ------------------------------------------------------------------ #
        cls.org = Organization.objects.create(
            name="Test Corp",
            slug="test-corp",
        )
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Main Restaurant",
            slug="main-restaurant",
            code="MAIN01",
        )
        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Main Branch",
            code="MB01",
        )
        cls.other_restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Other Restaurant",
            slug="other-restaurant",
            code="OTHER01",
        )
        cls.other_branch = Branch.objects.create(
            restaurant=cls.other_restaurant,
            name="Other Branch",
            code="OB01",
        )

        # ------------------------------------------------------------------ #
        # Permissions — register all financial permission codes               #
        # ------------------------------------------------------------------ #
        for code, module, action, name in ALL_FINANCIAL_PERMISSIONS:
            Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "module": module, "action": action},
            )

        # ------------------------------------------------------------------ #
        # Roles                                                                #
        # ------------------------------------------------------------------ #
        def _make_role(code, scope, perms=None):
            role, _ = Role.objects.get_or_create(
                code=code,
                defaults={"name": code.replace("_", " ").title(), "scope": scope},
            )
            if perms:
                perm_objs = Permission.objects.filter(code__in=perms)
                role.permissions.set(perm_objs)
            return role

        # Owner — full financial access
        owner_perms = [p[0] for p in ALL_FINANCIAL_PERMISSIONS]
        cls.owner_role = _make_role(
            Role.CODE_RESTAURANT_OWNER, Role.SCOPE_RESTAURANT, owner_perms
        )

        # Manager — can create/submit expenses; no approve
        manager_perms = [
            "expense.view", "expense.create", "expense.update",
            "expense.submit", "expense.cancel",
            "expense.category.view",
            "expense.attachment.view", "expense.attachment.create",
            "expense.correction.request",
            "recurring_expense.view", "recurring_expense.create",
            "supplier_invoice.view", "supplier_invoice.create",
            "supplier_invoice.submit",
            "payable.view",
            "financial.dashboard.view",
        ]
        cls.manager_role = _make_role(
            Role.CODE_RESTAURANT_MANAGER, Role.SCOPE_BRANCH, manager_perms
        )

        # Accountant — financial records + approval
        accountant_perms = [
            "expense.view", "expense.approve", "expense.reject",
            "expense.category.view",
            "expense.attachment.view",
            "expense.correction.approve", "expense.correction.reject",
            "recurring_expense.view",
            "supplier_invoice.view", "supplier_invoice.approve",
            "supplier_invoice.cancel",
            "payable.view", "payable.manage",
            "financial.dashboard.view",
        ]
        cls.accountant_role = _make_role(
            Role.CODE_ACCOUNTANT, Role.SCOPE_BRANCH, accountant_perms
        )

        # Cashier — no financial management
        cls.cashier_role = _make_role(Role.CODE_CASHIER, Role.SCOPE_BRANCH, [])

        # ------------------------------------------------------------------ #
        # Users                                                                #
        # ------------------------------------------------------------------ #
        def _make_user(email, role, org=None, rest=None, branch=None):
            user = User.objects.create_user(
                email=email, password="TestPass123!",
                first_name="Test", last_name="User",
            )
            UserRoleAssignment.objects.create(
                user=user, role=role,
                organization=org or cls.org,
                restaurant=rest,
                branch=branch,
            )
            return user

        cls.owner = _make_user(
            "owner@test.com", cls.owner_role,
            org=cls.org, rest=cls.restaurant,
        )
        cls.manager = _make_user(
            "manager@test.com", cls.manager_role,
            org=cls.org, rest=cls.restaurant, branch=cls.branch,
        )
        cls.accountant = _make_user(
            "accountant@test.com", cls.accountant_role,
            org=cls.org, rest=cls.restaurant, branch=cls.branch,
        )
        cls.cashier = _make_user(
            "cashier@test.com", cls.cashier_role,
            org=cls.org, rest=cls.restaurant, branch=cls.branch,
        )
        cls.other_user = _make_user(
            "other@test.com", cls.owner_role,
            org=cls.org, rest=cls.other_restaurant,
        )

        # ------------------------------------------------------------------ #
        # Expense Categories                                                   #
        # ------------------------------------------------------------------ #
        cls.category = ExpenseCategory.objects.create(
            restaurant=cls.restaurant,
            name="Rent",
            code="RENT",
        )
        cls.other_category = ExpenseCategory.objects.create(
            restaurant=cls.other_restaurant,
            name="Rent",
            code="RENT",
        )

    def setUp(self):
        super().setUp()
        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)

        self.manager_client = APIClient()
        self.manager_client.force_authenticate(user=self.manager)

        self.accountant_client = APIClient()
        self.accountant_client.force_authenticate(user=self.accountant)

        self.cashier_client = APIClient()
        self.cashier_client.force_authenticate(user=self.cashier)

        self.other_client = APIClient()
        self.other_client.force_authenticate(user=self.other_user)

        self.anon_client = APIClient()

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _create_expense(
        self,
        user=None,
        restaurant=None,
        category=None,
        title="Office Rent",
        amount=Decimal("5000.00"),
        tax_amount=Decimal("0.00"),
        status=None,
    ):
        from financials.services import ExpenseService
        from django.utils import timezone
        user = user or self.manager
        restaurant = restaurant or self.restaurant
        category = category or self.category
        expense = ExpenseService.create_expense(
            restaurant=restaurant,
            category=category,
            title=title,
            amount=amount,
            expense_date=timezone.now().date(),
            user=user,
            tax_amount=tax_amount,
        )
        if status == "SUBMITTED":
            expense = ExpenseService.submit_expense(expense, user)
        elif status == "APPROVED":
            expense = ExpenseService.submit_expense(expense, user)
            expense = ExpenseService.approve_expense(expense, self.accountant)
        elif status == "REJECTED":
            expense = ExpenseService.submit_expense(expense, user)
            expense = ExpenseService.reject_expense(expense, self.accountant, "Not valid.")
        elif status == "CANCELLED":
            expense = ExpenseService.cancel_expense(expense, user)
        return expense

    def _create_supplier_invoice(
        self,
        user=None,
        restaurant=None,
        subtotal=Decimal("10000.00"),
    ):
        from financials.services import SupplierInvoiceService
        from inventory.models import Supplier
        from django.utils import timezone
        user = user or self.owner
        restaurant = restaurant or self.restaurant
        supplier, _ = Supplier.objects.get_or_create(
            restaurant=restaurant,
            code="SUP001",
            defaults={"name": "Test Supplier"},
        )
        return SupplierInvoiceService.create_invoice(
            restaurant=restaurant,
            supplier=supplier,
            invoice_date=timezone.now().date(),
            user=user,
            subtotal=subtotal,
        )
