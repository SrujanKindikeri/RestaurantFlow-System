# =============================================================================
# RestaurantFlow — Observability Metrics Tests
# Phase 24
# =============================================================================

from django.test import RequestFactory, override_settings
from django.http import HttpResponse

from observability.tests.base import ObservabilityTestCase
from observability.metrics import (
    REGISTRY, Registry, Counter, Gauge, Histogram,
    http_requests_total, http_errors_total,
)


class MetricPrimitiveTests(ObservabilityTestCase):

    def test_counter_increments_and_rejects_negative(self):
        c = Counter("t_c", "help", ("route",))
        c.inc(route="a")
        c.inc(2, route="a")
        self.assertEqual(c.get(route="a"), 3.0)
        with self.assertRaises(ValueError):
            c.inc(-1, route="a")

    def test_gauge_set_inc_dec(self):
        g = Gauge("t_g", "help", ("queue",))
        g.set(5, queue="q")
        self.assertEqual(g.get(queue="q"), 5.0)
        g.inc(2, queue="q")
        self.assertEqual(g.get(queue="q"), 7.0)
        g.dec(3, queue="q")
        self.assertEqual(g.get(queue="q"), 4.0)

    def test_histogram_cumulative_buckets_sum_count(self):
        reg = Registry()
        h = reg.register(Histogram("t_h", "help", (0.1, 1.0, 10.0), ("route",)))
        h.observe(0.05, route="a")
        h.observe(0.5, route="a")
        h.observe(5.0, route="a")
        self.assertEqual(h.get_count(route="a"), 3)
        self.assertAlmostEqual(h.get_sum(route="a"), 5.55)
        # Buckets: <=0.1 -> 1, <=1.0 -> 2, <=10.0 -> 3, +Inf -> 3
        body = reg.render()
        self.assertIn("t_h_bucket", body)

    def test_unknown_label_rejected(self):
        c = Counter("t_u", "help", ("route",))
        with self.assertRaises(KeyError):
            c.inc(route="a", unexpected="x")
        with self.assertRaises(KeyError):
            c.inc()

    def test_cardinality_cap_enforced(self):
        c = Counter("t_cap", "help", ("k",))
        from observability.constants import METRIC_CARDINALITY_CAP
        # exceed the cap
        for i in range(METRIC_CARDINALITY_CAP + 10):
            c.inc(k=f"key-{i}")
        # only CAP distinct keys recorded; the last 10 dropped
        self.assertEqual(len(c._values), METRIC_CARDINALITY_CAP)
        self.assertEqual(c.get(k=f"key-{METRIC_CARDINALITY_CAP + 9}"), 0.0)


class HttpRequestMetricsTests(ObservabilityTestCase):

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def _run_middleware(self, response_status=200, path="/health/live/", method="GET"):
        from observability.middleware import MetricsMiddleware
        request = getattr(self.factory, method.lower())(path)
        request.resolver_match = None  # simulate unresolved route handling
        response = HttpResponse(status=response_status, content=b'{"status":"ok"}')
        mw = MetricsMiddleware(lambda req: response)
        return mw(request)

    def test_request_counter_increments_by_status_class(self):
        self._run_middleware(response_status=200)
        self.assertEqual(http_requests_total.get(route="not_resolved", method="GET", status_class="2xx"), 1.0)
        self._run_middleware(response_status=404)
        self.assertEqual(http_requests_total.get(route="not_resolved", method="GET", status_class="4xx"), 1.0)

    def test_error_counter_increments_on_5xx(self):
        self._run_middleware(response_status=500)
        self.assertEqual(http_errors_total.get(route="not_resolved", method="GET"), 1.0)
        self._run_middleware(response_status=200)
        # still only the one 5xx
        self.assertEqual(http_errors_total.get(route="not_resolved", method="GET"), 1.0)

    def test_metrics_skip_path(self):
        # /metrics is skipped to avoid scrape self-noise — assert no data
        # SAMPLE line is emitted (HELP/TYPE still present).
        self._run_middleware(path="/metrics")
        body = REGISTRY.render()
        sample_lines = [
            l for l in body.splitlines()
            if l.startswith("restaurantflow_http_requests_total{")
        ]
        self.assertEqual(sample_lines, [])

    def test_low_cardinality_repeated_requests_one_combination(self):
        for _ in range(3):
            self._run_middleware(response_status=200, path="/health/live/")
        body = REGISTRY.render()
        # exactly one http_requests_total line for this route/method/status_class
        lines = [l for l in body.splitlines() if l.startswith("restaurantflow_http_requests_total{")]
        matching = [l for l in lines if 'route="not_resolved"' in l and 'status_class="2xx"' in l]
        self.assertEqual(len(matching), 1)
        self.assertIn(" 3", matching[0].split("}")[-1])


class MetricsEndpointTests(ObservabilityTestCase):

    @override_settings(DEBUG=True)
    def test_metrics_endpoint_renders_text_format_in_debug(self):
        http_requests_total.inc(route="r", method="GET", status_class="2xx")
        from observability.views import metrics_view
        request = RequestFactory().get("/metrics")
        response = metrics_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])
        body = response.content.decode()
        self.assertIn("# HELP restaurantflow_http_requests_total", body)
        self.assertIn("# TYPE restaurantflow_http_requests_total counter", body)
        self.assertIn('route="r"', body)

    @override_settings(DEBUG=False, PROMETHEUS_SCRAPE_TOKEN="bearer-secret",
                       SECURE_SSL_REDIRECT=False)
    def test_metrics_accepts_bearer_authorization_header(self):
        from observability.views import metrics_view
        request = RequestFactory().get(
            "/metrics", HTTP_AUTHORIZATION="Bearer bearer-secret"
        )
        response = metrics_view(request)
        self.assertEqual(response.status_code, 200)
        # wrong bearer token → 403
        request = RequestFactory().get("/metrics", HTTP_AUTHORIZATION="Bearer nope")
        self.assertEqual(metrics_view(request).status_code, 403)
