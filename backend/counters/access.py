# =============================================================================
# RestaurantFlow — Counter Access Control
# Phase 4
#
# Public API:
#   get_accessible_counters(user)             → QuerySet[Counter]
#   can_access_counter(user, counter)         → bool
#   get_accessible_sessions(user)             → QuerySet[CounterSession]
#   get_accessible_assignments(user)          → QuerySet[CounterAssignment]
#   get_accessible_shifts(user)               → QuerySet[Shift]
#
# Delegates to accounts.access for branch/restaurant/org scope resolution.
# =============================================================================

import logging
from django.db.models import Q

from accounts import access as acl

logger = logging.getLogger("counters")


# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------

def get_accessible_counters(user):
    """
    Return the Counters queryset scoped to the requesting user.

    - Superuser / staff  → all counters
    - COMPANY_HEAD / CENTRAL_ADMIN → all counters in their org(s)
    - RESTAURANT_OWNER   → all counters in their restaurant(s)
    - MANAGER / CASHIER  → counters in their assigned branch(es)
    """
    from counters.models import Counter

    if not user or not user.is_authenticated or not user.is_active:
        return Counter.objects.none()

    if user.is_superuser or user.is_staff:
        return Counter.objects.select_related(
            "branch__restaurant__organization"
        )

    accessible_branch_ids = acl.get_accessible_branches(user).values_list(
        "pk", flat=True
    )
    return Counter.objects.filter(
        branch_id__in=accessible_branch_ids
    ).select_related("branch__restaurant__organization")


def can_access_counter(user, counter) -> bool:
    """Return True if user is allowed to see/interact with this counter."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    accessible = get_accessible_counters(user)
    return accessible.filter(pk=counter.pk).exists()


# ---------------------------------------------------------------------------
# Counter Sessions
# ---------------------------------------------------------------------------

def get_accessible_sessions(user):
    """
    Return CounterSessions scoped to the user's accessible counters.
    """
    from counters.models import CounterSession

    if not user or not user.is_authenticated or not user.is_active:
        return CounterSession.objects.none()

    if user.is_superuser or user.is_staff:
        return CounterSession.objects.select_related(
            "counter__branch__restaurant__organization",
            "opened_by",
            "closed_by",
            "shift",
        )

    accessible_counter_ids = get_accessible_counters(user).values_list(
        "pk", flat=True
    )
    return CounterSession.objects.filter(
        counter_id__in=accessible_counter_ids
    ).select_related(
        "counter__branch__restaurant__organization",
        "opened_by",
        "closed_by",
        "shift",
    )


# ---------------------------------------------------------------------------
# Counter Assignments
# ---------------------------------------------------------------------------

def get_accessible_assignments(user):
    """
    Return CounterAssignments scoped to the user's accessible counters.
    """
    from counters.models import CounterAssignment

    if not user or not user.is_authenticated or not user.is_active:
        return CounterAssignment.objects.none()

    if user.is_superuser or user.is_staff:
        return CounterAssignment.objects.select_related(
            "counter__branch__restaurant__organization",
            "user",
            "assigned_by",
        )

    accessible_counter_ids = get_accessible_counters(user).values_list(
        "pk", flat=True
    )
    return CounterAssignment.objects.filter(
        counter_id__in=accessible_counter_ids
    ).select_related(
        "counter__branch__restaurant__organization",
        "user",
        "assigned_by",
    )


# ---------------------------------------------------------------------------
# Shifts
# ---------------------------------------------------------------------------

def get_accessible_shifts(user):
    """Return Shifts scoped to the user's accessible branches."""
    from counters.models import Shift

    if not user or not user.is_authenticated or not user.is_active:
        return Shift.objects.none()

    if user.is_superuser or user.is_staff:
        return Shift.objects.select_related("branch__restaurant__organization")

    accessible_branch_ids = acl.get_accessible_branches(user).values_list(
        "pk", flat=True
    )
    return Shift.objects.filter(
        branch_id__in=accessible_branch_ids
    ).select_related("branch__restaurant__organization")
