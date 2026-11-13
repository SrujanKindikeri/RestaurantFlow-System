# =============================================================================
# RestaurantFlow — Rate Limiting Throttles
# Phase 21 — Security, Audit & Compliance Hardening
#
# DRF throttle classes for abuse-prone endpoints.  Limits are configurable
# via environment variables and fall back to safe defaults.
#
# Throttle scopes:
#   - auth_login        → POST /api/auth/login/
#   - auth_register     → POST /api/auth/register/
#   - auth_password     → password reset / change endpoints
#   - sensitive_op      → refunds, cancellations, reversals, etc.
#   - export            → data export endpoints
#   - search            → expensive search / report queries
#
# Redis is used as the cache backend (configured in settings.CACHES).
# If Redis is unavailable, DRF falls back to the local memory cache backend,
# which is adequate for single-process deployments but not for multi-process.
# =============================================================================

import logging

from rest_framework.throttling import ScopedRateThrottle

logger = logging.getLogger("core")


class ConfigurableScopedRateThrottle(ScopedRateThrottle):
    """
    Base throttle that reads its rate from a Django setting or env var,
    falling back to a safe default if not configured.

    Subclasses set ``scope_attr`` (the settings key) and ``default_rate``.
    """

    scope_attr = "THROTTLE_DEFAULT_RATE"
    default_rate = "100/hour"
    scope = "default"

    def get_cache_key(self, request, view):
        # Use the authenticated user's PK if available, otherwise fall back to IP.
        # This makes throttling tenant-aware without trusting a client-supplied tenant ID.
        if request.user and request.user.is_authenticated:
            ident = f"user:{request.user.pk}"
        else:
            ident = self.get_ident(request)
        return self.cache_format % {"scope": self.scope, "ident": ident}

    def get_rate(self):
        from django.conf import settings
        rates = getattr(settings, "THROTTLE_RATES", {})
        return rates.get(self.scope, self.default_rate)


# ---------------------------------------------------------------------------
# Authentication throttles
# ---------------------------------------------------------------------------

class LoginRateThrottle(ConfigurableScopedRateThrottle):
    """Throttle login attempts — limits brute-force attacks."""
    scope = "auth_login"
    default_rate = "30/hour"

    def get_cache_key(self, request, view):
        # For login, always throttle by IP (user is not yet authenticated).
        # Also include any email hint if present, to catch distributed brute-force
        # against a single account from the same IP.
        ident = self.get_ident(request)
        email = request.data.get("email", "")
        if email:
            ident = f"{ident}:{email.lower()[:64]}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


class RegistrationRateThrottle(ConfigurableScopedRateThrottle):
    """Throttle public registration — prevents account-spam attacks."""
    scope = "auth_register"
    default_rate = "5/hour"


class PasswordResetRateThrottle(ConfigurableScopedRateThrottle):
    """Throttle password-reset requests — prevents enumeration and spam."""
    scope = "auth_password"
    default_rate = "10/hour"

    def get_cache_key(self, request, view):
        # Throttle by IP for reset requests (user may not be authenticated).
        ident = self.get_ident(request)
        email = request.data.get("email", "")
        if email:
            ident = f"{ident}:{email.lower()[:64]}"
        return self.cache_format % {"scope": self.scope, "ident": ident}


# ---------------------------------------------------------------------------
# Sensitive-operation throttles
# ---------------------------------------------------------------------------

class SensitiveOperationThrottle(ConfigurableScopedRateThrottle):
    """
    Throttle high-impact endpoints: refunds, bill cancellations, accounting
    reversals, period closure, bulk operations.
    """
    scope = "sensitive_op"
    default_rate = "60/hour"


class ExportRateThrottle(ConfigurableScopedRateThrottle):
    """Throttle data-export endpoints — prevents data-exfiltration at scale."""
    scope = "export"
    default_rate = "20/hour"


class SearchRateThrottle(ConfigurableScopedRateThrottle):
    """Throttle expensive search and report queries."""
    scope = "search"
    default_rate = "120/hour"
