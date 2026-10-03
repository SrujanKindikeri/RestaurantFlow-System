# =============================================================================
# RestaurantFlow — Payments Initial Migration
# Phase 9
#
# Creates:
#   payments_paymentsequence
#   payments_payment
#   payments_paymentrefund
#   payments_paymentauditlog
# =============================================================================

import django.db.models.deletion
import django.utils.timezone
import uuid

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("billing", "0001_initial"),
        ("counters", "0001_initial"),
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ------------------------------------------------------------------
        # PaymentSequence
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="PaymentSequence",
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
                    "sequence_key",
                    models.CharField(
                        db_index=True,
                        default="GLOBAL",
                        max_length=20,
                        unique=True,
                    ),
                ),
                ("last_sequence", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Payment Sequence",
                "verbose_name_plural": "Payment Sequences",
            },
        ),
        # ------------------------------------------------------------------
        # Payment
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="Payment",
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
                    "payment_number",
                    models.CharField(
                        db_index=True,
                        help_text="Human-readable payment number. Format: PAY-{seq:06d}. Immutable.",
                        max_length=20,
                        unique=True,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Authoritative payment amount. Immutable after COMPLETED.",
                        max_digits=12,
                    ),
                ),
                (
                    "cash_received",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Cash tendered by the customer (CASH method only).",
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "change_amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Change returned to customer. Calculated by backend.",
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "payment_method",
                    models.CharField(
                        choices=[
                            ("CASH", "Cash"),
                            ("UPI", "UPI"),
                            ("CARD", "Card"),
                            ("WALLET", "Wallet"),
                            ("NET_BANKING", "Net Banking"),
                            ("BANK_TRANSFER", "Bank Transfer"),
                            ("CHEQUE", "Cheque"),
                            ("CREDIT", "Credit"),
                            ("OTHER", "Other"),
                        ],
                        db_index=True,
                        max_length=20,
                    ),
                ),
                (
                    "transaction_reference",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Safe external transaction reference. NEVER store card numbers or credentials.",
                        max_length=200,
                    ),
                ),
                (
                    "provider_reference",
                    models.CharField(
                        blank=True,
                        help_text="Provider-internal reference.",
                        max_length=200,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                            ("CANCELLED", "Cancelled"),
                            ("REFUNDED", "Refunded"),
                            ("PARTIALLY_REFUNDED", "Partially Refunded"),
                        ],
                        db_index=True,
                        default="PENDING",
                        max_length=30,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                (
                    "idempotency_key",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        help_text="Client-supplied idempotency key. Prevents duplicate payment on retry.",
                        max_length=128,
                    ),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("failed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("cancellation_reason", models.TextField(blank=True)),
                # FKs
                (
                    "bill",
                    models.ForeignKey(
                        db_index=True,
                        help_text="The finalized bill this payment is for.",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="billing.bill",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="organizations.branch",
                    ),
                ),
                (
                    "counter",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="counters.counter",
                    ),
                ),
                (
                    "counter_session",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payments",
                        to="counters.countersession",
                    ),
                ),
                (
                    "initiated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="initiated_payments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "completed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="completed_payments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Payment",
                "verbose_name_plural": "Payments",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["bill", "status"], name="payments_pa_bill_id_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["branch", "status"], name="payments_pa_branch_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["branch", "created_at"], name="payments_pa_branch_created_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["counter", "status"], name="payments_pa_counter_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["counter_session", "status"], name="payments_pa_csession_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["payment_method", "status"], name="payments_pa_method_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["status", "created_at"], name="payments_pa_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["initiated_by", "status"], name="payments_pa_initiated_status_idx"),
        ),
        migrations.AddIndex(
            model_name="payment",
            index=models.Index(fields=["transaction_reference"], name="payments_pa_txn_ref_idx"),
        ),
        # ------------------------------------------------------------------
        # PaymentRefund
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="PaymentRefund",
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
                    "refund_number",
                    models.CharField(
                        db_index=True,
                        max_length=20,
                        unique=True,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("REQUESTED", "Requested"),
                            ("APPROVED", "Approved"),
                            ("REJECTED", "Rejected"),
                            ("PROCESSED", "Processed"),
                            ("CANCELLED", "Cancelled"),
                        ],
                        db_index=True,
                        default="REQUESTED",
                        max_length=20,
                    ),
                ),
                ("reason", models.TextField()),
                ("rejection_reason", models.TextField(blank=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "transaction_reference",
                    models.CharField(blank=True, max_length=200),
                ),
                ("requested_at", models.DateTimeField(auto_now_add=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("rejected_at", models.DateTimeField(blank=True, null=True)),
                # FKs
                (
                    "payment",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="refunds",
                        to="payments.payment",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="requested_refunds",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_refunds",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "processed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="processed_refunds",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Payment Refund",
                "verbose_name_plural": "Payment Refunds",
                "ordering": ["-requested_at"],
            },
        ),
        migrations.AddIndex(
            model_name="paymentrefund",
            index=models.Index(fields=["payment", "status"], name="payments_ref_payment_status_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentrefund",
            index=models.Index(fields=["refund_number"], name="payments_ref_refund_number_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentrefund",
            index=models.Index(fields=["status", "requested_at"], name="payments_ref_status_created_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentrefund",
            index=models.Index(fields=["requested_by", "status"], name="payments_ref_requestedby_idx"),
        ),
        # ------------------------------------------------------------------
        # PaymentAuditLog
        # ------------------------------------------------------------------
        migrations.CreateModel(
            name="PaymentAuditLog",
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
                    "action",
                    models.CharField(
                        choices=[
                            ("PAYMENT_CREATED", "Payment Created"),
                            ("PAYMENT_COMPLETED", "Payment Completed"),
                            ("PAYMENT_FAILED", "Payment Failed"),
                            ("PAYMENT_CANCELLED", "Payment Cancelled"),
                            ("REFUND_REQUESTED", "Refund Requested"),
                            ("REFUND_APPROVED", "Refund Approved"),
                            ("REFUND_REJECTED", "Refund Rejected"),
                            ("REFUND_PROCESSED", "Refund Processed"),
                            ("REFUND_CANCELLED", "Refund Cancelled"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                ("old_status", models.CharField(blank=True, max_length=30)),
                ("new_status", models.CharField(blank=True, max_length=30)),
                (
                    "amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=12,
                        null=True,
                    ),
                ),
                ("reason", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                # FKs
                (
                    "payment",
                    models.ForeignKey(
                        db_index=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_logs",
                        to="payments.payment",
                    ),
                ),
                (
                    "refund",
                    models.ForeignKey(
                        blank=True,
                        db_index=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="audit_logs",
                        to="payments.paymentrefund",
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="payment_audit_logs",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Payment Audit Log",
                "verbose_name_plural": "Payment Audit Logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="paymentauditlog",
            index=models.Index(fields=["payment", "created_at"], name="payments_aud_payment_created_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentauditlog",
            index=models.Index(fields=["actor", "created_at"], name="payments_aud_actor_created_idx"),
        ),
        migrations.AddIndex(
            model_name="paymentauditlog",
            index=models.Index(fields=["action", "created_at"], name="payments_aud_action_created_idx"),
        ),
    ]
