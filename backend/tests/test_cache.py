# =============================================================================
# RestaurantFlow — Cache Behavior Tests
# FEAT-004: Verifies CacheService hit/miss, Redis failure fallback,
# tenant key isolation, and on_commit invalidation.
# =============================================================================

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
