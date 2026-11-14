# =============================================================================
# RestaurantFlow — Locust Auth Scenarios
# Simulates login and token refresh; provides shared helpers used by
# other scenario modules.
# =============================================================================

import os

from locust import task, between
from locust.contrib.fasthttp import FastHttpUser


# ---------------------------------------------------------------------------
# Credentials read from environment — never hard-code secrets
# ---------------------------------------------------------------------------
STAFF_EMAIL = os.environ.get("LOAD_TEST_STAFF_EMAIL", "staff@example.com")
STAFF_PASSWORD = os.environ.get("LOAD_TEST_STAFF_PASSWORD", "changeme")

KITCHEN_EMAIL = os.environ.get("LOAD_TEST_KITCHEN_EMAIL", "kitchen@example.com")
KITCHEN_PASSWORD = os.environ.get("LOAD_TEST_KITCHEN_PASSWORD", "changeme")

MANAGER_EMAIL = os.environ.get("LOAD_TEST_MANAGER_EMAIL", "manager@example.com")
MANAGER_PASSWORD = os.environ.get("LOAD_TEST_MANAGER_PASSWORD", "changeme")

PAYMENT_EMAIL = os.environ.get("LOAD_TEST_PAYMENT_EMAIL", "cashier@example.com")
PAYMENT_PASSWORD = os.environ.get("LOAD_TEST_PAYMENT_PASSWORD", "changeme")


# ---------------------------------------------------------------------------
# Shared mixin: obtain a JWT on startup and add it to every request
# ---------------------------------------------------------------------------
class JWTAuthMixin:
    """
    Mixin for Locust HttpUser subclasses.
    Call `self._login(email, password)` in `on_start` to authenticate.
    After that, all requests automatically carry the Authorization header.
    """

    _access_token: str = ""
    _refresh_token: str = ""

    def _login(self, email: str, password: str) -> None:
        with self.client.post(
            "/api/auth/login/",
            json={"email": email, "password": password},
            catch_response=True,
            name="/api/auth/login/",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data.get("access", "")
                self._refresh_token = data.get("refresh", "")
                self.client.headers.update(
                    {"Authorization": f"Bearer {self._access_token}"}
                )
                resp.success()
            else:
                resp.failure(f"Login failed: {resp.status_code} {resp.text[:200]}")

    def _refresh(self) -> None:
        with self.client.post(
            "/api/auth/token/refresh/",
            json={"refresh": self._refresh_token},
            catch_response=True,
            name="/api/auth/token/refresh/",
        ) as resp:
            if resp.status_code == 200:
                data = resp.json()
                self._access_token = data.get("access", "")
                self.client.headers.update(
                    {"Authorization": f"Bearer {self._access_token}"}
                )
                resp.success()
            else:
                resp.failure(f"Token refresh failed: {resp.status_code}")


# ---------------------------------------------------------------------------
# Standalone auth user (useful for auth-only load testing)
# ---------------------------------------------------------------------------
class AuthOnlyUser(JWTAuthMixin, FastHttpUser):
    """
    Exercises login and token refresh only.
    Useful when measuring the overhead of the auth layer in isolation.
    """

    wait_time = between(1, 3)
    weight = 1

    def on_start(self):
        self._login(STAFF_EMAIL, STAFF_PASSWORD)

    @task(3)
    def verify_token(self):
        self.client.get(
            "/api/auth/me/",
            name="/api/auth/me/",
        )

    @task(1)
    def refresh_token(self):
        self._refresh()
