# =============================================================================
# RestaurantFlow — Core Models
# Phase 1: No business models yet.
# Future phases will add shared abstract base models here.
# =============================================================================

from django.db import models


class TimestampedModel(models.Model):
    """
    Abstract base model providing created_at / updated_at timestamps.
    All future RestaurantFlow models should inherit from this.
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
