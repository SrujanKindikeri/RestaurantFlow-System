# =============================================================================
# RestaurantFlow — Reporting Views
# Phase 14
#
# Thin views: parse filters → call service → serialize → return response.
# No business logic here. All aggregation is in services/aggregations.
#
# All endpoints:
#   GET /api/reporting/dashboard/
#   GET /api/reporting/sales/summary/
#   GET /api/reporting/sales/trend/
#   GET /api/reporting/sales/hourly/
#   GET /api/reporting/orders/summary/
#   GET /api/reporting/orders/by-type/
#   GET /api/reporting/menu/items/
#   GET /api/reporting/menu/top-selling/
#   GET /api/reporting/menu/categories/
#   GET /api/reporting/menu/profitability/
#   GET /api/reporting/branches/performance/
#   GET /api/reporting/counters/performance/
#   GET /api/reporting/payments/summary/
#   GET /api/reporting/payments/methods/
#   GET /api/reporting/refunds/
#   GET /api/reporting/discounts/
#   GET /api/reporting/kitchen/performance/
#   GET /api/reporting/kitchen/items/
#   GET /api/reporting/staff/waiters/
#   GET /api/reporting/staff/cashiers/
#   GET /api/reporting/inventory/summary/
#   GET /api/reporting/inventory/consumption/
#   GET /api/reporting/inventory/wastage/
#   GET /api/reporting/purchases/
#   GET /api/reporting/suppliers/
#   GET /api/reporting/expenses/
#   GET /api/reporting/payables/
#   GET /api/reporting/financial-summary/
#   GET /api/reporting/export/<report_type>/
# =============================================================================

import logging
from datetime import date

from django.http import HttpResponse
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reporting import services
from reporting.dashboard_services import get_dashboard_kpis
from reporting.export_services import (
    generate_csv, record_export_audit,
    EXPORT_COLUMNS,
)
from reporting.filters import ReportFilterParams
from reporting.models import ReportExportAudit
from reporting.permissions import (
    CanViewDashboard, CanViewSalesReport, CanViewOrdersReport,
    CanViewMenuReport, CanViewBranchReport, CanViewCounterReport,
    CanViewPaymentReport, CanViewRefundReport, CanViewDiscountReport,
    CanViewKitchenReport, CanViewStaffReport, CanViewInventoryReport,
    CanViewPurchaseReport, CanViewSupplierReport, CanViewExpenseReport,
    CanViewPayableReport, CanViewProfitabilityReport, CanViewFinancialReport,
    CanExportCSV,
)

logger = logging.getLogger("reporting")


def _report_response(data, filters: ReportFilterParams, many=False):
    """
    Wrap report data in a consistent envelope.
    """
    return Response({
        "period": {
            "date_from": filters.date_from.isoformat() if filters.date_from else None,
            "date_to": filters.date_to.isoformat() if filters.date_to else None,
        },
        "filters": {k: v for k, v in filters.to_dict().items()
                    if k not in ("date_from", "date_to")},
        "data": data,
    })


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    permission_classes = [IsAuthenticated, CanViewDashboard]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = get_dashboard_kpis(
            request.user,
            restaurant_id=filters.restaurant_id,
            branch_id=filters.branch_id,
        )
        return Response(data)


# ---------------------------------------------------------------------------
# Sales
# ---------------------------------------------------------------------------

class SalesSummaryView(APIView):
    permission_classes = [IsAuthenticated, CanViewSalesReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_sales_summary(request.user, filters)
        return _report_response(data, filters)


class SalesTrendView(APIView):
    permission_classes = [IsAuthenticated, CanViewSalesReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_sales_trend(request.user, filters)
        return _report_response(data, filters, many=True)


class HourlySalesView(APIView):
    permission_classes = [IsAuthenticated, CanViewSalesReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_hourly_sales(request.user, filters)
        return _report_response(data, filters, many=True)


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrdersSummaryView(APIView):
    permission_classes = [IsAuthenticated, CanViewOrdersReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_orders_summary(request.user, filters)
        return _report_response(data, filters)


class OrdersByTypeView(APIView):
    permission_classes = [IsAuthenticated, CanViewOrdersReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_orders_by_type(request.user, filters)
        return _report_response(data, filters, many=True)


# ---------------------------------------------------------------------------
# Menu
# ---------------------------------------------------------------------------

class MenuItemsView(APIView):
    permission_classes = [IsAuthenticated, CanViewMenuReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_menu_items(request.user, filters)
        return _report_response(data, filters, many=True)


class TopSellingItemsView(APIView):
    permission_classes = [IsAuthenticated, CanViewMenuReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_top_selling_items(request.user, filters)
        return _report_response(data, filters, many=True)


class CategoryPerformanceView(APIView):
    permission_classes = [IsAuthenticated, CanViewMenuReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_category_performance(request.user, filters)
        return _report_response(data, filters, many=True)


class MenuProfitabilityView(APIView):
    permission_classes = [IsAuthenticated, CanViewProfitabilityReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_menu_profitability(request.user, filters)
        return _report_response(data, filters, many=True)


# ---------------------------------------------------------------------------
# Branch / Counter
# ---------------------------------------------------------------------------

class BranchPerformanceView(APIView):
    permission_classes = [IsAuthenticated, CanViewBranchReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_branch_performance(request.user, filters)
        return _report_response(data, filters, many=True)


class CounterPerformanceView(APIView):
    permission_classes = [IsAuthenticated, CanViewCounterReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_counter_performance(request.user, filters)
        return _report_response(data, filters, many=True)


# ---------------------------------------------------------------------------
# Payments / Refunds / Discounts
# ---------------------------------------------------------------------------

class PaymentSummaryView(APIView):
    permission_classes = [IsAuthenticated, CanViewPaymentReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_payment_summary(request.user, filters)
        return _report_response(data, filters)


class PaymentMethodsView(APIView):
    permission_classes = [IsAuthenticated, CanViewPaymentReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_payment_methods(request.user, filters)
        return _report_response(data, filters, many=True)


class RefundsView(APIView):
    permission_classes = [IsAuthenticated, CanViewRefundReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_refunds(request.user, filters)
        return _report_response(data, filters)


class DiscountsView(APIView):
    permission_classes = [IsAuthenticated, CanViewDiscountReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_discounts(request.user, filters)
        return _report_response(data, filters)


# ---------------------------------------------------------------------------
# Kitchen
# ---------------------------------------------------------------------------

class KitchenPerformanceView(APIView):
    permission_classes = [IsAuthenticated, CanViewKitchenReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_kitchen_performance(request.user, filters)
        return _report_response(data, filters)


class KitchenItemsView(APIView):
    permission_classes = [IsAuthenticated, CanViewKitchenReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_kitchen_items(request.user, filters)
        return _report_response(data, filters, many=True)


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

class WaiterPerformanceView(APIView):
    permission_classes = [IsAuthenticated, CanViewStaffReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_waiter_performance(request.user, filters)
        return _report_response(data, filters, many=True)


class CashierPerformanceView(APIView):
    permission_classes = [IsAuthenticated, CanViewStaffReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_cashier_performance(request.user, filters)
        return _report_response(data, filters, many=True)


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

class InventorySummaryView(APIView):
    permission_classes = [IsAuthenticated, CanViewInventoryReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_inventory_summary(request.user, filters)
        return _report_response(data, filters)


class InventoryConsumptionView(APIView):
    permission_classes = [IsAuthenticated, CanViewInventoryReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_inventory_consumption(request.user, filters)
        return _report_response(data, filters, many=True)


class WastageView(APIView):
    permission_classes = [IsAuthenticated, CanViewInventoryReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_wastage(request.user, filters)
        return _report_response(data, filters)


# ---------------------------------------------------------------------------
# Purchases / Suppliers
# ---------------------------------------------------------------------------

class PurchasesView(APIView):
    permission_classes = [IsAuthenticated, CanViewPurchaseReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_purchases(request.user, filters)
        return _report_response(data, filters)


class SuppliersView(APIView):
    permission_classes = [IsAuthenticated, CanViewSupplierReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_suppliers(request.user, filters)
        return _report_response(data, filters, many=True)


# ---------------------------------------------------------------------------
# Expenses / Payables
# ---------------------------------------------------------------------------

class ExpensesView(APIView):
    permission_classes = [IsAuthenticated, CanViewExpenseReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_expenses(request.user, filters)
        return _report_response(data, filters)


class PayablesView(APIView):
    permission_classes = [IsAuthenticated, CanViewPayableReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_payables(request.user, filters)
        return _report_response(data, filters)


# ---------------------------------------------------------------------------
# Financial Summary (delegates to Phase 13)
# ---------------------------------------------------------------------------

class FinancialSummaryView(APIView):
    permission_classes = [IsAuthenticated, CanViewFinancialReport]

    def get(self, request):
        filters = ReportFilterParams.from_request(request)
        data = services.get_financial_summary(request.user, filters)
        return _report_response(data, filters)


# ---------------------------------------------------------------------------
# CSV Export
# ---------------------------------------------------------------------------

class ExportCSVView(APIView):
    permission_classes = [IsAuthenticated, CanExportCSV]

    # Map URL report_type to service function and report name
    REPORT_MAP = {
        "sales_summary":       (services.get_sales_summary, "sales_summary"),
        "sales_trend":         (services.get_sales_trend, "sales_trend"),
        "menu_items":          (services.get_menu_items, "menu_items"),
        "menu_top_selling":    (services.get_top_selling_items, "menu_top_selling"),
        "menu_categories":     (services.get_category_performance, "menu_categories"),
        "menu_profitability":  (services.get_menu_profitability, "menu_profitability"),
        "branch_performance":  (services.get_branch_performance, "branch_performance"),
        "payment_methods":     (services.get_payment_methods, "payment_methods"),
        "kitchen_items":       (services.get_kitchen_items, "kitchen_items"),
        "inventory_consumption": (services.get_inventory_consumption, "inventory_consumption"),
        "waiter_performance":  (services.get_waiter_performance, "waiter_performance"),
        "cashier_performance": (services.get_cashier_performance, "cashier_performance"),
    }

    def get(self, request, report_type):
        if report_type not in self.REPORT_MAP:
            return Response(
                {"error": True, "message": f"Unknown report type: {report_type}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        filters = ReportFilterParams.from_request(request)
        service_fn, export_type = self.REPORT_MAP[report_type]

        try:
            data = service_fn(request.user, filters)
        except Exception as exc:
            logger.error("Export service error for %s: %s", report_type, exc, exc_info=True)
            record_export_audit(
                actor=request.user,
                report_type=report_type,
                export_format="CSV",
                filters_dict=filters.to_dict(),
                status=ReportExportAudit.EXPORT_FAILED,
                failure_reason=str(exc),
            )
            return Response(
                {"error": True, "message": "Failed to generate export."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            # Normalise: if data is a dict wrapping lists, flatten
            rows = data if isinstance(data, list) else [data]
            csv_bytes, row_count = generate_csv(export_type, rows if len(rows) > 1 else data)
        except Exception as exc:
            logger.error("CSV generation error for %s: %s", report_type, exc, exc_info=True)
            record_export_audit(
                actor=request.user,
                report_type=report_type,
                export_format="CSV",
                filters_dict=filters.to_dict(),
                status=ReportExportAudit.EXPORT_FAILED,
                failure_reason=str(exc),
            )
            return Response(
                {"error": True, "message": "CSV generation failed."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        record_export_audit(
            actor=request.user,
            report_type=report_type,
            export_format="CSV",
            filters_dict=filters.to_dict(),
            status=ReportExportAudit.EXPORT_SUCCESS,
            row_count=row_count,
        )

        filename = f"{report_type}_{filters.date_from}_{filters.date_to}.csv"
        response = HttpResponse(csv_bytes, content_type="text/csv; charset=utf-8-sig")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
