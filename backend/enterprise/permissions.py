# =============================================================================
# RestaurantFlow — Enterprise DRF Permission Classes
# Phase 20
#
# All authorization logic delegates to accounts.access and enterprise.access.
# Never duplicate access logic here.
#
# Usage:
#   class MyView(APIView):
#       permission_classes = [IsAuthenticated, HasPermission("enterprise.branch.open")]
#
#   class MyView(APIView):
#       permission_classes = [IsAuthenticated, HasEnterprisePermission("enterprise.branch.view")]
#       def get_object(self):
#           obj = ...
#           self.check_object_permissions(self.request, obj)
#           return obj
# =============================================================================

import logging
from rest_framework.permissions import BasePermission, IsAuthenticated  # noqa: F401 — re-exported

from accounts import access as acl

logger = logging.getLogger("enterprise")


# ---------------------------------------------------------------------------
# HasPermission factory (mirrors accounts.permissions pattern)
# ---------------------------------------------------------------------------

def HasPermission(code: str):
    """
    Factory that returns a DRF permission class checking for `code`.

    Usage:
        permission_classes = [IsAuthenticated, HasPermission("enterprise.branch.open")]
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
                    "enterprise.permission denied: user=%s code=%s view=%s",
                    request.user.email,
                    self.required_code,
                    view.__class__.__name__,
                )
            return result

    _HasPermission.__name__ = f"HasPermission_{code.replace('.', '_')}"
    return _HasPermission


# ---------------------------------------------------------------------------
# Object-level permission classes
# ---------------------------------------------------------------------------

class HasBranchEnterpriseAccess(BasePermission):
    """
    Object-level: user must have branch access (via accounts.access.can_access_branch).
    Used on BranchOperatingHour, BranchClosure, StaffBranchAssignment views.
    """

    message = "You do not have access to this branch."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from organizations.models import Branch
        from enterprise.models import (
            BranchOperatingHour, BranchClosure,
            StaffBranchAssignment, BranchOperationalStatus,
        )

        # Extract branch from the object
        branch = None
        if isinstance(obj, Branch):
            branch = obj
        elif hasattr(obj, "branch"):
            branch = obj.branch
        elif hasattr(obj, "source_branch"):
            branch = obj.source_branch

        if branch is None:
            return False

        result = acl.can_access_branch(request.user, branch)
        if not result:
            logger.warning(
                "enterprise.branch access denied: user=%s branch=%s",
                request.user.email,
                branch.pk,
            )
        return result


class HasRestaurantEnterpriseAccess(BasePermission):
    """
    Object-level: user must have restaurant access.
    Used on MenuRollout, StaffTransfer views.
    """

    message = "You do not have access to this restaurant."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from organizations.models import Restaurant
        from enterprise.models import MenuRollout, StaffTransfer

        restaurant = None
        if isinstance(obj, Restaurant):
            restaurant = obj
        elif hasattr(obj, "restaurant"):
            restaurant = obj.restaurant

        if restaurant is None:
            return False

        result = acl.can_access_restaurant(request.user, restaurant)
        if not result:
            logger.warning(
                "enterprise.restaurant access denied: user=%s restaurant=%s",
                request.user.email,
                restaurant.pk,
            )
        return result


class HasOrganizationEnterpriseAccess(BasePermission):
    """
    Object-level: user must have organization (company) access.
    Used on EnterpriseConfiguration, ApprovalPolicy, EnterpriseAuditLog views.
    """

    message = "You do not have access to this company's data."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        from organizations.models import Organization
        from enterprise.models import (
            EnterpriseConfiguration, ConfigurationChange,
            ApprovalPolicy, EnterpriseAuditLog,
        )

        company = None
        if isinstance(obj, Organization):
            company = obj
        elif hasattr(obj, "company"):
            company = obj.company
        elif hasattr(obj, "organization"):
            company = obj.organization

        if company is None:
            return False

        result = acl.can_access_organization(request.user, company)
        if not result:
            logger.warning(
                "enterprise.company access denied: user=%s company=%s",
                request.user.email,
                company.pk,
            )
        return result


# ---------------------------------------------------------------------------
# Composite permission helpers
# ---------------------------------------------------------------------------

class IsEnterpriseAdmin(BasePermission):
    """
    Request-level: user must hold COMPANY_HEAD, CENTRAL_ADMIN, or RESTAURANT_OWNER.
    Used as a broad gate on enterprise management endpoints.
    """

    message = "Enterprise administrator access required."

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
