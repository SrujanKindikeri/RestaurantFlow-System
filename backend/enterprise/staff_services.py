# =============================================================================
# RestaurantFlow — Staff Services
# Phase 20
#
# Business logic for:
#   - Staff branch assignment
#   - Staff transfer (request / approve / reject / complete)
#
# Rules:
#   - Users and roles remain authoritative in accounts app — not duplicated.
#   - Transfer must be within same restaurant.
#   - User must not have blocking operational sessions at source branch.
#   - Historical transactions retain their original branch context.
#   - StaffBranchAssignment is updated only when transfer is COMPLETED.
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from enterprise.constants import (
    TRANSFER_STATUS_REQUESTED,
    TRANSFER_STATUS_APPROVED,
    TRANSFER_STATUS_REJECTED,
    TRANSFER_STATUS_COMPLETED,
    TRANSFER_STATUS_CANCELLED,
    TRANSFER_TERMINAL_STATUSES,
    PERM_STAFF_ASSIGN,
    PERM_STAFF_TRANSFER,
    PERM_STAFF_TRANSFER_APPROVE,
    AUDIT_STAFF_ASSIGNED,
    AUDIT_STAFF_TRANSFER_REQUESTED,
    AUDIT_STAFF_TRANSFER_APPROVED,
    AUDIT_STAFF_TRANSFER_REJECTED,
    AUDIT_STAFF_TRANSFER_COMPLETED,
    WS_TRANSFER_CREATED,
    WS_TRANSFER_COMPLETED,
)
from enterprise.exceptions import StaffTransferBlockedError, StaffTransferScopeError
from enterprise.models import StaffBranchAssignment, StaffTransfer
from enterprise.validators import validate_transfer_scope
from enterprise.audit_services import record_audit

logger = logging.getLogger("enterprise")


def _require_auth(user):
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Authentication required.")


# ---------------------------------------------------------------------------
# Staff Branch Assignment
# ---------------------------------------------------------------------------

def assign_staff_to_branch(
    user_to_assign,
    branch,
    role,
    assigned_by,
    start_date=None,
    end_date=None,
    is_primary: bool = True,
) -> StaffBranchAssignment:
    """
    Assign a staff member to a branch.

    If is_primary=True and the user already has an active primary assignment
    in the same restaurant, the previous primary is deactivated first.

    Permissions: enterprise.staff.assign
    """
    _require_auth(assigned_by)
    if not acl.has_permission(assigned_by, PERM_STAFF_ASSIGN):
        raise PermissionDenied("You do not have permission to assign staff to branches.")
    if not acl.can_access_branch(assigned_by, branch):
        raise PermissionDenied("You do not have access to this branch.")

    restaurant = branch.restaurant
    company = restaurant.organization

    # Cross-restaurant check — user must belong to same org
    user_orgs = set(
        user_to_assign.role_assignments.filter(is_active=True)
        .values_list("organization_id", flat=True)
    )
    if company.pk not in user_orgs:
        raise ValidationError({
            "code": "STAFF_CROSS_ORG",
            "message": "Cannot assign a user from a different organization.",
        })

    with transaction.atomic():
        if is_primary:
            # Deactivate any existing primary assignment in this restaurant
            StaffBranchAssignment.objects.select_for_update().filter(
                user=user_to_assign,
                restaurant=restaurant,
                is_primary=True,
                is_active=True,
            ).update(is_active=False, updated_at=timezone.now())

        assignment = StaffBranchAssignment.objects.create(
            user=user_to_assign,
            restaurant=restaurant,
            branch=branch,
            role=role,
            assigned_by=assigned_by,
            start_date=start_date,
            end_date=end_date,
            is_primary=is_primary,
            is_active=True,
        )

    record_audit(
        action=AUDIT_STAFF_ASSIGNED,
        company=company,
        restaurant=restaurant,
        branch=branch,
        performed_by=assigned_by,
        description=f"{user_to_assign.email} assigned to '{branch.name}' as {role.name}.",
        source_type="StaffBranchAssignment",
        source_id=str(assignment.pk),
        metadata={
            "user": user_to_assign.email,
            "role": role.code,
            "is_primary": is_primary,
        },
    )
    logger.info(
        "staff_services: assigned user=%s to branch=%s role=%s by=%s",
        user_to_assign.email,
        branch.name,
        role.code,
        assigned_by.email,
    )
    return assignment


# ---------------------------------------------------------------------------
# Staff Transfer
# ---------------------------------------------------------------------------

def request_staff_transfer(
    user_to_transfer,
    source_branch,
    destination_branch,
    requested_by,
    reason: str,
) -> StaffTransfer:
    """
    Create a staff transfer request.

    Checks:
    1. source and destination are different.
    2. Both branches are in the same restaurant.
    3. User has an active assignment at source_branch.
    4. User does not have a blocking operational session.

    Permissions: enterprise.staff.transfer
    """
    _require_auth(requested_by)
    if not acl.has_permission(requested_by, PERM_STAFF_TRANSFER):
        raise PermissionDenied("You do not have permission to request staff transfers.")

    restaurant = source_branch.restaurant

    try:
        validate_transfer_scope(source_branch, destination_branch, user_to_transfer)
    except StaffTransferScopeError as exc:
        raise ValidationError({"code": exc.code, "message": exc.message})

    # User must have an active assignment at source branch
    source_assignment = StaffBranchAssignment.objects.filter(
        user=user_to_transfer,
        branch=source_branch,
        is_active=True,
    ).first()
    if not source_assignment:
        raise ValidationError({
            "code": "TRANSFER_NO_SOURCE_ASSIGNMENT",
            "message": f"{user_to_transfer.email} does not have an active assignment at {source_branch.name}.",
        })

    # Check for blocking operational sessions (counter sessions)
    _check_transfer_blockers(user_to_transfer, source_branch)

    # Check for pending transfers for this user
    pending = StaffTransfer.objects.filter(
        user=user_to_transfer,
        status__in={TRANSFER_STATUS_REQUESTED, TRANSFER_STATUS_APPROVED},
    ).first()
    if pending:
        raise ValidationError({
            "code": "TRANSFER_ALREADY_PENDING",
            "message": f"User already has a pending transfer (id={pending.pk}).",
        })

    with transaction.atomic():
        transfer = StaffTransfer.objects.create(
            user=user_to_transfer,
            restaurant=restaurant,
            source_branch=source_branch,
            destination_branch=destination_branch,
            requested_by=requested_by,
            reason=reason,
            status=TRANSFER_STATUS_REQUESTED,
        )

    company = restaurant.organization
    record_audit(
        action=AUDIT_STAFF_TRANSFER_REQUESTED,
        company=company,
        restaurant=restaurant,
        branch=source_branch,
        performed_by=requested_by,
        description=f"Transfer requested: {user_to_transfer.email} → {destination_branch.name}.",
        source_type="StaffTransfer",
        source_id=str(transfer.pk),
        metadata={"reason": reason},
    )

    _publish_ws_transfer(WS_TRANSFER_CREATED, transfer)
    logger.info(
        "staff_services: transfer requested user=%s %s→%s by=%s",
        user_to_transfer.email,
        source_branch.name,
        destination_branch.name,
        requested_by.email,
    )
    return transfer


def approve_staff_transfer(transfer, approved_by) -> StaffTransfer:
    """
    Approve a REQUESTED staff transfer.

    Permissions: enterprise.staff.transfer.approve
    """
    _require_auth(approved_by)
    if not acl.has_permission(approved_by, PERM_STAFF_TRANSFER_APPROVE):
        raise PermissionDenied("You do not have permission to approve staff transfers.")
    if not acl.can_access_restaurant(approved_by, transfer.restaurant):
        raise PermissionDenied("You do not have access to this transfer's restaurant.")

    if transfer.status != TRANSFER_STATUS_REQUESTED:
        raise ValidationError({
            "code": "TRANSFER_INVALID_STATUS",
            "message": f"Cannot approve a transfer in status '{transfer.status}'.",
        })

    with transaction.atomic():
        locked = StaffTransfer.objects.select_for_update().get(pk=transfer.pk)
        if locked.status != TRANSFER_STATUS_REQUESTED:
            raise ValidationError({
                "code": "TRANSFER_CONCURRENT_UPDATE",
                "message": "Transfer status changed concurrently.",
            })
        locked.status = TRANSFER_STATUS_APPROVED
        locked.approved_by = approved_by
        locked.approved_at = timezone.now()
        locked.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    company = transfer.restaurant.organization
    record_audit(
        action=AUDIT_STAFF_TRANSFER_APPROVED,
        company=company,
        restaurant=transfer.restaurant,
        performed_by=approved_by,
        description=f"Transfer approved: {transfer.user.email} → {transfer.destination_branch.name}.",
        source_type="StaffTransfer",
        source_id=str(transfer.pk),
    )

    _send_transfer_notification(locked, "approved")
    return locked


def reject_staff_transfer(transfer, rejected_by, rejection_reason: str = "") -> StaffTransfer:
    """
    Reject a REQUESTED staff transfer.

    Permissions: enterprise.staff.transfer.approve
    """
    _require_auth(rejected_by)
    if not acl.has_permission(rejected_by, PERM_STAFF_TRANSFER_APPROVE):
        raise PermissionDenied("You do not have permission to reject staff transfers.")
    if not acl.can_access_restaurant(rejected_by, transfer.restaurant):
        raise PermissionDenied("You do not have access to this transfer.")

    if transfer.status != TRANSFER_STATUS_REQUESTED:
        raise ValidationError({
            "code": "TRANSFER_INVALID_STATUS",
            "message": f"Cannot reject a transfer in status '{transfer.status}'.",
        })

    with transaction.atomic():
        locked = StaffTransfer.objects.select_for_update().get(pk=transfer.pk)
        locked.status = TRANSFER_STATUS_REJECTED
        locked.rejected_at = timezone.now()
        locked.rejection_reason = rejection_reason
        locked.save(update_fields=["status", "rejected_at", "rejection_reason", "updated_at"])

    company = transfer.restaurant.organization
    record_audit(
        action=AUDIT_STAFF_TRANSFER_REJECTED,
        company=company,
        restaurant=transfer.restaurant,
        performed_by=rejected_by,
        description=f"Transfer rejected: {transfer.user.email}. Reason: {rejection_reason}",
        source_type="StaffTransfer",
        source_id=str(transfer.pk),
    )

    _send_transfer_notification(locked, "rejected")
    return locked


def complete_staff_transfer(transfer, completed_by) -> StaffTransfer:
    """
    Complete an APPROVED staff transfer.

    Updates the user's StaffBranchAssignment to the destination branch.
    Historical transactions are NOT affected.

    Permissions: enterprise.staff.transfer.approve
    """
    _require_auth(completed_by)
    if not acl.has_permission(completed_by, PERM_STAFF_TRANSFER_APPROVE):
        raise PermissionDenied("You do not have permission to complete staff transfers.")
    if not acl.can_access_restaurant(completed_by, transfer.restaurant):
        raise PermissionDenied("You do not have access to this transfer.")

    if transfer.status != TRANSFER_STATUS_APPROVED:
        raise ValidationError({
            "code": "TRANSFER_INVALID_STATUS",
            "message": f"Cannot complete a transfer in status '{transfer.status}'.",
        })

    # Re-check blockers at completion time
    _check_transfer_blockers(transfer.user, transfer.source_branch)

    with transaction.atomic():
        locked = StaffTransfer.objects.select_for_update().get(pk=transfer.pk)
        if locked.status != TRANSFER_STATUS_APPROVED:
            raise ValidationError({
                "code": "TRANSFER_CONCURRENT_UPDATE",
                "message": "Transfer was modified concurrently.",
            })

        # Deactivate source branch assignment
        StaffBranchAssignment.objects.filter(
            user=locked.user,
            branch=locked.source_branch,
            is_active=True,
        ).update(is_active=False, updated_at=timezone.now())

        # Look up the role from the source assignment (may have been deactivated above — get last)
        source_assignment = StaffBranchAssignment.objects.filter(
            user=locked.user,
            branch=locked.source_branch,
        ).order_by("-assigned_at").first()

        role = source_assignment.role if source_assignment else None

        # Create new assignment at destination
        if role:
            StaffBranchAssignment.objects.create(
                user=locked.user,
                restaurant=locked.restaurant,
                branch=locked.destination_branch,
                role=role,
                assigned_by=completed_by,
                is_primary=True,
                is_active=True,
            )

        locked.status = TRANSFER_STATUS_COMPLETED
        locked.completed_at = timezone.now()
        locked.save(update_fields=["status", "completed_at", "updated_at"])

    company = transfer.restaurant.organization
    record_audit(
        action=AUDIT_STAFF_TRANSFER_COMPLETED,
        company=company,
        restaurant=locked.restaurant,
        branch=locked.destination_branch,
        performed_by=completed_by,
        description=(
            f"Transfer completed: {locked.user.email} "
            f"moved from {locked.source_branch.name} to {locked.destination_branch.name}."
        ),
        source_type="StaffTransfer",
        source_id=str(locked.pk),
    )

    _publish_ws_transfer(WS_TRANSFER_COMPLETED, locked)
    _send_transfer_notification(locked, "completed")
    logger.info(
        "staff_services: transfer completed user=%s %s→%s",
        locked.user.email,
        locked.source_branch.name,
        locked.destination_branch.name,
    )
    return locked


def cancel_staff_transfer(transfer, cancelled_by) -> StaffTransfer:
    """Cancel a REQUESTED or APPROVED transfer."""
    _require_auth(cancelled_by)
    if not acl.can_access_restaurant(cancelled_by, transfer.restaurant):
        raise PermissionDenied("You do not have access to this transfer.")

    if transfer.status in TRANSFER_TERMINAL_STATUSES:
        raise ValidationError({
            "code": "TRANSFER_ALREADY_TERMINAL",
            "message": f"Transfer is already in terminal status '{transfer.status}'.",
        })

    with transaction.atomic():
        locked = StaffTransfer.objects.select_for_update().get(pk=transfer.pk)
        locked.status = TRANSFER_STATUS_CANCELLED
        locked.save(update_fields=["status", "updated_at"])

    return locked


# ---------------------------------------------------------------------------
# Blockers check
# ---------------------------------------------------------------------------

def _check_transfer_blockers(user_to_transfer, source_branch) -> None:
    """
    Raise StaffTransferBlockedError if the user has active operational sessions
    at the source branch.
    """
    try:
        from counters.models import CounterSession, SessionStatus
        open_sessions = CounterSession.objects.filter(
            counter__branch=source_branch,
            opened_by=user_to_transfer,
            status=SessionStatus.OPEN,
        ).count()
        if open_sessions:
            raise StaffTransferBlockedError(
                f"{user_to_transfer.email} has {open_sessions} open counter session(s) "
                f"at {source_branch.name}. Close the session before transferring.",
                code="STAFF_HAS_OPEN_COUNTER_SESSION",
            )
    except StaffTransferBlockedError:
        raise
    except Exception as e:
        logger.warning("staff_services: blocker check failed (non-fatal): %s", e)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _publish_ws_transfer(event_type: str, transfer) -> None:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        group = f"enterprise_org_{transfer.restaurant.organization_id}"
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "enterprise_event",
                "event": event_type,
                "payload": {
                    "transfer_id": str(transfer.pk),
                    "user": transfer.user.email,
                    "status": transfer.status,
                },
            },
        )
    except Exception as exc:
        logger.warning("staff_services: WS publish failed (non-fatal): %s", exc)


def _send_transfer_notification(transfer, outcome: str) -> None:
    try:
        from enterprise.constants import NOTIF_TRANSFER_APPROVED, NOTIF_TRANSFER_REJECTED
        from notifications.services import create_and_dispatch

        notif_type = (
            NOTIF_TRANSFER_APPROVED if outcome in {"approved", "completed"}
            else NOTIF_TRANSFER_REJECTED
        )
        company = transfer.restaurant.organization
        create_and_dispatch(
            company=company,
            restaurant=transfer.restaurant,
            notification_type=notif_type,
            severity="MEDIUM",
            title=f"Staff transfer {outcome}: {transfer.user.email}",
            message=(
                f"Transfer of {transfer.user.email} from "
                f"{transfer.source_branch.name} to {transfer.destination_branch.name} "
                f"has been {outcome}."
            ),
            source_type="StaffTransfer",
            source_id=str(transfer.pk),
        )
    except Exception as exc:
        logger.warning("staff_services: notification failed (non-fatal): %s", exc)
