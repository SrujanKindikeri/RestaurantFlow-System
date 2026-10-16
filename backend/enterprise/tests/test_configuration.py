# =============================================================================
# RestaurantFlow — Enterprise Configuration Tests
# Phase 20
#
# Tests:
#   - Company defaults
#   - Restaurant overrides
#   - Branch overrides
#   - Fallback resolution (branch → restaurant → company → system default)
#   - Configuration history immutability
#   - Invalid configuration values
#   - Invalid configuration keys
#   - Duplicate active config rejection
#   - Configuration rollback
# =============================================================================

from decimal import Decimal
from django.test import TestCase
from rest_framework.exceptions import ValidationError, PermissionDenied

from enterprise.tests.base import EnterpriseTestBase
from enterprise.configuration_resolver import ConfigurationResolver
from enterprise.services import set_configuration, rollback_configuration
from enterprise.models import EnterpriseConfiguration, ConfigurationChange
from enterprise.validators import validate_configuration_key, validate_configuration_value
from enterprise.exceptions import ConfigurationKeyNotAllowedError, ConfigurationValueTypeError
from enterprise.constants import (
    VALUE_TYPE_BOOLEAN, VALUE_TYPE_DECIMAL, VALUE_TYPE_INTEGER,
    VALUE_TYPE_STRING, VALUE_TYPE_JSON,
    CONFIG_SCOPE_COMPANY, CONFIG_SCOPE_RESTAURANT, CONFIG_SCOPE_BRANCH,
)


class TestConfigurationValidators(TestCase):

    def test_allowed_key_passes(self):
        """A key from the allow-list should not raise."""
        validate_configuration_key("billing.maximum_discount_percentage")

    def test_unknown_key_raises(self):
        """A key not in the allow-list must raise ConfigurationKeyNotAllowedError."""
        with self.assertRaises(ConfigurationKeyNotAllowedError):
            validate_configuration_key("arbitrary.unknown.key")

    def test_boolean_valid_values(self):
        for v in ["true", "false", "1", "0", "yes", "no"]:
            validate_configuration_value(v, VALUE_TYPE_BOOLEAN)

    def test_boolean_invalid_value(self):
        with self.assertRaises(ConfigurationValueTypeError):
            validate_configuration_value("maybe", VALUE_TYPE_BOOLEAN)

    def test_decimal_valid(self):
        validate_configuration_value("10.50", VALUE_TYPE_DECIMAL)

    def test_decimal_invalid(self):
        with self.assertRaises(ConfigurationValueTypeError):
            validate_configuration_value("not_a_number", VALUE_TYPE_DECIMAL)

    def test_integer_valid(self):
        validate_configuration_value("42", VALUE_TYPE_INTEGER)

    def test_integer_invalid(self):
        with self.assertRaises(ConfigurationValueTypeError):
            validate_configuration_value("3.14", VALUE_TYPE_INTEGER)

    def test_json_valid(self):
        validate_configuration_value('{"key": "value"}', VALUE_TYPE_JSON)

    def test_json_invalid(self):
        with self.assertRaises(ConfigurationValueTypeError):
            validate_configuration_value("{not valid json", VALUE_TYPE_JSON)

    def test_string_always_valid(self):
        validate_configuration_value("any string value at all", VALUE_TYPE_STRING)


class TestConfigurationResolution(EnterpriseTestBase):

    def test_system_default_when_no_config_set(self):
        """Should return system default when no DB record exists."""
        val = ConfigurationResolver.get_effective_value(
            key="billing.allow_discount",
            company=self.org,
        )
        # System default is "true" → cast to True
        self.assertTrue(val)

    def test_company_default_returned_for_branch(self):
        """Company-level config should propagate to branch with no override."""
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="20.00",
            user=self.company_head,
            reason="company default",
        )
        val = ConfigurationResolver.get_effective_value(
            key="billing.maximum_discount_percentage",
            branch=self.branch_a1,
        )
        self.assertEqual(val, Decimal("20.00"))

    def test_restaurant_override_wins_over_company(self):
        """Restaurant-level config should win over company-level."""
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="10.00",
            user=self.company_head,
        )
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="15.00",
            user=self.restaurant_owner,
            restaurant=self.restaurant_a,
        )
        val = ConfigurationResolver.get_effective_value(
            key="billing.maximum_discount_percentage",
            restaurant=self.restaurant_a,
            company=self.org,
        )
        self.assertEqual(val, Decimal("15.00"))

    def test_branch_override_wins_over_restaurant(self):
        """Branch-level override must take precedence over restaurant default."""
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="10.00",
            user=self.company_head,
        )
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="15.00",
            user=self.restaurant_owner,
            restaurant=self.restaurant_a,
        )
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="25.00",
            user=self.branch_manager,
            restaurant=self.restaurant_a,
            branch=self.branch_a1,
        )
        val = ConfigurationResolver.get_effective_value(
            key="billing.maximum_discount_percentage",
            branch=self.branch_a1,
        )
        self.assertEqual(val, Decimal("25.00"))

    def test_branch_without_override_falls_back_to_restaurant(self):
        """Branch A2 has no override → should get restaurant default."""
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="5.00",
            user=self.company_head,
        )
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="12.00",
            user=self.restaurant_owner,
            restaurant=self.restaurant_a,
        )
        # Only branch_a1 gets a branch override
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="20.00",
            user=self.branch_manager,
            restaurant=self.restaurant_a,
            branch=self.branch_a1,
        )
        # branch_a2 → no branch config → should fall back to restaurant → 12%
        val_a2 = ConfigurationResolver.get_effective_value(
            key="billing.maximum_discount_percentage",
            branch=self.branch_a2,
        )
        self.assertEqual(val_a2, Decimal("12.00"))

    def test_get_effective_config_with_source_branch(self):
        """get_effective_config_with_source should report BRANCH scope when branch has override."""
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="false",
            user=self.branch_manager,
            restaurant=self.restaurant_a,
            branch=self.branch_a1,
        )
        result = ConfigurationResolver.get_effective_config_with_source(
            key="billing.allow_discount",
            branch=self.branch_a1,
        )
        self.assertEqual(result["source"], CONFIG_SCOPE_BRANCH)
        self.assertTrue(result["is_overridden"])

    def test_get_effective_config_with_source_system_default(self):
        """When no config exists at any level, source should be SYSTEM_DEFAULT."""
        result = ConfigurationResolver.get_effective_config_with_source(
            key="customer.loyalty_enabled",
            branch=self.branch_a1,
        )
        self.assertEqual(result["source"], "SYSTEM_DEFAULT")
        self.assertFalse(result["is_overridden"])

    def test_get_branch_configuration_returns_all_keys(self):
        """get_branch_configuration should return a dict with all allow-listed keys."""
        from enterprise.constants import ALLOWED_CONFIGURATION_KEYS
        result = ConfigurationResolver.get_branch_configuration(self.branch_a1)
        self.assertEqual(set(result.keys()), set(ALLOWED_CONFIGURATION_KEYS.keys()))


class TestConfigurationService(EnterpriseTestBase):

    def test_set_config_creates_history(self):
        """Every set_configuration call should create a ConfigurationChange row."""
        initial_count = ConfigurationChange.objects.count()
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="18.00",
            user=self.company_head,
            reason="test reason",
        )
        self.assertEqual(ConfigurationChange.objects.count(), initial_count + 1)

    def test_set_config_deactivates_old_and_creates_new(self):
        """Updating a config key must deactivate the old record and create a new versioned one."""
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="10.00",
            user=self.company_head,
        )
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="15.00",
            user=self.company_head,
        )
        active = EnterpriseConfiguration.objects.filter(
            company=self.org,
            restaurant=None,
            branch=None,
            configuration_key="billing.maximum_discount_percentage",
            is_active=True,
        )
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.first().configuration_value, "15.00")
        self.assertEqual(active.first().version, 2)

    def test_set_config_invalid_key_raises(self):
        with self.assertRaises(ValidationError):
            set_configuration(
                company=self.org,
                key="hacker.arbitrary_key",
                value="bad",
                user=self.company_head,
            )

    def test_set_config_invalid_value_raises(self):
        with self.assertRaises(ValidationError):
            set_configuration(
                company=self.org,
                key="billing.maximum_discount_percentage",
                value="not_a_decimal",
                user=self.company_head,
            )

    def test_set_config_wrong_user_raises_permission_denied(self):
        """A user without enterprise.configuration.create permission must be denied."""
        with self.assertRaises(PermissionDenied):
            set_configuration(
                company=self.org,
                key="billing.allow_discount",
                value="true",
                user=self.cashier,  # cashier has no enterprise perms
            )

    def test_configuration_history_immutable(self):
        """ConfigurationChange rows must raise ValueError on update."""
        set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="true",
            user=self.company_head,
        )
        change = ConfigurationChange.objects.first()
        change.change_reason = "TAMPERED"
        with self.assertRaises(ValueError):
            change.save()

    def test_rollback_configuration(self):
        """Rollback should restore the previous value."""
        set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="10.00",
            user=self.company_head,
        )
        config = set_configuration(
            company=self.org,
            key="billing.maximum_discount_percentage",
            value="20.00",
            user=self.company_head,
        )
        restored = rollback_configuration(config, self.company_head, reason="rollback test")
        self.assertEqual(restored.configuration_value, "10.00")

    def test_rollback_with_no_history_raises(self):
        """Rollback on a brand-new config (no previous version) must raise ValidationError."""
        config = set_configuration(
            company=self.org,
            key="billing.allow_discount",
            value="true",
            user=self.company_head,
        )
        with self.assertRaises(ValidationError):
            rollback_configuration(config, self.company_head)
