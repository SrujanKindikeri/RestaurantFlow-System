# =============================================================================
# RestaurantFlow — Central Control Center Tests: Escalation Engine
# Phase 15
# =============================================================================

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from organizations.models import Organization, Restaurant, Branch
from accounts.models import Role, UserRoleAssignment
from central_control.models import CentralAlert, EscalationRule, CentralIssue, CentralControlSettings
from central_control.constants import (
    ALERT_OPEN, ALERT_TYPE_KITCHEN_DELAY, SEVERITY_HIGH,
    SOURCE_TYPE_KITCHEN_ORDER, ISSUE_ACTIVE_STATUSES,
)
from central_control.alert_rules import EscalationEngine, _build_fingerprint

User = get_user_model()


def _org(n="Esc Org"):
    return Organization.objects.create(name=n, slug=n.replace(" ", "-").lower())


def _rest(org):
    return Restaurant.objects.create(organization=org, name="EscRest", code="ER1")


def _superuser(email="esc_super@test.com"):
    return User.objects.create_superuser(email=email, password="pass")


class EscalationEngineTests(TestCase):

    def setUp(self):
        self.org = _org()
        self.restaurant = _rest(self.org)
        self.branch = Branch.objects.create(restaurant=self.restaurant, name="EscBranch", code="EB1")
        self.superuser = _superuser()

        # Create CentralControlSettings with escalation enabled
        CentralControlSettings.objects.create(
            organization=self.org,
            alert_escalation_enabled=True,
            issue_auto_creation_enabled=True,
        )

    def _old_alert(self, minutes_ago=60):
        """Create an old OPEN alert that should trigger escalation."""
        return CentralAlert.objects.create(
            organization=self.org,
            restaurant=self.restaurant,
            branch=self.branch,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            title="Old kitchen delay",
            message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="esc-ko-001",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "esc-ko-001", self.org.pk, self.restaurant.pk,
            ),
            status=ALERT_OPEN,
            detected_at=timezone.now() - timedelta(minutes=minutes_ago),
        )

    def test_escalation_creates_issue_for_old_alert(self):
        """An alert older than threshold_minutes should generate a CentralIssue."""
        rule = EscalationRule.objects.create(
            organization=self.org,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            threshold_minutes=30,
            auto_create_issue=True,
            is_active=True,
        )
        alert = self._old_alert(minutes_ago=60)

        engine = EscalationEngine(self.org)
        engine.run()

        issues = CentralIssue.objects.filter(detected_from_alert=alert)
        self.assertEqual(issues.count(), 1)
        issue = issues.first()
        self.assertIn(issue.status, list(ISSUE_ACTIVE_STATUSES))

    def test_escalation_does_not_duplicate_issue(self):
        """Running escalation twice must not create two issues for the same alert."""
        EscalationRule.objects.create(
            organization=self.org,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            threshold_minutes=30,
            auto_create_issue=True,
            is_active=True,
        )
        alert = self._old_alert(minutes_ago=90)

        engine = EscalationEngine(self.org)
        engine.run()
        engine.run()  # second run should not duplicate

        issues = CentralIssue.objects.filter(detected_from_alert=alert)
        self.assertEqual(issues.count(), 1)

    def test_recent_alert_does_not_escalate(self):
        """An alert younger than threshold_minutes must NOT trigger escalation."""
        EscalationRule.objects.create(
            organization=self.org,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            threshold_minutes=30,
            auto_create_issue=True,
            is_active=True,
        )
        alert = self._old_alert(minutes_ago=10)  # Only 10 minutes old

        engine = EscalationEngine(self.org)
        engine.run()

        issues = CentralIssue.objects.filter(detected_from_alert=alert)
        self.assertEqual(issues.count(), 0)

    def test_disabled_rule_does_not_escalate(self):
        """An inactive escalation rule must not create issues."""
        EscalationRule.objects.create(
            organization=self.org,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            threshold_minutes=30,
            auto_create_issue=True,
            is_active=False,  # DISABLED
        )
        alert = self._old_alert(minutes_ago=90)

        engine = EscalationEngine(self.org)
        engine.run()

        issues = CentralIssue.objects.filter(detected_from_alert=alert)
        self.assertEqual(issues.count(), 0)

    def test_escalation_disabled_in_settings(self):
        """If CentralControlSettings.alert_escalation_enabled=False, engine does nothing."""
        settings_obj = self.org.central_control_settings
        settings_obj.alert_escalation_enabled = False
        settings_obj.save()

        EscalationRule.objects.create(
            organization=self.org,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            threshold_minutes=30,
            auto_create_issue=True,
            is_active=True,
        )
        alert = self._old_alert(minutes_ago=90)

        engine = EscalationEngine(self.org)
        engine.run()

        issues = CentralIssue.objects.filter(detected_from_alert=alert)
        self.assertEqual(issues.count(), 0)
