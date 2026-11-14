# =============================================================================
# RestaurantFlow — Observability Celery Tasks
# Phase 24
#
# Lightweight periodic tasks that push monitoring data into the in-process
# metrics registry. No business logic; never block.
# =============================================================================

from celery import shared_task
import logging

logger = logging.getLogger("observability.tasks")


@shared_task(name="observability.tasks.update_celery_queue_depths", ignore_result=True)
def update_celery_queue_depths():
    """Update the celery_queue_depth gauge for each configured queue."""
    try:
        from observability.celery_signals import update_queue_depths
        update_queue_depths()
    except Exception as exc:
        logger.debug("update_celery_queue_depths failed: %s", exc)
