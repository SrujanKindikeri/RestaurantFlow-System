# =============================================================================
# RestaurantFlow — Export Services
# Phase 14
#
# CSV export for reporting data.
# All exports apply identical authentication, permissions and scope as
# the underlying report views — never bypasses backend filters.
#
# Architecture is prepared for Excel/PDF via additional generators.
# =============================================================================

import csv
import io
import logging
from datetime import date
from decimal import Decimal

from reporting.constants import EXPORT_FORMAT_CSV
from reporting.exceptions import ExportPermissionError, ExportGenerationError

logger = logging.getLogger("reporting")


# ---------------------------------------------------------------------------
# Column definitions per report type
# ---------------------------------------------------------------------------

EXPORT_COLUMNS = {
    "sales_summary": [
        ("gross_sales", "Gross Sales"),
        ("discount_amount", "Discount Amount"),
        ("taxable_amount", "Taxable Amount"),
        ("tax_amount", "Tax Amount"),
        ("rounding_amount", "Rounding"),
        ("net_sales", "Net Sales"),
        ("number_of_bills", "Bill Count"),
        ("average_bill_value", "Avg Bill Value"),
    ],
    "sales_trend": [
        ("date", "Date"),
        ("gross_sales", "Gross Sales"),
        ("discounts", "Discounts"),
        ("tax", "Tax"),
        ("net_sales", "Net Sales"),
        ("bill_count", "Bills"),
        ("order_count", "Orders"),
        ("average_bill_value", "Avg Bill Value"),
    ],
    "menu_items": [
        ("menu_item_name", "Item Name"),
        ("category", "Category"),
        ("quantity_sold", "Qty Sold"),
        ("gross_revenue", "Gross Revenue"),
        ("discount_amount", "Discount"),
        ("net_revenue", "Net Revenue"),
        ("average_selling_price", "Avg Price"),
        ("number_of_orders", "Orders"),
        ("percentage_of_sales", "% of Sales"),
    ],
    "menu_top_selling": [
        ("rank", "Rank"),
        ("menu_item_name", "Item Name"),
        ("category", "Category"),
        ("quantity_sold", "Qty Sold"),
        ("net_revenue", "Revenue"),
        ("number_of_orders", "Orders"),
    ],
    "menu_categories": [
        ("category", "Category"),
        ("quantity_sold", "Qty Sold"),
        ("gross_revenue", "Gross Revenue"),
        ("net_revenue", "Net Revenue"),
        ("sales_percentage", "% of Sales"),
        ("average_item_value", "Avg Item Value"),
    ],
    "menu_profitability": [
        ("menu_item_name", "Item Name"),
        ("quantity_sold", "Qty Sold"),
        ("revenue", "Revenue"),
        ("ingredient_cost", "Ingredient Cost"),
        ("gross_profit", "Gross Profit"),
        ("gross_margin_percentage", "Gross Margin %"),
    ],
    "branch_performance": [
        ("branch_name", "Branch"),
        ("orders", "Orders"),
        ("bills", "Bills"),
        ("revenue", "Revenue"),
        ("payments", "Payments"),
        ("refunds", "Refunds"),
        ("discounts", "Discounts"),
        ("taxes", "Taxes"),
        ("average_bill_value", "Avg Bill Value"),
        ("ingredient_cost", "Ingredient Cost"),
        ("gross_profit", "Gross Profit"),
        ("gross_margin", "Gross Margin %"),
    ],
    "payment_methods": [
        ("payment_method", "Method"),
        ("total", "Total Amount"),
        ("count", "Count"),
        ("percentage", "% Share"),
    ],
    "kitchen_items": [
        ("menu_item_name", "Item Name"),
        ("quantity_prepared", "Qty Prepared"),
        ("average_preparation_time_seconds", "Avg Prep Time (s)"),
        ("max_preparation_time_seconds", "Max Prep Time (s)"),
        ("ready_count", "Ready"),
        ("cancelled_count", "Cancelled"),
    ],
    "inventory_consumption": [
        ("inventory_item", "Item"),
        ("unit", "Unit"),
        ("quantity_consumed", "Qty Consumed"),
        ("consumption_cost", "Consumption Cost"),
    ],
    "expenses": [
        ("total_expenses", "Total Expenses"),
        ("approved_expenses", "Approved"),
        ("pending_expenses", "Pending"),
        ("paid_expenses", "Paid"),
    ],
    "waiter_performance": [
        ("waiter_name", "Waiter"),
        ("order_count", "Orders"),
        ("sales", "Sales"),
        ("average_order_value", "Avg Order Value"),
        ("cancellation_count", "Cancellations"),
    ],
    "cashier_performance": [
        ("cashier_name", "Cashier"),
        ("payment_count", "Payments"),
        ("collected_amount", "Collected"),
        ("cash_collected", "Cash"),
        ("upi_collected", "UPI"),
        ("card_collected", "Card"),
        ("refund_count", "Refunds"),
    ],
}


def _to_str(value):
    """Convert Python values to clean CSV strings."""
    if value is None:
        return ""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def generate_csv(report_type: str, data) -> bytes:
    """
    Generate a UTF-8 CSV from the report data.
    `data` may be a dict (summary) or list (tabular).
    Returns bytes ready to send as an HTTP response.
    """
    columns = EXPORT_COLUMNS.get(report_type)
    if not columns:
        raise ExportGenerationError(f"No column definition for report type: {report_type}")

    output = io.StringIO()
    writer = csv.writer(output)

    # Header row
    writer.writerow([label for _, label in columns])

    # Data rows
    if isinstance(data, dict):
        # Summary report — single row
        writer.writerow([_to_str(data.get(key)) for key, _ in columns])
        row_count = 1
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                writer.writerow([_to_str(item.get(key)) for key, _ in columns])
            else:
                writer.writerow([_to_str(item)])
        row_count = len(data)
    else:
        row_count = 0

    return output.getvalue().encode("utf-8-sig"), row_count


def record_export_audit(actor, report_type, export_format, filters_dict,
                         status, row_count=None, failure_reason="",
                         restaurant=None, branch=None):
    """
    Append an immutable audit record for this export event.
    Silently logs if saving fails — never block the export itself.
    """
    try:
        from reporting.models import ReportExportAudit
        org = restaurant.organization if restaurant else None
        ReportExportAudit.objects.create(
            actor=actor,
            organization=org,
            restaurant=restaurant,
            branch=branch,
            report_type=report_type,
            export_format=export_format,
            filters_applied=filters_dict,
            status=status,
            row_count=row_count,
            failure_reason=failure_reason,
        )
    except Exception as exc:
        logger.error("Failed to record export audit: %s", exc)
