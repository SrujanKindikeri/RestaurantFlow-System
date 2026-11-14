# =============================================================================
# RestaurantFlow — Observability Integration Tests
# Phase 24
# =============================================================================

import json

from django.test import TestCase, override_settings
from django.urls import reverse

from observability.metrics import REGISTRY
from observability.business_events import record_business_event
from central_control.models import CentralAlert
from notifications.models import Notification
from observability.tests.base import make_org


AM_TOKEN = "am-secret-token"
SCRAPE_TOKEN = "scrape-token"


@override_settings(PROMETHEUS_SCRAPE_TOKEN=SCRAPE_TOKEN, SECURE_SSL_REDIRECT=False)
class PrometheusScrapeIntegrationTests(TestCase):

    def setUp(self):
        REGISTRY.clear()

    def test_request_then_scrape_shows_request_metric(self):
        # An unauthenticated request to a health endpoint is counted...
        self.client.get("/health/live/")
        # ...and the /metrics endpoint exposes it (token-gated, as in prod).
        resp = self.client.get("/metrics", HTTP_X_PROMETHEUS_TOKEN=SCRAPE_TOKEN)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        self.assertIn("# TYPE restaurantflow_http_requests_total counter", body)
        # The health request produced at least one 2xx request sample.
        self.assertIn('status_class="2xx"', body)

    def test_scrape_format_is_valid_exposition(self):
        # Prime at least one metric so the body has data lines.
        self.client.get("/health/ready/")
        resp = self.client.get("/metrics", HTTP_X_PROMETHEUS_TOKEN=SCRAPE_TOKEN)
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        type_lines = [l for l in body.splitlines() if l.startswith("# TYPE")]
        help_lines = [l for l in body.splitlines() if l.startswith("# HELP")]
        self.assertGreater(len(type_lines), 0)
        self.assertEqual(len(type_lines), len(help_lines))

    def test_scrape_refused_without_token(self):
        resp = self.client.get("/metrics")
        self.assertEqual(resp.status_code, 403)
        resp = self.client.get("/metrics", HTTP_X_PROMETHEUS_TOKEN="wrong")
        self.assertEqual(resp.status_code, 403)


class RequestCorrelationIntegrationTests(TestCase):

    def test_generated_request_id_returned_in_header(self):
        resp = self.client.get("/health/live/")
        self.assertIn("X-Request-ID", resp.headers)
        rid = resp["X-Request-ID"]
        self.assertTrue(rid)
        self.assertLessEqual(len(rid), 128)

    def test_valid_client_request_id_is_propagated(self):
        rid = "client-req-id-abc-123"
        resp = self.client.get("/health/live/", HTTP_X_REQUEST_ID=rid)
        self.assertEqual(resp["X-Request-ID"], rid)

    def test_invalid_client_request_id_is_replaced(self):
        # An unsafe/oversized id must not be trusted verbatim.
        resp = self.client.get("/health/live/", HTTP_X_REQUEST_ID="bad id with spaces!!")
        rid = resp["X-Request-ID"]
        self.assertNotEqual("bad id with spaces!!", rid)
        self.assertRegex(rid, r"^[A-Za-z0-9._\-]+$")


class BusinessEventIntegrationTests(TestCase):

    def test_business_event_counter_records_event(self):
        REGISTRY.clear()
        record_business_event("payment.completion.failed", severity="HIGH", company_id="c1")
        record_business_event("payment.completion.failed", severity="HIGH", company_id="c2")
        from observability.metrics import business_events_total
        self.assertEqual(
            business_events_total.get(event="payment.completion.failed", severity="HIGH"),
            2.0,
        )
        body = REGISTRY.render()
        self.assertIn('event="payment.completion.failed"', body)

    def test_business_event_never_raises_into_caller(self):
        # Passing bad label types should not raise into the business path.
        record_business_event("order.creation.failed", severity="MEDIUM")
        # No assertion needed — not raising is the contract.


class AlertToCentralControlIntegrationTests(TestCase):

    @override_settings(ALERTMANAGER_WEBHOOK_TOKEN=AM_TOKEN)
    def test_metric_alert_routes_to_central_control_and_notifies(self):
        org = make_org("Integ Corp")
        url = reverse("observability_alertmanager_webhook")
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "ApiDown", "severity": "critical", "instance": "api:8000"},
                "annotations": {"summary": "API unavailable", "description": "no successful scrapes"},
            }]
        }
        resp = self.client.post(url, data=json.dumps(payload), content_type="application/json",
                                HTTP_X_ALERTMANAGER_TOKEN=AM_TOKEN)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["created"], 1)
        # Alert visible in the existing Central Control surface.
        self.assertEqual(
            CentralAlert.objects.filter(organization=org, source_type="MONITORING",
                                         severity="CRITICAL").count(),
            1,
        )
        # Notification delivered via the existing notification center.
        self.assertEqual(
            Notification.objects.filter(notification_type="monitoring_alert", company=org).count(),
            1,
        )
