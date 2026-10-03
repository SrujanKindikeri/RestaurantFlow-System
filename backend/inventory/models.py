# =============================================================================
# RestaurantFlow — Inventory Models
# Phase 10: Inventory and Stock Management
#
# Model hierarchy:
#   Company → Restaurant → Branch → StorageLocation → StockBalance
#
# Domain models:
#   InventoryCategory      — restaurant-scoped item groupings
#   InventoryItem          — SKU-level items with costing fields
#   StorageLocation        — branch-level physical locations
#   StockBalance           — current quantity per (item, location) — unique pair
#   StockMovement          — immutable audit trail of every stock change
#   Supplier               — vendor/supplier per restaurant
#   PurchaseSequence       — concurrency-safe PO number generation
#   PurchaseOrder          — purchase document with workflow statuses
#   PurchaseOrderItem      — line items on a purchase order
#   PurchaseReceipt        — record of one goods-receiving event
#   PurchaseReceiptItem    — per-item quantities received in one receipt
#   TransferSequence       — concurrency-safe transfer number generation
#   StockTransfer          — stock movement between two storage locations
#   StockTransferItem      — per-item quantities in a transfer
#   StockWastage           — wastage request with approval workflow
#   StockAdjustment        — reconciliation record (physical vs system)
#
# Design principles:
#   - UUID primary keys on all models.
#   - All monetary/quantity values use DecimalField — never float.
#   - StockMovement is immutable — never edited or deleted after creation.
#   - available_quantity is always derived: quantity - reserved_quantity.
#   - StockBalance uniqueness enforced at DB level: (item, location).
#   - PO/Transfer numbers use select_for_update() sequences.
#   - All status transitions are controlled (constants.PO_VALID_TRANSITIONS).
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel
from inventory.constants import (
    UNIT_CHOICES,
    LOCATION_TYPE_CHOICES,
    MOVEMENT_TYPE_CHOICES,
    PO_STATUS_CHOICES, PO_DRAFT,
    TRANSFER_STATUS_CHOICES, TRANSFER_DRAFT,
    WASTAGE_TYPE_CHOICES, WASTAGE_STATUS_CHOICES, WASTAGE_PENDING,
)

logger = logging.getLogger("inventory")


# =============================================================================
# InventoryCategory
# =============================================================================

class InventoryCategory(TimestampedModel):
    """
    Restaurant-scoped grouping for inventory items.

    Examples: Vegetables, Dairy, Meat, Grains, Spices, Beverages, Packaging.
    Categories are not hard-coded — any restaurant can define their own.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="inventory_categories",
        db_index=True,
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Inventory Category"
        verbose_name_plural = "Inventory Categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "name"],
                name="unique_inventory_category_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "name"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.restaurant.name})"


# =============================================================================
# InventoryItem
# =============================================================================

class InventoryItem(TimestampedModel):
    """
    A trackable inventory item (SKU-level).

    Represents a single purchasable/consumable ingredient or product.
    SKU must be unique within a restaurant.

    Costing:
        average_cost is updated on every purchase receipt using
        weighted-average method: (old_qty × old_cost + new_qty × new_cost) / total_qty

    Stock thresholds:
        minimum_stock  — absolute minimum; below this is critical
        reorder_level  — trigger point for repurchase
        maximum_stock  — storage capacity limit
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="inventory_items",
        db_index=True,
    )
    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name="items",
        null=True,
        blank=True,
        db_index=True,
    )
    name = models.CharField(max_length=150, db_index=True)
    sku = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Stock Keeping Unit — unique within the restaurant.",
    )
    description = models.TextField(blank=True)
    default_unit = models.CharField(
        max_length=15,
        choices=UNIT_CHOICES,
        db_index=True,
    )
    minimum_stock = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default="0.000",
        help_text="Absolute minimum stock level. Below this is critical.",
    )
    reorder_level = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default="0.000",
        help_text="Stock level at which repurchase should be triggered.",
    )
    maximum_stock = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default="0.000",
        help_text="Maximum storage capacity. 0 = unlimited.",
    )
    average_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text=(
            "Weighted-average cost per default_unit. "
            "Updated on every purchase receipt. Never trust frontend value."
        ),
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Inventory Item"
        verbose_name_plural = "Inventory Items"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "sku"],
                name="unique_inventory_sku_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "category"]),
            models.Index(fields=["restaurant", "sku"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.sku}] ({self.restaurant.name})"


# =============================================================================
# StorageLocation
# =============================================================================

class StorageLocation(TimestampedModel):
    """
    A physical storage location within a branch.

    Examples: Main Store, Kitchen Store, Cold Storage, Freezer, Bar Store.
    Code must be unique within the branch.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="storage_locations",
        db_index=True,
    )
    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Short code unique within the branch. e.g. MAIN, COLD, FRZ.",
    )
    location_type = models.CharField(
        max_length=20,
        choices=LOCATION_TYPE_CHOICES,
        db_index=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Storage Location"
        verbose_name_plural = "Storage Locations"
        ordering = ["branch", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "code"],
                name="unique_storage_location_code_per_branch",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "is_active"]),
            models.Index(fields=["branch", "location_type"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.code}] — {self.branch.name}"


# =============================================================================
# StockBalance
# =============================================================================

class StockBalance(TimestampedModel):
    """
    Current stock level for a specific (item, location) pair.

    This is the live balance snapshot — updated by StockService on every
    stock-changing operation.

    Uniqueness:
        (inventory_item, storage_location) — enforced at DB level.

    Formula:
        available_quantity = quantity - reserved_quantity

    reserved_quantity is reserved for future use (e.g., committed orders).
    In Phase 10 it defaults to 0.

    average_cost here mirrors InventoryItem.average_cost but is kept
    per-location for accurate transfer costing.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="stock_balances",
        db_index=True,
    )
    storage_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="stock_balances",
        db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default="0.000",
        help_text="Total on-hand quantity at this location.",
    )
    reserved_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        default="0.000",
        help_text="Quantity reserved/committed. Phase 10: always 0.",
    )
    average_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text="Per-unit weighted-average cost at this location.",
    )
    last_movement_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last stock movement affecting this balance.",
    )

    class Meta:
        verbose_name = "Stock Balance"
        verbose_name_plural = "Stock Balances"
        ordering = ["inventory_item", "storage_location"]
        constraints = [
            models.UniqueConstraint(
                fields=["inventory_item", "storage_location"],
                name="unique_stock_balance_per_item_location",
            ),
        ]
        indexes = [
            models.Index(fields=["inventory_item", "storage_location"]),
            models.Index(fields=["storage_location"]),
            models.Index(fields=["inventory_item"]),
        ]

    def __str__(self):
        return (
            f"{self.inventory_item.name} @ {self.storage_location.name} "
            f"= {self.quantity} {self.inventory_item.default_unit}"
        )

    @property
    def available_quantity(self):
        """Available = total - reserved. Derived property — never stored."""
        return self.quantity - self.reserved_quantity

    def get_stock_status(self) -> str:
        """
        Derive stock status from available_quantity vs item thresholds.
        Never stored — always derived on-the-fly.
        """
        from inventory.constants import (
            STOCK_STATUS_OUT_OF_STOCK,
            STOCK_STATUS_LOW_STOCK,
            STOCK_STATUS_IN_STOCK,
            ZERO,
        )
        available = self.available_quantity
        reorder = self.inventory_item.reorder_level
        if available <= ZERO:
            return STOCK_STATUS_OUT_OF_STOCK
        if available <= reorder:
            return STOCK_STATUS_LOW_STOCK
        return STOCK_STATUS_IN_STOCK


# =============================================================================
# StockMovement
# =============================================================================

class StockMovement(TimestampedModel):
    """
    Immutable historical record of every stock change.

    Every increase or decrease of stock creates one StockMovement.
    StockMovements are NEVER edited or deleted after creation.
    Corrections create a new StockMovement of type CORRECTION.

    reference_type + reference_id form a generic FK pattern to the
    source document (PurchaseReceipt, StockTransfer, StockWastage, etc.)
    Using strings avoids GenericForeignKey complexity while remaining queryable.

    Cost fields:
        unit_cost   — cost per unit at movement time
        total_cost  — unit_cost × quantity
    These are preserved as historical snapshots.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        db_index=True,
    )
    storage_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        db_index=True,
    )
    movement_type = models.CharField(
        max_length=25,
        choices=MOVEMENT_TYPE_CHOICES,
        db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=3,
        help_text="Absolute quantity moved. Always positive.",
    )
    unit_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text="Cost per unit at the time of movement.",
    )
    total_cost = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        default="0.00",
        help_text="unit_cost × quantity. Stored as snapshot.",
    )
    reference_type = models.CharField(
        max_length=30,
        blank=True,
        db_index=True,
        help_text=(
            "Type of the source document. "
            "e.g. PURCHASE_RECEIPT, STOCK_TRANSFER, STOCK_WASTAGE, STOCK_ADJUSTMENT."
        ),
    )
    reference_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of the source document referenced by reference_type.",
    )
    reason = models.TextField(
        blank=True,
        help_text="Human-readable reason for this movement.",
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_movements",
        db_index=True,
    )

    class Meta:
        verbose_name = "Stock Movement"
        verbose_name_plural = "Stock Movements"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["inventory_item", "created_at"]),
            models.Index(fields=["storage_location", "created_at"]),
            models.Index(fields=["movement_type", "created_at"]),
            models.Index(fields=["reference_type", "reference_id"]),
            models.Index(fields=["performed_by", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.movement_type} {self.quantity} {self.inventory_item.default_unit} "
            f"— {self.inventory_item.name} @ {self.storage_location.name}"
        )


# =============================================================================
# Supplier
# =============================================================================

class Supplier(TimestampedModel):
    """
    A vendor/supplier that provides inventory items to a restaurant.

    Supplier code must be unique within the restaurant.
    Supplier payments/accounting are out of scope for Phase 10.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="suppliers",
        db_index=True,
    )
    name = models.CharField(max_length=150, db_index=True)
    code = models.CharField(
        max_length=30,
        db_index=True,
        help_text="Supplier code — unique within the restaurant.",
    )
    contact_person = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    tax_identifier = models.CharField(
        max_length=50,
        blank=True,
        help_text="Tax ID / GSTIN of the supplier.",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_supplier_code_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "code"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.code}] ({self.restaurant.name})"


# =============================================================================
# PurchaseSequence
# =============================================================================

class PurchaseSequence(TimestampedModel):
    """
    Concurrency-safe purchase order number sequence per restaurant.

    One row per restaurant. select_for_update() is used in the service.
    Format: PO-{seq:06d}  e.g. PO-000001

    Never uses MAX()+1 — always uses DB-level locking.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.OneToOneField(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="purchase_sequence",
    )
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Purchase Sequence"
        verbose_name_plural = "Purchase Sequences"

    def __str__(self):
        return f"PurchaseSeq restaurant={self.restaurant.name} seq={self.last_sequence}"


# =============================================================================
# PurchaseOrder
# =============================================================================

class PurchaseOrder(TimestampedModel):
    """
    A purchase order document representing goods to be bought from a supplier.

    Status lifecycle:
        DRAFT → SUBMITTED → APPROVED → PARTIALLY_RECEIVED / RECEIVED
        Any non-terminal state → CANCELLED

    Creating a PO does NOT affect stock.
    Stock only increases when goods are received (PurchaseReceipt).

    Financial fields (all Decimal):
        subtotal        = sum of PurchaseOrderItem.total_amount
        tax_amount      = sum of item-level taxes
        discount_amount = order-level discount
        total_amount    = subtotal + tax_amount - discount_amount

    Backend recalculates all totals — frontend values are NEVER trusted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        db_index=True,
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_orders",
        db_index=True,
    )
    purchase_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Human-readable PO number. Format: PO-NNNNNN. Immutable.",
    )
    status = models.CharField(
        max_length=25,
        choices=PO_STATUS_CHOICES,
        default=PO_DRAFT,
        db_index=True,
    )
    order_date = models.DateField(null=True, blank=True)
    expected_date = models.DateField(null=True, blank=True)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default="0.00")
    tax_amount = models.DecimalField(max_digits=14, decimal_places=2, default="0.00")
    discount_amount = models.DecimalField(max_digits=14, decimal_places=2, default="0.00")
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default="0.00")

    notes = models.TextField(blank=True)

    # Actors
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_purchase_orders",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="approved_purchase_orders",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="received_purchase_orders",
    )
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Purchase Order"
        verbose_name_plural = "Purchase Orders"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["supplier", "status"]),
            models.Index(fields=["purchase_number"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.purchase_number} [{self.status}] — {self.supplier.name}"


# =============================================================================
# PurchaseOrderItem
# =============================================================================

class PurchaseOrderItem(TimestampedModel):
    """
    A single line item on a PurchaseOrder.

    total_amount is always computed by the backend:
        total_amount = (quantity × unit_cost × (1 + tax_rate/100)) - discount_amount
    Frontend total_amount is NEVER trusted.

    received_quantity tracks how much has been physically received so far.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="purchase_order_items",
        db_index=True,
    )
    quantity = models.DecimalField(
        max_digits=14, decimal_places=3,
        help_text="Ordered quantity.",
    )
    unit = models.CharField(max_length=15, choices=UNIT_CHOICES)
    unit_cost = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text="Cost per unit from the supplier.",
    )
    tax_rate = models.DecimalField(
        max_digits=6, decimal_places=3,
        default="0.000",
        help_text="Tax rate percentage for this item (e.g. 5.000 = 5%).",
    )
    discount_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default="0.00",
        help_text="Line-item discount amount.",
    )
    total_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default="0.00",
        help_text="Backend-computed total. Never trust frontend value.",
    )
    received_quantity = models.DecimalField(
        max_digits=14, decimal_places=3, default="0.000",
        help_text="How much has been physically received so far.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Purchase Order Item"
        verbose_name_plural = "Purchase Order Items"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["purchase_order", "inventory_item"]),
            models.Index(fields=["inventory_item"]),
        ]

    def __str__(self):
        return (
            f"{self.inventory_item.name} × {self.quantity} {self.unit} "
            f"@ {self.unit_cost} — {self.purchase_order.purchase_number}"
        )

    @property
    def remaining_quantity(self):
        """How much more can be received on this item."""
        return self.quantity - self.received_quantity


# =============================================================================
# PurchaseReceipt
# =============================================================================

class PurchaseReceipt(TimestampedModel):
    """
    A record of one goods-receiving event against a PurchaseOrder.

    One PO can have multiple PurchaseReceipts (partial receiving).
    Each receipt records:
        - which items were received
        - how much was received
        - where they were stored
        - who received them

    A receipt is auditable and immutable after creation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.PROTECT,
        related_name="receipts",
        db_index=True,
    )
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="purchase_receipts",
    )
    storage_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="purchase_receipts",
        db_index=True,
    )
    received_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Purchase Receipt"
        verbose_name_plural = "Purchase Receipts"
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["purchase_order", "received_at"]),
            models.Index(fields=["storage_location", "received_at"]),
        ]

    def __str__(self):
        return (
            f"Receipt for {self.purchase_order.purchase_number} "
            f"by {self.received_by.email} at {self.received_at}"
        )


# =============================================================================
# PurchaseReceiptItem
# =============================================================================

class PurchaseReceiptItem(TimestampedModel):
    """
    Per-item quantities received in one PurchaseReceipt.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    receipt = models.ForeignKey(
        PurchaseReceipt,
        on_delete=models.CASCADE,
        related_name="items",
    )
    purchase_order_item = models.ForeignKey(
        PurchaseOrderItem,
        on_delete=models.PROTECT,
        related_name="receipt_items",
        db_index=True,
    )
    quantity_received = models.DecimalField(
        max_digits=14, decimal_places=3,
        help_text="Quantity received in this specific receipt event.",
    )
    unit_cost = models.DecimalField(
        max_digits=14, decimal_places=2,
        help_text="Unit cost at time of receiving (snapshot from PO item).",
    )

    class Meta:
        verbose_name = "Purchase Receipt Item"
        verbose_name_plural = "Purchase Receipt Items"
        indexes = [
            models.Index(fields=["receipt", "purchase_order_item"]),
        ]

    def __str__(self):
        return (
            f"{self.purchase_order_item.inventory_item.name} "
            f"× {self.quantity_received} received"
        )


# =============================================================================
# TransferSequence
# =============================================================================

class TransferSequence(TimestampedModel):
    """
    Concurrency-safe transfer number sequence per restaurant.

    Format: TR-{seq:06d}  e.g. TR-000001
    Never uses MAX()+1.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.OneToOneField(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="transfer_sequence",
    )
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Transfer Sequence"
        verbose_name_plural = "Transfer Sequences"

    def __str__(self):
        return f"TransferSeq restaurant={self.restaurant.name} seq={self.last_sequence}"


# =============================================================================
# StockTransfer
# =============================================================================

class StockTransfer(TimestampedModel):
    """
    Movement of stock between two storage locations within the same restaurant.

    Status lifecycle:
        DRAFT → REQUESTED → APPROVED → COMPLETED
        Any non-terminal state → CANCELLED

    Stock is only moved when status reaches COMPLETED:
        source_location: TRANSFER_OUT movements created
        destination_location: TRANSFER_IN movements created
    Both operations are atomic.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="stock_transfers",
        db_index=True,
    )
    source_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
        db_index=True,
    )
    destination_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        db_index=True,
    )
    transfer_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Human-readable transfer number. Format: TR-NNNNNN. Immutable.",
    )
    status = models.CharField(
        max_length=15,
        choices=TRANSFER_STATUS_CHOICES,
        default=TRANSFER_DRAFT,
        db_index=True,
    )
    notes = models.TextField(blank=True)

    # Actors
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_transfers",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="approved_transfers",
    )
    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="completed_transfers",
    )

    requested_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Stock Transfer"
        verbose_name_plural = "Stock Transfers"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["source_location", "status"]),
            models.Index(fields=["destination_location", "status"]),
            models.Index(fields=["transfer_number"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return (
            f"{self.transfer_number} [{self.status}] "
            f"{self.source_location.name} → {self.destination_location.name}"
        )


# =============================================================================
# StockTransferItem
# =============================================================================

class StockTransferItem(TimestampedModel):
    """
    Per-item quantity and unit for a StockTransfer.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transfer = models.ForeignKey(
        StockTransfer,
        on_delete=models.CASCADE,
        related_name="items",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="transfer_items",
        db_index=True,
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=15, choices=UNIT_CHOICES)

    class Meta:
        verbose_name = "Stock Transfer Item"
        verbose_name_plural = "Stock Transfer Items"
        indexes = [
            models.Index(fields=["transfer", "inventory_item"]),
        ]

    def __str__(self):
        return (
            f"{self.inventory_item.name} × {self.quantity} {self.unit} "
            f"— {self.transfer.transfer_number}"
        )


# =============================================================================
# StockWastage
# =============================================================================

class StockWastage(TimestampedModel):
    """
    A wastage request recording spoiled/damaged/expired stock.

    Status lifecycle:
        PENDING → APPROVED → (stock decreased, status becomes RECORDED)
        PENDING → REJECTED  (no stock change)

    Stock is only decreased after APPROVED.
    estimated_cost uses the average_cost at approval time.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="wastage_records",
        db_index=True,
    )
    storage_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="wastage_records",
        db_index=True,
    )
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    unit = models.CharField(max_length=15, choices=UNIT_CHOICES)
    wastage_type = models.CharField(
        max_length=20,
        choices=WASTAGE_TYPE_CHOICES,
        db_index=True,
    )
    reason = models.TextField(help_text="Reason for the wastage.")
    estimated_cost = models.DecimalField(
        max_digits=14, decimal_places=2, default="0.00",
        help_text=(
            "Estimated cost of wasted stock. "
            "Calculated from average_cost at approval time."
        ),
    )
    status = models.CharField(
        max_length=10,
        choices=WASTAGE_STATUS_CHOICES,
        default=WASTAGE_PENDING,
        db_index=True,
    )

    # Actors
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="recorded_wastages",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="approved_wastages",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Stock Wastage"
        verbose_name_plural = "Stock Wastages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["inventory_item", "status"]),
            models.Index(fields=["storage_location", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["recorded_by", "created_at"]),
        ]

    def __str__(self):
        return (
            f"Wastage {self.quantity} {self.unit} of {self.inventory_item.name} "
            f"[{self.status}]"
        )


# =============================================================================
# StockAdjustment
# =============================================================================

class StockAdjustment(TimestampedModel):
    """
    A physical stock count reconciliation record.

    Records the difference between physical count and system balance,
    then creates the appropriate ADJUSTMENT_IN or ADJUSTMENT_OUT movement.

    Examples:
        System: 100 KG, Physical: 95 KG  → quantity_difference = -5 KG → ADJUSTMENT_OUT
        System: 95 KG,  Physical: 100 KG → quantity_difference = +5 KG → ADJUSTMENT_IN
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="adjustments",
        db_index=True,
    )
    storage_location = models.ForeignKey(
        StorageLocation,
        on_delete=models.PROTECT,
        related_name="adjustments",
        db_index=True,
    )
    quantity_before = models.DecimalField(
        max_digits=14, decimal_places=3,
        help_text="System quantity before adjustment.",
    )
    quantity_physical = models.DecimalField(
        max_digits=14, decimal_places=3,
        help_text="Physical count quantity entered by the user.",
    )
    quantity_difference = models.DecimalField(
        max_digits=14, decimal_places=3,
        help_text=(
            "physical - before. Positive = ADJUSTMENT_IN, Negative = ADJUSTMENT_OUT."
        ),
    )
    unit = models.CharField(max_length=15, choices=UNIT_CHOICES)
    reason = models.TextField(help_text="Required reason for the adjustment.")
    adjusted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_adjustments",
    )
    # Linked movement for traceability
    stock_movement = models.OneToOneField(
        StockMovement,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="adjustment",
        help_text="The StockMovement created by this adjustment.",
    )

    class Meta:
        verbose_name = "Stock Adjustment"
        verbose_name_plural = "Stock Adjustments"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["inventory_item", "created_at"]),
            models.Index(fields=["storage_location", "created_at"]),
            models.Index(fields=["adjusted_by", "created_at"]),
        ]

    def __str__(self):
        sign = "+" if self.quantity_difference >= 0 else ""
        return (
            f"Adjustment {sign}{self.quantity_difference} {self.unit} "
            f"of {self.inventory_item.name} @ {self.storage_location.name}"
        )
