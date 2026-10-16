# =============================================================================
# RestaurantFlow — Branch Services
# Phase 20
#
# Business logic for branch lifecycle management:
#   - Open / close / reopen / temporarily-close a branch
#   - Branch operational status management
#   - Opening checklist generation
#
# Design:
#   - Auth + permission + scope check first (every public function).
#   - select_for_update() inside transaction.atomic() for status mutations.
#   - Pre-close operational checks warn / block depending on configuration.
#   - Historical transactions are NEVER modified by status changes.
#   - Audit and notifications happen OUTSIDE the transaction (after commit).
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from enterprise.constants import (
    BRANCH_STATUS_ACTIVE,
    BRANCH_STATUS_TEMPORARILY_CLOSED,
    BRANCH_STATUS_MAINTENANCE,
    BRANCH_STATUS_INACTIVE,
    BRANCH_STATUS_TRANSITIONS,
    CHECKLIST_COUNTER_READY,
    CHECKLIST_KITCHEN_READY,
    CHECKLIST_INVENTORY_READY,
    CHECKLIST_STAFF_READY,
    CHECKLIST_PAYMENT_METHODS_READY,
    CHECKLIST_POS_READY,
    CHECKLIST_STATUS_READY,
    CHECKLIST_STATUS_WARNING,
    CHECKLIST_STATUS_BLOCKED,
    AUDIT_BRANCH_OPENED,
    AUDIT_BRANCH_CLOSED,
    AUDIT_BRANCH_REOPENED,
    AUDIT_BRANCH_STATUS_CHANGED,
    PERM_BRANCH_OPEN,
    PERM_BRANCH_CLOSE,
    PERM_BRANCH_REOPEN,
    PERM_BRANCH_UPDATE,
    WS_BRANCH_STATUS_CHANGED,
)
from enterprise.exceptions import BranchStatusTransitionError, BranchOperationalBlockError
from enterprise.models import BranchOperationalStatus
from enterprise.audit_services import record_audit

logger = logging.getLogger("enterprise")


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _require_auth(user):
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Authentication required.")


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def get_or_create_operational_status(branch) -> BranchOperationalStatus:
    """
    Fetch (or lazily create) the BranchOperationalStatus record for a branch.
    """
    status_obj, _ = BranchOperationalStatus.objects.get_or_create(
        branch=branch,
        defaults={"status": BRANCH_STATUS_ACTIVE},
    )
    return status_obj


def _apply_status_transition(branch, new_status: str, user, reason: str = "") -> BranchOperationalStatus:
    """
    Internal: apply a validated status transition inside an atomic block.

    Caller must ensure transaction.atomic() is active.
    Uses select_for_update() on the status row.
    """
    status_obj = (
        BranchOperationalStatus.objects.select_for_update()
        .select_related("branch", "branch__restaurant", "branch__restaurant__organization")
        .get_or_create(branch=branch)[0]
    )
    current = status_obj.status

    allowed = BRANCH_STATUS_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        raise BranchStatusTransitionError(
            f"Cannot transition branch from {current} to {new_status}. "
            f"Allowed transitions: {allowed}",
        )

    status_obj.status = new_status
    status_obj.status_changed_at = timezone.now()
    status_obj.status_changed_by = user
    status_obj.status_reason = reason
    status_obj.save(update_fields=[
        "status", "status_changed_at", "status_changed_by", "status_reason", "updated_at"
    ])
    return status_obj


# ---------------------------------------------------------------------------
# Pre-close checks
# ---------------------------------------------------------------------------

def check_branch_operational_blockers(branch) -> list:
    """
    Return a list of dicts describing open operational items.

    Each item has:
        {type, severity, description, count}

    severity:
        "BLOCKED"  — must be resolved before closing
        "WARNING"  — can proceed with warning
    """
    blockers = []

    # 1. Open counter sessions
    try:
        from counters.models import CounterSession, SessionStatus
        open_sessions = CounterSession.objects.filter(
            counter__branch=branch,
            status=SessionStatus.OPEN,
        ).count()
        if open_sessions:
            blockers.append({
                "type": "OPEN_COUNTER_SESSIONS",
                "severity": "BLOCKED",
                "description": f"{open_sessions} open counter session(s) must be closed before branch closure.",
                "count": open_sessions,
            })
    except Exception as e:
        logger.warning("branch_services: counter session check failed: %s", e)

    # 2. Unpaid finalized bills
    try:
        from billing.models import Bill, BillStatus
        unpaid = Bill.objects.filter(
            branch=branch,
            status=BillStatus.FINALIZED,
        ).count()
        if unpaid:
            blockers.append({
                "type": "UNPAID_FINALIZED_BILLS",
                "severity": "WARNING",
                "description": f"{unpaid} finalized bill(s) without payment.",
                "count": unpaid,
            })
    except Exception as e:
        logger.warning("branch_services: unpaid bill check failed: %s", e)

    # 3. Pending kitchen orders
    try:
        from kitchen.models import KitchenOrder, KitchenOrderStatus
        pending_kitchen = KitchenOrder.objects.filter(
            branch=branch,
            status__in=[KitchenOrderStatus.PENDING, KitchenOrderStatus.PREPARING],
        ).count()
        if pending_kitchen:
            blockers.append({
                "type": "PENDING_KITCHEN_ORDERS",
                "severity": "WARNING",
                "description": f"{pending_kitchen} kitchen order(s) still in progress.",
                "count": pending_kitchen,
            })
    except Exception as e:
        logger.warning("branch_services: kitchen order check failed: %s", e)

    return blockers


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def open_branch(branch, user, reason: str = "") -> BranchOperationalStatus:
    """
    Open a branch (transition to ACTIVE).

    Permissions: enterprise.branch.open
    Scope:       User must have access to the branch.
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_BRANCH_OPEN):
        raise PermissionDenied("You do not have permission to open branches.")
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    try:
        with transaction.atomic():
            status_obj = _apply_status_transition(
                branch=branch,
                new_status=BRANCH_STATUS_ACTIVE,
                user=user,
                reason=reason,
            )
    except BranchStatusTransitionError as exc:
        raise ValidationError({"code": exc.code, "message": exc.message})

    restaurant = branch.restaurant
    company = restaurant.organization

    record_audit(
        action=AUDIT_BRANCH_OPENED,
        company=company,
        restaurant=restaurant,
        branch=branch,
        performed_by=user,
        description=f"Branch '{branch.name}' opened.",
        source_type="Branch",
        source_id=str(branch.pk),
        metadata={"reason": reason},
    )

    _publish_ws_event(WS_BRANCH_STATUS_CHANGED, branch, BRANCH_STATUS_ACTIVE)
    logger.info("branch_services: branch=%s opened by user=%s", branch.name, user.email)
    return status_obj


def close_branch(
    branch,
    user,
    reason: str,
    force: bool = False,
) -> BranchOperationalStatus:
    """
    Close a branch (transition to TEMPORARILY_CLOSED or INACTIVE).

    Checks for open operational items (counter sessions, kitchen orders, etc.).
    If force=True, warnings are bypassed; BLOCKED items still prevent closure.

    Permissions: enterprise.branch.close
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_BRANCH_CLOSE):
        raise PermissionDenied("You do not have permission to close branches.")
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    # Pre-close checks
    blockers = check_branch_operational_blockers(branch)
    hard_blockers = [b for b in blockers if b["severity"] == "BLOCKED"]
    if hard_blockers:
        messages = "; ".join(b["description"] for b in hard_blockers)
        raise BranchOperationalBlockError(
            f"Branch cannot be closed: {messages}",
            code="BRANCH_HAS_OPEN_OPERATIONS",
        )

    if not force and any(b["severity"] == "WARNING" for b in blockers):
        # Return warnings without closing — caller should prompt for confirmation
        raise ValidationError({
            "code": "BRANCH_CLOSE_WARNINGS",
            "message": "Branch has open items. Pass force=True to proceed.",
            "warnings": [b for b in blockers if b["severity"] == "WARNING"],
        })

    try:
        with transaction.atomic():
            status_obj = _apply_status_transition(
                branch=branch,
                new_status=BRANCH_STATUS_TEMPORARILY_CLOSED,
                user=user,
                reason=reason,
            )
    except BranchStatusTransitionError as exc:
        raise ValidationError({"code": exc.code, "message": exc.message})

    restaurant = branch.restaurant
    company = restaurant.organization

    record_audit(
        action=AUDIT_BRANCH_CLOSED,
        company=company,
        restaurant=restaurant,
        branch=branch,
        performed_by=user,
        description=f"Branch '{branch.name}' closed. Reason: {reason}",
        source_type="Branch",
        source_id=str(branch.pk),
        metadata={"reason": reason, "force": force},
    )

    _publish_ws_event(WS_BRANCH_STATUS_CHANGED, branch, BRANCH_STATUS_TEMPORARILY_CLOSED)
    _send_branch_status_notification(branch, BRANCH_STATUS_TEMPORARILY_CLOSED, user)
    logger.info("branch_services: branch=%s closed by user=%s", branch.name, user.email)
    return status_obj


def reopen_branch(branch, user, reason: str = "") -> BranchOperationalStatus:
    """
    Reopen a closed/maintenance branch (transition to ACTIVE).

    Permissions: enterprise.branch.reopen
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_BRANCH_REOPEN):
        raise PermissionDenied("You do not have permission to reopen branches.")
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    try:
        with transaction.atomic():
            status_obj = _apply_status_transition(
                branch=branch,
                new_status=BRANCH_STATUS_ACTIVE,
                user=user,
                reason=reason,
            )
    except BranchStatusTransitionError as exc:
        raise ValidationError({"code": exc.code, "message": exc.message})

    restaurant = branch.restaurant
    company = restaurant.organization

    record_audit(
        action=AUDIT_BRANCH_REOPENED,
        company=company,
        restaurant=restaurant,
        branch=branch,
        performed_by=user,
        description=f"Branch '{branch.name}' reopened.",
        source_type="Branch",
        source_id=str(branch.pk),
        metadata={"reason": reason},
    )

    _publish_ws_event(WS_BRANCH_STATUS_CHANGED, branch, BRANCH_STATUS_ACTIVE)
    _send_branch_status_notification(branch, BRANCH_STATUS_ACTIVE, user)
    logger.info("branch_services: branch=%s reopened by user=%s", branch.name, user.email)
    return status_obj


def set_branch_status(
    branch,
    new_status: str,
    user,
    reason: str = "",
) -> BranchOperationalStatus:
    """
    Generic status setter — for MAINTENANCE, INACTIVE, and SCHEDULED_CLOSURE transitions.

    Permissions: enterprise.branch.update
    """
    _require_auth(user)
    if not acl.has_permission(user, PERM_BRANCH_UPDATE):
        raise PermissionDenied("You do not have permission to update branch status.")
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    try:
        with transaction.atomic():
            status_obj = _apply_status_transition(
                branch=branch,
                new_status=new_status,
                user=user,
                reason=reason,
            )
    except BranchStatusTransitionError as exc:
        raise ValidationError({"code": exc.code, "message": exc.message})

    restaurant = branch.restaurant
    company = restaurant.organization

    record_audit(
        action=AUDIT_BRANCH_STATUS_CHANGED,
        company=company,
        restaurant=restaurant,
        branch=branch,
        performed_by=user,
        description=f"Branch '{branch.name}' status changed to {new_status}.",
        source_type="Branch",
        source_id=str(branch.pk),
        metadata={"new_status": new_status, "reason": reason},
    )

    _publish_ws_event(WS_BRANCH_STATUS_CHANGED, branch, new_status)
    logger.info(
        "branch_services: branch=%s status→%s by user=%s", branch.name, new_status, user.email
    )
    return status_obj


# ---------------------------------------------------------------------------
# Opening Checklist
# ---------------------------------------------------------------------------

def get_opening_checklist(branch, user) -> list:
    """
    Return the branch opening checklist.

    Each item: {type, label, status, detail}
    status: READY | WARNING | BLOCKED
    """
    _require_auth(user)
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")

    checklist = []

    # 1. Counter ready (at least one active counter)
    try:
        from counters.models import Counter, CounterStatus
        active_counters = Counter.objects.filter(
            branch=branch, status=CounterStatus.ACTIVE
        ).count()
        checklist.append({
            "type": CHECKLIST_COUNTER_READY,
            "label": "Counter Ready",
            "status": CHECKLIST_STATUS_READY if active_counters > 0 else CHECKLIST_STATUS_BLOCKED,
            "detail": (
                f"{active_counters} active counter(s)."
                if active_counters > 0
                else "No active counters configured for this branch."
            ),
        })
    except Exception as e:
        logger.warning("checklist: counter check failed: %s", e)
        checklist.append(_checklist_error(CHECKLIST_COUNTER_READY, "Counter Ready"))

    # 2. Kitchen ready (at least one kitchen exists)
    try:
        from kitchen.models import KitchenStation
        kitchen_count = KitchenStation.objects.filter(branch=branch, is_active=True).count()
        checklist.append({
            "type": CHECKLIST_KITCHEN_READY,
            "label": "Kitchen Ready",
            "status": CHECKLIST_STATUS_READY if kitchen_count > 0 else CHECKLIST_STATUS_WARNING,
            "detail": (
                f"{kitchen_count} active kitchen station(s)."
                if kitchen_count > 0
                else "No active kitchen stations — kitchen display may not function."
            ),
        })
    except Exception as e:
        logger.warning("checklist: kitchen check failed: %s", e)
        checklist.append(_checklist_error(CHECKLIST_KITCHEN_READY, "Kitchen Ready"))

    # 3. Inventory ready (no critical out-of-stock items)
    try:
        from inventory.models import StockLevel
        critical_oos = StockLevel.objects.filter(
            branch=branch,
            quantity__lte=0,
            inventory_item__is_active=True,
        ).count()
        checklist.append({
            "type": CHECKLIST_INVENTORY_READY,
            "label": "Inventory Ready",
            "status": CHECKLIST_STATUS_WARNING if critical_oos > 0 else CHECKLIST_STATUS_READY,
            "detail": (
                f"{critical_oos} item(s) at or below zero stock."
                if critical_oos > 0
                else "All tracked inventory items are in stock."
            ),
        })
    except Exception as e:
        logger.warning("checklist: inventory check failed: %s", e)
        checklist.append(_checklist_error(CHECKLIST_INVENTORY_READY, "Inventory Ready"))

    # 4. Staff ready (at least one active staff assignment)
    try:
        from enterprise.models import StaffBranchAssignment
        active_staff = StaffBranchAssignment.objects.filter(
            branch=branch, is_active=True
        ).count()
        checklist.append({
            "type": CHECKLIST_STAFF_READY,
            "label": "Staff Ready",
            "status": CHECKLIST_STATUS_READY if active_staff > 0 else CHECKLIST_STATUS_WARNING,
            "detail": (
                f"{active_staff} staff member(s) assigned to this branch."
                if active_staff > 0
                else "No staff currently assigned to this branch."
            ),
        })
    except Exception as e:
        logger.warning("checklist: staff check failed: %s", e)
        checklist.append(_checklist_error(CHECKLIST_STAFF_READY, "Staff Ready"))

    # 5. Payment methods ready (at least one enabled via configuration)
    try:
        from enterprise.configuration_resolver import ConfigurationResolver
        cash_on = ConfigurationResolver.get_effective_value("payment.cash_enabled", branch=branch)
        upi_on  = ConfigurationResolver.get_effective_value("payment.upi_enabled",  branch=branch)
        card_on = ConfigurationResolver.get_effective_value("payment.card_enabled", branch=branch)
        any_payment = any([cash_on, upi_on, card_on])
        checklist.append({
            "type": CHECKLIST_PAYMENT_METHODS_READY,
            "label": "Payment Methods Ready",
            "status": CHECKLIST_STATUS_READY if any_payment else CHECKLIST_STATUS_BLOCKED,
            "detail": (
                "At least one payment method is enabled."
                if any_payment
                else "No payment methods are enabled — review enterprise configuration."
            ),
        })
    except Exception as e:
        logger.warning("checklist: payment methods check failed: %s", e)
        checklist.append(_checklist_error(CHECKLIST_PAYMENT_METHODS_READY, "Payment Methods Ready"))

    # 6. POS ready (counter session requirement check)
    try:
        from enterprise.configuration_resolver import ConfigurationResolver
        require_session = ConfigurationResolver.get_effective_value(
            "pos.require_counter_session", branch=branch
        )
        checklist.append({
            "type": CHECKLIST_POS_READY,
            "label": "POS Ready",
            "status": CHECKLIST_STATUS_READY,
            "detail": (
                "POS requires an open counter session before processing orders."
                if require_session
                else "POS can operate without a counter session (check configuration)."
            ),
        })
    except Exception as e:
        logger.warning("checklist: POS check failed: %s", e)
        checklist.append(_checklist_error(CHECKLIST_POS_READY, "POS Ready"))

    return checklist


def _checklist_error(item_type: str, label: str) -> dict:
    return {
        "type": item_type,
        "label": label,
        "status": CHECKLIST_STATUS_WARNING,
        "detail": "Could not verify this item — check manually before opening.",
    }


# ---------------------------------------------------------------------------
# Private notification/WS helpers
# ---------------------------------------------------------------------------

def _publish_ws_event(event_type: str, branch, new_status: str) -> None:
    """Publish a WebSocket event via Django Channels."""
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
                "event": event_type,
                "payload": {
                    "branch_id": str(branch.pk),
                    "branch_name": branch.name,
                    "new_status": new_status,
                },
            },
        )
    except Exception as exc:
        logger.warning("branch_services: WS publish failed (non-fatal): %s", exc)


def _send_branch_status_notification(branch, new_status: str, actor) -> None:
    """Fire a notification for branch status changes. Non-fatal on failure."""
    try:
        from enterprise.constants import NOTIF_BRANCH_REOPENED, NOTIF_BRANCH_CLOSURE_APPROVED
        from notifications.services import create_and_dispatch

        notif_type = (
            NOTIF_BRANCH_REOPENED
            if new_status == BRANCH_STATUS_ACTIVE
            else NOTIF_BRANCH_CLOSURE_APPROVED
        )
        company = branch.restaurant.organization
        create_and_dispatch(
            company=company,
            restaurant=branch.restaurant,
            branch=branch,
            notification_type=notif_type,
            severity="MEDIUM",
            title=f"Branch status changed: {branch.name}",
            message=f"Branch '{branch.name}' is now {new_status}.",
            source_type="Branch",
            source_id=str(branch.pk),
            metadata={"new_status": new_status},
        )
    except Exception as exc:
        logger.warning(
            "branch_services: notification dispatch failed (non-fatal): %s", exc
        )
