# =============================================================================
# RestaurantFlow — Enterprise Configuration Services
# Phase 20
#
# Business logic for EnterpriseConfiguration CRUD operations.
# All read operations live in selectors.py.
# Cache invalidation is handled here after every mutation.
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from enterprise.configuration_resolver import ConfigurationResolver
from enterprise.constants import (
    ALLOWED_CONFIGURATION_KEYS,
    CONFIG_SCOPE_BRANCH,
    CONFIG_SCOPE_RESTAURANT,
    CONFIG_SCOPE_COMPANY,
    PERM_CONFIG_CREATE,
    PERM_CONFIG_UPDATE,
    AUDIT_CONFIG_CREATED,
    AUDIT_CONFIG_UPDATED,
    AUDIT_CONFIG_ROLLED_BACK,
    WS_CONFIG_UPDATED,
)
from enterprise.exceptions import (
    ConfigurationKeyNotAllowedError,
    ConfigurationValueTypeError,
    ConfigurationConflictError,
)
from enterprise.models import EnterpriseConfiguration, ConfigurationChange
from enterprise.validators import (
    validate_configuration_key,
    validate_configuration_value,
)
from enterprise.audit_services import record_audit

logger = logging.getLogger("enterprise")


def _require_auth(user):
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Authentication required.")


# ---------------------------------------------------------------------------
# Create or update a configuration entry
# ---------------------------------------------------------------------------

def set_configuration(
    company,
    key: str,
    value: str,
    user,
    restaurant=None,
    branch=None,
    reason: str = "",
) -> EnterpriseConfiguration:
    """
    Create or update an EnterpriseConfiguration entry.

    If an active entry already exists at the same scope, it is deactivated
    and replaced with a new versioned entry (preserving history).

    Permissions: enterprise.configuration.create / enterprise.configuration.update
    Scope:       User must have access to the company/restaurant/branch scope.

    Returns:
        The new (or updated) EnterpriseConfiguration instance.
    """
    _require_auth(user)

    # Permission — create vs update
    perm = PERM_CONFIG_UPDATE if _has_existing_config(company, key, restaurant, branch) else PERM_CONFIG_CREATE
    if not acl.has_permission(user, perm):
        raise PermissionDenied(f"You do not have the required permission: {perm}")

    # Scope access checks
    if branch and not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")
    elif restaurant and not acl.can_access_restaurant(user, restaurant):
        raise PermissionDenied("You do not have access to this restaurant.")
    elif not acl.can_access_organization(user, company):
        raise PermissionDenied("You do not have access to this company.")

    # Validate key + value
    try:
        validate_configuration_key(key)
    except ConfigurationKeyNotAllowedError as exc:
        raise ValidationError({"code": exc.code, "message": exc.message})

    value_type = ALLOWED_CONFIGURATION_KEYS[key]["type"]
    try:
        validate_configuration_value(value, value_type)
    except ConfigurationValueTypeError as exc:
        raise ValidationError({"code": exc.code, "message": exc.message})

    with transaction.atomic():
        # Find and deactivate any existing active config at this exact scope
        existing_qs = EnterpriseConfiguration.objects.select_for_update().filter(
            company=company,
            restaurant=restaurant,
            branch=branch,
            configuration_key=key,
            is_active=True,
        )
        existing = existing_qs.first()
        old_value = existing.configuration_value if existing else ""
        next_version = (existing.version + 1) if existing else 1

        if existing:
            existing.is_active = False
            existing.updated_by = user
            existing.save(update_fields=["is_active", "updated_by", "updated_at"])

        # Create new active entry
        config = EnterpriseConfiguration.objects.create(
            company=company,
            restaurant=restaurant,
            branch=branch,
            configuration_key=key,
            configuration_value=value,
            value_type=value_type,
            is_active=True,
            version=next_version,
            created_by=user,
            updated_by=user,
        )

        # Record history
        scope = _get_scope(restaurant, branch)
        ConfigurationChange.objects.create(
            company=company,
            restaurant=restaurant,
            branch=branch,
            configuration_key=key,
            old_value=old_value,
            new_value=value,
            version=next_version,
            changed_by=user,
            change_reason=reason,
            scope=scope,
        )

    # Invalidate cache after commit
    ConfigurationResolver.invalidate_cache_for_config(config)

    # Invalidate branch config cache in the common caching layer
    if branch:
        from common.caching.invalidation import invalidate_branch_config
        invalidate_branch_config(str(branch.pk))

    audit_action = AUDIT_CONFIG_UPDATED if old_value else AUDIT_CONFIG_CREATED
    record_audit(
        action=audit_action,
        company=company,
        restaurant=restaurant,
        branch=branch,
        performed_by=user,
        description=f"Configuration '{key}' set to '{value}'.",
        source_type="EnterpriseConfiguration",
        source_id=str(config.pk),
        metadata={"key": key, "old_value": old_value, "new_value": value, "reason": reason},
    )

    _publish_ws_config(config)
    logger.info(
        "enterprise_services: config set key=%s scope=%s/%s/%s by=%s",
        key,
        company.pk,
        restaurant.pk if restaurant else None,
        branch.pk if branch else None,
        user.email,
    )
    return config


# ---------------------------------------------------------------------------
# Rollback configuration to previous version
# ---------------------------------------------------------------------------

def rollback_configuration(config, user, reason: str = "") -> EnterpriseConfiguration:
    """
    Rollback an EnterpriseConfiguration to the previous version's value.

    Finds the most recent ConfigurationChange for this scope and reverts to
    its old_value. Creates a new history entry for the rollback.

    Permissions: enterprise.configuration.update
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_CONFIG_UPDATE):
        raise PermissionDenied("You do not have permission to update configuration.")

    previous_change = (
        ConfigurationChange.objects.filter(
            company=config.company,
            restaurant=config.restaurant,
            branch=config.branch,
            configuration_key=config.configuration_key,
        )
        .order_by("-created_at")
        .first()
    )

    if not previous_change or not previous_change.old_value:
        raise ValidationError({
            "code": "CONFIG_NO_PREVIOUS_VERSION",
            "message": "No previous version to roll back to.",
        })

    # Re-use set_configuration to handle versioning + history correctly
    restored = set_configuration(
        company=config.company,
        key=config.configuration_key,
        value=previous_change.old_value,
        user=user,
        restaurant=config.restaurant,
        branch=config.branch,
        reason=reason or f"Rolled back from v{config.version} to v{previous_change.version}",
    )

    record_audit(
        action=AUDIT_CONFIG_ROLLED_BACK,
        company=config.company,
        restaurant=config.restaurant,
        branch=config.branch,
        performed_by=user,
        description=(
            f"Configuration '{config.configuration_key}' rolled back "
            f"from '{config.configuration_value}' to '{previous_change.old_value}'."
        ),
        source_type="EnterpriseConfiguration",
        source_id=str(restored.pk),
        metadata={
            "rolled_back_from": config.configuration_value,
            "rolled_back_to": previous_change.old_value,
        },
    )
    return restored


# ---------------------------------------------------------------------------
# Approval policy CRUD
# ---------------------------------------------------------------------------

def create_approval_policy(
    company,
    policy_type: str,
    required_permission: str,
    user,
    restaurant=None,
    branch=None,
    threshold_amount=None,
    threshold_percentage=None,
    required_role=None,
) -> "ApprovalPolicy":
    """
    Create an ApprovalPolicy at the given scope.

    Permissions: enterprise.approval_policy.manage
    """
    from enterprise.constants import PERM_APPROVAL_POLICY_MANAGE, AUDIT_APPROVAL_POLICY_CREATED
    from enterprise.models import ApprovalPolicy

    _require_auth(user)
    if not acl.has_permission(user, PERM_APPROVAL_POLICY_MANAGE):
        raise PermissionDenied("You do not have permission to manage approval policies.")

    if branch and not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")
    elif restaurant and not acl.can_access_restaurant(user, restaurant):
        raise PermissionDenied("You do not have access to this restaurant.")

    with transaction.atomic():
        policy = ApprovalPolicy.objects.create(
            company=company,
            restaurant=restaurant,
            branch=branch,
            policy_type=policy_type,
            threshold_amount=threshold_amount,
            threshold_percentage=threshold_percentage,
            required_permission=required_permission,
            required_role=required_role,
            is_active=True,
            created_by=user,
            updated_by=user,
        )

    record_audit(
        action=AUDIT_APPROVAL_POLICY_CREATED,
        company=company,
        restaurant=restaurant,
        branch=branch,
        performed_by=user,
        description=f"Approval policy created: {policy_type}.",
        source_type="ApprovalPolicy",
        source_id=str(policy.pk),
        metadata={"policy_type": policy_type, "required_permission": required_permission},
    )
    return policy


def update_approval_policy(policy, user, **kwargs) -> "ApprovalPolicy":
    """
    Update fields on an existing ApprovalPolicy.

    Permissions: enterprise.approval_policy.manage
    """
    from enterprise.constants import PERM_APPROVAL_POLICY_MANAGE, AUDIT_APPROVAL_POLICY_UPDATED

    _require_auth(user)
    if not acl.has_permission(user, PERM_APPROVAL_POLICY_MANAGE):
        raise PermissionDenied("You do not have permission to manage approval policies.")

    allowed_fields = {
        "threshold_amount", "threshold_percentage",
        "required_permission", "required_role", "is_active"
    }
    update_fields = []
    for field, val in kwargs.items():
        if field in allowed_fields:
            setattr(policy, field, val)
            update_fields.append(field)

    policy.updated_by = user
    update_fields.extend(["updated_by", "updated_at"])

    with transaction.atomic():
        locked = type(policy).objects.select_for_update().get(pk=policy.pk)
        for field in update_fields:
            setattr(locked, field, getattr(policy, field))
        locked.save(update_fields=update_fields)

    record_audit(
        action=AUDIT_APPROVAL_POLICY_UPDATED,
        company=policy.company,
        restaurant=policy.restaurant,
        branch=policy.branch,
        performed_by=user,
        description=f"Approval policy updated: {policy.policy_type}.",
        source_type="ApprovalPolicy",
        source_id=str(policy.pk),
        metadata={"updated_fields": list(kwargs.keys())},
    )
    return locked


# ---------------------------------------------------------------------------
# Bulk configuration rollout
# ---------------------------------------------------------------------------

def bulk_set_configurations(
    company,
    configs: list,
    user,
    restaurant=None,
    branch=None,
    reason: str = "",
) -> dict:
    """
    Apply multiple configuration keys in one call.

    configs: list of {key, value} dicts

    Returns:
        {successful: [...], failed: [...], skipped: [], warnings: []}
    """
    result = {"successful": [], "failed": [], "skipped": [], "warnings": []}

    for entry in configs:
        key = entry.get("key")
        value = entry.get("value")
        if not key or value is None:
            result["failed"].append({"key": key, "error": "Missing key or value."})
            continue
        try:
            config = set_configuration(
                company=company,
                key=key,
                value=str(value),
                user=user,
                restaurant=restaurant,
                branch=branch,
                reason=reason,
            )
            result["successful"].append({"key": key, "config_id": str(config.pk)})
        except Exception as exc:
            result["failed"].append({"key": key, "error": str(exc)})
            logger.warning("bulk_set_config: key=%s failed — %s", key, exc)

    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _has_existing_config(company, key, restaurant, branch) -> bool:
    return EnterpriseConfiguration.objects.filter(
        company=company,
        restaurant=restaurant,
        branch=branch,
        configuration_key=key,
        is_active=True,
    ).exists()


def _get_scope(restaurant, branch) -> str:
    if branch:
        return CONFIG_SCOPE_BRANCH
    if restaurant:
        return CONFIG_SCOPE_RESTAURANT
    return CONFIG_SCOPE_COMPANY


def _publish_ws_config(config) -> None:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        group = f"enterprise_org_{config.company_id}"
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "enterprise_event",
                "event": WS_CONFIG_UPDATED,
                "payload": {
                    "key": config.configuration_key,
                    "scope": config.scope,
                    "branch_id": str(config.branch_id) if config.branch_id else None,
                },
            },
        )
    except Exception as exc:
        logger.warning("enterprise_services: WS publish failed (non-fatal): %s", exc)
