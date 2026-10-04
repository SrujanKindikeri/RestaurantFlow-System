# =============================================================================
# RestaurantFlow — Reporting Access Control
# Phase 14
#
# Thin wrappers over accounts.access that apply reporting-specific scoping.
# Views and selectors delegate here — never duplicate access logic.
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("reporting")


def get_accessible_branches(user):
    """Return branches the user can run reports against."""
    return acl.get_accessible_branches(user)


def get_accessible_restaurants(user):
    """Return restaurants the user can run reports against."""
    return acl.get_accessible_restaurants(user)


def get_accessible_organizations(user):
    """Return organizations the user can run reports against."""
    return acl.get_accessible_organizations(user)


def resolve_report_scope(user, restaurant_id=None, branch_id=None):
    """
    Resolve and validate the requested restaurant/branch scope for a report.

    Returns (restaurant, branch) where either or both may be None.
    Raises ReportScopeError if a requested ID is outside the user's scope.

    NEVER trust frontend-supplied IDs — always validate server-side.
    """
    from reporting.exceptions import ReportScopeError

    restaurant = None
    branch = None

    if branch_id:
        accessible = acl.get_accessible_branches(user)
        try:
            branch = accessible.get(pk=branch_id)
        except Exception:
            raise ReportScopeError(
                "The requested branch is not within your authorized scope."
            )
        # Derive the restaurant from the branch
        restaurant = branch.restaurant

    elif restaurant_id:
        accessible = acl.get_accessible_restaurants(user)
        try:
            restaurant = accessible.get(pk=restaurant_id)
        except Exception:
            raise ReportScopeError(
                "The requested restaurant is not within your authorized scope."
            )

    return restaurant, branch
