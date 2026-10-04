# =============================================================================
# RestaurantFlow — Reporting Initial Migration
# Phase 14
# =============================================================================

import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReportExportAudit",
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
                    "report_type",
                    models.CharField(
                        db_index=True,
                        max_length=60,
                        help_text="Report type code, e.g. 'sales_summary', 'menu_items'.",
                    ),
                ),
                (
                    "export_format",
                    models.CharField(
                        choices=[("CSV", "CSV"), ("EXCEL", "Excel"), ("PDF", "PDF")],
                        default="CSV",
                        max_length=10,
                    ),
                ),
                (
                    "filters_applied",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Sanitised filters used for this export.",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("SUCCESS", "Success"),
                            ("FAILED", "Failed"),
                            ("DENIED", "Denied"),
                        ],
                        db_index=True,
                        default="SUCCESS",
                        max_length=10,
                    ),
                ),
                (
                    "row_count",
                    models.PositiveIntegerField(
                        blank=True,
                        null=True,
                        help_text="Number of rows exported (populated on SUCCESS).",
                    ),
                ),
                (
                    "failure_reason",
                    models.TextField(
                        blank=True,
                        help_text="Populated when status=FAILED.",
                    ),
                ),
                (
                    "actor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="report_export_audits",
                        to=settings.AUTH_USER_MODEL,
                        help_text="User who requested the export.",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organizations.organization",
                    ),
                ),
                (
                    "restaurant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organizations.restaurant",
                    ),
                ),
                (
                    "branch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to="organizations.branch",
                    ),
                ),
            ],
            options={
                "verbose_name": "Report Export Audit",
                "verbose_name_plural": "Report Export Audits",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="reportexportaudit",
            index=models.Index(
                fields=["actor", "created_at"],
                name="report_audit_actor_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reportexportaudit",
            index=models.Index(
                fields=["report_type", "created_at"],
                name="report_audit_type_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reportexportaudit",
            index=models.Index(
                fields=["restaurant", "created_at"],
                name="report_audit_restaurant_date_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reportexportaudit",
            index=models.Index(
                fields=["status", "created_at"],
                name="report_audit_status_date_idx",
            ),
        ),
    ]
