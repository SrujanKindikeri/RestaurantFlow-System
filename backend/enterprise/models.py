# =============================================================================
# RestaurantFlow — Enterprise Models
# Phase 20: Multi-Branch Enterprise Operations & Configuration
#
# Model inventory:
#   BranchOperationalStatus  — extends Branch with operational status tracking
#   BranchOperatingHour      — weekly schedule per branch (supports overnight)
#   BranchClosure            — planned/emergency closure records
#   EnterpriseConfiguration  — hierarchical key/value config (company→restaurant→branch)
#   ConfigurationChange      — immutable history of every config mutation
#   MenuRollout              — orchestrated rollout of menu/price changes to branches
#   MenuRolloutBranch        — per-branch result record for a rollout
#   StaffBranchAssignment    — controlled assignment of users to branches
#   StaffTransfer            — branch-to-branch staff transfer workflow
#   ApprovalPolicy           — configurable threshold-based approval rules
#   EnterpriseAuditLog       — immutable audit trail of enterprise actions
#
# Design principles (consistent with Phases 1–19):
#   - UUID primary keys on all business models.
#   - Soft disable — never hard-delete.
#   - PROTECT foreign keys — no accidental cascade deletion.
#   - DecimalField for all monetary / rate values.
#   - TimestampedModel base on every model.
#   - Scope validation enforced in clean() / service layer.
#   - Audit log rows are immutable (save() blocks updates on existing rows).
#   - No duplicate models from other apps — extend or reference by FK only.
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel
from enterprise.constants import (
    # Branch status
    BRANCH_STATUS_ACTIVE,
    BRANCH_STATUS_CHOICES,
    # Days of week
    DAY_OF_WEEK_CHOICES,
    # Closure
    CLOSURE_TYPE_CHOICES,
    CLOSURE_STATUS_DRAFT,
    CLOSURE_STATUS_CHOICES,
    # Configuration
    VALUE_TYPE_CHOICES, VALUE_TYPE_STRING,
    ALLOWED_CONFIGURATION_KEY_CHOICES,
    CONFIG_SCOPE_CHOICES, CONFIG_SCOPE_COMPANY,
    # Rollout
    ROLLOUT_TYPE_CHOICES, ROLLOUT_TYPE_MENU_AVAILABILITY,
    ROLLOUT_SCOPE_CHOICES, ROLLOUT_SCOPE_ALL_BRANCHES,
    ROLLOUT_STATUS_DRAFT, ROLLOUT_STATUS_CHOICES,
    # Transfer
    TRANSFER_STATUS_REQUESTED, TRANSFER_STATUS_CHOICES,
    # Policy
    POLICY_TYPE_CHOICES,
    # Audit
    AUDIT_ACTION_CHOICES,
)

logger = logging.getLogger("enterprise")


# =============================================================================
# BranchOperationalStatus
# =============================================================================

class BranchOperationalStatus(TimestampedModel):
    """
    Extends Branch with an explicit operational status.

    OneToOne with Branch — created lazily when the branch first requires
    status tracking. This avoids adding a migration to the organizations app.

    Status:
        ACTIVE              — branch is open and operational
        TEMPORARILY_CLOSED  — short-term closure (e.g. staff illness)
        SCHEDULED_CLOSURE   — known upcoming closure (holiday)
        MAINTENANCE         — planned maintenance downtime
        INACTIVE            — branch is permanently deactivated

    Historical transactions always retain their original branch context.
    Deactivating a branch does NOT delete or modify historical data.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.OneToOneField(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="operational_status",
    )
    status = models.CharField(
        max_length=30,
        choices=BRANCH_STATUS_CHOICES,
        default=BRANCH_STATUS_ACTIVE,
        db_index=True,
    )
    status_changed_at = models.DateTimeField(null=True, blank=True)
    status_changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="branch_status_changes",
    )
    status_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Branch Operational Status"
        verbose_name_plural = "Branch Operational Statuses"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["branch", "status"]),
        ]

    def __str__(self):
        return f"{self.branch.name} — {self.status}"


# =============================================================================
# BranchOperatingHour
# =============================================================================

class BranchOperatingHour(TimestampedModel):
    """
    Weekly operating schedule for a branch.

    One row per (branch, day_of_week). Set is_closed=True for days the
    branch does not open at all.

    Overnight support:
        closing_time < opening_time  →  closing is NEXT day
        e.g. opening_time=18:00, closing_time=02:00 → closes 02:00 next morning

    Uniqueness:
        (branch, day_of_week) — one schedule row per day.
        Managed via UniqueConstraint; updates go through the service, not direct saves.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="operating_hours",
    )
    day_of_week = models.CharField(
        max_length=10,
        choices=DAY_OF_WEEK_CHOICES,
        db_index=True,
    )
    opening_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Null if is_closed=True.",
    )
    closing_time = models.TimeField(
        null=True,
        blank=True,
        help_text=(
            "Null if is_closed=True. "
            "May be less than opening_time for overnight schedules."
        ),
    )
    is_closed = models.BooleanField(
        default=False,
        help_text="True if the branch does not open on this day.",
    )

    class Meta:
        verbose_name = "Branch Operating Hour"
        verbose_name_plural = "Branch Operating Hours"
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "day_of_week"],
                name="unique_branch_operating_hour_per_day",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "day_of_week"]),
            models.Index(fields=["branch", "is_closed"]),
        ]
        ordering = ["branch", "day_of_week"]

    def __str__(self):
        if self.is_closed:
            return f"{self.branch.name} — {self.day_of_week}: Closed"
        return (
            f"{self.branch.name} — {self.day_of_week}: "
            f"{self.opening_time} → {self.closing_time}"
        )

    @property
    def is_overnight(self) -> bool:
        """True if closing_time < opening_time (closes the next calendar day)."""
        if self.is_closed or not self.opening_time or not self.closing_time:
            return False
        return self.closing_time < self.opening_time

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.is_closed:
            if not self.opening_time:
                raise ValidationError({"opening_time": "Opening time is required when branch is open."})
            if not self.closing_time:
                raise ValidationError({"closing_time": "Closing time is required when branch is open."})


# =============================================================================
# BranchClosure
# =============================================================================

class BranchClosure(TimestampedModel):
    """
    A planned or emergency closure record for a branch.

    Closures are never deleted — historical closure data is preserved.
    Terminal statuses: COMPLETED, CANCELLED, REJECTED.

    Lifecycle:
        DRAFT → PENDING_APPROVAL → APPROVED → ACTIVE → COMPLETED
        DRAFT → CANCELLED
        PENDING_APPROVAL → REJECTED
        APPROVED → CANCELLED
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="closures",
    )
    closure_type = models.CharField(
        max_length=20,
        choices=CLOSURE_TYPE_CHOICES,
        db_index=True,
    )
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField(db_index=True)
    reason = models.TextField(
        help_text="Human-readable explanation of why the branch is closing.",
    )
    status = models.CharField(
        max_length=20,
        choices=CLOSURE_STATUS_CHOICES,
        default=CLOSURE_STATUS_DRAFT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_closures",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_closures",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Branch Closure"
        verbose_name_plural = "Branch Closures"
        ordering = ["-start_datetime"]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "start_datetime"]),
            models.Index(fields=["branch", "end_datetime"]),
            models.Index(fields=["status", "start_datetime"]),
        ]

    def __str__(self):
        return (
            f"{self.branch.name} — {self.closure_type} "
            f"({self.start_datetime.date()} → {self.end_datetime.date()}) [{self.status}]"
        )

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.start_datetime and self.end_datetime:
            if self.end_datetime <= self.start_datetime:
                raise ValidationError(
                    {"end_datetime": "End datetime must be after start datetime."}
                )


# =============================================================================
# EnterpriseConfiguration
# =============================================================================

class EnterpriseConfiguration(TimestampedModel):
    """
    Hierarchical key/value configuration record.

    Scope resolution (most-specific wins):
        Branch override  → restaurant is set, branch is set
        Restaurant default → restaurant is set, branch is null
        Company default    → restaurant is null, branch is null

    Keys are allow-listed in constants.ALLOWED_CONFIGURATION_KEYS to prevent
    arbitrary configuration injection.

    Values are stored as strings and cast to their declared value_type by
    the ConfigurationResolver. Do not store executable content or secrets.

    Uniqueness: (company, restaurant, branch, configuration_key, is_active=True)
    — only one active value per key per scope.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Scope
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="enterprise_configurations",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="enterprise_configurations",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="enterprise_configurations",
        db_index=True,
    )

    # Key / value
    configuration_key = models.CharField(
        max_length=100,
        choices=ALLOWED_CONFIGURATION_KEY_CHOICES,
        db_index=True,
    )
    configuration_value = models.TextField(
        help_text="Value stored as string; cast by ConfigurationResolver.",
    )
    value_type = models.CharField(
        max_length=10,
        choices=VALUE_TYPE_CHOICES,
        default=VALUE_TYPE_STRING,
    )

    # Metadata
    is_active = models.BooleanField(default=True, db_index=True)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_configurations",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="updated_configurations",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Enterprise Configuration"
        verbose_name_plural = "Enterprise Configurations"
        ordering = ["company", "restaurant", "branch", "configuration_key"]
        constraints = [
            # Enforce at most one active value per key per scope
            models.UniqueConstraint(
                fields=["company", "configuration_key"],
                condition=models.Q(is_active=True, restaurant__isnull=True, branch__isnull=True),
                name="unique_active_company_config_key",
            ),
            models.UniqueConstraint(
                fields=["company", "restaurant", "configuration_key"],
                condition=models.Q(is_active=True, branch__isnull=True),
                name="unique_active_restaurant_config_key",
            ),
            models.UniqueConstraint(
                fields=["company", "restaurant", "branch", "configuration_key"],
                condition=models.Q(is_active=True),
                name="unique_active_branch_config_key",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "configuration_key", "is_active"]),
            models.Index(fields=["company", "restaurant", "configuration_key", "is_active"]),
            models.Index(fields=["company", "restaurant", "branch", "configuration_key", "is_active"]),
        ]

    def __str__(self):
        scope = f"org={self.company_id}"
        if self.restaurant_id:
            scope += f" rest={self.restaurant_id}"
        if self.branch_id:
            scope += f" branch={self.branch_id}"
        return f"[{scope}] {self.configuration_key} = {self.configuration_value}"

    @property
    def scope(self) -> str:
        from enterprise.constants import (
            CONFIG_SCOPE_BRANCH,
            CONFIG_SCOPE_RESTAURANT,
            CONFIG_SCOPE_COMPANY,
        )
        if self.branch_id:
            return CONFIG_SCOPE_BRANCH
        if self.restaurant_id:
            return CONFIG_SCOPE_RESTAURANT
        return CONFIG_SCOPE_COMPANY

    def clean(self):
        from django.core.exceptions import ValidationError
        from enterprise.validators import validate_configuration_value
        # Branch requires restaurant; restaurant requires company
        if self.branch_id and not self.restaurant_id:
            raise ValidationError(
                {"restaurant": "A branch-scoped configuration requires a restaurant."}
            )
        if self.restaurant_id and not self.company_id:
            raise ValidationError(
                {"company": "A restaurant-scoped configuration requires a company."}
            )
        # Branch must belong to restaurant
        if self.branch_id and self.restaurant_id:
            try:
                if str(self.branch.restaurant_id) != str(self.restaurant_id):
                    raise ValidationError(
                        {"branch": "Branch does not belong to the specified restaurant."}
                    )
            except Exception:
                pass
        # Validate value type
        if self.configuration_value and self.value_type:
            try:
                validate_configuration_value(self.configuration_value, self.value_type)
            except Exception as e:
                raise ValidationError({"configuration_value": str(e)})


# =============================================================================
# ConfigurationChange
# =============================================================================

class ConfigurationChange(TimestampedModel):
    """
    Immutable record of every change made to EnterpriseConfiguration.

    This model is append-only — rows must NEVER be updated after creation.
    Provides a full audit trail with old/new values, actor, and reason.

    created_at on TimestampedModel serves as changed_at.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Scope (denormalized for independent history queries)
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="configuration_changes",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="configuration_changes",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="configuration_changes",
    )

    # What changed
    configuration_key = models.CharField(max_length=100, db_index=True)
    old_value = models.TextField(
        blank=True,
        help_text="Empty string if this is a new configuration record.",
    )
    new_value = models.TextField()
    version = models.PositiveIntegerField(
        help_text="Version number of the EnterpriseConfiguration after this change.",
    )

    # Who / why
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="configuration_changes",
        null=True,
        blank=True,
    )
    change_reason = models.TextField(
        blank=True,
        help_text="Optional human-readable reason for this change.",
    )
    scope = models.CharField(
        max_length=20,
        choices=CONFIG_SCOPE_CHOICES,
        default=CONFIG_SCOPE_COMPANY,
        db_index=True,
    )

    class Meta:
        verbose_name = "Configuration Change"
        verbose_name_plural = "Configuration Changes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "configuration_key", "created_at"]),
            models.Index(fields=["company", "restaurant", "branch", "configuration_key"]),
            models.Index(fields=["changed_by", "created_at"]),
        ]

    def __str__(self):
        return f"{self.configuration_key} v{self.version} by {self.changed_by_id}"

    def save(self, *args, **kwargs):
        if self.pk and ConfigurationChange.objects.filter(pk=self.pk).exists():
            raise ValueError(
                "ConfigurationChange records are immutable — do not update existing rows."
            )
        super().save(*args, **kwargs)


# =============================================================================
# MenuRollout
# =============================================================================

class MenuRollout(TimestampedModel):
    """
    Orchestrated rollout of a menu item availability or price change to branches.

    A rollout targets either ALL branches in the restaurant or SELECTED branches.
    Branch-specific overrides are preserved unless force_override=True is set.

    Lifecycle:
        DRAFT → PENDING_APPROVAL → APPROVED → SCHEDULED → RUNNING
             → COMPLETED / PARTIALLY_COMPLETED / FAILED / CANCELLED

    A rollout must not be executed while another is RUNNING for the same item.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="menu_rollouts",
        db_index=True,
    )
    menu_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.PROTECT,
        related_name="rollouts",
    )
    rollout_type = models.CharField(
        max_length=30,
        choices=ROLLOUT_TYPE_CHOICES,
        default=ROLLOUT_TYPE_MENU_AVAILABILITY,
        db_index=True,
    )

    # For PRICE rollouts — the price to roll out
    new_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="For PRICE rollouts only — the new price to apply.",
    )

    # For MENU_AVAILABILITY rollouts
    is_available = models.BooleanField(
        null=True,
        blank=True,
        help_text="For MENU_AVAILABILITY rollouts — target availability state.",
    )

    # Whether this rollout should overwrite existing branch-specific overrides
    force_override = models.BooleanField(
        default=False,
        help_text="If True, overwrites existing branch-specific price/availability overrides.",
    )

    source_branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sourced_rollouts",
        help_text="Optional — copy configuration FROM this branch.",
    )

    target_scope = models.CharField(
        max_length=20,
        choices=ROLLOUT_SCOPE_CHOICES,
        default=ROLLOUT_SCOPE_ALL_BRANCHES,
    )
    target_branches = models.ManyToManyField(
        "organizations.Branch",
        blank=True,
        related_name="targeted_rollouts",
        help_text="Populated when target_scope=SELECTED_BRANCHES.",
    )

    effective_from = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this rollout becomes effective. Null = immediately on execution.",
    )
    status = models.CharField(
        max_length=25,
        choices=ROLLOUT_STATUS_CHOICES,
        default=ROLLOUT_STATUS_DRAFT,
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_rollouts",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_rollouts",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Menu Rollout"
        verbose_name_plural = "Menu Rollouts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "menu_item", "status"]),
            models.Index(fields=["status", "effective_from"]),
        ]

    def __str__(self):
        return (
            f"Rollout [{self.rollout_type}] {self.menu_item.name} "
            f"→ {self.restaurant.name} [{self.status}]"
        )


# =============================================================================
# MenuRolloutBranch
# =============================================================================

class MenuRolloutBranch(TimestampedModel):
    """
    Per-branch execution result record for a MenuRollout.

    Created during rollout execution to track which branches succeeded,
    failed, or were skipped (e.g. due to existing branch overrides).
    """

    RESULT_SUCCESS  = "SUCCESS"
    RESULT_FAILED   = "FAILED"
    RESULT_SKIPPED  = "SKIPPED"
    RESULT_OVERRIDE = "SKIPPED_OVERRIDE"

    RESULT_CHOICES = [
        (RESULT_SUCCESS,  "Success"),
        (RESULT_FAILED,   "Failed"),
        (RESULT_SKIPPED,  "Skipped"),
        (RESULT_OVERRIDE, "Skipped — Branch Override Preserved"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rollout = models.ForeignKey(
        MenuRollout,
        on_delete=models.PROTECT,
        related_name="branch_results",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="rollout_results",
    )
    result = models.CharField(
        max_length=20,
        choices=RESULT_CHOICES,
        db_index=True,
    )
    old_value = models.TextField(blank=True, help_text="Previous price or availability state.")
    new_value = models.TextField(blank=True, help_text="New price or availability state applied.")
    failure_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Menu Rollout Branch Result"
        verbose_name_plural = "Menu Rollout Branch Results"
        constraints = [
            models.UniqueConstraint(
                fields=["rollout", "branch"],
                name="unique_rollout_branch_result",
            ),
        ]
        indexes = [
            models.Index(fields=["rollout", "result"]),
            models.Index(fields=["branch", "result"]),
        ]

    def __str__(self):
        return f"{self.rollout} → {self.branch.name}: {self.result}"


# =============================================================================
# StaffBranchAssignment
# =============================================================================

class StaffBranchAssignment(TimestampedModel):
    """
    Controlled assignment of a user (staff member) to a branch.

    A user can have exactly ONE primary branch and any number of
    temporary/secondary branch assignments.

    This model does NOT duplicate UserRoleAssignment — it tracks the
    operational branch assignment layer used by enterprise workflows.
    Role-based access is still governed by accounts.UserRoleAssignment.

    Uniqueness: a user can have one active primary assignment per restaurant.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="branch_assignments",
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="staff_assignments",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="staff_assignments",
        db_index=True,
    )
    role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.PROTECT,
        related_name="branch_assignments",
        help_text="The role this staff member holds at this branch.",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    start_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this assignment becomes effective.",
    )
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="When this assignment expires. Null = indefinite.",
    )
    is_primary = models.BooleanField(
        default=True,
        help_text="True if this is the user's primary branch assignment.",
        db_index=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Staff Branch Assignment"
        verbose_name_plural = "Staff Branch Assignments"
        ordering = ["-assigned_at"]
        constraints = [
            # Only one active primary assignment per user per restaurant
            models.UniqueConstraint(
                fields=["user", "restaurant"],
                condition=models.Q(is_primary=True, is_active=True),
                name="unique_primary_branch_assignment",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "restaurant", "is_active"]),
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["user", "is_primary", "is_active"]),
        ]

    def __str__(self):
        kind = "PRIMARY" if self.is_primary else "secondary"
        return f"{self.user.email} @ {self.branch.name} [{kind}]"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Branch must belong to restaurant
        if self.branch_id and self.restaurant_id:
            try:
                if str(self.branch.restaurant_id) != str(self.restaurant_id):
                    raise ValidationError(
                        {"branch": "Branch does not belong to the specified restaurant."}
                    )
            except Exception:
                pass


# =============================================================================
# StaffTransfer
# =============================================================================

class StaffTransfer(TimestampedModel):
    """
    A formal request to move a staff member from one branch to another.

    Both branches must belong to the same restaurant.
    Historical transactions retain their original branch context.
    The user's StaffBranchAssignment is updated only on COMPLETED.

    Lifecycle:
        REQUESTED → APPROVED → COMPLETED
        REQUESTED → REJECTED
        REQUESTED / APPROVED → CANCELLED
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="staff_transfers",
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="staff_transfers",
        db_index=True,
    )
    source_branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
    )
    destination_branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="transfer_requests_made",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transfer_approvals",
    )
    reason = models.TextField(
        help_text="Business justification for the transfer.",
    )
    status = models.CharField(
        max_length=15,
        choices=TRANSFER_STATUS_CHOICES,
        default=TRANSFER_STATUS_REQUESTED,
        db_index=True,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Staff Transfer"
        verbose_name_plural = "Staff Transfers"
        ordering = ["-requested_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["source_branch", "status"]),
            models.Index(fields=["destination_branch", "status"]),
        ]

    def __str__(self):
        return (
            f"{self.user.email}: {self.source_branch.name} → "
            f"{self.destination_branch.name} [{self.status}]"
        )

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.source_branch_id and self.destination_branch_id:
            if self.source_branch_id == self.destination_branch_id:
                raise ValidationError(
                    "Source and destination branches must be different."
                )
        if self.source_branch_id and self.restaurant_id:
            try:
                if str(self.source_branch.restaurant_id) != str(self.restaurant_id):
                    raise ValidationError(
                        {"source_branch": "Source branch does not belong to the specified restaurant."}
                    )
            except Exception:
                pass
        if self.destination_branch_id and self.restaurant_id:
            try:
                if str(self.destination_branch.restaurant_id) != str(self.restaurant_id):
                    raise ValidationError(
                        {"destination_branch": "Destination branch must be in the same restaurant."}
                    )
            except Exception:
                pass


# =============================================================================
# ApprovalPolicy
# =============================================================================

class ApprovalPolicy(TimestampedModel):
    """
    Configurable threshold-based approval policy.

    Policies are resolved hierarchically (most-specific wins):
        Branch → Restaurant → Company → System default

    Examples:
        Expense > ₹10,000 → requires permission "expense.approve_manager"
        Discount > 20%    → requires permission "discount.approve"
        Refund > ₹5,000   → requires permission "billing.refund.approve"

    Exactly one of threshold_amount or threshold_percentage should be
    set (depending on policy_type), but both are nullable for flexibility.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Scope
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="approval_policies",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approval_policies",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approval_policies",
    )

    policy_type = models.CharField(
        max_length=20,
        choices=POLICY_TYPE_CHOICES,
        db_index=True,
    )
    threshold_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monetary threshold that triggers approval requirement.",
    )
    threshold_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Percentage threshold that triggers approval requirement.",
    )
    required_permission = models.CharField(
        max_length=100,
        help_text="Permission code required to approve this type of operation.",
    )
    required_role = models.ForeignKey(
        "accounts.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approval_policies",
        help_text="Optionally restrict approvals to holders of this specific role.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_approval_policies",
        null=True,
        blank=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_approval_policies",
    )

    class Meta:
        verbose_name = "Approval Policy"
        verbose_name_plural = "Approval Policies"
        ordering = ["company", "policy_type"]
        indexes = [
            models.Index(fields=["company", "policy_type", "is_active"]),
            models.Index(fields=["company", "restaurant", "policy_type", "is_active"]),
            models.Index(fields=["company", "restaurant", "branch", "policy_type", "is_active"]),
        ]

    def __str__(self):
        scope = f"company={self.company_id}"
        if self.restaurant_id:
            scope += f" rest={self.restaurant_id}"
        if self.branch_id:
            scope += f" branch={self.branch_id}"
        return f"[{scope}] {self.policy_type}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.branch_id and not self.restaurant_id:
            raise ValidationError(
                {"restaurant": "Branch-scoped policy requires a restaurant."}
            )
        if self.threshold_amount is not None and self.threshold_amount < 0:
            raise ValidationError(
                {"threshold_amount": "Threshold amount cannot be negative."}
            )
        if self.threshold_percentage is not None:
            if not (0 <= self.threshold_percentage <= 100):
                raise ValidationError(
                    {"threshold_percentage": "Threshold percentage must be between 0 and 100."}
                )


# =============================================================================
# EnterpriseAuditLog
# =============================================================================

class EnterpriseAuditLog(TimestampedModel):
    """
    Immutable append-only audit trail for all significant enterprise actions.

    Rows cannot be updated after creation — save() raises ValueError if
    an attempt is made to update an existing row.

    Scope fields are denormalized for efficient history queries without joins.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Actor
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="enterprise_audit_logs",
        null=True,
        blank=True,
    )

    # Scope (denormalized)
    company = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        related_name="enterprise_audit_logs",
        db_index=True,
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="enterprise_audit_logs",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="enterprise_audit_logs",
    )

    # Action
    action = models.CharField(
        max_length=50,
        choices=AUDIT_ACTION_CHOICES,
        db_index=True,
    )
    description = models.TextField()

    # Source reference
    source_type = models.CharField(
        max_length=50,
        blank=True,
        db_index=True,
        help_text="Model name of the object this action relates to.",
    )
    source_id = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="UUID/ID of the source object.",
    )

    # Snapshot — never store secrets
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary non-secret context about the action.",
    )

    class Meta:
        verbose_name = "Enterprise Audit Log"
        verbose_name_plural = "Enterprise Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "action", "created_at"]),
            models.Index(fields=["company", "restaurant", "action"]),
            models.Index(fields=["company", "restaurant", "branch", "action"]),
            models.Index(fields=["performed_by", "created_at"]),
            models.Index(fields=["source_type", "source_id"]),
        ]

    def __str__(self):
        return f"[{self.action}] {self.description[:80]}"

    def save(self, *args, **kwargs):
        if self.pk and EnterpriseAuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError(
                "EnterpriseAuditLog rows are immutable — do not update existing entries."
            )
        super().save(*args, **kwargs)
