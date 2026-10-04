# =============================================================================
# RestaurantFlow — Central Control Center Issue Services
# Phase 15
#
# IssueService: full CRUD + workflow for CentralIssue.
#   create_issue()
#   assign_issue()
#   start_issue()
#   resolve_issue()
#   close_issue()
#   cancel_issue()
#   update_issue()
#
# All transitions:
#   - wrapped in transaction.atomic()
#   - validate scope (assignee must have access to issue's restaurant/branch)
#   - produce CentralControlAuditLog entries
#   - broadcast WebSocket events
#   - record CentralSystemEvent entries for significant transitions
# =============================================================================

import logging

from django.db import transaction
from django.utils import timezone

from central_control.constants import (
    ISSUE_OPEN, ISSUE_ASSIGNED, ISSUE_IN_PROGRESS,
    ISSUE_RESOLVED, ISSUE_CLOSED, ISSUE_CANCELLED,
    ISSUE_SEVERITY_CRITICAL,
    AUDIT_ISSUE_CREATED, AUDIT_ISSUE_ASSIGNED, AUDIT_ISSUE_UPDATED,
    AUDIT_ISSUE_RESOLVED, AUDIT_ISSUE_CLOSED, AUDIT_ISSUE_CANCELLED,
    WS_ISSUE_CREATED, WS_ISSUE_UPDATED, WS_ISSUE_RESOLVED,
)
from central_control.exceptions import (
    IssueNotFoundError, IssueTransitionError,
    IssueImmutableError, IssueAssignmentScopeError,
    ResolutionNoteRequiredError,
)
from central_control.validators import (
    validate_issue_transition,
    validate_resolution_note_for_critical,
)

logger = logging.getLogger("central_control")


class IssueService:
    """Handles the full lifecycle of CentralIssue records."""

    @staticmethod
    @transaction.atomic
    def create_issue(
        *,
        actor,
        organization,
        restaurant=None,
        branch=None,
        category: str,
        title: str,
        description: str,
        severity: str,
        detected_from_alert=None,
        due_at=None,
    ):
        """
        Create a new CentralIssue in OPEN status.

        Args:
            actor:               The User creating the issue.
            organization:        The scoping Organization.
            restaurant:          Optional restaurant scope.
            branch:              Optional branch scope.
            category:            Issue category (from ISSUE_CATEGORY_CHOICES).
            title:               Short title.
            description:         Detailed description.
            severity:            Issue severity (from ISSUE_SEVERITY_CHOICES).
            detected_from_alert: Optional CentralAlert that triggered this issue.
            due_at:              Optional deadline datetime.

        Returns:
            The created CentralIssue.
        """
        from central_control.models import CentralIssue
        from central_control.services import (
            record_audit_entry, record_system_event, broadcast_issue_event
        )

        issue = CentralIssue.objects.create(
            organization=organization,
            restaurant=restaurant,
            branch=branch,
            category=category,
            title=title,
            description=description,
            severity=severity,
            status=ISSUE_OPEN,
            created_by=actor,
            detected_from_alert=detected_from_alert,
            due_at=due_at,
        )

        record_audit_entry(
            actor=actor,
            action=AUDIT_ISSUE_CREATED,
            entity_type="ISSUE",
            entity_id=issue.pk,
            organization=organization,
            restaurant=restaurant,
            branch=branch,
            new_status=ISSUE_OPEN,
            metadata={"category": category, "severity": severity},
        )

        broadcast_issue_event(issue, WS_ISSUE_CREATED)

        record_system_event(
            organization=organization,
            event_type="ISSUE_CREATED",
            title=f"Issue created: {title}",
            severity=severity,
            restaurant=restaurant,
            branch=branch,
            issue=issue,
            alert=detected_from_alert,
        )

        logger.info("CentralIssue %s created by %s", issue.pk, actor.email)
        return issue

    @staticmethod
    @transaction.atomic
    def assign_issue(*, actor, issue_id, organization, assignee_user):
        """
        Assign an issue to a user. Validates assignee scope.

        The assignee must have a role assignment that covers the issue's
        restaurant/branch scope.

        Transitions: OPEN → ASSIGNED, or updates assignment on ASSIGNED/IN_PROGRESS.
        """
        from central_control.models import CentralIssue
        from accounts import access as acl
        from central_control.services import (
            record_audit_entry, broadcast_issue_event
        )

        try:
            issue = CentralIssue.objects.select_for_update().get(
                pk=issue_id, organization=organization
            )
        except CentralIssue.DoesNotExist:
            raise IssueNotFoundError(f"Issue {issue_id} not found.")

        if issue.is_terminal:
            raise IssueImmutableError(
                f"Issue {issue_id} is in terminal status {issue.status} and cannot be modified."
            )

        # Validate assignee scope
        if issue.branch:
            if not acl.can_access_branch(assignee_user, issue.branch):
                raise IssueAssignmentScopeError(
                    f"User {assignee_user.email} does not have access to "
                    f"branch {issue.branch.name}."
                )
        elif issue.restaurant:
            if not acl.can_access_restaurant(assignee_user, issue.restaurant):
                raise IssueAssignmentScopeError(
                    f"User {assignee_user.email} does not have access to "
                    f"restaurant {issue.restaurant.name}."
                )
        else:
            if not acl.can_access_organization(assignee_user, issue.organization):
                raise IssueAssignmentScopeError(
                    f"User {assignee_user.email} does not have access to "
                    f"organization {issue.organization.name}."
                )

        old_status = issue.status
        new_status = ISSUE_ASSIGNED if issue.status == ISSUE_OPEN else issue.status
        validate_issue_transition(old_status, new_status) if new_status != old_status else None

        issue.assigned_to = assignee_user
        if issue.status == ISSUE_OPEN:
            issue.status = ISSUE_ASSIGNED
        issue.save(update_fields=["assigned_to", "status", "updated_at"])

        record_audit_entry(
            actor=actor,
            action=AUDIT_ISSUE_ASSIGNED,
            entity_type="ISSUE",
            entity_id=issue.pk,
            organization=organization,
            restaurant=issue.restaurant,
            branch=issue.branch,
            old_status=old_status,
            new_status=issue.status,
            metadata={"assignee": assignee_user.email},
        )

        broadcast_issue_event(issue, WS_ISSUE_UPDATED)
        logger.info(
            "Issue %s assigned to %s by %s",
            issue.pk, assignee_user.email, actor.email,
        )
        return issue

    @staticmethod
    @transaction.atomic
    def start_issue(*, actor, issue_id, organization):
        """
        Move an issue to IN_PROGRESS (ASSIGNED → IN_PROGRESS).
        """
        from central_control.models import CentralIssue
        from central_control.services import record_audit_entry, broadcast_issue_event

        try:
            issue = CentralIssue.objects.select_for_update().get(
                pk=issue_id, organization=organization
            )
        except CentralIssue.DoesNotExist:
            raise IssueNotFoundError(f"Issue {issue_id} not found.")

        validate_issue_transition(issue.status, ISSUE_IN_PROGRESS)

        old_status = issue.status
        issue.status = ISSUE_IN_PROGRESS
        issue.save(update_fields=["status", "updated_at"])

        record_audit_entry(
            actor=actor,
            action=AUDIT_ISSUE_UPDATED,
            entity_type="ISSUE",
            entity_id=issue.pk,
            organization=organization,
            old_status=old_status,
            new_status=ISSUE_IN_PROGRESS,
        )

        broadcast_issue_event(issue, WS_ISSUE_UPDATED)
        return issue

    @staticmethod
    @transaction.atomic
    def resolve_issue(*, actor, issue_id, organization, resolution_note: str):
        """
        Move an issue to RESOLVED. Critical issues require a non-empty resolution_note.
        """
        from central_control.models import CentralIssue
        from central_control.services import (
            record_audit_entry, broadcast_issue_event, record_system_event
        )

        try:
            issue = CentralIssue.objects.select_for_update().get(
                pk=issue_id, organization=organization
            )
        except CentralIssue.DoesNotExist:
            raise IssueNotFoundError(f"Issue {issue_id} not found.")

        validate_issue_transition(issue.status, ISSUE_RESOLVED)
        validate_resolution_note_for_critical(issue.severity, resolution_note)

        old_status = issue.status
        issue.status = ISSUE_RESOLVED
        issue.resolved_by = actor
        issue.resolved_at = timezone.now()
        issue.resolution_note = resolution_note or ""
        issue.save(update_fields=[
            "status", "resolved_by", "resolved_at", "resolution_note", "updated_at"
        ])

        record_audit_entry(
            actor=actor,
            action=AUDIT_ISSUE_RESOLVED,
            entity_type="ISSUE",
            entity_id=issue.pk,
            organization=organization,
            restaurant=issue.restaurant,
            branch=issue.branch,
            old_status=old_status,
            new_status=ISSUE_RESOLVED,
            metadata={"resolution_note": resolution_note},
        )

        broadcast_issue_event(issue, WS_ISSUE_RESOLVED)

        record_system_event(
            organization=organization,
            event_type="ISSUE_RESOLVED",
            title=f"Issue resolved: {issue.title}",
            severity=issue.severity,
            restaurant=issue.restaurant,
            branch=issue.branch,
            issue=issue,
        )

        logger.info("Issue %s resolved by %s", issue.pk, actor.email)
        return issue

    @staticmethod
    @transaction.atomic
    def close_issue(*, actor, issue_id, organization):
        """
        Move a RESOLVED issue to CLOSED (terminal — immutable afterwards).
        """
        from central_control.models import CentralIssue
        from central_control.services import record_audit_entry, broadcast_issue_event

        try:
            issue = CentralIssue.objects.select_for_update().get(
                pk=issue_id, organization=organization
            )
        except CentralIssue.DoesNotExist:
            raise IssueNotFoundError(f"Issue {issue_id} not found.")

        validate_issue_transition(issue.status, ISSUE_CLOSED)

        old_status = issue.status
        issue.status = ISSUE_CLOSED
        issue.closed_by = actor
        issue.closed_at = timezone.now()
        issue.save(update_fields=["status", "closed_by", "closed_at", "updated_at"])

        record_audit_entry(
            actor=actor,
            action=AUDIT_ISSUE_CLOSED,
            entity_type="ISSUE",
            entity_id=issue.pk,
            organization=organization,
            old_status=old_status,
            new_status=ISSUE_CLOSED,
        )

        broadcast_issue_event(issue, WS_ISSUE_UPDATED)
        logger.info("Issue %s closed by %s", issue.pk, actor.email)
        return issue

    @staticmethod
    @transaction.atomic
    def cancel_issue(*, actor, issue_id, organization, reason: str = ""):
        """
        Cancel an issue (OPEN/ASSIGNED/IN_PROGRESS → CANCELLED).
        """
        from central_control.models import CentralIssue
        from central_control.services import record_audit_entry, broadcast_issue_event

        try:
            issue = CentralIssue.objects.select_for_update().get(
                pk=issue_id, organization=organization
            )
        except CentralIssue.DoesNotExist:
            raise IssueNotFoundError(f"Issue {issue_id} not found.")

        validate_issue_transition(issue.status, ISSUE_CANCELLED)

        old_status = issue.status
        issue.status = ISSUE_CANCELLED
        issue.cancelled_by = actor
        issue.cancelled_at = timezone.now()
        issue.save(update_fields=["status", "cancelled_by", "cancelled_at", "updated_at"])

        record_audit_entry(
            actor=actor,
            action=AUDIT_ISSUE_CANCELLED,
            entity_type="ISSUE",
            entity_id=issue.pk,
            organization=organization,
            old_status=old_status,
            new_status=ISSUE_CANCELLED,
            metadata={"reason": reason},
        )

        broadcast_issue_event(issue, WS_ISSUE_UPDATED)
        logger.info("Issue %s cancelled by %s", issue.pk, actor.email)
        return issue

    @staticmethod
    @transaction.atomic
    def update_issue(*, actor, issue_id, organization, **fields):
        """
        Update mutable fields on a non-terminal issue.
        Allowed fields: title, description, severity, due_at.
        """
        from central_control.models import CentralIssue
        from central_control.services import record_audit_entry, broadcast_issue_event

        MUTABLE_FIELDS = {"title", "description", "severity", "due_at"}

        try:
            issue = CentralIssue.objects.select_for_update().get(
                pk=issue_id, organization=organization
            )
        except CentralIssue.DoesNotExist:
            raise IssueNotFoundError(f"Issue {issue_id} not found.")

        if issue.is_terminal:
            raise IssueImmutableError(
                f"Issue {issue_id} is in terminal status '{issue.status}' "
                "and cannot be modified."
            )

        updated = []
        for field, value in fields.items():
            if field in MUTABLE_FIELDS:
                setattr(issue, field, value)
                updated.append(field)

        if updated:
            issue.save(update_fields=updated + ["updated_at"])
            record_audit_entry(
                actor=actor,
                action=AUDIT_ISSUE_UPDATED,
                entity_type="ISSUE",
                entity_id=issue.pk,
                organization=organization,
                metadata={"updated_fields": updated},
            )
            broadcast_issue_event(issue, WS_ISSUE_UPDATED)

        return issue
