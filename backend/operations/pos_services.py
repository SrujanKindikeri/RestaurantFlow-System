# =============================================================================
# RestaurantFlow — POS Services
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone

from operations.constants import (
    POS_SESSION_ACTIVE, POS_SESSION_PAUSED, POS_SESSION_ENDED,
    AUDIT_POS_SESSION_STARTED, AUDIT_POS_SESSION_PAUSED,
    AUDIT_POS_SESSION_ENDED,
)
from operations.exceptions import (
    POSSessionConflict, CounterSessionNotActive, UnauthorizedCounter,
)

logger = logging.getLogger("operations")


def start_pos_session(*, user, counter_id, device_identifier="", branch):
    """
    Start a new POS session for the given user at the given counter.

    Security:
        - counter.branch must match the authorized branch.
        - Counter must be ACTIVE.
        - An OPEN CounterSession must exist.
        - Only ONE ACTIVE POSSession per (counter + user) at a time.

    Returns the new POSSession.
    """
    from counters.models import Counter, CounterStatus, SessionStatus
    from operations.models import POSSession, OperationsAuditLog

    with transaction.atomic():
        # Validate and lock the counter
        try:
            counter = (
                Counter.objects
                .select_for_update()
                .get(pk=counter_id, branch=branch)
            )
        except Counter.DoesNotExist:
            raise UnauthorizedCounter(
                "Counter does not exist or does not belong to your branch."
            )

        if counter.status != CounterStatus.ACTIVE:
            raise UnauthorizedCounter(
                f"Counter '{counter.code}' is not active (status={counter.status})."
            )

        # Must have an open CounterSession
        counter_session = counter.sessions.filter(
            status=SessionStatus.OPEN
        ).first()
        if not counter_session:
            raise CounterSessionNotActive(
                f"No open counter session for counter '{counter.code}'."
            )

        # Check for existing ACTIVE pos session
        existing = POSSession.objects.filter(
            counter=counter,
            user=user,
            status=POS_SESSION_ACTIVE,
        ).first()
        if existing:
            raise POSSessionConflict(
                "You already have an active POS session at this counter. "
                "End the existing session before starting a new one."
            )

        session = POSSession.objects.create(
            counter=counter,
            counter_session=counter_session,
            user=user,
            branch=branch,
            device_identifier=device_identifier,
            status=POS_SESSION_ACTIVE,
            last_activity_at=timezone.now(),
        )

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_POS_SESSION_STARTED,
            branch=branch,
            pos_session_id=session.id,
            metadata={
                "counter_id": str(counter.id),
                "counter_code": counter.code,
                "counter_session_id": str(counter_session.id),
            },
        )

    logger.info(
        "POS session started: user=%s counter=%s session=%s",
        user.email, counter.code, session.id,
    )
    return session


def pause_pos_session(*, session, user):
    """Pause an ACTIVE POS session."""
    from operations.models import OperationsAuditLog

    if session.status != POS_SESSION_ACTIVE:
        from operations.exceptions import POSSessionConflict
        raise POSSessionConflict(
            f"Cannot pause a session in status '{session.status}'."
        )

    with transaction.atomic():
        session.status = POS_SESSION_PAUSED
        session.last_activity_at = timezone.now()
        session.save(update_fields=["status", "last_activity_at", "updated_at"])

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_POS_SESSION_PAUSED,
            branch=session.branch,
            pos_session_id=session.id,
        )

    return session


def resume_pos_session(*, session, user):
    """Resume a PAUSED POS session."""
    from operations.models import OperationsAuditLog

    if session.status != POS_SESSION_PAUSED:
        from operations.exceptions import POSSessionConflict
        raise POSSessionConflict(
            f"Cannot resume a session in status '{session.status}'."
        )

    # Ensure no other ACTIVE session exists for same counter+user
    from operations.models import POSSession
    conflict = POSSession.objects.filter(
        counter=session.counter,
        user=user,
        status=POS_SESSION_ACTIVE,
    ).exclude(pk=session.pk).exists()
    if conflict:
        raise POSSessionConflict(
            "Another active POS session exists for this counter."
        )

    with transaction.atomic():
        session.status = POS_SESSION_ACTIVE
        session.last_activity_at = timezone.now()
        session.save(update_fields=["status", "last_activity_at", "updated_at"])

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_POS_SESSION_STARTED,
            branch=session.branch,
            pos_session_id=session.id,
            metadata={"resumed": True},
        )

    return session


def end_pos_session(*, session, user):
    """End an ACTIVE or PAUSED POS session."""
    from operations.models import OperationsAuditLog

    if session.status == POS_SESSION_ENDED:
        from operations.exceptions import POSSessionConflict
        raise POSSessionConflict("This POS session is already ended.")

    with transaction.atomic():
        session.status = POS_SESSION_ENDED
        session.ended_at = timezone.now()
        session.last_activity_at = timezone.now()
        session.save(
            update_fields=["status", "ended_at", "last_activity_at", "updated_at"]
        )

        OperationsAuditLog.objects.create(
            actor=user,
            event_type=AUDIT_POS_SESSION_ENDED,
            branch=session.branch,
            pos_session_id=session.id,
        )

    return session


def scan_barcode_or_sku(*, barcode_or_sku, branch):
    """
    Resolve a barcode/SKU to a MenuItem with current pricing for the branch.

    Returns a dict with: menu_item, price, tax_rate, tax_code
    Never trusts frontend price — always resolves from DB.
    """
    from menu.models import MenuItem, MenuItemAvailability
    from operations.exceptions import SKUNotFound

    # Try exact SKU match first, then barcode match
    item_qs = MenuItem.objects.filter(
        is_active=True,
    ).filter(
        models.Q(sku=barcode_or_sku) | models.Q(barcode=barcode_or_sku)
        if hasattr(MenuItem, "barcode")
        else models.Q(sku=barcode_or_sku)
    )

    item = item_qs.first()
    if not item:
        raise SKUNotFound(
            f"No active menu item found for '{barcode_or_sku}'."
        )

    # Check branch availability (if the app has availability model)
    try:
        availability = MenuItemAvailability.objects.get(
            menu_item=item, branch=branch
        )
        if not availability.is_available:
            raise SKUNotFound(
                f"Item '{item.name}' is not available at this branch."
            )
        price = availability.override_price
        tax_rate = availability.tax_rate
        tax_code = getattr(availability, "tax_code", "")
    except Exception:
        # Fall back to item defaults if availability model not applicable
        price = getattr(item, "base_price", None)
        tax_rate = getattr(item, "tax_rate", None)
        tax_code = getattr(item, "tax_code", "")

    return {
        "menu_item": item,
        "menu_item_id": str(item.id),
        "name": item.name,
        "sku": item.sku,
        "price": str(price) if price else None,
        "tax_rate": str(tax_rate) if tax_rate else "0.000",
        "tax_code": tax_code or "",
    }


def get_active_pos_session(*, user, counter):
    """Return the active POS session for user+counter, or None."""
    from operations.models import POSSession
    return POSSession.objects.filter(
        user=user,
        counter=counter,
        status=POS_SESSION_ACTIVE,
    ).first()


# Import models inside functions to avoid circular imports
import django.db.models as models
