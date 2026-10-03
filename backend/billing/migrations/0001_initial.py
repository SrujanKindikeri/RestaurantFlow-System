# =============================================================================
# RestaurantFlow — Billing Initial Migration
# Phase 8
#
# Models: BillSequence, Bill, BillItem, BillCorrectionRequest
# =============================================================================

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("orders", "0001_initial"),
        ("organizations", "0001_initial"),
        ("menu", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # =====================================================================
        # BillSequence
        # =====================================================================
        migrations.CreateModel(
            name="BillSequence",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "year_key",
                    models.CharField(db_index=True, max_length=4),
                ),
                ("last_sequence", models.PositiveIntegerField(default=0)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bill_sequences",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Bill Sequence",
                "verbose_name_plural": "Bill Sequences",
            },
        ),
        migrations.AddConstraint(
            model_name="billsequence",
            constraint=models.UniqueConstraint(
                fields=["branch", "year_key"],
                name="unique_bill_sequence_per_branch_year",
            ),
        ),
        migrations.AddIndex(
            model_name="billsequence",
            index=models.Index(fields=["branch", "year_key"], name="billing_bil_branch__year_idx"),
        ),

        # =====================================================================
        # Bill
        # =====================================================================
        migrations.CreateModel(
            name="Bill",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "bill_number",
                    models.CharField(
                        db_index=True,
                        help_text="Human-readable bill number. Format: B-{YYYY}-{seq:06d}. Immutable.",
                        max_length=30,
                        unique=True,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("DRAFT", "Draft"),
                            ("FINALIZED", "Finalized"),
                            ("CANCELLED", "Cancelled"),
                            ("VOID", "Void"),
                        ],
                        db_index=True,
                        default="DRAFT",
                        max_length=20,
                    ),
                ),
                (
                    "discount_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("PERCENTAGE", "Percentage"),
                            ("FIXED_AMOUNT", "Fixed Amount"),
                        ],
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "discount_value",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=10,
                    ),
                ),
                (
                    "subtotal",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "discount_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "taxable_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "tax_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "tax_breakdown",
                    models.JSONField(blank=True, default=dict),
                ),
                (
                    "rounding_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=6,
                    ),
                ),
                (
                    "grand_total",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("finalized_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancellation_reason", models.TextField(blank=True)),
                (
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bills",
                        to="organizations.branch",
                    ),
                ),
                (
                    "cancelled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cancelled_bills",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_bills",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "finalized_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="finalized_bills",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "order",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bill",
                        to="orders.order",
                    ),
                ),
            ],
            options={
                "verbose_name": "Bill",
                "verbose_name_plural": "Bills",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(fields=["branch", "status"], name="billing_bil_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(fields=["branch", "created_at"], name="billing_bil_branch_created_idx"),
        ),
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(fields=["branch", "status", "created_at"], name="billing_bil_branch_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(fields=["status", "created_at"], name="billing_bil_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(fields=["bill_number"], name="billing_bil_bill_number_idx"),
        ),
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(fields=["order"], name="billing_bil_order_idx"),
        ),
        migrations.AddIndex(
            model_name="bill",
            index=models.Index(fields=["created_by", "status"], name="billing_bil_created_by_status_idx"),
        ),

        # =====================================================================
        # BillItem
        # =====================================================================
        migrations.CreateModel(
            name="BillItem",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "item_name_snapshot",
                    models.CharField(max_length=200),
                ),
                (
                    "sku_snapshot",
                    models.CharField(blank=True, max_length=100),
                ),
                (
                    "quantity",
                    models.DecimalField(decimal_places=3, max_digits=7),
                ),
                (
                    "unit_price",
                    models.DecimalField(decimal_places=2, max_digits=12),
                ),
                (
                    "gross_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "discount_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "taxable_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "tax_rate",
                    models.DecimalField(
                        decimal_places=3,
                        default="0.000",
                        max_digits=6,
                    ),
                ),
                (
                    "tax_code",
                    models.CharField(blank=True, max_length=50),
                ),
                (
                    "tax_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "total_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default="0.00",
                        max_digits=12,
                    ),
                ),
                (
                    "bill",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="items",
                        to="billing.bill",
                    ),
                ),
                (
                    "menu_item",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bill_items",
                        to="menu.menuitem",
                    ),
                ),
                (
                    "order_item",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="bill_item",
                        to="orders.orderitem",
                    ),
                ),
            ],
            options={
                "verbose_name": "Bill Item",
                "verbose_name_plural": "Bill Items",
                "ordering": ["created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="billitem",
            index=models.Index(fields=["bill"], name="billing_billitem_bill_idx"),
        ),
        migrations.AddIndex(
            model_name="billitem",
            index=models.Index(fields=["order_item"], name="billing_billitem_order_item_idx"),
        ),
        migrations.AddIndex(
            model_name="billitem",
            index=models.Index(fields=["menu_item"], name="billing_billitem_menu_item_idx"),
        ),

        # =====================================================================
        # BillCorrectionRequest
        # =====================================================================
        migrations.CreateModel(
            name="BillCorrectionRequest",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "correction_type",
                    models.CharField(
                        choices=[
                            ("ITEM_CORRECTION", "Item Correction"),
                            ("DISCOUNT_CORRECTION", "Discount Correction"),
                            ("TAX_CORRECTION", "Tax Correction"),
                            ("CANCELLATION", "Cancellation"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                ("reason", models.TextField()),
                ("requested_data", models.JSONField(blank=True, default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.TextField(blank=True)),
                (
                    "bill",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="correction_requests",
                        to="billing.bill",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requested_bill_corrections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reviewed_bill_corrections",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Bill Correction Request",
                "verbose_name_plural": "Bill Correction Requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="billcorrectionrequest",
            index=models.Index(fields=["bill", "status"], name="billing_bcr_bill_status_idx"),
        ),
        migrations.AddIndex(
            model_name="billcorrectionrequest",
            index=models.Index(fields=["bill", "created_at"], name="billing_bcr_bill_created_idx"),
        ),
        migrations.AddIndex(
            model_name="billcorrectionrequest",
            index=models.Index(fields=["status", "created_at"], name="billing_bcr_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="billcorrectionrequest",
            index=models.Index(fields=["requested_by", "status"], name="billing_bcr_requested_by_idx"),
        ),
        migrations.AddIndex(
            model_name="billcorrectionrequest",
            index=models.Index(fields=["reviewed_by", "status"], name="billing_bcr_reviewed_by_idx"),
        ),
    ]
