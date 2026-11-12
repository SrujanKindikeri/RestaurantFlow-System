# =============================================================================
# RestaurantFlow — Central Control Center Tests: Scope Isolation
# Phase 15
# =============================================================================

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from organizations.models import Organization, Restaurant, Branch
from accounts.models import Role, Permission, UserRoleAssignment
from central_control.selectors import (
    get_alerts_for_user, get_issues_for_user, get_restaurants_for_user,
    get_branches_for_user,
)

User = get_user_model()


def _org(n):
    return Organization.objects.create(name=n, slug=n.replace(" ", "-").lower())


def _rest(org, code="R1"):
    return Restaurant.objects.create(organization=org, name=f"Rest {code}", code=code)


def _branch(restaurant, code="B1"):
    return Branch.objects.create(restaurant=restaurant, name=f"Branch {code}", code=code)


def _cc_user(org, email):
    role, _ = Role.objects.get_or_create(
        code=Role.CODE_COMPANY_HEAD,
        defaults={"name": "Company Head", "scope": Role.SCOPE_ORGANIZATION},
    )
    user = User.objects.create_user(email=email, password="pass", first_name="S", last_name="U")
    UserRoleAssignment.objects.create(user=user, role=role, organization=org, is_active=True)
    return user


class SelectorScopeTests(TestCase):

    def setUp(self):
        self.org_a = _org("Scope Org A")
        self.org_b = _org("Scope Org B")
        self.rest_a = _rest(self.org_a, "A1")
        self.rest_b = _rest(self.org_b, "B1")
        self.branch_a = _branch(self.rest_a, "BA1")
        self.branch_b = _branch(self.rest_b, "BB1")
        self.user_a = _cc_user(self.org_a, "scope_a@test.com")
        self.user_b = _cc_user(self.org_b, "scope_b@test.com")

    def test_get_restaurants_scope(self):
        """user_a should only see org_a's restaurant."""
        qs = get_restaurants_for_user(self.user_a)
        pks = list(qs.values_list("pk", flat=True))
        self.assertIn(self.rest_a.pk, pks)
        self.assertNotIn(self.rest_b.pk, pks)

    def test_get_branches_scope(self):
        """user_b should only see org_b's branch."""
        qs = get_branches_for_user(self.user_b)
        pks = list(qs.values_list("pk", flat=True))
        self.assertIn(self.branch_b.pk, pks)
        self.assertNotIn(self.branch_a.pk, pks)

    def test_get_alerts_for_user_scope(self):
        """Alerts from org_a are not visible to user_b."""
        from django.utils import timezone
        from central_control.models import CentralAlert
        from central_control.constants import (
            ALERT_OPEN, ALERT_TYPE_KITCHEN_DELAY, SEVERITY_HIGH,
            SOURCE_TYPE_KITCHEN_ORDER,
        )
        from central_control.alert_rules import _build_fingerprint

        alert_a = CentralAlert.objects.create(
            organization=self.org_a,
            restaurant=self.rest_a,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            title="Org A alert",
            message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="scope-ko-001",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "scope-ko-001", self.org_a.pk,
            ),
            status=ALERT_OPEN,
            detected_at=timezone.now(),
        )

        qs_for_b = get_alerts_for_user(self.user_b)
        self.assertNotIn(alert_a.pk, list(qs_for_b.values_list("pk", flat=True)))

        qs_for_a = get_alerts_for_user(self.user_a)
        self.assertIn(alert_a.pk, list(qs_for_a.values_list("pk", flat=True)))

    def test_get_issues_for_user_scope(self):
        """Issues from org_b are not visible to user_a."""
        from central_control.issue_services import IssueService
        from central_control.constants import ISSUE_CATEGORY_KITCHEN, ISSUE_SEVERITY_MEDIUM

        issue_b = IssueService.create_issue(
            actor=self.user_b, organization=self.org_b,
            restaurant=self.rest_b, branch=self.branch_b,
            category=ISSUE_CATEGORY_KITCHEN, title="Org B issue",
            description=".", severity=ISSUE_SEVERITY_MEDIUM,
        )

        qs_for_a = get_issues_for_user(self.user_a)
        self.assertNotIn(issue_b.pk, list(qs_for_a.values_list("pk", flat=True)))

        qs_for_b = get_issues_for_user(self.user_b)
        self.assertIn(issue_b.pk, list(qs_for_b.values_list("pk", flat=True)))
