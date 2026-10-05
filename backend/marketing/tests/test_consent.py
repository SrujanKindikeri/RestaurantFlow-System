# =============================================================================
# RestaurantFlow — Marketing Consent & Delivery Tests
# Phase 18
# =============================================================================

from marketing.tests.base import MarketingTestBase
from marketing.campaign_services import CampaignService
from marketing.tracking_services import (
    MarketingConsentService, CampaignDeliveryService, CampaignConversionService,
)
from marketing.models import (
    MarketingCampaign, CampaignDelivery, CampaignConversion,
)
from marketing.constants import (
    CAMPAIGN_PROMOTION, CHANNEL_EMAIL, CHANNEL_SMS, CHANNEL_IN_APP,
    DELIVERY_UNSUBSCRIBED, DELIVERY_PENDING,
    CONVERSION_ORDER_PLACED, CONVERSION_PROMOTION_REDEEMED,
)
from crm.models import CustomerConsent
from crm.constants import CONSENT_GRANTED, CONSENT_REVOKED, CONSENT_MARKETING_SMS


class MarketingConsentTests(MarketingTestBase):

    def _make_campaign(self, code):
        return CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": f"Consent {code}", "code": code, "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )

    def test_email_consent_granted(self):
        # customer has MARKETING_EMAIL granted (set up in base)
        result = MarketingConsentService.has_marketing_consent(self.customer, CHANNEL_EMAIL)
        self.assertTrue(result)

    def test_sms_consent_not_granted(self):
        # customer does NOT have SMS consent
        result = MarketingConsentService.has_marketing_consent(self.customer, CHANNEL_SMS)
        self.assertFalse(result)

    def test_in_app_always_allowed(self):
        result = MarketingConsentService.has_marketing_consent(self.customer, CHANNEL_IN_APP)
        self.assertTrue(result)

    def test_revoked_consent_blocked(self):
        # Grant SMS consent then revoke
        consent, _ = CustomerConsent.objects.get_or_create(
            customer=self.customer2,
            consent_type=CONSENT_MARKETING_SMS,
            defaults={"status": CONSENT_GRANTED, "source": "CUSTOMER"},
        )
        self.assertTrue(
            MarketingConsentService.has_marketing_consent(self.customer2, CHANNEL_SMS)
        )
        consent.status = CONSENT_REVOKED
        consent.save()
        self.assertFalse(
            MarketingConsentService.has_marketing_consent(self.customer2, CHANNEL_SMS)
        )

    def test_no_consent_record_returns_false(self):
        # customer2 has no consent records
        result = MarketingConsentService.has_marketing_consent(self.customer2, CHANNEL_EMAIL)
        self.assertFalse(result)


class CampaignDeliveryTests(MarketingTestBase):

    def _make_campaign(self, code):
        return CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": f"Delivery {code}", "code": code, "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )

    def test_create_delivery_with_consent(self):
        """Customer with EMAIL consent → delivery created."""
        campaign = self._make_campaign("DEL_EMAIL")
        delivery = CampaignDeliveryService.create_delivery(campaign, self.customer, CHANNEL_EMAIL)
        self.assertIsNotNone(delivery)
        self.assertEqual(delivery.status, DELIVERY_PENDING)

    def test_create_delivery_without_consent_skipped(self):
        """Customer without SMS consent → UNSUBSCRIBED record, no active delivery."""
        campaign = self._make_campaign("DEL_SMS")
        delivery = CampaignDeliveryService.create_delivery(campaign, self.customer, CHANNEL_SMS)
        self.assertIsNone(delivery)
        # An UNSUBSCRIBED record should exist
        record = CampaignDelivery.objects.filter(
            campaign=campaign, customer=self.customer, channel=CHANNEL_SMS
        ).first()
        self.assertIsNotNone(record)
        self.assertEqual(record.status, DELIVERY_UNSUBSCRIBED)

    def test_delivery_idempotent(self):
        """Creating delivery twice returns existing record."""
        campaign = self._make_campaign("DEL_IDEM")
        d1 = CampaignDeliveryService.create_delivery(campaign, self.customer, CHANNEL_EMAIL)
        d2 = CampaignDeliveryService.create_delivery(campaign, self.customer, CHANNEL_EMAIL)
        self.assertIsNotNone(d1)
        self.assertIsNotNone(d2)
        self.assertEqual(d1.pk, d2.pk)

    def test_mark_sent(self):
        campaign = self._make_campaign("DEL_SENT")
        delivery = CampaignDeliveryService.create_delivery(campaign, self.customer, CHANNEL_EMAIL)
        CampaignDeliveryService.mark_sent(delivery)
        delivery.refresh_from_db()
        from marketing.constants import DELIVERY_SENT
        self.assertEqual(delivery.status, DELIVERY_SENT)

    def test_mark_failed(self):
        campaign = self._make_campaign("DEL_FAIL")
        delivery = CampaignDeliveryService.create_delivery(campaign, self.customer, CHANNEL_EMAIL)
        CampaignDeliveryService.mark_failed(delivery, reason="Provider unavailable")
        delivery.refresh_from_db()
        from marketing.constants import DELIVERY_FAILED
        self.assertEqual(delivery.status, DELIVERY_FAILED)
        self.assertEqual(delivery.failure_reason, "Provider unavailable")


class CampaignConversionTests(MarketingTestBase):

    def _make_campaign(self, code):
        return CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": f"Conv {code}", "code": code, "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )

    def test_record_conversion(self):
        campaign = self._make_campaign("CONV01")
        conversion = CampaignConversionService.record_conversion(
            campaign,
            self.customer,
            conversion_type=CONVERSION_ORDER_PLACED,
            conversion_value=500,
        )
        self.assertIsNotNone(conversion)
        self.assertEqual(conversion.conversion_type, CONVERSION_ORDER_PLACED)

    def test_conversion_idempotent_with_order(self):
        """Same (campaign, customer, order, type) → only one record."""
        from orders.models import Order
        # Create a minimal order — only required non-nullable fields
        order = Order.objects.create(
            branch=self.branch,
            order_number="ORD-TEST-001",
            order_type="COUNTER",
            status="CONFIRMED",
            created_by=self.cashier,
        )
        campaign = self._make_campaign("CONV02")
        c1 = CampaignConversionService.record_conversion(
            campaign, self.customer,
            order=order,
            conversion_type=CONVERSION_ORDER_PLACED,
        )
        c2 = CampaignConversionService.record_conversion(
            campaign, self.customer,
            order=order,
            conversion_type=CONVERSION_ORDER_PLACED,
        )
        self.assertIsNotNone(c1)
        self.assertIsNone(c2)  # idempotent duplicate

    def test_conversion_updates_member_status(self):
        from marketing.models import CampaignAudienceMember
        from marketing.audience_services import CampaignAudienceService
        from marketing.constants import MEMBER_CONVERTED

        campaign = self._make_campaign("CONV03")
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type="ALL_CUSTOMERS",
            criteria={},
            actor=self.marketer,
        )
        CampaignAudienceService.generate_audience_members(campaign, audience)

        CampaignConversionService.record_conversion(
            campaign, self.customer,
            conversion_type=CONVERSION_ORDER_PLACED,
        )
        member = CampaignAudienceMember.objects.get(
            campaign=campaign, customer=self.customer
        )
        self.assertEqual(member.status, MEMBER_CONVERTED)
