# =============================================================================
# RestaurantFlow — Locust Payment Scenarios
#
# CRITICAL SCENARIO: concurrent payment attempts on the same bill.
# This directly exercises the select_for_update() overpayment guard
# added in FEAT-001.  Run with high concurrency (-u 20 -r 5) to stress
# the guard.
#
# Because locust users are greenlets (not threads), true simultaneous DB
# writes happen only when spawn rate is high or the host runs real threads.
# To maximise contention: run with --processes and high spawn rate.
# =============================================================================

import os
import random

from locust import task, between
from locust.contrib.fasthttp import FastHttpUser

from scenarios.auth import JWTAuthMixin, PAYMENT_EMAIL, PAYMENT_PASSWORD

# A list of pre-seeded finalized bill UUIDs for concurrent payment attempts.
# Set LOAD_TEST_BILL_IDS as a comma-separated list of UUIDs.
# Example: export LOAD_TEST_BILL_IDS="uuid1,uuid2,uuid3"
_raw_bill_ids = os.environ.get("LOAD_TEST_BILL_IDS", "")
SEED_BILL_IDS: list[str] = [b.strip() for b in _raw_bill_ids.split(",") if b.strip()]


class PaymentTasksMixin(JWTAuthMixin):
    """
    Payment tasks.  Multiple users target the same bill IDs to test the
    overpayment guard under realistic concurrent load.
    """

    @task(5)
    def attempt_concurrent_payment(self):
        """
        POST a full payment against a seeded bill.
        Multiple concurrent users will hit the same bill_id — the backend
        overpayment guard must reject duplicates rather than over-collect.
        """
        if not SEED_BILL_IDS:
            # Fallback: list bills and pick one
            resp = self.client.get("/api/billing/bills/?status=FINALIZED&page_size=5",
                                   name="/api/billing/bills/ [fallback]")
            if resp.status_code != 200:
                return
            results = resp.json().get("results", [])
            if not results:
                return
            bill_id = random.choice(results)["id"]
        else:
            bill_id = random.choice(SEED_BILL_IDS)

        payload = {
            "bill": bill_id,
            "amount": "100.00",
            "payment_method": "CASH",
            "cash_received": "100.00",
        }
        with self.client.post(
            "/api/payments/",
            json=payload,
            catch_response=True,
            name="/api/payments/ [concurrent]",
        ) as resp:
            if resp.status_code in (200, 201):
                resp.success()
            elif resp.status_code == 400:
                # Overpayment rejection is the expected outcome for duplicate
                # requests — count as success for load test purposes.
                resp.success()
            else:
                resp.failure(f"Payment failed unexpectedly: {resp.status_code}")

    @task(2)
    def view_payment_summary(self):
        """Check payment summary for a seeded bill."""
        if not SEED_BILL_IDS:
            return
        bill_id = random.choice(SEED_BILL_IDS)
        self.client.get(
            f"/api/payments/bill/{bill_id}/summary/",
            name="/api/payments/bill/{id}/summary/",
        )

    @task(1)
    def list_payments(self):
        self.client.get(
            "/api/payments/list/?page_size=20",
            name="/api/payments/list/",
        )
