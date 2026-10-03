# =============================================================================
# RestaurantFlow — Billing Models
# Phase 8: Bill, BillItem, BillSequence, BillCorrectionRequest
#
# Architecture:
#   Order (Phase 6, operational source of truth)
#       └── Bill  (financial document — one per confirmed order)
#               └── BillItem  (line-item financial snapshot)
#
#   BillSequence  (concurrency-safe bill number generation, per-branch)
#
#   BillCorrectionRequest  (controlled workflow for modifying finalized bills)
#
# Design principles:
#   - UUID primary keys on all models.
#   - One Bill per Order (UniqueConstraint at DB level).
#   - Bill and BillItem are IMMUTABLE after finalization.
#   - All monetary values use DecimalField — never float.
#   - Correction workflow never silently overwrites a finalized bill.
#   - BillSequence uses select_for_update() — never MAX()+1.
#   - Bill number format: B-{YYYY}-{seq:06d}  e.g. B-2026-000001
#   - Tax snapshots are read from OrderItem at bill creation time.
#   - Price snapshots are read from OrderItem at bill creation time.
#   - Discount is permission-controlled (see services.py).
#   - Rounding is applied as the final step before grand_total.
#
# Status state machines:
#   Bill:   DRAFT → FINALIZED (terminal) or CANCELLED / VOID
#   Correction:  PENDING → APPROVED / REJECTED / CANCELLED
#
# Future-proofing:
#   - Payment fields intentionally absent (Phase 9).
#   - Split-bill support deferred (Phase 9+).
#   - Coupon/loyalty systems not implemented (future phases).
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel

logger = logging.getLogger("billing")


# =============================================================================
# Bill Status
# =============================================================================

class BillStatus(models.TextChoices):
    DRAFT     = "DRAFT",     "Draft"
    FINALIZED = "FINALIZED", "Finalized"
    CANCELLED = "CANCELLED", "Cancelled"
    VOID      = "VOID",      "Void"


# =============================================================================
# Discount Type
# =============================================================================

class DiscountType(models.TextChoices):
    PERCENTAGE   = "PERCENTAGE",   "Percentage"
    FIXED_AMOUNT = "FIXED_AMOUNT", "Fixed Amount"


# =============================================================================
# Correction Type
# =============================================================================

class CorrectionType(models.TextChoices):
    ITEM_CORRECTION     = "ITEM_CORRECTION",     "Item Correction"
    DISCOUNT_CORRECTION = "DISCOUNT_CORRECTION", "Discount Correction"
    TAX_CORRECTION      = "TAX_CORRECTION",       "Tax Correction"
    CANCELLATION        = "CANCELLATION",         "Cancellation"


# =============================================================================
# Correction Status
# =============================================================================

class CorrectionStatus(models.TextChoices):
    PENDING   = "PENDING",   "Pending"
    APPROVED  = "APPROVED",  "Approved"
    REJECTED  = "REJECTED",  "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


# =============================================================================
# BillSequence
# =============================================================================

class BillSequence(TimestampedModel):
    """
    Concurrency-safe bill number sequence per branch.

    Unlike OrderSequence (which resets daily), bill sequences are
    ANNUAL — they reset per year, giving numbers like:
        B-2026-000001
        B-2026-000002
        ...
        B-2027-000001

    Format: B-{year}-{seq:06d}

    One row per (branch, year_key).
    select_for_update() is used in the service layer — never MAX()+1.

    Immutable once a bill number is issued.  Do not reassign sequences.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="bill_sequences",
        db_index=True,
    )

    # e.g. '2026'
    year_key = models.CharField(max_length=4, db_index=True)

    # The last issued sequence number for this branch+year — incremented atomically
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Bill Sequence"
        verbose_name_plural = "Bill Sequences"
        constraints = [
            models.UniqueConstraint(
                fields=["branch", "year_key"],
                name="unique_bill_sequence_per_branch_year",
            ),
        ]
        indexes = [
            models.Index(fields=["branch", "year_key"]),
        ]

    def __str__(self):
        return f"BillSeq branch={self.branch.name} year={self.year_key} seq={self.last_sequence}"


# =============================================================================
# Bill
# =============================================================================

class Bill(TimestampedModel):
    """
    Financial document generated from a confirmed Order.

    A Bill is SEPARATE from an Order:
      - Order = operational transaction (items, table, kitchen workflow)
      - Bill  = financial document (amounts, tax, discounts, rounding, total)

    One Order → One Bill.  DB-level UniqueConstraint enforces this.

    Status lifecycle:
        DRAFT     — created but not yet finalized; can be recalculated
        FINALIZED — locked; amounts are immutable; ready for payment (Phase 9)
        CANCELLED — cancelled before payment; reason recorded
        VOID      — post-payment void; requires approval + audit trail

    Financial fields (all Decimal — never float):
        subtotal         = sum of (quantity × unit_price) across all BillItems
        discount_amount  = applied discount (from PERCENTAGE or FIXED_AMOUNT)
        taxable_amount   = subtotal - discount_amount
        tax_amount       = sum of tax calculated per BillItem
        rounding_amount  = small adjustment to reach a round number (−0.99 to +0.99)
        grand_total      = taxable_amount + tax_amount + rounding_amount

    Calculation sequence (authoritative — see services.calculate_bill()):
        1. Per-item: gross = quantity × unit_price
        2. Bill-level discount applied to subtotal
        3. taxable_amount = subtotal - discount_amount
        4. Per-item tax: tax = (gross_amount - item_discount) × tax_rate / 100
        5. Rounding applied to reach a convenient total
        6. grand_total = taxable_amount + tax_amount + rounding_amount

    Discount:
        discount_type    = PERCENTAGE or FIXED_AMOUNT
        discount_value   = the input value (e.g. 10 for 10% or ₹50 for fixed)
        discount_amount  = computed amount (stored after calculation)
        Discount is permission-controlled; maximum thresholds configured per role.

    Tax:
        Tax breakdown stored as JSON in tax_breakdown field.
        Example: {"GST_STANDARD": "50.00", "CESS": "5.00"}
        This supports multi-component taxes without hard-coding CGST/SGST.

    Immutability:
        After FINALIZED status is set:
        - No direct edits to financial fields are permitted.
        - Corrections require BillCorrectionRequest workflow.

    Future Phase 9 (Payment):
        - payment_status field will be added
        - Payment records will reference this bill by FK
        - No payment fields exist here yet
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Core references
    # -------------------------------------------------------------------------
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="bill",
        help_text=(
            "The confirmed order this bill is for. "
            "OneToOne prevents duplicate bills per order."
        ),
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="bills",
        db_index=True,
        help_text="Denormalized branch reference for efficient billing queries.",
    )

    # -------------------------------------------------------------------------
    # Human-readable bill number — immutable after creation
    # -------------------------------------------------------------------------
    bill_number = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Human-readable bill number. Format: B-{YYYY}-{seq:06d}. Immutable.",
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=BillStatus.choices,
        default=BillStatus.DRAFT,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Discount fields
    # -------------------------------------------------------------------------
    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
        null=True,
        blank=True,
        help_text="PERCENTAGE or FIXED_AMOUNT. Null if no discount applied.",
    )
    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default="0.00",
        help_text=(
            "Input discount value. "
            "For PERCENTAGE: e.g. 10.00 = 10%. "
            "For FIXED_AMOUNT: e.g. 50.00 = ₹50."
        ),
    )

    # -------------------------------------------------------------------------
    # Financial totals — Decimal; authoritative after calculate_bill()
    # -------------------------------------------------------------------------
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="Sum of (quantity × unit_price) across all bill items before discount.",
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="Computed discount amount applied to the bill.",
    )
    taxable_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="subtotal - discount_amount.",
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="Total tax computed from all bill items.",
    )
    tax_breakdown = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Per-component tax breakdown. "
            "Example: {\"GST_STANDARD\": \"50.00\", \"CESS\": \"5.00\"}. "
            "Supports multi-component taxes without hard-coding CGST/SGST."
        ),
    )
    rounding_amount = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default="0.00",
        help_text=(
            "Small rounding adjustment. Allowed range: -0.99 to +0.99. "
            "Applied as the final step before grand_total."
        ),
    )
    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="taxable_amount + tax_amount + rounding_amount.",
    )

    notes = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Actors
    # -------------------------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_bills",
        help_text="User who created this bill (typically the cashier).",
    )
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="finalized_bills",
        help_text="User who finalized this bill.",
    )
    finalized_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of finalization.",
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cancelled_bills",
    )
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Bill"
        verbose_name_plural = "Bills"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["branch", "created_at"]),
            models.Index(fields=["branch", "status", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["bill_number"]),
            models.Index(fields=["order"]),
            models.Index(fields=["created_by", "status"]),
        ]

    def __str__(self):
        return f"{self.bill_number} [{self.status}] — {self.branch.name}"

    @property
    def is_editable(self) -> bool:
        """Only DRAFT bills can be modified directly."""
        return self.status == BillStatus.DRAFT

    @property
    def order_number(self) -> str:
        return self.order.order_number

    @property
    def order_type(self) -> str:
        return self.order.order_type


# =============================================================================
# BillItem
# =============================================================================

class BillItem(TimestampedModel):
    """
    A single line item in a Bill.

    BillItem is a FINANCIAL snapshot of an OrderItem at billing time.
    It preserves the exact values used when the bill was created.
    These values are immutable after the bill is finalized.

    Price source:
        unit_price is read from OrderItem.unit_price_snapshot.
        Do NOT query today's menu price after bill finalization.

    Tax source:
        tax_rate and tax_code are read from OrderItem.tax_rate_snapshot
        and OrderItem.tax_code_snapshot at bill creation.
        If the snapshot is missing (legacy data), it is handled explicitly —
        never silently assumed.

    Calculation (per item):
        gross_amount   = quantity × unit_price
        discount_amount = item-level discount (currently 0; bill-level discount
                         is applied at Bill level, not per item in Phase 8)
        taxable_amount = gross_amount - discount_amount
        tax_amount     = taxable_amount × tax_rate / 100
        total_amount   = taxable_amount + tax_amount

    All monetary fields use DecimalField — never float.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bill = models.ForeignKey(
        Bill,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="Parent bill. Cascade delete when bill is deleted (DRAFT only).",
    )
    order_item = models.OneToOneField(
        "orders.OrderItem",
        on_delete=models.PROTECT,
        related_name="bill_item",
        help_text=(
            "Source OrderItem. OneToOne ensures each order item maps to at most "
            "one bill item. PROTECT prevents accidental cascade."
        ),
    )

    # -------------------------------------------------------------------------
    # Menu item reference (denormalized for receipt display)
    # -------------------------------------------------------------------------
    menu_item = models.ForeignKey(
        "menu.MenuItem",
        on_delete=models.PROTECT,
        related_name="bill_items",
        help_text="Menu item reference. PROTECT — never lose financial history.",
    )

    # -------------------------------------------------------------------------
    # Snapshots — immutable financial record
    # These are copied from the OrderItem at bill creation time.
    # -------------------------------------------------------------------------
    item_name_snapshot = models.CharField(
        max_length=200,
        help_text="Item name at billing time. Immutable.",
    )
    sku_snapshot = models.CharField(
        max_length=100,
        blank=True,
        help_text="SKU at billing time. May be blank if item had no SKU.",
    )
    quantity = models.DecimalField(
        max_digits=7,
        decimal_places=3,
        help_text="Quantity ordered. Copied from OrderItem.",
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text=(
            "Price per unit from OrderItem.unit_price_snapshot. "
            "Historical value — not today's menu price."
        ),
    )

    # -------------------------------------------------------------------------
    # Per-item computed amounts
    # -------------------------------------------------------------------------
    gross_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="quantity × unit_price.",
    )
    discount_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text=(
            "Item-level discount amount. Currently always 0.00 in Phase 8 "
            "(bill-level discount applied at Bill). Reserved for future item-level discounts."
        ),
    )
    taxable_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="gross_amount - discount_amount.",
    )

    # -------------------------------------------------------------------------
    # Tax snapshots — copied from OrderItem at bill creation
    # -------------------------------------------------------------------------
    tax_rate = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        default="0.000",
        help_text=(
            "Tax rate % from OrderItem.tax_rate_snapshot. "
            "e.g. 5.000 = 5%%. Immutable after finalization."
        ),
    )
    tax_code = models.CharField(
        max_length=50,
        blank=True,
        help_text=(
            "Tax code from OrderItem.tax_code_snapshot. "
            "e.g. GST_STANDARD. Used in tax breakdown."
        ),
    )
    tax_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="taxable_amount × tax_rate / 100 (rounded).",
    )

    # -------------------------------------------------------------------------
    # Final line total
    # -------------------------------------------------------------------------
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default="0.00",
        help_text="taxable_amount + tax_amount.",
    )

    class Meta:
        verbose_name = "Bill Item"
        verbose_name_plural = "Bill Items"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["bill"]),
            models.Index(fields=["order_item"]),
            models.Index(fields=["menu_item"]),
        ]

    def __str__(self):
        return (
            f"{self.item_name_snapshot} x{self.quantity} "
            f"@ ₹{self.unit_price} — {self.bill.bill_number}"
        )


# =============================================================================
# BillCorrectionRequest
# =============================================================================

class BillCorrectionRequest(TimestampedModel):
    """
    A controlled workflow for requesting corrections to a FINALIZED bill.

    Design rationale:
        A finalized bill must NEVER be silently overwritten.
        Any correction requires:
            1. A cashier (or eligible user) submits a correction request.
            2. A manager (or authorized approver) reviews and approves or rejects.
            3. If approved, the service layer creates a correction record and
               optionally a replacement bill.
            4. The original bill remains intact with full audit trail.

    Correction types:
        ITEM_CORRECTION     — wrong item, quantity, or price needs fixing
        DISCOUNT_CORRECTION — discount was wrong or unauthorized
        TAX_CORRECTION      — tax rate/code was incorrect
        CANCELLATION        — entire bill needs to be voided

    Status lifecycle:
        PENDING  → APPROVED (by authorized reviewer)
        PENDING  → REJECTED (by authorized reviewer)
        PENDING  → CANCELLED (by the requester, before approval)

    Security:
        - A user may NOT approve their own correction request
          (enforced in the service layer).
        - Approval requires bill.correction.approve permission.
        - Rejection requires bill.correction.approve permission.

    Audit trail:
        requested_data stores the original values (JSON snapshot of what
        was on the bill when the correction was requested).
        review_note documents the reviewer's decision reasoning.
        All actor references and timestamps are preserved forever.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bill = models.ForeignKey(
        Bill,
        on_delete=models.PROTECT,
        related_name="correction_requests",
        help_text="The finalized bill this correction targets.",
    )

    # -------------------------------------------------------------------------
    # Request
    # -------------------------------------------------------------------------
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_bill_corrections",
    )
    correction_type = models.CharField(
        max_length=30,
        choices=CorrectionType.choices,
        db_index=True,
    )
    reason = models.TextField(
        help_text="Required reason for the correction request. Must be descriptive.",
    )
    requested_data = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Snapshot of the bill's financial values at the time the correction "
            "was requested. Stored for audit/comparison purposes. "
            "Structure: {bill_number, subtotal, discount_amount, tax_amount, "
            "grand_total, items: [...]}."
        ),
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=CorrectionStatus.choices,
        default=CorrectionStatus.PENDING,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Review
    # -------------------------------------------------------------------------
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_bill_corrections",
        help_text=(
            "The user who approved or rejected this correction. "
            "Must NOT be the same as requested_by (enforced in service layer)."
        ),
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the correction was reviewed.",
    )
    review_note = models.TextField(
        blank=True,
        help_text="Reviewer's note explaining approval or rejection decision.",
    )

    class Meta:
        verbose_name = "Bill Correction Request"
        verbose_name_plural = "Bill Correction Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["bill", "status"]),
            models.Index(fields=["bill", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["requested_by", "status"]),
            models.Index(fields=["reviewed_by", "status"]),
        ]

    def __str__(self):
        return (
            f"Correction [{self.correction_type}] for {self.bill.bill_number} "
            f"— {self.status}"
        )

    @property
    def is_pending(self) -> bool:
        return self.status == CorrectionStatus.PENDING
