# =============================================================================
# RestaurantFlow — Financials Models
# Phase 12: Financial Operations
#
# Model hierarchy:
#   ExpenseCategory          — restaurant-scoped category definitions
#   ExpenseSequence          — concurrency-safe EXP number generation
#   Expense                  — general operating expense record
#   ExpenseApproval          — approval request/review record
#   ExpenseCorrectionRequest — controlled mutation of approved expenses
#   ExpenseAttachment        — supporting documents for an expense
#   RecurringExpense         — recurring expense template (NOT a transaction)
#   SupplierInvoiceSequence  — concurrency-safe SINV number generation
#   SupplierInvoice          — payable from inventory purchase
#   Payable                  — generic financial obligation abstraction
#   FinancialAuditLog        — immutable append-only financial audit trail
#
# Design principles:
#   - UUID primary keys on all models.
#   - All monetary values use DecimalField — NEVER float.
#   - Expense records are immutable once APPROVED; corrections are separate.
#   - Sequence models use select_for_update() in the service layer.
#   - Payable records prevent duplicates via unique source constraints.
#   - Audit log rows cannot be updated after creation.
#   - Organization isolation enforced via Restaurant/Branch scoping.
#   - Attachments stored under media/expense_attachments/ with no public access.
#   - RecurringExpense is a template — generates Expense records on schedule.
#   - SupplierInvoice references existing inventory.PurchaseOrder (no duplication).
#   - Payable.remaining_amount = amount - paid_amount (never negative).
# =============================================================================

import os
import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel
from financials.constants import (
    EXPENSE_STATUS_CHOICES, EXPENSE_DRAFT,
    EXPENSE_PAYMENT_STATUS_CHOICES, PAYMENT_STATUS_UNPAID,
    APPROVAL_STATUS_CHOICES, APPROVAL_PENDING,
    CORRECTION_STATUS_CHOICES, CORRECTION_PENDING,
    CORRECTION_TYPE_CHOICES,
    FREQUENCY_CHOICES,
    SUPPLIER_INVOICE_STATUS_CHOICES, SINV_DRAFT,
    PAYABLE_TYPE_CHOICES,
    PAYABLE_STATUS_CHOICES, PAYABLE_OPEN,
    AUDIT_ACTION_CHOICES,
)

logger = logging.getLogger("financials")


# =============================================================================
# ExpenseCategory
# =============================================================================

class ExpenseCategory(TimestampedModel):
    """
    Restaurant-scoped category for expenses.

    Examples: RENT, ELECTRICITY, SALARY, MAINTENANCE, TRANSPORT.
    Category code must be unique within the restaurant.
    Inactive categories cannot be used for new expenses, but existing records
    that reference them remain intact.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="expense_categories",
        db_index=True,
    )
    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=30,
        db_index=True,
        help_text="Short identifier, unique within the restaurant. e.g. RENT, ELEC, SALARY.",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "Expense Category"
        verbose_name_plural = "Expense Categories"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_expense_category_code_per_restaurant",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["restaurant", "code"]),
        ]

    def __str__(self):
        return f"{self.name} [{self.code}] ({self.restaurant.name})"


# =============================================================================
# ExpenseSequence
# =============================================================================

class ExpenseSequence(TimestampedModel):
    """
    Concurrency-safe expense number sequence per restaurant.

    One row per restaurant. select_for_update() is used in the service.
    Format: EXP-{seq:06d}  e.g. EXP-000001

    Never uses MAX()+1 — always uses DB-level locking.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.OneToOneField(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="expense_sequence",
    )
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Expense Sequence"
        verbose_name_plural = "Expense Sequences"

    def __str__(self):
        return f"ExpenseSeq restaurant={self.restaurant.name} seq={self.last_sequence}"


# =============================================================================
# Expense
# =============================================================================

class Expense(TimestampedModel):
    """
    A general operating expense record.

    Represents money spent or owed by the restaurant for operational costs
    such as rent, utilities, salaries, maintenance, etc.

    IMPORTANT: This is NOT an inventory purchase. Inventory purchases create
    SupplierInvoice records via the Purchase → Receive → Invoice workflow.

    Status lifecycle:
        DRAFT → SUBMITTED → APPROVED
        DRAFT → CANCELLED
        SUBMITTED → REJECTED (terminal)
        SUBMITTED → CANCELLED (via service, before approval)

    Immutability:
        APPROVED expenses are immutable financial records.
        Corrections require an ExpenseCorrectionRequest.

    Financial fields (all Decimal — backend-authoritative):
        amount       = base expense amount before tax
        tax_amount   = tax portion
        total_amount = amount + tax_amount (backend-calculated; never trust frontend)

    Payment status is tracked separately from approval status:
        UNPAID → PARTIALLY_PAID → PAID
    Payment recording is prepared for a future financial payment workflow.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Scope
    # -------------------------------------------------------------------------
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="expenses",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="expenses",
        null=True,
        blank=True,
        db_index=True,
        help_text="The branch this expense belongs to (optional for restaurant-level expenses).",
    )

    # -------------------------------------------------------------------------
    # Identity
    # -------------------------------------------------------------------------
    expense_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Human-readable expense number. Format: EXP-NNNNNN. Immutable once created.",
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="expenses",
        db_index=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # -------------------------------------------------------------------------
    # Financial fields — all Decimal; backend-authoritative
    # -------------------------------------------------------------------------
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Base expense amount before tax. Backend-authoritative.",
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text="Tax portion. Backend-authoritative.",
    )
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text="total = amount + tax_amount. Computed by backend; never trust frontend.",
    )

    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------
    expense_date = models.DateField(
        help_text="The date the expense was incurred.",
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Payment due date (optional).",
    )

    # -------------------------------------------------------------------------
    # Vendor information
    # -------------------------------------------------------------------------
    vendor_name = models.CharField(max_length=200, blank=True)
    vendor_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Vendor's own reference number (e.g. their invoice number).",
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=EXPENSE_STATUS_CHOICES,
        default=EXPENSE_DRAFT,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=EXPENSE_PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_UNPAID,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Actors and timestamps
    # -------------------------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_expenses",
        help_text="User who originally created the expense.",
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="submitted_expenses",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_expenses",
    )
    rejected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="rejected_expenses",
    )

    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at  = models.DateTimeField(null=True, blank=True)
    rejected_at  = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=0),
                name="expense_amount_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(tax_amount__gte=0),
                name="expense_tax_amount_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name="expense_total_amount_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "payment_status"]),
            models.Index(fields=["branch", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["expense_date"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["created_by"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["expense_number"]),
        ]

    def __str__(self):
        return f"{self.expense_number} — {self.title} [{self.status}]"

    @property
    def is_editable(self) -> bool:
        """Only DRAFT expenses can be directly edited."""
        return self.status == EXPENSE_DRAFT


# =============================================================================
# ExpenseApproval
# =============================================================================

class ExpenseApproval(TimestampedModel):
    """
    An approval request / review record for an Expense.

    Created when an expense is submitted. Tracks who requested approval,
    who reviewed it, and the outcome.

    One Expense can have multiple approval attempts if it gets rejected
    and resubmitted (via a future workflow). For Phase 12, one Expense →
    one active ExpenseApproval.

    The person who submits the expense must not approve their own expense
    (enforced in the service layer).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="approvals",
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expense_approval_requests",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense_approvals_reviewed",
    )
    status = models.CharField(
        max_length=20,
        choices=APPROVAL_STATUS_CHOICES,
        default=APPROVAL_PENDING,
        db_index=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approval_note = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Expense Approval"
        verbose_name_plural = "Expense Approvals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expense", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"Approval for {self.expense.expense_number} [{self.status}]"


# =============================================================================
# ExpenseCorrectionRequest
# =============================================================================

class ExpenseCorrectionRequest(TimestampedModel):
    """
    A controlled request to mutate an APPROVED expense record.

    APPROVED expenses are immutable financial records.
    Any change requires an ExpenseCorrectionRequest to be submitted,
    reviewed, and approved before the underlying expense is modified.

    correction_type identifies the nature of the change.
    requested_data is a JSON snapshot of the proposed changes.
    The actual mutation happens inside a transaction when the correction
    is approved (see services.ExpenseCorrectionService.approve_correction).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="corrections",
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expense_corrections_requested",
    )
    correction_type = models.CharField(
        max_length=30,
        choices=CORRECTION_TYPE_CHOICES,
        db_index=True,
    )
    requested_data = models.JSONField(
        default=dict,
        help_text="JSON snapshot of proposed changes.",
    )
    reason = models.TextField(help_text="Why this correction is needed.")

    status = models.CharField(
        max_length=20,
        choices=CORRECTION_STATUS_CHOICES,
        default=CORRECTION_PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="expense_corrections_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    class Meta:
        verbose_name = "Expense Correction Request"
        verbose_name_plural = "Expense Correction Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["expense", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return (
            f"Correction ({self.correction_type}) for "
            f"{self.expense.expense_number} [{self.status}]"
        )


# =============================================================================
# ExpenseAttachment
# =============================================================================

def _expense_attachment_upload_path(instance, filename):
    """
    Upload supporting documents to a scoped directory.
    Path: expense_attachments/{restaurant_id}/{expense_id}/{filename}
    Never exposes arbitrary filesystem paths.
    """
    ext = os.path.splitext(filename)[1].lower()
    safe_filename = f"{uuid.uuid4()}{ext}"
    return os.path.join(
        "expense_attachments",
        str(instance.expense.restaurant_id),
        str(instance.expense_id),
        safe_filename,
    )


class ExpenseAttachment(TimestampedModel):
    """
    A supporting document (receipt, invoice, quote, bill) for an Expense.

    Security:
        - Authenticated access only (never publicly accessible).
        - Scope validation: user must have access to the expense's restaurant.
        - File size validated against MAX_ATTACHMENT_SIZE_BYTES.
        - MIME type / extension validated against ALLOWED_ATTACHMENT_* lists.
        - Uploaded files are never executed.
        - Filenames are randomised (UUID-based) on upload.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name="attachments",
        db_index=True,
    )
    file = models.FileField(
        upload_to=_expense_attachment_upload_path,
        help_text="The uploaded supporting document.",
    )
    file_name = models.CharField(
        max_length=255,
        help_text="Original filename as uploaded by the user.",
    )
    file_type = models.CharField(
        max_length=100,
        help_text="MIME type of the uploaded file.",
    )
    file_size = models.PositiveIntegerField(
        help_text="File size in bytes.",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="expense_attachments",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Expense Attachment"
        verbose_name_plural = "Expense Attachments"
        ordering = ["-uploaded_at"]
        indexes = [
            models.Index(fields=["expense"]),
            models.Index(fields=["uploaded_by"]),
        ]

    def __str__(self):
        return f"{self.file_name} → {self.expense.expense_number}"


# =============================================================================
# RecurringExpense
# =============================================================================

class RecurringExpense(TimestampedModel):
    """
    A recurring expense template.

    IMPORTANT: This is a TEMPLATE, not a financial transaction.
    It does NOT itself represent money spent. When a RecurringExpense
    is due, the service generates a new Expense record which then goes
    through the normal approval workflow.

    The generated Expense starts in DRAFT status — never APPROVED.

    next_run_date tracks when the next Expense should be generated.
    It is updated each time a generation occurs.

    Celery integration: RecurringExpenseService.generate_due_expenses()
    is designed to be called from a periodic Celery task. The scheduler
    infrastructure is prepared (see services.py) but Celery wiring is
    left for Phase 13+ infrastructure task.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="recurring_expenses",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="recurring_expenses",
        null=True,
        blank=True,
        db_index=True,
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name="recurring_expenses",
        db_index=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    # Financial fields — Decimal only
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Base amount for the generated expense.",
    )
    tax_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
    )

    # Recurrence configuration
    frequency = models.CharField(
        max_length=20,
        choices=FREQUENCY_CHOICES,
        db_index=True,
    )
    start_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True,
        help_text="If set, no new expenses are generated after this date.",
    )
    next_run_date = models.DateField(
        db_index=True,
        help_text="Next date the system should generate an Expense from this template.",
    )
    is_active = models.BooleanField(default=True, db_index=True)

    # Actor
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_recurring_expenses",
    )

    class Meta:
        verbose_name = "Recurring Expense"
        verbose_name_plural = "Recurring Expenses"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(amount__gte=0),
                name="recurring_expense_amount_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
            models.Index(fields=["next_run_date", "is_active"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.frequency}) — {self.restaurant.name}"


# =============================================================================
# SupplierInvoiceSequence
# =============================================================================

class SupplierInvoiceSequence(TimestampedModel):
    """
    Concurrency-safe supplier invoice sequence per restaurant.

    One row per restaurant. Uses select_for_update() in service layer.
    Format: SINV-{seq:06d}  e.g. SINV-000001
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    restaurant = models.OneToOneField(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="supplier_invoice_sequence",
    )
    last_sequence = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Supplier Invoice Sequence"
        verbose_name_plural = "Supplier Invoice Sequences"

    def __str__(self):
        return f"SINVSeq restaurant={self.restaurant.name} seq={self.last_sequence}"


# =============================================================================
# SupplierInvoice
# =============================================================================

class SupplierInvoice(TimestampedModel):
    """
    A supplier invoice / accounts payable record generated from an
    inventory purchase.

    IMPORTANT:
        - Supplier and PurchaseOrder exist in the inventory app. We reference
          them here by FK — we do NOT recreate them.
        - The inventory receiving workflow remains in the inventory app.
        - SupplierInvoice represents the FINANCIAL OBLIGATION arising from
          a confirmed goods receipt.

    invoice_number is our internal number (SINV-NNNNNN).
    external_invoice_number is the supplier's own invoice number (their ref).

    Status lifecycle:
        DRAFT → SUBMITTED → APPROVED → PARTIALLY_PAID / PAID
        Any non-terminal → CANCELLED

    Financial fields (all Decimal — backend-authoritative):
        subtotal        = sum of received goods value
        tax_amount      = total tax on the invoice
        discount_amount = any agreed discount
        total_amount    = subtotal + tax_amount - discount_amount

    Backend validates all totals — frontend values are never trusted.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Scope
    # -------------------------------------------------------------------------
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="supplier_invoices",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="supplier_invoices",
        null=True,
        blank=True,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Source references — reuse existing inventory models
    # -------------------------------------------------------------------------
    supplier = models.ForeignKey(
        "inventory.Supplier",
        on_delete=models.PROTECT,
        related_name="supplier_invoices",
        db_index=True,
    )
    purchase_order = models.ForeignKey(
        "inventory.PurchaseOrder",
        on_delete=models.PROTECT,
        related_name="supplier_invoices",
        null=True,
        blank=True,
        db_index=True,
        help_text="The PurchaseOrder this invoice is for. Null for manual invoices.",
    )

    # -------------------------------------------------------------------------
    # Invoice numbers
    # -------------------------------------------------------------------------
    invoice_number = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Internal invoice number. Format: SINV-NNNNNN. Immutable.",
    )
    external_invoice_number = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
        help_text="The supplier's own invoice number (their reference).",
    )

    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------
    invoice_date = models.DateField()
    due_date = models.DateField(
        null=True,
        blank=True,
        help_text="Payment due date.",
    )

    # -------------------------------------------------------------------------
    # Financial fields — all Decimal; backend-authoritative
    # -------------------------------------------------------------------------
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=2, default="0.00",
    )
    tax_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default="0.00",
    )
    discount_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default="0.00",
    )
    total_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default="0.00",
        help_text="subtotal + tax_amount - discount_amount. Backend-computed.",
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=SUPPLIER_INVOICE_STATUS_CHOICES,
        default=SINV_DRAFT,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Actors
    # -------------------------------------------------------------------------
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_supplier_invoices",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_supplier_invoices",
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Supplier Invoice"
        verbose_name_plural = "Supplier Invoices"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(subtotal__gte=0),
                name="sinv_subtotal_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(tax_amount__gte=0),
                name="sinv_tax_amount_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(discount_amount__gte=0),
                name="sinv_discount_amount_non_negative",
            ),
            models.CheckConstraint(
                check=models.Q(total_amount__gte=0),
                name="sinv_total_amount_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["supplier", "status"]),
            models.Index(fields=["purchase_order"]),
            models.Index(fields=["invoice_number"]),
            models.Index(fields=["external_invoice_number"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.invoice_number} [{self.status}] — {self.supplier.name}"


# =============================================================================
# Payable
# =============================================================================

class Payable(TimestampedModel):
    """
    A generic financial obligation abstraction.

    A Payable represents money owed by the restaurant.
    It can arise from two sources:
        SUPPLIER_INVOICE — created from a SupplierInvoice (inventory purchase)
        EXPENSE          — created from an approved Expense

    Financial invariants:
        remaining_amount = amount - paid_amount
        paid_amount <= amount      (enforced by CheckConstraint)
        remaining_amount >= 0      (enforced by CheckConstraint)

    Overdue logic (derived, never manually toggled):
        remaining_amount > 0 AND due_date < today → OVERDUE

    Duplicate prevention:
        A Payable cannot be created twice for the same source document.
        UniqueConstraints on (supplier_invoice) and (expense) prevent duplicates.
        Backend service enforces this before creation.

    Payments against payables are tracked via paid_amount, which is updated
    when a future Financial Payment is recorded (Phase 13+).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # -------------------------------------------------------------------------
    # Scope
    # -------------------------------------------------------------------------
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="payables",
        db_index=True,
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        related_name="payables",
        null=True,
        blank=True,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Source reference — exactly ONE must be set
    # -------------------------------------------------------------------------
    payable_type = models.CharField(
        max_length=20,
        choices=PAYABLE_TYPE_CHOICES,
        db_index=True,
    )
    supplier_invoice = models.OneToOneField(
        SupplierInvoice,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payable",
        help_text="Source supplier invoice. Mutually exclusive with expense.",
    )
    expense = models.OneToOneField(
        Expense,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payable",
        help_text="Source expense. Mutually exclusive with supplier_invoice.",
    )

    # -------------------------------------------------------------------------
    # Reference number — human-readable
    # -------------------------------------------------------------------------
    reference_number = models.CharField(
        max_length=30,
        db_index=True,
        help_text="Derived from the source document number (expense_number or invoice_number).",
    )

    # -------------------------------------------------------------------------
    # Financial fields — all Decimal
    # -------------------------------------------------------------------------
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Total amount owed.",
    )
    paid_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text="Amount paid so far. Updated when payments are recorded.",
    )
    remaining_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default="0.00",
        help_text="amount - paid_amount. Backend-maintained.",
    )

    # -------------------------------------------------------------------------
    # Dates
    # -------------------------------------------------------------------------
    due_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
    )

    # -------------------------------------------------------------------------
    # Status
    # -------------------------------------------------------------------------
    status = models.CharField(
        max_length=20,
        choices=PAYABLE_STATUS_CHOICES,
        default=PAYABLE_OPEN,
        db_index=True,
    )

    class Meta:
        verbose_name = "Payable"
        verbose_name_plural = "Payables"
        ordering = ["-created_at"]
        constraints = [
            # Paid amount cannot exceed total
            models.CheckConstraint(
                check=models.Q(paid_amount__lte=models.F("amount")),
                name="payable_paid_cannot_exceed_amount",
            ),
            # Remaining amount is non-negative
            models.CheckConstraint(
                check=models.Q(remaining_amount__gte=0),
                name="payable_remaining_non_negative",
            ),
            # Amount is positive
            models.CheckConstraint(
                check=models.Q(amount__gt=0),
                name="payable_amount_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "status"]),
            models.Index(fields=["restaurant", "payable_type"]),
            models.Index(fields=["due_date", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["reference_number"]),
        ]

    def __str__(self):
        return f"Payable {self.reference_number} [{self.status}] ₹{self.remaining_amount}"

    def refresh_status(self):
        """
        Derive and update status from financial state and due date.
        Call this after any paid_amount change.
        """
        from django.utils import timezone
        from financials.constants import (
            PAYABLE_PAID, PAYABLE_PARTIALLY_PAID,
            PAYABLE_OPEN, PAYABLE_OVERDUE,
        )
        from decimal import Decimal
        today = timezone.now().date()

        if self.remaining_amount <= Decimal("0.00"):
            self.status = PAYABLE_PAID
        elif self.paid_amount > Decimal("0.00"):
            if self.due_date and today > self.due_date:
                self.status = PAYABLE_OVERDUE
            else:
                self.status = PAYABLE_PARTIALLY_PAID
        else:
            if self.due_date and today > self.due_date:
                self.status = PAYABLE_OVERDUE
            else:
                self.status = PAYABLE_OPEN


# =============================================================================
# FinancialAuditLog
# =============================================================================

class FinancialAuditLog(TimestampedModel):
    """
    Immutable append-only audit trail for every financial state change.

    Once created, a FinancialAuditLog row CANNOT be updated.
    The save() method enforces this by rejecting updates.

    Fields:
        actor       — the user who performed the action
        action      — what happened (from AUDIT_ACTION_CHOICES)
        entity_type — the class/type of the entity (e.g. "Expense")
        entity_id   — UUID of the entity
        restaurant  — scope for multi-tenant isolation
        old_status  — status before the action (nullable)
        new_status  — status after the action (nullable)
        metadata    — JSON blob for additional context (amount, reason, etc.)

    Users must never be able to edit audit history.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="financial_audit_logs",
        db_index=True,
    )
    action = models.CharField(
        max_length=60,
        choices=AUDIT_ACTION_CHOICES,
        db_index=True,
    )
    entity_type = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Class name of the entity. e.g. 'Expense', 'SupplierInvoice', 'Payable'.",
    )
    entity_id = models.UUIDField(
        db_index=True,
        help_text="UUID of the entity.",
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        related_name="financial_audit_logs",
        db_index=True,
        help_text="Restaurant scope for multi-tenant isolation.",
    )
    old_status = models.CharField(max_length=30, blank=True)
    new_status = models.CharField(max_length=30, blank=True)
    metadata = models.JSONField(
        default=dict,
        help_text="Additional context: amount, reason, correction_type, etc.",
    )

    class Meta:
        verbose_name = "Financial Audit Log"
        verbose_name_plural = "Financial Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["restaurant", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def save(self, *args, **kwargs):
        """Prevent updates — audit logs are immutable once created."""
        if self.pk and FinancialAuditLog.objects.filter(pk=self.pk).exists():
            raise ValueError(
                "FinancialAuditLog records are immutable — "
                "they cannot be updated after creation."
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"[{self.action}] {self.entity_type}:{self.entity_id} "
            f"by {self.actor_id} at {self.created_at}"
        )
