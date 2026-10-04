# =============================================================================
# RestaurantFlow — Central Control Center Models
# Phase 15
#
# Models:
#   CentralControlSettings  — per-company configurable thresholds
#   CentralAlert            — operational alerts with deduplication fingerprint
#   EscalationRule          — alert→issue escalation configuration
#   CentralIssue            — tracked operational issues
#   CentralSystemEvent      — organization-level event timeline
#   CentralControlAuditLog  — immutable append-only audit trail
#
# Design principles:
#   - UUID primary keys on all business models.
#   - TimestampedModel base for created_at/updated_at.
#   - PROTECT foreign keys — no accidental cascade deletion.
#   - All monetary values use DecimalField — never float.
#   - Alert deduplication via fingerprint field + UniqueConstraint on active alerts.
#   - Audit log rows cannot be updated after creation (save() guard).
#   - Company/restaurant/branch scope enforced in service layer.
#   - Never duplicate models from other apps — reference by FK only.
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel
from central_control.constants import (
    ALERT_SEVERITY_CHOICES, SEVERITY_MEDIUM,
    ALERT_STATUS_CHOICES, ALERT_OPEN,
    ALERT_TYPE_CHOICES,
    SOURCE_TYPE_CHOICES,
    ISSUE_CATEGORY_CHOICES,
    ISSUE_SEVERITY_CHOICES, ISSUE_SEVERITY_MEDIUM,
    ISSUE_STATUS_CHOICES, ISSUE_OPEN,
    AUDIT_ACTION_CHOICES,
    DEFAULT_KITCHEN_DELAY_MINUTES,
    DEFAULT_KITCHEN_BACKLOG_THRESHOLD,
    DEFAULT_PAYMENT_FAILURE_THRESHOLD,
    DEFAULT_COUNTER_SESSION_MAX_HOURS,
)

logger = logging.getLogger("central_control")


# =============================================================================
# CentralControlSettings
# =============================================================================

class CentralControlSettings(TimestampedModel):
    """
    Per-company configuration for Central Control Center behavior.

    OneToOne with Organization. Contains all configurable thresholds
    used by the alert detection engine and health rule engine.

    Thresholds are validated before save to prevent nonsensical values.
    All fields have safe defaults so the system works without configuration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="central_control_settings",
    )

    # -------------------------------------------------------------------------
    # Kitchen thresholds
    # -------------------------------------------------------------------------
    kitchen_delay_minutes = models.PositiveIntegerField(
        default=DEFAULT_KITCHEN_DELAY_MINUTES,
        help_text=(
            "Minutes before a PREPARING kitchen order is considered delayed. "
            "Range: 1–480."
        ),
    )
    kitchen_backlog_threshold = models.PositiveIntegerField(
        default=DEFAULT_KITCHEN_BACKLOG_THRESHOLD,
        help_text=(
            "Number of pending/preparing kitchen orders that triggers a "
            "KITCHEN_BACKLOG alert. Range: 1–500."
        ),
    )

    # -------------------------------------------------------------------------
    # Inventory alert toggles
    # -------------------------------------------------------------------------
    low_stock_alert_enabled = models.BooleanField(
        default=True,
        help_text="If False, LOW_STOCK alerts are not generated.",
    )
    out_of_stock_alert_enabled = models.BooleanField(
        default=True,
        help_text="If False, OUT_OF_STOCK alerts are not generated.",
    )

    # -------------------------------------------------------------------------
    # Financial alert toggles
    # -------------------------------------------------------------------------
    payable_overdue_alert_enabled = models.BooleanField(
        default=True,
        help_text="If False, PAYABLE_OVERDUE alerts are not generated.",
    )

    # -------------------------------------------------------------------------
    # Payment thresholds
    # -------------------------------------------------------------------------
    payment_failure_threshold = models.PositiveIntegerField(
        default=DEFAULT_PAYMENT_FAILURE_THRESHOLD,
        help_text=(
            "Number of FAILED payments within the detection window that "
            "triggers a PAYMENT_FAILURE alert. Range: 1–1000."
        ),
    )

    # -------------------------------------------------------------------------
    # Counter session thresholds
    # -------------------------------------------------------------------------
    counter_session_max_hours = models.PositiveIntegerField(
        default=DEFAULT_COUNTER_SESSION_MAX_HOURS,
        help_text=(
            "Hours after which an OPEN counter session is flagged as unusually long."
        ),
    )

    # -------------------------------------------------------------------------
    # Escalation settings
    # -------------------------------------------------------------------------
    alert_escalation_enabled = models.BooleanField(
        default=True,
        help_text="Master switch for the alert→issue escalation engine.",
    )
    issue_auto_creation_enabled = models.BooleanField(
        default=True,
        help_text="Allow escalation rules to automatically create CentralIssues.",
    )

    class Meta:
        verbose_name = "Central Control Settings"
        verbose_name_plural = "Central Control Settings"

    def __str__(self):
        return f"CentralControlSettings — {self.organization.name}"

    def clean(self):
        from central_control.validators import validate_settings_thresholds
        validate_settings_thresholds({
            "kitchen_delay_minutes": self.kitchen_delay_minutes,
            "kitchen_backlog_threshold": self.kitchen_backlog_threshold,
            "payment_failure_threshold": self.payment_failure_threshold,
        })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


# =============================================================================
# CentralAlert
# =============================================================================

class CentralAlert(TimestampedModel):
    """
    An operational alert surfaced by the Central Control Center.

    Alerts are OBSERVED conditions, not transactions.  The central alert
    engine reads existing data from other apps (kitchen, inventory, payments,
    etc.) and surfaces conditions that require attention.

    DEDUPLICATION:
        The `fingerprint` field encodes a deterministic string derived from
        (alert_type + source_type + source_id + company + restaurant + branch).
        An active alert with the same fingerprint will be updated rather than
        duplicated. A UniqueConstraint prevents two OPEN/ACKNOWLEDGED alerts
        with the same fingerprint.

    LIFECYCLE:
        OPEN → ACKNOWLEDGED → RESOLVED
        OPEN → DISMISSED
        OPEN → EXPIRED

    Alerts are NEVER deleted — the full lifecycle history is preserved.
    Resolved/dismissed alerts serve as historical records.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Scope — company is mandatory; restaurant/branch are optional
    # -------------------------------------------------------------------------
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="central_alerts",
        db_index=True,
        help_text="The company/organization this alert belongs to.",
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="central_alerts",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="central_alerts",
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Alert identity
    # -------------------------------------------------------------------------
    alert_type = models.CharField(
        max_length=40,
        choices=ALERT_TYPE_CHOICES,
        db_index=True,
    )
    severity = models.CharField(
        max_length=10,
        choices=ALERT_SEVERITY_CHOICES,
        default=SEVERITY_MEDIUM,
        db_index=True,
    )
    title = models.CharField(max_length=300)
    message = models.TextField()

    # -------------------------------------------------------------------------
    # Source reference — what object triggered this alert
    # -------------------------------------------------------------------------
    source_type = models.CharField(
        max_length=30,
        choices=SOURCE_TYPE_CHOICES,
        db_index=True,
        blank=True,
    )
    source_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="String ID of the source object (UUID or composite key).",
    )

    # -------------------------------------------------------------------------
    # Deduplication fingerprint
    # -------------------------------------------------------------------------
    fingerprint = models.CharField(
        max_length=255,
        db_index=True,
        help_text=(
            "Deterministic string that identifies this alert condition. "
            "Derived from alert_type + source_type + source_id + scoping. "
            "Used to prevent duplicate active alerts for the same condition."
        ),
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=ALERT_STATUS_CHOICES,
        default=ALERT_OPEN,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Lifecycle timestamps and actors
    # -------------------------------------------------------------------------
    detected_at = models.DateTimeField(
        db_index=True,
        help_text="When this alert condition was first detected.",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="If set, the alert auto-expires at this timestamp.",
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="acknowledged_central_alerts",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_central_alerts",
    )
    resolution_note = models.TextField(blank=True)

    # Detection count — incremented when the same condition is re-detected
    detection_count = models.PositiveIntegerField(
        default=1,
        help_text="How many times this condition has been detected/re-detected.",
    )
    last_detected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent re-detection.",
    )

    class Meta:
        verbose_name = "Central Alert"
        verbose_name_plural = "Central Alerts"
        ordering = ["-detected_at"]
        constraints = [
            # Prevent two OPEN or ACKNOWLEDGED alerts with the same fingerprint
            # for the same organization. This is the core deduplication constraint.
            models.UniqueConstraint(
                fields=["organization", "fingerprint", "status"],
                condition=models.Q(status__in=["OPEN", "ACKNOWLEDGED"]),
                name="unique_active_alert_per_fingerprint_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "severity"]),
            models.Index(fields=["organization", "alert_type"]),
            models.Index(fields=["organization", "status", "severity"]),
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["alert_type", "status"]),
            models.Index(fields=["severity", "status"]),
            models.Index(fields=["detected_at"]),
            models.Index(fields=["source_type", "source_id"]),
            models.Index(fields=["fingerprint"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.alert_type} — {self.title[:60]} [{self.status}]"

    @property
    def is_active(self) -> bool:
        from central_control.constants import ALERT_ACTIVE_STATUSES
        return self.status in ALERT_ACTIVE_STATUSES

    @property
    def is_terminal(self) -> bool:
        from central_control.constants import ALERT_TERMINAL_STATUSES
        return self.status in ALERT_TERMINAL_STATUSES


# =============================================================================
# EscalationRule
# =============================================================================

class EscalationRule(TimestampedModel):
    """
    Configures when an unresolved alert should automatically create a
    CentralIssue.

    Example:
        If KITCHEN_DELAY alert with severity HIGH remains unresolved for
        30 minutes, create a CentralIssue and assign to RESTAURANT_MANAGER.

    Rules are evaluated by the EscalationEngine in alert_rules.py.
    They are company-scoped and optional (null → applies to all restaurants).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="escalation_rules",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="escalation_rules",
        db_index=True,
        help_text="If null, rule applies to all restaurants in the org.",
    )

    # Which alert type and severity triggers this rule
    alert_type = models.CharField(
        max_length=40,
        choices=ALERT_TYPE_CHOICES,
        db_index=True,
    )
    severity = models.CharField(
        max_length=10,
        choices=ALERT_SEVERITY_CHOICES,
        db_index=True,
    )

    # How long (minutes) the alert must remain unresolved before escalating
    threshold_minutes = models.PositiveIntegerField(
        default=30,
        help_text=(
            "Minutes the alert must remain unresolved before this rule fires. "
            "Range: 1–1440 (24 hours)."
        ),
    )

    # What to do when the rule fires
    auto_create_issue = models.BooleanField(
        default=True,
        help_text="If True, automatically create a CentralIssue when this rule fires.",
    )
    escalation_target_role = models.CharField(
        max_length=50,
        blank=True,
        help_text=(
            "Role code (e.g. RESTAURANT_MANAGER) of the user to assign "
            "the auto-created issue to. Leave blank for unassigned."
        ),
    )

    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Escalation Rule"
        verbose_name_plural = "Escalation Rules"
        ordering = ["alert_type", "severity"]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["alert_type", "severity"]),
        ]

    def __str__(self):
        return (
            f"EscalationRule: {self.alert_type} [{self.severity}] "
            f"→ {self.threshold_minutes}min "
            f"→ {self.escalation_target_role or 'unassigned'}"
        )


# =============================================================================
# CentralIssue
# =============================================================================

class CentralIssue(TimestampedModel):
    """
    A tracked operational issue requiring investigation and resolution.

    CentralIssues are created manually or automatically from CentralAlerts
    via the escalation engine.  Unlike alerts (which are conditions), issues
    are tasks — they have owners, due dates, and a workflow.

    CLOSED issues are immutable: the service layer prevents any further changes
    except in controlled administrative corrections.

    Critical issues require a resolution note before RESOLVED → CLOSED.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Scope
    # -------------------------------------------------------------------------
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="central_issues",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="central_issues",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="central_issues",
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    category = models.CharField(
        max_length=20,
        choices=ISSUE_CATEGORY_CHOICES,
        db_index=True,
    )
    title = models.CharField(max_length=300)
    description = models.TextField()

    severity = models.CharField(
        max_length=10,
        choices=ISSUE_SEVERITY_CHOICES,
        default=ISSUE_SEVERITY_MEDIUM,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=ISSUE_STATUS_CHOICES,
        default=ISSUE_OPEN,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Link to originating alert (optional)
    # -------------------------------------------------------------------------
    detected_from_alert = models.ForeignKey(
        CentralAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_issues",
        db_index=True,
        help_text="The CentralAlert that triggered creation of this issue.",
    )

    # -------------------------------------------------------------------------
    # Assignment and actors
    # -------------------------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_central_issues",
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_central_issues",
        db_index=True,
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="resolved_central_issues",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_central_issues",
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancelled_central_issues",
    )

    # -------------------------------------------------------------------------
    # Timing
    # -------------------------------------------------------------------------
    due_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Optional deadline for issue resolution.",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    resolution_note = models.TextField(
        blank=True,
        help_text="Required for CRITICAL issues when resolving.",
    )

    class Meta:
        verbose_name = "Central Issue"
        verbose_name_plural = "Central Issues"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["organization", "severity"]),
            models.Index(fields=["organization", "status", "severity"]),
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["due_at"]),
            models.Index(fields=["severity", "status"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.title[:80]} [{self.status}]"

    @property
    def is_active(self) -> bool:
        from central_control.constants import ISSUE_ACTIVE_STATUSES
        return self.status in ISSUE_ACTIVE_STATUSES

    @property
    def is_terminal(self) -> bool:
        from central_control.constants import ISSUE_TERMINAL_STATUSES
        return self.status in ISSUE_TERMINAL_STATUSES


# =============================================================================
# CentralSystemEvent
# =============================================================================

class CentralSystemEvent(TimestampedModel):
    """
    An entry in the organization-level event timeline.

    These are significant operational events — not every transaction.
    Examples: branch status change, critical alert, issue created/resolved,
    accounting exception, unusual activity.

    Events are APPEND-ONLY — never modified after creation.
    They power the real-time event timeline in the Central Control UI.
    """

    EVENT_KITCHEN_DELAY      = "KITCHEN_DELAY"
    EVENT_KITCHEN_BACKLOG     = "KITCHEN_BACKLOG"
    EVENT_INVENTORY_LOW       = "INVENTORY_LOW"
    EVENT_INVENTORY_OUT       = "INVENTORY_OUT"
    EVENT_PAYMENT_EXCEPTION   = "PAYMENT_EXCEPTION"
    EVENT_EXPENSE_APPROVAL    = "EXPENSE_APPROVAL"
    EVENT_PAYABLE_OVERDUE     = "PAYABLE_OVERDUE"
    EVENT_ACCOUNTING_EXCEPT   = "ACCOUNTING_EXCEPTION"
    EVENT_ISSUE_CREATED       = "ISSUE_CREATED"
    EVENT_ISSUE_RESOLVED      = "ISSUE_RESOLVED"
    EVENT_BRANCH_STATUS       = "BRANCH_STATUS_CHANGE"
    EVENT_USER_ACCESS         = "USER_ACCESS_EVENT"
    EVENT_SYSTEM_HEALTH       = "SYSTEM_HEALTH_EVENT"
    EVENT_ALERT_CREATED       = "ALERT_CREATED"
    EVENT_ALERT_RESOLVED      = "ALERT_RESOLVED"
    EVENT_COUNTER_EXCEPTION   = "COUNTER_EXCEPTION"

    EVENT_TYPE_CHOICES = [
        (EVENT_KITCHEN_DELAY,    "Kitchen Delay"),
        (EVENT_KITCHEN_BACKLOG,  "Kitchen Backlog"),
        (EVENT_INVENTORY_LOW,    "Inventory Low Stock"),
        (EVENT_INVENTORY_OUT,    "Inventory Out of Stock"),
        (EVENT_PAYMENT_EXCEPTION,"Payment Exception"),
        (EVENT_EXPENSE_APPROVAL, "Expense Approval"),
        (EVENT_PAYABLE_OVERDUE,  "Payable Overdue"),
        (EVENT_ACCOUNTING_EXCEPT,"Accounting Exception"),
        (EVENT_ISSUE_CREATED,    "Issue Created"),
        (EVENT_ISSUE_RESOLVED,   "Issue Resolved"),
        (EVENT_BRANCH_STATUS,    "Branch Status Change"),
        (EVENT_USER_ACCESS,      "User Access Event"),
        (EVENT_SYSTEM_HEALTH,    "System Health Event"),
        (EVENT_ALERT_CREATED,    "Alert Created"),
        (EVENT_ALERT_RESOLVED,   "Alert Resolved"),
        (EVENT_COUNTER_EXCEPTION,"Counter Session Exception"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="system_events",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="system_events",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="system_events",
        db_index=True,
    )

    event_type = models.CharField(
        max_length=40,
        choices=EVENT_TYPE_CHOICES,
        db_index=True,
    )
    severity = models.CharField(
        max_length=10,
        choices=ALERT_SEVERITY_CHOICES,
        default=SEVERITY_MEDIUM,
        db_index=True,
    )
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)

    # Optional link to the alert or issue that generated this event
    alert = models.ForeignKey(
        CentralAlert,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )
    issue = models.ForeignKey(
        CentralIssue,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )

    # Extra structured data for the event (e.g. order number, stock levels)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Extra structured context for this event.",
    )

    occurred_at = models.DateTimeField(
        db_index=True,
        help_text="When the event occurred.",
    )

    class Meta:
        verbose_name = "Central System Event"
        verbose_name_plural = "Central System Events"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["organization", "occurred_at"]),
            models.Index(fields=["organization", "event_type"]),
            models.Index(fields=["organization", "severity"]),
            models.Index(fields=["restaurant", "occurred_at"]),
            models.Index(fields=["branch", "occurred_at"]),
            models.Index(fields=["event_type", "occurred_at"]),
        ]

    def __str__(self):
        return f"[{self.event_type}] {self.title[:80]} @ {self.occurred_at}"


# =============================================================================
# CentralControlAuditLog
# =============================================================================

class CentralControlAuditLog(TimestampedModel):
    """
    Immutable append-only audit trail for Central Control Center actions.

    Every action by a Central Admin on alerts, issues, and configuration
    produces an audit entry. Rows cannot be updated after creation.

    Pattern follows existing per-domain audit logs (PaymentAuditLog,
    FinancialAuditLog, AccountingAuditLog).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="central_control_audit_entries",
    )
    action = models.CharField(
        max_length=50,
        choices=AUDIT_ACTION_CHOICES,
        db_index=True,
    )

    # What was acted on
    entity_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="e.g. ALERT, ISSUE, SETTINGS",
    )
    entity_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the entity being acted on.",
    )

    # Scope
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="central_audit_logs",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="central_audit_logs",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="central_audit_logs",
    )

    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, blank=True)

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional structured data about this action.",
    )

    class Meta:
        verbose_name = "Central Control Audit Log"
        verbose_name_plural = "Central Control Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["action", "created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["organization", "created_at"]),
        ]

    def __str__(self):
        return f"Audit: {self.action} on {self.entity_type}:{self.entity_id} by {self.actor_id}"

    def save(self, *args, **kwargs):
        # Immutable: block updates to existing rows
        if self.pk and CentralControlAuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError(
                "CentralControlAuditLog records are immutable — "
                "they cannot be updated after creation."
            )
        super().save(*args, **kwargs)
