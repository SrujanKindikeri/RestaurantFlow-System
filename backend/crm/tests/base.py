# =============================================================================
# RestaurantFlow — CRM Test Base
# Phase 17
#
# Shared fixtures and helpers for all CRM tests.
# Follows the pattern established by billing/tests/base.py.
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings


class CRMTestBase(TestCase):
    """
    Base test case providing a fully wired-up multi-tenant fixture:
        org → restaurant → branch
        superuser, cashier_user, kitchen_user (no CRM perms)

    Subclasses add their own model instances as needed.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        # ---------------------------------------------------------------
        # Organization hierarchy
        # ---------------------------------------------------------------
        cls.org = Organization.objects.create(
            name="Test Corp",
            slug="test-corp",
            currency="INR",
            timezone="Asia/Kolkata",
        )
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Test Restaurant",
            slug="test-restaurant",
            code="TR-001",
        )
        RestaurantSettings.objects.get_or_create(
            restaurant=cls.restaurant,
            defaults={"currency": "INR", "order_prefix": "ORD"},
        )
        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Test Branch",
            code="TB-001",
        )
        BranchSettings.objects.get_or_create(branch=cls.branch)

        # Second restaurant for cross-restaurant isolation tests
        cls.other_restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Other Restaurant",
            slug="other-restaurant",
            code="OR-001",
        )
        RestaurantSettings.objects.get_or_create(
            restaurant=cls.other_restaurant,
            defaults={"currency": "INR", "order_prefix": "ORD"},
        )
        cls.other_branch = Branch.objects.create(
            restaurant=cls.other_restaurant,
            name="Other Branch",
            code="OB-001",
        )
        BranchSettings.objects.get_or_create(branch=cls.other_branch)

        # ---------------------------------------------------------------
        # Roles
        # ---------------------------------------------------------------
        cls.cashier_role = Role.objects.get_or_create(
            code="CASHIER",
            defaults={
                "name": "Cashier",
                "scope": Role.SCOPE_BRANCH,
            },
        )[0]
        cls.manager_role = Role.objects.get_or_create(
            code="RESTAURANT_MANAGER",
            defaults={
                "name": "Restaurant Manager",
                "scope": Role.SCOPE_BRANCH,
            },
        )[0]

        # ---------------------------------------------------------------
        # CRM Permissions
        # ---------------------------------------------------------------
        from crm.constants import ALL_CRM_PERMISSIONS
        for code, name, module, action in ALL_CRM_PERMISSIONS:
            perm, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "module": module, "action": action},
            )
            cls.manager_role.permissions.add(perm)
            # Cashier gets limited CRM permissions
            if code in ("customer.view", "customer.create", "customer.link",
                        "feedback.create", "loyalty.view", "reward.view"):
                cls.cashier_role.permissions.add(perm)

        # ---------------------------------------------------------------
        # Users
        # ---------------------------------------------------------------
        cls.superuser = User.objects.create_superuser(
            email="superuser@test.com",
            password="testpass123",
            first_name="Super",
            last_name="User",
        )

        cls.manager_user = User.objects.create_user(
            email="manager@test.com",
            password="testpass123",
            first_name="Manager",
            last_name="User",
        )
        UserRoleAssignment.objects.create(
            user=cls.manager_user,
            role=cls.manager_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )

        cls.cashier_user = User.objects.create_user(
            email="cashier@test.com",
            password="testpass123",
            first_name="Cashier",
            last_name="User",
        )
        UserRoleAssignment.objects.create(
            user=cls.cashier_user,
            role=cls.cashier_role,
            organization=cls.org,
            restaurant=cls.restaurant,
            branch=cls.branch,
        )

        cls.no_crm_user = User.objects.create_user(
            email="nocrmuser@test.com",
            password="testpass123",
            first_name="NoCRM",
            last_name="User",
        )

    def get_token(self, user):
        """Return a JWT access token for the given user."""
        from rest_framework_simplejwt.tokens import AccessToken
        return str(AccessToken.for_user(user))

    def auth_header(self, user):
        return {"HTTP_AUTHORIZATION": f"Bearer {self.get_token(user)}"}

    def make_customer(self, restaurant=None, phone="", email="", first_name="Test"):
        """Create a Customer for testing."""
        from crm.customer_services import CustomerService
        restaurant = restaurant or self.restaurant
        return CustomerService.create_customer(
            restaurant=restaurant,
            data={
                "first_name": first_name,
                "last_name": "Customer",
                "phone": phone,
                "email": email,
            },
            actor=self.manager_user,
        )

    def make_loyalty_program(self, restaurant=None, points_per_unit="1.0000"):
        """Create a LoyaltyProgram for testing."""
        from crm.models import LoyaltyProgram
        restaurant = restaurant or self.restaurant
        return LoyaltyProgram.objects.create(
            restaurant=restaurant,
            name="Test Loyalty",
            is_active=True,
            points_per_currency_unit=Decimal(points_per_unit),
            minimum_redemption_points=100,
        )

    def make_reward(self, restaurant=None, points_required=100):
        """Create a LoyaltyReward for testing."""
        from crm.models import LoyaltyReward
        return LoyaltyReward.objects.create(
            restaurant=restaurant or self.restaurant,
            name="Test Reward",
            reward_type="DISCOUNT",
            points_required=points_required,
            reward_value=Decimal("50.00"),
            is_active=True,
        )
