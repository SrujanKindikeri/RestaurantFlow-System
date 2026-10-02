# =============================================================================
# RestaurantFlow — Counter Services
# Phase 4
#
# All business logic for counter lifecycle lives here.
# Views call these; serializers validate input shapes.
#
# Services:
#   open_session(actor, counter, opening_cash, shift)    → CounterSession
#   close_session(actor, session, actual_cash, note)     → CounterSession
#   force_close_session(actor, session, actual_cash, reason) → CounterSession
#   assign_counter(actor, counter, user, expires_at)     → CounterAssignment
#   deactivate_assignment(actor, assignment)             → CounterAssignment
#   disable_counter(actor, counter)                      → Counter
#   reactivate_counter(actor, counter)                   → Counter
#
# Concurrency:
#   open_session uses select_for_update() + transaction.atomic() to
#   prevent two simultaneous open-session requests from succeeding.
# =============================================================================

import logging
from decimal import Decimal

from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from counters import access as counter_acl
from .models import Counter, CounterAssignment, CounterSession, CounterStatus, SessionStatus

logger = logging.getLogger("counters")


# ---------------------------------------------------------------------------
# Open session
# ---------------------------------------------------------------------------

def open_session(actor, *, counter, opening_cash, shift=None):
    """
    Open a new cash session on a counter.

    Checks:
        - actor is authenticated and active
        - actor has counter.session.open permission
        - actor can access the counter's branch
        - counter is ACTIVE
        - no existing OPEN session on this counter (with DB-level lock)

    Returns the newly created CounterSession.
    """
    _require_auth(actor)

    if not acl.has_permission(actor, "counter.session.open"):
        raise PermissionDenied("You do not have permission to open a counter session.")

    if not counter_acl.can_access_counter(actor, counter):
        raise PermissionDenied("You do not have access to this counter.")

    if counter.status == CounterStatus.INACTIVE:
        raise ValidationError(
            {
                "code": "COUNTER_INACTIVE",
                "message": "This counter is inactive and cannot accept a new session.",
            }
        )
    if counter.status == CounterStatus.MAINTENANCE:
        raise ValidationError(
            {
                "code": "COUNTER_MAINTENANCE",
                "message": "This counter is under maintenance and cannot accept a new session.",
            }
        )

    opening_cash = Decimal(str(opening_cash))
    if opening_cash < Decimal("0.00"):
        raise ValidationError(
            {
                "code": "INVALID_OPENING_CASH",
                "message": "Opening cash cannot be negative.",
            }
        )

    try:
        with transaction.atomic():
            # Lock the counter row to prevent concurrent open-session requests
            locked_counter = Counter.objects.select_for_update().get(pk=counter.pk)

            existing = CounterSession.objects.filter(
                counter=locked_counter, status=SessionStatus.OPEN
            ).first()
            if existing:
                raise ValidationError(
                    {
                        "code": "COUNTER_SESSION_ALREADY_OPEN",
                        "message": "This counter already has an open session.",
                    }
                )

            session = CounterSession.objects.create(
                counter=locked_counter,
                shift=shift,
                opened_by=actor,
                opening_cash=opening_cash,
                expected_cash=opening_cash,  # Phase 4: no transactions yet
                status=SessionStatus.OPEN,
            )
            logger.info(
                "Counter session opened: counter=%s session=%s by user=%s opening_cash=%s",
                locked_counter.code,
                session.id,
                actor.email,
                opening_cash,
            )
            return session

    except IntegrityError:
        # Catches the DB-level partial unique constraint as a last resort
        raise ValidationError(
            {
                "code": "COUNTER_SESSION_ALREADY_OPEN",
                "message": "This counter already has an open session.",
            }
        )


# ---------------------------------------------------------------------------
# Close session
# ---------------------------------------------------------------------------

def close_session(actor, *, session, actual_cash, closing_note=""):
    """
    Close a counter session.

    Checks:
        - actor has counter.session.close permission
        - actor can access the session's counter
        - session is currently OPEN

    Calculates cash_difference = actual_cash - expected_cash server-side.
    """
    _require_auth(actor)

    if not acl.has_permission(actor, "counter.session.close"):
        raise PermissionDenied("You do not have permission to close a counter session.")

    if not counter_acl.can_access_counter(actor, session.counter):
        raise PermissionDenied("You do not have access to this counter session.")

    if session.status != SessionStatus.OPEN:
        raise ValidationError(
            {
                "code": "COUNTER_SESSION_NOT_OPEN",
                "message": "This session is not open and cannot be closed.",
            }
        )

    actual_cash = Decimal(str(actual_cash))
    if actual_cash < Decimal("0.00"):
        raise ValidationError(
            {
                "code": "INVALID_ACTUAL_CASH",
                "message": "Actual cash cannot be negative.",
            }
        )

    with transaction.atomic():
        session.actual_cash = actual_cash
        session.cash_difference = actual_cash - session.expected_cash
        session.status = SessionStatus.CLOSED
        session.closed_by = actor
        session.closed_at = timezone.now()
        session.closing_note = closing_note or ""
        session.save(update_fields=[
            "actual_cash", "cash_difference", "status",
            "closed_by", "closed_at", "closing_note", "updated_at",
        ])

    logger.info(
        "Counter session closed: session=%s counter=%s by user=%s "
        "actual=%s expected=%s diff=%s",
        session.id,
        session.counter.code,
        actor.email,
        session.actual_cash,
        session.expected_cash,
        session.cash_difference,
    )
    return session


# ---------------------------------------------------------------------------
# Force close session
# ---------------------------------------------------------------------------

def force_close_session(actor, *, session, actual_cash=None, reason=""):
    """
    Force-close a counter session (manager / authorized user).

    Requires counter.session.force_close permission.
    actual_cash is optional for force-close; if omitted, it remains NULL.
    """
    _require_auth(actor)

    if not acl.has_permission(actor, "counter.session.force_close"):
        raise PermissionDenied(
            {
                "code": "FORCE_CLOSE_NOT_ALLOWED",
                "message": "You do not have permission to force-close a counter session.",
            }
        )

    if not counter_acl.can_access_counter(actor, session.counter):
        raise PermissionDenied("You do not have access to this counter session.")

    if session.status != SessionStatus.OPEN:
        raise ValidationError(
            {
                "code": "COUNTER_SESSION_NOT_OPEN",
                "message": "This session is not open.",
            }
        )

    if actual_cash is not None:
        actual_cash = Decimal(str(actual_cash))
        if actual_cash < Decimal("0.00"):
            raise ValidationError(
                {
                    "code": "INVALID_ACTUAL_CASH",
                    "message": "Actual cash cannot be negative.",
                }
            )
        session.actual_cash = actual_cash
        session.cash_difference = actual_cash - session.expected_cash

    with transaction.atomic():
        session.status = SessionStatus.FORCE_CLOSED
        session.closed_by = actor
        session.closed_at = timezone.now()
        session.closing_note = reason or ""
        update_fields = [
            "status", "closed_by", "closed_at", "closing_note", "updated_at",
        ]
        if actual_cash is not None:
            update_fields += ["actual_cash", "cash_difference"]
        session.save(update_fields=update_fields)

    logger.warning(
        "Counter session FORCE CLOSED: session=%s counter=%s by user=%s reason='%s'",
        session.id,
        session.counter.code,
        actor.email,
        reason,
    )
    return session


# ---------------------------------------------------------------------------
# Counter assignment
# ---------------------------------------------------------------------------

def assign_counter(actor, *, counter, user, expires_at=None):
    """
    Assign a user to a counter.

    Checks:
        - actor has counter.assign permission
        - actor can access the counter
        - user belongs to the same branch/restaurant/org scope

    Historical assignments are preserved; deactivate old ones first if needed.
    """
    _require_auth(actor)

    if not acl.has_permission(actor, "counter.assign"):
        raise PermissionDenied("You do not have permission to assign users to counters.")

    if not counter_acl.can_access_counter(actor, counter):
        raise PermissionDenied("You do not have access to this counter.")

    # Validate that the target user can access this counter's branch
    if not acl.can_access_branch(user, counter.branch):
        raise ValidationError(
            {
                "code": "COUNTER_ACCESS_DENIED",
                "message": (
                    f"User '{user.email}' does not have access to branch "
                    f"'{counter.branch.name}'. Cannot assign to this counter."
                ),
            }
        )

    with transaction.atomic():
        assignment = CounterAssignment.objects.create(
            counter=counter,
            user=user,
            assigned_by=actor,
            expires_at=expires_at,
            is_active=True,
        )

    logger.info(
        "Counter assigned: counter=%s user=%s by actor=%s",
        counter.code,
        user.email,
        actor.email,
    )
    return assignment


def deactivate_assignment(actor, *, assignment):
    """Soft-deactivate a counter assignment."""
    _require_auth(actor)

    if not acl.has_permission(actor, "counter.unassign"):
        raise PermissionDenied("You do not have permission to unassign users from counters.")

    if not counter_acl.can_access_counter(actor, assignment.counter):
        raise PermissionDenied("You do not have access to this counter assignment.")

    assignment.is_active = False
    assignment.save(update_fields=["is_active", "updated_at"])

    logger.info(
        "Counter assignment deactivated: id=%s counter=%s user=%s by actor=%s",
        assignment.pk,
        assignment.counter.code,
        assignment.user.email,
        actor.email,
    )
    return assignment


# ---------------------------------------------------------------------------
# Counter lifecycle
# ---------------------------------------------------------------------------

def disable_counter(actor, *, counter):
    """Set counter status to INACTIVE."""
    _require_auth(actor)

    if not acl.has_permission(actor, "counter.disable"):
        raise PermissionDenied("You do not have permission to disable this counter.")

    if not counter_acl.can_access_counter(actor, counter):
        raise PermissionDenied("You do not have access to this counter.")

    counter.status = CounterStatus.INACTIVE
    counter.is_active = False
    counter.save(update_fields=["status", "is_active", "updated_at"])

    logger.info(
        "Counter disabled: counter=%s by actor=%s",
        counter.code,
        actor.email,
    )
    return counter


def reactivate_counter(actor, *, counter):
    """Set counter status back to ACTIVE."""
    _require_auth(actor)

    if not acl.has_permission(actor, "counter.update"):
        raise PermissionDenied("You do not have permission to reactivate this counter.")

    if not counter_acl.can_access_counter(actor, counter):
        raise PermissionDenied("You do not have access to this counter.")

    counter.status = CounterStatus.ACTIVE
    counter.is_active = True
    counter.save(update_fields=["status", "is_active", "updated_at"])

    logger.info(
        "Counter reactivated: counter=%s by actor=%s",
        counter.code,
        actor.email,
    )
    return counter


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _require_auth(user):
    if not user or not getattr(user, "is_authenticated", False) or not user.is_active:
        raise PermissionDenied("Authentication required.")
