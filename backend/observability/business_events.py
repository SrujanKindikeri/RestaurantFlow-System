# =============================================================================
# RestaurantFlow — Business Event Emission
# Phase 24
#
# A single, safe helper for recording business-critical operational events as
# both a structured log line AND a Prometheus counter increment. Business
# modules call this from failure paths; it never raises into the caller and
# never records sensitive payloads.
#
# This is intentionally a thin instrumentation surface. The authoritative
# business audit trail remains the existing audit system (Phase 1-23).
# =============================================================================

import logging

from observability.metrics import business_events_total

logger = logging.getLogger("observability.business")


def record_business_event(
    event: str,
    *,
    severity: str = "MEDIUM",
    company_id=None,
    restaurant_id=None,
    branch_id=None,
    user_id=None,
    error_code: str = "",
    duration_ms=None,
    extra: dict = None,
):
    """
    Record a business-critical event.

    Args:
        event:       An EVENT_* constant from observability.constants.
        severity:    INFO / LOW / MEDIUM / HIGH / CRITICAL.
        company_id/restaurant_id/branch_id/user_id: safe tenant context.
        error_code:  A stable machine code (never a raw exception message).
        duration_ms: Optional measured duration.
        extra:       Additional SAFE metadata only — never secrets or payloads.

    This function never raises. Metric/cardinality safety is enforced by the
    registry; the `event` and `severity` labels are low-cardinality by design.
    """
    try:
        business_events_total.inc(event=event, severity=severity)

        log_extra = dict(extra or {})
        log_extra.update({
            "event": event,
            "severity": severity,
            "error_code": error_code,
        })
        if company_id:
            log_extra["company_id"] = str(company_id)
        if restaurant_id:
            log_extra["restaurant_id"] = str(restaurant_id)
        if branch_id:
            log_extra["branch_id"] = str(branch_id)
        if user_id:
            log_extra["user_id"] = str(user_id)
        if duration_ms is not None:
            log_extra["duration_ms"] = duration_ms

        level = logging.WARNING if severity in ("HIGH", "CRITICAL") else logging.INFO
        logger.log(
            level,
            "Business event: %s [%s]%s",
            event,
            severity,
            f" error_code={error_code}" if error_code else "",
            extra=log_extra,
        )
    except Exception as exc:  # never break the caller's business transaction
        logger.error("record_business_event failed for %s: %s", event, exc)
