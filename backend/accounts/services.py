# =============================================================================
# RestaurantFlow — Account Services
# Phase 3
#
# Centralised business-logic operations that span multiple models.
# Views should call these rather than duplicating logic inline.
#
# Services:
#   create_user(actor, data)              → User
#   disable_user(actor, user)             → User
#   reactivate_user(actor, user)          → User
#   assign_role(actor, user, role, ...)   → UserRoleAssignment
#   remove_role_assignment(actor, assignment) → UserRoleAssignment
# =============================================================================

import logging
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from core.security import record_security_event, revoke_user_sessions

logger = logging.getLogger("accounts")

# ---------------------------------------------------------------------------
# User creation
# ---------------------------------------------------------------------------

def create_user(actor, *, email, first_name, last_name, phone="", password, **extra):
    """
    Create a new user on behalf of `actor`.

    Security rules enforced here:
    - `is_superuser` and `is_staff` can NEVER be set via this service
      unless the actor is a superuser.
    - Actors without org-admin privileges cannot create users at all.
    """
    from accounts.models import User
    from accounts.access import can_assign_role

    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("Authentication required.")

    # Strip escalation fields unconditionally
    extra.pop("is_superuser", None)
    extra.pop("is_staff", None)

    # Only org admins or superusers may create users
    if not (actor.is_superuser or actor.is_staff or _is_org_admin(actor)):
        raise PermissionDenied("You do not have permission to create users.")

    with transaction.atomic():
        user = User.objects.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            password=password,
            **extra,
        )
        logger.info(
            "User created: email=%s by actor=%s",
            user.email,
            actor.email,
        )
        record_security_event(
            event="user_created",
            actor=actor,
            target_user=user,
            metadata={"email": user.email},
        )
    return user


# ---------------------------------------------------------------------------
# User disable / reactivate
# ---------------------------------------------------------------------------

def disable_user(actor, user):
    """
    Soft-disable a user.  actor must have authority over the user.
    Superusers cannot be disabled via this service.

    After disabling, all active JWT refresh tokens are revoked to prevent
    continued access with a disabled account.
    """
    from accounts.access import can_manage_user

    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("Authentication required.")

    if user.is_superuser:
        raise PermissionDenied("Superuser accounts cannot be disabled via the API.")

    if not (actor.is_superuser or actor.is_staff or can_manage_user(actor, user)):
        raise PermissionDenied("You do not have permission to disable this user.")

    if actor.pk == user.pk:
        raise ValidationError("You cannot disable your own account.")

    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    logger.warning("User disabled: email=%s by actor=%s", user.email, actor.email)

    # Revoke all active sessions for the disabled user
    revoked_count = revoke_user_sessions(user)

    record_security_event(
        event="account_disabled",
        actor=actor,
        target_user=user,
        metadata={"sessions_revoked": revoked_count},
    )

    return user


def reactivate_user(actor, user):
    """Reactivate a previously disabled user."""
    from accounts.access import can_manage_user

    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("Authentication required.")

    if not (actor.is_superuser or actor.is_staff or can_manage_user(actor, user)):
        raise PermissionDenied("You do not have permission to reactivate this user.")

    user.is_active = True
    user.save(update_fields=["is_active", "updated_at"])
    logger.info("User reactivated: email=%s by actor=%s", user.email, actor.email)

    record_security_event(
        event="account_reactivated",
        actor=actor,
        target_user=user,
    )

    return user


# ---------------------------------------------------------------------------
# Role assignment
# ---------------------------------------------------------------------------

def assign_role(actor, *, user, role, organization=None, restaurant=None, branch=None):
    """
    Create a UserRoleAssignment, enforcing privilege-escalation rules.

    The assignment model's clean() handles hierarchy validation (branch belongs
    to restaurant, restaurant belongs to org, etc.).
    """
    from accounts.models import UserRoleAssignment
    from accounts.access import can_assign_role

    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("Authentication required.")

    if not can_assign_role(
        actor,
        role,
        organization=organization,
        restaurant=restaurant,
        branch=branch,
    ):
        raise PermissionDenied(
            f"You do not have permission to assign the '{role.code}' role."
        )

    with transaction.atomic():
        assignment = UserRoleAssignment(
            user=user,
            role=role,
            organization=organization,
            restaurant=restaurant,
            branch=branch,
            is_active=True,
        )
        assignment.full_clean()   # triggers scope validation
        assignment.save()

    logger.info(
        "Role assigned: user=%s role=%s by actor=%s",
        user.email,
        role.code,
        actor.email,
    )
    record_security_event(
        event="role_assigned",
        actor=actor,
        target_user=user,
        metadata={
            "role_code": role.code,
            "organization_id": str(organization.pk) if organization else None,
            "restaurant_id": str(restaurant.pk) if restaurant else None,
            "branch_id": str(branch.pk) if branch else None,
        },
        organization=organization,
    )
    return assignment


def remove_role_assignment(actor, assignment):
    """Soft-disable (deactivate) a role assignment."""
    from accounts.access import can_manage_user

    if not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("Authentication required.")

    if not (
        actor.is_superuser
        or actor.is_staff
        or can_manage_user(actor, assignment.user)
    ):
        raise PermissionDenied(
            "You do not have permission to remove this role assignment."
        )

    assignment.is_active = False
    assignment.save(update_fields=["is_active", "updated_at"])
    logger.info(
        "Role assignment deactivated: id=%s user=%s role=%s by actor=%s",
        assignment.pk,
        assignment.user.email,
        assignment.role.code,
        actor.email,
    )
    record_security_event(
        event="role_revoked",
        actor=actor,
        target_user=assignment.user,
        metadata={
            "role_code": assignment.role.code,
            "assignment_id": str(assignment.pk),
        },
        organization=assignment.organization,
    )
    return assignment


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_org_admin(user) -> bool:
    """Return True if user holds any org-admin role."""
    from accounts.models import Role
    return user.role_assignments.filter(
        is_active=True,
        role__code__in=[Role.CODE_COMPANY_HEAD, Role.CODE_CENTRAL_ADMIN],
        role__is_active=True,
    ).exists()
