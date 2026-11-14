# =============================================================================
# RestaurantFlow — Alertmanager → Central Control Forwarder
# Phase 24
#
# Receives Alertmanager webhook payloads and forwards them into the EXISTING
# CentralAlert model (Phase 15), reusing its fingerprint-based deduplication
# and lifecycle. Metric-based alerts therefore appear in the same Central
# Control surface as business-detected alerts — no duplicate alert engine.
#
# Recovery: when Alertmanager reports `status=resolved`, the matching active
# CentralAlert is resolved via the existing AlertService path.
#
# This module creates CentralAlert rows scoped to a system/monitoring
# organization. It never logs or stores raw alert payloads containing
# secrets. Sensitive labels are stripped before persistence.
# =============================================================================

import logging
import re

from django.utils import timezone

logger = logging.getLogger("observability.alert_forwarder")

from observability.constants import ALERTMANAGER_SEVERITY_MAP, ALERT_SOURCE_MONITORING

# Strip values that look like secrets/tokens before persistence.
_SECRET_HINT_RE = re.compile(r"(?i)(password|token|secret|key|auth|cvv|pan)")


def _normalise_severity(raw) -> str:
    raw = (raw or "").lower()
    return ALERTMANAGER_SEVERITY_MAP.get(raw, "MEDIUM")


def _safe_label_value(value: str) -> str:
    """Truncate and strip secret-ish label values."""
    if value is None:
        return ""
    s = str(value)
    if len(s) > 200:
        s = s[:200]
    if _SECRET_HINT_RE.search(s):
        return "[redacted]"
    return s


def _fingerprint_for(alert_label: dict, alert_type: str, org_pk) -> str:
    """Build a deterministic fingerprint consistent with CentralAlert's scheme."""
    import hashlib
    parts = [
        alert_type,
        ALERT_SOURCE_MONITORING,
        alert_label.get("alertname", ""),
        alert_label.get("instance", ""),
        str(org_pk),
    ]
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:64]


def handle_alertmanager_webhook(payload: dict, organization=None) -> dict:
    """
    Process an Alertmanager webhook payload.

    Args:
        payload:     Parsed Alertmanager webhook body ({"alerts": [...]}).
        organization: Optional Organization to scope alerts to. If None, the
                      call is a no-op (alerts require an owning org).

    Returns:
        {"processed": int, "created": int, "updated": int, "resolved": int, "errors": int}
    """
    from central_control.models import CentralAlert
    from central_control.constants import (
        ALERT_OPEN, ALERT_RESOLVED, SEVERITY_INFO,
    )

    result = {"processed": 0, "created": 0, "updated": 0, "resolved": 0, "errors": 0}
    if organization is None:
        # Alerts require an owning organization; skip silently otherwise.
        return result

    alerts = payload.get("alerts") or []
    now = timezone.now()

    for alert in alerts:
        try:
            status = (alert.get("status") or "firing").lower()
            labels = alert.get("labels") or {}
            annotations = alert.get("annotations") or {}
            alertname = _safe_label_value(labels.get("alertname", "monitoring_alert"))
            severity = _normalise_severity(labels.get("severity"))
            instance = _safe_label_value(labels.get("instance", ""))
            summary = _safe_label_value(annotations.get("summary") or alertname)
            description = _safe_label_value(annotations.get("description", ""))

            alert_type = "SYSTEM_HEALTH"
            source_id = _safe_label_value(f"{alertname}:{instance}")
            fingerprint = _fingerprint_for(
                {"alertname": alertname, "instance": instance}, alert_type, organization.pk
            )

            if status == "resolved":
                resolved = CentralAlert.objects.filter(
                    organization=organization,
                    fingerprint=fingerprint,
                    status__in=[ALERT_OPEN, "ACKNOWLEDGED"],
                ).update(
                    status=ALERT_RESOLVED,
                    resolved_at=now,
                    resolution_note="Automatically resolved by Alertmanager.",
                    updated_at=now,
                )
                result["resolved"] += int(resolved)
                result["processed"] += 1
                continue

            existing = (
                CentralAlert.objects
                .filter(organization=organization, fingerprint=fingerprint,
                        status__in=[ALERT_OPEN, "ACKNOWLEDGED"])
                .first()
            )
            if existing:
                existing.detection_count += 1
                existing.last_detected_at = now
                from central_control.constants import SEVERITY_ORDER
                if SEVERITY_ORDER.get(severity, 0) > SEVERITY_ORDER.get(existing.severity, 0):
                    existing.severity = severity
                existing.save(update_fields=[
                    "detection_count", "last_detected_at", "severity", "updated_at",
                ])
                result["updated"] += 1
            else:
                CentralAlert.objects.create(
                    organization=organization,
                    alert_type=alert_type,
                    severity=severity,
                    title=summary[:300],
                    message=description or summary,
                    source_type=ALERT_SOURCE_MONITORING,
                    source_id=source_id,
                    fingerprint=fingerprint,
                    status=ALERT_OPEN,
                    detected_at=now,
                    last_detected_at=now,
                    detection_count=1,
                )
                _notify_monitoring_alert(organization, summary, severity, source_id)
                result["created"] += 1
            result["processed"] += 1
        except Exception as exc:
            result["errors"] += 1
            logger.error("Alertmanager webhook: failed to process alert: %s", exc)

    logger.info(
        "Alertmanager webhook processed: %s", {k: v for k, v in result.items()}
    )
    return result


def _notify_monitoring_alert(organization, title: str, severity: str, source_id: str):
    """
    Deliver a Central Control notification for a new monitoring alert,
    reusing the Phase 16 Notification center. Failures are non-fatal.
    """
    try:
        from notifications.services import create_and_dispatch
        from notifications.constants import (
            SOURCE_SYSTEM,
            SEVERITY_HIGH, SEVERITY_CRITICAL, SEVERITY_MEDIUM,
        )
        # Only escalate HIGH/CRITICAL monitoring alerts to push notifications;
        # lower severities remain visible in Central Control dashboards.
        if severity not in (SEVERITY_HIGH, SEVERITY_CRITICAL):
            return
        create_and_dispatch(
            company=organization,
            notification_type="monitoring_alert",
            severity=SEVERITY_HIGH if severity == SEVERITY_HIGH else SEVERITY_CRITICAL,
            title=f"Monitoring alert: {title}",
            message=(
                "A metric-based alert was raised by Alertmanager and forwarded "
                "into Central Control. Open the Central Control dashboard to "
                "investigate."
            ),
            source_type=SOURCE_SYSTEM,
            source_id=source_id,
            bypass_cooldown=True,
        )
    except Exception as exc:
        logger.debug("monitoring alert notification failed: %s", exc)
