# =============================================================================
# RestaurantFlow — Central Control Center Tests: Issues
# Phase 15
# =============================================================================

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from organizations.models import Organization, Restaurant, Branch
from accounts.models import Role, UserRoleAssignment
from central_control.issue_services import IssueService
from central_control.constants import (
    ISSUE_OPEN, ISSUE_ASSIGNED, ISSUE_IN_PROGRESS, ISSUE_RESOLVED,
    ISSUE_CLOSED, ISSUE_CANCELLED,
    ISSUE_SEVERITY_CRITICAL, ISSUE_SEVERITY_MEDIUM,
    ISSUE_CATEGORY_KITCHEN,
)
from central_control.exceptions import (
    IssueTransitionError, IssueImmutableError,
    ResolutionNoteRequiredError, IssueAssignmentScopeError,
)

User = get_user_model()


def _org(name="Issue Org"):
    return Organization.objects.create(name=name, slug=name.replace(' ', '-').lower())


def _rest(org):
    return Restaurant.objects.create(organization=org, name="IssueRest", code="IR1")


def _branch(restaurant):
    return Branch.objects.create(restaurant=restaurant, name="IssueBranch", code="IB1")


def _user(email="issue_actor@test.com"):
    return User.objects.create_user(email=email, password="pass", first_name="I", last_name="A")


class IssueWorkflowTests(TestCase):

    def setUp(self):
        self.org = _org()
        self.restaurant = _rest(self.org)
        self.branch = _branch(self.restaurant)
        self.actor = _user()

    def _create_issue(self, severity=ISSUE_SEVERITY_MEDIUM):
        return IssueService.create_issue(
            actor=self.actor,
            organization=self.org,
            restaurant=self.restaurant,
            branch=self.branch,
            category=ISSUE_CATEGORY_KITCHEN,
            title="Test Issue",
            description="Description",
            severity=severity,
        )

    def test_create_issue(self):
        issue = self._create_issue()
        self.assertEqual(issue.status, ISSUE_OPEN)
        self.assertEqual(issue.created_by, self.actor)
        self.assertEqual(issue.organization, self.org)

    def test_start_issue(self):
        issue = self._create_issue()
        # OPEN → IN_PROGRESS is valid
        started = IssueService.start_issue(
            actor=self.actor, issue_id=issue.pk, organization=self.org
        )
        self.assertEqual(started.status, ISSUE_IN_PROGRESS)

    def test_full_workflow(self):
        issue = self._create_issue()
        started = IssueService.start_issue(actor=self.actor, issue_id=issue.pk, organization=self.org)
        resolved = IssueService.resolve_issue(
            actor=self.actor, issue_id=issue.pk, organization=self.org,
            resolution_note="Resolved the kitchen delay."
        )
        self.assertEqual(resolved.status, ISSUE_RESOLVED)
        closed = IssueService.close_issue(actor=self.actor, issue_id=issue.pk, organization=self.org)
        self.assertEqual(closed.status, ISSUE_CLOSED)

    def test_closed_issue_is_immutable(self):
        issue = self._create_issue()
        IssueService.start_issue(actor=self.actor, issue_id=issue.pk, organization=self.org)
        IssueService.resolve_issue(actor=self.actor, issue_id=issue.pk, organization=self.org, resolution_note="done")
        IssueService.close_issue(actor=self.actor, issue_id=issue.pk, organization=self.org)
        with self.assertRaises(IssueImmutableError):
            IssueService.update_issue(
                actor=self.actor, issue_id=issue.pk, organization=self.org,
                title="New title"
            )

    def test_cancel_open_issue(self):
        issue = self._create_issue()
        cancelled = IssueService.cancel_issue(
            actor=self.actor, issue_id=issue.pk, organization=self.org,
            reason="Not needed."
        )
        self.assertEqual(cancelled.status, ISSUE_CANCELLED)

    def test_critical_issue_requires_resolution_note(self):
        issue = self._create_issue(severity=ISSUE_SEVERITY_CRITICAL)
        IssueService.start_issue(actor=self.actor, issue_id=issue.pk, organization=self.org)
        with self.assertRaises(ResolutionNoteRequiredError):
            IssueService.resolve_issue(
                actor=self.actor, issue_id=issue.pk, organization=self.org,
                resolution_note=""
            )

    def test_critical_issue_resolves_with_note(self):
        issue = self._create_issue(severity=ISSUE_SEVERITY_CRITICAL)
        IssueService.start_issue(actor=self.actor, issue_id=issue.pk, organization=self.org)
        resolved = IssueService.resolve_issue(
            actor=self.actor, issue_id=issue.pk, organization=self.org,
            resolution_note="Critical issue fully investigated and resolved."
        )
        self.assertEqual(resolved.status, ISSUE_RESOLVED)


class IssueAssignmentScopeTests(TestCase):

    def setUp(self):
        self.org = _org("Assign Org")
        self.restaurant = _rest(self.org)
        self.branch = _branch(self.restaurant)
        self.actor = _user("assign_actor@test.com")

    def test_assign_to_user_with_correct_scope(self):
        """Assigning to a user who can access the restaurant should succeed."""
        issue = IssueService.create_issue(
            actor=self.actor, organization=self.org,
            restaurant=self.restaurant, branch=self.branch,
            category=ISSUE_CATEGORY_KITCHEN, title="T", description="D",
            severity=ISSUE_SEVERITY_MEDIUM,
        )
        # Create assignee with restaurant access
        assignee = User.objects.create_user(email="assignee@test.com", password="pass", first_name="A", last_name="A")
        role, _ = Role.objects.get_or_create(
            code=Role.CODE_RESTAURANT_MANAGER,
            defaults={"name": "Restaurant Manager", "scope": Role.SCOPE_RESTAURANT},
        )
        UserRoleAssignment.objects.create(
            user=assignee, role=role, organization=self.org,
            restaurant=self.restaurant, is_active=True,
        )
        updated = IssueService.assign_issue(
            actor=self.actor, issue_id=issue.pk,
            organization=self.org, assignee_user=assignee
        )
        self.assertEqual(updated.assigned_to, assignee)

    def test_assign_to_user_without_scope_raises(self):
        """Assigning to a user without restaurant access should raise IssueAssignmentScopeError."""
        issue = IssueService.create_issue(
            actor=self.actor, organization=self.org,
            restaurant=self.restaurant, branch=self.branch,
            category=ISSUE_CATEGORY_KITCHEN, title="T", description="D",
            severity=ISSUE_SEVERITY_MEDIUM,
        )
        outsider = User.objects.create_user(email="outsider@test.com", password="pass", first_name="O", last_name="O")
        with self.assertRaises(IssueAssignmentScopeError):
            IssueService.assign_issue(
                actor=self.actor, issue_id=issue.pk,
                organization=self.org, assignee_user=outsider
            )
