# =============================================================================
# RestaurantFlow — Payment Access Control
# Phase 9
#
# IDOR prevention: all payment querysets are filtered through these functions.
# A user from Restaurant A can NEVER see Restaurant B's payments,
# even by guessing a valid UUID.
#
# Public API:
#   get_accessible_payments(user)          → QuerySet[Payment]
#   get_accessible_refunds(user)           → QuerySet[PaymentRefund]
#   can_access_payment(user, payment)      → bool
#   can_access_refund(user, refund)        → bool
# =============================================================================

import logging

from accounts import access as acl

logger = logging.getLogger("payments")


def get_accessible_payments(user):
    """
    Return the queryset of Payments this user is authorized to see.

    Scope is determined by the branches the user can access.
    """
    from payments.models import Payment

    if not user or not user.is_authenticated or not user.is_active:
        return Payment.objects.none()

    if user.is_superuser or user.is_staff:
        return Payment.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return Payment.objects.filter(branch__in=accessible_branches)


def get_accessible_refunds(user):
    """
    Return the queryset of PaymentRefunds this user is authorized to see.
    """
    from payments.models import PaymentRefund

    if not user or not user.is_authenticated or not user.is_active:
        return PaymentRefund.objects.none()

    if user.is_superuser or user.is_staff:
        return PaymentRefund.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return PaymentRefund.objects.filter(payment__branch__in=accessible_branches)


def can_access_payment(user, payment) -> bool:
    """Return True if the user is allowed to see/act on this payment."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_branch(user, payment.branch)


def can_access_refund(user, refund) -> bool:
    """Return True if the user is allowed to see/act on this refund."""
    if not user or not user.is_authenticated or not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        return True
    return acl.can_access_branch(user, refund.payment.branch)
