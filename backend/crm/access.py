# =============================================================================
# RestaurantFlow — CRM Access Control
# Phase 17
#
# Single source of truth for CRM authorization decisions.
# Views and services delegate here — never duplicate access logic.
#
# Public API:
#   get_accessible_customers(user)                → QuerySet[Customer]
#   get_accessible_loyalty_programs(user)         → QuerySet[LoyaltyProgram]
#   get_accessible_rewards(user)                  → QuerySet[LoyaltyReward]
#   get_accessible_feedback(user)                 → QuerySet[CustomerFeedback]
#   get_accessible_segments(user)                 → QuerySet[CustomerSegment]
#   get_accessible_tags(user)                     → QuerySet[CustomerTag]
#   can_access_customer(user, customer)           → bool
#   can_view_customer_contact(user, customer)     → bool
# =============================================================================

import logging
from accounts import access as acl

logger = logging.getLogger("crm")


def get_accessible_customers(user):
    """
    Return customers scoped to the user's accessible restaurants.

    - Superuser / staff     → all customers
    - Org-scope roles       → all customers in their org's restaurants
    - Restaurant-scope roles→ customers in their restaurant(s)
    - Branch-scope roles    → customers in the restaurant(s) of their branch(es)
    """
    from crm.models import Customer

    if not user or not user.is_authenticated or not user.is_active:
        return Customer.objects.none()

    if user.is_superuser or user.is_staff:
        return Customer.objects.all()

    accessible_restaurants = acl.get_accessible_restaurants(user)
    return Customer.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_loyalty_programs(user):
    from crm.models import LoyaltyProgram

    if not user or not user.is_authenticated or not user.is_active:
        return LoyaltyProgram.objects.none()

    if user.is_superuser or user.is_staff:
        return LoyaltyProgram.objects.all()

    accessible_restaurants = acl.get_accessible_restaurants(user)
    return LoyaltyProgram.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_rewards(user):
    from crm.models import LoyaltyReward

    if not user or not user.is_authenticated or not user.is_active:
        return LoyaltyReward.objects.none()

    if user.is_superuser or user.is_staff:
        return LoyaltyReward.objects.all()

    accessible_restaurants = acl.get_accessible_restaurants(user)
    return LoyaltyReward.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_feedback(user):
    from crm.models import CustomerFeedback

    if not user or not user.is_authenticated or not user.is_active:
        return CustomerFeedback.objects.none()

    if user.is_superuser or user.is_staff:
        return CustomerFeedback.objects.all()

    accessible_restaurants = acl.get_accessible_restaurants(user)
    return CustomerFeedback.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_segments(user):
    from crm.models import CustomerSegment

    if not user or not user.is_authenticated or not user.is_active:
        return CustomerSegment.objects.none()

    if user.is_superuser or user.is_staff:
        return CustomerSegment.objects.all()

    accessible_restaurants = acl.get_accessible_restaurants(user)
    return CustomerSegment.objects.filter(restaurant__in=accessible_restaurants)


def get_accessible_tags(user):
    from crm.models import CustomerTag

    if not user or not user.is_authenticated or not user.is_active:
        return CustomerTag.objects.none()

    if user.is_superuser or user.is_staff:
        return CustomerTag.objects.all()

    accessible_restaurants = acl.get_accessible_restaurants(user)
    return CustomerTag.objects.filter(restaurant__in=accessible_restaurants)


def can_access_customer(user, customer) -> bool:
    """Return True if user can access this specific customer."""
    return get_accessible_customers(user).filter(pk=customer.pk).exists()


def can_view_customer_contact(user, customer) -> bool:
    """Return True if user can see full PII (phone, email, address)."""
    from crm.constants import PERM_CUSTOMER_CONTACT_VIEW
    return (
        can_access_customer(user, customer)
        and acl.has_permission(user, PERM_CUSTOMER_CONTACT_VIEW)
    )
