# =============================================================================
# RestaurantFlow — Locust Load Test Entry Point
#
# Usage:
#   locust -f performance/locustfile.py --host http://localhost:8000
#
# Headless (CI):
#   locust -f performance/locustfile.py --headless -u 50 -r 5 --run-time 60s
#
# See performance/README.md for full instructions.
# =============================================================================

import os
import sys

# Allow `from scenarios.xxx import ...` when running from repo root
sys.path.insert(0, os.path.dirname(__file__))

from locust import between
from locust.contrib.fasthttp import FastHttpUser

from scenarios.auth import (
    JWTAuthMixin,
    STAFF_EMAIL,
    STAFF_PASSWORD,
    KITCHEN_EMAIL,
    KITCHEN_PASSWORD,
    MANAGER_EMAIL,
    MANAGER_PASSWORD,
    PAYMENT_EMAIL,
    PAYMENT_PASSWORD,
)
from scenarios.orders import OrderTasksMixin
from scenarios.payments import PaymentTasksMixin
from scenarios.reporting import ReportingTasksMixin


# ---------------------------------------------------------------------------
# Concrete user classes
# Each class combines role-specific tasks and sets weight + wait_time.
# ---------------------------------------------------------------------------


class RestaurantStaffUser(OrderTasksMixin, FastHttpUser):
    """
    Branch staff (cashier / waiter).
    Browses the menu, creates orders, and finalizes bills.
    Highest spawn count — represents the typical busy-hour POS workload.
    """

    wait_time = between(1, 5)
    weight = 4

    def on_start(self):
        self._login(STAFF_EMAIL, STAFF_PASSWORD)


class KitchenUser(OrderTasksMixin, FastHttpUser):
    """
    Kitchen tablet user.
    Primarily updates order status (new → in-progress → ready).
    Uses the same OrderTasksMixin but the status-update task dominates.
    """

    wait_time = between(2, 8)
    weight = 2

    def on_start(self):
        self._login(KITCHEN_EMAIL, KITCHEN_PASSWORD)

    # Override task weights: kitchen users mostly read the catalog and
    # update order status; they rarely create orders or finalize bills.
    # Locust respects the @task weights defined on OrderTasksMixin, so
    # the natural distribution (update_order_status weight=2) works fine.
    # No override needed.


class ManagerUser(ReportingTasksMixin, FastHttpUser):
    """
    Branch or restaurant manager.
    Runs dashboard and reporting queries — the heaviest read workload.
    Lower weight because managers are fewer than POS staff.
    """

    wait_time = between(3, 10)
    weight = 1

    def on_start(self):
        self._login(MANAGER_EMAIL, MANAGER_PASSWORD)


class PaymentUser(PaymentTasksMixin, FastHttpUser):
    """
    Cashier focused on payment collection.
    Deliberately targets the same seeded bills to exercise the concurrent
    overpayment guard.  Run with high -u count to maximise contention.
    """

    wait_time = between(1, 3)
    weight = 2

    def on_start(self):
        self._login(PAYMENT_EMAIL, PAYMENT_PASSWORD)
