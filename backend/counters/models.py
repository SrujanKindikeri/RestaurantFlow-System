# =============================================================================
# RestaurantFlow — Counters Models
# Phase 4: Counter, CounterAssignment, Shift, CounterSession
#
# Hierarchy:
#   Branch
#       └── Counter  (physical POS station)
#               ├── CounterAssignment  (cashier ↔ counter link)
#               └── CounterSession     (one cash session per counter)
#
# Design principles:
#   - UUID primary keys on all business models.
#   - Soft disable via is_active / status — never hard-delete.
#   - PROTECT foreign keys — no accidental cascade deletion of history.
#   - Decimal for all monetary values — never float.
#   - Conditional unique constraint: only ONE open session per counter.
#   - Concurrency protection: select_for_update() in the service layer.
#   - Counter code is unique within a branch (branch + code).
#   - Counter status ≠ Counter Session status — clearly separated.
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel

logger = logging.getLogger("counters")


# =============================================================================
# Counter Type choices
# =============================================================================

class CounterType(models.TextChoices):
    MAIN_BILLING  = "MAIN_BILLING",  "Main Billing"
    TAKEAWAY      = "TAKEAWAY",      "Takeaway"
    SNACKS        = "SNACKS",        "Snacks"
    DRIVE_THROUGH = "DRIVE_THROUGH", "Drive Through"
    OTHER         = "OTHER",         "Other"


# =============================================================================
# Counter Status choices
# =============================================================================

class CounterStatus(models.TextChoices):
    ACTIVE      = "ACTIVE",      "Active"
    INACTIVE    = "INACTIVE",    "Inactive"
    MAINTENANCE = "MAINTENANCE", "Maintenance"


# =============================================================================
# Counter Session Status choices
# =============================================================================

class SessionStatus(models.TextChoices):
    OPEN         = "OPEN",         "Open"
    CLOSED       = "CLOSED",       "Closed"
    FORCE_CLOSED = "FORCE_CLOSED", "Force Closed"


# =============================================================================
# Shift
# =============================================================================

class Shift(TimestampedModel):
    """
    A named shift schedule for a branch.

    Shifts are configurations — they are NOT permanently tied to a single
    employee.  Actual work is captured by CounterSession.

    Examples:
        Morning  08:00–16:00
        Evening  16:00–00:00
        Night    00:00–08:00
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="shifts",
    )
    name = models.CharField(max_length=100)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"
        ordering = ["branch", "start_time"]
        indexes = [
            models.Index(fields=["branch", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.branch.name})"


# =============================================================================
# Counter
# =============================================================================

class Counter(TimestampedModel):
    """
    A physical POS billing station at a Branch.

    Counter code is unique within its branch (branch + code uniqueness enforced
    at the DB level).  Two different branches may each have a counter coded C01.

    Status separates:
        ACTIVE      — normal operation
        INACTIVE    — temporarily disabled; no new sessions
        MAINTENANCE — under maintenance; no new sessions

    is_active mirrors status == ACTIVE for quick boolean queries.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="counters",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=20, db_index=True)
    description = models.TextField(blank=True)
    counter_type = models.CharField(
        max_length=20,
        choices=CounterType.choices,
        default=CounterType.MAIN_BILLING,
        db_index=True,
    )
    location = models.CharField(max_length=200, blank=True)

    # Status field — primary operational state
    status = models.CharField(
        max_length=20,
        choices=CounterStatus.choices,
        default=CounterStatus.ACTIVE,
        db_index=True,
    )

    # is_active is a convenience boolean kept in sync with status == ACTIVE
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Counter"
        verbose_name_plural = "Counters"
        ordering = ["branch", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "code"],
                name="unique_counter_code_per_branch",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["branch", "code"]),
        ]

    def __str__(self):
        return f"{self.code} — {self.name} ({self.branch.name})"

    def save(self, *args, **kwargs):
        # Keep is_active in sync with status
        self.is_active = (self.status == CounterStatus.ACTIVE)
        # Normalise code to uppercase
        self.code = self.code.strip().upper()
        super().save(*args, **kwargs)

    @property
    def can_open_session(self) -> bool:
        """Return True only if this counter can accept a new session."""
        return self.status == CounterStatus.ACTIVE

    @property
    def current_session(self):
        """Return the currently OPEN session, or None."""
        return self.sessions.filter(status=SessionStatus.OPEN).first()


# =============================================================================
# CounterAssignment
# =============================================================================

class CounterAssignment(TimestampedModel):
    """
    Assignment of a user (cashier, manager) to a specific counter.

    Historical assignments are NEVER deleted — use is_active=False or set
    expires_at to end an assignment.  The history record remains intact.

    Multiple assignments may exist for a counter over time; only one should
    be active at any point for normal operation (enforced by the service layer,
    not a DB constraint, to allow overlap during shift handover).

    Scope validation (enforced in service layer):
        - counter.branch must be accessible by the assigned user
        - user must belong to the same organization / restaurant / branch scope
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    counter = models.ForeignKey(
        Counter,
        on_delete=models.PROTECT,
        related_name="assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="counter_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="counter_assignments_made",
        null=True,
        blank=True,
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Counter Assignment"
        verbose_name_plural = "Counter Assignments"
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["counter", "is_active"]),
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["counter", "user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user.email} → {self.counter.code} ({self.counter.branch.name})"


# =============================================================================
# CounterSession
# =============================================================================

class CounterSession(TimestampedModel):
    """
    One cash session at a Counter.

    Lifecycle:
        opened_by opens with opening_cash  → status = OPEN
        During session: transactions accumulate (Phase 5+)
        closed_by enters actual_cash       → status = CLOSED
        (or force-closed by manager)       → status = FORCE_CLOSED

    Cash reconciliation:
        cash_difference = actual_cash - expected_cash

    In Phase 4, expected_cash = opening_cash (no transactions yet).
    Future phases will add:
        opening_cash + cash_sales - cash_refunds ± adjustments = expected_cash

    Concurrency:
        The service layer uses select_for_update() + transaction.atomic()
        to prevent duplicate open sessions.
        A partial unique index (unique when status=OPEN) is applied via a
        database constraint.

    Financial fields use DecimalField — NEVER float.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    counter = models.ForeignKey(
        Counter,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sessions",
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="opened_sessions",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_sessions",
    )

    # Timestamps
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # Cash fields — Decimal only
    opening_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
    )
    expected_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text=(
            "Phase 4: equals opening_cash. "
            "Future phases will add sales/refunds/adjustments."
        ),
    )
    actual_cash = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    cash_difference = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="actual_cash - expected_cash. Calculated by backend; never trusted from client.",
    )

    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.OPEN,
        db_index=True,
    )
    closing_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Counter Session"
        verbose_name_plural = "Counter Sessions"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["counter", "status"]),
            models.Index(fields=["opened_by", "status"]),
            models.Index(fields=["counter", "opened_at"]),
        ]
        # Partial uniqueness at the DB level:
        # Only ONE open session per counter at a time.
        # Using a UniqueConstraint with a condition (PostgreSQL partial index).
        constraints = [
            models.UniqueConstraint(
                fields=["counter"],
                condition=models.Q(status="OPEN"),
                name="unique_open_session_per_counter",
            ),
        ]

    def __str__(self):
        return (
            f"Session {self.id} | {self.counter.code} | "
            f"{self.status} | opened by {self.opened_by.email}"
        )

    def save(self, *args, **kwargs):
        # Phase 4: expected_cash = opening_cash when first saved (session open).
        # Future phases will recalculate via transaction aggregations.
        if self.status == SessionStatus.OPEN and not self.pk:
            self.expected_cash = self.opening_cash
        super().save(*args, **kwargs)
