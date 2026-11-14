# =============================================================================
# RestaurantFlow — Health Endpoint Tests
# Phase 24
# =============================================================================

from django.test import TestCase


class HealthEndpointTests(TestCase):

    def test_live_returns_ok(self):
        resp = self.client.get("/health/live/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_ready_checks_db_and_redis(self):
        resp = self.client.get("/health/ready/")
        # In the test env DB (sqlite) + locmem cache are healthy.
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ready")
        self.assertEqual(data["database"], "ok")
        self.assertEqual(data["redis"], "ok")

    def test_dependencies_reports_components(self):
        resp = self.client.get("/health/dependencies/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("dependencies", data)
        deps = data["dependencies"]
        for component in ("database", "redis", "channels", "celery", "config"):
            self.assertIn(component, deps)
        self.assertEqual(deps["database"], "ok")
        self.assertEqual(deps["redis"], "ok")

    def test_dependencies_does_not_leak_secrets(self):
        resp = self.client.get("/health/dependencies/")
        body = resp.content.decode()
        # No actual secret values, stack traces, or raw field names leak.
        self.assertNotIn("change_me", body)
        self.assertNotIn("Traceback", body)
        # The config status is coarse (ok/error), never naming a secret field.
        deps = resp.json()["dependencies"]
        self.assertIn(deps["config"], ("ok", "error", "unknown"))
