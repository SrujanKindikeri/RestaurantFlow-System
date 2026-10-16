# =============================================================================
# RestaurantFlow — Enterprise Selectors (Read Layer)
# Phase 20
#
# Pure read/query functions — no DB writes, no side effects.
# Views and serializers should call these for all read operations.
# Returns QuerySets or dicts — never serialized data.
# =============================================================================

import logging
from datetime import timedelta
from django.db.models import Count, Q
from django.utils import timezone

from enterprise.access import (
    get_accessible_configurations,
    get_accessible_configuration_history,
    get_accessible_operating_hours,
    get_accessible_closures,
    get_accessible_rollouts,
    get_accessible_assignments,
    get_accessible_transfers,
    get_accessible_approval_policies,
    get_accessible_audit_logs,
    get_accessible_branch_statuses,
)
from enterprise.configuration_resolver import ConfigurationResolver
from enterprise.constants import (
    BRANCH_STATUS_ACTIVE,
    BRANCH_STATUS_TEMPORARILY_CLOSED,
    BRANCH_STATUS_SCHEDULED_CLOSURE,
    ROLLOUT_STATUS_COMPLETED,
    ROLLOUT_STATUS_FAILED,
    ROLLOUT_STATUS_RUNNING,
    TRANSFER_STATUS_REQUESTED,
    TRANSFER_STATUS_APPROVED,
    CLOSURE_STATUS_APPROVED,
    CLOSURE_STATUS_ACTIVE,
    CLOSURE_STATUS_PENDING_APPROVAL,
)

logger = logging.getLogger("enterprise")


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------

def get_enterprise_dashboard(user, company) -> dict:
    """
    Return aggregated enterprise dashboard data for a company.

    Queries:
        - total restaurants, total branches, active branches
        - branches by status
        - pending transfers, running rollouts, config exceptions
        - pending closures
    """
    from organizations.models import Restaurant, Branch
    from accounts import access as acl
    from enterprise.models import (
        BranchOperationalStatus,
        StaffTransfer,
        MenuRollout,
        BranchClosure,
    )

    # Counts scoped to this company
    restaurants = Restaurant.objects.filter(organization=company, is_active=True)
    restaurant_count = restaurants.count()

    branches = Branch.objects.filter(restaurant__organization=company, is_active=True)
    branch_count = branches.count()

    # Status distribution — BranchOperationalStatus entries
    status_qs = BranchOperationalStatus.objects.filter(
        branch__restaurant__organization=company
    )
    status_counts = {}
    for row in status_qs.values("status").annotate(n=Count("pk")):
        status_counts[row["status"]] = row["n"]

    # Branches without a BranchOperationalStatus record are implicitly ACTIVE
    branches_with_status = status_qs.values_list("branch_id", flat=True)
    implicit_active = branches.exclude(pk__in=branches_with_status).count()
    active_count = (
        status_counts.get(BRANCH_STATUS_ACTIVE, 0) + implicit_active
    )

    return {
        "total_restaurants": restaurant_count,
        "total_branches": branch_count,
        "active_branches": active_count,
        "temporarily_closed": status_counts.get(BRANCH_STATUS_TEMPORARILY_CLOSED, 0),
        "scheduled_closures": status_counts.get(BRANCH_STATUS_SCHEDULED_CLOSURE, 0),
        "pending_transfers": StaffTransfer.objects.filter(
            restaurant__organization=company,
            status__in=[TRANSFER_STATUS_REQUESTED, TRANSFER_STATUS_APPROVED],
        ).count(),
        "pending_rollouts": MenuRollout.objects.filter(
            restaurant__organization=company,
            status=ROLLOUT_STATUS_RUNNING,
        ).count(),
        "pending_closures": BranchClosure.objects.filter(
            branch__restaurant__organization=company,
            status=CLOSURE_STATUS_PENDING_APPROVAL,
        ).count(),
        "failed_rollouts_24h": MenuRollout.objects.filter(
            restaurant__organization=company,
            status=ROLLOUT_STATUS_FAILED,
            updated_at__gte=timezone.now() - timedelta(hours=24),
        ).count(),
    }


# ---------------------------------------------------------------------------
# Branch selectors
# ---------------------------------------------------------------------------

def get_branch_detail(user, branch) -> dict:
    """
    Return an aggregated branch detail dict including status, counters,
    staff count, operating hours, and active closures.
    """
    from enterprise.models import (
        BranchOperationalStatus,
        StaffBranchAssignment,
        BranchOperatingHour,
        BranchClosure,
    )

    status_obj = (
        BranchOperationalStatus.objects
        .filter(branch=branch)
        .select_related("status_changed_by")
        .first()
    )

    staff_count = StaffBranchAssignment.objects.filter(
        branch=branch, is_active=True
    ).count()

    operating_hours = list(
        BranchOperatingHour.objects.filter(branch=branch)
        .order_by("day_of_week")
        .values("day_of_week", "opening_time", "closing_time", "is_closed")
    )

    active_closures = list(
        BranchClosure.objects.filter(
            branch=branch,
            status__in=[CLOSURE_STATUS_APPROVED, CLOSURE_STATUS_ACTIVE],
        ).order_by("start_datetime").values(
            "id", "closure_type", "start_datetime", "end_datetime", "reason", "status"
        )
    )

    # Counter count (from counters app)
    try:
        from counters.models import Counter, CounterStatus
        counter_count = Counter.objects.filter(
            branch=branch, status=CounterStatus.ACTIVE
        ).count()
    except Exception:
        counter_count = None

    return {
        "branch_id": str(branch.pk),
        "branch_name": branch.name,
        "branch_code": branch.code,
        "operational_status": status_obj.status if status_obj else BRANCH_STATUS_ACTIVE,
        "status_changed_at": status_obj.status_changed_at if status_obj else None,
        "status_reason": status_obj.status_reason if status_obj else "",
        "active_staff_count": staff_count,
        "active_counter_count": counter_count,
        "operating_hours": operating_hours,
        "active_closures": active_closures,
    }


# ---------------------------------------------------------------------------
# Configuration selectors
# ---------------------------------------------------------------------------

def get_configurations_for_scope(
    user,
    company,
    restaurant=None,
    branch=None,
    active_only: bool = True,
) -> "QuerySet":
    """
    Return EnterpriseConfiguration rows for a specific scope.
    """
    from enterprise.models import EnterpriseConfiguration

    qs = get_accessible_configurations(user).filter(company=company)
    if restaurant is not None:
        qs = qs.filter(restaurant=restaurant)
    else:
        qs = qs.filter(restaurant__isnull=True)

    if branch is not None:
        qs = qs.filter(branch=branch)
    else:
        qs = qs.filter(branch__isnull=True)

    if active_only:
        qs = qs.filter(is_active=True)

    return qs.select_related("created_by", "updated_by", "company", "restaurant", "branch")


def get_effective_configuration_for_branch(user, branch) -> dict:
    """
    Return the fully-resolved effective configuration for a branch.
    Includes source (BRANCH/RESTAURANT/COMPANY/SYSTEM_DEFAULT) per key.
    """
    from accounts import access as acl
    if not acl.can_access_branch(user, branch):
        return {}
    return ConfigurationResolver.get_branch_configuration(branch)


def get_configuration_history(user, company, key: str = None, limit: int = 100) -> "QuerySet":
    """Return configuration change history for a company, optionally filtered by key."""
    qs = get_accessible_configuration_history(user).filter(company=company)
    if key:
        qs = qs.filter(configuration_key=key)
    return (
        qs.select_related("changed_by", "company", "restaurant", "branch")
        .order_by("-created_at")[:limit]
    )


# ---------------------------------------------------------------------------
# Operating hours selectors
# ---------------------------------------------------------------------------

def get_operating_hours_for_branch(user, branch) -> "QuerySet":
    from enterprise.models import BranchOperatingHour
    from accounts import access as acl
    if not acl.can_access_branch(user, branch):
        from enterprise.models import BranchOperatingHour
        return BranchOperatingHour.objects.none()
    return (
        BranchOperatingHour.objects.filter(branch=branch)
        .order_by("day_of_week")
    )


# ---------------------------------------------------------------------------
# Closure selectors
# ---------------------------------------------------------------------------

def get_closures_for_branch(user, branch, status_filter: list = None) -> "QuerySet":
    qs = get_accessible_closures(user).filter(branch=branch)
    if status_filter:
        qs = qs.filter(status__in=status_filter)
    return qs.select_related("created_by", "approved_by").order_by("-start_datetime")


# ---------------------------------------------------------------------------
# Rollout selectors
# ---------------------------------------------------------------------------

def get_rollouts_for_restaurant(
    user,
    restaurant,
    status_filter: list = None,
    rollout_type: str = None,
) -> "QuerySet":
    qs = get_accessible_rollouts(user).filter(restaurant=restaurant)
    if status_filter:
        qs = qs.filter(status__in=status_filter)
    if rollout_type:
        qs = qs.filter(rollout_type=rollout_type)
    return qs.select_related(
        "menu_item", "created_by", "approved_by", "source_branch"
    ).order_by("-created_at")


def get_rollout_with_results(user, rollout) -> "QuerySet":
    """Return rollout branch results for a specific rollout."""
    from enterprise.models import MenuRolloutBranch
    from accounts import access as acl
    if not acl.can_access_restaurant(user, rollout.restaurant):
        return MenuRolloutBranch.objects.none()
    return (
        MenuRolloutBranch.objects.filter(rollout=rollout)
        .select_related("branch")
        .order_by("branch__name")
    )


# ---------------------------------------------------------------------------
# Staff selectors
# ---------------------------------------------------------------------------

def get_assignments_for_branch(user, branch, active_only: bool = True) -> "QuerySet":
    qs = get_accessible_assignments(user).filter(branch=branch)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.select_related("user", "role", "assigned_by").order_by("-assigned_at")


def get_assignments_for_user(user, target_user, active_only: bool = True) -> "QuerySet":
    qs = get_accessible_assignments(user).filter(user=target_user)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.select_related("branch", "restaurant", "role").order_by("-assigned_at")


def get_transfers_for_restaurant(
    user,
    restaurant,
    status_filter: list = None,
) -> "QuerySet":
    qs = get_accessible_transfers(user).filter(restaurant=restaurant)
    if status_filter:
        qs = qs.filter(status__in=status_filter)
    return qs.select_related(
        "user", "source_branch", "destination_branch",
        "requested_by", "approved_by"
    ).order_by("-requested_at")


def get_transfers_for_user(user, target_user) -> "QuerySet":
    qs = get_accessible_transfers(user).filter(user=target_user)
    return qs.select_related(
        "source_branch", "destination_branch", "restaurant"
    ).order_by("-requested_at")


# ---------------------------------------------------------------------------
# Approval policy selectors
# ---------------------------------------------------------------------------

def get_approval_policies_for_company(
    user,
    company,
    policy_type: str = None,
    active_only: bool = True,
) -> "QuerySet":
    qs = get_accessible_approval_policies(user).filter(company=company)
    if policy_type:
        qs = qs.filter(policy_type=policy_type)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs.select_related("restaurant", "branch", "required_role").order_by("policy_type")


# ---------------------------------------------------------------------------
# Audit log selectors
# ---------------------------------------------------------------------------

def get_audit_logs(
    user,
    company,
    restaurant=None,
    branch=None,
    action: str = None,
    limit: int = 100,
) -> "QuerySet":
    qs = get_accessible_audit_logs(user).filter(company=company)
    if restaurant:
        qs = qs.filter(restaurant=restaurant)
    if branch:
        qs = qs.filter(branch=branch)
    if action:
        qs = qs.filter(action=action)
    return (
        qs.select_related("performed_by", "company", "restaurant", "branch")
        .order_by("-created_at")[:limit]
    )


# ---------------------------------------------------------------------------
# Staff list for a restaurant (for the enterprise staff panel)
# ---------------------------------------------------------------------------

def get_staff_overview_for_restaurant(user, restaurant) -> "QuerySet":
    """
    Return all active staff assignments for a restaurant,
    grouped by user — for the enterprise staff panel.
    """
    qs = get_accessible_assignments(user).filter(
        restaurant=restaurant, is_active=True
    )
    return qs.select_related(
        "user", "branch", "role", "assigned_by"
    ).order_by("user__email", "-assigned_at")
