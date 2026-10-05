# =============================================================================
# RestaurantFlow — CRM Segmentation Services
# Phase 17
#
# CustomerSegmentationService — evaluate criteria-based segments for customers.
#
# Segmentation is DETERMINISTIC:
#   - Criteria is evaluated from stored JSON on CustomerSegment.
#   - Results are predictable given the same customer stats.
#   - Manually assigned tags are NOT overwritten.
#   - Segments and tags are different concepts.
#
# Supported criteria keys:
#   min_orders              — customer.total_orders >= value
#   min_lifetime_spend      — customer.lifetime_spend >= value
#   days_since_last_order   — (today - last_order_at).days >= value (at-risk / inactive)
#   max_days_since_last_order — (today - last_order_at).days <= value (active)
#   min_visits              — customer.total_visits >= value
# =============================================================================

import logging
from decimal import Decimal
from django.utils import timezone

from accounts import access as acl
from crm.constants import (
    AUDIT_CUSTOMER_SEGMENT_ASSIGNED, AUDIT_CUSTOMER_SEGMENT_REMOVED,
    PERM_CUSTOMER_SEGMENT_MANAGE,
)
from crm.exceptions import CRMPermissionDenied

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


class CustomerSegmentationService:

    @staticmethod
    def _build_snapshot(customer) -> dict:
        """Build a snapshot of customer metrics for evaluation and audit."""
        now = timezone.now()
        days_since_last_order = None
        if customer.last_order_at:
            days_since_last_order = (now - customer.last_order_at).days

        return {
            "total_orders": customer.total_orders,
            "total_visits": customer.total_visits,
            "lifetime_spend": float(customer.lifetime_spend),
            "days_since_last_order": days_since_last_order,
            "evaluated_at": now.isoformat(),
        }

    @staticmethod
    def _evaluate_criteria(criteria: dict, snapshot: dict) -> bool:
        """
        Return True if the customer snapshot satisfies ALL criteria.
        Unknown criteria keys are ignored (forward-compatible).
        """
        for key, value in criteria.items():
            if key == "min_orders":
                if snapshot.get("total_orders", 0) < int(value):
                    return False

            elif key == "min_lifetime_spend":
                if snapshot.get("lifetime_spend", 0) < float(value):
                    return False

            elif key == "days_since_last_order":
                # Customer must have been inactive for at least `value` days
                days = snapshot.get("days_since_last_order")
                if days is None:
                    return False
                if days < int(value):
                    return False

            elif key == "max_days_since_last_order":
                # Customer must have ordered within the last `value` days
                days = snapshot.get("days_since_last_order")
                if days is None:
                    return False
                if days > int(value):
                    return False

            elif key == "min_visits":
                if snapshot.get("total_visits", 0) < int(value):
                    return False

        return True

    @staticmethod
    def evaluate_customer(customer, segment) -> bool:
        """Return True if this customer satisfies the segment criteria."""
        snapshot = CustomerSegmentationService._build_snapshot(customer)
        return CustomerSegmentationService._evaluate_criteria(
            segment.criteria, snapshot
        )

    @staticmethod
    def assign_segments(customer, actor=None) -> list:
        """
        Evaluate all active segments for this customer's restaurant
        and create/update assignments accordingly.

        Returns list of newly assigned segments.
        """
        from crm.models import CustomerSegment, CustomerSegmentAssignment

        restaurant = customer.restaurant
        active_segments = CustomerSegment.objects.filter(
            restaurant=restaurant, is_active=True
        )

        snapshot = CustomerSegmentationService._build_snapshot(customer)
        newly_assigned = []

        for segment in active_segments:
            qualifies = CustomerSegmentationService._evaluate_criteria(
                segment.criteria, snapshot
            )

            if qualifies:
                assignment, created = CustomerSegmentAssignment.objects.get_or_create(
                    customer=customer,
                    segment=segment,
                    is_active=True,
                    defaults={"evaluation_snapshot": snapshot},
                )
                if created:
                    newly_assigned.append(segment)
                    _emit_audit(
                        AUDIT_CUSTOMER_SEGMENT_ASSIGNED,
                        "CUSTOMER_SEGMENT", assignment.pk,
                        actor=actor, company=customer.company,
                        restaurant=restaurant, customer=customer,
                        metadata={"segment_code": segment.code, "snapshot": snapshot},
                    )
            else:
                # Remove assignment if customer no longer qualifies
                removed = CustomerSegmentAssignment.objects.filter(
                    customer=customer, segment=segment, is_active=True
                ).update(is_active=False)
                if removed:
                    _emit_audit(
                        AUDIT_CUSTOMER_SEGMENT_REMOVED,
                        "CUSTOMER_SEGMENT", segment.pk,
                        actor=actor, company=customer.company,
                        restaurant=restaurant, customer=customer,
                        metadata={"segment_code": segment.code},
                    )

        return newly_assigned

    @staticmethod
    def remove_invalid_segments(customer, actor=None) -> int:
        """
        Remove any active segment assignments the customer no longer qualifies for.
        Returns count of removed assignments.
        """
        from crm.models import CustomerSegmentAssignment

        snapshot = CustomerSegmentationService._build_snapshot(customer)
        active_assignments = CustomerSegmentAssignment.objects.filter(
            customer=customer, is_active=True
        ).select_related("segment")

        removed_count = 0
        for assignment in active_assignments:
            if not CustomerSegmentationService._evaluate_criteria(
                assignment.segment.criteria, snapshot
            ):
                assignment.is_active = False
                assignment.save(update_fields=["is_active", "updated_at"])
                removed_count += 1
                _emit_audit(
                    AUDIT_CUSTOMER_SEGMENT_REMOVED,
                    "CUSTOMER_SEGMENT", assignment.segment_id,
                    actor=actor, customer=customer,
                    metadata={"segment_code": assignment.segment.code},
                )

        return removed_count

    @staticmethod
    def evaluate_restaurant(restaurant, actor=None) -> dict:
        """
        Run segmentation for ALL active customers in a restaurant.
        Used by Celery beat task — can be slow for large restaurants.
        Returns counts of assignments created/removed.
        """
        from crm.models import Customer

        customers = Customer.objects.filter(restaurant=restaurant, is_active=True)
        total_assigned = 0
        total_removed = 0

        for customer in customers.iterator(chunk_size=200):
            assigned = CustomerSegmentationService.assign_segments(customer, actor=actor)
            total_assigned += len(assigned)

        logger.info(
            "CustomerSegmentationService.evaluate_restaurant: "
            "restaurant=%s assigned=%d removed=%d",
            restaurant.pk, total_assigned, total_removed,
        )
        return {"assigned": total_assigned, "removed": total_removed}
