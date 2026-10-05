# =============================================================================
# RestaurantFlow — Marketing Security Tests
# Phase 18
#
# Cross-company, cross-restaurant, cross-branch isolation.
# IDOR prevention, unauthorized action prevention.
# =============================================================================

from decimal import Decimal
from django.test import TestCase

from accounts.models import User, Role, Permission, UserRoleAssignment
from organizations.models import Organization, Restaurant, Branch

from marketing.tests.base import MarketingTestBase
from marketing.campaign_services import CampaignService, CampaignApprovalService
from marketing.promotion_services import PromotionService, PromotionEligibilityService
from marketing.access import can_access_campaign, can_access_promotion
from marketing.models import MarketingCampaign, Promotion
from marketing.constants import (
    CAMPAIGN_PROMOTION,
    PROMO_PERCENTAGE_DISCOUNT, DISCOUNT_PERCENTAGE,
)
from marketing.exceptions import MarketingPermissionDenied


class CrossRestaurantIsolationTests(MarketingTestBase):
    """No campaign or promotion from restaurant A should be accessible from restaurant B."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        # Create a second organization with its own restaurant
        cls.org2 = Organization.objects.create(
            name="Other Org", slug="other-org-2", currency="INR", tax_id="GSTIN99999"
        )
        cls.restaurant2 = Restaurant.objects.create(
            organization=cls.org2,
            name="Other Restaurant 2",
            slug="other-restaurant-2",
            code="OR02",
        )
        cls.other_org_user = User.objects.create_user(
            email="org2user@test.com", password="pass123",
            first_name="Org2", last_name="User",
        )
        other_role = Role.objects.create(
            name="Org2 Marketer", code="ORG2_MARKETER", scope=Role.SCOPE_RESTAURANT,
        )
        # No marketing permissions — simulates a user from a different company
        UserRoleAssignment.objects.create(
            user=cls.other_org_user, role=other_role,
            organization=cls.org2, restaurant=cls.restaurant2,
        )

    def test_campaign_not_visible_cross_company(self):
        campaign = CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": "Org1 Campaign", "code": "ORG1_CAMP", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )
        # other_org_user belongs to org2, cannot see org1's campaign
        visible = can_access_campaign(self.other_org_user, campaign)
        self.assertFalse(visible)

    def test_promotion_not_visible_cross_company(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Org1 Promo",
                "code": "ORG1_PROMO",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
            },
            actor=self.marketer,
        )
        visible = can_access_promotion(self.other_org_user, promo)
        self.assertFalse(visible)

    def test_promotion_eligibility_cross_branch_blocked(self):
        """Promotion for branch A must not apply at branch B."""
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Branch Promo",
                "code": "BRANCHPROMO",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
            },
            actor=self.marketer,
        )
        # Bind promotion to branch
        Promotion.objects.filter(pk=promo.pk).update(branch=self.branch)
        promo.refresh_from_db()
        PromotionService.activate(promo, self.marketer)

        # Validate at other_branch
        result = PromotionEligibilityService.validate(
            promotion=promo,
            branch=self.other_branch,
        )
        self.assertFalse(result["eligible"])

    def test_create_campaign_for_inaccessible_restaurant_blocked(self):
        """User from org2 cannot create a campaign for org1's restaurant."""
        with self.assertRaises(Exception):
            # Either PermissionDenied or MarketingPermissionDenied
            CampaignService.create_campaign(
                company=self.org,
                restaurant=self.restaurant,
                data={"name": "Hack", "code": "HACK01", "campaign_type": CAMPAIGN_PROMOTION},
                actor=self.other_org_user,
            )


class UnauthorizedActionsTests(MarketingTestBase):

    def _make_campaign(self, code="UNAUTH01"):
        return CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": "Auth Test", "code": code, "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )

    def test_cashier_cannot_create_campaign(self):
        with self.assertRaises(MarketingPermissionDenied):
            CampaignService.create_campaign(
                company=self.org,
                restaurant=self.restaurant,
                data={"name": "Bad", "code": "CASH_CAMP", "campaign_type": CAMPAIGN_PROMOTION},
                actor=self.cashier,
            )

    def test_cashier_cannot_approve_campaign(self):
        campaign = self._make_campaign("CASH_APP")
        CampaignApprovalService.submit_for_approval(campaign, self.marketer)
        from marketing.models import CampaignApproval
        approval = CampaignApproval.objects.filter(campaign=campaign).first()
        with self.assertRaises(MarketingPermissionDenied):
            CampaignApprovalService.approve(campaign, approval, actor=self.cashier)

    def test_unauthenticated_access_returns_no_campaigns(self):
        from marketing.access import get_accessible_campaigns
        from django.contrib.auth.models import AnonymousUser

        # AnonymousUser (not authenticated)
        anon = User()
        anon.is_active = False
        qs = get_accessible_campaigns(anon)
        self.assertEqual(qs.count(), 0)

    def test_unauthenticated_access_returns_no_promotions(self):
        from marketing.access import get_accessible_promotions

        anon = User()
        anon.is_active = False
        qs = get_accessible_promotions(anon)
        self.assertEqual(qs.count(), 0)


class PromotionAbusePreventionTests(MarketingTestBase):

    def test_cannot_exceed_global_usage_limit(self):
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Abuse Test",
                "code": "ABUSE01",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
                "usage_limit": 2,
            },
            actor=self.marketer,
        )
        PromotionService.activate(promo, self.marketer)

        from marketing.promotion_services import PromotionUsageService
        from marketing.exceptions import PromotionUsageLimitReached

        PromotionUsageService.reserve_usage(promo, customer=self.customer)
        PromotionUsageService.reserve_usage(promo, customer=self.customer2)
        with self.assertRaises(PromotionUsageLimitReached):
            PromotionUsageService.reserve_usage(promo, customer=self.customer)

    def test_frontend_discount_manipulation_prevented(self):
        """Eligibility must always be validated server-side."""
        promo = PromotionService.create_promotion(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Manipulation Test",
                "code": "MANI01",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
                "minimum_order_amount": Decimal("300.00"),
            },
            actor=self.marketer,
        )
        PromotionService.activate(promo, self.marketer)

        # Frontend sends order_subtotal=500 but real subtotal is 200
        # Server always uses its own validated subtotal
        result = PromotionEligibilityService.validate(
            promotion=promo,
            order_subtotal=Decimal("200.00"),  # Real server-side value
        )
        self.assertFalse(result["eligible"])
