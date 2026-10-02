# =============================================================================
# RestaurantFlow — DRF Permission Classes
# Phase 3
#
# All authorization logic delegates to accounts.access — never duplicated here.
#
# Usage examples:
#
#   class MyView(APIView):
#       permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]
#
#   class MyView(APIView):
#       permission_classes = [IsAuthenticated, HasRestaurantAccess]
#
# Composability:
#   DRF evaluates permission_classes left-to-right; all must pass.
#   Always include IsAuthenticated first.
# =============================================================================

import logging
from rest_framework.permissions import BasePermission, IsAuthenticated  # noqa: F401 — re-exported

from accounts import access as acl

logger = logging.getLogger("accounts")


# ---------------------------------------------------------------------------
# HasPermission factory
# ---------------------------------------------------------------------------

def HasPermission(code: str):
    """
    Factory that returns a DRF permission class checking for a specific
    permission code.

    Usage:
        permission_classes = [IsAuthenticated, HasPermission("restaurant.view")]
    """

    class _HasPermission(BasePermission):
        message = f"You do not have the required permission: {code}"
        required_code = code

        def has_permission(self, request, view):
            if not request.user or not request.user.is_authenticated:
                return False
            result = acl.has_permission(request.user, self.required_code)
            if not result:
                logger.warning(
                    "Permission denied: user=%s code=%s view=%s",
                    request.user.email,
                    self.required_code,
                    view.__class__.__name__,
                )
            return result

    _HasPermission.__name__ = f"HasPermission_{code.replace('.', '_')}"
    return _HasPermission


# ---------------------------------------------------------------------------
# Organization-scope permission
# ---------------------------------------------------------------------------

class HasOrganizationAccess(BasePermission):
    """
    Object-level permission: the requesting user must have access to the
    Organization instance.

    Used with retrieve/update views where the organization is the object.
    """

    message = "You do not have access to this organization."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from organizations.models import Organization
        if not isinstance(obj, Organization):
            return False
        result = acl.can_access_organization(request.user, obj)
        if not result:
            logger.warning(
                "Organization access denied: user=%s org=%s",
                request.user.email,
                obj.pk,
            )
        return result


# ---------------------------------------------------------------------------
# Restaurant-scope permission
# ---------------------------------------------------------------------------

class HasRestaurantAccess(BasePermission):
    """
    Object-level permission: the requesting user must have access to the
    Restaurant instance.
    """

    message = "You do not have access to this restaurant."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from organizations.models import Restaurant
        if not isinstance(obj, Restaurant):
            return False
        result = acl.can_access_restaurant(request.user, obj)
        if not result:
            logger.warning(
                "Restaurant access denied: user=%s restaurant=%s",
                request.user.email,
                obj.pk,
            )
        return result


# ---------------------------------------------------------------------------
# Branch-scope permission
# ---------------------------------------------------------------------------

class HasBranchAccess(BasePermission):
    """
    Object-level permission: the requesting user must have access to the
    Branch instance.
    """

    message = "You do not have access to this branch."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from organizations.models import Branch
        if not isinstance(obj, Branch):
            return False
        result = acl.can_access_branch(request.user, obj)
        if not result:
            logger.warning(
                "Branch access denied: user=%s branch=%s",
                request.user.email,
                obj.pk,
            )
        return result


# ---------------------------------------------------------------------------
# IsOrganizationAdmin — can manage org-level resources
# ---------------------------------------------------------------------------

class IsOrganizationAdmin(BasePermission):
    """
    Request-level permission: user must hold a COMPANY_HEAD or CENTRAL_ADMIN
    role assignment, or be staff/superuser.
    """

    message = "Organization administrator access required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True

        from accounts.models import Role
        ORG_ADMIN_CODES = {Role.CODE_COMPANY_HEAD, Role.CODE_CENTRAL_ADMIN}

        return request.user.role_assignments.filter(
            is_active=True,
            role__code__in=ORG_ADMIN_CODES,
            role__is_active=True,
        ).exists()


# ---------------------------------------------------------------------------
# IsRestaurantAdmin — can manage restaurant-level resources
# ---------------------------------------------------------------------------

class IsRestaurantAdmin(BasePermission):
    """
    Request-level: user must hold COMPANY_HEAD, CENTRAL_ADMIN, or
    RESTAURANT_OWNER, or be staff/superuser.
    """

    message = "Restaurant administrator access required."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True

        from accounts.models import Role
        ADMIN_CODES = {
            Role.CODE_COMPANY_HEAD,
            Role.CODE_CENTRAL_ADMIN,
            Role.CODE_RESTAURANT_OWNER,
        }

        return request.user.role_assignments.filter(
            is_active=True,
            role__code__in=ADMIN_CODES,
            role__is_active=True,
        ).exists()


# ---------------------------------------------------------------------------
# IsSelfOrAdmin — can act on their own record or is an admin
# ---------------------------------------------------------------------------

class IsSelfOrAdmin(BasePermission):
    """
    Object-level: user can access their own record; staff/superuser access all.
    """

    message = "You can only access your own user record."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from accounts.models import User
        if isinstance(obj, User):
            return (
                request.user.is_superuser
                or request.user.is_staff
                or obj.pk == request.user.pk
                or acl.can_manage_user(request.user, obj)
            )
        return False
