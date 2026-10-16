# =============================================================================
# RestaurantFlow — Enterprise Test Base
# Phase 20
#
# Shared fixture setup for all enterprise integration tests.
# All test classes that need DB access should inherit from EnterpriseTestBase.
#
# Fixture hierarchy:
#   Organization → Restaurant (2x) → Branch (per restaurant, 2 branches each)
#   Users: company_head, restaurant_owner, branch_manager, cashier, other_org_user
#   Permissions: all enterprise permissions
#   Roles: COMPANY_HEAD, RESTAURANT_OWNER, BRANCH_MANAGER, CASHIER
#   Role assignments scoped correctly
#   Menu: category, menu_item_biryani
#   MenuItemBranch + MenuItemPrice for branch_a1
#   TaxRate: gst5
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
from menu.models import Category, MenuItem, MenuItemPrice, MenuItemBranch, TaxRate
from enterprise.constants import ALL_ENTERPRISE_PERMISSIONS


class EnterpriseTestBase(TestCase):
    """
    Base test class providing a full fixture stack for enterprise tests.

    setUpTestData runs ONCE per test class — do NOT mutate shared fixtures
    in individual tests. Create transient objects inside test methods instead.
    """

    @classmethod
    def setUpTestData(cls):
        # -----------------------------------------------------------------
        # Organization A (primary)
        # -----------------------------------------------------------------
        cls.org = Organization.objects.create(
            name="Test Corp",
            slug="test-corp",
            currency="INR",
            tax_id="GSTIN_TEST",
        )
        cls.restaurant_a = Restaurant.objects.create(
            organization=cls.org,
            name="Restaurant Alpha",
            slug="restaurant-alpha",
            code="RA01",
        )
        RestaurantSettings.objects.create(
            restaurant=cls.restaurant_a,
            currency="INR",
            tax_enabled=True,
            default_tax_rate=Decimal("5.00"),
        )
        cls.branch_a1 = Branch.objects.create(
            restaurant=cls.restaurant_a,
            name="Branch Alpha-1",
            code="A1",
            city="Mumbai",
        )
        cls.branch_a2 = Branch.objects.create(
            restaurant=cls.restaurant_a,
            name="Branch Alpha-2",
            code="A2",
            city="Pune",
        )
        BranchSettings.objects.create(branch=cls.branch_a1)
        BranchSettings.objects.create(branch=cls.branch_a2)

        # -----------------------------------------------------------------
        # Organization B (for cross-tenant isolation tests)
        # -----------------------------------------------------------------
        cls.org_b = Organization.objects.create(
            name="Other Corp",
            slug="other-corp",
            currency="INR",
        )
        cls.restaurant_b = Restaurant.objects.create(
            organization=cls.org_b,
            name="Restaurant Beta",
            slug="restaurant-beta",
            code="RB01",
        )
        cls.branch_b1 = Branch.objects.create(
            restaurant=cls.restaurant_b,
            name="Branch Beta-1",
            code="B1",
        )
        BranchSettings.objects.create(branch=cls.branch_b1)

        # -----------------------------------------------------------------
        # Permissions
        # -----------------------------------------------------------------
        cls.perms = {}
        for code, name, module, action in ALL_ENTERPRISE_PERMISSIONS:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "module": module, "action": action},
            )
            cls.perms[code] = p

        # -----------------------------------------------------------------
        # Roles
        # -----------------------------------------------------------------
        cls.role_company_head = Role.objects.create(
            name="Company Head Test",
            code="COMPANY_HEAD_TEST",
            scope=Role.SCOPE_ORGANIZATION,
        )
        cls.role_company_head.permissions.set(list(cls.perms.values()))

        cls.role_owner = Role.objects.create(
            name="Restaurant Owner Test",
            code="RESTAURANT_OWNER_TEST",
            scope=Role.SCOPE_RESTAURANT,
        )
        cls.role_owner.permissions.set(list(cls.perms.values()))

        cls.role_manager = Role.objects.create(
            name="Branch Manager Test",
            code="BRANCH_MANAGER_TEST",
            scope=Role.SCOPE_BRANCH,
        )
        cls.role_manager.permissions.set(list(cls.perms.values()))

        cls.role_cashier = Role.objects.create(
            name="Cashier Test",
            code="CASHIER_TEST",
            scope=Role.SCOPE_BRANCH,
        )
        # Cashier gets NO enterprise permissions

        # -----------------------------------------------------------------
        # Users
        # -----------------------------------------------------------------
        cls.company_head = User.objects.create_user(
            email="company_head@test.com",
            password="pass123",
            first_name="Company",
            last_name="Head",
        )
        cls.restaurant_owner = User.objects.create_user(
            email="owner@test.com",
            password="pass123",
            first_name="Restaurant",
            last_name="Owner",
        )
        cls.branch_manager = User.objects.create_user(
            email="manager@test.com",
            password="pass123",
            first_name="Branch",
            last_name="Manager",
        )
        cls.cashier = User.objects.create_user(
            email="cashier@test.com",
            password="pass123",
            first_name="Counter",
            last_name="Cashier",
        )
        cls.other_org_user = User.objects.create_user(
            email="other@org-b.com",
            password="pass123",
            first_name="Other",
            last_name="User",
        )

        # -----------------------------------------------------------------
        # Role assignments
        # -----------------------------------------------------------------
        UserRoleAssignment.objects.create(
            user=cls.company_head,
            role=cls.role_company_head,
            organization=cls.org,
        )
        UserRoleAssignment.objects.create(
            user=cls.restaurant_owner,
            role=cls.role_owner,
            organization=cls.org,
            restaurant=cls.restaurant_a,
        )
        UserRoleAssignment.objects.create(
            user=cls.branch_manager,
            role=cls.role_manager,
            organization=cls.org,
            restaurant=cls.restaurant_a,
            branch=cls.branch_a1,
        )
        UserRoleAssignment.objects.create(
            user=cls.cashier,
            role=cls.role_cashier,
            organization=cls.org,
            restaurant=cls.restaurant_a,
            branch=cls.branch_a1,
        )
        UserRoleAssignment.objects.create(
            user=cls.other_org_user,
            role=cls.role_owner,
            organization=cls.org_b,
            restaurant=cls.restaurant_b,
        )

        # -----------------------------------------------------------------
        # Menu
        # -----------------------------------------------------------------
        cls.tax_gst5 = TaxRate.objects.create(
            restaurant=cls.restaurant_a,
            name="GST 5%",
            code="GST_5",
            rate=Decimal("5.000"),
        )
        cls.category = Category.objects.create(
            restaurant=cls.restaurant_a,
            name="Main Course",
            slug="main-course",
        )
        cls.menu_item = MenuItem.objects.create(
            restaurant=cls.restaurant_a,
            category=cls.category,
            name="Chicken Biryani",
            slug="chicken-biryani",
            sku="CB-001",
            tax_rate=cls.tax_gst5,
        )
        MenuItemBranch.objects.create(
            menu_item=cls.menu_item,
            branch=cls.branch_a1,
            is_available=True,
        )
        MenuItemBranch.objects.create(
            menu_item=cls.menu_item,
            branch=cls.branch_a2,
            is_available=True,
        )
        MenuItemPrice.objects.create(
            menu_item=cls.menu_item,
            branch=cls.branch_a1,
            price=Decimal("250.00"),
            is_active=True,
        )
        MenuItemPrice.objects.create(
            menu_item=cls.menu_item,
            branch=cls.branch_a2,
            price=Decimal("270.00"),  # branch-specific override
            is_active=True,
        )
