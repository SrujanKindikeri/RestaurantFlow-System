# =============================================================================
# RestaurantFlow — Central Control Center Tests: Alerts
# Phase 15
# =============================================================================

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from organizations.models import Organization, Restaurant, Branch
from accounts.models import Role, Permission, UserRoleAssignment
from central_control.models import CentralAlert
from central_control.constants import (
    ALERT_OPEN, ALERT_ACKNOWLEDGED, ALERT_RESOLVED, ALERT_DISMISSED,
    ALERT_TYPE_KITCHEN_DELAY, SEVERITY_HIGH, SEVERITY_CRITICAL,
    SOURCE_TYPE_KITCHEN_ORDER,
)
from central_control.services import AlertService
from central_control.alert_rules import _build_fingerprint, _upsert_alert

User = get_user_model()


def _make_org(name="Test Corp"):
    return Organization.objects.create(name=name, slug=f"alert-test-{name.replace(' ','-').lower()}")


def _make_restaurant(org):
    return Restaurant.objects.create(organization=org, name="R1", code="R1")


def _make_branch(restaurant):
    return Branch.objects.create(restaurant=restaurant, name="B1", code="B1")


def _make_user(email="actor@test.com"):
    return User.objects.create_user(email=email, password="pass", first_name="A", last_name="B")


class FingerprintTests(TestCase):

    def test_same_inputs_produce_same_fingerprint(self):
        fp1 = _build_fingerprint("KITCHEN_DELAY", "KITCHEN_ORDER", "abc", "org1", "rest1", "branch1")
        fp2 = _build_fingerprint("KITCHEN_DELAY", "KITCHEN_ORDER", "abc", "org1", "rest1", "branch1")
        self.assertEqual(fp1, fp2)

    def test_different_inputs_produce_different_fingerprint(self):
        fp1 = _build_fingerprint("KITCHEN_DELAY", "KITCHEN_ORDER", "abc", "org1")
        fp2 = _build_fingerprint("KITCHEN_BACKLOG", "KITCHEN_ORDER", "abc", "org1")
        self.assertNotEqual(fp1, fp2)

    def test_fingerprint_max_length(self):
        fp = _build_fingerprint("KITCHEN_DELAY", "KITCHEN_ORDER", "abc", "org1")
        self.assertLessEqual(len(fp), 64)


class AlertDeduplicationTests(TestCase):

    def setUp(self):
        self.org = _make_org()
        self.restaurant = _make_restaurant(self.org)
        self.branch = _make_branch(self.restaurant)

    def test_duplicate_detection_increments_count(self):
        """Detecting the same condition twice should update, not create a second alert."""
        now = timezone.now()
        alert1, created1 = _upsert_alert(
            organization=self.org,
            restaurant=self.restaurant,
            branch=self.branch,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            title="Kitchen delay",
            message="Order is delayed.",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-001",
            now=now,
        )
        self.assertTrue(created1)
        self.assertEqual(alert1.detection_count, 1)

        alert2, created2 = _upsert_alert(
            organization=self.org,
            restaurant=self.restaurant,
            branch=self.branch,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            title="Kitchen delay",
            message="Still delayed.",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-001",
            now=now,
        )
        self.assertFalse(created2)
        self.assertEqual(alert2.pk, alert1.pk)
        alert2.refresh_from_db()
        self.assertEqual(alert2.detection_count, 2)

    def test_two_different_sources_create_two_alerts(self):
        now = timezone.now()
        alert1, created1 = _upsert_alert(
            organization=self.org, restaurant=self.restaurant, branch=self.branch,
            alert_type=ALERT_TYPE_KITCHEN_DELAY, severity=SEVERITY_HIGH,
            title="Delay A", message=".", source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-001", now=now,
        )
        alert2, created2 = _upsert_alert(
            organization=self.org, restaurant=self.restaurant, branch=self.branch,
            alert_type=ALERT_TYPE_KITCHEN_DELAY, severity=SEVERITY_HIGH,
            title="Delay B", message=".", source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-002", now=now,
        )
        self.assertTrue(created1)
        self.assertTrue(created2)
        self.assertNotEqual(alert1.pk, alert2.pk)


class AlertLifecycleTests(TestCase):

    def setUp(self):
        self.org = _make_org()
        self.restaurant = _make_restaurant(self.org)
        self.branch = _make_branch(self.restaurant)
        self.actor = _make_user()

    def _create_alert(self, severity=SEVERITY_HIGH):
        return CentralAlert.objects.create(
            organization=self.org,
            restaurant=self.restaurant,
            branch=self.branch,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=severity,
            title="Test alert",
            message="Test message",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-test",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "ko-test", self.org.pk, self.restaurant.pk, self.branch.pk,
            ),
            status=ALERT_OPEN,
            detected_at=timezone.now(),
        )

    def test_acknowledge_alert(self):
        alert = self._create_alert()
        updated = AlertService.acknowledge_alert(
            actor=self.actor, alert_id=alert.pk, organization=self.org
        )
        self.assertEqual(updated.status, ALERT_ACKNOWLEDGED)
        self.assertIsNotNone(updated.acknowledged_at)
        self.assertEqual(updated.acknowledged_by, self.actor)

    def test_resolve_alert(self):
        alert = self._create_alert()
        updated = AlertService.resolve_alert(
            actor=self.actor, alert_id=alert.pk, organization=self.org,
            resolution_note="Fixed the kitchen issue.",
        )
        self.assertEqual(updated.status, ALERT_RESOLVED)
        self.assertIsNotNone(updated.resolved_at)

    def test_dismiss_alert(self):
        alert = self._create_alert()
        updated = AlertService.dismiss_alert(
            actor=self.actor, alert_id=alert.pk, organization=self.org,
        )
        self.assertEqual(updated.status, ALERT_DISMISSED)

    def test_invalid_transition_raises(self):
        from central_control.exceptions import AlertTransitionError
        alert = self._create_alert()
        # OPEN → RESOLVED is valid, but RESOLVED → ACKNOWLEDGED is not
        AlertService.resolve_alert(
            actor=self.actor, alert_id=alert.pk, organization=self.org,
            resolution_note="done",
        )
        with self.assertRaises(AlertTransitionError):
            AlertService.acknowledge_alert(
                actor=self.actor, alert_id=alert.pk, organization=self.org,
            )

    def test_critical_alert_requires_resolution_note(self):
        from central_control.exceptions import ResolutionNoteRequiredError
        alert = self._create_alert(severity=SEVERITY_CRITICAL)
        with self.assertRaises(ResolutionNoteRequiredError):
            AlertService.resolve_alert(
                actor=self.actor, alert_id=alert.pk, organization=self.org,
                resolution_note="",
            )


class AlertScopeTests(TestCase):

    def test_alert_not_accessible_from_different_org(self):
        org_a = _make_org("Org A Scope")
        org_b = _make_org("Org B Scope")
        rest_a = _make_restaurant(org_a)
        branch_a = _make_branch(rest_a)
        actor = _make_user("scope_actor@test.com")

        alert = CentralAlert.objects.create(
            organization=org_a,
            restaurant=rest_a,
            branch=branch_a,
            alert_type=ALERT_TYPE_KITCHEN_DELAY,
            severity=SEVERITY_HIGH,
            title="Private alert",
            message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER,
            source_id="ko-priv",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "ko-priv", org_a.pk,
            ),
            status=ALERT_OPEN,
            detected_at=timezone.now(),
        )

        # Alert belongs to org_a — accessing from org_b context should fail
        from central_control.exceptions import AlertNotFoundError
        with self.assertRaises(AlertNotFoundError):
            AlertService.acknowledge_alert(
                actor=actor, alert_id=alert.pk, organization=org_b
            )


class AlertExpireTests(TestCase):

    def test_expire_stale_open_alerts(self):
        from datetime import timedelta
        org = _make_org("Expire Org")
        rest = _make_restaurant(org)
        branch = _make_branch(rest)
        now = timezone.now()

        alert = CentralAlert.objects.create(
            organization=org, restaurant=rest, branch=branch,
            alert_type=ALERT_TYPE_KITCHEN_DELAY, severity=SEVERITY_HIGH,
            title="Expiring", message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER, source_id="ko-exp",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER,
                "ko-exp", org.pk,
            ),
            status=ALERT_OPEN,
            detected_at=now,
            expires_at=now - timedelta(minutes=1),  # already expired
        )
        count = AlertService.expire_stale_alerts()
        self.assertGreaterEqual(count, 1)
        alert.refresh_from_db()
        self.assertEqual(alert.status, "EXPIRED")
