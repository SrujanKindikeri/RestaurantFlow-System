import logging
from django.core.cache import cache

try:
    from redis.exceptions import RedisError
except ImportError:
    RedisError = Exception

logger = logging.getLogger('common.caching')

# Sentinel object: distinct from None (cache miss) and False
# Callers receiving CACHE_MISS_SENTINEL must recheck DB
CACHE_MISS_SENTINEL = object()


class CacheService:
    @staticmethod
    def get(key):
        """Get a value from cache. Returns None on Redis failure (graceful fallback)."""
        try:
            return cache.get(key)
        except RedisError as e:
            logger.warning("Cache GET failed for %s: %s", key, e)
            return None

    @staticmethod
    def set(key, value, ttl):
        """Set a value in cache. Silently continues on Redis failure."""
        try:
            cache.set(key, value, ttl)
        except RedisError as e:
            logger.warning("Cache SET failed for %s: %s", key, e)

    @staticmethod
    def delete(key):
        """Delete a key from cache. Silently continues on Redis failure."""
        try:
            cache.delete(key)
        except RedisError as e:
            logger.warning("Cache DELETE failed for %s: %s", key, e)

    @staticmethod
    def delete_pattern(pattern):
        """Delete all keys matching a pattern. Requires django-redis cache backend."""
        try:
            cache.delete_pattern(pattern)
        except (RedisError, AttributeError) as e:
            logger.warning("Cache DELETE_PATTERN failed for %s: %s", pattern, e)

    @staticmethod
    def get_or_set(key, callable_fn, ttl):
        """Get from cache or call callable_fn. Uses Redis lock to prevent stampede."""
        value = CacheService.get(key)
        if value is not None:
            return value

        lock_key = f"{key}:lock"
        acquired = False
        try:
            from django_redis import get_redis_connection
            redis_client = get_redis_connection("default")
            acquired = redis_client.set(lock_key, "1", nx=True, ex=10)
        except Exception:
            acquired = True  # fall through to DB on lock failure

        if not acquired:
            # Another caller holds the lock; re-read the cache before hitting the DB.
            cached = CacheService.get(key)
            if cached is not None:
                return cached
            # Cache is still empty (the lock holder hasn't written yet or failed).
            # Fall through and compute independently. The lock key remains owned by
            # the original acquirer and will expire via its 10-second TTL — this is
            # intentional: the non-acquiring caller never owns the lock and therefore
            # never cleans it up. The duplicate write is harmless (idempotent value)
            # and the lock expiry is bounded, so the next cold-cache caller within
            # that window may also fall through; this is acceptable for availability.

        try:
            value = callable_fn()
            from .policies import add_jitter
            CacheService.set(key, value, add_jitter(ttl))
        finally:
            if acquired:
                try:
                    CacheService.delete(lock_key)
                except Exception:
                    pass
        return value

    @staticmethod
    def get_secure(key):
        """For security-sensitive data: returns CACHE_MISS_SENTINEL on Redis failure.
        Callers must handle CACHE_MISS_SENTINEL by going directly to DB.
        This ensures Redis failure never silently grants or denies access.
        """
        try:
            return cache.get(key)
        except RedisError as e:
            logger.warning("Cache GET_SECURE failed for %s: %s", key, e)
            return CACHE_MISS_SENTINEL
