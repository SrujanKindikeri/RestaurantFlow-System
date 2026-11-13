# =============================================================================
# RestaurantFlow — Security Event Service
# Phase 21 — Security, Audit & Compliance Hardening
#
# Centralized service for recording security events to the SecurityAuditLog,
# detecting anomalies (repeated failures, suspicious patterns), and routing
# high-severity events to administrators via the existing notification system.
#
# Design principles:
#   - Never store passwords, tokens, session IDs, or secret keys in metadata.
#   - Use deduplication and cooldowns to prevent alert storms.
#   - Do not automatically suspend accounts based on weak signals.
#   - Business transactions are not rolled back if a notification fails.
#   - Audit writes use a separate savepoint so a failed audit write does not
#     silently erase evidence of a successful sensitive operation.
# =============================================================================

import logging
import hashlib
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger("core")

# Failure tracking constants — read from settings with safe defaults
MAX_LOGIN_FAILURES = getattr(settings, "SECURITY_MAX_LOGIN_FAILURES", 5)
LOGIN_LOCKOUT_MINUTES = getattr(settings, "SECURITY_LOGIN_LOCKOUT_MINUTES", 15)


# =============================================================================
# Audit writing
# =============================================================================

def record_security_event(
    *,
    event,
    actor=None,
    target_user=None,
    outcome="success",
    ip_address=None,
    user_agent="",
    request_id="",
    metadata=None,
    organization=None,
):
    """
    Write a SecurityAuditLog record.

    This uses a separate database savepoint so that a failure in audit
    writing does NOT silently erase the evidence of a completed operation.
    If the audit write fails, the error is logged at ERROR level but the
    caller's transaction is not rolled back.

    Returns the created SecurityAuditLog instance, or None on failure.
    """
    from accounts.models import SecurityAuditLog

    safe_meta = _sanitize_metadata(metadata or {})

    try:
        with transaction.atomic(using="default"):
            log = SecurityAuditLog.objects.create(
                actor=actor,
                target_user=target_user,
                event=event,
                outcome=outcome,
                ip_address=ip_address,
                user_agent=(user_agent or "")[:500],
                request_id=(request_id or "")[:100],
                metadata=safe_meta,
                organization=organization,
            )
        return log
    except Exception:
        logger.error(
            "Failed to write SecurityAuditLog: event=%s actor=%s outcome=%s",
            event,
            getattr(actor, "email", None),
            outcome,
            exc_info=True,
        )
        return None


def _sanitize_metadata(metadata):
    """
    Remove any sensitive keys from metadata before storing.

    This is a defense-in-depth measure — callers should never pass secrets,
    but this ensures they never end up in the audit log.
    """
    if not isinstance(metadata, dict):
        return {}

    SENSITIVE_KEYS = frozenset({
        "password", "password_confirm", "old_password",
        "token", "refresh", "access", "refresh_token", "access_token",
        "secret", "secret_key", "api_key", "authorization",
        "session_id", "session_key", "csrf_token",
        "card_number", "cvv", "pin",
    })

    return {
        k: "[REDACTED]" if k.lower() in SENSITIVE_KEYS else v
        for k, v in metadata.items()
    }


# =============================================================================
# Login failure tracking & temporary lockout
# =============================================================================

def _lockout_cache_key(ip_address, email):
    """Build a cache key for tracking login failures."""
    from django.core.cache import caches
    # Use a hash to avoid storing raw email/IP in cache keys
    raw = f"{ip_address}:{email or ''}"
    hashed = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"login_fail:{hashed}"


def record_login_failure(ip_address, email=""):
    """
    Record a failed login attempt and return (should_lockout, failure_count).

    Uses Django's cache backend (Redis in production) for fast, ephemeral
    failure tracking.  Does NOT permanently lock accounts — uses a temporary
    cooldown window to prevent denial-of-service via permanent lockout.
    """
    from django.core.cache import caches
    cache = caches["default"]
    key = _lockout_cache_key(ip_address, email)
    fail_count = cache.get(key, 0) + 1
    cache.set(key, fail_count, timeout=LOGIN_LOCKOUT_MINUTES * 120)  # 2x lockout window
    should_lockout = fail_count >= MAX_LOGIN_FAILURES
    return should_lockout, fail_count


def get_login_failure_count(ip_address, email=""):
    """Return the current failure count for this IP/email combo."""
    from django.core.cache import caches
    cache = caches["default"]
    key = _lockout_cache_key(ip_address, email)
    return cache.get(key, 0)


def is_login_locked_out(ip_address, email=""):
    """Check if this IP/email combo is temporarily locked out."""
    from django.core.cache import caches
    cache = caches["default"]
    key = _lockout_cache_key(ip_address, email)
    fail_count = cache.get(key, 0)
    return fail_count >= MAX_LOGIN_FAILURES


def clear_login_failures(ip_address, email=""):
    """Clear failure tracking after a successful login."""
    from django.core.cache import caches
    cache = caches["default"]
    key = _lockout_cache_key(ip_address, email)
    cache.delete(key)


# =============================================================================
# Security event detection — deduplication & routing
# =============================================================================

# Cooldown window for security alerts (seconds)
ALERT_COOLDOWN_SECONDS = 300  # 5 minutes


def _alert_dedupe_key(event, ip_address=None, target_user=None, organization=None):
    """Build a cache key for alert deduplication."""
    parts = [event]
    if ip_address:
        parts.append(str(ip_address))
    if target_user:
        parts.append(f"user:{target_user.pk}")
    if organization:
        parts.append(f"org:{organization.pk}")
    raw = ":".join(parts)
    return f"sec_alert_dedupe:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"


def should_emit_security_alert(event, ip_address=None, target_user=None, organization=None):
    """
    Check if a security alert should be emitted, using a cooldown to
    prevent alert storms.  Returns True if the alert should fire.
    """
    from django.core.cache import caches
    cache = caches["default"]
    key = _alert_dedupe_key(event, ip_address, target_user, organization)
    if cache.get(key):
        return False  # Already alerted within the cooldown window
    cache.set(key, True, timeout=ALERT_COOLDOWN_SECONDS)
    return True


def route_security_alert(event, metadata, organization=None):
    """
    Route a high-severity security event to authorized administrators.

    Uses the existing notification service — does not create a parallel
    notification system.  Notifications are sent after the main transaction
    commits (transaction.on_commit) so business logic is never rolled back
    due to notification failure.
    """
    try:
        alert_title_map = {
            "repeated_auth_failures": "Repeated authentication failures detected",
            "suspicious_permission_change": "Suspicious permission change detected",
            "repeated_unauthorized_requests": "Repeated unauthorized access attempts",
            "cross_scope_access_attempt": "Cross-scope access attempt detected",
            "repeated_password_reset_requests": "Abnormal password-reset activity",
            "suspicious_bulk_export": "Suspicious bulk data export detected",
            "audit_subsystem_failure": "Audit subsystem failure detected",
            "unexpected_configuration_change": "Unexpected configuration change detected",
        }

        title = alert_title_map.get(event, f"Security alert: {event}")

        # Defer notification delivery until after the current transaction commits.
        transaction.on_commit(lambda: _deliver_security_notification(
            title=title,
            event=event,
            metadata=metadata,
            organization=organization,
        ))
    except Exception:
        logger.error("Failed to route security alert: event=%s", event, exc_info=True)


def _deliver_security_notification(*, title, event, metadata, organization=None):
    """Actually deliver the security notification (called post-commit)."""
    try:
        from notifications.services import create_and_dispatch
        from notifications.constants import (
            NOTIF_SYSTEM_HEALTH_DEGRADED,
            SEVERITY_CRITICAL,
        )
        from accounts.models import Role, UserRoleAssignment

        if not organization:
            # Without org scope, skip — alerts need a company context
            logger.warning("Security alert skipped (no org): event=%s", event)
            return

        create_and_dispatch(
            company=organization,
            notification_type=NOTIF_SYSTEM_HEALTH_DEGRADED,
            severity=SEVERITY_CRITICAL,
            title=title,
            message=f"Security event: {event}. Review the Security Audit Log.",
            source_type="SECURITY_AUDIT",
            source_id=event,
            metadata={"event": event, **(metadata or {})},
        )

    except Exception:
        logger.error(
            "Failed to deliver security notification: event=%s", event, exc_info=True
        )


# =============================================================================
# Security checks
# =============================================================================

def check_password_change_safety(user, old_password):
    """
    Verify the old password matches before allowing a password change.
    Returns True if the old password is correct.
    """
    if not user or not user.is_authenticated:
        return False
    return user.check_password(old_password)


def revoke_user_sessions(user):
    """
    Revoke all active JWT refresh tokens for a user by blacklisting them.

    Called when:
    - A user account is disabled.
    - A user changes their password (optional, configurable).
    - An admin forces a session revocation.

    This does NOT invalidate already-issued access tokens (JWT limitation).
    Access tokens expire naturally based on ACCESS_TOKEN_LIFETIME.
    """
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

    count = 0
    try:
        outstanding = OutstandingToken.objects.filter(user=user)
        for token in outstanding:
            try:
                from rest_framework_simplejwt.tokens import RefreshToken
                RefreshToken(token.token).blacklist()
                count += 1
            except Exception:
                # Token may already be blacklisted or expired — skip.
                pass
    except Exception:
        logger.error("Failed to revoke sessions for user=%s", getattr(user, "email", "?"), exc_info=True)

    if count:
        logger.info("Revoked %d sessions for user=%s", count, getattr(user, "email", "?"))
    return count
