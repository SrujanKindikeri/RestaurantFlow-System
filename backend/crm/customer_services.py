# =============================================================================
# RestaurantFlow — CRM Customer Services
# Phase 17
#
# CustomerIdentityService  — normalize, find, resolve-or-create
# CustomerService          — create, update, block, link-to-order, merge
# CustomerStatisticsService — backend-authoritative computed statistics
# CustomerVisitService     — idempotent visit creation and tracking
# CustomerTagService       — tag assignment and removal
# =============================================================================

import logging
import uuid as _uuid
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts import access as acl
from crm.constants import (
    CUSTOMER_NUMBER_PREFIX,
    VISIT_DINE_IN, VISIT_TAKEAWAY, VISIT_COUNTER,
    VISIT_COMPLETED, VISIT_OPEN,
    AUDIT_CUSTOMER_CREATED, AUDIT_CUSTOMER_UPDATED,
    AUDIT_CUSTOMER_BLOCKED, AUDIT_CUSTOMER_UNBLOCKED,
    AUDIT_CUSTOMER_LINKED_TO_ORDER,
    AUDIT_CUSTOMER_TAG_ASSIGNED, AUDIT_CUSTOMER_TAG_REMOVED,
    AUDIT_CUSTOMER_MERGE_REQUESTED, AUDIT_MERGE_REQUESTED,
    AUDIT_MERGE_APPROVED, AUDIT_MERGE_REJECTED,
    MERGE_REQUESTED, MERGE_APPROVED, MERGE_REJECTED, MERGE_CANCELLED,
    PERM_CUSTOMER_CREATE, PERM_CUSTOMER_UPDATE,
    PERM_CUSTOMER_BLOCK, PERM_CUSTOMER_LINK,
    PERM_CUSTOMER_TAG_MANAGE, PERM_CUSTOMER_MERGE_REQUEST,
    PERM_CUSTOMER_MERGE_APPROVE,
)
from crm.exceptions import (
    CustomerNotFound, CustomerAlreadyExists, CustomerBlocked,
    CustomerScopeViolation, CustomerIdentityConflict,
    CustomerMergeConflict, CustomerMergeNotAllowed,
    CRMPermissionDenied,
)
from crm.validators import (
    normalize_phone, normalize_email,
    validate_phone, validate_email,
)

logger = logging.getLogger("crm")


def _emit_audit(action, entity_type, entity_id, actor=None,
                company=None, restaurant=None, branch=None, customer=None,
                metadata=None):
    """Write a CRMAuditLog entry. Never raises — errors are logged only."""
    from crm.models import CRMAuditLog
    try:
        CRMAuditLog.objects.create(
            actor=actor,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            company=company,
            restaurant=restaurant,
            branch=branch,
            customer=customer,
            metadata=metadata or {},
        )
    except Exception as exc:
        logger.error("_emit_audit failed: action=%s error=%s", action, exc)


# =============================================================================
# CustomerIdentityService
# =============================================================================

class CustomerIdentityService:
    """
    Handles customer de-duplication and identity resolution.

    Matching strategy:
      - Normalize phone and email before any comparison.
      - If phone matches an existing active customer → reuse.
      - If email matches an existing active customer → reuse.
      - If phone matches one customer AND email matches a DIFFERENT customer
        → return a conflict; do NOT auto-merge.
      - If no match → create a new customer.
    """

    @staticmethod
    def normalize_phone(phone: str) -> str:
        return normalize_phone(phone)

    @staticmethod
    def normalize_email(email: str) -> str:
        return normalize_email(email)

    @staticmethod
    def find_existing_customer(restaurant, phone: str = "", email: str = ""):
        """
        Look for an existing active customer in this restaurant matching phone or email.

        Returns:
            (customer_or_None, conflict: bool)
            conflict=True means phone+email matched different customers.
        """
        from crm.models import Customer

        norm_phone = normalize_phone(phone)
        norm_email = normalize_email(email)

        phone_match = None
        email_match = None

        if norm_phone:
            phone_match = (
                Customer.objects.filter(
                    restaurant=restaurant,
                    phone=norm_phone,
                    is_active=True,
                )
                .exclude(merged_into__isnull=False)
                .first()
            )

        if norm_email:
            email_match = (
                Customer.objects.filter(
                    restaurant=restaurant,
                    email=norm_email,
                    is_active=True,
                )
                .exclude(merged_into__isnull=False)
                .first()
            )

        if phone_match and email_match:
            if phone_match.pk == email_match.pk:
                return phone_match, False
            else:
                # Conflict — phone and email point to different customers
                return None, True

        return phone_match or email_match, False

    @staticmethod
    def resolve_or_create_customer(restaurant, data: dict, actor=None):
        """
        Resolve an existing customer or create a new one.

        data keys: first_name, last_name, phone, email, (optional extras)

        Returns:
            (customer, created: bool)

        Raises:
            CustomerIdentityConflict if phone+email match different customers.
        """
        from crm.exceptions import CustomerIdentityConflict

        phone = normalize_phone(data.get("phone", ""))
        email = normalize_email(data.get("email", ""))

        existing, conflict = CustomerIdentityService.find_existing_customer(
            restaurant, phone=phone, email=email
        )
        if conflict:
            raise CustomerIdentityConflict()

        if existing:
            return existing, False

        # Create new
        customer = CustomerService.create_customer(
            restaurant=restaurant,
            data=data,
            actor=actor,
        )
        return customer, True


# =============================================================================
# CustomerService
# =============================================================================

class CustomerService:

    @staticmethod
    def _generate_customer_number(restaurant) -> str:
        """
        Concurrency-safe customer number generator.
        Uses select_for_update() on CustomerSequence — never MAX()+1.
        Format: CUS-000001
        """
        from crm.models import CustomerSequence

        seq, _ = CustomerSequence.objects.select_for_update().get_or_create(
            restaurant=restaurant,
            defaults={"last_sequence": 0},
        )
        seq.last_sequence += 1
        seq.save(update_fields=["last_sequence", "updated_at"])
        return f"{CUSTOMER_NUMBER_PREFIX}-{seq.last_sequence:06d}"

    @staticmethod
    def create_customer(restaurant, data: dict, actor=None) -> "Customer":
        """
        Create a new Customer for a restaurant.

        All identity fields are normalized before saving.
        customer_number is generated atomically.
        """
        from crm.models import Customer

        if actor and not acl.has_permission(actor, PERM_CUSTOMER_CREATE):
            raise CRMPermissionDenied("customer.create permission required.")

        # Normalize
        phone = normalize_phone(data.get("phone", ""))
        email = normalize_email(data.get("email", ""))

        if phone:
            validate_phone(phone)
        if email:
            validate_email(email)

        with transaction.atomic():
            customer_number = CustomerService._generate_customer_number(restaurant)

            first_name = (data.get("first_name") or "").strip()
            last_name = (data.get("last_name") or "").strip()

            customer = Customer.objects.create(
                company=restaurant.organization,
                restaurant=restaurant,
                customer_number=customer_number,
                first_name=first_name,
                last_name=last_name,
                display_name=data.get("display_name", "").strip(),
                phone=phone,
                email=email,
                date_of_birth=data.get("date_of_birth"),
                gender=data.get("gender", ""),
                address=data.get("address", ""),
                city=data.get("city", ""),
                state=data.get("state", ""),
                postal_code=data.get("postal_code", ""),
                country=data.get("country", "India"),
                notes=data.get("notes", ""),
                preferred_language=data.get("preferred_language", ""),
            )

        _emit_audit(
            AUDIT_CUSTOMER_CREATED, "CUSTOMER", customer.pk,
            actor=actor, company=restaurant.organization,
            restaurant=restaurant, customer=customer,
            metadata={"customer_number": customer_number},
        )

        logger.info(
            "CustomerService.create_customer: restaurant=%s number=%s actor=%s",
            restaurant.pk, customer_number,
            actor.email if actor else "system",
        )
        return customer

    @staticmethod
    def update_customer(customer, data: dict, actor=None) -> "Customer":
        """Update mutable customer fields. Never updates computed stats or customer_number."""
        if actor and not acl.has_permission(actor, PERM_CUSTOMER_UPDATE):
            raise CRMPermissionDenied("customer.update permission required.")

        IMMUTABLE = {"customer_number", "company", "restaurant", "id"}
        COMPUTED = {"total_visits", "total_orders", "lifetime_spend",
                    "last_visit_at", "last_order_at", "first_order_at"}

        update_fields = []
        for field, value in data.items():
            if field in IMMUTABLE or field in COMPUTED:
                continue
            if field == "phone":
                value = normalize_phone(value)
                if value:
                    validate_phone(value)
            elif field == "email":
                value = normalize_email(value)
                if value:
                    validate_email(value)
            setattr(customer, field, value)
            update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            customer.save(update_fields=update_fields)
            _emit_audit(
                AUDIT_CUSTOMER_UPDATED, "CUSTOMER", customer.pk,
                actor=actor, company=customer.company,
                restaurant=customer.restaurant, customer=customer,
                metadata={"updated_fields": update_fields},
            )

        return customer

    @staticmethod
    def block_customer(customer, reason: str, actor=None) -> "Customer":
        """Block a customer with a reason."""
        if actor and not acl.has_permission(actor, PERM_CUSTOMER_BLOCK):
            raise CRMPermissionDenied("customer.block permission required.")
        if not reason:
            raise ValidationError({"blocked_reason": "A reason is required to block a customer."})

        customer.is_blocked = True
        customer.blocked_reason = reason
        customer.save(update_fields=["is_blocked", "blocked_reason", "updated_at"])

        _emit_audit(
            AUDIT_CUSTOMER_BLOCKED, "CUSTOMER", customer.pk,
            actor=actor, company=customer.company,
            restaurant=customer.restaurant, customer=customer,
            metadata={"reason": reason},
        )
        return customer

    @staticmethod
    def unblock_customer(customer, actor=None) -> "Customer":
        """Unblock a previously blocked customer."""
        if actor and not acl.has_permission(actor, PERM_CUSTOMER_BLOCK):
            raise CRMPermissionDenied("customer.block permission required.")

        customer.is_blocked = False
        customer.blocked_reason = ""
        customer.save(update_fields=["is_blocked", "blocked_reason", "updated_at"])

        _emit_audit(
            AUDIT_CUSTOMER_UNBLOCKED, "CUSTOMER", customer.pk,
            actor=actor, company=customer.company,
            restaurant=customer.restaurant, customer=customer,
        )
        return customer

    @staticmethod
    def link_customer_to_order(order, customer, actor=None) -> None:
        """
        Link a Customer to an existing Order.
        Idempotent: if already linked to the same customer, no-op.
        """
        if actor and not acl.has_permission(actor, PERM_CUSTOMER_LINK):
            raise CRMPermissionDenied("customer.link permission required.")

        if order.customer_id == customer.pk:
            return  # idempotent

        if order.customer_id and order.customer_id != customer.pk:
            raise ValidationError(
                "Order is already linked to a different customer."
            )

        # Verify same restaurant scope
        order_restaurant = order.branch.restaurant
        if str(order_restaurant.pk) != str(customer.restaurant_id):
            raise CustomerScopeViolation(
                "Customer and order must belong to the same restaurant."
            )

        order.customer = customer
        order.save(update_fields=["customer", "updated_at"])

        _emit_audit(
            AUDIT_CUSTOMER_LINKED_TO_ORDER, "ORDER", order.pk,
            actor=actor, company=customer.company,
            restaurant=customer.restaurant, customer=customer,
            metadata={"order_id": str(order.pk), "order_number": order.order_number},
        )

        logger.info(
            "CustomerService.link_customer_to_order: customer=%s order=%s",
            customer.customer_number, order.order_number,
        )


# =============================================================================
# CustomerStatisticsService
# =============================================================================

class CustomerStatisticsService:
    """
    Compute and update backend-authoritative customer statistics.

    All statistics are derived from actual Order / Bill / Payment records.
    Never trust frontend-supplied counts or amounts.
    """

    @staticmethod
    def refresh_statistics(customer) -> None:
        """
        Recalculate and persist all statistics for a customer.
        Safe to call multiple times — idempotent.
        """
        from orders.models import Order
        from billing.models import Bill, BillStatus

        restaurant = customer.restaurant

        # All confirmed orders for this customer in this restaurant
        orders_qs = Order.objects.filter(
            customer=customer,
            branch__restaurant=restaurant,
        )

        completed_orders = orders_qs.filter(status="CONFIRMED")
        total_orders = completed_orders.count()

        # First and last order timestamps
        first_order = completed_orders.order_by("created_at").first()
        last_order = completed_orders.order_by("-created_at").first()

        first_order_at = first_order.created_at if first_order else None
        last_order_at = last_order.created_at if last_order else None

        # Lifetime spend from finalized bills
        from django.db.models import Sum, Count
        bill_agg = Bill.objects.filter(
            order__customer=customer,
            order__branch__restaurant=restaurant,
            status=BillStatus.FINALIZED,
        ).aggregate(
            total=Sum("grand_total"),
        )
        lifetime_spend = bill_agg["total"] or Decimal("0.00")

        # Visit count
        from crm.models import CustomerVisit
        total_visits = CustomerVisit.objects.filter(
            customer=customer,
            restaurant=restaurant,
            status=VISIT_COMPLETED,
        ).count()

        last_visit = (
            CustomerVisit.objects.filter(
                customer=customer,
                restaurant=restaurant,
                status=VISIT_COMPLETED,
            )
            .order_by("-visit_started_at")
            .first()
        )
        last_visit_at = last_visit.visit_started_at if last_visit else None

        # Persist
        customer.total_orders = total_orders
        customer.total_visits = total_visits
        customer.lifetime_spend = lifetime_spend
        customer.first_order_at = first_order_at
        customer.last_order_at = last_order_at
        customer.last_visit_at = last_visit_at
        customer.save(update_fields=[
            "total_orders", "total_visits", "lifetime_spend",
            "first_order_at", "last_order_at", "last_visit_at",
            "updated_at",
        ])

    @staticmethod
    def get_favorite_items(customer, limit: int = 5) -> list:
        """Return most-ordered menu items for a customer (top N by frequency)."""
        from orders.models import OrderItem
        from django.db.models import Count

        return (
            OrderItem.objects.filter(
                order__customer=customer,
                order__status="CONFIRMED",
            )
            .values("menu_item_id", "item_name_snapshot")
            .annotate(order_count=Count("id"))
            .order_by("-order_count")[:limit]
        )

    @staticmethod
    def get_favorite_categories(customer, limit: int = 3) -> list:
        """Return most-ordered menu categories for a customer."""
        from orders.models import OrderItem
        from django.db.models import Count

        return (
            OrderItem.objects.filter(
                order__customer=customer,
                order__status="CONFIRMED",
            )
            .values(
                "menu_item__category_id",
                "menu_item__category__name",
            )
            .annotate(order_count=Count("id"))
            .order_by("-order_count")[:limit]
        )


# =============================================================================
# CustomerVisitService
# =============================================================================

class CustomerVisitService:
    """
    Idempotent customer visit tracking.

    One qualifying (CONFIRMED) order creates at most one CustomerVisit.
    Uses the order's OneToOne relationship as the idempotency key.
    """

    ORDER_TYPE_TO_VISIT_TYPE = {
        "DINE_IN":  VISIT_DINE_IN,
        "TAKEAWAY": VISIT_TAKEAWAY,
        "COUNTER":  VISIT_COUNTER,
    }

    @staticmethod
    def record_visit_for_order(order) -> "CustomerVisit | None":
        """
        Create a CustomerVisit for a CONFIRMED order that has a customer linked.
        Returns None if order is not eligible (DRAFT/CANCELLED/no customer).
        Idempotent — returns existing visit if already created.
        """
        from crm.models import CustomerVisit

        if order.status != "CONFIRMED":
            return None
        if not order.customer_id:
            return None

        # Check idempotency
        existing = CustomerVisit.objects.filter(order=order).first()
        if existing:
            return existing

        customer = order.customer
        restaurant = order.branch.restaurant
        branch = order.branch

        visit_type = CustomerVisitService.ORDER_TYPE_TO_VISIT_TYPE.get(
            order.order_type, VISIT_DINE_IN
        )

        # Sequential visit number for this customer at this restaurant
        visit_number = (
            CustomerVisit.objects.filter(
                customer=customer,
                restaurant=restaurant,
            ).count() + 1
        )

        with transaction.atomic():
            visit = CustomerVisit.objects.create(
                customer=customer,
                restaurant=restaurant,
                branch=branch,
                order=order,
                table_session=order.table_session,
                visit_number=visit_number,
                visit_started_at=order.confirmed_at or order.created_at,
                guest_count=order.guest_count or 1,
                visit_type=visit_type,
                status=VISIT_COMPLETED,
            )

        logger.info(
            "CustomerVisitService.record_visit_for_order: "
            "customer=%s order=%s visit=#%d",
            customer.customer_number, order.order_number, visit_number,
        )
        return visit

    @staticmethod
    def complete_visit(visit) -> "CustomerVisit":
        if visit.status == VISIT_COMPLETED:
            return visit
        visit.status = VISIT_COMPLETED
        visit.visit_completed_at = timezone.now()
        visit.save(update_fields=["status", "visit_completed_at", "updated_at"])
        return visit


# =============================================================================
# CustomerTagService
# =============================================================================

class CustomerTagService:

    @staticmethod
    def assign_tag(customer, tag, actor=None) -> "CustomerTagAssignment":
        """Assign a tag to a customer. Idempotent if already active."""
        from crm.models import CustomerTagAssignment

        if actor and not acl.has_permission(actor, PERM_CUSTOMER_TAG_MANAGE):
            raise CRMPermissionDenied("customer.tag.manage permission required.")

        # Check scope
        if str(tag.restaurant_id) != str(customer.restaurant_id):
            raise CustomerScopeViolation(
                "Tag must belong to the same restaurant as the customer."
            )

        assignment, created = CustomerTagAssignment.objects.get_or_create(
            customer=customer,
            tag=tag,
            is_active=True,
            defaults={"assigned_by": actor},
        )

        if created:
            _emit_audit(
                AUDIT_CUSTOMER_TAG_ASSIGNED, "CUSTOMER_TAG", assignment.pk,
                actor=actor, company=customer.company,
                restaurant=customer.restaurant, customer=customer,
                metadata={"tag_code": tag.code},
            )

        return assignment

    @staticmethod
    def remove_tag(customer, tag, actor=None) -> None:
        """Deactivate a tag assignment for a customer."""
        from crm.models import CustomerTagAssignment

        if actor and not acl.has_permission(actor, PERM_CUSTOMER_TAG_MANAGE):
            raise CRMPermissionDenied("customer.tag.manage permission required.")

        updated = CustomerTagAssignment.objects.filter(
            customer=customer,
            tag=tag,
            is_active=True,
        ).update(is_active=False)

        if updated:
            _emit_audit(
                AUDIT_CUSTOMER_TAG_REMOVED, "CUSTOMER_TAG", tag.pk,
                actor=actor, company=customer.company,
                restaurant=customer.restaurant, customer=customer,
                metadata={"tag_code": tag.code},
            )


# =============================================================================
# CustomerMergeService
# =============================================================================

class CustomerMergeService:

    @staticmethod
    def request_merge(source_customer, target_customer, reason: str, actor) -> "CustomerMergeRequest":
        from crm.models import CustomerMergeRequest
        from crm.constants import AUDIT_MERGE_REQUESTED

        if not acl.has_permission(actor, PERM_CUSTOMER_MERGE_REQUEST):
            raise CRMPermissionDenied("customer.merge.request permission required.")

        if source_customer.pk == target_customer.pk:
            raise CustomerMergeConflict("Source and target customers must be different.")

        if str(source_customer.restaurant_id) != str(target_customer.restaurant_id):
            raise CustomerMergeConflict("Customers must belong to the same restaurant.")

        # Check no pending request already exists
        existing = CustomerMergeRequest.objects.filter(
            source_customer=source_customer,
            target_customer=target_customer,
            status=MERGE_REQUESTED,
        ).first()
        if existing:
            raise CustomerMergeConflict("A merge request for these customers already exists.")

        merge_request = CustomerMergeRequest.objects.create(
            source_customer=source_customer,
            target_customer=target_customer,
            requested_by=actor,
            reason=reason,
            status=MERGE_REQUESTED,
        )

        _emit_audit(
            AUDIT_MERGE_REQUESTED, "CUSTOMER_MERGE", merge_request.pk,
            actor=actor, company=source_customer.company,
            restaurant=source_customer.restaurant,
            metadata={
                "source": str(source_customer.pk),
                "target": str(target_customer.pk),
            },
        )
        return merge_request

    @staticmethod
    def approve_merge(merge_request, actor) -> "CustomerMergeRequest":
        from crm.models import CustomerMergeRequest

        if not acl.has_permission(actor, PERM_CUSTOMER_MERGE_APPROVE):
            raise CRMPermissionDenied("customer.merge.approve permission required.")

        if merge_request.status != MERGE_REQUESTED:
            raise CustomerMergeNotAllowed(
                f"Cannot approve a merge in status {merge_request.status}."
            )

        with transaction.atomic():
            # Lock both customers
            from crm.models import Customer
            source = Customer.objects.select_for_update().get(
                pk=merge_request.source_customer_id
            )
            target = Customer.objects.select_for_update().get(
                pk=merge_request.target_customer_id
            )

            # Reassign orders
            from orders.models import Order
            Order.objects.filter(customer=source).update(customer=target)

            # Reassign loyalty accounts
            from crm.models import LoyaltyAccount, LoyaltyTransaction
            for src_acc in LoyaltyAccount.objects.filter(customer=source):
                try:
                    tgt_acc = LoyaltyAccount.objects.select_for_update().get(
                        customer=target,
                        loyalty_program=src_acc.loyalty_program,
                    )
                    # Merge balance: create an ADJUSTMENT on target
                    if src_acc.points_balance > 0:
                        from crm.loyalty_services import LoyaltyService
                        LoyaltyService.adjust_points(
                            loyalty_account=tgt_acc,
                            points=src_acc.points_balance,
                            reason=f"Merged from customer {source.customer_number}",
                            actor=actor,
                        )
                except LoyaltyAccount.DoesNotExist:
                    src_acc.customer = target
                    src_acc.save(update_fields=["customer", "updated_at"])

            # Reassign feedback
            from crm.models import CustomerFeedback
            CustomerFeedback.objects.filter(customer=source).update(customer=target)

            # Reassign visits
            from crm.models import CustomerVisit
            CustomerVisit.objects.filter(customer=source).update(customer=target)

            # Deactivate source
            source.is_active = False
            source.merged_into = target
            source.save(update_fields=["is_active", "merged_into", "updated_at"])

            # Approve request
            merge_request.status = MERGE_APPROVED
            merge_request.approved_by = actor
            merge_request.approved_at = timezone.now()
            merge_request.save(update_fields=[
                "status", "approved_by", "approved_at", "updated_at"
            ])

        # Refresh target stats after merge
        CustomerStatisticsService.refresh_statistics(target)

        _emit_audit(
            AUDIT_MERGE_APPROVED, "CUSTOMER_MERGE", merge_request.pk,
            actor=actor, company=source.company, restaurant=source.restaurant,
            metadata={"source": str(source.pk), "target": str(target.pk)},
        )
        return merge_request

    @staticmethod
    def reject_merge(merge_request, actor) -> "CustomerMergeRequest":
        if not acl.has_permission(actor, PERM_CUSTOMER_MERGE_APPROVE):
            raise CRMPermissionDenied("customer.merge.approve permission required.")

        if merge_request.status != MERGE_REQUESTED:
            raise CustomerMergeNotAllowed(
                f"Cannot reject a merge in status {merge_request.status}."
            )

        merge_request.status = MERGE_REJECTED
        merge_request.approved_by = actor
        merge_request.rejected_at = timezone.now()
        merge_request.save(update_fields=[
            "status", "approved_by", "rejected_at", "updated_at"
        ])

        _emit_audit(
            AUDIT_MERGE_REJECTED, "CUSTOMER_MERGE", merge_request.pk,
            actor=actor, company=merge_request.source_customer.company,
            restaurant=merge_request.source_customer.restaurant,
        )
        return merge_request
