# =============================================================================
# RestaurantFlow — Cache Behavior Tests
# FEAT-004: Verifies CacheService hit/miss, Redis failure fallback,
# tenant key isolation, and on_commit invalidation.
# =============================================================================

from datetime import date
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from redis.exceptions import RedisError

from common.caching.services import CacheService, CACHE_MISS_SENTINEL
from common.caching.keys import menu_catalog_key, user_permissions_key


class CacheHitMissTest(TestCase):
    """Basic set / get / delete round-trip."""

    TEST_KEY = "rf:test:hit_miss_key"

    def tearDown(self):
        CacheService.delete(self.TEST_KEY)

    def test_cache_set_and_get_returns_value(self):
        CacheService.set(self.TEST_KEY, {"data": 42}, ttl=60)
        result = CacheService.get(self.TEST_KEY)
        self.assertEqual(result, {"data": 42})

    def test_cache_delete_removes_value(self):
        CacheService.set(self.TEST_KEY, "hello", ttl=60)
        CacheService.delete(self.TEST_KEY)
        result = CacheService.get(self.TEST_KEY)
        self.assertIsNone(result)

    def test_cache_miss_returns_none(self):
        CacheService.delete(self.TEST_KEY)
        result = CacheService.get(self.TEST_KEY)
        self.assertIsNone(result)


class RedisFailureFallbackTest(TestCase):
    """CacheService.get returns None and logs a warning on RedisError."""

    def test_get_returns_none_on_redis_failure(self):
        with patch("common.caching.services.cache.get", side_effect=RedisError("down")):
            result = CacheService.get("any_key")
        self.assertIsNone(result)

    def test_set_does_not_raise_on_redis_failure(self):
        with patch("common.caching.services.cache.set", side_effect=RedisError("down")):
            # Must not raise
            CacheService.set("any_key", "value", ttl=60)

    def test_get_secure_returns_sentinel_on_redis_failure(self):
        with patch("common.caching.services.cache.get", side_effect=RedisError("down")):
            result = CacheService.get_secure("any_key")
        self.assertIs(result, CACHE_MISS_SENTINEL)


class CacheKeyTenantIsolationTest(TestCase):
    """Keys for different tenant IDs must be distinct."""

    def test_menu_catalog_keys_differ_by_branch(self):
        key_a = menu_catalog_key("branch-aaa")
        key_b = menu_catalog_key("branch-bbb")
        self.assertNotEqual(key_a, key_b)

    def test_user_permissions_keys_differ_by_user(self):
        key_1 = user_permissions_key(user_id=1, branch_id="branch-x")
        key_2 = user_permissions_key(user_id=2, branch_id="branch-x")
        self.assertNotEqual(key_1, key_2)

    def test_user_permissions_keys_differ_by_branch(self):
        key_1 = user_permissions_key(user_id=1, branch_id="branch-x")
        key_2 = user_permissions_key(user_id=1, branch_id="branch-y")
        self.assertNotEqual(key_1, key_2)


class InvalidationOnCommitTest(TransactionTestCase):
    """
    invalidate_menu_catalog must delete cache only after the DB transaction commits.
    Uses TransactionTestCase so on_commit hooks actually fire.
    Requires django-redis backend — skipped with locmem.
    """

    def _has_redis_backend(self):
        from django.core.cache import cache as _cache
        return hasattr(_cache, 'delete_pattern')

    def test_invalidation_fires_on_commit(self):
        if not self._has_redis_backend():
            self.skipTest("delete_pattern not available on locmem cache backend")

        from django.db import transaction
        from common.caching.invalidation import invalidate_menu_catalog

        branch_id = "branch-invalidate-test"
        test_key = menu_catalog_key(branch_id)

        # Pre-populate cache
        CacheService.set(test_key, [{"item": "burger"}], ttl=300)
        self.assertIsNotNone(CacheService.get(test_key))

        # Schedule invalidation inside a transaction
        with transaction.atomic():
            invalidate_menu_catalog(branch_id)

        # After commit, cache should be cleared
        result = CacheService.get(test_key)
        self.assertIsNone(result)


class GetSecureSentinelTest(TestCase):
    """get_secure never silently falls back to stale data."""

    TEST_KEY = "rf:test:secure_key"

    def tearDown(self):
        CacheService.delete(self.TEST_KEY)

    def test_get_secure_returns_value_on_cache_hit(self):
        CacheService.set(self.TEST_KEY, {"perm": "read"}, ttl=60)
        result = CacheService.get_secure(self.TEST_KEY)
        self.assertEqual(result, {"perm": "read"})

    def test_get_secure_returns_sentinel_not_none_on_failure(self):
        """Distinguish Redis failure (SENTINEL) from a genuine None / cache miss."""
        with patch("common.caching.services.cache.get", side_effect=RedisError("fail")):
            result = CacheService.get_secure(self.TEST_KEY)
        self.assertIs(result, CACHE_MISS_SENTINEL)
        self.assertIsNot(result, None)


class ReportingCacheCrossOrgIsolationTest(TestCase):
    """
    Two users from different organizations must never receive each other's
    cached reporting data, even when both query at org-scope (restaurant=None,
    branch=None).

    This exercises the specific key-collision scenario fixed in Phase 22:
    scope_hash is now keyed by user.pk so the two requests produce distinct
    cache keys.
    """

    def _make_cache_key_for(self, user):
        """Return the sales_summary cache key that the selector would generate."""
        from common.caching.keys import reporting_key, make_params_hash
        # Mirrors the logic in select_sales_summary with restaurant=None, branch=None
        scope_hash = make_params_hash(
            str(user.pk),
            None,
            None,
        )
        return reporting_key(
            "sales_summary",
            scope_hash,
            str(date(2025, 1, 1)),
            str(date(2025, 1, 31)),
        )

    def setUp(self):
        from accounts.models import User
        self.user_org_a = User.objects.create_user(
            email="cache_isolation_a@test.com",
            password="pass123",
        )
        self.user_org_b = User.objects.create_user(
            email="cache_isolation_b@test.com",
            password="pass123",
        )

    def tearDown(self):
        CacheService.delete(self._make_cache_key_for(self.user_org_a))
        CacheService.delete(self._make_cache_key_for(self.user_org_b))

    def test_reporting_cache_keys_differ_by_user(self):
        """Different users must produce different cache keys even with identical scope params."""
        key_a = self._make_cache_key_for(self.user_org_a)
        key_b = self._make_cache_key_for(self.user_org_b)
        self.assertNotEqual(key_a, key_b)

    def test_org_a_data_not_served_to_org_b(self):
        """Populating cache for user A must not be visible to user B."""
        key_a = self._make_cache_key_for(self.user_org_a)
        key_b = self._make_cache_key_for(self.user_org_b)

        # Populate Org A's cached result
        org_a_data = {"net_sales": "10000.00", "org": "A"}
        CacheService.set(key_a, org_a_data, ttl=60)

        # Org B's key must be absent
        result_b = CacheService.get(key_b)
        self.assertIsNone(result_b, (
            "User B received User A's cached reporting data — cross-tenant key collision detected."
        ))

    def test_each_user_gets_own_cached_data(self):
        """Each user's cache slot is independent and returns only their own data."""
        key_a = self._make_cache_key_for(self.user_org_a)
        key_b = self._make_cache_key_for(self.user_org_b)

        CacheService.set(key_a, {"net_sales": "10000.00", "org": "A"}, ttl=60)
        CacheService.set(key_b, {"net_sales": "5000.00", "org": "B"}, ttl=60)

        result_a = CacheService.get(key_a)
        result_b = CacheService.get(key_b)

        self.assertEqual(result_a["org"], "A")
        self.assertEqual(result_b["org"], "B")
        self.assertNotEqual(result_a, result_b)
