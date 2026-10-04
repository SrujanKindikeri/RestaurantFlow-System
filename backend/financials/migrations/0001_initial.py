# =============================================================================
# RestaurantFlow — Financials Initial Migration
# Phase 12
# Generated manually — run: python manage.py migrate
# =============================================================================

import django.db.models.deletion
import django.utils.timezone
import financials.models
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("inventory", "0001_initial"),
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # =====================================================================
        # ExpenseCategory
        # =====================================================================
        migrations.CreateModel(
            name="ExpenseCategory",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("code", models.CharField(db_index=True, help_text="Short identifier, unique within the restaurant.", max_length=30)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expense_categories",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={"verbose_name": "Expense Category", "verbose_name_plural": "Expense Categories", "ordering": ["name"]},
        ),
        migrations.AddConstraint(
            model_name="expensecategory",
            constraint=models.UniqueConstraint(
                fields=["restaurant", "code"],
                name="unique_expense_category_code_per_restaurant",
            ),
        ),
        migrations.AddIndex(
            model_name="expensecategory",
            index=models.Index(fields=["restaurant", "is_active"], name="financials__restaur_6a8e3f_idx"),
        ),
        migrations.AddIndex(
            model_name="expensecategory",
            index=models.Index(fields=["restaurant", "code"], name="financials__restaur_7b9d4e_idx"),
        ),

        # =====================================================================
        # ExpenseSequence
        # =====================================================================
        migrations.CreateModel(
            name="ExpenseSequence",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("last_sequence", models.PositiveIntegerField(default=0)),
                (
                    "restaurant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expense_sequence",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={"verbose_name": "Expense Sequence", "verbose_name_plural": "Expense Sequences"},
        ),

        # =====================================================================
        # Expense
        # =====================================================================
        migrations.CreateModel(
            name="Expense",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("expense_number", models.CharField(db_index=True, max_length=20, unique=True)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("tax_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("expense_date", models.DateField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("vendor_name", models.CharField(blank=True, max_length=200)),
                ("vendor_reference", models.CharField(blank=True, max_length=100)),
                ("status", models.CharField(choices=[("DRAFT","Draft"),("SUBMITTED","Submitted"),("APPROVED","Approved"),("REJECTED","Rejected"),("CANCELLED","Cancelled")], db_index=True, default="DRAFT", max_length=20)),
                ("payment_status", models.CharField(choices=[("UNPAID","Unpaid"),("PARTIALLY_PAID","Partially Paid"),("PAID","Paid")], db_index=True, default="UNPAID", max_length=20)),
                ("submitted_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                ("rejection_reason", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True, db_index=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expenses",
                        to="organizations.branch",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expenses",
                        to="financials.expensecategory",
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_expenses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_expenses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "rejected_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="rejected_expenses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expenses",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "submitted_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="submitted_expenses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Expense", "verbose_name_plural": "Expenses", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="expense",
            constraint=models.CheckConstraint(check=models.Q(amount__gte=0), name="expense_amount_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="expense",
            constraint=models.CheckConstraint(check=models.Q(tax_amount__gte=0), name="expense_tax_amount_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="expense",
            constraint=models.CheckConstraint(check=models.Q(total_amount__gte=0), name="expense_total_amount_non_negative"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["restaurant", "status"], name="financials__restaur_exp_idx1"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["restaurant", "payment_status"], name="financials__restaur_exp_idx2"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["branch", "status"], name="financials__branch_exp_idx1"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["expense_date"], name="financials__exp_date_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["due_date"], name="financials__due_date_idx"),
        ),
        migrations.AddIndex(
            model_name="expense",
            index=models.Index(fields=["status", "created_at"], name="financials__status_created_exp_idx"),
        ),

        # =====================================================================
        # ExpenseApproval
        # =====================================================================
        migrations.CreateModel(
            name="ExpenseApproval",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("PENDING","Pending"),("APPROVED","Approved"),("REJECTED","Rejected"),("CANCELLED","Cancelled")], db_index=True, default="PENDING", max_length=20)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("approval_note", models.TextField(blank=True)),
                ("rejection_reason", models.TextField(blank=True)),
                (
                    "expense",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="approvals",
                        to="financials.expense",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expense_approval_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expense_approvals_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Expense Approval", "verbose_name_plural": "Expense Approvals", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="expenseapproval",
            index=models.Index(fields=["expense", "status"], name="financials__exp_appr_idx1"),
        ),

        # =====================================================================
        # ExpenseCorrectionRequest
        # =====================================================================
        migrations.CreateModel(
            name="ExpenseCorrectionRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("correction_type", models.CharField(choices=[("AMOUNT_CORRECTION","Amount Correction"),("CATEGORY_CORRECTION","Category Correction"),("DATE_CORRECTION","Date Correction"),("VENDOR_CORRECTION","Vendor Correction"),("CANCELLATION","Cancellation"),("OTHER","Other")], db_index=True, max_length=30)),
                ("requested_data", models.JSONField(default=dict)),
                ("reason", models.TextField()),
                ("status", models.CharField(choices=[("PENDING","Pending"),("APPROVED","Approved"),("REJECTED","Rejected"),("CANCELLED","Cancelled")], db_index=True, default="PENDING", max_length=20)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.TextField(blank=True)),
                (
                    "expense",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="corrections",
                        to="financials.expense",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expense_corrections_requested",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expense_corrections_reviewed",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Expense Correction Request", "verbose_name_plural": "Expense Correction Requests", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="expensecorrectionrequest",
            index=models.Index(fields=["expense", "status"], name="financials__exp_corr_idx1"),
        ),

        # =====================================================================
        # ExpenseAttachment
        # =====================================================================
        migrations.CreateModel(
            name="ExpenseAttachment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("file", models.FileField(upload_to=financials.models._expense_attachment_upload_path)),
                ("file_name", models.CharField(max_length=255)),
                ("file_type", models.CharField(max_length=100)),
                ("file_size", models.PositiveIntegerField()),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "expense",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="financials.expense",
                    ),
                ),
                (
                    "uploaded_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="expense_attachments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"verbose_name": "Expense Attachment", "verbose_name_plural": "Expense Attachments", "ordering": ["-uploaded_at"]},
        ),
        migrations.AddIndex(
            model_name="expenseattachment",
            index=models.Index(fields=["expense"], name="financials__exp_att_idx1"),
        ),

        # =====================================================================
        # RecurringExpense
        # =====================================================================
        migrations.CreateModel(
            name="RecurringExpense",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("tax_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("frequency", models.CharField(choices=[("WEEKLY","Weekly"),("MONTHLY","Monthly"),("QUARTERLY","Quarterly"),("YEARLY","Yearly")], db_index=True, max_length=20)),
                ("start_date", models.DateField()),
                ("end_date", models.DateField(blank=True, null=True)),
                ("next_run_date", models.DateField(db_index=True)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True, db_index=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recurring_expenses",
                        to="organizations.branch",
                    ),
                ),
                (
                    "category",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recurring_expenses",
                        to="financials.expensecategory",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_recurring_expenses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="recurring_expenses",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={"verbose_name": "Recurring Expense", "verbose_name_plural": "Recurring Expenses", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="recurringexpense",
            constraint=models.CheckConstraint(check=models.Q(amount__gte=0), name="recurring_expense_amount_non_negative"),
        ),
        migrations.AddIndex(
            model_name="recurringexpense",
            index=models.Index(fields=["restaurant", "is_active"], name="financials__recur_rest_idx"),
        ),
        migrations.AddIndex(
            model_name="recurringexpense",
            index=models.Index(fields=["next_run_date", "is_active"], name="financials__next_run_idx"),
        ),

        # =====================================================================
        # SupplierInvoiceSequence
        # =====================================================================
        migrations.CreateModel(
            name="SupplierInvoiceSequence",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("last_sequence", models.PositiveIntegerField(default=0)),
                (
                    "restaurant",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_invoice_sequence",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={"verbose_name": "Supplier Invoice Sequence", "verbose_name_plural": "Supplier Invoice Sequences"},
        ),

        # =====================================================================
        # SupplierInvoice
        # =====================================================================
        migrations.CreateModel(
            name="SupplierInvoice",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("invoice_number", models.CharField(db_index=True, max_length=20, unique=True)),
                ("external_invoice_number", models.CharField(blank=True, db_index=True, max_length=100)),
                ("invoice_date", models.DateField()),
                ("due_date", models.DateField(blank=True, null=True)),
                ("subtotal", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("tax_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("discount_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("total_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("status", models.CharField(choices=[("DRAFT","Draft"),("SUBMITTED","Submitted"),("APPROVED","Approved"),("PARTIALLY_PAID","Partially Paid"),("PAID","Paid"),("CANCELLED","Cancelled")], db_index=True, default="DRAFT", max_length=20)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_supplier_invoices",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True, db_index=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_invoices",
                        to="organizations.branch",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_supplier_invoices",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "purchase_order",
                    models.ForeignKey(
                        blank=True, db_index=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_invoices",
                        to="inventory.purchaseorder",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_invoices",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "supplier",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="supplier_invoices",
                        to="inventory.supplier",
                    ),
                ),
            ],
            options={"verbose_name": "Supplier Invoice", "verbose_name_plural": "Supplier Invoices", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="supplierinvoice",
            constraint=models.CheckConstraint(check=models.Q(subtotal__gte=0), name="sinv_subtotal_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="supplierinvoice",
            constraint=models.CheckConstraint(check=models.Q(tax_amount__gte=0), name="sinv_tax_amount_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="supplierinvoice",
            constraint=models.CheckConstraint(check=models.Q(discount_amount__gte=0), name="sinv_discount_amount_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="supplierinvoice",
            constraint=models.CheckConstraint(check=models.Q(total_amount__gte=0), name="sinv_total_amount_non_negative"),
        ),
        migrations.AddIndex(
            model_name="supplierinvoice",
            index=models.Index(fields=["restaurant", "status"], name="financials__sinv_rest_idx"),
        ),
        migrations.AddIndex(
            model_name="supplierinvoice",
            index=models.Index(fields=["supplier", "status"], name="financials__sinv_supp_idx"),
        ),
        migrations.AddIndex(
            model_name="supplierinvoice",
            index=models.Index(fields=["due_date"], name="financials__sinv_due_idx"),
        ),
        migrations.AddIndex(
            model_name="supplierinvoice",
            index=models.Index(fields=["status", "created_at"], name="financials__sinv_status_idx"),
        ),

        # =====================================================================
        # Payable
        # =====================================================================
        migrations.CreateModel(
            name="Payable",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("payable_type", models.CharField(choices=[("SUPPLIER_INVOICE","Supplier Invoice"),("EXPENSE","Expense")], db_index=True, max_length=20)),
                ("reference_number", models.CharField(db_index=True, max_length=30)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=14)),
                ("paid_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("remaining_amount", models.DecimalField(decimal_places=2, default="0.00", max_digits=14)),
                ("due_date", models.DateField(blank=True, db_index=True, null=True)),
                ("status", models.CharField(choices=[("OPEN","Open"),("PARTIALLY_PAID","Partially Paid"),("PAID","Paid"),("OVERDUE","Overdue"),("CANCELLED","Cancelled")], db_index=True, default="OPEN", max_length=20)),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True, db_index=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payables",
                        to="organizations.branch",
                    ),
                ),
                (
                    "expense",
                    models.OneToOneField(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payable",
                        to="financials.expense",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payables",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "supplier_invoice",
                    models.OneToOneField(
                        blank=True, null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payable",
                        to="financials.supplierinvoice",
                    ),
                ),
            ],
            options={"verbose_name": "Payable", "verbose_name_plural": "Payables", "ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="payable",
            constraint=models.CheckConstraint(check=models.Q(paid_amount__lte=models.F("amount")), name="payable_paid_cannot_exceed_amount"),
        ),
        migrations.AddConstraint(
            model_name="payable",
            constraint=models.CheckConstraint(check=models.Q(remaining_amount__gte=0), name="payable_remaining_non_negative"),
        ),
        migrations.AddConstraint(
            model_name="payable",
            constraint=models.CheckConstraint(check=models.Q(amount__gt=0), name="payable_amount_positive"),
        ),
        migrations.AddIndex(
            model_name="payable",
            index=models.Index(fields=["restaurant", "status"], name="financials__payable_rest_idx"),
        ),
        migrations.AddIndex(
            model_name="payable",
            index=models.Index(fields=["restaurant", "payable_type"], name="financials__payable_type_idx"),
        ),
        migrations.AddIndex(
            model_name="payable",
            index=models.Index(fields=["due_date", "status"], name="financials__payable_due_idx"),
        ),
        migrations.AddIndex(
            model_name="payable",
            index=models.Index(fields=["status", "created_at"], name="financials__payable_status_idx"),
        ),

        # =====================================================================
        # FinancialAuditLog
        # =====================================================================
        migrations.CreateModel(
            name="FinancialAuditLog",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(db_index=True, max_length=60)),
                ("entity_type", models.CharField(db_index=True, max_length=50)),
                ("entity_id", models.UUIDField(db_index=True)),
                ("old_status", models.CharField(blank=True, max_length=30)),
                ("new_status", models.CharField(blank=True, max_length=30)),
                ("metadata", models.JSONField(default=dict)),
                (
                    "actor",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="financial_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="financial_audit_logs",
                        to="organizations.restaurant",
                    ),
                ),
            ],
            options={"verbose_name": "Financial Audit Log", "verbose_name_plural": "Financial Audit Logs", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="financialauditlog",
            index=models.Index(fields=["entity_type", "entity_id"], name="financials__audit_entity_idx"),
        ),
        migrations.AddIndex(
            model_name="financialauditlog",
            index=models.Index(fields=["actor", "created_at"], name="financials__audit_actor_idx"),
        ),
        migrations.AddIndex(
            model_name="financialauditlog",
            index=models.Index(fields=["restaurant", "created_at"], name="financials__audit_rest_idx"),
        ),
        migrations.AddIndex(
            model_name="financialauditlog",
            index=models.Index(fields=["action", "created_at"], name="financials__audit_action_idx"),
        ),
    ]
