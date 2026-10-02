# =============================================================================
# RestaurantFlow — Core Tests
# Phase 1: Health endpoint test
# =============================================================================

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status


class HealthCheckTest(TestCase):
    """Tests for GET /api/health/"""

    def setUp(self):
        self.client = APIClient()

    def test_health_check_returns_200(self):
        url = reverse("health-check")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_check_response_body(self):
        url = reverse("health-check")
        response = self.client.get(url)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "RestaurantFlow API")

    def test_health_check_requires_no_authentication(self):
        """Health endpoint must be publicly accessible."""
        url = reverse("health-check")
        # No auth header at all — must still return 200
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_health_check_method_not_allowed(self):
        """Only GET is allowed on the health endpoint."""
        url = reverse("health-check")
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
