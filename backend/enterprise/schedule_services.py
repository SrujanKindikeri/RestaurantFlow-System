# =============================================================================
# RestaurantFlow — Schedule Services
# Phase 20
#
# Business logic for:
#   - Branch operating hours (CRUD, upsert per day)
#   - Branch closure schedules (create, approve, reject, cancel)
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from enterprise.constants import (
    CLOSURE_STATUS_DRAFT,
    CLOSURE_STATUS_PENDING_APPROVAL,
    CLOSURE_STATUS_APPROVED,
    CLOSURE_STATUS_REJECTED,
    CLOSURE_STATUS_CANCELLED,
    CLOSURE_STATUS_ACTIVE,
    CLOSURE_STATUS_COMPLETED,
    PERM_SCHEDULE_MANAGE,
    PERM_SCHEDULE_VIEW,
    WS_SCHEDULE_UPDATED,
)
from enterprise.exceptions import ScheduleOverlapError
from enterprise.models import BranchOperatingHour, BranchClosure
from enterprise.validators import validate_operating_hours, validate_no_closure_overlap
from enterprise.audit_services import record_audit

logger = logging.getLogger("enterprise")


def _require_auth(user):
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Authentication required.")


# ---------------------------------------------------------------------------
# Operating Hours
# ---------------------------------------------------------------------------

def upsert_operating_hour(
    branch,
    day_of_week: str,
    opening_time,
    closing_time,
    is_closed: bool,
    user,
) -> BranchOperatingHour:
    """
    Create or update the operating hour for (branch, day_of_week).

    Uses get_or_create + update pattern to avoid duplicate-key races.
    Validates times and overnight schedules before persisting.

    Permissions: enterprise.schedule.manage
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_SCHEDULE_MANAGE):
        raise PermissionDenied("You do not have permission to manage branch schedules.")
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    try:
        validate_operating_hours(
            branch_id=branch.pk,
            day_of_week=day_of_week,
            opening_time=opening_time,
            closing_time=closing_time,
            is_closed=is_closed,
        )
    except ValueError as exc:
        raise ValidationError({"code": "SCHEDULE_VALIDATION_ERROR", "message": str(exc)})

    with transaction.atomic():
        hour, created = BranchOperatingHour.objects.select_for_update().get_or_create(
            branch=branch,
            day_of_week=day_of_week,
            defaults={
                "opening_time": opening_time if not is_closed else None,
                "closing_time": closing_time if not is_closed else None,
                "is_closed": is_closed,
            },
        )
        if not created:
            hour.opening_time = opening_time if not is_closed else None
            hour.closing_time = closing_time if not is_closed else None
            hour.is_closed = is_closed
            hour.save(update_fields=["opening_time", "closing_time", "is_closed", "updated_at"])

    _publish_ws_schedule(branch)
    logger.info(
        "schedule_services: operating_hour branch=%s day=%s is_closed=%s by=%s",
        branch.name,
        day_of_week,
        is_closed,
        user.email,
    )
    return hour


def bulk_upsert_operating_hours(branch, hours_data: list, user) -> list:
    """
    Upsert a full week's schedule in one call.

    hours_data: list of dicts with keys:
        {day_of_week, opening_time, closing_time, is_closed}

    Returns list of BranchOperatingHour instances.
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_SCHEDULE_MANAGE):
        raise PermissionDenied("You do not have permission to manage branch schedules.")
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    results = []
    for entry in hours_data:
        hour = upsert_operating_hour(
            branch=branch,
            day_of_week=entry["day_of_week"],
            opening_time=entry.get("opening_time"),
            closing_time=entry.get("closing_time"),
            is_closed=entry.get("is_closed", False),
            user=user,
        )
        results.append(hour)
    return results


# ---------------------------------------------------------------------------
# Branch Closure
# ---------------------------------------------------------------------------

def create_branch_closure(
    branch,
    closure_type: str,
    start_datetime,
    end_datetime,
    reason: str,
    user,
    auto_approve: bool = False,
) -> BranchClosure:
    """
    Create a new BranchClosure record.

    Validates no overlap with existing non-terminal closures.
    If auto_approve=True (e.g. for emergency closures by owner), sets status
    to APPROVED directly; otherwise starts as DRAFT.

    Permissions: enterprise.schedule.manage
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_SCHEDULE_MANAGE):
        raise PermissionDenied("You do not have permission to manage branch closures.")
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    if end_datetime <= start_datetime:
        raise ValidationError({
            "code": "CLOSURE_INVALID_DATES",
            "message": "End datetime must be after start datetime.",
        })

    try:
        validate_no_closure_overlap(branch.pk, start_datetime, end_datetime)
    except ValueError as exc:
        raise ValidationError({"code": "CLOSURE_OVERLAP", "message": str(exc)})

    initial_status = CLOSURE_STATUS_APPROVED if auto_approve else CLOSURE_STATUS_DRAFT

    with transaction.atomic():
        closure = BranchClosure.objects.create(
            branch=branch,
            closure_type=closure_type,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            reason=reason,
            status=initial_status,
            created_by=user,
            approved_by=user if auto_approve else None,
            approved_at=timezone.now() if auto_approve else None,
        )

    logger.info(
        "schedule_services: closure created branch=%s type=%s status=%s by=%s",
        branch.name,
        closure_type,
        initial_status,
        user.email,
    )
    return closure


def approve_branch_closure(closure, user) -> BranchClosure:
    """
    Approve a DRAFT or PENDING_APPROVAL branch closure.

    Permissions: enterprise.schedule.manage
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_SCHEDULE_MANAGE):
        raise PermissionDenied("You do not have permission to approve branch closures.")
    if not acl.can_access_branch(user, closure.branch):
        raise PermissionDenied("You do not have access to this branch.")

    allowed_from = {CLOSURE_STATUS_DRAFT, CLOSURE_STATUS_PENDING_APPROVAL}
    if closure.status not in allowed_from:
        raise ValidationError({
            "code": "CLOSURE_INVALID_STATUS",
            "message": f"Cannot approve a closure in status '{closure.status}'.",
        })

    with transaction.atomic():
        locked = BranchClosure.objects.select_for_update().get(pk=closure.pk)
        if locked.status not in allowed_from:
            raise ValidationError({
                "code": "CLOSURE_CONCURRENT_UPDATE",
                "message": "Closure status changed concurrently.",
            })
        locked.status = CLOSURE_STATUS_APPROVED
        locked.approved_by = user
        locked.approved_at = timezone.now()
        locked.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    _send_closure_notification(locked, user)
    _publish_ws_schedule(locked.branch)
    return locked


def reject_branch_closure(closure, user, rejection_reason: str = "") -> BranchClosure:
    """Reject a DRAFT or PENDING_APPROVAL closure."""
    _require_auth(user)
    if not acl.has_permission(user, PERM_SCHEDULE_MANAGE):
        raise PermissionDenied("You do not have permission to reject branch closures.")
    if not acl.can_access_branch(user, closure.branch):
        raise PermissionDenied("You do not have access to this branch.")

    allowed_from = {CLOSURE_STATUS_DRAFT, CLOSURE_STATUS_PENDING_APPROVAL}
    if closure.status not in allowed_from:
        raise ValidationError({
            "code": "CLOSURE_INVALID_STATUS",
            "message": f"Cannot reject a closure in status '{closure.status}'.",
        })

    with transaction.atomic():
        locked = BranchClosure.objects.select_for_update().get(pk=closure.pk)
        locked.status = CLOSURE_STATUS_REJECTED
        locked.rejected_at = timezone.now()
        locked.rejection_reason = rejection_reason
        locked.save(update_fields=["status", "rejected_at", "rejection_reason", "updated_at"])

    return locked


def cancel_branch_closure(closure, user) -> BranchClosure:
    """Cancel a DRAFT, PENDING_APPROVAL, or APPROVED closure."""
    _require_auth(user)
    if not acl.has_permission(user, PERM_SCHEDULE_MANAGE):
        raise PermissionDenied("You do not have permission to cancel branch closures.")
    if not acl.can_access_branch(user, closure.branch):
        raise PermissionDenied("You do not have access to this branch.")

    cancellable = {
        CLOSURE_STATUS_DRAFT,
        CLOSURE_STATUS_PENDING_APPROVAL,
        CLOSURE_STATUS_APPROVED,
    }
    if closure.status not in cancellable:
        raise ValidationError({
            "code": "CLOSURE_CANNOT_CANCEL",
            "message": f"Closure in status '{closure.status}' cannot be cancelled.",
        })

    with transaction.atomic():
        locked = BranchClosure.objects.select_for_update().get(pk=closure.pk)
        if locked.status not in cancellable:
            raise ValidationError({
                "code": "CLOSURE_CONCURRENT_UPDATE",
                "message": "Closure was already modified by another user.",
            })
        locked.status = CLOSURE_STATUS_CANCELLED
        locked.save(update_fields=["status", "updated_at"])

    _publish_ws_schedule(locked.branch)
    return locked


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _publish_ws_schedule(branch) -> None:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        group = f"enterprise_org_{branch.restaurant.organization_id}"
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "enterprise_event",
                "event": WS_SCHEDULE_UPDATED,
                "payload": {"branch_id": str(branch.pk)},
            },
        )
    except Exception as exc:
        logger.warning("schedule_services: WS publish failed (non-fatal): %s", exc)


def _send_closure_notification(closure, actor) -> None:
    try:
        from enterprise.constants import NOTIF_BRANCH_CLOSURE_APPROVED
        from notifications.services import create_and_dispatch
        company = closure.branch.restaurant.organization
        create_and_dispatch(
            company=company,
            restaurant=closure.branch.restaurant,
            branch=closure.branch,
            notification_type=NOTIF_BRANCH_CLOSURE_APPROVED,
            severity="MEDIUM",
            title=f"Branch closure approved: {closure.branch.name}",
            message=(
                f"Closure of '{closure.branch.name}' from "
                f"{closure.start_datetime.strftime('%Y-%m-%d %H:%M')} to "
                f"{closure.end_datetime.strftime('%Y-%m-%d %H:%M')} has been approved."
            ),
            source_type="BranchClosure",
            source_id=str(closure.pk),
        )
    except Exception as exc:
        logger.warning("schedule_services: closure notification failed (non-fatal): %s", exc)
