# =============================================================================
# RestaurantFlow — Marketing API Tests
# Phase 18
# =============================================================================

from decimal import Decimal
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from accounts.models import User
from organizations.models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
from accounts.models import Role, Permission, UserRoleAssignment

from marketing.tests.base import MarketingTestBase
from marketing.campaign_services import CampaignService
from marketing.promotion_services import PromotionService
from marketing.models import MarketingCampaign, Promotion
from marketing.constants import (
    CAMPAIGN_PROMOTION, PROMO_PERCENTAGE_DISCOUNT, DISCOUNT_PERCENTAGE,
)


class CampaignAPITests(MarketingTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.marketer)

    def test_list_campaigns_authenticated(self):
        CampaignService.create_campaign(
            company=self.org, restaurant=self.restaurant,
            data={"name": "API Campaign", "code": "API01", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )
        url = "/api/marketing/campaigns/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_list_campaigns_unauthenticated_denied(self):
        client = APIClient()
        response = client.get("/api/marketing/campaigns/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_campaign_api(self):
        response = self.client.post(
            "/api/marketing/campaigns/",
            {
                "name": "API Create",
                "code": "APICREATE",
                "campaign_type": CAMPAIGN_PROMOTION,
                "restaurant": str(self.restaurant.pk),
            },
            format="json",
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_get_campaign_detail(self):
        campaign = CampaignService.create_campaign(
            company=self.org, restaurant=self.restaurant,
            data={"name": "Detail Campaign", "code": "DET01", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )
        response = self.client.get(f"/api/marketing/campaigns/{campaign.pk}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["code"], "DET01")

    def test_get_campaign_not_found(self):
        import uuid
        response = self.client.get(f"/api/marketing/campaigns/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_submit_campaign_for_approval(self):
        campaign = CampaignService.create_campaign(
            company=self.org, restaurant=self.restaurant,
            data={"name": "Submit Test", "code": "SUBMIT01", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )
        response = self.client.post(f"/api/marketing/campaigns/{campaign.pk}/submit/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cancel_campaign(self):
        campaign = CampaignService.create_campaign(
            company=self.org, restaurant=self.restaurant,
            data={"name": "Cancel API", "code": "CANCEL_API", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )
        response = self.client.post(
            f"/api/marketing/campaigns/{campaign.pk}/cancel/",
            {"reason": "Test cancel"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        campaign.refresh_from_db()
        from marketing.constants import CAMPAIGN_CANCELLED
        self.assertEqual(campaign.status, CAMPAIGN_CANCELLED)

    def test_cashier_cannot_list_campaigns(self):
        self.client.force_authenticate(user=self.cashier)
        response = self.client.get("/api/marketing/campaigns/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class PromotionAPITests(MarketingTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.marketer)

    def test_list_promotions(self):
        PromotionService.create_promotion(
            company=self.org, restaurant=self.restaurant,
            data={
                "name": "API Promo",
                "code": "APIPROMO",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
            },
            actor=self.marketer,
        )
        response = self.client.get("/api/marketing/promotions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_promotion_api(self):
        response = self.client.post(
            "/api/marketing/promotions/",
            {
                "name": "New Promo",
                "code": "NEWP001",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": "15.00",
                "restaurant": str(self.restaurant.pk),
            },
            format="json",
        )
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])

    def test_validate_promotion_api(self):
        promo = PromotionService.create_promotion(
            company=self.org, restaurant=self.restaurant,
            data={
                "name": "Validate Promo",
                "code": "VALPROMO",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("10.00"),
            },
            actor=self.marketer,
        )
        PromotionService.activate(promo, self.marketer)

        response = self.client.post(
            "/api/marketing/promotions/validate/",
            {
                "promotion_code": "VALPROMO",
                "branch_id": str(self.branch.pk),
                "order_subtotal": "200.00",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["eligible"])

    def test_activate_promotion_api(self):
        promo = PromotionService.create_promotion(
            company=self.org, restaurant=self.restaurant,
            data={
                "name": "Activate API",
                "code": "ACTAPI",
                "promotion_type": PROMO_PERCENTAGE_DISCOUNT,
                "discount_type": DISCOUNT_PERCENTAGE,
                "discount_value": Decimal("5.00"),
            },
            actor=self.marketer,
        )
        response = self.client.post(f"/api/marketing/promotions/{promo.pk}/activate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        promo.refresh_from_db()
        self.assertTrue(promo.is_active)


class DashboardAPITests(MarketingTestBase):

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.marketer)

    def test_dashboard_requires_permission(self):
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get("/api/marketing/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_dashboard_returns_stats(self):
        response = self.client.get(
            "/api/marketing/dashboard/",
            {"restaurant": str(self.restaurant.pk)},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("active_campaigns", response.data)
        self.assertIn("total_discount_given", response.data)
