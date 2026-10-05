# =============================================================================
# RestaurantFlow — CRM Permissions & API Security Tests
# Phase 17
# =============================================================================

from rest_framework.test import APIClient
from crm.tests.base import CRMTestBase


class CRMAPIAuthTests(CRMTestBase):

    def setUp(self):
        self.client = APIClient()

    # -----------------------------------------------------------------------
    # Unauthenticated access
    # -----------------------------------------------------------------------

    def test_customer_list_requires_auth(self):
        res = self.client.get("/api/crm/customers/")
        self.assertEqual(res.status_code, 401)

    def test_customer_search_requires_auth(self):
        res = self.client.get("/api/crm/customers/search/?q=test")
        self.assertEqual(res.status_code, 401)

    def test_feedback_list_requires_auth(self):
        res = self.client.get("/api/crm/feedback/")
        self.assertEqual(res.status_code, 401)

    def test_segments_requires_auth(self):
        res = self.client.get("/api/crm/segments/")
        self.assertEqual(res.status_code, 401)

    def test_loyalty_requires_auth(self):
        res = self.client.get("/api/crm/loyalty/program/")
        self.assertEqual(res.status_code, 401)

    def test_rewards_requires_auth(self):
        res = self.client.get("/api/crm/rewards/")
        self.assertEqual(res.status_code, 401)

    # -----------------------------------------------------------------------
    # No CRM permission user
    # -----------------------------------------------------------------------

    def test_no_crm_user_cannot_list_customers(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.no_crm_user)}"
        )
        res = self.client.get("/api/crm/customers/")
        self.assertEqual(res.status_code, 403)

    def test_no_crm_user_cannot_create_customer(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.no_crm_user)}"
        )
        res = self.client.post("/api/crm/customers/", {
            "first_name": "Test", "restaurant_id": str(self.restaurant.pk)
        }, format="json")
        self.assertEqual(res.status_code, 403)

    # -----------------------------------------------------------------------
    # IDOR prevention — cross-restaurant customer access
    # -----------------------------------------------------------------------

    def test_cannot_access_other_restaurant_customer(self):
        """Manager from restaurant A should get 404 for restaurant B customer."""
        c_other = self.make_customer(
            restaurant=self.other_restaurant, phone="+910005000001"
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.manager_user)}"
        )
        res = self.client.get(f"/api/crm/customers/{c_other.pk}/")
        self.assertEqual(res.status_code, 404)

    def test_cannot_see_other_restaurant_customers_in_list(self):
        c_mine = self.make_customer(restaurant=self.restaurant, phone="+910005000002")
        c_other = self.make_customer(restaurant=self.other_restaurant, phone="+910005000003")

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.manager_user)}"
        )
        res = self.client.get("/api/crm/customers/")
        self.assertEqual(res.status_code, 200)
        result_ids = [r["id"] for r in res.data["results"]]
        self.assertIn(str(c_mine.pk), result_ids)
        self.assertNotIn(str(c_other.pk), result_ids)

    # -----------------------------------------------------------------------
    # Authorized access
    # -----------------------------------------------------------------------

    def test_manager_can_list_customers(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.manager_user)}"
        )
        res = self.client.get("/api/crm/customers/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("results", res.data)

    def test_cashier_can_search_customers(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.cashier_user)}"
        )
        res = self.client.get("/api/crm/customers/search/?q=test")
        self.assertEqual(res.status_code, 200)

    def test_manager_can_create_customer(self):
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.manager_user)}"
        )
        res = self.client.post("/api/crm/customers/", {
            "first_name": "API",
            "last_name": "Test",
            "phone": "+910005000099",
            "restaurant_id": str(self.restaurant.pk),
        }, format="json")
        self.assertIn(res.status_code, [200, 201])

    def test_superuser_can_access_any_customer(self):
        c_other = self.make_customer(
            restaurant=self.other_restaurant, phone="+910005000010"
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.superuser)}"
        )
        res = self.client.get(f"/api/crm/customers/{c_other.pk}/")
        self.assertEqual(res.status_code, 200)


class MaskedPIITests(CRMTestBase):
    """Ensure that list/search responses use masked PII, not full PII."""

    def setUp(self):
        self.client = APIClient()

    def test_list_response_has_masked_phone_not_full_phone(self):
        self.make_customer(phone="+919876543210", email="real@example.com")
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.cashier_user)}"
        )
        res = self.client.get("/api/crm/customers/")
        self.assertEqual(res.status_code, 200)
        for c in res.data["results"]:
            # Should have masked fields, NOT raw phone/email at this level
            self.assertIn("masked_phone", c)
            self.assertIn("masked_email", c)
            # Raw phone should not appear in list serializer output
            self.assertNotIn("phone", c)

    def test_search_response_masked(self):
        self.make_customer(phone="+919876543211", email="search@example.com")
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {self.get_token(self.cashier_user)}"
        )
        res = self.client.get("/api/crm/customers/search/?q=9876543211")
        self.assertEqual(res.status_code, 200)
        for r in res.data["results"]:
            self.assertIn("masked_phone", r)
