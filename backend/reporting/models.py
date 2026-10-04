# =============================================================================
# RestaurantFlow — Reporting Models
# Phase 14
#
# IMPORTANT: Reporting is READ-ONLY analytics over existing transactional data.
# This app intentionally has NO transaction models.
#
# The only model here is ReportExportAudit — an append-only audit log
# for CSV/Excel/PDF export events, as required by the security specification.
#
# Source of truth:
#   Sales     → billing.Bill, billing.BillItem
#   Payments  → payments.Payment, payments.PaymentRefund
#   Orders    → orders.Order, orders.OrderItem
#   Kitchen   → kitchen.KitchenOrder, kitchen.KitchenOrderItem
#   Inventory → inventory.StockBalance, inventory.StockMovement
#   Recipes   → recipes.StockConsumption, recipes.Recipe
#   Expenses  → financials.Expense, financials.SupplierInvoice, financials.Payable
#   Accounting→ accounting.JournalEntry, accounting.JournalEntryLine
#
# DO NOT create ReportOrder, ReportBill, AnalyticsInventory, etc.
# =============================================================================

import uuid
import logging

from django.conf import settings
from django.db import models

from core.models import TimestampedModel

logger = logging.getLogger("reporting")


class ReportExportAudit(TimestampedModel):
    """
    Immutable audit log for report export events.

    Created whenever a user generates a CSV/Excel/PDF export.
    Records actor, scope, report type, filters, format and outcome.

    Append-only: records are never updated or deleted after creation.
    Sensitive filter values are stored for compliance purposes only
    and must not expose other-restaurant data.
    """

    EXPORT_CSV   = "CSV"
    EXPORT_EXCEL = "EXCEL"
    EXPORT_PDF   = "PDF"

    EXPORT_FORMAT_CHOICES = [
        (EXPORT_CSV,   "CSV"),
        (EXPORT_EXCEL, "Excel"),
        (EXPORT_PDF,   "PDF"),
    ]

    EXPORT_SUCCESS = "SUCCESS"
    EXPORT_FAILED  = "FAILED"
    EXPORT_DENIED  = "DENIED"

    EXPORT_STATUS_CHOICES = [
        (EXPORT_SUCCESS, "Success"),
        (EXPORT_FAILED,  "Failed"),
        (EXPORT_DENIED,  "Denied"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="report_export_audits",
        help_text="User who requested the export.",
    )

    # Scope (which org/restaurant/branch the data was for)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Organization scope at time of export.",
    )
    restaurant = models.ForeignKey(
        "organizations.Restaurant",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Restaurant scope at time of export.",
    )
    branch = models.ForeignKey(
        "organizations.Branch",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
        help_text="Branch scope at time of export.",
    )

    # Report metadata
    report_type = models.CharField(
        max_length=60,
        db_index=True,
        help_text="Report type code, e.g. 'sales_summary', 'menu_items'.",
    )
    export_format = models.CharField(
        max_length=10,
        choices=EXPORT_FORMAT_CHOICES,
        default=EXPORT_CSV,
    )
    filters_applied = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Sanitised filters used for this export "
            "(date_from, date_to, branch_id, etc.). "
            "Never store passwords or sensitive PII."
        ),
    )

    # Outcome
    status = models.CharField(
        max_length=10,
        choices=EXPORT_STATUS_CHOICES,
        default=EXPORT_SUCCESS,
        db_index=True,
    )
    row_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of rows exported (populated on SUCCESS).",
    )
    failure_reason = models.TextField(
        blank=True,
        help_text="Populated when status=FAILED.",
    )

    class Meta:
        verbose_name = "Report Export Audit"
        verbose_name_plural = "Report Export Audits"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["actor", "created_at"]),
            models.Index(fields=["report_type", "created_at"]),
            models.Index(fields=["restaurant", "created_at"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return (
            f"Export {self.report_type} [{self.export_format}] "
            f"by {self.actor.email} [{self.status}]"
        )

    def save(self, *args, **kwargs):
        """Audit records are append-only — block updates."""
        if self.pk and ReportExportAudit.objects.filter(pk=self.pk).exists():
            raise ValueError("ReportExportAudit records are immutable.")
        super().save(*args, **kwargs)
