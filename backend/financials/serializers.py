# =============================================================================
# RestaurantFlow — Financials Serializers
# Phase 12
#
# Serializers validate input shapes and produce API-safe output.
# Business logic (calculations, state transitions) stays in services.py.
# Frontend-supplied totals are NEVER trusted for monetary calculations.
# =============================================================================

from decimal import Decimal
from rest_framework import serializers

from financials.models import (
    ExpenseCategory,
    Expense,
    ExpenseApproval,
    ExpenseCorrectionRequest,
    ExpenseAttachment,
    RecurringExpense,
    SupplierInvoice,
    Payable,
    FinancialAuditLog,
)
from financials.constants import (
    CORRECTION_TYPE_CHOICES,
    FREQUENCY_CHOICES,
    EXPENSE_STATUS_CHOICES,
    EXPENSE_PAYMENT_STATUS_CHOICES,
    SUPPLIER_INVOICE_STATUS_CHOICES,
    PAYABLE_STATUS_CHOICES,
    PAYABLE_TYPE_CHOICES,
    MAX_ATTACHMENT_SIZE_MB,
)

ZERO = Decimal("0.00")


# =============================================================================
# Shared nested serializers
# =============================================================================

class UserMinimalSerializer(serializers.Serializer):
    """Minimal user representation for nested display."""
    id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.CharField()


# =============================================================================
# ExpenseCategory
# =============================================================================

class ExpenseCategorySerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = ExpenseCategory
        fields = [
            "id", "restaurant", "restaurant_name",
            "name", "code", "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "restaurant_name", "created_at", "updated_at"]


class CreateExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["restaurant", "name", "code", "description", "is_active"]

    def validate_code(self, value):
        return value.strip().upper()

    def validate_name(self, value):
        return value.strip()

    def validate(self, attrs):
        restaurant = attrs.get("restaurant")
        code = attrs.get("code", "").upper()
        if restaurant and code:
            qs = ExpenseCategory.objects.filter(restaurant=restaurant, code=code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"code": f"Category code '{code}' already exists for this restaurant."}
                )
        return attrs


class UpdateExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["name", "description", "is_active"]

    def validate_name(self, value):
        return value.strip()


# =============================================================================
# ExpenseApproval
# =============================================================================

class ExpenseApprovalSerializer(serializers.ModelSerializer):
    requested_by_detail = UserMinimalSerializer(source="requested_by", read_only=True)
    reviewed_by_detail  = UserMinimalSerializer(source="reviewed_by",  read_only=True)

    class Meta:
        model = ExpenseApproval
        fields = [
            "id", "expense", "status",
            "requested_by", "requested_by_detail",
            "reviewed_by",  "reviewed_by_detail",
            "reviewed_at", "approval_note", "rejection_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


# =============================================================================
# ExpenseAttachment
# =============================================================================

class ExpenseAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_detail = UserMinimalSerializer(source="uploaded_by", read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = ExpenseAttachment
        fields = [
            "id", "expense",
            "file", "file_url", "file_name", "file_type", "file_size",
            "uploaded_by", "uploaded_by_detail",
            "uploaded_at",
        ]
        read_only_fields = [
            "id", "file_url", "file_name", "file_type",
            "file_size", "uploaded_by_detail", "uploaded_at",
        ]

    def get_file_url(self, obj):
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None


class UploadAttachmentSerializer(serializers.Serializer):
    """Input for uploading an attachment to an expense."""
    file = serializers.FileField(
        help_text=f"Supported types: PDF, JPG, PNG, WEBP, DOCX, XLSX. Max {MAX_ATTACHMENT_SIZE_MB}MB."
    )


# =============================================================================
# ExpenseCorrectionRequest
# =============================================================================

class ExpenseCorrectionRequestSerializer(serializers.ModelSerializer):
    requested_by_detail = UserMinimalSerializer(source="requested_by", read_only=True)
    reviewed_by_detail  = UserMinimalSerializer(source="reviewed_by",  read_only=True)
    expense_number = serializers.CharField(source="expense.expense_number", read_only=True)

    class Meta:
        model = ExpenseCorrectionRequest
        fields = [
            "id", "expense", "expense_number",
            "requested_by", "requested_by_detail",
            "correction_type", "requested_data", "reason",
            "status",
            "reviewed_by", "reviewed_by_detail",
            "reviewed_at", "review_note",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "expense_number", "requested_by_detail", "reviewed_by_detail",
            "status", "reviewed_by", "reviewed_at", "review_note",
            "created_at", "updated_at",
        ]


class CreateCorrectionRequestSerializer(serializers.Serializer):
    correction_type = serializers.ChoiceField(choices=CORRECTION_TYPE_CHOICES)
    requested_data  = serializers.DictField(child=serializers.CharField(allow_blank=True))
    reason          = serializers.CharField(min_length=10)


class ReviewCorrectionSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=False, allow_blank=True, default="")


class RejectCorrectionSerializer(serializers.Serializer):
    review_note = serializers.CharField(min_length=5)


# =============================================================================
# Expense — list / detail
# =============================================================================

class ExpenseListSerializer(serializers.ModelSerializer):
    category_name   = serializers.CharField(source="category.name",      read_only=True)
    category_code   = serializers.CharField(source="category.code",      read_only=True)
    branch_name     = serializers.CharField(source="branch.name",        read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name",    read_only=True)
    created_by_email = serializers.CharField(source="created_by.email",  read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id", "expense_number", "restaurant", "restaurant_name",
            "branch", "branch_name",
            "category", "category_name", "category_code",
            "title", "amount", "tax_amount", "total_amount",
            "expense_date", "due_date",
            "vendor_name", "vendor_reference",
            "status", "payment_status",
            "created_by", "created_by_email",
            "submitted_at", "approved_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class ExpenseDetailSerializer(serializers.ModelSerializer):
    category_name    = serializers.CharField(source="category.name",     read_only=True)
    category_code    = serializers.CharField(source="category.code",     read_only=True)
    branch_name      = serializers.CharField(source="branch.name",       read_only=True)
    restaurant_name  = serializers.CharField(source="restaurant.name",   read_only=True)
    created_by_detail  = UserMinimalSerializer(source="created_by",     read_only=True)
    submitted_by_detail = UserMinimalSerializer(source="submitted_by",   read_only=True)
    approved_by_detail  = UserMinimalSerializer(source="approved_by",    read_only=True)
    rejected_by_detail  = UserMinimalSerializer(source="rejected_by",    read_only=True)
    attachments      = ExpenseAttachmentSerializer(many=True, read_only=True)
    approvals        = ExpenseApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id", "expense_number",
            "restaurant", "restaurant_name",
            "branch", "branch_name",
            "category", "category_name", "category_code",
            "title", "description",
            "amount", "tax_amount", "total_amount",
            "expense_date", "due_date",
            "vendor_name", "vendor_reference",
            "status", "payment_status",
            "created_by", "created_by_detail",
            "submitted_by", "submitted_by_detail",
            "approved_by", "approved_by_detail",
            "rejected_by", "rejected_by_detail",
            "submitted_at", "approved_at", "rejected_at",
            "rejection_reason",
            "notes",
            "attachments", "approvals",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class CreateExpenseSerializer(serializers.Serializer):
    """Input for creating a new expense (DRAFT)."""
    restaurant      = serializers.UUIDField()
    branch          = serializers.UUIDField(required=False, allow_null=True)
    category        = serializers.UUIDField()
    title           = serializers.CharField(max_length=200)
    description     = serializers.CharField(required=False, allow_blank=True, default="")
    amount          = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO)
    tax_amount      = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, default=ZERO)
    expense_date    = serializers.DateField()
    due_date        = serializers.DateField(required=False, allow_null=True)
    vendor_name     = serializers.CharField(max_length=200, required=False, allow_blank=True, default="")
    vendor_reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    notes           = serializers.CharField(required=False, allow_blank=True, default="")


class UpdateExpenseSerializer(serializers.Serializer):
    """Input for updating a DRAFT expense."""
    category        = serializers.UUIDField(required=False)
    title           = serializers.CharField(max_length=200, required=False)
    description     = serializers.CharField(required=False, allow_blank=True)
    amount          = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, required=False)
    tax_amount      = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, required=False)
    expense_date    = serializers.DateField(required=False)
    due_date        = serializers.DateField(required=False, allow_null=True)
    vendor_name     = serializers.CharField(max_length=200, required=False, allow_blank=True)
    vendor_reference = serializers.CharField(max_length=100, required=False, allow_blank=True)
    notes           = serializers.CharField(required=False, allow_blank=True)
    branch          = serializers.UUIDField(required=False, allow_null=True)


class ApproveExpenseSerializer(serializers.Serializer):
    approval_note = serializers.CharField(required=False, allow_blank=True, default="")


class RejectExpenseSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(min_length=5)


# =============================================================================
# RecurringExpense
# =============================================================================

class RecurringExpenseSerializer(serializers.ModelSerializer):
    category_name   = serializers.CharField(source="category.name",   read_only=True)
    branch_name     = serializers.CharField(source="branch.name",     read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    created_by_detail = UserMinimalSerializer(source="created_by",    read_only=True)

    class Meta:
        model = RecurringExpense
        fields = [
            "id", "restaurant", "restaurant_name",
            "branch", "branch_name",
            "category", "category_name",
            "title", "description",
            "amount", "tax_amount",
            "frequency", "start_date", "end_date", "next_run_date",
            "is_active",
            "created_by", "created_by_detail",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "restaurant_name", "category_name", "branch_name",
            "created_by_detail", "next_run_date",
            "created_at", "updated_at",
        ]


class CreateRecurringExpenseSerializer(serializers.Serializer):
    restaurant   = serializers.UUIDField()
    branch       = serializers.UUIDField(required=False, allow_null=True)
    category     = serializers.UUIDField()
    title        = serializers.CharField(max_length=200)
    description  = serializers.CharField(required=False, allow_blank=True, default="")
    amount       = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO)
    tax_amount   = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, default=ZERO)
    frequency    = serializers.ChoiceField(choices=FREQUENCY_CHOICES)
    start_date   = serializers.DateField()
    end_date     = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        start = attrs.get("start_date")
        end   = attrs.get("end_date")
        if start and end and end < start:
            raise serializers.ValidationError(
                {"end_date": "end_date cannot be before start_date."}
            )
        return attrs


class UpdateRecurringExpenseSerializer(serializers.Serializer):
    title       = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    amount      = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, required=False)
    tax_amount  = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, required=False)
    frequency   = serializers.ChoiceField(choices=FREQUENCY_CHOICES, required=False)
    end_date    = serializers.DateField(required=False, allow_null=True)
    category    = serializers.UUIDField(required=False)


# =============================================================================
# SupplierInvoice
# =============================================================================

class SupplierInvoiceListSerializer(serializers.ModelSerializer):
    supplier_name   = serializers.CharField(source="supplier.name",     read_only=True)
    branch_name     = serializers.CharField(source="branch.name",       read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name",   read_only=True)
    purchase_number = serializers.CharField(
        source="purchase_order.purchase_number", read_only=True
    )
    created_by_email = serializers.CharField(source="created_by.email", read_only=True)

    class Meta:
        model = SupplierInvoice
        fields = [
            "id", "invoice_number", "external_invoice_number",
            "restaurant", "restaurant_name",
            "branch", "branch_name",
            "supplier", "supplier_name",
            "purchase_order", "purchase_number",
            "invoice_date", "due_date",
            "subtotal", "tax_amount", "discount_amount", "total_amount",
            "status",
            "created_by", "created_by_email",
            "approved_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class SupplierInvoiceDetailSerializer(serializers.ModelSerializer):
    supplier_name    = serializers.CharField(source="supplier.name",     read_only=True)
    branch_name      = serializers.CharField(source="branch.name",       read_only=True)
    restaurant_name  = serializers.CharField(source="restaurant.name",   read_only=True)
    purchase_number  = serializers.CharField(
        source="purchase_order.purchase_number", read_only=True
    )
    created_by_detail  = UserMinimalSerializer(source="created_by",      read_only=True)
    approved_by_detail = UserMinimalSerializer(source="approved_by",     read_only=True)
    payable_id = serializers.SerializerMethodField()

    class Meta:
        model = SupplierInvoice
        fields = [
            "id", "invoice_number", "external_invoice_number",
            "restaurant", "restaurant_name",
            "branch", "branch_name",
            "supplier", "supplier_name",
            "purchase_order", "purchase_number",
            "invoice_date", "due_date",
            "subtotal", "tax_amount", "discount_amount", "total_amount",
            "status",
            "created_by", "created_by_detail",
            "approved_by", "approved_by_detail",
            "approved_at", "notes",
            "payable_id",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_payable_id(self, obj):
        try:
            return str(obj.payable.pk)
        except Exception:
            return None


class CreateSupplierInvoiceSerializer(serializers.Serializer):
    restaurant             = serializers.UUIDField()
    branch                 = serializers.UUIDField(required=False, allow_null=True)
    supplier               = serializers.UUIDField()
    purchase_order         = serializers.UUIDField(required=False, allow_null=True)
    external_invoice_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    invoice_date           = serializers.DateField()
    due_date               = serializers.DateField(required=False, allow_null=True)
    subtotal               = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, default=ZERO)
    tax_amount             = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, default=ZERO)
    discount_amount        = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=ZERO, default=ZERO)
    notes                  = serializers.CharField(required=False, allow_blank=True, default="")


class ApproveInvoiceSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class CancelInvoiceSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


# =============================================================================
# Payable
# =============================================================================

class PayableSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name",     read_only=True)
    branch_name     = serializers.CharField(source="branch.name",         read_only=True)
    supplier_name   = serializers.SerializerMethodField()
    is_overdue      = serializers.SerializerMethodField()

    class Meta:
        model = Payable
        fields = [
            "id", "restaurant", "restaurant_name",
            "branch", "branch_name",
            "payable_type",
            "supplier_invoice", "expense",
            "reference_number",
            "amount", "paid_amount", "remaining_amount",
            "due_date", "status",
            "supplier_name",
            "is_overdue",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_supplier_name(self, obj):
        if obj.payable_type == "SUPPLIER_INVOICE" and obj.supplier_invoice:
            return obj.supplier_invoice.supplier.name
        return None

    def get_is_overdue(self, obj):
        from django.utils import timezone
        if obj.due_date and obj.remaining_amount > Decimal("0.00"):
            return obj.due_date < timezone.now().date()
        return False


class RecordPaymentSerializer(serializers.Serializer):
    payment_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01")
    )


# =============================================================================
# FinancialAuditLog
# =============================================================================

class FinancialAuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(source="actor.email", read_only=True)

    class Meta:
        model = FinancialAuditLog
        fields = [
            "id", "actor", "actor_email",
            "action", "entity_type", "entity_id",
            "restaurant",
            "old_status", "new_status",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields


# =============================================================================
# Dashboard
# =============================================================================

class FinancialDashboardSerializer(serializers.Serializer):
    """Response shape for GET /api/financials/dashboard/"""
    total_expenses      = serializers.IntegerField()
    pending_approval    = serializers.IntegerField()
    approved_expenses   = serializers.IntegerField()
    rejected_expenses   = serializers.IntegerField()
    unpaid_expenses     = serializers.IntegerField()
    partially_paid      = serializers.IntegerField()
    overdue_payables    = serializers.IntegerField()
    total_payable_amount    = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_paid_amount       = serializers.DecimalField(max_digits=16, decimal_places=2)
    total_remaining_amount  = serializers.DecimalField(max_digits=16, decimal_places=2)
    category_summary    = serializers.ListField(child=serializers.DictField())
    branch_summary      = serializers.ListField(child=serializers.DictField())
    recent_expenses     = ExpenseListSerializer(many=True)


class PayableDashboardSerializer(serializers.Serializer):
    """Response shape for GET /api/financials/payables/dashboard/"""
    total_payables      = serializers.IntegerField()
    open_payables       = serializers.IntegerField()
    partially_paid      = serializers.IntegerField()
    paid_payables       = serializers.IntegerField()
    overdue_payables    = serializers.IntegerField()
    total_amount        = serializers.DecimalField(max_digits=16, decimal_places=2)
    paid_amount         = serializers.DecimalField(max_digits=16, decimal_places=2)
    remaining_amount    = serializers.DecimalField(max_digits=16, decimal_places=2)
    by_type             = serializers.ListField(child=serializers.DictField())
