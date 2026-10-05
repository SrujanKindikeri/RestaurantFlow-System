# =============================================================================
# RestaurantFlow — Orders Models
# Phase 6: DiningTable, TableSession, OrderSequence, Order, OrderItem
#
# Architecture:
#   Branch
#       ├── DiningTable          (physical table configuration)
#       │       └── TableSession (one open session per table at a time)
#       └── Order                (DINE_IN / TAKEAWAY / COUNTER)
#               └── OrderItem    (snapshot of menu item + price + tax)
#
# Design principles (consistent with Phases 1–5):
#   - UUID primary keys on all business models.
#   - Soft disable via is_active/status — never hard-delete business records.
#   - PROTECT foreign keys — no accidental cascade deletion of history.
#   - DecimalField for all monetary values — never float.
#   - Concurrency protection via select_for_update() in service layer.
#   - DB-level partial unique constraints for session uniqueness.
#   - Price/tax snapshots stored on OrderItem — immutable after creation.
#   - OrderSequence provides concurrency-safe order number generation.
#   - Table occupancy derived from active TableSession — never a simple flag.
#
# Future compatibility:
#   - Order.status can be extended by Phase 7 (Kitchen) with ACCEPTED/PREPARING/READY/SERVED
#   - OrderItem carries all fields needed for Phase 8 (Billing) snapshots
#   - OrderSequence is reusable for any counter/branch sequence needs
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel

logger = logging.getLogger("orders")


# =============================================================================
# Table Status choices
# =============================================================================

class TableStatus(models.TextChoices):
    ACTIVE   = "ACTIVE",   "Active"
    INACTIVE = "INACTIVE", "Inactive"


# =============================================================================
# Table Session Status choices
# =============================================================================

class TableSessionStatus(models.TextChoices):
    OPEN   = "OPEN",   "Open"
    CLOSED = "CLOSED", "Closed"


# =============================================================================
# Order Type choices
# =============================================================================

class OrderType(models.TextChoices):
    DINE_IN  = "DINE_IN",  "Dine In"
    TAKEAWAY = "TAKEAWAY", "Takeaway"
    COUNTER  = "COUNTER",  "Counter"


# =============================================================================
# Order Status choices
# =============================================================================

class OrderStatus(models.TextChoices):
    DRAFT     = "DRAFT",     "Draft"
    CONFIRMED = "CONFIRMED", "Confirmed"
    CANCELLED = "CANCELLED", "Cancelled"
    # Phase 7 will extend: ACCEPTED, PREPARING, READY, SERVED, COLLECTED


# =============================================================================
# DiningTable
# =============================================================================

class DiningTable(TimestampedModel):
    """
    A physical dining table at a Branch.

    table_number is unique within a branch — two different branches may each
    have a table numbered T01.  The uniqueness constraint is at the DB level.

    Occupancy is NOT represented by a field on this model — it is derived
    from whether an active TableSession exists for this table.
    Do NOT add is_occupied=True/False here; that creates synchronisation bugs.

    Inactive tables cannot receive new orders.
    Do not hard-delete tables that have historical transaction references.
    Use status=INACTIVE to archive them.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="dining_tables",
    )

    # Human-readable identifier unique within the branch
    table_number = models.CharField(max_length=20, db_index=True)

    # Optional friendly label
    name = models.CharField(
        max_length=150,
        blank=True,
        help_text="Optional friendly name, e.g. 'Window Table', 'VIP Table'.",
    )

    # Seating capacity — must be > 0 (enforced by PositiveIntegerField + clean())
    capacity = models.PositiveIntegerField(
        default=2,
        help_text="Number of seats at this table. Must be greater than 0.",
    )

    # Section / area — e.g. Indoor, Outdoor, Terrace, AC Hall
    section = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="Area/section of the restaurant, e.g. Indoor, Outdoor, Terrace.",
    )

    # Status — ACTIVE / INACTIVE (occupancy is tracked via TableSession)
    status = models.CharField(
        max_length=20,
        choices=TableStatus.choices,
        default=TableStatus.ACTIVE,
        db_index=True,
    )

    # Display order for consistent UI ordering
    display_order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        verbose_name = "Dining Table"
        verbose_name_plural = "Dining Tables"
        ordering = ["display_order", "table_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "table_number"],
                name="unique_table_number_per_branch",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "section"]),
            models.Index(fields=["branch", "display_order"]),
            models.Index(fields=["branch", "table_number"]),
        ]

    def __str__(self):
        return f"{self.table_number} — {self.branch.name}"

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.capacity is not None and self.capacity < 1:
            raise ValidationError({"capacity": "Capacity must be greater than 0."})

    @property
    def is_active(self) -> bool:
        return self.status == TableStatus.ACTIVE

    @property
    def current_session(self):
        """Return the currently OPEN TableSession, or None."""
        return self.sessions.filter(status=TableSessionStatus.OPEN).first()

    @property
    def is_occupied(self) -> bool:
        """Derived occupancy — True if an open TableSession exists."""
        return self.sessions.filter(status=TableSessionStatus.OPEN).exists()


# =============================================================================
# TableSession
# =============================================================================

class TableSession(TimestampedModel):
    """
    One dining session at a DiningTable.

    A table session represents a group of guests occupying a table from
    opening through billing/departure.  Occupancy is derived from whether
    an OPEN TableSession exists for that table.

    Concurrency:
        Service layer uses select_for_update() + transaction.atomic().
        A partial unique DB constraint ensures only ONE open session per table.

    Historical sessions must remain available — never delete.
    Closed sessions cannot be casually edited (enforced in service layer).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(
        DiningTable,
        on_delete=models.PROTECT,
        related_name="sessions",
    )
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="opened_table_sessions",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_table_sessions",
    )

    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=TableSessionStatus.choices,
        default=TableSessionStatus.OPEN,
        db_index=True,
    )

    guest_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of guests at this table.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Table Session"
        verbose_name_plural = "Table Sessions"
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["table", "status"]),
            models.Index(fields=["opened_by", "status"]),
            models.Index(fields=["table", "opened_at"]),
        ]
        # Partial unique constraint: only ONE open session per table at any time.
        # PostgreSQL enforces this at the DB level as a partial index.
        constraints = [
            models.UniqueConstraint(
                fields=["table"],
                condition=models.Q(status="OPEN"),
                name="unique_open_session_per_table",
            ),
        ]

    def __str__(self):
        return (
            f"TableSession {self.id} | {self.table.table_number} | "
            f"{self.status} | opened by {self.opened_by.email}"
        )


# =============================================================================
# OrderSequence
# =============================================================================

class OrderSequence(TimestampedModel):
    """
    Concurrency-safe sequence counter for order number generation.

    One row per (scope_type, scope_id, date_key) where:
        scope_type  = 'counter' or 'branch'
        scope_id    = UUID of the counter or branch
        date_key    = YYYYMMDD business date string

    The `last_sequence` integer is incremented atomically using
    select_for_update() in the service layer — never MAX()+1.

    Format examples:
        Counter orders: C01-{date}-{seq:04d}  →  e.g. C01-20261003-0001
        Dine-in orders: D-{date}-{seq:04d}    →  e.g. D-20261003-0042

    The date_key allows sequences to reset daily, which is standard in
    restaurant operations.  The UUID remains the immutable PK.
    """

    SCOPE_COUNTER = "counter"
    SCOPE_BRANCH  = "branch"

    SCOPE_CHOICES = [
        (SCOPE_COUNTER, "Counter"),
        (SCOPE_BRANCH,  "Branch"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    scope_type = models.CharField(
        max_length=20,
        choices=SCOPE_CHOICES,
        db_index=True,
    )
    # UUID of the counter or branch this sequence belongs to (stored as char for flexibility)
    scope_id = models.CharField(max_length=50, db_index=True)

    # Business date string e.g. '20261003' — allows daily reset
    date_key = models.CharField(max_length=8, db_index=True)

    # The last issued sequence number — incremented atomically
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Order Sequence"
        verbose_name_plural = "Order Sequences"
        ordering = ["scope_type", "scope_id", "date_key"]
        constraints = [
            models.UniqueConstraint(
                fields=["scope_type", "scope_id", "date_key"],
                name="unique_order_sequence",
            ),
        ]
        indexes = [
            models.Index(fields=["scope_type", "scope_id", "date_key"]),
        ]

    def __str__(self):
        return f"{self.scope_type}:{self.scope_id} [{self.date_key}] seq={self.last_sequence}"


# =============================================================================
# Order
# =============================================================================

class Order(TimestampedModel):
    """
    A transaction order in the system.

    Order types:
        DINE_IN  — table required, counter not required
        TAKEAWAY — counter required, table not required
        COUNTER  — counter required, table not required

    The order_number is human-readable and immutable after creation.
    Never use it as a PK — use the UUID id.

    Status lifecycle (Phase 6):
        DRAFT → CONFIRMED → (future ACCEPTED → PREPARING → READY → SERVED)
        DRAFT → CANCELLED
        CONFIRMED → CANCELLED (requires stronger permission)

    Cross-model validation (enforced in service layer):
        - table.branch == order.branch
        - counter.branch == order.branch
        - counter_session.counter.branch == order.branch
        - table_session.table.branch == order.branch
        - assigned_waiter must have access to order.branch
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="orders",
        db_index=True,
    )

    # Human-readable order number — immutable after creation
    order_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Human-readable order number. Immutable once set.",
    )

    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.DINE_IN,
        db_index=True,
    )

    # DINE_IN fields — required for DINE_IN, null for others
    table = models.ForeignKey(
        DiningTable,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    table_session = models.ForeignKey(
        TableSession,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )

    # COUNTER / TAKEAWAY fields — required for those types, null for DINE_IN
    counter = models.ForeignKey(
        "counters.Counter",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )
    counter_session = models.ForeignKey(
        "counters.CounterSession",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="orders",
    )

    # Actors
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_orders",
    )
    assigned_waiter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_orders",
    )

    # Guest count — relevant primarily for DINE_IN
    guest_count = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
        db_index=True,
    )

    notes = models.TextField(blank=True)

    # Lifecycle timestamps
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancelled_orders",
    )
    cancellation_reason = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Phase 17 — CRM: Optional customer link
    # Null for anonymous/guest orders. Existing orders are unaffected.
    # Do NOT make this mandatory — guest orders must keep working.
    # -------------------------------------------------------------------------
    customer = models.ForeignKey(
        "crm.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        help_text=(
            "Optional CRM customer link. Null for anonymous/guest orders. "
            "Never required — POS can create orders without a customer."
        ),
    )

    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "order_type"]),
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["order_number"]),
            models.Index(fields=["table", "status"]),
            models.Index(fields=["counter", "status"]),
            models.Index(fields=["assigned_waiter", "status"]),
            models.Index(fields=["created_by", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["customer", "created_at"]),
        ]

    def __str__(self):
        return f"{self.order_number} [{self.order_type}] {self.status} — {self.branch.name}"

    @property
    def item_count(self) -> int:
        return self.items.count()


# =============================================================================
# OrderItem
# =============================================================================

class OrderItem(TimestampedModel):
    """
    A single line item in an Order.

    Price and tax information is SNAPSHOTTED at the time of order item creation.
    This ensures that future menu price changes do not retroactively alter
    historical orders.

    The frontend sends:
        menu_item_id, quantity, notes

    The backend resolves:
        MenuItem → BranchPrice → TaxRate → snapshots everything

    Never trust price or tax values from the frontend.

    Quantity must be > 0.  DecimalField allows fractional quantities (e.g.
    for items sold by weight) while PositiveIntegerField would be too restrictive.
    Use max_digits=7, decimal_places=3 to handle e.g. 1000.000 kg.

    Future Kitchen (Phase 7):
        OrderItem.menu_item.preparation_time_minutes is available for KDS scheduling.

    Future Billing (Phase 8):
        All snapshot fields are immutable once set — billing phase reads them as-is.

    Future Inventory (Phase 9):
        MenuItem → Recipe/BOM → Inventory consumption will process confirmed orders.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,   # Items are subordinate to the order
        related_name="items",
    )
    menu_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.PROTECT,   # Never cascade-delete items because of menu changes
        related_name="order_items",
    )

    # -------------------------------------------------------------------------
    # Immutable snapshots — set at creation, never updated
    # -------------------------------------------------------------------------
    item_name_snapshot = models.CharField(
        max_length=200,
        help_text="Name of the item at the time of order. Immutable.",
    )
    sku_snapshot = models.CharField(
        max_length=100,
        blank=True,
        help_text="SKU of the item at the time of order. Blank if item had no SKU.",
    )
    unit_price_snapshot = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Price per unit at the time of order. Immutable after creation.",
    )
    tax_rate_snapshot = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default="0.000",
        help_text="Tax rate % at the time of order, e.g. 5.000 = 5%. Immutable.",
    )
    tax_code_snapshot = models.CharField(
        max_length=50,
        blank=True,
        help_text="Tax code at the time of order, e.g. GST_STANDARD. Immutable.",
    )

    # -------------------------------------------------------------------------
    # Mutable while order is DRAFT
    # -------------------------------------------------------------------------
    quantity = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Quantity ordered. Must be > 0.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Order Item"
        verbose_name_plural = "Order Items"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["order", "menu_item"]),
            models.Index(fields=["menu_item"]),
        ]

    def __str__(self):
        return f"{self.item_name_snapshot} x{self.quantity} — Order {self.order.order_number}"

    def clean(self):
        from django.core.exceptions import ValidationError
        from decimal import Decimal
        if self.quantity is not None and self.quantity <= Decimal("0"):
            raise ValidationError({"quantity": "Quantity must be greater than 0."})

    @property
    def line_total(self):
        """Convenience: quantity × unit_price_snapshot. Not the billing total."""
        from decimal import Decimal
        if self.quantity is not None and self.unit_price_snapshot is not None:
            return self.quantity * self.unit_price_snapshot
        return Decimal("0.00")
