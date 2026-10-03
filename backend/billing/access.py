# =============================================================================
# RestaurantFlow — Billing Access Control
# Phase 8
#
# Single source of truth for billing authorization decisions.
# Views and serializers delegate here — never duplicate access logic.
#
# Public API:
#   get_accessible_bills(user)               → QuerySet[Bill]
#   get_accessible_corrections(user)         → QuerySet[BillCorrectionRequest]
#   can_access_bill(user, bill)              → bool
#   can_access_correction(user, correction)  → bool
#
# Security principle:
#   All querysets are scoped to what the user's role permits.
#   A user from Restaurant A must never see Restaurant B's bills
#   even if they guess a valid UUID.
#   Views call get_queryset().get(pk=pk) → 404 on miss (IDOR prevention).
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("billing")


def get_accessible_bills(user):
    """
    Return the set of Bills this user is authorized to see.

    - Superuser / staff     → all bills
    - Org-scope roles       → all bills in their org's branches
    - Restaurant-scope roles → all bills in their restaurant's branches
    - Branch-scope roles    → bills in their assigned branch(es) only
    """
    from billing.models import Bill

    if not user or not user.is_authenticated or not user.is_active:
        return Bill.objects.none()

    if user.is_superuser or user.is_staff:
        return Bill.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return Bill.objects.filter(branch__in=accessible_branches)


def get_accessible_corrections(user):
    """
    Return the set of BillCorrectionRequests this user is authorized to see.

    Scoped to the same branches as get_accessible_bills().
    """
    from billing.models import BillCorrectionRequest

    if not user or not user.is_authenticated or not user.is_active:
        return BillCorrectionRequest.objects.none()

    if user.is_superuser or user.is_staff:
        return BillCorrectionRequest.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return BillCorrectionRequest.objects.filter(bill__branch__in=accessible_branches)


def can_access_bill(user, bill) -> bool:
    """Return True if user can access this specific bill."""
    return get_accessible_bills(user).filter(pk=bill.pk).exists()


def can_access_correction(user, correction) -> bool:
    """Return True if user can access this specific correction request."""
    return get_accessible_corrections(user).filter(pk=correction.pk).exists()
