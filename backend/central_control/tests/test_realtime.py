# =============================================================================
# RestaurantFlow — Central Control Center Tests: WebSocket Real-Time
# Phase 15
# =============================================================================

from django.test import TestCase
from django.contrib.auth import get_user_model
from unittest.mock import patch, AsyncMock, MagicMock

from organizations.models import Organization, Restaurant, Branch
from accounts.models import Role, Permission, UserRoleAssignment

User = get_user_model()


def _org(n):
    return Organization.objects.create(name=n, slug=n.replace(" ", "-").lower())


def _cc_user(org, email, with_perm=True):
    role, _ = Role.objects.get_or_create(
        code=Role.CODE_COMPANY_HEAD,
        defaults={"name": "Company Head", "scope": Role.SCOPE_ORGANIZATION},
    )
    if with_perm:
        perm, _ = Permission.objects.get_or_create(
            code="central_control.dashboard.view",
            defaults={"name": "CC View", "module": "central_control", "action": "dashboard.view"},
        )
        role.permissions.add(perm)
    user = User.objects.create_user(email=email, password="pass", first_name="RT", last_name="U")
    UserRoleAssignment.objects.create(user=user, role=role, organization=org, is_active=True)
    return user


class WebSocketGroupNameTests(TestCase):
    """Verify group names are derived server-side from organization ID."""

    def test_group_name_format(self):
        from central_control.constants import WS_GROUP_COMPANY
        org_id = "12345678-1234-1234-1234-123456789abc"
        group_name = WS_GROUP_COMPANY.format(company_id=org_id)
        self.assertEqual(group_name, f"company_{org_id}_central_control")

    def test_different_orgs_have_different_group_names(self):
        from central_control.constants import WS_GROUP_COMPANY
        org_a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
        org_b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
        self.assertNotEqual(
            WS_GROUP_COMPANY.format(company_id=org_a),
            WS_GROUP_COMPANY.format(company_id=org_b),
        )


class BroadcastTests(TestCase):
    """Unit tests for broadcast helper functions."""

    def test_broadcast_alert_event_safe_on_channel_layer_failure(self):
        """broadcast_alert_event must not raise if channel layer is unavailable."""
        from central_control.services import broadcast_alert_event
        from central_control.constants import WS_ALERT_CREATED

        org = _org("Broadcast Org A")
        rest = Restaurant.objects.create(organization=org, name="BroadRest", code="BR1")
        branch = Branch.objects.create(restaurant=rest, name="BroadBranch", code="BB1")

        from central_control.models import CentralAlert
        from central_control.constants import (
            ALERT_OPEN, ALERT_TYPE_KITCHEN_DELAY, SEVERITY_HIGH,
            SOURCE_TYPE_KITCHEN_ORDER,
        )
        from central_control.alert_rules import _build_fingerprint
        from django.utils import timezone

        alert = CentralAlert.objects.create(
            organization=org, restaurant=rest, branch=branch,
            alert_type=ALERT_TYPE_KITCHEN_DELAY, severity=SEVERITY_HIGH,
            title="Broadcast test", message=".",
            source_type=SOURCE_TYPE_KITCHEN_ORDER, source_id="bc-ko",
            fingerprint=_build_fingerprint(
                ALERT_TYPE_KITCHEN_DELAY, SOURCE_TYPE_KITCHEN_ORDER, "bc-ko", org.pk,
            ),
            status=ALERT_OPEN, detected_at=timezone.now(),
        )

        # Should not raise even without real Redis
        with patch("central_control.services._get_channel_layer", return_value=None):
            try:
                broadcast_alert_event(alert, WS_ALERT_CREATED)
            except Exception as e:
                self.fail(f"broadcast_alert_event raised unexpectedly: {e}")

    def test_broadcast_issue_event_safe_on_failure(self):
        """broadcast_issue_event must not raise if channel layer is unavailable."""
        from central_control.services import broadcast_issue_event
        from central_control.constants import WS_ISSUE_CREATED
        from central_control.issue_services import IssueService
        from central_control.constants import ISSUE_CATEGORY_KITCHEN, ISSUE_SEVERITY_MEDIUM

        org = _org("Broadcast Org B")
        actor = _cc_user(org, "bc_issue@test.com")

        rest = Restaurant.objects.create(organization=org, name="IssueRest", code="IR2")
        branch = Branch.objects.create(restaurant=rest, name="IssueBranch", code="IB2")

        issue = IssueService.create_issue(
            actor=actor, organization=org, restaurant=rest, branch=branch,
            category=ISSUE_CATEGORY_KITCHEN, title="BC issue", description=".",
            severity=ISSUE_SEVERITY_MEDIUM,
        )

        with patch("central_control.services._get_channel_layer", return_value=None):
            try:
                broadcast_issue_event(issue, WS_ISSUE_CREATED)
            except Exception as e:
                self.fail(f"broadcast_issue_event raised unexpectedly: {e}")
