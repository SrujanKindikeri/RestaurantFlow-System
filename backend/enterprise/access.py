# =============================================================================
# RestaurantFlow — Enterprise Access Control
# Phase 20
#
# App-specific scoping functions that wrap accounts.access.
# Views fetch objects through these functions — never raw .objects.get().
# 404 (not 403) is returned for unauthorized UUIDs — IDOR prevention.
# =============================================================================

import logging
from django.db.models import QuerySet

from accounts import access as acl

logger = logging.getLogger("enterprise")


# ---------------------------------------------------------------------------
# EnterpriseConfiguration
# ---------------------------------------------------------------------------

def get_accessible_configurations(user) -> QuerySet:
    """Return EnterpriseConfiguration rows visible to this user."""
    from enterprise.models import EnterpriseConfiguration

    if not user or not user.is_authenticated or not user.is_active:
        return EnterpriseConfiguration.objects.none()

    if user.is_superuser or user.is_staff:
        return EnterpriseConfiguration.objects.all()

    accessible_orgs  = acl.get_accessible_organizations(user).values_list("pk", flat=True)
    accessible_rests = acl.get_accessible_restaurants(user).values_list("pk", flat=True)
    accessible_branchs = acl.get_accessible_branches(user).values_list("pk", flat=True)

    from django.db.models import Q
    return EnterpriseConfiguration.objects.filter(
        Q(company_id__in=accessible_orgs)
    ).filter(
        Q(restaurant__isnull=True)
        | Q(restaurant_id__in=accessible_rests)
    ).filter(
        Q(branch__isnull=True)
        | Q(branch_id__in=accessible_branchs)
    )


def get_accessible_configuration_history(user) -> QuerySet:
    """Return ConfigurationChange rows visible to this user."""
    from enterprise.models import ConfigurationChange
    from django.db.models import Q

    if not user or not user.is_authenticated or not user.is_active:
        return ConfigurationChange.objects.none()

    if user.is_superuser or user.is_staff:
        return ConfigurationChange.objects.all()

    accessible_orgs = acl.get_accessible_organizations(user).values_list("pk", flat=True)
    return ConfigurationChange.objects.filter(company_id__in=accessible_orgs)


# ---------------------------------------------------------------------------
# BranchOperatingHour
# ---------------------------------------------------------------------------

def get_accessible_operating_hours(user) -> QuerySet:
    from enterprise.models import BranchOperatingHour

    if not user or not user.is_authenticated or not user.is_active:
        return BranchOperatingHour.objects.none()

    if user.is_superuser or user.is_staff:
        return BranchOperatingHour.objects.all()

    accessible_branches = acl.get_accessible_branches(user).values_list("pk", flat=True)
    return BranchOperatingHour.objects.filter(branch_id__in=accessible_branches)


# ---------------------------------------------------------------------------
# BranchClosure
# ---------------------------------------------------------------------------

def get_accessible_closures(user) -> QuerySet:
    from enterprise.models import BranchClosure

    if not user or not user.is_authenticated or not user.is_active:
        return BranchClosure.objects.none()

    if user.is_superuser or user.is_staff:
        return BranchClosure.objects.all()

    accessible_branches = acl.get_accessible_branches(user).values_list("pk", flat=True)
    return BranchClosure.objects.filter(branch_id__in=accessible_branches)


# ---------------------------------------------------------------------------
# MenuRollout
# ---------------------------------------------------------------------------

def get_accessible_rollouts(user) -> QuerySet:
    from enterprise.models import MenuRollout

    if not user or not user.is_authenticated or not user.is_active:
        return MenuRollout.objects.none()

    if user.is_superuser or user.is_staff:
        return MenuRollout.objects.all()

    accessible_rests = acl.get_accessible_restaurants(user).values_list("pk", flat=True)
    return MenuRollout.objects.filter(restaurant_id__in=accessible_rests)


# ---------------------------------------------------------------------------
# StaffBranchAssignment
# ---------------------------------------------------------------------------

def get_accessible_assignments(user) -> QuerySet:
    from enterprise.models import StaffBranchAssignment

    if not user or not user.is_authenticated or not user.is_active:
        return StaffBranchAssignment.objects.none()

    if user.is_superuser or user.is_staff:
        return StaffBranchAssignment.objects.all()

    accessible_branches = acl.get_accessible_branches(user).values_list("pk", flat=True)
    return StaffBranchAssignment.objects.filter(branch_id__in=accessible_branches)


# ---------------------------------------------------------------------------
# StaffTransfer
# ---------------------------------------------------------------------------

def get_accessible_transfers(user) -> QuerySet:
    from enterprise.models import StaffTransfer

    if not user or not user.is_authenticated or not user.is_active:
        return StaffTransfer.objects.none()

    if user.is_superuser or user.is_staff:
        return StaffTransfer.objects.all()

    accessible_rests = acl.get_accessible_restaurants(user).values_list("pk", flat=True)
    return StaffTransfer.objects.filter(restaurant_id__in=accessible_rests)


# ---------------------------------------------------------------------------
# ApprovalPolicy
# ---------------------------------------------------------------------------

def get_accessible_approval_policies(user) -> QuerySet:
    from enterprise.models import ApprovalPolicy
    from django.db.models import Q

    if not user or not user.is_authenticated or not user.is_active:
        return ApprovalPolicy.objects.none()

    if user.is_superuser or user.is_staff:
        return ApprovalPolicy.objects.all()

    accessible_orgs = acl.get_accessible_organizations(user).values_list("pk", flat=True)
    return ApprovalPolicy.objects.filter(company_id__in=accessible_orgs)


# ---------------------------------------------------------------------------
# EnterpriseAuditLog
# ---------------------------------------------------------------------------

def get_accessible_audit_logs(user) -> QuerySet:
    from enterprise.models import EnterpriseAuditLog

    if not user or not user.is_authenticated or not user.is_active:
        return EnterpriseAuditLog.objects.none()

    if user.is_superuser or user.is_staff:
        return EnterpriseAuditLog.objects.all()

    accessible_orgs = acl.get_accessible_organizations(user).values_list("pk", flat=True)
    return EnterpriseAuditLog.objects.filter(company_id__in=accessible_orgs)


# ---------------------------------------------------------------------------
# BranchOperationalStatus
# ---------------------------------------------------------------------------

def get_accessible_branch_statuses(user) -> QuerySet:
    from enterprise.models import BranchOperationalStatus

    if not user or not user.is_authenticated or not user.is_active:
        return BranchOperationalStatus.objects.none()

    if user.is_superuser or user.is_staff:
        return BranchOperationalStatus.objects.all()

    accessible_branches = acl.get_accessible_branches(user).values_list("pk", flat=True)
    return BranchOperationalStatus.objects.filter(branch_id__in=accessible_branches)
