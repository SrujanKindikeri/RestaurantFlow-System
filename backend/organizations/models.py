# =============================================================================
# RestaurantFlow — Organizations Models
# Phase 2: Organization → Restaurant → Branch hierarchy
#
# Hierarchy:
#   Organization  (company / legal entity)
#       └── Restaurant  (a restaurant brand operated by the organization)
#               └── Branch  (a physical location of the restaurant)
#
# Design principles:
#   - UUID primary keys on all business entities (never expose integer IDs).
#   - Soft disable via `is_active` — never hard-delete business records.
#   - PROTECT foreign keys — no accidental cascade deletion of history.
#   - TimestampedModel provides created_at / updated_at on every model.
#   - UniqueConstraints enforce business invariants at the DB level.
#   - All slug fields are unique within their natural scope.
#   - Settings models use OneToOne for a clean 1:1 config pattern.
# =============================================================================

import uuid
import logging

from django.db import models
from django.utils.text import slugify

from core.models import TimestampedModel

logger = logging.getLogger("organizations")


# =============================================================================
# Organization
# =============================================================================

class Organization(TimestampedModel):
    """
    Represents a company or legal entity that owns and operates restaurants
    within RestaurantFlow.

    One Organization → many Restaurants → many Branches.

    Phase 3 will link Users to Organizations for scoped access control.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    legal_name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)

    # Contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default="India")
    postal_code = models.CharField(max_length=20, blank=True)

    # Business details
    tax_id = models.CharField(max_length=100, blank=True)
    currency = models.CharField(max_length=10, default="INR")
    timezone = models.CharField(max_length=50, default="Asia/Kolkata")

    # Status — soft disable, never hard delete
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not provided
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Organization.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def restaurant_count(self):
        return self.restaurants.count()

    @property
    def active_restaurant_count(self):
        return self.restaurants.filter(is_active=True).count()


# =============================================================================
# Restaurant
# =============================================================================

class Restaurant(TimestampedModel):
    """
    A restaurant brand operated by an Organization.

    One Restaurant → many Branches.
    One Restaurant ── 1 RestaurantSettings.

    The `code` field is a short human-readable identifier (e.g. SPICE-001)
    unique within the owning organization.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,       # Never accidentally delete an org with restaurants
        related_name="restaurants",
    )
    name = models.CharField(max_length=255, db_index=True)
    slug = models.SlugField(max_length=255, db_index=True)
    code = models.CharField(max_length=50, db_index=True)
    description = models.TextField(blank=True)

    # Contact
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Status
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                name="unique_restaurant_code_per_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "slug"],
                name="unique_restaurant_slug_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "code"]),
            models.Index(fields=["organization", "slug"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while (
                Restaurant.objects.filter(organization=self.organization, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def branch_count(self):
        return self.branches.count()

    @property
    def active_branch_count(self):
        return self.branches.filter(is_active=True).count()


# =============================================================================
# Branch
# =============================================================================

class Branch(TimestampedModel):
    """
    A physical location of a Restaurant.

    One Branch ── 1 BranchSettings.
    The `code` is unique within its parent restaurant (e.g. SG-LPU).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        Restaurant,
        on_delete=models.PROTECT,       # Never cascade-delete branches
        related_name="branches",
    )
    name = models.CharField(max_length=255, db_index=True)
    code = models.CharField(max_length=50, db_index=True)

    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)

    # Contact
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)

    # Geolocation (optional — useful for future map/delivery features)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )

    # Status
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Branch"
        verbose_name_plural = "Branches"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_branch_code_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "code"]),
        ]

    def __str__(self):
        return f"{self.name} — {self.restaurant.name}"


# =============================================================================
# RestaurantSettings
# =============================================================================

class RestaurantSettings(TimestampedModel):
    """
    Per-restaurant configuration.

    OneToOne with Restaurant.  Created automatically when a restaurant is
    created (via signal or explicit save in the view).  Future phases will
    extend this with menu, tax, and receipt configuration.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.OneToOneField(
        Restaurant,
        on_delete=models.CASCADE,       # Settings are subordinate to the restaurant
        related_name="settings",
    )

    # Localisation overrides (falls back to Organization values if blank)
    currency = models.CharField(max_length=10, blank=True, default="")
    timezone = models.CharField(max_length=50, blank=True, default="")

    # Tax
    tax_enabled = models.BooleanField(default=True)
    default_tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00
    )

    # Receipt
    receipt_header = models.TextField(blank=True)
    receipt_footer = models.TextField(blank=True)

    # Inventory behaviour
    allow_negative_stock = models.BooleanField(default=False)

    # Order prefix (e.g. "ORD-") — used by future order generation
    order_prefix = models.CharField(max_length=20, default="ORD")

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Restaurant Settings"
        verbose_name_plural = "Restaurant Settings"

    def __str__(self):
        return f"Settings — {self.restaurant.name}"


# =============================================================================
# BranchSettings
# =============================================================================

class BranchSettings(TimestampedModel):
    """
    Per-branch operational configuration.

    OneToOne with Branch.  Kept intentionally minimal in Phase 2.
    Future phases (Counters, POS, Delivery) will extend this.
    """

    ORDER_TYPE_DINE_IN = "dine_in"
    ORDER_TYPE_TAKEAWAY = "takeaway"
    ORDER_TYPE_DELIVERY = "delivery"

    ORDER_TYPE_CHOICES = [
        (ORDER_TYPE_DINE_IN, "Dine In"),
        (ORDER_TYPE_TAKEAWAY, "Takeaway"),
        (ORDER_TYPE_DELIVERY, "Delivery"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.OneToOneField(
        Branch,
        on_delete=models.CASCADE,
        related_name="settings",
    )

    # Operating hours
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)

    # POS defaults
    default_order_type = models.CharField(
        max_length=20,
        choices=ORDER_TYPE_CHOICES,
        default=ORDER_TYPE_DINE_IN,
    )

    # Receipt
    receipt_footer = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Branch Settings"
        verbose_name_plural = "Branch Settings"

    def __str__(self):
        return f"Settings — {self.branch.name}"
