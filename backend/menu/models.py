# =============================================================================
# RestaurantFlow — Menu Models
# Phase 5: TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch
#
# Architecture:
#   Restaurant
#       └── Menu
#             ├── TaxRate           (restaurant-scoped tax configuration)
#             ├── Category          (Veg, Non-Veg, Snacks, …)
#             └── MenuItem          (individual dish / product)
#                   ├── MenuItemPrice     (branch-specific pricing + history)
#                   └── MenuItemBranch    (branch availability + time windows)
#
# Design principles (consistent with Phases 1–4):
#   - UUID primary keys on all business models.
#   - Soft disable via is_active — never hard-delete once referenced.
#   - PROTECT foreign keys — no accidental cascade deletion.
#   - DecimalField for all monetary / rate values — never float.
#   - Slug uniqueness scoped to restaurant (not globally unique).
#   - SKU uniqueness scoped to restaurant.
#   - Price history preserved — MenuItemPrice rows are never deleted.
#   - Branch availability separate from item active status.
#   - Tax configuration is a FK reference — never duplicated into items.
#   - Category must belong to the same restaurant as the MenuItem.
#   - Branch must belong to the same restaurant as the MenuItem.
#
# Future compatibility:
#   - MenuItem carries all fields needed for order/billing snapshots.
#   - MenuItemPrice effective_from / effective_to enable date-accurate
#     price reconstruction for historical bills.
#   - TaxRate code + rate allows billing to snapshot tax at transaction time.
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models
from django.utils.text import slugify

from core.models import TimestampedModel

logger = logging.getLogger("menu")


# =============================================================================
# FoodType choices
# =============================================================================

class FoodType(models.TextChoices):
    VEG     = "VEG",     "Vegetarian"
    NON_VEG = "NON_VEG", "Non-Vegetarian"
    EGG     = "EGG",     "Egg"
    VEGAN   = "VEGAN",   "Vegan"
    OTHER   = "OTHER",   "Other"


# =============================================================================
# TaxRate
# =============================================================================

class TaxRate(TimestampedModel):
    """
    A named tax configuration record belonging to a Restaurant.

    Rate is a percentage stored as Decimal (e.g. 5.00 = 5 %).

    Design rationale:
        - Belongs to restaurant so different restaurants can have different tax
          codes without global collision.
        - Tax code is unique within a restaurant (e.g. "GST_STANDARD").
        - Future billing must snapshot the rate used at transaction time —
          this model provides the reference; the snapshot is stored on the
          bill/order line (Phase 6+).
        - Do not hard-code or assume tax rates in business logic. Always
          read from this table.

    Examples:
        code=GST_STANDARD  rate=5.00
        code=GST_REDUCED   rate=2.50
        code=ZERO_TAX      rate=0.00
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="tax_rates",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, db_index=True)
    rate = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text="Tax percentage, e.g. 5.000 = 5%.",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Tax Rate"
        verbose_name_plural = "Tax Rates"
        ordering = ["restaurant", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_taxrate_code_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "code"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.rate}%) — {self.restaurant.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.rate is not None and self.rate < 0:
            raise ValidationError({"rate": "Tax rate cannot be negative."})


# =============================================================================
# Category
# =============================================================================

class Category(TimestampedModel):
    """
    A menu category belonging to a Restaurant.

    Examples: Veg, Non-Veg, Snacks, Beverages, Desserts.

    Slug uniqueness is scoped to restaurant (two restaurants may share slugs).
    display_order controls the ordering in menus; always use explicit ordering
    rather than relying on DB insertion order.

    Do not hard-delete categories — future menu history may reference them.
    Use is_active=False to disable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="menu_categories",
    )
    name = models.CharField(max_length=150, db_index=True)
    slug = models.SlugField(max_length=150, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(
        upload_to="menu/categories/",
        null=True,
        blank=True,
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "slug"],
                name="unique_category_slug_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "display_order"]),
            models.Index(fields=["restaurant", "slug"]),
        ]

    def __str__(self):
        return f"{self.name} — {self.restaurant.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while (
                Category.objects.filter(restaurant=self.restaurant, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


# =============================================================================
# MenuItem
# =============================================================================

class MenuItem(TimestampedModel):
    """
    A single dish / product in the restaurant's catalog.

    MenuItem belongs to both a Restaurant and a Category.
    Both must belong to the same restaurant — validated in clean() and
    enforced in the serializer.

    Key fields:
        food_type       — VEG / NON_VEG / EGG / VEGAN / OTHER (controlled choices)
        sku             — Internal stock-keeping code, unique within restaurant
        slug            — URL-friendly identifier, unique within restaurant
        is_active       — Whether the item exists in the catalog
        is_available    — Global default availability flag
                          (distinct from branch-level MenuItemBranch.is_available)
        preparation_time_minutes — Used by Kitchen Display System (KDS) in Phase 7+
        tax_rate        — FK to TaxRate; never hard-code a tax percentage

    Price is NOT on this model — see MenuItemPrice for branch-specific pricing.

    Do not hard-delete — once an item is referenced by any order, it must remain
    for historical lookup. Use is_active=False.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="menu_items",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="items",
    )
    tax_rate = models.ForeignKey(
        TaxRate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="menu_items",
    )
    name = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, db_index=True)
    sku = models.CharField(max_length=100, blank=True, db_index=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=300, blank=True)
    image = models.ImageField(
        upload_to="menu/items/",
        null=True,
        blank=True,
    )
    food_type = models.CharField(
        max_length=10,
        choices=FoodType.choices,
        default=FoodType.VEG,
        db_index=True,
    )
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    # is_active: item exists in the restaurant catalog
    is_active = models.BooleanField(default=True, db_index=True)

    # is_available: restaurant-level default availability
    # (branch-level availability is controlled via MenuItemBranch)
    is_available = models.BooleanField(default=True, db_index=True)

    # Preparation time in minutes — used by KDS in future phases
    preparation_time_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Estimated preparation time in minutes.",
    )

    class Meta:
        verbose_name = "Menu Item"
        verbose_name_plural = "Menu Items"
        ordering = ["category__display_order", "display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "slug"],
                name="unique_menuitem_slug_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "category"]),
            models.Index(fields=["restaurant", "food_type"]),
            models.Index(fields=["restaurant", "slug"]),
            models.Index(fields=["restaurant", "sku"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"

    def save(self, *args, **kwargs):
        # Auto-generate slug from name if not provided
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while (
                MenuItem.objects.filter(restaurant=self.restaurant, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def clean(self):
        """
        Validate cross-model consistency:
          - category must belong to the same restaurant as the item.
          - tax_rate (if set) must belong to the same restaurant as the item.
        """
        from django.core.exceptions import ValidationError
        if self.category_id and self.restaurant_id:
            if str(self.category.restaurant_id) != str(self.restaurant_id):
                raise ValidationError(
                    {"category": "Category must belong to the same restaurant as the menu item."}
                )
        if self.tax_rate_id and self.restaurant_id:
            if str(self.tax_rate.restaurant_id) != str(self.restaurant_id):
                raise ValidationError(
                    {"tax_rate": "Tax rate must belong to the same restaurant as the menu item."}
                )


# =============================================================================
# MenuItemPrice
# =============================================================================

class MenuItemPrice(TimestampedModel):
    """
    Branch-specific pricing for a MenuItem.

    Design rationale:
        - Do NOT put a single price on MenuItem — branches may charge differently.
        - Price history is preserved via effective_from / effective_to.
          Never overwrite old rows; create a new row and set effective_to on the old.
        - is_active marks the currently applicable price for a branch.
        - Validation must ensure no two active prices overlap for the same
          menu_item + branch + time period.

    Price must be >= 0 (free items are valid, e.g. complimentary bread).

    Example:
        Chicken Biryani — LPU Campus:
            ₹220  (effective 01-Oct → 15-Oct, is_active=False after price change)
            ₹240  (effective 16-Oct → current, is_active=True)

    Financial field:
        price — DecimalField(max_digits=12, decimal_places=2)
        Never use float for monetary values.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="prices",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="menu_item_prices",
    )
    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Selling price in restaurant's currency. Must be >= 0.",
    )
    effective_from = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this price record becomes effective (inclusive).",
    )
    effective_to = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this price record expires (exclusive). NULL = still active.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is this the currently active price for this item+branch?",
    )

    class Meta:
        verbose_name = "Menu Item Price"
        verbose_name_plural = "Menu Item Prices"
        ordering = ["-effective_from", "-created_at"]
        indexes = [
            models.Index(fields=["menu_item", "branch", "is_active"]),
            models.Index(fields=["menu_item", "branch", "effective_from"]),
            models.Index(fields=["branch", "is_active"]),
        ]

    def __str__(self):
        return (
            f"{self.menu_item.name} @ {self.branch.name}: "
            f"{self.price} "
            f"({'active' if self.is_active else 'historical'})"
        )

    def clean(self):
        """
        Validate cross-model consistency:
          - branch.restaurant must equal menu_item.restaurant.
          - price must be >= 0.
        """
        from django.core.exceptions import ValidationError
        if self.price is not None and self.price < 0:
            raise ValidationError({"price": "Price cannot be negative."})
        if self.menu_item_id and self.branch_id:
            try:
                if str(self.menu_item.restaurant_id) != str(self.branch.restaurant_id):
                    raise ValidationError(
                        {
                            "branch": (
                                "Branch must belong to the same restaurant as the menu item. "
                                f"Item restaurant: {self.menu_item.restaurant.name}, "
                                f"Branch restaurant: {self.branch.restaurant.name}."
                            )
                        }
                    )
            except (MenuItem.DoesNotExist, Exception):
                pass


# =============================================================================
# MenuItemBranch
# =============================================================================

class MenuItemBranch(TimestampedModel):
    """
    Branch-specific availability record for a MenuItem.

    Purpose:
        Controls whether a specific branch currently offers a menu item.
        This is distinct from:
            MenuItem.is_active     — the item exists in the restaurant catalog
            MenuItem.is_available  — the restaurant-level default
            MenuItemBranch.is_available — this branch currently offers the item

    Time window:
        available_from / available_to are TIME fields (not datetime) for daily
        scheduling windows. Example:
            Breakfast items: available_from=07:00, available_to=11:00
            Lunch Combo:     available_from=12:00, available_to=16:00
        NULL on both fields means "available at all times of day".

    Future availability check logic (to be implemented by is_menu_item_available):
        MenuItem.is_active
            AND branch.is_active
            AND MenuItemBranch.is_available
            AND (current_time within available_from–available_to or both NULL)
            AND [inventory check — Phase 7+]

    One record per menu_item + branch (enforced by UniqueConstraint).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.PROTECT,
        related_name="branch_availability",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="menu_item_availability",
    )
    is_available = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Is this item currently available at this branch?",
    )

    # Time-of-day availability window (uses branch/restaurant timezone)
    available_from = models.TimeField(
        null=True,
        blank=True,
        help_text="Start of daily availability window (restaurant timezone). NULL = all day.",
    )
    available_to = models.TimeField(
        null=True,
        blank=True,
        help_text="End of daily availability window (restaurant timezone). NULL = all day.",
    )

    class Meta:
        verbose_name = "Menu Item Branch Availability"
        verbose_name_plural = "Menu Item Branch Availabilities"
        ordering = ["menu_item", "branch"]
        constraints = [
            models.UniqueConstraint(
                fields=["menu_item", "branch"],
                name="unique_menuitem_branch_availability",
            ),
        ]
        indexes = [
            models.Index(fields=["menu_item", "branch", "is_available"]),
            models.Index(fields=["branch", "is_available"]),
        ]

    def __str__(self):
        status = "available" if self.is_available else "unavailable"
        return f"{self.menu_item.name} @ {self.branch.name}: {status}"

    def clean(self):
        """Branch must belong to same restaurant as menu item."""
        from django.core.exceptions import ValidationError
        if self.menu_item_id and self.branch_id:
            try:
                if str(self.menu_item.restaurant_id) != str(self.branch.restaurant_id):
                    raise ValidationError(
                        {
                            "branch": (
                                "Branch must belong to the same restaurant as the menu item."
                            )
                        }
                    )
            except (MenuItem.DoesNotExist, Exception):
                pass
