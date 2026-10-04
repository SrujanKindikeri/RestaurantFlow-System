# =============================================================================
# RestaurantFlow — Central Control Center Selectors
# Phase 15
#
# Read-only query layer. Views and serializers call these functions;
# they never build querysets directly.
#
# All selectors enforce organization/restaurant/branch scope.
# Never return data outside the user's authorized scope.
# =============================================================================

import logging
from django.db.models import Count, Q

from central_control.constants import (
    ALERT_ACTIVE_STATUSES, ALERT_TERMINAL_STATUSES,
    ISSUE_ACTIVE_STATUSES, ISSUE_TERMINAL_STATUSES,
    ALERT_OPEN, ALERT_ACKNOWLEDGED,
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_LOW,
)

logger = logging.getLogger("central_control")


# ---------------------------------------------------------------------------
# Scope helper
# ---------------------------------------------------------------------------

def _get_accessible_org_ids(user) -> list:
    """Return list of org PKs accessible to the user."""
    from accounts import access as acl
    return list(acl.get_accessible_organizations(user).values_list("pk", flat=True))


def _get_accessible_restaurant_ids(user) -> list:
    """Return list of restaurant PKs accessible to the user."""
    from accounts import access as acl
    return list(acl.get_accessible_restaurants(user).values_list("pk", flat=True))


def _get_accessible_branch_ids(user) -> list:
    """Return list of branch PKs accessible to the user."""
    from accounts import access as acl
    return list(acl.get_accessible_branches(user).values_list("pk", flat=True))


# ---------------------------------------------------------------------------
# Alert selectors
# ---------------------------------------------------------------------------

def get_alerts_for_user(
    user,
    *,
    organization_id=None,
    restaurant_id=None,
    branch_id=None,
    severity=None,
    status=None,
    alert_type=None,
    search=None,
    ordering="-detected_at",
):
    """
    Return a scoped, filtered CentralAlert queryset for the requesting user.

    Applies organization/restaurant/branch scope before any filters.
    """
    from central_control.models import CentralAlert
    from accounts import access as acl

    accessible_org_ids = _get_accessible_org_ids(user)

    qs = CentralAlert.objects.filter(
        organization_id__in=accessible_org_ids
    ).select_related(
        "organization", "restaurant", "branch",
        "acknowledged_by", "resolved_by",
    )

    # Narrow to specific org/restaurant/branch if requested
    if organization_id:
        if str(organization_id) not in [str(oid) for oid in accessible_org_ids]:
            return CentralAlert.objects.none()
        qs = qs.filter(organization_id=organization_id)

    if restaurant_id:
        accessible_restaurant_ids = _get_accessible_restaurant_ids(user)
        if str(restaurant_id) not in [str(rid) for rid in accessible_restaurant_ids]:
            return CentralAlert.objects.none()
        qs = qs.filter(restaurant_id=restaurant_id)

    if branch_id:
        accessible_branch_ids = _get_accessible_branch_ids(user)
        if str(branch_id) not in [str(bid) for bid in accessible_branch_ids]:
            return CentralAlert.objects.none()
        qs = qs.filter(branch_id=branch_id)

    # Apply filters
    if severity:
        qs = qs.filter(severity=severity)
    if status:
        qs = qs.filter(status=status)
    if alert_type:
        qs = qs.filter(alert_type=alert_type)
    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(message__icontains=search)
        )

    # Validate ordering field
    allowed_ordering = {
        "detected_at", "-detected_at", "severity", "-severity",
        "status", "-status", "alert_type", "-alert_type",
    }
    if ordering not in allowed_ordering:
        ordering = "-detected_at"

    return qs.order_by(ordering)


def get_alert_by_id(user, alert_id):
    """
    Return a single CentralAlert by ID if the user has access.
    Returns None if not found or out of scope.
    """
    from central_control.models import CentralAlert

    accessible_org_ids = _get_accessible_org_ids(user)
    try:
        return CentralAlert.objects.select_related(
            "organization", "restaurant", "branch",
            "acknowledged_by", "resolved_by",
        ).get(pk=alert_id, organization_id__in=accessible_org_ids)
    except CentralAlert.DoesNotExist:
        return None


def get_alert_counts_for_organization(organization_id) -> dict:
    """
    Return alert counts by severity for an organization.
    Used by the dashboard. Cached at view layer.
    """
    from central_control.models import CentralAlert

    counts = CentralAlert.objects.filter(
        organization_id=organization_id,
        status__in=list(ALERT_ACTIVE_STATUSES),
    ).values("severity").annotate(count=Count("id"))

    result = {SEVERITY_CRITICAL: 0, SEVERITY_HIGH: 0, SEVERITY_MEDIUM: 0, SEVERITY_LOW: 0}
    for row in counts:
        if row["severity"] in result:
            result[row["severity"]] = row["count"]
    return result


# ---------------------------------------------------------------------------
# Issue selectors
# ---------------------------------------------------------------------------

def get_issues_for_user(
    user,
    *,
    organization_id=None,
    restaurant_id=None,
    branch_id=None,
    severity=None,
    status=None,
    category=None,
    assigned_to_id=None,
    search=None,
    ordering="-created_at",
):
    """
    Return a scoped, filtered CentralIssue queryset for the requesting user.
    """
    from central_control.models import CentralIssue

    accessible_org_ids = _get_accessible_org_ids(user)

    qs = CentralIssue.objects.filter(
        organization_id__in=accessible_org_ids
    ).select_related(
        "organization", "restaurant", "branch",
        "created_by", "assigned_to", "resolved_by", "closed_by",
        "detected_from_alert",
    )

    if organization_id:
        if str(organization_id) not in [str(oid) for oid in accessible_org_ids]:
            return CentralIssue.objects.none()
        qs = qs.filter(organization_id=organization_id)

    if restaurant_id:
        accessible_restaurant_ids = _get_accessible_restaurant_ids(user)
        if str(restaurant_id) not in [str(rid) for rid in accessible_restaurant_ids]:
            return CentralIssue.objects.none()
        qs = qs.filter(restaurant_id=restaurant_id)

    if branch_id:
        accessible_branch_ids = _get_accessible_branch_ids(user)
        if str(branch_id) not in [str(bid) for bid in accessible_branch_ids]:
            return CentralIssue.objects.none()
        qs = qs.filter(branch_id=branch_id)

    if severity:
        qs = qs.filter(severity=severity)
    if status:
        qs = qs.filter(status=status)
    if category:
        qs = qs.filter(category=category)
    if assigned_to_id:
        qs = qs.filter(assigned_to_id=assigned_to_id)
    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    allowed_ordering = {
        "created_at", "-created_at", "severity", "-severity",
        "status", "-status", "due_at", "-due_at",
    }
    if ordering not in allowed_ordering:
        ordering = "-created_at"

    return qs.order_by(ordering)


def get_issue_by_id(user, issue_id):
    """Return a single CentralIssue by ID if accessible."""
    from central_control.models import CentralIssue

    accessible_org_ids = _get_accessible_org_ids(user)
    try:
        return CentralIssue.objects.select_related(
            "organization", "restaurant", "branch",
            "created_by", "assigned_to", "resolved_by", "closed_by",
            "detected_from_alert",
        ).get(pk=issue_id, organization_id__in=accessible_org_ids)
    except CentralIssue.DoesNotExist:
        return None


def get_issue_counts_for_organization(organization_id) -> dict:
    """Return issue counts grouped by status for an organization."""
    from central_control.models import CentralIssue

    open_count = CentralIssue.objects.filter(
        organization_id=organization_id,
        status__in=list(ISSUE_ACTIVE_STATUSES),
    ).count()

    critical_count = CentralIssue.objects.filter(
        organization_id=organization_id,
        status__in=list(ISSUE_ACTIVE_STATUSES),
        severity=SEVERITY_CRITICAL,
    ).count()

    return {"open": open_count, "critical": critical_count}


# ---------------------------------------------------------------------------
# Event timeline selectors
# ---------------------------------------------------------------------------

def get_events_for_user(
    user,
    *,
    organization_id=None,
    restaurant_id=None,
    branch_id=None,
    event_type=None,
    severity=None,
    search=None,
    ordering="-occurred_at",
):
    """Return a scoped event timeline queryset."""
    from central_control.models import CentralSystemEvent

    accessible_org_ids = _get_accessible_org_ids(user)

    qs = CentralSystemEvent.objects.filter(
        organization_id__in=accessible_org_ids
    ).select_related("organization", "restaurant", "branch", "alert", "issue")

    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    if restaurant_id:
        qs = qs.filter(restaurant_id=restaurant_id)
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    if event_type:
        qs = qs.filter(event_type=event_type)
    if severity:
        qs = qs.filter(severity=severity)
    if search:
        qs = qs.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )

    return qs.order_by(ordering)


# ---------------------------------------------------------------------------
# Restaurant / Branch overview selectors
# ---------------------------------------------------------------------------

def get_restaurants_for_user(user, *, organization_id=None, is_active=None):
    """Return a scoped restaurant queryset with annotation summaries."""
    from accounts import access as acl
    from organizations.models import Restaurant

    qs = acl.get_accessible_restaurants(user).select_related("organization")

    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    return qs.prefetch_related("branches")


def get_branches_for_user(user, *, restaurant_id=None, organization_id=None, is_active=None):
    """Return a scoped branch queryset."""
    from accounts import access as acl
    from organizations.models import Branch

    qs = acl.get_accessible_branches(user).select_related(
        "restaurant", "restaurant__organization"
    )

    if organization_id:
        qs = qs.filter(restaurant__organization_id=organization_id)
    if restaurant_id:
        qs = qs.filter(restaurant_id=restaurant_id)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)

    return qs


# ---------------------------------------------------------------------------
# User access selectors (read-only visibility for Central Control)
# ---------------------------------------------------------------------------

def get_users_for_central_control(user, *, organization_id=None, search=None):
    """
    Return a queryset of users visible to the Central Control user.
    Minimum exposure: only shows users in accessible orgs.
    Never exposes passwords, tokens, or sensitive credentials.
    """
    from accounts.models import UserRoleAssignment
    from django.contrib.auth import get_user_model

    User = get_user_model()
    accessible_org_ids = _get_accessible_org_ids(user)

    # Find users who have role assignments in accessible orgs
    user_ids_in_scope = UserRoleAssignment.objects.filter(
        organization_id__in=accessible_org_ids,
        is_active=True,
    ).values_list("user_id", flat=True).distinct()

    qs = User.objects.filter(pk__in=user_ids_in_scope).select_related("profile")

    if organization_id:
        extra_user_ids = UserRoleAssignment.objects.filter(
            organization_id=organization_id,
            is_active=True,
        ).values_list("user_id", flat=True)
        qs = qs.filter(pk__in=extra_user_ids)

    if search:
        qs = qs.filter(
            Q(email__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
        )

    return qs.order_by("email")


# ---------------------------------------------------------------------------
# Audit log selectors
# ---------------------------------------------------------------------------

def get_audit_logs_for_user(user, *, organization_id=None, entity_type=None, entity_id=None):
    """Return scoped audit log entries."""
    from central_control.models import CentralControlAuditLog

    accessible_org_ids = _get_accessible_org_ids(user)

    qs = CentralControlAuditLog.objects.filter(
        organization_id__in=accessible_org_ids
    ).select_related("actor", "organization", "restaurant", "branch")

    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    if entity_type:
        qs = qs.filter(entity_type=entity_type)
    if entity_id:
        qs = qs.filter(entity_id=entity_id)

    return qs.order_by("-created_at")


# ---------------------------------------------------------------------------
# Settings selectors
# ---------------------------------------------------------------------------

def get_settings_for_organization(organization):
    """
    Return the CentralControlSettings for an organization,
    creating with defaults if it does not exist.
    """
    from central_control.models import CentralControlSettings

    settings_obj, _ = CentralControlSettings.objects.get_or_create(
        organization=organization
    )
    return settings_obj


# ---------------------------------------------------------------------------
# Escalation rule selectors
# ---------------------------------------------------------------------------

def get_escalation_rules_for_organization(organization, *, is_active=True):
    """Return escalation rules for an organization."""
    from central_control.models import EscalationRule

    qs = EscalationRule.objects.filter(organization=organization)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return qs.select_related("restaurant").order_by("alert_type", "severity")
