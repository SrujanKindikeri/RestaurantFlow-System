# =============================================================================
# RestaurantFlow — Operations Access Control
# Phase 19: Advanced POS & Restaurant Operations
#
# Single source of truth for operations authorization.
# Views and serializers delegate here — never duplicate access logic.
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("operations")


def get_accessible_pos_sessions(user):
    """Return POSSessions visible to this user."""
    from operations.models import POSSession

    if not user or not user.is_authenticated or not user.is_active:
        return POSSession.objects.none()
    if user.is_superuser or user.is_staff:
        return POSSession.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return POSSession.objects.filter(branch__in=accessible_branches)


def get_accessible_shifts(user):
    """Return OperationalShifts visible to this user."""
    from operations.models import OperationalShift

    if not user or not user.is_authenticated or not user.is_active:
        return OperationalShift.objects.none()
    if user.is_superuser or user.is_staff:
        return OperationalShift.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return OperationalShift.objects.filter(branch__in=accessible_branches)


def get_accessible_table_transfers(user):
    """Return TableTransfers visible to this user."""
    from operations.models import TableTransfer

    if not user or not user.is_authenticated or not user.is_active:
        return TableTransfer.objects.none()
    if user.is_superuser or user.is_staff:
        return TableTransfer.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return TableTransfer.objects.filter(
        source_table__branch__in=accessible_branches
    )


def get_accessible_bill_splits(user):
    """Return BillSplits visible to this user."""
    from operations.models import BillSplit

    if not user or not user.is_authenticated or not user.is_active:
        return BillSplit.objects.none()
    if user.is_superuser or user.is_staff:
        return BillSplit.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return BillSplit.objects.filter(bill__branch__in=accessible_branches)


def get_accessible_modifier_groups(user):
    """Return MenuModifierGroups visible to this user."""
    from operations.models import MenuModifierGroup

    if not user or not user.is_authenticated or not user.is_active:
        return MenuModifierGroup.objects.none()
    if user.is_superuser or user.is_staff:
        return MenuModifierGroup.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    restaurant_ids = accessible_branches.values_list(
        "restaurant_id", flat=True
    ).distinct()
    return MenuModifierGroup.objects.filter(restaurant_id__in=restaurant_ids)


def get_accessible_change_requests(user):
    """Return OrderChangeRequests visible to this user."""
    from operations.models import OrderChangeRequest

    if not user or not user.is_authenticated or not user.is_active:
        return OrderChangeRequest.objects.none()
    if user.is_superuser or user.is_staff:
        return OrderChangeRequest.objects.all()

    accessible_branches = acl.get_accessible_branches(user)
    return OrderChangeRequest.objects.filter(
        order__branch__in=accessible_branches
    )


def can_access_pos_session(user, session) -> bool:
    return get_accessible_pos_sessions(user).filter(pk=session.pk).exists()


def can_access_shift(user, shift) -> bool:
    return get_accessible_shifts(user).filter(pk=shift.pk).exists()


def can_access_bill_split(user, split) -> bool:
    return get_accessible_bill_splits(user).filter(pk=split.pk).exists()
