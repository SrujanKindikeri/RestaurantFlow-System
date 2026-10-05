# =============================================================================
# RestaurantFlow — Campaign Tests
# Phase 18
# =============================================================================

from decimal import Decimal
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from marketing.tests.base import MarketingTestBase
from marketing.campaign_services import CampaignService, CampaignApprovalService
from marketing.models import MarketingCampaign, CampaignApproval
from marketing.constants import (
    CAMPAIGN_DRAFT, CAMPAIGN_PENDING_APPROVAL, CAMPAIGN_APPROVED,
    CAMPAIGN_SCHEDULED, CAMPAIGN_RUNNING, CAMPAIGN_PAUSED,
    CAMPAIGN_COMPLETED, CAMPAIGN_CANCELLED,
    CAMPAIGN_PROMOTION,
)
from marketing.exceptions import (
    MarketingPermissionDenied, CampaignInvalidTransition, CampaignAlreadyExists,
)


class CampaignCreateTests(MarketingTestBase):
    """Test campaign creation."""

    def test_create_campaign_success(self):
        campaign = CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={
                "name": "Summer Sale",
                "code": "SUMMER24",
                "campaign_type": CAMPAIGN_PROMOTION,
                "description": "Summer promotional campaign",
            },
            actor=self.marketer,
        )
        self.assertIsNotNone(campaign.pk)
        self.assertEqual(campaign.status, CAMPAIGN_DRAFT)
        self.assertEqual(campaign.code, "SUMMER24")
        self.assertEqual(campaign.company, self.org)
        self.assertEqual(campaign.restaurant, self.restaurant)

    def test_create_campaign_normalizes_code(self):
        campaign = CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": "Test", "code": "  lowercase  ", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )
        self.assertEqual(campaign.code, "LOWERCASE")

    def test_create_campaign_duplicate_code_raises(self):
        CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": "Campaign 1", "code": "DUP01", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )
        with self.assertRaises(CampaignAlreadyExists):
            CampaignService.create_campaign(
                company=self.org,
                restaurant=self.restaurant,
                data={"name": "Campaign 2", "code": "DUP01", "campaign_type": CAMPAIGN_PROMOTION},
                actor=self.marketer,
            )

    def test_create_campaign_without_permission_raises(self):
        with self.assertRaises(MarketingPermissionDenied):
            CampaignService.create_campaign(
                company=self.org,
                restaurant=self.restaurant,
                data={"name": "Campaign", "code": "NOPERM", "campaign_type": CAMPAIGN_PROMOTION},
                actor=self.cashier,
            )

    def test_create_campaign_invalid_date_raises(self):
        now = timezone.now()
        with self.assertRaises(ValidationError):
            CampaignService.create_campaign(
                company=self.org,
                restaurant=self.restaurant,
                data={
                    "name": "Campaign",
                    "code": "BADDATES",
                    "campaign_type": CAMPAIGN_PROMOTION,
                    "start_at": now + timezone.timedelta(days=5),
                    "end_at": now + timezone.timedelta(days=1),
                },
                actor=self.marketer,
            )


class CampaignUpdateTests(MarketingTestBase):

    def setUp(self):
        self.campaign = CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": "Original", "code": "UPD01", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )

    def test_update_campaign_success(self):
        updated = CampaignService.update_campaign(
            self.campaign,
            data={"name": "Updated Name", "description": "New description"},
            actor=self.marketer,
        )
        self.assertEqual(updated.name, "Updated Name")
        self.assertEqual(updated.description, "New description")

    def test_update_running_campaign_raises(self):
        # Manually set to RUNNING
        MarketingCampaign.objects.filter(pk=self.campaign.pk).update(status=CAMPAIGN_RUNNING)
        self.campaign.refresh_from_db()
        with self.assertRaises(ValidationError):
            CampaignService.update_campaign(
                self.campaign,
                data={"name": "Bad update"},
                actor=self.marketer,
            )


class CampaignStatusTransitionTests(MarketingTestBase):

    def setUp(self):
        self.campaign = CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": "Transition", "code": "TRANS01", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )

    def test_draft_to_pending_approval(self):
        approval = CampaignApprovalService.submit_for_approval(self.campaign, self.marketer)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CAMPAIGN_PENDING_APPROVAL)
        self.assertIsNotNone(approval.pk)

    def test_invalid_transition_raises(self):
        """DRAFT → RUNNING is not a valid transition."""
        with self.assertRaises(CampaignInvalidTransition):
            CampaignService.transition_status(
                self.campaign,
                new_status=CAMPAIGN_RUNNING,
                actor=self.marketer,
            )

    def test_cancel_from_draft(self):
        campaign = CampaignService.transition_status(
            self.campaign,
            new_status=CAMPAIGN_CANCELLED,
            actor=self.marketer,
            reason="Not needed",
        )
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CAMPAIGN_CANCELLED)

    def test_terminal_state_no_transition(self):
        """Cancelled campaign cannot be transitioned further."""
        MarketingCampaign.objects.filter(pk=self.campaign.pk).update(status=CAMPAIGN_CANCELLED)
        self.campaign.refresh_from_db()
        with self.assertRaises(CampaignInvalidTransition):
            CampaignService.transition_status(
                self.campaign,
                new_status=CAMPAIGN_DRAFT,
                actor=self.marketer,
            )

    def test_pause_and_resume(self):
        """RUNNING → PAUSED → SCHEDULED"""
        MarketingCampaign.objects.filter(pk=self.campaign.pk).update(status=CAMPAIGN_RUNNING)
        self.campaign.refresh_from_db()

        CampaignService.transition_status(self.campaign, new_status=CAMPAIGN_PAUSED, actor=self.marketer)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CAMPAIGN_PAUSED)

        CampaignService.transition_status(self.campaign, new_status=CAMPAIGN_SCHEDULED, actor=self.marketer)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CAMPAIGN_SCHEDULED)


class CampaignApprovalTests(MarketingTestBase):

    def setUp(self):
        self.campaign = CampaignService.create_campaign(
            company=self.org,
            restaurant=self.restaurant,
            data={"name": "Approval Test", "code": "APPTEST", "campaign_type": CAMPAIGN_PROMOTION},
            actor=self.marketer,
        )

    def test_full_approval_workflow(self):
        approval = CampaignApprovalService.submit_for_approval(self.campaign, self.marketer)
        self.assertEqual(approval.status, "PENDING")

        approval = CampaignApprovalService.approve(
            self.campaign, approval, actor=self.approver, note="Looks good"
        )
        self.campaign.refresh_from_db()
        self.assertEqual(approval.status, "APPROVED")
        self.assertEqual(self.campaign.status, CAMPAIGN_APPROVED)

    def test_reject_without_note_raises(self):
        approval = CampaignApprovalService.submit_for_approval(self.campaign, self.marketer)
        with self.assertRaises(ValidationError):
            CampaignApprovalService.reject(self.campaign, approval, actor=self.approver, note="")

    def test_reject_sends_campaign_back_to_draft(self):
        approval = CampaignApprovalService.submit_for_approval(self.campaign, self.marketer)
        CampaignApprovalService.reject(
            self.campaign, approval, actor=self.approver, note="Needs revision"
        )
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, CAMPAIGN_DRAFT)

    def test_self_approval_blocked(self):
        """marketer submits and tries to approve their own campaign."""
        # Give marketer approve permission
        approve_perm = self.perms.get("marketing.campaign.approve")
        self.marketer_role.permissions.add(approve_perm)
        approval = CampaignApprovalService.submit_for_approval(self.campaign, self.marketer)
        with self.assertRaises(MarketingPermissionDenied):
            CampaignApprovalService.approve(
                self.campaign, approval, actor=self.marketer, note="self-approve"
            )

    def test_approve_without_permission_raises(self):
        approval = CampaignApprovalService.submit_for_approval(self.campaign, self.marketer)
        with self.assertRaises(MarketingPermissionDenied):
            CampaignApprovalService.approve(
                self.campaign, approval, actor=self.cashier, note="approve"
            )
