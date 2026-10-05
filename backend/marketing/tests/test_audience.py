# =============================================================================
# RestaurantFlow — Audience Tests
# Phase 18
# =============================================================================

from decimal import Decimal
from django.utils import timezone

from marketing.tests.base import MarketingTestBase
from marketing.campaign_services import CampaignService
from marketing.audience_services import CampaignAudienceService
from marketing.models import MarketingCampaign, CampaignAudience, CampaignAudienceMember
from marketing.constants import (
    CAMPAIGN_PROMOTION,
    AUDIENCE_ALL_CUSTOMERS, AUDIENCE_VIP, AUDIENCE_NEW_CUSTOMERS,
    AUDIENCE_CUSTOM_SEGMENT, AUDIENCE_CUSTOM_TAG, AUDIENCE_CUSTOM_FILTER,
    MEMBER_ELIGIBLE, MEMBER_EXCLUDED,
)


class AudienceGenerationTests(MarketingTestBase):

    def _make_campaign(self, code="AUD_CAMP"):
        return CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": f"Campaign {code}", "code": code, "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )

    def test_all_customers_audience(self):
        campaign = self._make_campaign("AUD_ALL")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=AUDIENCE_ALL_CUSTOMERS,
            criteria={},
            actor=self.marketer,
        )
        count = CampaignAudienceService.generate_audience_members(campaign, audience)
        # Should include active, non-blocked customers
        self.assertGreaterEqual(count, 2)  # customer + customer2

    def test_blocked_customer_excluded(self):
        campaign = self._make_campaign("AUD_BLOCK")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=AUDIENCE_ALL_CUSTOMERS,
            criteria={},
            actor=self.marketer,
        )
        CampaignAudienceService.generate_audience_members(campaign, audience)

        # blocked_customer should be EXCLUDED
        member = CampaignAudienceMember.objects.filter(
            campaign=campaign, customer=self.blocked_customer
        ).first()
        if member:
            self.assertEqual(member.status, MEMBER_EXCLUDED)

    def test_vip_segment_audience(self):
        campaign = self._make_campaign("AUD_VIP")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=AUDIENCE_VIP,
            criteria={},
            actor=self.marketer,
        )
        count = CampaignAudienceService.generate_audience_members(campaign, audience)
        # Only customer1 has VIP segment
        self.assertEqual(count, 1)
        member = CampaignAudienceMember.objects.filter(
            campaign=campaign, customer=self.customer
        ).first()
        self.assertIsNotNone(member)
        self.assertEqual(member.status, MEMBER_ELIGIBLE)

    def test_new_customers_audience(self):
        campaign = self._make_campaign("AUD_NEW")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=AUDIENCE_NEW_CUSTOMERS,
            criteria={},
            actor=self.marketer,
        )
        count = CampaignAudienceService.generate_audience_members(campaign, audience)
        # customer2 has 0 orders
        self.assertGreaterEqual(count, 1)

    def test_custom_segment_audience(self):
        campaign = self._make_campaign("AUD_SEG")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=AUDIENCE_CUSTOM_SEGMENT,
            criteria={"segment_id": str(self.vip_segment.pk)},
            actor=self.marketer,
        )
        count = CampaignAudienceService.generate_audience_members(campaign, audience)
        self.assertEqual(count, 1)

    def test_custom_tag_audience(self):
        campaign = self._make_campaign("AUD_TAG")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=AUDIENCE_CUSTOM_TAG,
            criteria={"tag_code": "FREQUENT"},
            actor=self.marketer,
        )
        count = CampaignAudienceService.generate_audience_members(campaign, audience)
        self.assertEqual(count, 1)

    def test_custom_filter_min_orders(self):
        campaign = self._make_campaign("AUD_FILT")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=AUDIENCE_CUSTOM_FILTER,
            criteria={"min_orders": 2},
            actor=self.marketer,
        )
        count = CampaignAudienceService.generate_audience_members(campaign, audience)
        # Only customer has 3 orders
        self.assertEqual(count, 1)

    def test_idempotent_generation(self):
        """Generating audience twice should not create duplicate members."""
        campaign = self._make_campaign("AUD_IDEM")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=AUDIENCE_ALL_CUSTOMERS,
            criteria={},
            actor=self.marketer,
        )
        count1 = CampaignAudienceService.generate_audience_members(campaign, audience)
        count2 = CampaignAudienceService.generate_audience_members(campaign, audience)
        self.assertEqual(count1, count2)
        total_members = CampaignAudienceMember.objects.filter(campaign=campaign).count()
        # Should not have doubled up
        self.assertEqual(total_members, count1 + CampaignAudienceMember.objects.filter(
            campaign=campaign, status=MEMBER_EXCLUDED
        ).count())
