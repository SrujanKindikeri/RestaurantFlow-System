# =============================================================================
# RestaurantFlow — CRM Event Handlers (Notification Integration)
# Phase 17
#
# Dispatches CRM domain events to the Phase 16 Notification Center.
# All events use transaction.on_commit() and are wrapped in try/except
# so CRM notification failures NEVER affect the business transaction.
#
# Uses existing notifications.services.create_and_dispatch().
# Adds CRM-specific notification types to the notifications system.
# =============================================================================

import logging
from django.db import transaction

logger = logging.getLogger("crm")


def dispatch_loyalty_points_earned(loyalty_transaction):
    """
    Dispatch a notification when a customer earns loyalty points.
    Called after LoyaltyTransaction(EARN) is committed.
    """
    txn_pk = str(loyalty_transaction.pk)

    def _notify():
        try:
            from crm.models import LoyaltyTransaction
            from notifications.services import create_and_dispatch
            from notifications.constants import SEVERITY_LOW

            txn = LoyaltyTransaction.objects.select_related(
                "loyalty_account__customer__restaurant__organization"
            ).get(pk=txn_pk)

            customer = txn.loyalty_account.customer
            restaurant = customer.restaurant
            company = restaurant.organization

            create_and_dispatch(
                company=company,
                notification_type="CRM_LOYALTY_POINTS_EARNED",
                severity=SEVERITY_LOW,
                title="Points Earned",
                message=(
                    f"You earned {txn.points} loyalty points! "
                    f"Balance: {txn.balance_after} pts."
                ),
                source_type="LOYALTY_TRANSACTION",
                source_id=txn_pk,
                restaurant=restaurant,
                metadata={
                    "points_earned": txn.points,
                    "balance_after": txn.balance_after,
                    "customer_number": customer.customer_number,
                },
            )
        except Exception as exc:
            logger.error(
                "dispatch_loyalty_points_earned failed: txn=%s error=%s", txn_pk, exc
            )

    transaction.on_commit(_notify)


def dispatch_reward_available(loyalty_account):
    """
    Notify a customer when they have enough points for a reward.
    Called after a points earn transaction if balance crosses a reward threshold.
    """
    account_pk = str(loyalty_account.pk)

    def _notify():
        try:
            from crm.models import LoyaltyAccount, LoyaltyReward
            from notifications.services import create_and_dispatch
            from notifications.constants import SEVERITY_LOW

            account = LoyaltyAccount.objects.select_related(
                "customer__restaurant__organization",
                "loyalty_program",
            ).get(pk=account_pk)

            customer = account.customer
            restaurant = customer.restaurant

            # Check if any reward is now achievable
            available_reward = LoyaltyReward.objects.filter(
                restaurant=restaurant,
                is_active=True,
                points_required__lte=account.points_balance,
            ).order_by("points_required").first()

            if not available_reward:
                return

            create_and_dispatch(
                company=restaurant.organization,
                notification_type="CRM_REWARD_AVAILABLE",
                severity=SEVERITY_LOW,
                title="Reward Available",
                message=(
                    f"You have enough points to redeem: {available_reward.name}!"
                ),
                source_type="LOYALTY_ACCOUNT",
                source_id=account_pk,
                restaurant=restaurant,
                metadata={
                    "reward_name": available_reward.name,
                    "points_required": available_reward.points_required,
                    "current_balance": account.points_balance,
                    "customer_number": customer.customer_number,
                },
            )
        except Exception as exc:
            logger.error(
                "dispatch_reward_available failed: account=%s error=%s", account_pk, exc
            )

    transaction.on_commit(_notify)


def dispatch_feedback_submitted(feedback):
    """Notify restaurant staff when new feedback is submitted with a low rating."""
    feedback_pk = str(feedback.pk)

    def _notify():
        try:
            from crm.models import CustomerFeedback
            from notifications.services import create_and_dispatch
            from notifications.constants import SEVERITY_MEDIUM, SEVERITY_HIGH

            fb = CustomerFeedback.objects.select_related(
                "restaurant__organization", "branch"
            ).get(pk=feedback_pk)

            severity = SEVERITY_HIGH if fb.rating <= 2 else SEVERITY_MEDIUM

            create_and_dispatch(
                company=fb.restaurant.organization,
                notification_type="CRM_FEEDBACK_SUBMITTED",
                severity=severity,
                title=f"Customer Feedback — {fb.rating}/5",
                message=(
                    f"New {fb.rating}-star feedback received"
                    f"{f' at {fb.branch.name}' if fb.branch else ''}."
                    f"{' Comment: ' + fb.comment[:100] if fb.comment else ''}"
                ),
                source_type="FEEDBACK",
                source_id=feedback_pk,
                restaurant=fb.restaurant,
                branch=fb.branch,
                metadata={
                    "rating": fb.rating,
                    "feedback_id": feedback_pk,
                },
            )
        except Exception as exc:
            logger.error(
                "dispatch_feedback_submitted failed: feedback=%s error=%s",
                feedback_pk, exc,
            )

    transaction.on_commit(_notify)
