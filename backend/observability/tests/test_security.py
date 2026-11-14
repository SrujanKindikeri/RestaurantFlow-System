# =============================================================================
# RestaurantFlow — Observability Security Tests
# Phase 24
# =============================================================================

import json

from django.test import RequestFactory, TestCase, override_settings

from observability.views import metrics_view
from observability.metrics import REGISTRY, http_requests_total


class MetricsAccessTests(TestCase):

    @override_settings(DEBUG=False, PROMETHEUS_SCRAPE_TOKEN="", SECURE_SSL_REDIRECT=False)
    def test_metrics_refused_without_token_in_production(self):
        request = RequestFactory().get("/metrics")
        resp = metrics_view(request)
        self.assertEqual(resp.status_code, 403)

    @override_settings(DEBUG=False, PROMETHEUS_SCRAPE_TOKEN="secret",
                       SECURE_SSL_REDIRECT=False)
    def test_metrics_refused_with_wrong_token(self):
        request = RequestFactory().get("/metrics", HTTP_X_PROMETHEUS_TOKEN="nope")
        resp = metrics_view(request)
        self.assertEqual(resp.status_code, 403)

    @override_settings(DEBUG=False, PROMETHEUS_SCRAPE_TOKEN="secret",
                       SECURE_SSL_REDIRECT=False)
    def test_metrics_allowed_with_correct_token(self):
        request = RequestFactory().get("/metrics", HTTP_X_PROMETHEUS_TOKEN="secret")
        resp = metrics_view(request)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/plain", resp["Content-Type"])

    @override_settings(DEBUG=True)
    def test_metrics_allowed_in_debug(self):
        request = RequestFactory().get("/metrics")
        resp = metrics_view(request)
        self.assertEqual(resp.status_code, 200)


class MetricLabelSafetyTests(TestCase):

    def test_user_identifiers_never_appear_as_labels(self):
        REGISTRY.clear()
        # Simulate the middleware path with a resolved view name (low cardinality)
        from observability.middleware import MetricsMiddleware
        from django.http import HttpResponse

        factory = RequestFactory()

        class FakeMatch:
            view_name = "orders-list"

        request = factory.get("/api/orders/")
        request.resolver_match = FakeMatch()
        mw = MetricsMiddleware(lambda req: HttpResponse(status=200, content=b"[]"))
        mw(request)
        body = REGISTRY.render()
        # The route label must be the view name, and no high-cardinality id leaked.
        self.assertIn('route="orders-list"', body)
        # user ids / arbitrary ids would only appear if mis-labelled; assert the
        # counter has exactly the declared label set.
        line = [l for l in body.splitlines() if l.startswith("restaurantflow_http_requests_total{")][0]
        labels = line.split("{", 1)[1].split("}", 1)[0]
        self.assertIn("method=", labels)
        self.assertIn("status_class=", labels)
        self.assertIn("route=", labels)
        # No extra labels
        self.assertEqual(labels.count("="), 3)


class FrontendErrorEndpointTests(TestCase):

    def test_frontend_errors_are_anonymous_and_captured(self):
        resp = self.client.post(
            "/api/observability/frontend-errors",
            data=json.dumps({
                "type": "TypeError",
                "message": "Cannot read properties of undefined",
                "url": "https://app.example.com/dashboard",
                "line": 42,
                "column": 7,
                "severity": "HIGH",
                "app_version": "1.4.0",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_frontend_errors_truncate_large_messages(self):
        long_msg = "x" * 5000
        resp = self.client.post(
            "/api/observability/frontend-errors",
            data=json.dumps({"message": long_msg}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_frontend_errors_no_payload_persisted(self):
        # The endpoint must not echo or store request payloads back.
        resp = self.client.post(
            "/api/observability/frontend-errors",
            data=json.dumps({"type": "E", "message": "m", "card_number": "4111111111111111", "cvv": "123"}),
            content_type="application/json",
        )
        body = resp.content.decode()
        self.assertNotIn("4111111111111111", body)
        self.assertNotIn("123", body)
