# =============================================================================
# RestaurantFlow — CRM Selectors
# Phase 17
#
# All optimised read/query logic lives here.
# Views call selectors; selectors never modify data.
#
# Performance rules:
#   - Use select_related() / prefetch_related() to prevent N+1
#   - Use annotate() / aggregate() for computed fields at DB level
#   - Never load entire order history in a Python loop
#   - Always filter by accessible scope before returning querysets
# =============================================================================

import logging
from decimal import Decimal

from django.db.models import (
    Avg, Count, Sum, Q, Max, Min, Prefetch, OuterRef, Subquery,
)
from django.utils import timezone

import crm.access as crm_acl

logger = logging.getLogger("crm")


# ---------------------------------------------------------------------------
# Customer selectors
# ---------------------------------------------------------------------------

def get_customer_list(user, filters: dict = None):
    """
    Return an optimised, scoped customer queryset.

    Supports filters:
        search          — searches name, phone, email, customer_number
        is_active       — bool
        is_blocked      — bool
        restaurant_id   — UUID
        branch_id       — UUID (via preferred_branch preference)
        segment_code    — segment code string
        tag_code        — tag code string
        created_after   — datetime
        created_before  — datetime
    """
    from crm.models import Customer, CustomerSegmentAssignment, CustomerTagAssignment

    qs = crm_acl.get_accessible_customers(user).select_related(
        "restaurant", "restaurant__organization"
    )

    filters = filters or {}

    search = filters.get("search", "").strip()
    if search:
        qs = qs.filter(
            Q(customer_number__icontains=search)
            | Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(display_name__icontains=search)
            | Q(phone__icontains=search)
            | Q(email__icontains=search)
        )

    if "is_active" in filters:
        qs = qs.filter(is_active=filters["is_active"])

    if "is_blocked" in filters:
        qs = qs.filter(is_blocked=filters["is_blocked"])

    if filters.get("restaurant_id"):
        qs = qs.filter(restaurant_id=filters["restaurant_id"])

    if filters.get("segment_code"):
        qs = qs.filter(
            segment_assignments__segment__code=filters["segment_code"],
            segment_assignments__is_active=True,
        )

    if filters.get("tag_code"):
        qs = qs.filter(
            tag_assignments__tag__code=filters["tag_code"],
            tag_assignments__is_active=True,
        )

    if filters.get("created_after"):
        qs = qs.filter(created_at__gte=filters["created_after"])

    if filters.get("created_before"):
        qs = qs.filter(created_at__lte=filters["created_before"])

    return qs.distinct()


def get_customer_detail(user, customer_pk):
    """Return a single customer with related data prefetched."""
    from crm.models import Customer

    qs = crm_acl.get_accessible_customers(user).select_related(
        "restaurant", "restaurant__organization",
        "preference",
    ).prefetch_related(
        Prefetch(
            "tag_assignments",
            queryset=__import__(
                "crm.models", fromlist=["CustomerTagAssignment"]
            ).CustomerTagAssignment.objects.filter(
                is_active=True
            ).select_related("tag"),
            to_attr="active_tags",
        ),
        Prefetch(
            "segment_assignments",
            queryset=__import__(
                "crm.models", fromlist=["CustomerSegmentAssignment"]
            ).CustomerSegmentAssignment.objects.filter(
                is_active=True
            ).select_related("segment"),
            to_attr="active_segments",
        ),
    )

    return qs.filter(pk=customer_pk).first()


def get_customer_order_history(customer, filters: dict = None):
    """
    Return orders for a customer with related bill data.
    Never exposes data from outside the customer's restaurant.
    """
    from orders.models import Order

    filters = filters or {}
    qs = Order.objects.filter(
        customer=customer,
    ).select_related(
        "branch", "bill",
    ).prefetch_related("items")

    if filters.get("date_from"):
        qs = qs.filter(created_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(created_at__date__lte=filters["date_to"])
    if filters.get("branch_id"):
        qs = qs.filter(branch_id=filters["branch_id"])
    if filters.get("order_type"):
        qs = qs.filter(order_type=filters["order_type"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])

    return qs.order_by("-created_at")


def get_customer_spending_history(customer, filters: dict = None):
    """
    Return finalized bills for a customer.
    Financial truth comes from billing — never from CRM fields.
    """
    from billing.models import Bill, BillStatus
    from payments.models import Payment, PaymentRefund

    filters = filters or {}

    qs = Bill.objects.filter(
        order__customer=customer,
        status=BillStatus.FINALIZED,
    ).select_related(
        "order", "branch",
    ).order_by("-created_at")

    if filters.get("date_from"):
        qs = qs.filter(created_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(created_at__date__lte=filters["date_to"])
    if filters.get("branch_id"):
        qs = qs.filter(branch_id=filters["branch_id"])

    return qs


def get_customer_visits(customer, filters: dict = None):
    from crm.models import CustomerVisit

    filters = filters or {}
    qs = CustomerVisit.objects.filter(customer=customer).select_related("branch")

    if filters.get("branch_id"):
        qs = qs.filter(branch_id=filters["branch_id"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])

    return qs.order_by("-visit_started_at")


def get_customer_loyalty(customer):
    """Return loyalty accounts with latest transactions prefetched."""
    from crm.models import LoyaltyAccount, LoyaltyTransaction

    return LoyaltyAccount.objects.filter(
        customer=customer,
    ).select_related(
        "loyalty_program",
    ).prefetch_related(
        Prefetch(
            "transactions",
            queryset=LoyaltyTransaction.objects.order_by("-created_at")[:20],
            to_attr="recent_transactions",
        )
    )


def get_customer_rewards(customer):
    """Return reward redemptions for a customer."""
    from crm.models import RewardRedemption

    return RewardRedemption.objects.filter(
        customer=customer,
    ).select_related("reward").order_by("-created_at")


def get_customer_feedback(customer):
    """Return feedback submitted by a customer."""
    from crm.models import CustomerFeedback

    return CustomerFeedback.objects.filter(
        customer=customer,
    ).select_related("branch").order_by("-created_at")


# ---------------------------------------------------------------------------
# Loyalty selectors
# ---------------------------------------------------------------------------

def get_loyalty_program_for_restaurant(restaurant):
    """Return the active loyalty program for a restaurant, or None."""
    from crm.models import LoyaltyProgram

    return LoyaltyProgram.objects.filter(
        restaurant=restaurant, is_active=True
    ).first()


def get_loyalty_transactions(loyalty_account, limit: int = 50):
    from crm.models import LoyaltyTransaction

    return LoyaltyTransaction.objects.filter(
        loyalty_account=loyalty_account
    ).order_by("-created_at")[:limit]


# ---------------------------------------------------------------------------
# Feedback selectors
# ---------------------------------------------------------------------------

def get_feedback_list(user, filters: dict = None):
    """Scoped feedback list with optional filters."""
    from crm.models import CustomerFeedback

    filters = filters or {}
    qs = crm_acl.get_accessible_feedback(user).select_related(
        "customer", "restaurant", "branch",
    )

    if filters.get("branch_id"):
        qs = qs.filter(branch_id=filters["branch_id"])
    if filters.get("rating"):
        qs = qs.filter(rating=filters["rating"])
    if filters.get("status"):
        qs = qs.filter(status=filters["status"])
    if filters.get("date_from"):
        qs = qs.filter(created_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(created_at__date__lte=filters["date_to"])

    return qs.order_by("-created_at")


def get_feedback_summary(restaurant, filters: dict = None):
    """Aggregate feedback stats for a restaurant."""
    from crm.models import CustomerFeedback

    filters = filters or {}
    qs = CustomerFeedback.objects.filter(restaurant=restaurant)

    if filters.get("branch_id"):
        qs = qs.filter(branch_id=filters["branch_id"])
    if filters.get("date_from"):
        qs = qs.filter(created_at__date__gte=filters["date_from"])
    if filters.get("date_to"):
        qs = qs.filter(created_at__date__lte=filters["date_to"])

    return qs.aggregate(
        count=Count("id"),
        average_rating=Avg("rating"),
        average_food_rating=Avg("food_rating"),
        average_service_rating=Avg("service_rating"),
        average_ambience_rating=Avg("ambience_rating"),
        one_star=Count("id", filter=Q(rating=1)),
        two_star=Count("id", filter=Q(rating=2)),
        three_star=Count("id", filter=Q(rating=3)),
        four_star=Count("id", filter=Q(rating=4)),
        five_star=Count("id", filter=Q(rating=5)),
    )


# ---------------------------------------------------------------------------
# CRM Dashboard / Analytics selectors
# ---------------------------------------------------------------------------

def get_crm_dashboard_kpis(restaurant, filters: dict = None):
    """
    Aggregate CRM dashboard KPIs for a restaurant.
    All calculations happen at DB level — no Python loops over full datasets.
    """
    from crm.models import Customer, CustomerVisit
    from django.db.models import Count, Avg, Sum, Q
    from crm.constants import (
        ANALYTICS_NEW_CUSTOMER_DAYS,
        ANALYTICS_INACTIVE_CUSTOMER_DAYS,
        ANALYTICS_RETURNING_MIN_ORDERS,
    )

    filters = filters or {}
    now = timezone.now()
    new_cutoff = now - timezone.timedelta(days=ANALYTICS_NEW_CUSTOMER_DAYS)
    inactive_cutoff = now - timezone.timedelta(days=ANALYTICS_INACTIVE_CUSTOMER_DAYS)

    base_qs = Customer.objects.filter(restaurant=restaurant, is_active=True)

    agg = base_qs.aggregate(
        total_customers=Count("id"),
        new_customers=Count("id", filter=Q(first_order_at__gte=new_cutoff)),
        returning_customers=Count(
            "id", filter=Q(total_orders__gte=ANALYTICS_RETURNING_MIN_ORDERS)
        ),
        inactive_customers=Count(
            "id",
            filter=Q(last_order_at__lt=inactive_cutoff)
            | Q(last_order_at__isnull=True, created_at__lt=inactive_cutoff),
        ),
        avg_lifetime_spend=Avg("lifetime_spend"),
        avg_visits=Avg("total_visits"),
        avg_orders=Avg("total_orders"),
    )

    return agg


def get_top_customers(restaurant, limit: int = 10):
    """Return top customers by lifetime spend."""
    from crm.models import Customer

    return (
        Customer.objects.filter(restaurant=restaurant, is_active=True)
        .order_by("-lifetime_spend")[:limit]
    )
