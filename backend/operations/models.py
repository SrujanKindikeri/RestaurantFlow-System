# =============================================================================
# RestaurantFlow — Operations Models
# Phase 19: Advanced POS & Restaurant Operations
#
# Models:
#   POSDevice              — registered POS hardware (metadata only)
#   POSSession             — active POS session within a CounterSession
#   MenuModifierGroup      — grouping of modifier options (Size, Toppings, etc.)
#   MenuModifierOption     — individual modifier option with price_adjustment
#   OrderItemModifier      — applied modifier on an OrderItem
#   OrderFulfillmentStatus — serving-state tracker for an Order
#   OrderChangeRequest     — controlled post-confirm order edit workflow
#   TableFloorPlan         — floor-plan layout metadata for DiningTable
#   TableTransfer          — table-to-table order transfer record
#   TableMerge             — multi-table merge record
#   OrderMergeRequest      — order combination workflow
#   BillSplit              — one portion of a split bill
#   BillSplitItem          — item allocation within a BillSplit
#   ReceiptPrintLog        — immutable print/reprint audit trail
#   OperationalShift       — branch-level shift (morning/evening/night)
#   ShiftHandoverNote      — shift-closing notes for handover
#   OperationsAuditLog     — append-only operations audit trail
#
# Design principles:
#   - UUID PKs on all business models.
#   - TimestampedModel base for created_at / updated_at.
#   - PROTECT FKs — no accidental cascade deletion.
#   - DecimalField for all monetary values — never float.
#   - Concurrency via select_for_update() in service layer.
#   - Never duplicate: Order, Bill, Payment, KitchenOrder, Customer, Counter,
#     CounterSession, DiningTable, TableSession.
#   - Extend existing models safely (e.g. Order.status gains ON_HOLD).
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel
from operations.constants import (
    POS_SESSION_STATUS_CHOICES, POS_SESSION_ACTIVE,
    DEVICE_TYPE_CHOICES, DEVICE_TABLET,
    ORDER_CHANGE_TYPE_CHOICES, ORDER_CHANGE_STATUS_CHOICES,
    CHANGE_STATUS_PENDING,
    TABLE_TRANSFER_STATUS_CHOICES, TRANSFER_REQUESTED,
    TABLE_MERGE_STATUS_CHOICES, MERGE_REQUESTED,
    ORDER_MERGE_STATUS_CHOICES, ORDER_MERGE_PENDING,
    BILL_SPLIT_TYPE_CHOICES, BILL_SPLIT_STATUS_CHOICES, SPLIT_DRAFT,
    RECEIPT_PRINT_TYPE_CHOICES, PRINT_ORIGINAL,
    OPERATIONAL_SHIFT_TYPE_CHOICES, SHIFT_MORNING,
    OPERATIONAL_SHIFT_STATUS_CHOICES, OP_SHIFT_OPEN,
    HANDOVER_NOTE_TYPE_CHOICES, HANDOVER_PRIORITY_CHOICES,
    HANDOVER_GENERAL, PRIORITY_NORMAL,
    TABLE_OPERATIONAL_STATUS_CHOICES, TABLE_SHAPE_CHOICES,
    TABLE_OP_AVAILABLE,
    ORDER_FULFILLMENT_STATUS_CHOICES, FULFILLMENT_CONFIRMED,
    AUDIT_EVENT_CHOICES,
)

logger = logging.getLogger("operations")


# =============================================================================
# POSDevice
# =============================================================================

class POSDevice(TimestampedModel):
    """
    A registered POS hardware device.

    device_identifier is operational metadata ONLY. It is NEVER used for
    authorization. All authorization uses User + Role + Permission + Scope.

    Devices are registered to a specific branch counter so floor managers
    know which physical station is which. is_active is set False to retire
    a device without deleting historical records.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="pos_devices",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="pos_devices",
        db_index=True,
    )
    counter = models.ForeignKey(
        "counters.Counter",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="pos_devices",
    )

    device_name = models.CharField(max_length=150)
    device_identifier = models.CharField(
        max_length=200,
        db_index=True,
        help_text="Browser fingerprint / device UUID — NEVER used for authorization.",
    )
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPE_CHOICES,
        default=DEVICE_TABLET,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="registered_pos_devices",
    )

    class Meta:
        verbose_name = "POS Device"
        verbose_name_plural = "POS Devices"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["device_identifier"]),
        ]

    def __str__(self):
        return f"{self.device_name} [{self.device_type}] — {self.branch.name}"


# =============================================================================
# POSSession
# =============================================================================

class POSSession(TimestampedModel):
    """
    An active POS session belonging to a CounterSession.

    Relationship:
        Counter → CounterSession → POSSession

    A POSSession does NOT replace CounterSession. It represents the
    POS application session for a specific user at a specific device.
    Multiple POSSessions may exist under one CounterSession (shift
    handovers, break resumptions, etc.).

    Status:
        ACTIVE  — currently active; user is operating POS
        PAUSED  — user stepped away; session locked but not ended
        ENDED   — session formally closed

    Security:
        The backend validates counter.branch == request.user's authorized branch.
        device_identifier is metadata only — never trusted for auth.

    Concurrency:
        Only ONE ACTIVE POSSession per (counter + user) at a time.
        Enforced via a partial unique constraint.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    counter = models.ForeignKey(
        "counters.Counter",
        on_delete=models.PROTECT,
        related_name="pos_sessions",
        db_index=True,
    )
    counter_session = models.ForeignKey(
        "counters.CounterSession",
        on_delete=models.PROTECT,
        related_name="pos_sessions",
        db_index=True,
        help_text="The parent CounterSession this POS session belongs to.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pos_sessions",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="pos_sessions",
        db_index=True,
        help_text="Denormalized for efficient queries.",
    )

    device_identifier = models.CharField(
        max_length=200,
        blank=True,
        help_text="Browser/device fingerprint — metadata only, NOT used for auth.",
    )

    status = models.CharField(
        max_length=10,
        choices=POS_SESSION_STATUS_CHOICES,
        default=POS_SESSION_ACTIVE,
        db_index=True,
    )

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "POS Session"
        verbose_name_plural = "POS Sessions"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["counter", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["counter_session", "status"]),
        ]
        constraints = [
            # Only ONE ACTIVE session per (counter, user) at a time.
            models.UniqueConstraint(
                fields=["counter", "user"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_pos_session_per_counter_user",
            ),
        ]

    def __str__(self):
        return (
            f"POSSession {self.user.email} @ {self.counter.code} "
            f"[{self.status}]"
        )


# =============================================================================
# MenuModifierGroup
# =============================================================================

class MenuModifierGroup(TimestampedModel):
    """
    A group of modifier options that can be applied to a MenuItem.

    Examples:
        Pizza: Size (required, select 1), Toppings (optional, select 0–5)
        Burger: Cheese (optional, select 0–1), Sauce (optional, select 0–3)

    is_required + min_selections + max_selections enforce validation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="modifier_groups",
        db_index=True,
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_required = models.BooleanField(
        default=False,
        help_text="If True, the customer MUST select at least min_selections options.",
    )
    min_selections = models.PositiveSmallIntegerField(
        default=0,
        help_text="Minimum number of options that must be selected.",
    )
    max_selections = models.PositiveSmallIntegerField(
        default=1,
        help_text="Maximum number of options that can be selected. 0 = unlimited.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Which menu items use this group
    menu_items = models.ManyToManyField(
        "menu.MenuItem",
        blank=True,
        related_name="modifier_groups",
        help_text="Menu items that use this modifier group.",
    )

    class Meta:
        verbose_name = "Menu Modifier Group"
        verbose_name_plural = "Menu Modifier Groups"
        ordering = ["restaurant", "name"]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"


# =============================================================================
# MenuModifierOption
# =============================================================================

class MenuModifierOption(TimestampedModel):
    """
    An individual option within a MenuModifierGroup.

    price_adjustment is a backend-authoritative value.
    Frontend NEVER submits price adjustments directly — it only submits
    the selected option ID. The backend resolves the price_adjustment
    from this record.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    modifier_group = models.ForeignKey(
        MenuModifierGroup,
        on_delete=models.CASCADE,
        related_name="options",
    )
    name = models.CharField(max_length=150)
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default="0.00",
        help_text=(
            "Price change when this option is selected. "
            "Backend-authoritative — never trusted from frontend. "
            "0.00 = no change. Positive = surcharge."
        ),
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Menu Modifier Option"
        verbose_name_plural = "Menu Modifier Options"
        ordering = ["modifier_group", "name"]
        indexes = [
            models.Index(fields=["modifier_group", "is_active"]),
        ]

    def __str__(self):
        adj = f" (+{self.price_adjustment})" if self.price_adjustment else ""
        return f"{self.modifier_group.name}: {self.name}{adj}"


# =============================================================================
# OrderItemModifier
# =============================================================================

class OrderItemModifier(TimestampedModel):
    """
    A modifier applied to a specific OrderItem.

    Examples:
        order_item = Margherita Pizza
        name       = "Spice"
        value      = "Less Spicy"
        price_adjustment = 0.00

        order_item = Burger
        name       = "Extra Cheese"
        value      = "Yes"
        price_adjustment = 15.00

    price_adjustment is resolved from MenuModifierOption.price_adjustment.
    Frontend CANNOT submit arbitrary price values.

    modifier_option is optional — free-text modifiers (e.g. special requests)
    have no associated option.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order_item = models.ForeignKey(
        "orders.OrderItem",
        on_delete=models.CASCADE,
        related_name="modifiers",
    )
    modifier_option = models.ForeignKey(
        MenuModifierOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_modifiers",
        help_text="Source option. Null for free-text/special-request modifiers.",
    )

    name = models.CharField(max_length=150, help_text="e.g. 'Spice Level'")
    value = models.CharField(max_length=150, help_text="e.g. 'Less Spicy'")
    price_adjustment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default="0.00",
        help_text="Copied from MenuModifierOption.price_adjustment. Backend-authoritative.",
    )

    class Meta:
        verbose_name = "Order Item Modifier"
        verbose_name_plural = "Order Item Modifiers"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["order_item"]),
        ]

    def __str__(self):
        return f"{self.name}: {self.value} [{self.order_item}]"


# =============================================================================
# OrderFulfillmentStatus
# =============================================================================

class OrderFulfillmentStatus(TimestampedModel):
    """
    Serving-state tracker for an Order.

    This is SEPARATE from Order.status (DRAFT/CONFIRMED/CANCELLED) and
    SEPARATE from KitchenOrder.status (kitchen preparation workflow).

    Order.status remains the authoritative operational status.
    KitchenOrder.status remains the authoritative kitchen status.
    This model tracks the serving/fulfillment lifecycle from the
    waiter's perspective after kitchen completion.

    Status:
        CONFIRMED — order confirmed, sent to kitchen
        PREPARING — kitchen is preparing
        READY     — kitchen marked READY; awaiting service
        SERVED    — waiter marked as served to the customer
        CANCELLED — order cancelled (mirrors Order.status=CANCELLED)

    OneToOne with Order — created when Order is confirmed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="fulfillment_status",
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_FULFILLMENT_STATUS_CHOICES,
        default=FULFILLMENT_CONFIRMED,
        db_index=True,
    )
    served_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="served_orders",
    )
    served_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Order Fulfillment Status"
        verbose_name_plural = "Order Fulfillment Statuses"
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Fulfillment {self.order.order_number} [{self.status}]"


# =============================================================================
# OrderChangeRequest
# =============================================================================

class OrderChangeRequest(TimestampedModel):
    """
    Controlled workflow for requesting changes to a CONFIRMED order.

    DRAFT orders are fully editable directly through OrderService.
    CONFIRMED orders that have been sent to kitchen require this workflow.

    Change types:
        ADD_ITEM, REMOVE_ITEM, CHANGE_QUANTITY, CHANGE_NOTE,
        CHANGE_TABLE, CHANGE_WAITER, CHANGE_CUSTOMER

    Status lifecycle:
        PENDING → APPROVED → (service applies the change)
        PENDING → REJECTED
        PENDING → CANCELLED (by requester)

    Security:
        Approver must NOT be the same as requested_by (service-enforced).
        Approval requires order.change.approve permission.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="change_requests",
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_order_changes",
    )
    change_type = models.CharField(
        max_length=30,
        choices=ORDER_CHANGE_TYPE_CHOICES,
        db_index=True,
    )
    reason = models.TextField(help_text="Required reason for the change request.")
    requested_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "The proposed change data. Structure depends on change_type. "
            "Examples: {item_id, quantity} for ADD_ITEM, "
            "{order_item_id} for REMOVE_ITEM."
        ),
    )
    status = models.CharField(
        max_length=20,
        choices=ORDER_CHANGE_STATUS_CHOICES,
        default=CHANGE_STATUS_PENDING,
        db_index=True,
    )

    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_order_changes",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Order Change Request"
        verbose_name_plural = "Order Change Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["requested_by", "status"]),
        ]

    def __str__(self):
        return (
            f"ChangeReq [{self.change_type}] for {self.order.order_number} "
            f"— {self.status}"
        )


# =============================================================================
# TableFloorPlan
# =============================================================================

class TableFloorPlan(TimestampedModel):
    """
    Floor-plan layout metadata for a DiningTable.

    This is presentation data only — NOT used for authorization.
    The DiningTable model remains authoritative for all business operations.

    One-to-one with DiningTable; created on demand.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    table = models.OneToOneField(
        "orders.DiningTable",
        on_delete=models.CASCADE,
        related_name="floor_plan",
    )

    # Position on the floor plan (pixels or grid units)
    position_x = models.FloatField(default=0.0)
    position_y = models.FloatField(default=0.0)
    width = models.FloatField(default=80.0)
    height = models.FloatField(default=80.0)
    rotation = models.FloatField(default=0.0, help_text="Degrees rotation.")
    shape = models.CharField(
        max_length=20,
        choices=TABLE_SHAPE_CHOICES,
        default="RECTANGLE",
    )

    class Meta:
        verbose_name = "Table Floor Plan"
        verbose_name_plural = "Table Floor Plans"

    def __str__(self):
        return f"FloorPlan for Table {self.table.table_number}"


# =============================================================================
# TableOperationalStatus
# =============================================================================

class TableOperationalStatus(TimestampedModel):
    """
    Operational status for a DiningTable — separate from DiningTable.status.

    DiningTable.status = ACTIVE / INACTIVE (configuration)
    TableOperationalStatus.status = AVAILABLE / OCCUPIED / CLEANING / etc. (runtime)

    This model allows setting explicit operational states like CLEANING or
    RESERVED without touching the configuration model.

    OneToOne with DiningTable. The service layer creates this on demand and
    updates it as operations occur.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    table = models.OneToOneField(
        "orders.DiningTable",
        on_delete=models.CASCADE,
        related_name="operational_status",
    )
    status = models.CharField(
        max_length=20,
        choices=TABLE_OPERATIONAL_STATUS_CHOICES,
        default=TABLE_OP_AVAILABLE,
        db_index=True,
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_table_statuses",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Table Operational Status"
        verbose_name_plural = "Table Operational Statuses"
        indexes = [
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"TableOp {self.table.table_number} [{self.status}]"


# =============================================================================
# TableTransfer
# =============================================================================

class TableTransfer(TimestampedModel):
    """
    Transfers an order from one table to another.

    Rules (enforced in service layer):
        - Destination table must be AVAILABLE (no open session).
        - Order must belong to the source table's session.
        - Historical table relationship remains auditable.
        - Concurrency: select_for_update() on both tables.

    Status:
        REQUESTED → APPROVED → COMPLETED
        REQUESTED → REJECTED
        REQUESTED → CANCELLED
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    source_table = models.ForeignKey(
        "orders.DiningTable",
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
        db_index=True,
    )
    destination_table = models.ForeignKey(
        "orders.DiningTable",
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        db_index=True,
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="table_transfers",
        db_index=True,
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_table_transfers",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_table_transfers",
    )

    status = models.CharField(
        max_length=20,
        choices=TABLE_TRANSFER_STATUS_CHOICES,
        default=TRANSFER_REQUESTED,
        db_index=True,
    )
    reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Table Transfer"
        verbose_name_plural = "Table Transfers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source_table", "status"]),
            models.Index(fields=["destination_table", "status"]),
            models.Index(fields=["order", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return (
            f"Transfer {self.source_table.table_number} → "
            f"{self.destination_table.table_number} [{self.status}]"
        )


# =============================================================================
# TableMerge
# =============================================================================

class TableMerge(TimestampedModel):
    """
    Combines multiple tables for a large group.

    source_tables is a ManyToMany to preserve which tables were merged.
    destination_table is the primary table where the merged session lands.
    Orders continue referencing their original table/session for historical accuracy.

    Status:
        REQUESTED → APPROVED → COMPLETED
        REQUESTED → REJECTED
        REQUESTED → CANCELLED
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="table_merges",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="table_merges",
        db_index=True,
    )
    source_tables = models.ManyToManyField(
        "orders.DiningTable",
        related_name="merge_sources",
        help_text="All tables being merged together.",
    )
    destination_table = models.ForeignKey(
        "orders.DiningTable",
        on_delete=models.PROTECT,
        related_name="merge_destinations",
        help_text="Primary table — the merged group sits here.",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_table_merges",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_table_merges",
    )

    status = models.CharField(
        max_length=20,
        choices=TABLE_MERGE_STATUS_CHOICES,
        default=MERGE_REQUESTED,
        db_index=True,
    )
    reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Table Merge"
        verbose_name_plural = "Table Merges"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return (
            f"TableMerge → {self.destination_table.table_number} "
            f"[{self.status}] @ {self.branch.name}"
        )


# =============================================================================
# OrderMergeRequest
# =============================================================================

class OrderMergeRequest(TimestampedModel):
    """
    Combines two or more open orders into one.

    Rules:
        - Only DRAFT or CONFIRMED orders may be merged.
        - CANCELLED and PAID orders cannot be merged.
        - All source orders must belong to the same restaurant.
        - All source orders must belong to compatible branches.
        - Do NOT rewrite payment history.

    source_orders: the orders being merged (will be cancelled after merge).
    destination_order: the order that survives with combined items.

    Status:
        PENDING → APPROVED → COMPLETED
        PENDING → REJECTED
        PENDING → CANCELLED
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    source_orders = models.ManyToManyField(
        "orders.Order",
        related_name="merge_sources",
        help_text="Orders being merged (will be cancelled after merge completes).",
    )
    destination_order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="merge_destination",
        help_text="The surviving order that receives all items.",
    )

    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_order_merges",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_order_merges",
    )

    status = models.CharField(
        max_length=20,
        choices=ORDER_MERGE_STATUS_CHOICES,
        default=ORDER_MERGE_PENDING,
        db_index=True,
    )
    reason = models.TextField(blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Order Merge Request"
        verbose_name_plural = "Order Merge Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["destination_order", "status"]),
        ]

    def __str__(self):
        return (
            f"OrderMerge → {self.destination_order.order_number} "
            f"[{self.status}]"
        )


# =============================================================================
# BillSplit
# =============================================================================

class BillSplit(TimestampedModel):
    """
    One portion of a split bill.

    The original Bill remains authoritative. BillSplit allocates portions
    of the bill for separate payment.

    Split types:
        ITEM     — each split contains specific items
        QUANTITY — splits contain fractional item quantities
        EQUAL    — bill total divided equally
        GUEST    — split by guest count

    Payment: each BillSplit references the original bill. Payments are made
    against the original Bill but reference the split for tracking.

    Concurrency:
        select_for_update() on the Bill during split creation/finalization.
        Only DRAFT and FINALIZED splits exist — no partial payments on DRAFT splits.

    Status:
        DRAFT     — being constructed
        FINALIZED — locked; ready for payment
        CANCELLED — split abandoned
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bill = models.ForeignKey(
        "billing.Bill",
        on_delete=models.PROTECT,
        related_name="splits",
        db_index=True,
    )
    split_number = models.PositiveSmallIntegerField(
        help_text="Sequential number within this bill (1, 2, 3, ...).",
    )
    split_type = models.CharField(
        max_length=20,
        choices=BILL_SPLIT_TYPE_CHOICES,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="Amount allocated to this split. Backend-calculated.",
    )
    status = models.CharField(
        max_length=20,
        choices=BILL_SPLIT_STATUS_CHOICES,
        default=SPLIT_DRAFT,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_bill_splits",
    )

    class Meta:
        verbose_name = "Bill Split"
        verbose_name_plural = "Bill Splits"
        ordering = ["bill", "split_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["bill", "split_number"],
                name="unique_split_number_per_bill",
            ),
        ]
        indexes = [
            models.Index(fields=["bill", "status"]),
        ]

    def __str__(self):
        return (
            f"Split {self.split_number}/{self.bill.bill_number} "
            f"[{self.split_type}] ₹{self.amount}"
        )


# =============================================================================
# BillSplitItem
# =============================================================================

class BillSplitItem(TimestampedModel):
    """
    Allocation of a BillItem to a specific BillSplit.

    Validation (enforced in service layer):
        Sum of quantity across splits must not exceed BillItem.quantity.
        Sum of amount across splits must not exceed BillItem.total_amount.

    Decimal precision used throughout — never float.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bill_split = models.ForeignKey(
        BillSplit,
        on_delete=models.CASCADE,
        related_name="split_items",
    )
    bill_item = models.ForeignKey(
        "billing.BillItem",
        on_delete=models.PROTECT,
        related_name="split_allocations",
    )
    quantity = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Quantity of this bill item allocated to this split.",
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Amount for this allocation. Backend-calculated.",
    )

    class Meta:
        verbose_name = "Bill Split Item"
        verbose_name_plural = "Bill Split Items"
        ordering = ["bill_split", "created_at"]
        indexes = [
            models.Index(fields=["bill_split"]),
            models.Index(fields=["bill_item"]),
        ]

    def __str__(self):
        return (
            f"SplitItem {self.bill_item} × {self.quantity} "
            f"in {self.bill_split}"
        )


# =============================================================================
# ReceiptPrintLog
# =============================================================================

class ReceiptPrintLog(TimestampedModel):
    """
    Immutable audit record of every receipt print / reprint.

    Every time a receipt is printed or reprinted, a new ReceiptPrintLog
    entry is created. This record can NEVER be edited after creation.

    print_type:
        ORIGINAL  — first print immediately after payment
        REPRINT   — subsequent print on request
        DUPLICATE — copy printed for records
        KITCHEN   — kitchen ticket (no financial data)

    Immutability:
        save() raises ValueError if self.pk already exists in DB.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bill = models.ForeignKey(
        "billing.Bill",
        on_delete=models.PROTECT,
        related_name="print_logs",
        db_index=True,
    )
    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="print_logs",
        help_text="Associated payment. Null for kitchen tickets.",
    )

    printed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="receipt_prints",
    )
    print_type = models.CharField(
        max_length=20,
        choices=RECEIPT_PRINT_TYPE_CHOICES,
        default=PRINT_ORIGINAL,
        db_index=True,
    )
    reason = models.TextField(
        blank=True,
        help_text="Required for REPRINT and DUPLICATE.",
    )
    printed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Receipt Print Log"
        verbose_name_plural = "Receipt Print Logs"
        ordering = ["-printed_at"]
        indexes = [
            models.Index(fields=["bill", "print_type"]),
            models.Index(fields=["printed_by", "printed_at"]),
        ]

    def __str__(self):
        return (
            f"PrintLog [{self.print_type}] {self.bill.bill_number} "
            f"by {self.printed_by.email}"
        )

    def save(self, *args, **kwargs):
        """Immutability guard — receipt print logs can never be edited."""
        if self.pk and ReceiptPrintLog.objects.filter(pk=self.pk).exists():
            raise ValueError(
                "ReceiptPrintLog records are immutable. "
                "Create a new record instead of editing an existing one."
            )
        super().save(*args, **kwargs)


# =============================================================================
# OperationalShift
# =============================================================================

class OperationalShift(TimestampedModel):
    """
    A branch-level operational shift (Morning, Afternoon, Evening, Night).

    This is SEPARATE from CounterSession. One OperationalShift may contain
    multiple CounterSessions (different counters, or shift changeovers at
    a single counter).

    Designed for shift handover workflows — not cash management (that is
    CounterSession's responsibility).

    Status:
        OPEN   — shift is active
        CLOSED — shift has ended
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="operational_shifts",
        db_index=True,
    )
    shift_type = models.CharField(
        max_length=20,
        choices=OPERATIONAL_SHIFT_TYPE_CHOICES,
        default=SHIFT_MORNING,
        db_index=True,
    )
    status = models.CharField(
        max_length=10,
        choices=OPERATIONAL_SHIFT_STATUS_CHOICES,
        default=OP_SHIFT_OPEN,
        db_index=True,
    )

    started_at = models.DateTimeField(
        help_text="When this shift began.",
    )
    ended_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this shift ended.",
    )

    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="opened_operational_shifts",
    )
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="closed_operational_shifts",
    )

    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Operational Shift"
        verbose_name_plural = "Operational Shifts"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "started_at"]),
            models.Index(fields=["status", "started_at"]),
        ]

    def __str__(self):
        return (
            f"{self.shift_type} Shift [{self.status}] "
            f"@ {self.branch.name} ({self.started_at.date()})"
        )


# =============================================================================
# ShiftHandoverNote
# =============================================================================

class ShiftHandoverNote(TimestampedModel):
    """
    A note created during shift closing for the next shift's team.

    Allows managers and staff to communicate operational issues
    (kitchen problems, VIP customer notes, equipment faults, etc.)
    across shifts without losing information.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    shift = models.ForeignKey(
        OperationalShift,
        on_delete=models.PROTECT,
        related_name="handover_notes",
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="shift_handover_notes",
    )

    note_type = models.CharField(
        max_length=20,
        choices=HANDOVER_NOTE_TYPE_CHOICES,
        default=HANDOVER_GENERAL,
        db_index=True,
    )
    content = models.TextField()
    priority = models.CharField(
        max_length=10,
        choices=HANDOVER_PRIORITY_CHOICES,
        default=PRIORITY_NORMAL,
        db_index=True,
    )

    class Meta:
        verbose_name = "Shift Handover Note"
        verbose_name_plural = "Shift Handover Notes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["shift", "note_type"]),
            models.Index(fields=["shift", "priority"]),
        ]

    def __str__(self):
        return (
            f"Handover [{self.note_type}] [{self.priority}] "
            f"Shift {self.shift_id}"
        )


# =============================================================================
# OperationsAuditLog
# =============================================================================

class OperationsAuditLog(TimestampedModel):
    """
    Immutable append-only audit trail for all Phase 19 operations.

    Records every significant operational event with full context.
    Once written, records can NEVER be edited (save() guard).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="operations_audit_logs",
    )
    event_type = models.CharField(
        max_length=50,
        choices=AUDIT_EVENT_CHOICES,
        db_index=True,
    )

    # Flexible entity references (nullable — not all events have all entities)
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="operations_audit_logs",
        db_index=True,
    )
    order_id = models.UUIDField(null=True, blank=True, db_index=True)
    bill_id = models.UUIDField(null=True, blank=True, db_index=True)
    table_id = models.UUIDField(null=True, blank=True, db_index=True)
    pos_session_id = models.UUIDField(null=True, blank=True)
    shift_id = models.UUIDField(null=True, blank=True)

    old_value = models.CharField(max_length=100, blank=True)
    new_value = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context for the event.",
    )

    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Operations Audit Log"
        verbose_name_plural = "Operations Audit Logs"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["event_type", "occurred_at"]),
            models.Index(fields=["actor", "occurred_at"]),
            models.Index(fields=["branch", "occurred_at"]),
            models.Index(fields=["order_id"]),
            models.Index(fields=["bill_id"]),
        ]

    def __str__(self):
        return f"OpsAudit [{self.event_type}] by {self.actor.email}"

    def save(self, *args, **kwargs):
        """Immutability guard — audit logs can never be edited."""
        if self.pk and OperationsAuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError(
                "OperationsAuditLog records are immutable. "
                "Create a new record instead of editing."
            )
        super().save(*args, **kwargs)
