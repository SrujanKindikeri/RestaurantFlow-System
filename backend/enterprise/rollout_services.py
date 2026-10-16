# =============================================================================
# RestaurantFlow — Rollout Services
# Phase 20
#
# Business logic for:
#   - Menu availability rollouts (enable/disable a MenuItem across branches)
#   - Price rollouts (apply a price to multiple branches)
#   - Rollout preview (what WILL change vs what is already overridden)
#   - Rollout approve / execute / cancel
#
# Key rules:
#   - Branch-specific overrides are preserved unless force_override=True.
#   - Only one RUNNING rollout per menu_item per restaurant at a time.
#   - Partial failures are recorded per branch — the rollout continues.
#   - Audit + notification happen AFTER the transaction commits.
# =============================================================================

import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from enterprise.constants import (
    ROLLOUT_STATUS_DRAFT,
    ROLLOUT_STATUS_PENDING_APPROVAL,
    ROLLOUT_STATUS_APPROVED,
    ROLLOUT_STATUS_RUNNING,
    ROLLOUT_STATUS_COMPLETED,
    ROLLOUT_STATUS_PARTIALLY_COMPLETED,
    ROLLOUT_STATUS_FAILED,
    ROLLOUT_STATUS_CANCELLED,
    ROLLOUT_STATUS_TERMINAL_STATUSES,
    ROLLOUT_ACTIVE_STATUSES,
    ROLLOUT_SCOPE_ALL_BRANCHES,
    ROLLOUT_SCOPE_SELECTED_BRANCHES,
    ROLLOUT_TYPE_MENU_AVAILABILITY,
    ROLLOUT_TYPE_PRICE,
    PERM_ROLLOUT_CREATE,
    PERM_ROLLOUT_APPROVE,
    PERM_ROLLOUT_EXECUTE,
    PERM_ROLLOUT_CANCEL,
    PERM_ROLLOUT_PREVIEW,
    AUDIT_ROLLOUT_CREATED,
    AUDIT_ROLLOUT_APPROVED,
    AUDIT_ROLLOUT_EXECUTED,
    AUDIT_ROLLOUT_FAILED,
    AUDIT_PRICE_ROLLOUT_CREATED,
    AUDIT_PRICE_ROLLOUT_EXECUTED,
    WS_ROLLOUT_CREATED,
    WS_ROLLOUT_COMPLETED,
    WS_ROLLOUT_FAILED,
)
from enterprise.exceptions import RolloutNotExecutableError
from enterprise.models import MenuRollout, MenuRolloutBranch
from enterprise.audit_services import record_audit

logger = logging.getLogger("enterprise")


def _require_auth(user):
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Authentication required.")


# ---------------------------------------------------------------------------
# Rollout creation
# ---------------------------------------------------------------------------

def create_menu_rollout(
    restaurant,
    menu_item,
    target_scope: str,
    is_available: bool,
    user,
    target_branch_ids: list = None,
    source_branch=None,
    force_override: bool = False,
    notes: str = "",
) -> MenuRollout:
    """
    Create a MENU_AVAILABILITY rollout.

    target_scope: ALL_BRANCHES | SELECTED_BRANCHES
    target_branch_ids: required when target_scope=SELECTED_BRANCHES

    Permissions: enterprise.rollout.create
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_ROLLOUT_CREATE):
        raise PermissionDenied("You do not have permission to create rollouts.")
    if not acl.can_access_restaurant(user, restaurant):
        raise PermissionDenied("You do not have access to this restaurant.")

    # Prevent duplicate active rollouts for the same item
    _check_no_active_rollout(restaurant, menu_item)

    # Validate branch scope
    target_branches = _resolve_target_branches(
        restaurant, target_scope, target_branch_ids
    )

    with transaction.atomic():
        rollout = MenuRollout.objects.create(
            restaurant=restaurant,
            menu_item=menu_item,
            rollout_type=ROLLOUT_TYPE_MENU_AVAILABILITY,
            is_available=is_available,
            target_scope=target_scope,
            source_branch=source_branch,
            force_override=force_override,
            status=ROLLOUT_STATUS_DRAFT,
            created_by=user,
            notes=notes,
        )
        if target_scope == ROLLOUT_SCOPE_SELECTED_BRANCHES:
            rollout.target_branches.set(target_branches)

    record_audit(
        action=AUDIT_ROLLOUT_CREATED,
        company=restaurant.organization,
        restaurant=restaurant,
        performed_by=user,
        description=f"Menu rollout created for '{menu_item.name}' ({target_scope}).",
        source_type="MenuRollout",
        source_id=str(rollout.pk),
        metadata={"is_available": is_available, "force_override": force_override},
    )
    _publish_ws_rollout(WS_ROLLOUT_CREATED, rollout)
    logger.info(
        "rollout_services: created rollout=%s item=%s by=%s",
        rollout.pk,
        menu_item.name,
        user.email,
    )
    return rollout


def create_price_rollout(
    restaurant,
    menu_item,
    new_price: Decimal,
    target_scope: str,
    user,
    target_branch_ids: list = None,
    force_override: bool = False,
    effective_from=None,
    notes: str = "",
) -> MenuRollout:
    """
    Create a PRICE rollout.

    Permissions: enterprise.rollout.create
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_ROLLOUT_CREATE):
        raise PermissionDenied("You do not have permission to create rollouts.")
    if not acl.can_access_restaurant(user, restaurant):
        raise PermissionDenied("You do not have access to this restaurant.")

    new_price = Decimal(str(new_price))
    if new_price < 0:
        raise ValidationError({"code": "INVALID_PRICE", "message": "Price cannot be negative."})

    _check_no_active_rollout(restaurant, menu_item)
    target_branches = _resolve_target_branches(
        restaurant, target_scope, target_branch_ids
    )

    with transaction.atomic():
        rollout = MenuRollout.objects.create(
            restaurant=restaurant,
            menu_item=menu_item,
            rollout_type=ROLLOUT_TYPE_PRICE,
            new_price=new_price,
            target_scope=target_scope,
            force_override=force_override,
            effective_from=effective_from,
            status=ROLLOUT_STATUS_DRAFT,
            created_by=user,
            notes=notes,
        )
        if target_scope == ROLLOUT_SCOPE_SELECTED_BRANCHES:
            rollout.target_branches.set(target_branches)

    record_audit(
        action=AUDIT_PRICE_ROLLOUT_CREATED,
        company=restaurant.organization,
        restaurant=restaurant,
        performed_by=user,
        description=f"Price rollout created for '{menu_item.name}' → ₹{new_price}.",
        source_type="MenuRollout",
        source_id=str(rollout.pk),
        metadata={"new_price": str(new_price), "force_override": force_override},
    )
    _publish_ws_rollout(WS_ROLLOUT_CREATED, rollout)
    return rollout


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def preview_rollout(rollout, user) -> dict:
    """
    Return a preview of what the rollout WILL change.

    For each target branch shows:
        current_value, new_value, will_change, skip_reason

    Permissions: enterprise.rollout.preview
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_ROLLOUT_PREVIEW):
        raise PermissionDenied("You do not have permission to preview rollouts.")
    if not acl.can_access_restaurant(user, rollout.restaurant):
        raise PermissionDenied("You do not have access to this rollout's restaurant.")

    target_branches = _get_target_branches_for_rollout(rollout)
    branch_previews = []

    for branch in target_branches:
        preview = _preview_single_branch(rollout, branch)
        branch_previews.append(preview)

    will_change = [p for p in branch_previews if p["will_change"]]
    will_skip   = [p for p in branch_previews if not p["will_change"]]

    return {
        "rollout_id": str(rollout.pk),
        "rollout_type": rollout.rollout_type,
        "menu_item": {"id": str(rollout.menu_item.pk), "name": rollout.menu_item.name},
        "target_scope": rollout.target_scope,
        "force_override": rollout.force_override,
        "total_branches": len(branch_previews),
        "will_change_count": len(will_change),
        "will_skip_count": len(will_skip),
        "branches": branch_previews,
    }


def _preview_single_branch(rollout, branch) -> dict:
    from menu.models import MenuItemPrice, MenuItemBranch

    will_change = True
    skip_reason = None
    current_value = None
    new_value = None

    if rollout.rollout_type == ROLLOUT_TYPE_PRICE:
        # Check for branch-specific override
        branch_price = MenuItemPrice.objects.filter(
            menu_item=rollout.menu_item,
            branch=branch,
            is_active=True,
        ).first()
        current_value = str(branch_price.price) if branch_price else None
        new_value = str(rollout.new_price)

        has_override = branch_price is not None
        if has_override and not rollout.force_override:
            will_change = False
            skip_reason = "Branch has an active price override — use force_override=True to overwrite."

    elif rollout.rollout_type == ROLLOUT_TYPE_MENU_AVAILABILITY:
        mib = MenuItemBranch.objects.filter(
            menu_item=rollout.menu_item,
            branch=branch,
        ).first()
        current_value = str(mib.is_available) if mib else None
        new_value = str(rollout.is_available)

        # If availability is already the same value, skip
        if mib and mib.is_available == rollout.is_available:
            will_change = False
            skip_reason = f"Branch already has is_available={rollout.is_available}."

    return {
        "branch_id": str(branch.pk),
        "branch_name": branch.name,
        "branch_code": branch.code,
        "current_value": current_value,
        "new_value": new_value,
        "will_change": will_change,
        "skip_reason": skip_reason,
    }


# ---------------------------------------------------------------------------
# Approval
# ---------------------------------------------------------------------------

def approve_rollout(rollout, user) -> MenuRollout:
    """
    Approve a rollout that is in DRAFT or PENDING_APPROVAL.

    Permissions: enterprise.rollout.approve
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_ROLLOUT_APPROVE):
        raise PermissionDenied("You do not have permission to approve rollouts.")
    if not acl.can_access_restaurant(user, rollout.restaurant):
        raise PermissionDenied("You do not have access to this rollout.")

    if rollout.status not in {ROLLOUT_STATUS_DRAFT, ROLLOUT_STATUS_PENDING_APPROVAL}:
        raise ValidationError({
            "code": "ROLLOUT_INVALID_STATUS",
            "message": f"Cannot approve rollout in status '{rollout.status}'.",
        })

    with transaction.atomic():
        locked = MenuRollout.objects.select_for_update().get(pk=rollout.pk)
        locked.status = ROLLOUT_STATUS_APPROVED
        locked.approved_by = user
        locked.approved_at = timezone.now()
        locked.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])

    record_audit(
        action=AUDIT_ROLLOUT_APPROVED,
        company=rollout.restaurant.organization,
        restaurant=rollout.restaurant,
        performed_by=user,
        description=f"Rollout '{rollout.menu_item.name}' approved.",
        source_type="MenuRollout",
        source_id=str(rollout.pk),
    )
    return locked


# ---------------------------------------------------------------------------
# Execute
# ---------------------------------------------------------------------------

def execute_rollout(rollout, user) -> dict:
    """
    Execute an APPROVED rollout.

    Applies changes branch by branch — records a MenuRolloutBranch per branch.
    Partial failures do NOT abort the entire rollout.

    Permissions: enterprise.rollout.execute

    Returns an operation result dict:
        {successful, failed, skipped, warnings}
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_ROLLOUT_EXECUTE):
        raise PermissionDenied("You do not have permission to execute rollouts.")
    if not acl.can_access_restaurant(user, rollout.restaurant):
        raise PermissionDenied("You do not have access to this rollout.")

    executable_statuses = {ROLLOUT_STATUS_APPROVED, ROLLOUT_STATUS_DRAFT}
    if rollout.status not in executable_statuses:
        raise RolloutNotExecutableError(
            f"Rollout cannot be executed from status '{rollout.status}'. "
            f"Executable statuses: {executable_statuses}",
        )

    # Mark RUNNING atomically — prevents concurrent execution
    with transaction.atomic():
        locked = MenuRollout.objects.select_for_update().get(pk=rollout.pk)
        if locked.status not in executable_statuses:
            raise RolloutNotExecutableError(
                f"Rollout status changed concurrently to '{locked.status}'."
            )
        locked.status = ROLLOUT_STATUS_RUNNING
        locked.save(update_fields=["status", "updated_at"])

    target_branches = _get_target_branches_for_rollout(locked)

    result = {
        "successful": [],
        "failed": [],
        "skipped": [],
        "warnings": [],
    }

    for branch in target_branches:
        try:
            outcome = _execute_single_branch(locked, branch)
            if outcome["result"] in {
                MenuRolloutBranch.RESULT_SKIPPED,
                MenuRolloutBranch.RESULT_OVERRIDE,
            }:
                result["skipped"].append({
                    "branch_id": str(branch.pk),
                    "branch_name": branch.name,
                    "reason": outcome.get("skip_reason"),
                })
            else:
                result["successful"].append({
                    "branch_id": str(branch.pk),
                    "branch_name": branch.name,
                })
        except Exception as exc:
            logger.warning(
                "rollout_services: branch=%s failed during rollout=%s — %s",
                branch.name,
                locked.pk,
                exc,
            )
            result["failed"].append({
                "branch_id": str(branch.pk),
                "branch_name": branch.name,
                "error": str(exc),
            })
            # Record per-branch failure
            MenuRolloutBranch.objects.get_or_create(
                rollout=locked,
                branch=branch,
                defaults={
                    "result": MenuRolloutBranch.RESULT_FAILED,
                    "failure_reason": str(exc),
                },
            )

    # Determine final rollout status
    n_success = len(result["successful"])
    n_failed  = len(result["failed"])
    n_total   = len(target_branches)

    if n_failed == 0:
        final_status = ROLLOUT_STATUS_COMPLETED
    elif n_success == 0:
        final_status = ROLLOUT_STATUS_FAILED
    else:
        final_status = ROLLOUT_STATUS_PARTIALLY_COMPLETED

    with transaction.atomic():
        locked = MenuRollout.objects.select_for_update().get(pk=rollout.pk)
        locked.status = final_status
        locked.completed_at = timezone.now()
        locked.save(update_fields=["status", "completed_at", "updated_at"])

    audit_action = (
        AUDIT_ROLLOUT_EXECUTED
        if locked.rollout_type == ROLLOUT_TYPE_MENU_AVAILABILITY
        else AUDIT_PRICE_ROLLOUT_EXECUTED
    )
    record_audit(
        action=audit_action,
        company=locked.restaurant.organization,
        restaurant=locked.restaurant,
        performed_by=user,
        description=(
            f"Rollout '{locked.menu_item.name}' executed: "
            f"{n_success}/{n_total} branches succeeded."
        ),
        source_type="MenuRollout",
        source_id=str(locked.pk),
        metadata={"successful": n_success, "failed": n_failed, "total": n_total},
    )

    ws_event = WS_ROLLOUT_COMPLETED if final_status == ROLLOUT_STATUS_COMPLETED else WS_ROLLOUT_FAILED
    _publish_ws_rollout(ws_event, locked)
    _send_rollout_notification(locked, result)

    logger.info(
        "rollout_services: rollout=%s final_status=%s success=%d failed=%d",
        locked.pk,
        final_status,
        n_success,
        n_failed,
    )
    return result


def _execute_single_branch(rollout, branch) -> dict:
    """
    Apply the rollout to a single branch inside a per-branch atomic block.
    Records a MenuRolloutBranch result row.
    """
    from menu.models import MenuItemPrice, MenuItemBranch

    with transaction.atomic():
        if rollout.rollout_type == ROLLOUT_TYPE_PRICE:
            return _apply_price_to_branch(rollout, branch)
        elif rollout.rollout_type == ROLLOUT_TYPE_MENU_AVAILABILITY:
            return _apply_availability_to_branch(rollout, branch)
        else:
            raise ValueError(f"Unknown rollout_type: {rollout.rollout_type}")


def _apply_price_to_branch(rollout, branch) -> dict:
    from menu.models import MenuItemPrice
    from django.utils import timezone as tz

    # Check for existing branch-specific override
    existing = MenuItemPrice.objects.select_for_update().filter(
        menu_item=rollout.menu_item,
        branch=branch,
        is_active=True,
    ).first()

    if existing and not rollout.force_override:
        MenuRolloutBranch.objects.create(
            rollout=rollout,
            branch=branch,
            result=MenuRolloutBranch.RESULT_OVERRIDE,
            old_value=str(existing.price),
            new_value=str(rollout.new_price),
        )
        return {"result": MenuRolloutBranch.RESULT_OVERRIDE, "skip_reason": "Branch override preserved."}

    # Deactivate current price
    if existing:
        existing.is_active = False
        existing.effective_to = tz.now()
        existing.save(update_fields=["is_active", "effective_to", "updated_at"])

    old_price = str(existing.price) if existing else None

    # Create new price row
    MenuItemPrice.objects.create(
        menu_item=rollout.menu_item,
        branch=branch,
        price=rollout.new_price,
        effective_from=rollout.effective_from or tz.now(),
        is_active=True,
    )

    MenuRolloutBranch.objects.create(
        rollout=rollout,
        branch=branch,
        result=MenuRolloutBranch.RESULT_SUCCESS,
        old_value=old_price or "",
        new_value=str(rollout.new_price),
    )
    return {"result": MenuRolloutBranch.RESULT_SUCCESS}


def _apply_availability_to_branch(rollout, branch) -> dict:
    from menu.models import MenuItemBranch

    mib, created = MenuItemBranch.objects.select_for_update().get_or_create(
        menu_item=rollout.menu_item,
        branch=branch,
        defaults={"is_available": rollout.is_available},
    )

    if not created and mib.is_available == rollout.is_available and not rollout.force_override:
        MenuRolloutBranch.objects.create(
            rollout=rollout,
            branch=branch,
            result=MenuRolloutBranch.RESULT_SKIPPED,
            old_value=str(mib.is_available),
            new_value=str(rollout.is_available),
        )
        return {
            "result": MenuRolloutBranch.RESULT_SKIPPED,
            "skip_reason": "Branch already has the target availability state.",
        }

    old_value = str(mib.is_available)
    mib.is_available = rollout.is_available
    mib.save(update_fields=["is_available", "updated_at"])

    MenuRolloutBranch.objects.create(
        rollout=rollout,
        branch=branch,
        result=MenuRolloutBranch.RESULT_SUCCESS,
        old_value=old_value,
        new_value=str(rollout.is_available),
    )
    return {"result": MenuRolloutBranch.RESULT_SUCCESS}


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

def cancel_rollout(rollout, user, reason: str = "") -> MenuRollout:
    """
    Cancel a rollout that has not yet started or completed.

    Permissions: enterprise.rollout.cancel
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_ROLLOUT_CANCEL):
        raise PermissionDenied("You do not have permission to cancel rollouts.")
    if not acl.can_access_restaurant(user, rollout.restaurant):
        raise PermissionDenied("You do not have access to this rollout.")

    if rollout.status in ROLLOUT_STATUS_TERMINAL_STATUSES:
        raise ValidationError({
            "code": "ROLLOUT_ALREADY_TERMINAL",
            "message": f"Rollout is already in terminal status '{rollout.status}'.",
        })
    if rollout.status == ROLLOUT_STATUS_RUNNING:
        raise ValidationError({
            "code": "ROLLOUT_RUNNING",
            "message": "Cannot cancel a rollout while it is running.",
        })

    with transaction.atomic():
        locked = MenuRollout.objects.select_for_update().get(pk=rollout.pk)
        locked.status = ROLLOUT_STATUS_CANCELLED
        locked.notes = f"{locked.notes}\nCancelled: {reason}".strip()
        locked.save(update_fields=["status", "notes", "updated_at"])

    return locked


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _check_no_active_rollout(restaurant, menu_item) -> None:
    """Prevent duplicate active rollouts for the same item."""
    active = MenuRollout.objects.filter(
        restaurant=restaurant,
        menu_item=menu_item,
        status__in=ROLLOUT_ACTIVE_STATUSES,
    ).first()
    if active:
        raise ValidationError({
            "code": "ROLLOUT_DUPLICATE_ACTIVE",
            "message": (
                f"An active rollout already exists for '{menu_item.name}' "
                f"(id={active.pk}, status={active.status}). "
                "Cancel or complete it before creating a new one."
            ),
        })


def _resolve_target_branches(restaurant, target_scope, target_branch_ids) -> list:
    """Validate and return the list of target Branch instances."""
    from organizations.models import Branch

    if target_scope == ROLLOUT_SCOPE_ALL_BRANCHES:
        return list(Branch.objects.filter(restaurant=restaurant, is_active=True))

    if not target_branch_ids:
        raise ValidationError({
            "code": "ROLLOUT_NO_TARGET_BRANCHES",
            "message": "target_branch_ids is required when target_scope=SELECTED_BRANCHES.",
        })

    branches = list(
        Branch.objects.filter(pk__in=target_branch_ids, restaurant=restaurant, is_active=True)
    )
    if len(branches) != len(set(target_branch_ids)):
        raise ValidationError({
            "code": "ROLLOUT_INVALID_BRANCHES",
            "message": "Some branch IDs are invalid, inactive, or belong to a different restaurant.",
        })
    return branches


def _get_target_branches_for_rollout(rollout) -> list:
    if rollout.target_scope == ROLLOUT_SCOPE_ALL_BRANCHES:
        from organizations.models import Branch
        return list(
            Branch.objects.filter(restaurant=rollout.restaurant, is_active=True)
        )
    return list(rollout.target_branches.filter(is_active=True))


def _publish_ws_rollout(event_type: str, rollout) -> None:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer
        channel_layer = get_channel_layer()
        if channel_layer is None:
            return
        group = f"enterprise_org_{rollout.restaurant.organization_id}"
        async_to_sync(channel_layer.group_send)(
            group,
            {
                "type": "enterprise_event",
                "event": event_type,
                "payload": {
                    "rollout_id": str(rollout.pk),
                    "menu_item": rollout.menu_item.name,
                    "status": rollout.status,
                },
            },
        )
    except Exception as exc:
        logger.warning("rollout_services: WS publish failed (non-fatal): %s", exc)


def _send_rollout_notification(rollout, result) -> None:
    try:
        from enterprise.constants import NOTIF_ROLLOUT_COMPLETED, NOTIF_ROLLOUT_FAILED, NOTIF_PRICE_ROLLOUT_COMPLETED
        from notifications.services import create_and_dispatch
        company = rollout.restaurant.organization
        n_success = len(result["successful"])
        n_failed  = len(result["failed"])

        if rollout.rollout_type == ROLLOUT_TYPE_PRICE:
            notif_type = NOTIF_PRICE_ROLLOUT_COMPLETED
        elif n_failed > 0:
            notif_type = NOTIF_ROLLOUT_FAILED
        else:
            notif_type = NOTIF_ROLLOUT_COMPLETED

        create_and_dispatch(
            company=company,
            restaurant=rollout.restaurant,
            notification_type=notif_type,
            severity="MEDIUM",
            title=f"Rollout {'completed' if n_failed == 0 else 'partially failed'}: {rollout.menu_item.name}",
            message=f"{n_success} branch(es) updated; {n_failed} failed.",
            source_type="MenuRollout",
            source_id=str(rollout.pk),
            metadata={"successful": n_success, "failed": n_failed},
        )
    except Exception as exc:
        logger.warning("rollout_services: notification failed (non-fatal): %s", exc)
