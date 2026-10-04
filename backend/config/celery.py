# =============================================================================
# RestaurantFlow — Celery Application
# Phase 16: Notification & Communication Center
#
# This file creates the Celery application instance that is used for
# asynchronous task execution (notification delivery, retries, cleanup).
#
# Usage:
#   Start worker:  celery -A config worker -l info
#   Start beat:    celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
# =============================================================================

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("restaurantflow")

# Use Django settings for all Celery configuration.
# CELERY_* prefixed settings in settings.py are loaded automatically.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """A simple debug task to verify Celery is working."""
    print(f"Request: {self.request!r}")
