# =============================================================================
# RestaurantFlow — Kitchen Models
# Phase 7: KitchenOrder, KitchenOrderItem
#
# Architecture:
#   Order (Phase 6, source of truth for the transaction)
#       └── KitchenOrder  (kitchen execution workflow — separate state machine)
#               └── KitchenOrderItem  (item-level preparation status)
#
# Design principles:
#   - Kitchen state is SEPARATE from Order status.
#     Order.status = transaction lifecycle (DRAFT / CONFIRMED / CANCELLED).
#     KitchenOrder.status = kitchen execution (NEW / ACCEPTED / PREPARING / READY / CANCELLED).
#   - UUID primary keys.
#   - PROTECT foreign keys — never delete kitchen history.
#   - OneToOne Order → KitchenOrder enforces one kitchen record per order.
#   - State machine transitions are validated in the service layer.
#   - Timestamps capture every state transition for audit/analytics.
#   - Item-level status supports partial completion workflows.
#   - Snapshots from Phase 6 OrderItem are copied — never overwritten.
#   - Financial data (price, tax) is intentionally NOT exposed here.
#
# Future-proofing:
#   - station field on KitchenOrderItem is nullable — can be used when
#     kitchen stations (Grill, Beverage, etc.) are introduced in future phases.
#   - Priority field supports NORMAL / HIGH / URGENT urgency classification.
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel

logger = logging.getLogger("kitchen")


# =============================================================================
# Kitchen Order Status
# =============================================================================

class KitchenOrderStatus(models.TextChoices):
    NEW        = "NEW",        "New"
    ACCEPTED   = "ACCEPTED",   "Accepted"
    PREPARING  = "PREPARING",  "Preparing"
    READY      = "READY",      "Ready"
    CANCELLED  = "CANCELLED",  "Cancelled"


# =============================================================================
# Kitchen Item Status
# =============================================================================

class KitchenItemStatus(models.TextChoices):
    NEW       = "NEW",       "New"
    PREPARING = "PREPARING", "Preparing"
    READY     = "READY",     "Ready"
    CANCELLED = "CANCELLED", "Cancelled"


# =============================================================================
# Kitchen Priority
# =============================================================================

class KitchenPriority(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    HIGH   = "HIGH",   "High"
    URGENT = "URGENT", "Urgent"


# =============================================================================
# Valid State Transitions
# =============================================================================

KITCHEN_ORDER_TRANSITIONS: dict[str, list[str]] = {
    KitchenOrderStatus.NEW:       [KitchenOrderStatus.ACCEPTED, KitchenOrderStatus.CANCELLED],
    KitchenOrderStatus.ACCEPTED:  [KitchenOrderStatus.PREPARING, KitchenOrderStatus.CANCELLED],
    KitchenOrderStatus.PREPARING: [KitchenOrderStatus.READY, KitchenOrderStatus.CANCELLED],
    KitchenOrderStatus.READY:     [],   # terminal — no normal transitions
    KitchenOrderStatus.CANCELLED: [],   # terminal — no normal transitions
}

KITCHEN_ITEM_TRANSITIONS: dict[str, list[str]] = {
    KitchenItemStatus.NEW:       [KitchenItemStatus.PREPARING, KitchenItemStatus.CANCELLED],
    KitchenItemStatus.PREPARING: [KitchenItemStatus.READY, KitchenItemStatus.CANCELLED],
    KitchenItemStatus.READY:     [],
    KitchenItemStatus.CANCELLED: [],
}


# =============================================================================
# KitchenOrder
# =============================================================================

class KitchenOrder(TimestampedModel):
    """
    Kitchen-side representation of a confirmed order.

    One KitchenOrder is created per confirmed Order.  The original Order
    remains the authoritative transaction record.  This model captures only
    the kitchen preparation workflow.

    State machine (enforced in services.py):
        NEW → ACCEPTED → PREPARING → READY
        NEW → CANCELLED
        ACCEPTED → CANCELLED
        PREPARING → CANCELLED

    Rules:
        1. KitchenOrder must reference a CONFIRMED Order.
        2. DRAFT or CANCELLED orders must not enter the kitchen.
        3. Branch must match the original order's branch.
        4. No duplicate kitchen records per order (OneToOne enforced at DB level).

    Timestamps capture every meaningful state transition for KDS display
    and future audit/analytics.

    Financial data is intentionally absent — kitchen does not handle payments.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="kitchen_order",
        help_text="The source confirmed order. OneToOne prevents duplicate kitchen records.",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="kitchen_orders",
        db_index=True,
        help_text="Denormalized branch reference for efficient KDS queries.",
    )

    status = models.CharField(
        max_length=20,
        choices=KitchenOrderStatus.choices,
        default=KitchenOrderStatus.NEW,
        db_index=True,
    )

    priority = models.CharField(
        max_length=10,
        choices=KitchenPriority.choices,
        default=KitchenPriority.NORMAL,
        db_index=True,
    )

    kitchen_note = models.TextField(
        blank=True,
        help_text="Optional note from kitchen manager visible on KDS.",
    )

    # -------------------------------------------------------------------------
    # Lifecycle timestamps — nullable, set when each transition occurs
    # -------------------------------------------------------------------------
    received_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this kitchen order was received (created).",
    )
    accepted_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When kitchen accepted this order.",
    )
    started_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When kitchen started preparing this order.",
    )
    ready_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When all items were ready.",
    )
    cancelled_at = models.DateTimeField(
        null=True, blank=True,
    )

    # -------------------------------------------------------------------------
    # Actors — who performed each state transition
    # -------------------------------------------------------------------------
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="kitchen_orders_accepted",
    )
    started_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="kitchen_orders_started",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="kitchen_orders_completed",
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="kitchen_orders_cancelled",
    )

    cancellation_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Kitchen Order"
        verbose_name_plural = "Kitchen Orders"
        ordering = ["received_at"]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "priority"]),
            models.Index(fields=["branch", "received_at"]),
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["status", "received_at"]),
            models.Index(fields=["branch", "status", "received_at"]),
        ]

    def __str__(self):
        return (
            f"KO-{self.order.order_number} [{self.status}] — {self.branch.name}"
        )

    def can_transition_to(self, new_status: str) -> bool:
        """Return True if the state machine allows this transition."""
        return new_status in KITCHEN_ORDER_TRANSITIONS.get(self.status, [])

    @property
    def order_number(self) -> str:
        return self.order.order_number

    @property
    def order_type(self) -> str:
        return self.order.order_type

    @property
    def age_seconds(self) -> float:
        """Seconds since this kitchen order was received (from received_at)."""
        from django.utils import timezone
        return (timezone.now() - self.received_at).total_seconds()


# =============================================================================
# KitchenOrderItem
# =============================================================================

class KitchenOrderItem(TimestampedModel):
    """
    Item-level kitchen preparation status.

    Each KitchenOrderItem maps to one OrderItem from Phase 6.
    Snapshots (name, quantity, notes) are copied from the OrderItem at creation
    and never overwritten — ensuring the kitchen always sees the original order
    details even if future edits were theoretically possible.

    Financial snapshots (unit_price, tax_rate) are intentionally NOT copied —
    kitchen staff do not need pricing information.

    Item-level status supports partial completion:
        Cold Coffee → READY  while  Chicken Biryani → PREPARING
    The parent KitchenOrder remains PREPARING until all non-cancelled items
    are READY.

    state machine (enforced in services.py):
        NEW → PREPARING → READY
        NEW → CANCELLED
        PREPARING → CANCELLED

    Future kitchen stations:
        The `station` field is nullable and can be set when a menu item is
        mapped to a specific kitchen station (Grill, Cold, Beverage, etc.).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    kitchen_order = models.ForeignKey(
        KitchenOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    order_item = models.OneToOneField(
        "orders.OrderItem",
        on_delete=models.PROTECT,
        related_name="kitchen_item",
        help_text="Source Phase 6 OrderItem. Snapshots copied at creation.",
    )
    menu_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.PROTECT,
        related_name="kitchen_items",
        help_text="FK kept for future station routing. Snapshot preserved below.",
    )

    # -------------------------------------------------------------------------
    # Snapshots copied from OrderItem at creation — immutable in kitchen
    # -------------------------------------------------------------------------
    item_name_snapshot = models.CharField(
        max_length=200,
        help_text="Name copied from OrderItem.item_name_snapshot at creation.",
    )
    quantity = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Quantity copied from OrderItem at creation.",
    )
    notes = models.TextField(
        blank=True,
        help_text="Preparation notes copied from OrderItem.notes at creation.",
    )
    food_type = models.CharField(
        max_length=10,
        blank=True,
        help_text="VEG/NON_VEG/EGG/VEGAN/OTHER — copied from MenuItem.food_type.",
    )
    preparation_time_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Estimated prep time — copied from MenuItem.preparation_time_minutes.",
    )

    status = models.CharField(
        max_length=20,
        choices=KitchenItemStatus.choices,
        default=KitchenItemStatus.NEW,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Future: kitchen station routing (nullable until stations are configured)
    # -------------------------------------------------------------------------
    station = models.CharField(
        max_length=100,
        blank=True,
        help_text=(
            "Optional kitchen station (Grill, Beverage, Cold, etc.). "
            "Nullable until kitchen station management is implemented."
        ),
    )

    # -------------------------------------------------------------------------
    # Lifecycle timestamps
    # -------------------------------------------------------------------------
    started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Kitchen Order Item"
        verbose_name_plural = "Kitchen Order Items"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["kitchen_order", "status"]),
            models.Index(fields=["menu_item", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"{self.item_name_snapshot} × {self.quantity} "
            f"[{self.status}] — KO-{self.kitchen_order.order_number}"
        )

    def can_transition_to(self, new_status: str) -> bool:
        """Return True if the state machine allows this transition."""
        return new_status in KITCHEN_ITEM_TRANSITIONS.get(self.status, [])
