# =============================================================================
# RestaurantFlow — Marketing Test Base
# Phase 18
#
# Shared fixture setup for all marketing tests.
#
# Fixture hierarchy:
#   Organization → Restaurant → Branch
#   Users: marketer, manager, approver, cashier, other_user
#   Permissions: all marketing + crm permissions
#   Roles: MARKETER_ROLE, APPROVER_ROLE, CASHIER_ROLE
#   CRM: Customer, CustomerSegment, CustomerTag, CustomerConsent, LoyaltyProgram
#   Menu: category, item
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from django.utils import timezone

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings


class MarketingTestBase(TestCase):
    """
    Base class providing a complete fixture stack for marketing tests.
    Uses setUpTestData for class-level shared state; individual tests should
    not mutate shared fixtures — use setUp() for mutable per-test state.
    """

    @classmethod
    def setUpTestData(cls):
        # ----------------------------------------------------------------
        # Organization / Restaurant / Branch
        # ----------------------------------------------------------------
        cls.org = Organization.objects.create(
            name="Mktg Test Org",
            slug="mktg-test-org",
            currency="INR",
            tax_id="GSTIN00001",
        )
        cls.restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Mktg Restaurant",
            slug="mktg-restaurant",
            code="MR01",
        )
        try:
            RestaurantSettings.objects.create(
                restaurant=cls.restaurant,
                currency="INR",
                tax_enabled=True,
                default_tax_rate=Decimal("5.00"),
                receipt_header="",
                receipt_footer="",
            )
        except Exception:
            pass

        cls.branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Main Branch",
            code="MB01",
            address="1 Test St",
            city="TestCity",
            state="TS",
            postal_code="000001",
            phone="9000000000",
        )
        try:
            BranchSettings.objects.create(branch=cls.branch)
        except Exception:
            pass

        cls.other_branch = Branch.objects.create(
            restaurant=cls.restaurant,
            name="Other Branch",
            code="OB01",
        )
        cls.other_restaurant = Restaurant.objects.create(
            organization=cls.org,
            name="Other Restaurant",
            slug="other-restaurant",
            code="OR01",
        )

        # ----------------------------------------------------------------
        # Users
        # ----------------------------------------------------------------
        cls.marketer = User.objects.create_user(
            email="marketer@test.com", password="pass123",
            first_name="Mark", last_name="Eter",
        )
        cls.approver = User.objects.create_user(
            email="approver@test.com", password="pass123",
            first_name="App", last_name="Rover",
        )
        cls.cashier = User.objects.create_user(
            email="cashier@test.com", password="pass123",
            first_name="Cash", last_name="Ier",
        )
        cls.other_user = User.objects.create_user(
            email="other@test.com", password="pass123",
            first_name="Other", last_name="User",
        )

        # ----------------------------------------------------------------
        # Permissions
        # ----------------------------------------------------------------
        perm_defs = [
            # Marketing
            ("marketing.dashboard.view",  "View Marketing Dashboard", "marketing", "dashboard.view"),
            ("marketing.campaign.view",   "View Campaigns",           "marketing", "campaign.view"),
            ("marketing.campaign.create", "Create Campaigns",         "marketing", "campaign.create"),
            ("marketing.campaign.update", "Update Campaigns",         "marketing", "campaign.update"),
            ("marketing.campaign.submit", "Submit Campaigns",         "marketing", "campaign.submit"),
            ("marketing.campaign.approve","Approve Campaigns",        "marketing", "campaign.approve"),
            ("marketing.campaign.reject", "Reject Campaigns",         "marketing", "campaign.reject"),
            ("marketing.campaign.schedule","Schedule Campaigns",      "marketing", "campaign.schedule"),
            ("marketing.campaign.pause",  "Pause Campaigns",          "marketing", "campaign.pause"),
            ("marketing.campaign.resume", "Resume Campaigns",         "marketing", "campaign.resume"),
            ("marketing.campaign.cancel", "Cancel Campaigns",         "marketing", "campaign.cancel"),
            ("marketing.audience.view",   "View Audiences",           "marketing", "audience.view"),
            ("marketing.audience.manage", "Manage Audiences",         "marketing", "audience.manage"),
            ("marketing.promotion.view",  "View Promotions",          "marketing", "promotion.view"),
            ("marketing.promotion.create","Create Promotions",        "marketing", "promotion.create"),
            ("marketing.promotion.update","Update Promotions",        "marketing", "promotion.update"),
            ("marketing.promotion.activate","Activate Promotions",    "marketing", "promotion.activate"),
            ("marketing.promotion.deactivate","Deactivate Promotions","marketing", "promotion.deactivate"),
            ("marketing.promotion.apply", "Apply Promotions",         "marketing", "promotion.apply"),
            ("marketing.analytics.view",  "View Analytics",           "marketing", "analytics.view"),
            ("marketing.settings.view",   "View Settings",            "marketing", "settings.view"),
            ("marketing.settings.manage", "Manage Settings",          "marketing", "settings.manage"),
            # CRM (needed by some marketing tests)
            ("customer.view",             "View Customers",           "customer",  "view"),
            ("customer.consent.view",     "View Consents",            "customer",  "consent.view"),
            ("loyalty.earn",              "Earn Points",              "loyalty",   "earn"),
        ]
        cls.perms = {}
        for code, name, module, action in perm_defs:
            p, _ = Permission.objects.get_or_create(
                code=code,
                defaults={"name": name, "module": module, "action": action},
            )
            cls.perms[code] = p

        # ----------------------------------------------------------------
        # Roles
        # ----------------------------------------------------------------
        cls.marketer_role = Role.objects.create(
            name="Marketer Test", code="MARKETER_TEST", scope=Role.SCOPE_RESTAURANT,
        )
        marketer_codes = [
            "marketing.dashboard.view",
            "marketing.campaign.view", "marketing.campaign.create",
            "marketing.campaign.update", "marketing.campaign.submit",
            "marketing.campaign.schedule", "marketing.campaign.pause",
            "marketing.campaign.resume", "marketing.campaign.cancel",
            "marketing.audience.view", "marketing.audience.manage",
            "marketing.promotion.view", "marketing.promotion.create",
            "marketing.promotion.update", "marketing.promotion.activate",
            "marketing.promotion.deactivate", "marketing.promotion.apply",
            "marketing.analytics.view",
            "marketing.settings.view",
        ]
        cls.marketer_role.permissions.set([cls.perms[c] for c in marketer_codes if c in cls.perms])

        cls.approver_role = Role.objects.create(
            name="Approver Test", code="APPROVER_TEST", scope=Role.SCOPE_RESTAURANT,
        )
        cls.approver_role.permissions.set([
            cls.perms.get("marketing.campaign.view"),
            cls.perms.get("marketing.campaign.approve"),
            cls.perms.get("marketing.campaign.reject"),
            cls.perms.get("marketing.promotion.view"),
        ])

        cls.cashier_role = Role.objects.create(
            name="Cashier Mktg Test", code="CASHIER_MKTG_TEST", scope=Role.SCOPE_BRANCH,
        )
        cls.cashier_role.permissions.set([
            cls.perms.get("marketing.promotion.view"),
            cls.perms.get("marketing.promotion.apply"),
        ])

        # ----------------------------------------------------------------
        # Role assignments
        # ----------------------------------------------------------------
        UserRoleAssignment.objects.create(
            user=cls.marketer, role=cls.marketer_role,
            organization=cls.org, restaurant=cls.restaurant,
        )
        UserRoleAssignment.objects.create(
            user=cls.approver, role=cls.approver_role,
            organization=cls.org, restaurant=cls.restaurant,
        )
        UserRoleAssignment.objects.create(
            user=cls.cashier, role=cls.cashier_role,
            organization=cls.org, restaurant=cls.restaurant, branch=cls.branch,
        )

        # ----------------------------------------------------------------
        # CRM: Customer + Segment + Tag + Consent + LoyaltyProgram
        # ----------------------------------------------------------------
        from crm.models import (
            Customer, CustomerSegment, CustomerSegmentAssignment,
            CustomerTag, CustomerTagAssignment,
            CustomerConsent, LoyaltyProgram, LoyaltyAccount,
        )
        from crm.constants import CONSENT_GRANTED, CONSENT_MARKETING_EMAIL

        cls.customer = Customer.objects.create(
            company=cls.org,
            restaurant=cls.restaurant,
            customer_number="CUS-000001",
            first_name="Alice",
            last_name="Test",
            email="alice@test.com",
            phone="+911234567890",
            is_active=True,
            is_blocked=False,
            total_orders=3,
            lifetime_spend=Decimal("1500.00"),
        )
        cls.customer2 = Customer.objects.create(
            company=cls.org,
            restaurant=cls.restaurant,
            customer_number="CUS-000002",
            first_name="Bob",
            last_name="Test",
            email="bob@test.com",
            is_active=True,
            is_blocked=False,
            total_orders=0,
        )
        cls.blocked_customer = Customer.objects.create(
            company=cls.org,
            restaurant=cls.restaurant,
            customer_number="CUS-000003",
            first_name="Blocked",
            last_name="User",
            is_active=True,
            is_blocked=True,
        )

        # Marketing email consent for customer
        cls.email_consent = CustomerConsent.objects.create(
            customer=cls.customer,
            consent_type=CONSENT_MARKETING_EMAIL,
            status=CONSENT_GRANTED,
            source="CUSTOMER",
        )

        # Segment + assignment
        cls.vip_segment = CustomerSegment.objects.create(
            restaurant=cls.restaurant,
            name="VIP Customers",
            code="VIP",
            criteria={"min_lifetime_spend": 1000},
        )
        cls.segment_assignment = CustomerSegmentAssignment.objects.create(
            customer=cls.customer,
            segment=cls.vip_segment,
            is_active=True,
            evaluation_snapshot={"lifetime_spend": "1500.00"},
        )

        # Tag + assignment
        cls.frequent_tag = CustomerTag.objects.create(
            restaurant=cls.restaurant,
            name="Frequent",
            code="FREQUENT",
        )
        cls.tag_assignment = CustomerTagAssignment.objects.create(
            customer=cls.customer,
            tag=cls.frequent_tag,
        )

        # Loyalty program
        cls.loyalty_program = LoyaltyProgram.objects.create(
            restaurant=cls.restaurant,
            name="Test Loyalty",
            is_active=True,
            points_per_currency_unit=Decimal("1.0000"),
            minimum_redemption_points=100,
        )

        # ----------------------------------------------------------------
        # Menu: Category + Item
        # ----------------------------------------------------------------
        from menu.models import Category, MenuItem

        cls.category = Category.objects.create(
            restaurant=cls.restaurant,
            name="Main Course",
            slug="main-course",
        )
        cls.menu_item = MenuItem.objects.create(
            restaurant=cls.restaurant,
            category=cls.category,
            name="Test Biryani",
            slug="test-biryani",
            is_active=True,
        )
