# =============================================================================
# RestaurantFlow — Locust Reporting Scenarios
# Exercises inventory dashboard, Central Control dashboard, and date-ranged
# reporting queries.  These are the most DB-intensive read endpoints.
# =============================================================================

import os

from locust import task, between
from locust.contrib.fasthttp import FastHttpUser

from scenarios.auth import JWTAuthMixin, MANAGER_EMAIL, MANAGER_PASSWORD

# Optional: restrict to a specific branch or restaurant for scoped queries
BRANCH_ID = os.environ.get("LOAD_TEST_BRANCH_ID", "")
DATE_FROM = os.environ.get("LOAD_TEST_DATE_FROM", "2024-01-01")
DATE_TO = os.environ.get("LOAD_TEST_DATE_TO", "2024-12-31")


class ReportingTasksMixin(JWTAuthMixin):
    """
    Read-heavy reporting tasks run by manager-role users.
    These endpoints aggregate data across many rows and are the most likely
    to exceed p95 latency targets without proper indexing.
    """

    @task(4)
    def inventory_dashboard(self):
        """
        GET /api/inventory/dashboard/
        Returns stock levels, low-stock alerts, recent movements.
        """
        self.client.get(
            "/api/inventory/dashboard/",
            name="/api/inventory/dashboard/",
        )

    @task(4)
    def central_control_dashboard(self):
        """
        GET /api/central-control/dashboard/
        Multi-restaurant aggregate metrics — most complex query in the system.
        """
        self.client.get(
            "/api/central-control/dashboard/",
            name="/api/central-control/dashboard/",
        )

    @task(3)
    def reporting_dashboard(self):
        """
        GET /api/reporting/dashboard/
        Branch-scoped revenue, order count, and payment aggregates.
        """
        params = ""
        if BRANCH_ID:
            params = f"?branch={BRANCH_ID}"
        self.client.get(
            f"/api/reporting/dashboard/{params}",
            name="/api/reporting/dashboard/",
        )

    @task(2)
    def sales_summary(self):
        self.client.get(
            f"/api/reporting/sales/summary/?date_from={DATE_FROM}&date_to={DATE_TO}",
            name="/api/reporting/sales/summary/",
        )

    @task(2)
    def sales_trend(self):
        self.client.get(
            f"/api/reporting/sales/trend/?date_from={DATE_FROM}&date_to={DATE_TO}",
            name="/api/reporting/sales/trend/",
        )

    @task(1)
    def top_selling_items(self):
        self.client.get(
            f"/api/reporting/menu/top-selling/?date_from={DATE_FROM}&date_to={DATE_TO}",
            name="/api/reporting/menu/top-selling/",
        )

    @task(1)
    def inventory_summary_report(self):
        self.client.get(
            "/api/reporting/inventory/summary/",
            name="/api/reporting/inventory/summary/",
        )

    @task(1)
    def branch_performance(self):
        self.client.get(
            f"/api/reporting/branches/performance/?date_from={DATE_FROM}&date_to={DATE_TO}",
            name="/api/reporting/branches/performance/",
        )
