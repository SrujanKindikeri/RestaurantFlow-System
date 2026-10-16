# =============================================================================
# RestaurantFlow — Enterprise Audit Service
# Phase 20
#
# Centralized audit log creation for all significant enterprise actions.
# Always call these functions AFTER a successful DB commit so that the
# audit record is never rolled back if the parent transaction fails.
#
# EnterpriseAuditLog rows are immutable — never update them.
# Never store secrets, passwords, or PII in audit metadata.
# =============================================================================

import logging
from typing import Optional

from enterprise.constants import AUDIT_ACTION_CHOICES
from enterprise.models import EnterpriseAuditLog

logger = logging.getLogger("enterprise")

# Build a set of valid action codes for fast validation
_VALID_ACTIONS = {code for code, _ in AUDIT_ACTION_CHOICES}


def record_audit(
    action: str,
    company,
    description: str,
    performed_by=None,
    restaurant=None,
    branch=None,
    source_type: str = "",
    source_id: str = "",
    metadata: Optional[dict] = None,
) -> EnterpriseAuditLog:
    """
    Create and persist an immutable EnterpriseAuditLog entry.

    Args:
        action:       One of the AUDIT_* constants from enterprise.constants.
        company:      Organization instance (required).
        description:  Human-readable summary of the action.
        performed_by: User who performed the action (nullable for system actions).
        restaurant:   Restaurant context (nullable).
        branch:       Branch context (nullable).
        source_type:  Model name of the primary object (e.g. "StaffTransfer").
        source_id:    String ID/UUID of the primary object.
        metadata:     Arbitrary non-secret context dict (do NOT include raw values
                      that could be secrets — use keys/descriptions only).

    Returns:
        The created EnterpriseAuditLog instance.
    """
    if action not in _VALID_ACTIONS:
        logger.error("audit_services: unknown action code '%s' — still recording", action)

    try:
        entry = EnterpriseAuditLog.objects.create(
            action=action,
            company=company,
            restaurant=restaurant,
            branch=branch,
            performed_by=performed_by,
            description=description,
            source_type=source_type or "",
            source_id=str(source_id) if source_id else "",
            metadata=metadata or {},
        )
        logger.info(
            "audit: action=%s company=%s rest=%s branch=%s by=%s source=%s/%s",
            action,
            company.pk,
            restaurant.pk if restaurant else None,
            branch.pk if branch else None,
            performed_by.email if performed_by else "system",
            source_type,
            source_id,
        )
        return entry
    except Exception as exc:
        # Audit failures must never block business operations
        logger.exception(
            "audit_services: FAILED to record audit action=%s — %s", action, exc
        )
        return None
