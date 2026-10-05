# =============================================================================
# RestaurantFlow — CRM Feedback Services
# Phase 17
#
# FeedbackService          — create, update feedback
# FeedbackModerationService — moderate feedback, integrate with CentralIssue
# =============================================================================

import logging

from django.db import transaction
from django.utils import timezone

from accounts import access as acl
from crm.constants import (
    FEEDBACK_SUBMITTED, FEEDBACK_REVIEWED, FEEDBACK_RESOLVED, FEEDBACK_HIDDEN,
    MODERATION_PENDING, MODERATION_APPROVED, MODERATION_HIDDEN, MODERATION_REJECTED,
    PERM_FEEDBACK_CREATE, PERM_FEEDBACK_UPDATE, PERM_FEEDBACK_MODERATE, PERM_FEEDBACK_RESOLVE,
    AUDIT_FEEDBACK_CREATED, AUDIT_FEEDBACK_UPDATED,
    AUDIT_FEEDBACK_MODERATED, AUDIT_FEEDBACK_RESOLVED,
)
from crm.exceptions import (
    FeedbackNotAllowed, FeedbackAlreadyExists,
    FeedbackModerationNotAllowed, CRMPermissionDenied,
)
from crm.validators import validate_rating

logger = logging.getLogger("crm")


def _emit_audit(action, entity_type, entity_id, actor=None,
                company=None, restaurant=None, customer=None, metadata=None):
    from crm.models import CRMAuditLog
    try:
        CRMAuditLog.objects.create(
            actor=actor, action=action, entity_type=entity_type,
            entity_id=entity_id, company=company, restaurant=restaurant,
            customer=customer, metadata=metadata or {},
        )
    except Exception as exc:
        logger.error("_emit_audit failed: action=%s error=%s", action, exc)


class FeedbackService:

    @staticmethod
    def create_feedback(data: dict, actor=None) -> "CustomerFeedback":
        """
        Create customer feedback.

        Validates:
          - Rating is 1–5
          - If order is provided, customer must be associated with it
          - Duplicate prevention: one feedback per customer/order pair
        """
        from crm.models import CustomerFeedback

        if actor and not acl.has_permission(actor, PERM_FEEDBACK_CREATE):
            raise CRMPermissionDenied("feedback.create permission required.")

        customer = data.get("customer")
        restaurant = data.get("restaurant")
        branch = data.get("branch")
        order = data.get("order")
        visit = data.get("visit")
        rating = data["rating"]

        validate_rating(rating)
        for sub_field in ("service_rating", "food_rating", "ambience_rating"):
            if data.get(sub_field) is not None:
                validate_rating(data[sub_field], sub_field)

        # Validate order ownership if provided
        if order and customer:
            if order.customer_id and str(order.customer_id) != str(customer.pk):
                raise FeedbackNotAllowed(
                    "This order is not associated with this customer."
                )
            if order.status == "CANCELLED":
                raise FeedbackNotAllowed("Cannot submit feedback for a cancelled order.")

            if str(order.branch.restaurant_id) != str(restaurant.pk):
                raise FeedbackNotAllowed(
                    "Order does not belong to this restaurant."
                )

        # Duplicate prevention per customer+order
        if order and customer:
            existing = CustomerFeedback.objects.filter(
                customer=customer, order=order
            ).first()
            if existing:
                raise FeedbackAlreadyExists(
                    "Feedback already exists for this customer and order."
                )

        feedback = CustomerFeedback.objects.create(
            customer=customer,
            restaurant=restaurant,
            branch=branch,
            order=order,
            visit=visit,
            rating=rating,
            service_rating=data.get("service_rating"),
            food_rating=data.get("food_rating"),
            ambience_rating=data.get("ambience_rating"),
            comment=data.get("comment", ""),
            status=FEEDBACK_SUBMITTED,
        )

        _emit_audit(
            AUDIT_FEEDBACK_CREATED, "CUSTOMER_FEEDBACK", feedback.pk,
            actor=actor,
            company=restaurant.organization if restaurant else None,
            restaurant=restaurant, customer=customer,
            metadata={"rating": rating},
        )

        logger.info(
            "FeedbackService.create_feedback: restaurant=%s rating=%d",
            restaurant.pk if restaurant else "?", rating,
        )
        return feedback

    @staticmethod
    def update_feedback(feedback, data: dict, actor=None) -> "CustomerFeedback":
        if actor and not acl.has_permission(actor, PERM_FEEDBACK_UPDATE):
            raise CRMPermissionDenied("feedback.update permission required.")

        if feedback.status in (FEEDBACK_RESOLVED, FEEDBACK_HIDDEN):
            raise FeedbackNotAllowed("Cannot update resolved or hidden feedback.")

        allowed = {"rating", "service_rating", "food_rating", "ambience_rating", "comment"}
        update_fields = []
        for field in allowed:
            if field in data:
                if "rating" in field and data[field] is not None:
                    validate_rating(data[field], field)
                setattr(feedback, field, data[field])
                update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            feedback.save(update_fields=update_fields)
            _emit_audit(
                AUDIT_FEEDBACK_UPDATED, "CUSTOMER_FEEDBACK", feedback.pk,
                actor=actor, customer=feedback.customer,
                restaurant=feedback.restaurant,
            )
        return feedback


class FeedbackModerationService:

    @staticmethod
    def moderate_feedback(feedback, status: str, note: str = "", actor=None) -> "FeedbackModeration":
        from crm.models import FeedbackModeration

        if actor and not acl.has_permission(actor, PERM_FEEDBACK_MODERATE):
            raise FeedbackModerationNotAllowed()

        allowed_statuses = {MODERATION_APPROVED, MODERATION_HIDDEN, MODERATION_REJECTED}
        if status not in allowed_statuses:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"status": f"Invalid moderation status: {status}"})

        with transaction.atomic():
            moderation = FeedbackModeration.objects.create(
                feedback=feedback,
                reviewed_by=actor,
                status=status,
                moderation_note=note,
                reviewed_at=timezone.now(),
            )

            # Update feedback status to reflect moderation
            if status == MODERATION_HIDDEN:
                feedback.status = FEEDBACK_HIDDEN
            elif status == MODERATION_APPROVED:
                feedback.status = FEEDBACK_REVIEWED
            feedback.save(update_fields=["status", "updated_at"])

        _emit_audit(
            AUDIT_FEEDBACK_MODERATED, "FEEDBACK_MODERATION", moderation.pk,
            actor=actor, restaurant=feedback.restaurant, customer=feedback.customer,
            metadata={"status": status, "feedback_rating": feedback.rating},
        )
        return moderation

    @staticmethod
    def resolve_feedback(feedback, note: str = "", actor=None) -> "CustomerFeedback":
        if actor and not acl.has_permission(actor, PERM_FEEDBACK_RESOLVE):
            raise CRMPermissionDenied("feedback.resolve permission required.")

        feedback.status = FEEDBACK_RESOLVED
        feedback.save(update_fields=["status", "updated_at"])

        _emit_audit(
            AUDIT_FEEDBACK_RESOLVED, "CUSTOMER_FEEDBACK", feedback.pk,
            actor=actor, restaurant=feedback.restaurant, customer=feedback.customer,
        )
        return feedback

    @staticmethod
    def create_central_issue_from_feedback(feedback, actor) -> "CentralIssue | None":
        """
        Create a CentralIssue from a serious feedback complaint.
        Reuses existing central_control.CentralIssue — no new model.
        """
        try:
            from central_control.models import CentralIssue
            from central_control.constants import (
                ISSUE_OPEN,
                ISSUE_CATEGORY_QUALITY,
            )

            restaurant = feedback.restaurant
            company = restaurant.organization

            issue = CentralIssue.objects.create(
                organization=company,
                restaurant=restaurant,
                branch=feedback.branch,
                category=ISSUE_CATEGORY_QUALITY,
                title=f"Customer feedback complaint (rating {feedback.rating}/5)",
                description=(
                    f"Feedback ID: {feedback.pk}\n"
                    f"Rating: {feedback.rating}/5\n"
                    f"Comment: {feedback.comment[:500]}"
                ),
                severity="HIGH" if feedback.rating <= 2 else "MEDIUM",
                status=ISSUE_OPEN,
                created_by=actor,
            )

            # Record the issue link on the moderation record
            from crm.models import FeedbackModeration
            FeedbackModeration.objects.filter(feedback=feedback).update(
                central_issue_id=issue.pk
            )

            logger.info(
                "FeedbackModerationService: created CentralIssue %s for feedback %s",
                issue.pk, feedback.pk,
            )
            return issue
        except Exception as exc:
            logger.error(
                "create_central_issue_from_feedback failed: feedback=%s error=%s",
                feedback.pk, exc,
            )
            return None
