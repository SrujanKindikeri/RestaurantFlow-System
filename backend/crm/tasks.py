# =============================================================================
# RestaurantFlow — CRM Celery Tasks
# Phase 17
#
# All tasks are idempotent — calling them multiple times produces the same
# result without side effects.
#
# Tasks:
#   refresh_customer_statistics       — update computed stats for one customer
#   run_segmentation_for_restaurant   — evaluate all segments for a restaurant
#   expire_loyalty_points             — run point expiry for all eligible accounts
#   cleanup_expired_redemptions       — mark expired redemptions as EXPIRED
# =============================================================================

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("crm")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    name="crm.refresh_customer_statistics",
    ignore_result=True,
)
def refresh_customer_statistics(self, customer_id: str):
    """
    Refresh backend-authoritative statistics for a single customer.
    Called after order confirmation, bill finalization, etc.
    """
    try:
        from crm.models import Customer
        from crm.customer_services import CustomerStatisticsService

        try:
            customer = Customer.objects.get(pk=customer_id, is_active=True)
        except Customer.DoesNotExist:
            logger.warning("refresh_customer_statistics: customer %s not found", customer_id)
            return

        CustomerStatisticsService.refresh_statistics(customer)
        logger.debug("refresh_customer_statistics: updated customer=%s", customer_id)

    except Exception as exc:
        logger.error(
            "refresh_customer_statistics failed: customer=%s error=%s",
            customer_id, exc,
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    name="crm.run_segmentation_for_restaurant",
    ignore_result=True,
)
def run_segmentation_for_restaurant(self, restaurant_id: str):
    """
    Run customer segmentation evaluation for all active customers
    in a restaurant. Scheduled periodically or triggered on demand.
    """
    try:
        from organizations.models import Restaurant
        from crm.segmentation_services import CustomerSegmentationService

        try:
            restaurant = Restaurant.objects.get(pk=restaurant_id, is_active=True)
        except Restaurant.DoesNotExist:
            logger.warning(
                "run_segmentation_for_restaurant: restaurant %s not found", restaurant_id
            )
            return

        result = CustomerSegmentationService.evaluate_restaurant(restaurant)
        logger.info(
            "run_segmentation_for_restaurant: restaurant=%s result=%s",
            restaurant_id, result,
        )

    except Exception as exc:
        logger.error(
            "run_segmentation_for_restaurant failed: restaurant=%s error=%s",
            restaurant_id, exc,
        )
        raise self.retry(exc=exc)


@shared_task(
    name="crm.expire_loyalty_points",
    ignore_result=True,
)
def expire_loyalty_points():
    """
    Periodic task: find loyalty accounts with expiring points and create
    EXPIRY transactions. Idempotent — uses date-keyed reference IDs.

    Only runs for programs with point_expiry_days configured.
    Processed in batches to avoid memory issues on large datasets.
    """
    from crm.models import LoyaltyAccount, LoyaltyProgram
    from crm.loyalty_services import LoyaltyService
    from crm.constants import LOYALTY_EXPIRY_BATCH_SIZE
    from django.db.models import Q

    now = timezone.now()
    processed = 0
    expired_count = 0

    # Find programs with expiry configured
    programs_with_expiry = LoyaltyProgram.objects.filter(
        is_active=True,
        point_expiry_days__isnull=False,
    )

    for program in programs_with_expiry:
        # Find accounts where the oldest unspent points have expired
        # Simplified: expire accounts where last earning was > point_expiry_days ago
        expiry_cutoff = now - timezone.timedelta(days=program.point_expiry_days)

        accounts = (
            LoyaltyAccount.objects.filter(
                loyalty_program=program,
                points_balance__gt=0,
            )
            .select_related("customer")
        )

        for account in accounts.iterator(chunk_size=LOYALTY_EXPIRY_BATCH_SIZE):
            try:
                # Check last EARN transaction date
                last_earn = account.transactions.filter(
                    transaction_type="EARN"
                ).order_by("-created_at").first()

                if last_earn and last_earn.created_at < expiry_cutoff:
                    txn = LoyaltyService.expire_points(
                        loyalty_account=account,
                        points=account.points_balance,
                        reason=f"Points expired after {program.point_expiry_days} days",
                    )
                    if txn:
                        expired_count += 1

                processed += 1
            except Exception as exc:
                logger.error(
                    "expire_loyalty_points: account=%s error=%s", account.pk, exc
                )

    logger.info(
        "expire_loyalty_points: processed=%d expired=%d", processed, expired_count
    )


@shared_task(
    name="crm.cleanup_expired_redemptions",
    ignore_result=True,
)
def cleanup_expired_redemptions():
    """
    Mark CONFIRMED redemptions that have passed their expires_at as EXPIRED.
    """
    from crm.models import RewardRedemption
    from crm.constants import REDEMPTION_CONFIRMED, REDEMPTION_EXPIRED

    now = timezone.now()
    updated = RewardRedemption.objects.filter(
        status=REDEMPTION_CONFIRMED,
        expires_at__lt=now,
    ).update(status=REDEMPTION_EXPIRED)

    if updated:
        logger.info("cleanup_expired_redemptions: expired %d redemptions", updated)


@shared_task(
    name="crm.run_segmentation_all_restaurants",
    ignore_result=True,
)
def run_segmentation_all_restaurants():
    """
    Periodic beat task: trigger segmentation for every active restaurant.
    Each restaurant is processed in its own sub-task to isolate failures.
    """
    from organizations.models import Restaurant

    for restaurant in Restaurant.objects.filter(is_active=True).values_list("pk", flat=True):
        run_segmentation_for_restaurant.delay(str(restaurant))
