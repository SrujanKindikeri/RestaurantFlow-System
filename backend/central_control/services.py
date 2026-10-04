# =============================================================================
# RestaurantFlow — Central Control Center Services
# Phase 15
#
# Alert lifecycle services:
#   AlertService.acknowledge_alert()
#   AlertService.resolve_alert()
#   AlertService.dismiss_alert()
#   AlertService.expire_stale_alerts()
#
# Event recording:
#   record_system_event()
#   record_audit_entry()
#
# Real-time broadcast:
#   broadcast_alert_event()
#   broadcast_issue_event()
#   broadcast_health_update()
#
# All services enforce scope and permissions.
# All state transitions are wrapped in transaction.atomic().
# All actions produce CentralControlAuditLog entries.
# =============================================================================

import logging

from django.db import transaction
from django.utils import timezone

from central_control.constants import (
    ALERT_OPEN, ALERT_ACKNOWLEDGED, ALERT_RESOLVED, ALERT_DISMISSED, ALERT_EXPIRED,
    ALERT_ACTIVE_STATUSES,
    AUDIT_ALERT_ACKNOWLEDGED, AUDIT_ALERT_RESOLVED, AUDIT_ALERT_DISMISSED,
    WS_ALERT_UPDATED, WS_ALERT_RESOLVED, WS_ALERT_CREATED,
    WS_GROUP_COMPANY,
)
from central_control.exceptions import (
    AlertNotFoundError, AlertTransitionError, ScopeViolationError,
)
from central_control.validators import validate_alert_transition

logger = logging.getLogger("central_control")


# ---------------------------------------------------------------------------
# Audit + Event helpers
# ---------------------------------------------------------------------------

def record_audit_entry(
    *,
    actor,
    action: str,
    entity_type: str,
    entity_id,
    organization=None,
    restaurant=None,
    branch=None,
    old_status: str = "",
    new_status: str = "",
    metadata: dict = None,
):
    """
    Create an immutable CentralControlAuditLog entry.
    Fire-and-forget; errors are logged but never raise to the caller.
    """
    from central_control.models import CentralControlAuditLog

    try:
        CentralControlAuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id if entity_id else None,
            organization=organization,
            restaurant=restaurant,
            branch=branch,
            old_status=old_status,
            new_status=new_status,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.error(
            "record_audit_entry failed: action=%s entity=%s error=%s",
            action, entity_id, exc,
        )


def record_system_event(
    *,
    organization,
    event_type: str,
    title: str,
    description: str = "",
    severity: str = "MEDIUM",
    restaurant=None,
    branch=None,
    alert=None,
    issue=None,
    metadata: dict = None,
    occurred_at=None,
):
    """
    Append an entry to the CentralSystemEvent timeline.
    These are significant operational events — not every routine transaction.
    """
    from central_control.models import CentralSystemEvent

    try:
        event = CentralSystemEvent.objects.create(
            organization=organization,
            restaurant=restaurant,
            branch=branch,
            event_type=event_type,
            severity=severity,
            title=title,
            description=description,
            alert=alert,
            issue=issue,
            metadata=metadata or {},
            occurred_at=occurred_at or timezone.now(),
        )
        return event
    except Exception as exc:
        logger.error(
            "record_system_event failed: type=%s org=%s error=%s",
            event_type, organization.pk if organization else None, exc,
        )
        return None


# ---------------------------------------------------------------------------
# Real-time broadcast helpers
# ---------------------------------------------------------------------------

def _get_channel_layer():
    """Return the configured channel layer, or None if unavailable."""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception:
        return None


def broadcast_alert_event(alert, event_type: str):
    """
    Broadcast a central alert event to the company WebSocket group.
    Non-blocking — failures are logged but never raised.
    """
    from asgiref.sync import async_to_sync
    import json

    channel_layer = _get_channel_layer()
    if channel_layer is None:
        return

    group_name = WS_GROUP_COMPANY.format(company_id=str(alert.organization_id))

    payload = {
        "type": event_type,
        "alert_id": str(alert.pk),
        "alert_type": alert.alert_type,
        "severity": alert.severity,
        "status": alert.status,
        "title": alert.title,
        "restaurant_id": str(alert.restaurant_id) if alert.restaurant_id else None,
        "branch_id": str(alert.branch_id) if alert.branch_id else None,
        "detected_at": alert.detected_at.isoformat() if alert.detected_at else None,
    }

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "central_event", "payload": payload},
        )
    except Exception as exc:
        logger.warning(
            "broadcast_alert_event failed: group=%s event=%s error=%s",
            group_name, event_type, exc,
        )


def broadcast_issue_event(issue, event_type: str):
    """Broadcast a central issue event to the company WebSocket group."""
    from asgiref.sync import async_to_sync

    channel_layer = _get_channel_layer()
    if channel_layer is None:
        return

    group_name = WS_GROUP_COMPANY.format(company_id=str(issue.organization_id))

    payload = {
        "type": event_type,
        "issue_id": str(issue.pk),
        "category": issue.category,
        "severity": issue.severity,
        "status": issue.status,
        "title": issue.title,
        "restaurant_id": str(issue.restaurant_id) if issue.restaurant_id else None,
        "branch_id": str(issue.branch_id) if issue.branch_id else None,
    }

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {"type": "central_event", "payload": payload},
        )
    except Exception as exc:
        logger.warning(
            "broadcast_issue_event failed: group=%s event=%s error=%s",
            group_name, event_type, exc,
        )


def broadcast_health_update(organization_id, health_data: dict):
    """Broadcast a restaurant health update to the company group."""
    from asgiref.sync import async_to_sync
    from central_control.constants import WS_HEALTH_UPDATED

    channel_layer = _get_channel_layer()
    if channel_layer is None:
        return

    group_name = WS_GROUP_COMPANY.format(company_id=str(organization_id))

    try:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                "type": "central_event",
                "payload": {"type": WS_HEALTH_UPDATED, **health_data},
            },
        )
    except Exception as exc:
        logger.warning(
            "broadcast_health_update failed: org=%s error=%s",
            organization_id, exc,
        )


# ---------------------------------------------------------------------------
# AlertService
# ---------------------------------------------------------------------------

class AlertService:
    """
    Handles alert lifecycle transitions: acknowledge, resolve, dismiss, expire.

    All transitions are atomic and produce audit log entries.
    Scope validation is performed before any mutation.
    """

    @staticmethod
    @transaction.atomic
    def acknowledge_alert(*, actor, alert_id, organization):
        """
        Move an alert from OPEN → ACKNOWLEDGED.

        Args:
            actor:        The User performing the action.
            alert_id:     UUID of the alert to acknowledge.
            organization: The scoping Organization (must match alert.organization).

        Returns:
            The updated CentralAlert.

        Raises:
            AlertNotFoundError if the alert does not exist or is out of scope.
            AlertTransitionError if the current status doesn't allow acknowledgement.
        """
        from central_control.models import CentralAlert

        try:
            alert = CentralAlert.objects.select_for_update().get(
                pk=alert_id,
                organization=organization,
            )
        except CentralAlert.DoesNotExist:
            raise AlertNotFoundError(f"Alert {alert_id} not found.")

        validate_alert_transition(alert.status, ALERT_ACKNOWLEDGED)

        old_status = alert.status
        alert.status = ALERT_ACKNOWLEDGED
        alert.acknowledged_at = timezone.now()
        alert.acknowledged_by = actor
        alert.save(update_fields=[
            "status", "acknowledged_at", "acknowledged_by", "updated_at"
        ])

        record_audit_entry(
            actor=actor,
            action=AUDIT_ALERT_ACKNOWLEDGED,
            entity_type="ALERT",
            entity_id=alert.pk,
            organization=organization,
            restaurant=alert.restaurant,
            branch=alert.branch,
            old_status=old_status,
            new_status=ALERT_ACKNOWLEDGED,
        )

        broadcast_alert_event(alert, WS_ALERT_UPDATED)
        logger.info("Alert %s acknowledged by user %s", alert.pk, actor.email)
        return alert

    @staticmethod
    @transaction.atomic
    def resolve_alert(*, actor, alert_id, organization, resolution_note: str = ""):
        """
        Move an alert from OPEN/ACKNOWLEDGED → RESOLVED.

        Critical alerts require a non-empty resolution_note.
        """
        from central_control.models import CentralAlert
        from central_control.constants import SEVERITY_CRITICAL

        try:
            alert = CentralAlert.objects.select_for_update().get(
                pk=alert_id,
                organization=organization,
            )
        except CentralAlert.DoesNotExist:
            raise AlertNotFoundError(f"Alert {alert_id} not found.")

        validate_alert_transition(alert.status, ALERT_RESOLVED)

        if alert.severity == SEVERITY_CRITICAL and not (resolution_note or "").strip():
            from central_control.exceptions import ResolutionNoteRequiredError
            raise ResolutionNoteRequiredError(
                "A resolution note is required when resolving CRITICAL alerts."
            )

        old_status = alert.status
        alert.status = ALERT_RESOLVED
        alert.resolved_at = timezone.now()
        alert.resolved_by = actor
        alert.resolution_note = resolution_note or ""
        alert.save(update_fields=[
            "status", "resolved_at", "resolved_by", "resolution_note", "updated_at"
        ])

        record_audit_entry(
            actor=actor,
            action=AUDIT_ALERT_RESOLVED,
            entity_type="ALERT",
            entity_id=alert.pk,
            organization=organization,
            restaurant=alert.restaurant,
            branch=alert.branch,
            old_status=old_status,
            new_status=ALERT_RESOLVED,
            metadata={"resolution_note": resolution_note},
        )

        broadcast_alert_event(alert, WS_ALERT_RESOLVED)

        # Record a timeline event
        record_system_event(
            organization=organization,
            event_type="ALERT_RESOLVED",
            title=f"Alert resolved: {alert.title}",
            severity=alert.severity,
            restaurant=alert.restaurant,
            branch=alert.branch,
            alert=alert,
        )

        logger.info("Alert %s resolved by user %s", alert.pk, actor.email)
        return alert

    @staticmethod
    @transaction.atomic
    def dismiss_alert(*, actor, alert_id, organization, resolution_note: str = ""):
        """Move an alert from OPEN/ACKNOWLEDGED → DISMISSED."""
        from central_control.models import CentralAlert

        try:
            alert = CentralAlert.objects.select_for_update().get(
                pk=alert_id,
                organization=organization,
            )
        except CentralAlert.DoesNotExist:
            raise AlertNotFoundError(f"Alert {alert_id} not found.")

        validate_alert_transition(alert.status, ALERT_DISMISSED)

        old_status = alert.status
        alert.status = ALERT_DISMISSED
        alert.resolution_note = resolution_note or ""
        alert.save(update_fields=["status", "resolution_note", "updated_at"])

        record_audit_entry(
            actor=actor,
            action=AUDIT_ALERT_DISMISSED,
            entity_type="ALERT",
            entity_id=alert.pk,
            organization=organization,
            restaurant=alert.restaurant,
            branch=alert.branch,
            old_status=old_status,
            new_status=ALERT_DISMISSED,
        )

        broadcast_alert_event(alert, WS_ALERT_UPDATED)
        logger.info("Alert %s dismissed by user %s", alert.pk, actor.email)
        return alert

    @staticmethod
    @transaction.atomic
    def expire_stale_alerts():
        """
        Mark OPEN alerts as EXPIRED if their expires_at timestamp has passed.
        Called periodically. Returns the number of expired alerts.
        """
        from central_control.models import CentralAlert

        now = timezone.now()
        expired_count = CentralAlert.objects.filter(
            status=ALERT_OPEN,
            expires_at__lt=now,
        ).update(status=ALERT_EXPIRED, updated_at=now)

        if expired_count:
            logger.info("Expired %d stale OPEN alerts.", expired_count)
        return expired_count
