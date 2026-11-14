# =============================================================================
# RestaurantFlow — Locust Orders Scenarios
# Menu catalog browse, order creation, kitchen status update, bill finalization.
# =============================================================================

import os
import uuid

from locust import task, between
from locust.contrib.fasthttp import FastHttpUser

from scenarios.auth import JWTAuthMixin, STAFF_EMAIL, STAFF_PASSWORD

# Branch UUID from env — must match a seeded branch
BRANCH_ID = os.environ.get("LOAD_TEST_BRANCH_ID", "")


class OrderTasksMixin(JWTAuthMixin):
    """
    Tasks shared between RestaurantStaffUser and KitchenUser.
    """

    _last_order_id: str = ""
    _last_bill_id: str = ""

    @task(5)
    def browse_menu_catalog(self):
        """Read the branch catalog — most frequent POS action."""
        if not BRANCH_ID:
            return
        self.client.get(
            f"/api/menu/branches/{BRANCH_ID}/catalog/",
            name="/api/menu/branches/{id}/catalog/",
        )

    @task(3)
    def list_orders(self):
        self.client.get(
            "/api/orders/?page_size=20",
            name="/api/orders/",
        )

    @task(2)
    def create_order(self):
        """Create a minimal counter order."""
        if not BRANCH_ID:
            return
        payload = {
            "branch": BRANCH_ID,
            "order_type": "COUNTER",
        }
        with self.client.post(
            "/api/orders/",
            json=payload,
            catch_response=True,
            name="/api/orders/ [POST]",
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                self._last_order_id = data.get("id", "")
                resp.success()
            else:
                resp.failure(f"Order creation failed: {resp.status_code}")

    @task(2)
    def update_order_status(self):
        """Simulate a kitchen tablet confirming an order."""
        if not self._last_order_id:
            return
        with self.client.patch(
            f"/api/orders/{self._last_order_id}/confirm/",
            json={},
            catch_response=True,
            name="/api/orders/{id}/confirm/",
        ) as resp:
            if resp.status_code in (200, 204, 400):
                # 400 is acceptable (already confirmed idempotent)
                resp.success()
            else:
                resp.failure(f"Order confirm failed: {resp.status_code}")

    @task(1)
    def finalize_bill(self):
        """Finalize the bill linked to the last created order."""
        if not self._last_order_id:
            return
        # Create bill from order first
        with self.client.post(
            f"/api/billing/bills/from-order/{self._last_order_id}/",
            json={},
            catch_response=True,
            name="/api/billing/bills/from-order/{id}/",
        ) as resp:
            if resp.status_code in (200, 201):
                data = resp.json()
                self._last_bill_id = data.get("id", "")
                resp.success()
            elif resp.status_code == 400:
                # Bill may already exist — still success for load test
                resp.success()
            else:
                resp.failure(f"Bill creation failed: {resp.status_code}")

        if self._last_bill_id:
            with self.client.post(
                f"/api/billing/bills/{self._last_bill_id}/finalize/",
                json={},
                catch_response=True,
                name="/api/billing/bills/{id}/finalize/",
            ) as resp:
                if resp.status_code in (200, 204, 400):
                    resp.success()
                else:
                    resp.failure(f"Bill finalize failed: {resp.status_code}")
