# =============================================================================
# RestaurantFlow — CRM Consent Tests
# Phase 17
# =============================================================================

from crm.consent_services import CustomerConsentService
from crm.constants import CONSENT_GRANTED, CONSENT_REVOKED
from crm.tests.base import CRMTestBase


class ConsentTests(CRMTestBase):

    def test_grant_consent(self):
        c = self.make_customer(phone="+910004000001")
        consent = CustomerConsentService.grant_consent(
            c, "MARKETING_EMAIL", source="CUSTOMER", actor=self.cashier_user
        )
        self.assertEqual(consent.status, CONSENT_GRANTED)
        self.assertIsNotNone(consent.granted_at)
        self.assertIsNone(consent.revoked_at)

    def test_revoke_consent(self):
        c = self.make_customer(phone="+910004000002")
        CustomerConsentService.grant_consent(c, "MARKETING_SMS", source="CUSTOMER")
        consent = CustomerConsentService.revoke_consent(c, "MARKETING_SMS", source="CUSTOMER")
        self.assertEqual(consent.status, CONSENT_REVOKED)
        self.assertIsNotNone(consent.revoked_at)

    def test_has_consent(self):
        c = self.make_customer(phone="+910004000003")
        self.assertFalse(CustomerConsentService.has_consent(c, "MARKETING_EMAIL"))
        CustomerConsentService.grant_consent(c, "MARKETING_EMAIL")
        self.assertTrue(CustomerConsentService.has_consent(c, "MARKETING_EMAIL"))
        CustomerConsentService.revoke_consent(c, "MARKETING_EMAIL")
        self.assertFalse(CustomerConsentService.has_consent(c, "MARKETING_EMAIL"))

    def test_consent_history_preserved(self):
        from crm.models import CustomerConsentHistory
        c = self.make_customer(phone="+910004000004")
        CustomerConsentService.grant_consent(c, "LOYALTY")
        CustomerConsentService.revoke_consent(c, "LOYALTY")
        CustomerConsentService.grant_consent(c, "LOYALTY")

        history = CustomerConsentHistory.objects.filter(
            customer=c, consent_type="LOYALTY"
        ).order_by("changed_at")
        self.assertEqual(history.count(), 3)
        self.assertEqual(history[0].new_status, CONSENT_GRANTED)
        self.assertEqual(history[1].new_status, CONSENT_REVOKED)
        self.assertEqual(history[2].new_status, CONSENT_GRANTED)

    def test_consent_history_immutable(self):
        from crm.models import CustomerConsentHistory
        c = self.make_customer(phone="+910004000005")
        CustomerConsentService.grant_consent(c, "FEEDBACK_COMMUNICATION")
        history = CustomerConsentHistory.objects.filter(customer=c).first()
        history.new_status = "GRANTED"  # same value but attempt update
        with self.assertRaises(ValueError):
            history.save()

    def test_get_consent_summary(self):
        c = self.make_customer(phone="+910004000006")
        CustomerConsentService.grant_consent(c, "MARKETING_EMAIL")
        CustomerConsentService.grant_consent(c, "LOYALTY")
        summary = CustomerConsentService.get_consent_summary(c)
        self.assertEqual(summary["MARKETING_EMAIL"], CONSENT_GRANTED)
        self.assertEqual(summary["LOYALTY"], CONSENT_GRANTED)
