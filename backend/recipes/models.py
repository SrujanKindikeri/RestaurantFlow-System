# =============================================================================
# RestaurantFlow — Recipes Models
# Phase 11: Recipe and Ingredient Consumption
#
# Model hierarchy:
#   Restaurant → MenuItem → Recipe (versioned) → RecipeItem → InventoryItem
#   Order → KitchenOrder → ConsumptionBatch → StockConsumption → StockMovement
#
# Design principles:
#   - UUID primary keys on all models.
#   - All monetary/quantity values use DecimalField — never float.
#   - Recipes are VERSIONED — historical records are never overwritten.
#   - Only one ACTIVE recipe per menu_item at a given time (enforced in service).
#   - StockConsumption is immutable after creation; reversals create new records.
#   - ConsumptionBatch groups all ingredient consumptions for one order event.
#   - Idempotency key on ConsumptionBatch prevents duplicate consumption.
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import TimestampedModel
from recipes.constants import (
    RECIPE_STATUS_CHOICES, RECIPE_DRAFT,
    BATCH_STATUS_CHOICES, BATCH_PENDING,
    CONSUMPTION_STATUS_CHOICES, CONSUMPTION_PENDING,
)

logger = logging.getLogger("recipes")


# =============================================================================
# BranchConsumptionConfig
# =============================================================================

class BranchConsumptionConfig(TimestampedModel):
    """
    Branch-level configuration for inventory consumption.

    Stores:
        - consumption_trigger: KITCHEN_STARTED or KITCHEN_COMPLETED (default)
        - default_consumption_location: the StorageLocation from which stock
          is consumed for this branch. Must be set before consumption can run.

    One config per branch. Created on demand; absence means defaults apply.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.OneToOneField(
        "organizations.Branch",
        on_delete=models.CASCADE,
        related_name="consumption_config",
    )
    consumption_trigger = models.CharField(
        max_length=25,
        default="KITCHEN_COMPLETED",
        help_text=(
            "KITCHEN_STARTED = trigger on PREPARING transition. "
            "KITCHEN_COMPLETED = trigger on READY transition (default)."
        ),
    )
    default_consumption_location = models.ForeignKey(
        "inventory.StorageLocation",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="branch_consumption_configs",
        help_text=(
            "The storage location from which stock is consumed for this branch. "
            "Must be active and belong to this branch."
        ),
    )

    class Meta:
        verbose_name = "Branch Consumption Config"
        verbose_name_plural = "Branch Consumption Configs"

    def __str__(self):
        return (
            f"Config — {self.branch.name} "
            f"[trigger={self.consumption_trigger}]"
        )


# =============================================================================
# Recipe
# =============================================================================

class Recipe(TimestampedModel):
    """
    A versioned recipe linking a MenuItem to its required ingredients.

    Versioning rules:
        - Only one recipe can be ACTIVE for a menu_item at any given time.
        - When a recipe changes, create a new version — never overwrite.
        - Historical consumption records reference the version that was used.
        - effective_from / effective_to control time-based applicability.

    Approval workflow:
        DRAFT → ACTIVE (via activate action)
        DRAFT → ARCHIVED
        ACTIVE → ARCHIVED

    The `version` field is auto-incremented per menu_item in the service layer.

    yield_quantity / yield_unit describe how much the recipe produces
    (e.g. "1 PLATE", "4 PIECES"). This is used to scale ingredient quantities
    for orders of more than one unit.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="recipes",
        db_index=True,
    )
    menu_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.PROTECT,
        related_name="recipes",
        db_index=True,
    )
    name = models.CharField(
        max_length=200,
        help_text="Human-readable recipe name, e.g. 'Chicken Biryani v2'.",
    )
    version = models.PositiveIntegerField(
        default=1,
        db_index=True,
        help_text="Auto-incremented version per menu_item. Managed by service layer.",
    )
    status = models.CharField(
        max_length=10,
        choices=RECIPE_STATUS_CHOICES,
        default=RECIPE_DRAFT,
        db_index=True,
    )

    # Yield — how much this recipe produces
    yield_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default="1.000",
        help_text="How many units this recipe produces (e.g. 1 for 1 plate).",
    )
    yield_unit = models.CharField(
        max_length=15,
        default="PIECE",
        help_text="Unit of the yield (e.g. PIECE, GRAM). From inventory UNIT_CHOICES.",
    )

    preparation_notes = models.TextField(
        blank=True,
        help_text="Optional preparation instructions visible to kitchen.",
    )

    # Effective date range — for time-based recipe resolution
    effective_from = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this recipe version becomes effective (inclusive).",
    )
    effective_to = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When this recipe version expires (exclusive). Null = no expiry.",
    )

    # Audit actors
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_recipes",
        null=True,
        blank=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_recipes",
        null=True,
        blank=True,
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Recipe"
        verbose_name_plural = "Recipes"
        ordering = ["menu_item", "-version"]
        indexes = [
            models.Index(fields=["restaurant", "menu_item"]),
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["menu_item", "status"]),
            models.Index(fields=["menu_item", "version"]),
            models.Index(fields=["status", "effective_from"]),
        ]
        constraints = [
            # Only one ACTIVE recipe per menu_item at any time
            # (partial unique constraint — DB-level guard for non-date overlap)
            models.UniqueConstraint(
                fields=["menu_item"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_recipe_per_menu_item",
            ),
        ]

    def __str__(self):
        return (
            f"{self.menu_item.name} — {self.name} "
            f"v{self.version} [{self.status}]"
        )

    @property
    def ingredient_count(self) -> int:
        return self.items.count()


# =============================================================================
# RecipeItem
# =============================================================================

class RecipeItem(TimestampedModel):
    """
    A single ingredient line in a Recipe.

    Maps: Recipe → InventoryItem with a required quantity and unit.

    preparation_loss_percentage (0–100):
        Accounts for trimming, cooking loss, etc.
        Effective consumed quantity = quantity × (1 + loss_pct / 100)

    Example:
        Recipe: Chicken Biryani
        RecipeItem: Rice, 250 GRAM, 5% loss → 262.5 g effective consumption

    Unit must be compatible with InventoryItem.default_unit (same family).
    Conversion is handled in the service layer using inventory constants.

    Uniqueness:
        (recipe, inventory_item) — one ingredient line per item per recipe.
        Validated in service; enforced at DB level.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="items",
    )
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="recipe_items",
        db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        help_text="Quantity of this ingredient per recipe yield. Must be > 0.",
    )
    unit = models.CharField(
        max_length=15,
        help_text=(
            "Unit for this recipe ingredient. Must be compatible with "
            "InventoryItem.default_unit (same measurement family)."
        ),
    )
    preparation_loss_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default="0.000",
        help_text=(
            "Percentage of additional quantity to account for preparation loss "
            "(trimming, cooking reduction, etc.). Range: 0.000–100.000."
        ),
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this ingredient's preparation.",
    )
    display_order = models.PositiveIntegerField(
        default=0,
        db_index=True,
        help_text="Controls display order in the recipe builder UI.",
    )

    class Meta:
        verbose_name = "Recipe Item"
        verbose_name_plural = "Recipe Items"
        ordering = ["display_order", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["recipe", "inventory_item"],
                name="unique_ingredient_per_recipe",
            ),
        ]
        indexes = [
            models.Index(fields=["recipe", "display_order"]),
            models.Index(fields=["inventory_item"]),
        ]

    def __str__(self):
        return (
            f"{self.inventory_item.name} × {self.quantity} {self.unit} "
            f"(loss {self.preparation_loss_percentage}%) — "
            f"{self.recipe.menu_item.name} v{self.recipe.version}"
        )

    @property
    def effective_quantity(self):
        """
        Quantity including preparation loss.
        effective = quantity × (1 + preparation_loss_percentage / 100)
        """
        from decimal import Decimal
        from recipes.constants import DECIMAL_QTY
        from decimal import ROUND_HALF_UP
        factor = Decimal("1") + (self.preparation_loss_percentage / Decimal("100"))
        return (self.quantity * factor).quantize(DECIMAL_QTY, rounding=ROUND_HALF_UP)


# =============================================================================
# ConsumptionBatch
# =============================================================================

class ConsumptionBatch(TimestampedModel):
    """
    Groups all ingredient consumption records for a single order event.

    One ConsumptionBatch is created per (order, trigger) pair.
    The idempotency_key (order_id + trigger) prevents duplicate consumption
    if the same kitchen event is delivered more than once.

    All StockConsumption records for the same batch succeed or fail together
    (atomic transaction at the service level).

    Statuses:
        PENDING     — batch created, not yet processed
        PROCESSING  — consumption in progress (short-lived; DB lock held)
        COMPLETED   — all ingredient consumptions succeeded
        FAILED      — consumption failed; failure_reason recorded
        REVERSED    — a controlled reversal has been applied
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="consumption_batches",
        db_index=True,
        null=True,
        blank=True,
        help_text="The order this batch belongs to. Null for manual consumption batches.",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="consumption_batches",
        db_index=True,
    )

    # Idempotency key — unique per (order, trigger) to prevent double-deduction
    idempotency_key = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text=(
            "Unique key preventing duplicate consumption. "
            "Format: {order_id}:{trigger_code}"
        ),
    )

    status = models.CharField(
        max_length=12,
        choices=BATCH_STATUS_CHOICES,
        default=BATCH_PENDING,
        db_index=True,
    )

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="triggered_consumption_batches",
        null=True,
        blank=True,
        help_text="The user who triggered this consumption (or null for system-triggered).",
    )
    triggered_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    failure_reason = models.TextField(
        blank=True,
        help_text="Populated when status=FAILED. Human-readable explanation.",
    )

    # Consumption trigger that created this batch
    trigger = models.CharField(
        max_length=25,
        default="KITCHEN_COMPLETED",
        help_text="Which business event triggered this batch.",
    )

    class Meta:
        verbose_name = "Consumption Batch"
        verbose_name_plural = "Consumption Batches"
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["triggered_at"]),
            models.Index(fields=["idempotency_key"]),
        ]

    def __str__(self):
        return (
            f"Batch {str(self.id)[:8]} — Order {self.order.order_number} "
            f"[{self.status}]"
        )


# =============================================================================
# StockConsumption
# =============================================================================

class StockConsumption(TimestampedModel):
    """
    An immutable record of one ingredient being consumed for one order item.

    One StockConsumption per (batch, order_item, inventory_item).

    Immutability:
        StockConsumption records are NEVER edited after creation.
        Reversals create new StockConsumption with status=REVERSED and
        a corresponding CONSUMPTION_REVERSAL StockMovement.

    Snapshot preservation:
        recipe_version is denormalized so that if the recipe changes later,
        historical records still reference what was actually consumed.

    Cost fields:
        unit_cost — authoritative average cost from InventoryItem at consumption time
        total_cost — unit_cost × quantity (in item's default_unit after conversion)

    reference_type / reference_id — generic FK to the trigger source
    (e.g. reference_type="KITCHEN_ORDER", reference_id=kitchen_order.id)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Batch grouping
    batch = models.ForeignKey(
        ConsumptionBatch,
        on_delete=models.PROTECT,
        related_name="consumptions",
        db_index=True,
    )

    # Order context
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="stock_consumptions",
        db_index=True,
        null=True,
        blank=True,
        help_text="The order this consumption belongs to. Null for manual consumption.",
    )
    order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.PROTECT,
        related_name="stock_consumptions",
        db_index=True,
        null=True,
        blank=True,
        help_text="The specific order item this consumption was generated from. Null for aggregated.",
    )

    # Restaurant / Branch scope
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="stock_consumptions",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="stock_consumptions",
        db_index=True,
    )

    # Recipe snapshot — immutable reference to the recipe version used
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.PROTECT,
        related_name="stock_consumptions",
        db_index=True,
        null=True,
        blank=True,
        help_text="Recipe used for this consumption. Null for manual consumption.",
    )
    recipe_version = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Snapshot of recipe.version at consumption time.",
    )

    # Inventory
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="stock_consumptions",
        db_index=True,
    )
    storage_location = models.ForeignKey(
        "inventory.StorageLocation",
        on_delete=models.PROTECT,
        related_name="stock_consumptions",
        db_index=True,
    )

    # Quantity in inventory item's default_unit (after unit conversion)
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        help_text="Quantity consumed in inventory_item.default_unit (after conversion).",
    )
    unit = models.CharField(
        max_length=15,
        help_text="Unit of consumed quantity — mirrors inventory_item.default_unit.",
    )

    # Cost snapshot (authoritative — never from frontend)
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text="Weighted-average cost per unit at time of consumption.",
    )
    total_cost = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default="0.00",
        help_text="unit_cost × quantity.",
    )

    status = models.CharField(
        max_length=12,
        choices=CONSUMPTION_STATUS_CHOICES,
        default=CONSUMPTION_PENDING,
        db_index=True,
    )

    consumed_at = models.DateTimeField(null=True, blank=True)
    consumed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_consumptions",
        null=True,
        blank=True,
    )

    # Generic reference to the trigger document
    reference_type = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text="e.g. KITCHEN_ORDER, MANUAL_CONSUMPTION",
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
    )

    # Link to the StockMovement created for this consumption
    stock_movement = models.OneToOneField(
        "inventory.StockMovement",
        on_delete=models.PROTECT,
        related_name="stock_consumption",
        null=True,
        blank=True,
        help_text="The StockMovement record created when this consumption was executed.",
    )

    class Meta:
        verbose_name = "Stock Consumption"
        verbose_name_plural = "Stock Consumptions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["order_item"]),
            models.Index(fields=["batch"]),
            models.Index(fields=["inventory_item", "created_at"]),
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.inventory_item.name} × {self.quantity} {self.unit} "
            f"[{self.status}] — Order {self.order.order_number}"
        )
