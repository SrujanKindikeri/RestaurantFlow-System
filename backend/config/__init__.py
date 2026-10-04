# RestaurantFlow config package
#
# Expose the Celery application so that Django apps loaded via autodiscover
# can use `from celery import current_app` or `@shared_task` correctly.

from .celery import app as celery_app  # noqa: F401

__all__ = ("celery_app",)
