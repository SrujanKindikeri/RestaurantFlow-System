# =============================================================================
# RestaurantFlow — Configuration Resolver
# Phase 20
#
# SINGLE SOURCE OF TRUTH for effective configuration resolution.
#
# Resolution order (most-specific wins):
#   1. Branch override
#   2. Restaurant default
#   3. Company default
#   4. System default (from ALLOWED_CONFIGURATION_KEYS)
#
# NEVER duplicate this logic elsewhere in the codebase.
# Every module that needs an effective config value must call:
#
#   ConfigurationResolver.get_effective_value(branch=branch, key="billing.maximum_discount_percentage")
#
# Caching:
#   Redis is used for non-critical keys (TTL = CACHE_TTL_EFFECTIVE_CONFIG).
#   HIGH_IMPACT_CONFIG_KEYS always bypass cache and resolve directly from DB.
#   Cache is invalidated on every configuration mutation.
# =============================================================================

import logging
from typing import Any, Optional

from django.core.cache import cache

from enterprise.constants import (
    ALLOWED_CONFIGURATION_KEYS,
    CONFIG_SCOPE_BRANCH,
    CONFIG_SCOPE_RESTAURANT,
    CONFIG_SCOPE_COMPANY,
    CACHE_KEY_EFFECTIVE_CONFIG,
    CACHE_TTL_EFFECTIVE_CONFIG,
    CACHE_TTL_CRITICAL_CONFIG,
    HIGH_IMPACT_CONFIG_KEYS,
)
from enterprise.validators import cast_configuration_value
from enterprise.exceptions import ConfigurationKeyNotAllowedError

logger = logging.getLogger("enterprise")


class ConfigurationResolver:
    """
    Resolves effective configuration values using the company→restaurant→branch
    inheritance hierarchy.

    All methods are class methods — this is a stateless service object.
    """

    # ------------------------------------------------------------------
    # Primary public API
    # ------------------------------------------------------------------

    @classmethod
    def get_effective_value(
        cls,
        key: str,
        branch=None,
        restaurant=None,
        company=None,
        cast: bool = True,
    ) -> Any:
        """
        Resolve and return the effective value for `key` at the most-specific
        available scope.

        Provide at least one of: branch, restaurant, company.
        If branch is provided, restaurant and company are derived automatically.

        Args:
            key:        Allow-listed configuration key.
            branch:     Branch instance (most specific scope).
            restaurant: Restaurant instance (used if branch not provided).
            company:    Organization instance (broadest scope).
            cast:       If True, return the value as its declared Python type.
                        If False, return the raw string value.

        Returns:
            The effective value (typed if cast=True, string otherwise).

        Raises:
            ConfigurationKeyNotAllowedError: key is not in the allow-list.
        """
        if key not in ALLOWED_CONFIGURATION_KEYS:
            raise ConfigurationKeyNotAllowedError(
                f"Configuration key '{key}' is not in the allow-list."
            )

        # Derive missing scope objects from branch hierarchy
        if branch is not None:
            if restaurant is None:
                restaurant = branch.restaurant
            if company is None:
                company = restaurant.organization

        if restaurant is not None and company is None:
            company = restaurant.organization

        if company is None:
            # Nothing to resolve — return system default
            return cls._system_default(key, cast)

        # Check cache (skip for high-impact keys)
        is_high_impact = key in HIGH_IMPACT_CONFIG_KEYS
        cache_key = cls._build_cache_key(
            company_id=str(company.pk),
            restaurant_id=str(restaurant.pk) if restaurant else "null",
            branch_id=str(branch.pk) if branch else "null",
            key=key,
        )

        if not is_high_impact:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached if not cast else cached  # already cast before storage

        # DB resolution — most specific scope first
        raw_value = None
        value_type = ALLOWED_CONFIGURATION_KEYS[key]["type"]

        # 1. Branch scope
        if branch is not None:
            raw_value = cls._fetch_db_value(
                key=key,
                company=company,
                restaurant=restaurant,
                branch=branch,
            )

        # 2. Restaurant scope
        if raw_value is None and restaurant is not None:
            raw_value = cls._fetch_db_value(
                key=key,
                company=company,
                restaurant=restaurant,
                branch=None,
            )

        # 3. Company scope
        if raw_value is None:
            raw_value = cls._fetch_db_value(
                key=key,
                company=company,
                restaurant=None,
                branch=None,
            )

        # 4. System default
        if raw_value is None:
            raw_value = ALLOWED_CONFIGURATION_KEYS[key]["default"]
            logger.debug(
                "config_resolver: key=%s using system default=%s", key, raw_value
            )

        # Cast
        result = cast_configuration_value(raw_value, value_type) if cast else raw_value

        # Store in cache
        ttl = CACHE_TTL_CRITICAL_CONFIG if is_high_impact else CACHE_TTL_EFFECTIVE_CONFIG
        if ttl > 0:
            cache.set(cache_key, result, ttl)

        return result

    @classmethod
    def get_effective_config_with_source(
        cls,
        key: str,
        branch=None,
        restaurant=None,
        company=None,
    ) -> dict:
        """
        Return the effective value AND which scope it came from.

        Returns:
            {
                "key":    str,
                "value":  typed value,
                "source": "BRANCH" | "RESTAURANT" | "COMPANY" | "SYSTEM_DEFAULT",
                "is_overridden": bool,   # True if branch or restaurant level
            }
        """
        if key not in ALLOWED_CONFIGURATION_KEYS:
            raise ConfigurationKeyNotAllowedError(
                f"Configuration key '{key}' is not in the allow-list."
            )

        if branch is not None:
            if restaurant is None:
                restaurant = branch.restaurant
            if company is None:
                company = restaurant.organization
        if restaurant is not None and company is None:
            company = restaurant.organization

        value_type = ALLOWED_CONFIGURATION_KEYS[key]["type"]
        source = "SYSTEM_DEFAULT"
        raw_value = None

        if branch is not None and company is not None:
            raw_value = cls._fetch_db_value(key, company, restaurant, branch)
            if raw_value is not None:
                source = CONFIG_SCOPE_BRANCH

        if raw_value is None and restaurant is not None and company is not None:
            raw_value = cls._fetch_db_value(key, company, restaurant, None)
            if raw_value is not None:
                source = CONFIG_SCOPE_RESTAURANT

        if raw_value is None and company is not None:
            raw_value = cls._fetch_db_value(key, company, None, None)
            if raw_value is not None:
                source = CONFIG_SCOPE_COMPANY

        if raw_value is None:
            raw_value = ALLOWED_CONFIGURATION_KEYS[key]["default"]

        typed_value = cast_configuration_value(raw_value, value_type)

        return {
            "key": key,
            "value": typed_value,
            "raw_value": raw_value,
            "source": source,
            "is_overridden": source in {CONFIG_SCOPE_BRANCH, CONFIG_SCOPE_RESTAURANT},
            "description": ALLOWED_CONFIGURATION_KEYS[key]["description"],
            "value_type": value_type,
        }

    @classmethod
    def get_branch_configuration(cls, branch) -> dict:
        """
        Return the full effective configuration for a branch — all keys resolved.

        Returns:
            {key: {value, source, is_overridden, description, value_type}, ...}
        """
        restaurant = branch.restaurant
        company = restaurant.organization
        result = {}
        for key in ALLOWED_CONFIGURATION_KEYS:
            result[key] = cls.get_effective_config_with_source(
                key=key,
                branch=branch,
                restaurant=restaurant,
                company=company,
            )
        return result

    @classmethod
    def get_restaurant_configuration(cls, restaurant) -> dict:
        """
        Return effective configuration for a restaurant (no branch override).
        """
        company = restaurant.organization
        result = {}
        for key in ALLOWED_CONFIGURATION_KEYS:
            result[key] = cls.get_effective_config_with_source(
                key=key,
                restaurant=restaurant,
                company=company,
            )
        return result

    @classmethod
    def get_company_configuration(cls, company) -> dict:
        """
        Return effective configuration at the company scope only.
        """
        result = {}
        for key in ALLOWED_CONFIGURATION_KEYS:
            result[key] = cls.get_effective_config_with_source(
                key=key,
                company=company,
            )
        return result

    @classmethod
    def resolve(
        cls,
        key: str,
        branch=None,
        restaurant=None,
        company=None,
    ) -> Any:
        """
        Alias for get_effective_value — kept for backward-compatibility.
        """
        return cls.get_effective_value(
            key=key,
            branch=branch,
            restaurant=restaurant,
            company=company,
        )

    # ------------------------------------------------------------------
    # Cache invalidation
    # ------------------------------------------------------------------

    @classmethod
    def invalidate_cache_for_config(cls, config) -> None:
        """
        Invalidate all cache entries that could be affected by `config`.

        When a branch config changes, we must also invalidate:
            - The branch-scope key
            - The restaurant-scope key (upstream consumers might have cached it)
            - The company-scope key

        Uses Django's cache delete_many for efficiency.
        """
        company = config.company
        restaurant = config.restaurant
        branch = config.branch
        key = config.configuration_key

        keys_to_delete = []

        # Company-level cache
        keys_to_delete.append(
            cls._build_cache_key(str(company.pk), "null", "null", key)
        )

        # Restaurant-level cache
        if restaurant:
            keys_to_delete.append(
                cls._build_cache_key(str(company.pk), str(restaurant.pk), "null", key)
            )
            # Also invalidate branch-level caches for all branches in the restaurant
            # This is a broad invalidation — acceptable for configuration mutations
            # which are infrequent.
            for b in restaurant.branches.values_list("pk", flat=True):
                keys_to_delete.append(
                    cls._build_cache_key(str(company.pk), str(restaurant.pk), str(b), key)
                )

        # Branch-level cache
        if branch:
            keys_to_delete.append(
                cls._build_cache_key(
                    str(company.pk),
                    str(branch.restaurant_id),
                    str(branch.pk),
                    key,
                )
            )

        if keys_to_delete:
            cache.delete_many(keys_to_delete)
            logger.debug(
                "config_resolver: invalidated %d cache key(s) for config key=%s",
                len(keys_to_delete),
                key,
            )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @classmethod
    def _fetch_db_value(
        cls,
        key: str,
        company,
        restaurant,
        branch,
    ) -> Optional[str]:
        """
        Fetch the raw string value from DB for the exact scope combination.
        Returns None if no record exists.
        """
        from enterprise.models import EnterpriseConfiguration

        try:
            config = EnterpriseConfiguration.objects.get(
                company=company,
                restaurant=restaurant,
                branch=branch,
                configuration_key=key,
                is_active=True,
            )
            return config.configuration_value
        except EnterpriseConfiguration.DoesNotExist:
            return None
        except EnterpriseConfiguration.MultipleObjectsReturned:
            # This should never happen due to UniqueConstraints, but handle defensively
            logger.error(
                "config_resolver: multiple active configs for key=%s company=%s rest=%s branch=%s — "
                "returning first. This is a data integrity issue.",
                key,
                company.pk,
                restaurant.pk if restaurant else None,
                branch.pk if branch else None,
            )
            return (
                EnterpriseConfiguration.objects.filter(
                    company=company,
                    restaurant=restaurant,
                    branch=branch,
                    configuration_key=key,
                    is_active=True,
                )
                .order_by("-updated_at")
                .first()
                .configuration_value
            )

    @classmethod
    def _system_default(cls, key: str, cast: bool = True) -> Any:
        """Return the system-level default value for a key."""
        raw = ALLOWED_CONFIGURATION_KEYS[key]["default"]
        if not cast:
            return raw
        return cast_configuration_value(raw, ALLOWED_CONFIGURATION_KEYS[key]["type"])

    @classmethod
    def _build_cache_key(
        cls,
        company_id: str,
        restaurant_id: str,
        branch_id: str,
        key: str,
    ) -> str:
        return CACHE_KEY_EFFECTIVE_CONFIG.format(
            company_id=company_id,
            restaurant_id=restaurant_id,
            branch_id=branch_id,
            key=key,
        )
