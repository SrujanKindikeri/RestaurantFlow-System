# =============================================================================
# RestaurantFlow — Campaign Services
# Phase 18
#
# CampaignService         — lifecycle management (create/update/transition)
# CampaignApprovalService — approval workflow
#
# Rules:
#   - All business logic here; views are thin.
#   - Status transitions go through transition_status() ONLY.
#   - Approval: creator cannot self-approve (unless settings allow it).
#   - All mutations inside transaction.atomic().
#   - Audit every significant action via _emit_audit().
#   - Real-time events emitted after DB commit via transaction.on_commit().
# =============================================================================

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from accounts import access as acl
from marketing.constants import (
    CAMPAIGN_DRAFT, CAMPAIGN_PENDING_APPROVAL,
    CAMPAIGN_APPROVED, CAMPAIGN_SCHEDULED,
    CAMPAIGN_RUNNING, CAMPAIGN_PAUSED,
    CAMPAIGN_COMPLETED, CAMPAIGN_CANCELLED, CAMPAIGN_FAILED,
    CAMPAIGN_STATUS_TRANSITIONS, CAMPAIGN_TERMINAL_STATUSES,
    APPROVAL_PENDING, APPROVAL_APPROVED, APPROVAL_REJECTED, APPROVAL_CANCELLED,
    PERM_CAMPAIGN_CREATE, PERM_CAMPAIGN_UPDATE, PERM_CAMPAIGN_SUBMIT,
    PERM_CAMPAIGN_APPROVE, PERM_CAMPAIGN_REJECT, PERM_CAMPAIGN_SCHEDULE,
    PERM_CAMPAIGN_PAUSE, PERM_CAMPAIGN_RESUME, PERM_CAMPAIGN_CANCEL,
    AUDIT_CAMPAIGN_CREATED, AUDIT_CAMPAIGN_UPDATED, AUDIT_CAMPAIGN_SUBMITTED,
    AUDIT_CAMPAIGN_APPROVED, AUDIT_CAMPAIGN_REJECTED, AUDIT_CAMPAIGN_SCHEDULED,
    AUDIT_CAMPAIGN_STARTED, AUDIT_CAMPAIGN_PAUSED, AUDIT_CAMPAIGN_RESUMED,
    AUDIT_CAMPAIGN_COMPLETED, AUDIT_CAMPAIGN_CANCELLED,
    WS_CAMPAIGN_CREATED, WS_CAMPAIGN_UPDATED, WS_CAMPAIGN_STARTED,
    WS_CAMPAIGN_PAUSED, WS_CAMPAIGN_COMPLETED,
)
from marketing.exceptions import (
    MarketingPermissionDenied, CampaignNotFound,
    CampaignInvalidTransition, CampaignAlreadyExists,
)

logger = logging.getLogger("marketing")


def _emit_audit(action, entity_type, entity_id, actor=None,
                company=None, restaurant=None, metadata=None):
    from marketing.models import MarketingAuditLog
    try:
        MarketingAuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            company=company,
            restaurant=restaurant,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.error("_emit_audit failed: action=%s error=%s", action, exc)


def _emit_ws(event_name: str, campaign_id, company_id):
    """Emit a real-time WebSocket group message after DB commit."""
    try:
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        if channel_layer:
            group = f"company_{company_id}"
            async_to_sync(channel_layer.group_send)(group, {
                "type": "marketing_event",
                "event": event_name,
                "campaign_id": str(campaign_id),
            })
    except Exception as exc:
        logger.debug("_emit_ws failed (non-critical): event=%s error=%s", event_name, exc)


# =============================================================================
# CampaignService
# =============================================================================

class CampaignService:

    @staticmethod
    def create_campaign(*, company, restaurant=None, branch=None,
                        data: dict, actor) -> "MarketingCampaign":
        """
        Create a new campaign in DRAFT status.

        Validates:
          - permission: marketing.campaign.create
          - code uniqueness within company/restaurant scope
          - date logic (start_at must be before end_at if both provided)
        """
        from marketing.models import MarketingCampaign

        if not acl.has_permission(actor, PERM_CAMPAIGN_CREATE):
            raise MarketingPermissionDenied(PERM_CAMPAIGN_CREATE + " permission required.")

        # Validate scope access
        if restaurant and not acl.can_access_restaurant(actor, restaurant):
            raise PermissionDenied("You do not have access to this restaurant.")

        code = data.get("code", "").strip().upper()
        if not code:
            raise ValidationError({"code": "Campaign code is required."})

        # Uniqueness check
        qs = MarketingCampaign.objects.filter(company=company, code=code)
        if restaurant:
            qs = qs.filter(restaurant=restaurant)
        else:
            qs = qs.filter(restaurant__isnull=True)
        if qs.exists():
            raise CampaignAlreadyExists(
                f"A campaign with code '{code}' already exists."
            )

        # Date validation
        start_at = data.get("start_at")
        end_at = data.get("end_at")
        if start_at and end_at and start_at >= end_at:
            raise ValidationError({"end_at": "end_at must be after start_at."})

        with transaction.atomic():
            campaign = MarketingCampaign.objects.create(
                company=company,
                restaurant=restaurant,
                branch=branch,
                name=data["name"],
                code=code,
                description=data.get("description", ""),
                campaign_type=data["campaign_type"],
                status=CAMPAIGN_DRAFT,
                start_at=start_at,
                end_at=end_at,
                audience_type=data.get("audience_type", ""),
                metadata=data.get("metadata", {}),
                created_by=actor,
            )
            campaign_id = campaign.pk

            transaction.on_commit(lambda: _emit_ws(WS_CAMPAIGN_CREATED, campaign_id, company.pk))

        _emit_audit(
            AUDIT_CAMPAIGN_CREATED, "CAMPAIGN", campaign.pk,
            actor=actor, company=company, restaurant=restaurant,
            metadata={"code": code, "campaign_type": campaign.campaign_type},
        )
        logger.info("CampaignService.create_campaign: %s by %s", code, actor.email)
        return campaign

    @staticmethod
    def update_campaign(campaign, *, data: dict, actor) -> "MarketingCampaign":
        """
        Update a DRAFT or APPROVED campaign.

        Only DRAFT campaigns can be freely edited.
        """
        if not acl.has_permission(actor, PERM_CAMPAIGN_UPDATE):
            raise MarketingPermissionDenied(PERM_CAMPAIGN_UPDATE + " permission required.")

        if campaign.status not in (CAMPAIGN_DRAFT, CAMPAIGN_APPROVED):
            raise ValidationError(
                {"status": "Only DRAFT or APPROVED campaigns can be updated."}
            )

        updatable = {
            "name", "description", "start_at", "end_at",
            "audience_type", "metadata", "campaign_type",
        }
        start_at = data.get("start_at", campaign.start_at)
        end_at = data.get("end_at", campaign.end_at)
        if start_at and end_at and start_at >= end_at:
            raise ValidationError({"end_at": "end_at must be after start_at."})

        with transaction.atomic():
            for field in updatable:
                if field in data:
                    setattr(campaign, field, data[field])
            campaign.save()

        _emit_audit(
            AUDIT_CAMPAIGN_UPDATED, "CAMPAIGN", campaign.pk,
            actor=actor, company=campaign.company, restaurant=campaign.restaurant,
            metadata={"updated_fields": list(data.keys())},
        )
        transaction.on_commit(lambda: _emit_ws(WS_CAMPAIGN_UPDATED, campaign.pk, campaign.company_id))
        return campaign

    @staticmethod
    def transition_status(campaign, *, new_status: str, actor,
                          reason: str = "") -> "MarketingCampaign":
        """
        Central status transition method.

        All status changes go through here. Raises CampaignInvalidTransition
        if the transition is not allowed. Validates permissions per transition.
        """
        current = campaign.status
        allowed = CAMPAIGN_STATUS_TRANSITIONS.get(current, set())

        if new_status not in allowed:
            raise CampaignInvalidTransition(
                f"Cannot transition from {current} to {new_status}. "
                f"Allowed: {', '.join(allowed) or 'none'}."
            )

        # Permission check per transition
        transition_perms = {
            CAMPAIGN_PENDING_APPROVAL: PERM_CAMPAIGN_SUBMIT,
            CAMPAIGN_APPROVED:         PERM_CAMPAIGN_APPROVE,
            CAMPAIGN_SCHEDULED:        PERM_CAMPAIGN_SCHEDULE,
            CAMPAIGN_RUNNING:          PERM_CAMPAIGN_SCHEDULE,
            CAMPAIGN_PAUSED:           PERM_CAMPAIGN_PAUSE,
            CAMPAIGN_CANCELLED:        PERM_CAMPAIGN_CANCEL,
            CAMPAIGN_COMPLETED:        PERM_CAMPAIGN_SCHEDULE,
        }
        required_perm = transition_perms.get(new_status)
        # Resume (PAUSED → SCHEDULED/RUNNING) uses RESUME permission
        if current == CAMPAIGN_PAUSED and new_status in (CAMPAIGN_SCHEDULED, CAMPAIGN_RUNNING):
            required_perm = PERM_CAMPAIGN_RESUME
        if required_perm and not acl.has_permission(actor, required_perm):
            raise MarketingPermissionDenied(f"{required_perm} permission required.")

        now = timezone.now()
        update_fields = ["status", "updated_at"]

        with transaction.atomic():
            # Lock the campaign row
            from marketing.models import MarketingCampaign
            locked = MarketingCampaign.objects.select_for_update().get(pk=campaign.pk)

            # Re-check status after lock (concurrent protection)
            if locked.status != current:
                raise CampaignInvalidTransition(
                    f"Campaign status changed concurrently: expected {current}, got {locked.status}."
                )

            locked.status = new_status

            if new_status == CAMPAIGN_CANCELLED:
                locked.cancelled_by = actor
                locked.cancelled_at = now
                locked.cancellation_reason = reason
                update_fields += ["cancelled_by", "cancelled_at", "cancellation_reason"]

            if new_status == CAMPAIGN_APPROVED:
                locked.approved_by = actor
                locked.approved_at = now
                update_fields += ["approved_by", "approved_at"]

            locked.save(update_fields=update_fields)

        # Audit action mapping
        audit_map = {
            CAMPAIGN_PENDING_APPROVAL: AUDIT_CAMPAIGN_SUBMITTED,
            CAMPAIGN_APPROVED:         AUDIT_CAMPAIGN_APPROVED,
            CAMPAIGN_SCHEDULED:        AUDIT_CAMPAIGN_SCHEDULED,
            CAMPAIGN_RUNNING:          AUDIT_CAMPAIGN_STARTED,
            CAMPAIGN_PAUSED:           AUDIT_CAMPAIGN_PAUSED,
            CAMPAIGN_COMPLETED:        AUDIT_CAMPAIGN_COMPLETED,
            CAMPAIGN_CANCELLED:        AUDIT_CAMPAIGN_CANCELLED,
        }
        if current == CAMPAIGN_PAUSED and new_status in (CAMPAIGN_SCHEDULED, CAMPAIGN_RUNNING):
            audit_action = AUDIT_CAMPAIGN_RESUMED
        else:
            audit_action = audit_map.get(new_status, AUDIT_CAMPAIGN_UPDATED)

        _emit_audit(
            audit_action, "CAMPAIGN", campaign.pk,
            actor=actor, company=campaign.company, restaurant=campaign.restaurant,
            metadata={"from_status": current, "to_status": new_status, "reason": reason},
        )

        # Real-time events
        ws_map = {
            CAMPAIGN_RUNNING:   WS_CAMPAIGN_STARTED,
            CAMPAIGN_PAUSED:    WS_CAMPAIGN_PAUSED,
            CAMPAIGN_COMPLETED: WS_CAMPAIGN_COMPLETED,
        }
        ws_event = ws_map.get(new_status, WS_CAMPAIGN_UPDATED)
        c_id = campaign.pk
        co_id = campaign.company_id
        transaction.on_commit(lambda: _emit_ws(ws_event, c_id, co_id))

        campaign.status = new_status
        return campaign


# =============================================================================
# CampaignApprovalService
# =============================================================================

class CampaignApprovalService:

    @staticmethod
    def submit_for_approval(campaign, actor) -> "CampaignApproval":
        """
        Submit a DRAFT campaign for approval.

        Transitions campaign to PENDING_APPROVAL and creates a CampaignApproval record.
        """
        from marketing.models import CampaignApproval

        # Transition first (validates permission + status)
        CampaignService.transition_status(
            campaign, new_status=CAMPAIGN_PENDING_APPROVAL, actor=actor
        )

        with transaction.atomic():
            approval = CampaignApproval.objects.create(
                campaign=campaign,
                requested_by=actor,
                status=APPROVAL_PENDING,
            )

        _emit_audit(
            AUDIT_CAMPAIGN_SUBMITTED, "CAMPAIGN_APPROVAL", approval.pk,
            actor=actor, company=campaign.company, restaurant=campaign.restaurant,
            metadata={"campaign_code": campaign.code},
        )
        return approval

    @staticmethod
    def approve(campaign, approval, *, actor, note: str = "") -> "CampaignApproval":
        """
        Approve a campaign.

        Creator cannot self-approve (unless MarketingSettings allows it).
        """
        if not acl.has_permission(actor, PERM_CAMPAIGN_APPROVE):
            raise MarketingPermissionDenied(PERM_CAMPAIGN_APPROVE + " permission required.")

        if approval.status != APPROVAL_PENDING:
            raise ValidationError({"status": "This approval request is no longer pending."})

        # Self-approval guard
        if approval.requested_by == actor:
            # Check if settings allow self-approval
            settings_allow = _self_approval_allowed(campaign)
            if not settings_allow:
                raise MarketingPermissionDenied(
                    "You cannot approve a campaign you submitted."
                )

        now = timezone.now()
        with transaction.atomic():
            from marketing.models import CampaignApproval
            locked = CampaignApproval.objects.select_for_update().get(pk=approval.pk)
            locked.status = APPROVAL_APPROVED
            locked.reviewed_by = actor
            locked.review_note = note
            locked.reviewed_at = now
            locked.save(update_fields=[
                "status", "reviewed_by", "review_note", "reviewed_at", "updated_at"
            ])

        # Transition campaign
        CampaignService.transition_status(
            campaign, new_status=CAMPAIGN_APPROVED, actor=actor
        )

        _emit_audit(
            AUDIT_CAMPAIGN_APPROVED, "CAMPAIGN_APPROVAL", approval.pk,
            actor=actor, company=campaign.company, restaurant=campaign.restaurant,
            metadata={"campaign_code": campaign.code, "note": note},
        )
        approval.status = APPROVAL_APPROVED
        return approval

    @staticmethod
    def reject(campaign, approval, *, actor, note: str) -> "CampaignApproval":
        """Reject a campaign approval request."""
        if not acl.has_permission(actor, PERM_CAMPAIGN_REJECT):
            raise MarketingPermissionDenied(PERM_CAMPAIGN_REJECT + " permission required.")

        if not note:
            raise ValidationError({"note": "A rejection reason is required."})

        if approval.status != APPROVAL_PENDING:
            raise ValidationError({"status": "This approval request is no longer pending."})

        now = timezone.now()
        with transaction.atomic():
            from marketing.models import CampaignApproval
            locked = CampaignApproval.objects.select_for_update().get(pk=approval.pk)
            locked.status = APPROVAL_REJECTED
            locked.reviewed_by = actor
            locked.review_note = note
            locked.reviewed_at = now
            locked.save(update_fields=[
                "status", "reviewed_by", "review_note", "reviewed_at", "updated_at"
            ])
            # Revert campaign to DRAFT
            from marketing.models import MarketingCampaign
            MarketingCampaign.objects.filter(pk=campaign.pk).update(
                status=CAMPAIGN_DRAFT, updated_at=now
            )

        _emit_audit(
            AUDIT_CAMPAIGN_REJECTED, "CAMPAIGN_APPROVAL", approval.pk,
            actor=actor, company=campaign.company, restaurant=campaign.restaurant,
            metadata={"campaign_code": campaign.code, "note": note},
        )
        approval.status = APPROVAL_REJECTED
        return approval


def _self_approval_allowed(campaign) -> bool:
    """Check if self-approval is permitted in marketing settings."""
    try:
        settings = campaign.restaurant.marketing_settings
        return getattr(settings, "allow_self_approval", False)
    except Exception:
        return False
