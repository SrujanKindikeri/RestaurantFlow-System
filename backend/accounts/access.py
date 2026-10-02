# =============================================================================
# RestaurantFlow — Access Control Service
# Phase 3
#
# This module is the single source of truth for authorization decisions.
# Views, serializers, and other modules should use these functions rather
# than duplicating access-logic.
#
# Public API:
#   has_permission(user, code)                  → bool
#   get_accessible_organizations(user)          → QuerySet[Organization]
#   get_accessible_restaurants(user)            → QuerySet[Restaurant]
#   get_accessible_branches(user)               → QuerySet[Branch]
#   can_access_organization(user, org)          → bool
#   can_access_restaurant(user, restaurant)     → bool
#   can_access_branch(user, branch)             → bool
#   get_user_scope_summary(user)                → dict
# =============================================================================

import logging
from django.db.models import Q

logger = logging.getLogger("accounts")


# ---------------------------------------------------------------------------
# Permission check
# ---------------------------------------------------------------------------

def has_permission(user, code: str) -> bool:
    """
    Check if a user holds a specific permission code.

    Superusers pass all checks.
    Inactive users always fail.
    Permission is granted if any of the user's active role assignments
    include a role that holds the specified permission code.
    """
    if not user or not user.is_authenticated:
        return False
    if not user.is_active:
        return False
    return user.has_perm_code(code)


# ---------------------------------------------------------------------------
# Queryset scoping — used by organization views
# ---------------------------------------------------------------------------

def get_accessible_organizations(user):
    """
    Return the set of Organizations this user is authorized to see.

    - Superuser / staff  → all organizations
    - COMPANY_HEAD / CENTRAL_ADMIN → their assigned organizations
    - Restaurant/branch roles → the organizations via their restaurant scope
    """
    from organizations.models import Organization

    if not user or not user.is_authenticated or not user.is_active:
        return Organization.objects.none()

    if user.is_superuser or user.is_staff:
        return Organization.objects.all()

    # Collect organization IDs from all active assignments
    org_ids = set()
    for assignment in user.get_active_assignments():
        if assignment.organization_id:
            org_ids.add(assignment.organization_id)

    return Organization.objects.filter(pk__in=org_ids)


def get_accessible_restaurants(user):
    """
    Return the set of Restaurants this user is authorized to see.

    - Superuser / staff       → all restaurants
    - COMPANY_HEAD            → all restaurants in their org(s)
    - CENTRAL_ADMIN           → all restaurants in their org(s)
    - RESTAURANT_OWNER        → their assigned restaurant(s)
    - Branch-level roles      → the restaurant of their assigned branch(es)
    """
    from organizations.models import Restaurant
    from accounts.models import Role

    if not user or not user.is_authenticated or not user.is_active:
        return Restaurant.objects.none()

    if user.is_superuser or user.is_staff:
        return Restaurant.objects.all()

    restaurant_ids = set()
    org_ids_full_access = set()  # org-scope roles can see all restaurants in that org

    for assignment in user.get_active_assignments():
        role = assignment.role
        if not role.is_active:
            continue

        if role.scope == Role.SCOPE_ORGANIZATION:
            # Org-level roles see all restaurants in the org
            if assignment.organization_id:
                org_ids_full_access.add(assignment.organization_id)
        elif role.scope in (Role.SCOPE_RESTAURANT, Role.SCOPE_BRANCH):
            if assignment.restaurant_id:
                restaurant_ids.add(assignment.restaurant_id)

    qs = Restaurant.objects.filter(
        Q(pk__in=restaurant_ids) |
        Q(organization_id__in=org_ids_full_access)
    )
    return qs.distinct()


def get_accessible_branches(user):
    """
    Return the set of Branches this user is authorized to see.

    - Superuser / staff       → all branches
    - COMPANY_HEAD            → all branches in their org(s)
    - CENTRAL_ADMIN           → all branches in their org(s)
    - RESTAURANT_OWNER        → all branches in their restaurant(s)
    - Branch-level roles      → their specifically assigned branch(es)
    """
    from organizations.models import Branch
    from accounts.models import Role

    if not user or not user.is_authenticated or not user.is_active:
        return Branch.objects.none()

    if user.is_superuser or user.is_staff:
        return Branch.objects.all()

    branch_ids = set()
    restaurant_ids_full_access = set()
    org_ids_full_access = set()

    for assignment in user.get_active_assignments():
        role = assignment.role
        if not role.is_active:
            continue

        if role.scope == Role.SCOPE_ORGANIZATION:
            if assignment.organization_id:
                org_ids_full_access.add(assignment.organization_id)
        elif role.scope == Role.SCOPE_RESTAURANT:
            if assignment.restaurant_id:
                restaurant_ids_full_access.add(assignment.restaurant_id)
        elif role.scope == Role.SCOPE_BRANCH:
            if assignment.branch_id:
                branch_ids.add(assignment.branch_id)
            elif assignment.restaurant_id:
                # Branch-role without specific branch → all branches in restaurant
                restaurant_ids_full_access.add(assignment.restaurant_id)

    qs = Branch.objects.filter(
        Q(pk__in=branch_ids) |
        Q(restaurant_id__in=restaurant_ids_full_access) |
        Q(restaurant__organization_id__in=org_ids_full_access)
    )
    return qs.distinct()


# ---------------------------------------------------------------------------
# Resource-level access checks
# ---------------------------------------------------------------------------

def can_access_organization(user, organization) -> bool:
    """
    Return True if `user` is allowed to access `organization`.

    Never trust the caller — always derive from stored assignments.
    """
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    accessible = get_accessible_organizations(user)
    return accessible.filter(pk=organization.pk).exists()


def can_access_restaurant(user, restaurant) -> bool:
    """Return True if `user` can access `restaurant`."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    accessible = get_accessible_restaurants(user)
    return accessible.filter(pk=restaurant.pk).exists()


def can_access_branch(user, branch) -> bool:
    """Return True if `user` can access `branch`."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    accessible = get_accessible_branches(user)
    return accessible.filter(pk=branch.pk).exists()


# ---------------------------------------------------------------------------
# Scope summary — used by /api/auth/me/ and user-detail responses
# ---------------------------------------------------------------------------

def get_user_scope_summary(user) -> dict:
    """
    Return a structured summary of a user's roles and accessible resources.

    Used by the frontend to understand what the logged-in user can see.
    """
    if not user or not user.is_authenticated:
        return {}

    assignments = list(user.get_active_assignments())

    roles = []
    for a in assignments:
        entry = {
            "assignment_id": str(a.pk),
            "role_code": a.role.code,
            "role_name": a.role.name,
            "scope": a.role.scope,
            "organization": {
                "id": str(a.organization.pk),
                "name": a.organization.name,
            } if a.organization else None,
            "restaurant": {
                "id": str(a.restaurant.pk),
                "name": a.restaurant.name,
            } if a.restaurant else None,
            "branch": {
                "id": str(a.branch.pk),
                "name": a.branch.name,
            } if a.branch else None,
        }
        roles.append(entry)

    return {
        "is_superuser": user.is_superuser,
        "is_staff": user.is_staff,
        "permissions": sorted(user.get_permissions_set()),
        "roles": roles,
    }


# ---------------------------------------------------------------------------
# Authorization helpers for user management
# ---------------------------------------------------------------------------

def can_manage_user(actor, target_user) -> bool:
    """
    Check if `actor` is allowed to manage (view/edit) `target_user`.

    Rules:
    - Superuser can manage anyone.
    - COMPANY_HEAD can manage users within their organization(s).
    - RESTAURANT_OWNER can manage users within their restaurant(s).
    - Others can only manage themselves.
    """
    if not actor.is_authenticated or not actor.is_active:
        return False
    if actor.is_superuser:
        return True
    if actor.pk == target_user.pk:
        return True

    from accounts.models import Role

    actor_assignments = actor.get_active_assignments()
    target_assignments = target_user.get_active_assignments()

    target_org_ids = {
        a.organization_id for a in target_assignments if a.organization_id
    }
    target_restaurant_ids = {
        a.restaurant_id for a in target_assignments if a.restaurant_id
    }

    for a in actor_assignments:
        if not a.role.is_active:
            continue
        if a.role.scope == Role.SCOPE_ORGANIZATION:
            if a.organization_id in target_org_ids:
                return True
        elif a.role.scope == Role.SCOPE_RESTAURANT:
            if a.restaurant_id in target_restaurant_ids:
                return True

    return False


def can_assign_role(actor, role, organization=None, restaurant=None, branch=None) -> bool:
    """
    Check if `actor` is allowed to assign a given role to someone else.

    Privilege escalation rules:
    - Nobody can assign a role with greater scope than their own.
    - COMPANY_HEAD can assign any role within their org.
    - RESTAURANT_OWNER can assign restaurant/branch roles within their restaurant.
    - Managers and below cannot assign roles.
    - Superuser can assign anything.
    """
    if not actor.is_authenticated or not actor.is_active:
        return False
    if actor.is_superuser:
        return True

    from accounts.models import Role as RoleModel

    # Roles that allow managing other users
    CAN_MANAGE = {
        RoleModel.CODE_COMPANY_HEAD,
        RoleModel.CODE_CENTRAL_ADMIN,
        RoleModel.CODE_RESTAURANT_OWNER,
    }

    # Roles that CANNOT be assigned by non-superusers
    PROTECTED_ROLES = {
        RoleModel.CODE_COMPANY_HEAD,
        RoleModel.CODE_CENTRAL_ADMIN,
    }

    if role.code in PROTECTED_ROLES:
        return False  # Only superuser can grant org-level roles

    actor_assignments = actor.get_active_assignments()

    for a in actor_assignments:
        if not a.role.is_active or a.role.code not in CAN_MANAGE:
            continue

        if a.role.code in (RoleModel.CODE_COMPANY_HEAD, RoleModel.CODE_CENTRAL_ADMIN):
            # Can assign restaurant/branch roles within their org
            if organization and a.organization_id == organization.pk:
                return True

        elif a.role.code == RoleModel.CODE_RESTAURANT_OWNER:
            # Can assign branch-level roles within their restaurant
            if role.scope == RoleModel.SCOPE_BRANCH and restaurant:
                if a.restaurant_id == restaurant.pk:
                    return True

    return False
