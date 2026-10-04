# =============================================================================
# RestaurantFlow — Accounting Views
# Phase 13
#
# Thin views: validate input → call service/selector → return response.
# No business logic here.
# =============================================================================

import logging
from decimal import Decimal

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from accounts import access as acl
from accounting import access as accounting_access
from accounting.models import (
    FiscalYear, AccountingPeriod, Account, AccountingSettings,
    JournalEntry, JournalEntryLine, AccountingAuditLog,
)
from accounting.serializers import (
    FiscalYearSerializer, FiscalYearCreateSerializer,
    AccountingPeriodSerializer, PeriodCloseSerializer,
    AccountSerializer, AccountCreateSerializer, AccountUpdateSerializer,
    AccountTreeSerializer,
    AccountingSettingsSerializer, AccountingSettingsUpdateSerializer,
    JournalEntrySerializer, JournalEntryCreateSerializer,
    JournalEntryLineSerializer,
    JournalReverseSerializer, JournalVoidSerializer,
    AccountingAuditLogSerializer,
    PayablePaymentSerializer,
)
from accounting.services import (
    AccountService, PeriodService, JournalService,
    AccountingSettingsService, AccountingPostingService,
)
from accounting.selectors import (
    get_general_ledger, get_account_statement,
    get_trial_balance, get_profit_and_loss,
    get_balance_sheet, get_cash_flow_basic,
    get_accounting_dashboard,
)
from accounting.permissions import (
    CanViewAccount, CanCreateAccount, CanUpdateAccount, CanDeactivateAccount,
    CanViewJournal, CanCreateJournal, CanPostJournal, CanReverseJournal,
    CanViewPeriod, CanCreatePeriod, CanClosePeriod,
    CanViewLedger, CanViewTrialBalance, CanViewProfitLoss,
    CanViewBalanceSheet, CanViewCashFlow,
    CanViewConfig, CanManageConfig,
)

logger = logging.getLogger("accounting")
ZERO = Decimal("0.00")


def _get_restaurant(user, restaurant_id):
    """Return a restaurant accessible to the user or 404."""
    from organizations.models import Restaurant
    accessible = acl.get_accessible_restaurants(user)
    return get_object_or_404(accessible, pk=restaurant_id)


# =============================================================================
# Accounting Dashboard
# =============================================================================

class AccountingDashboardView(APIView):
    permission_classes = [IsAuthenticated, CanViewLedger]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response(
                {"detail": "restaurant query parameter required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        restaurant = _get_restaurant(request.user, restaurant_id)
        period_id = request.query_params.get("period")
        data = get_accounting_dashboard(restaurant, period_id=period_id)
        return Response(data)


# =============================================================================
# Fiscal Year
# =============================================================================

class FiscalYearListView(APIView):
    permission_classes = [IsAuthenticated, CanViewPeriod]

    def get(self, request):
        qs = accounting_access.get_accessible_fiscal_years(request.user)
        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)
        qs = qs.select_related("restaurant", "closed_by").order_by("-start_date")
        return Response(FiscalYearSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, "accounting.period.create"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = FiscalYearCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        restaurant = _get_restaurant(request.user, d["restaurant"])
        fy = PeriodService.create_fiscal_year(
            restaurant, d["name"], d["start_date"], d["end_date"], request.user
        )
        return Response(FiscalYearSerializer(fy).data, status=status.HTTP_201_CREATED)


class FiscalYearDetailView(APIView):
    permission_classes = [IsAuthenticated, CanViewPeriod]

    def _get_fy(self, user, pk):
        return get_object_or_404(
            accounting_access.get_accessible_fiscal_years(user), pk=pk
        )

    def get(self, request, pk):
        fy = self._get_fy(request.user, pk)
        return Response(FiscalYearSerializer(fy).data)

    def post(self, request, pk):
        """POST /fiscal-years/{pk}/close/"""
        fy = self._get_fy(request.user, pk)
        if not acl.has_permission(request.user, "accounting.period.close"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        from accounting.constants import FY_OPEN
        from django.utils import timezone
        if fy.status != FY_OPEN:
            return Response({"detail": f"Fiscal year is {fy.status}."}, status=400)
        fy.status = "CLOSED"
        fy.closed_at = timezone.now()
        fy.closed_by = request.user
        fy.save(update_fields=["status", "closed_at", "closed_by", "updated_at"])
        return Response(FiscalYearSerializer(fy).data)


# =============================================================================
# Accounting Period
# =============================================================================

class AccountingPeriodListView(APIView):
    permission_classes = [IsAuthenticated, CanViewPeriod]

    def get(self, request):
        qs = accounting_access.get_accessible_periods(request.user)
        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.select_related("restaurant", "fiscal_year", "closed_by").order_by("-start_date")
        return Response(AccountingPeriodSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, "accounting.period.create"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = AccountingPeriodSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        restaurant = _get_restaurant(request.user, d["restaurant"].pk)
        fy = d.get("fiscal_year")
        period = PeriodService.create_period(
            restaurant, d["name"], d["start_date"], d["end_date"],
            request.user, fiscal_year=fy,
        )
        return Response(AccountingPeriodSerializer(period).data, status=status.HTTP_201_CREATED)


class AccountingPeriodDetailView(APIView):
    permission_classes = [IsAuthenticated, CanViewPeriod]

    def _get_period(self, user, pk):
        return get_object_or_404(
            accounting_access.get_accessible_periods(user), pk=pk
        )

    def get(self, request, pk):
        period = self._get_period(request.user, pk)
        return Response(AccountingPeriodSerializer(period).data)


class PeriodCloseView(APIView):
    permission_classes = [IsAuthenticated, CanClosePeriod]

    def post(self, request, pk):
        period = get_object_or_404(
            accounting_access.get_accessible_periods(request.user), pk=pk
        )
        ser = PeriodCloseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        period = PeriodService.close_period(period, request.user, ser.validated_data["note"])
        return Response(AccountingPeriodSerializer(period).data)


class PeriodReopenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not acl.has_permission(request.user, "accounting.period.reopen"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        period = get_object_or_404(
            accounting_access.get_accessible_periods(request.user), pk=pk
        )
        ser = PeriodCloseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        period = PeriodService.reopen_period(period, request.user, ser.validated_data["note"])
        return Response(AccountingPeriodSerializer(period).data)


# =============================================================================
# Chart of Accounts
# =============================================================================

class AccountListView(APIView):
    permission_classes = [IsAuthenticated, CanViewAccount]

    def get(self, request):
        qs = accounting_access.get_accessible_accounts(request.user)
        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)
        account_type = request.query_params.get("account_type")
        if account_type:
            qs = qs.filter(account_type=account_type)
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")
        is_postable = request.query_params.get("is_postable")
        if is_postable is not None:
            qs = qs.filter(is_postable=is_postable.lower() == "true")
        qs = qs.select_related("restaurant", "parent_account").order_by("code")
        return Response(AccountSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, "accounting.account.create"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = AccountCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        restaurant = _get_restaurant(request.user, d["restaurant"])

        parent = None
        if d.get("parent_account"):
            parent = get_object_or_404(
                accounting_access.get_accessible_accounts(request.user),
                pk=d["parent_account"],
            )

        account = AccountService.create_account(
            restaurant=restaurant,
            code=d["code"],
            name=d["name"],
            account_type=d["account_type"],
            normal_balance=d.get("normal_balance", ""),
            user=request.user,
            description=d.get("description", ""),
            account_subtype=d.get("account_subtype", ""),
            parent_account=parent,
            is_group=d.get("is_group", False),
            is_postable=d.get("is_postable", True),
        )
        return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)


class AccountDetailView(APIView):
    permission_classes = [IsAuthenticated, CanViewAccount]

    def _get_account(self, user, pk):
        return get_object_or_404(
            accounting_access.get_accessible_accounts(user), pk=pk
        )

    def get(self, request, pk):
        account = self._get_account(request.user, pk)
        return Response(AccountSerializer(account).data)

    def patch(self, request, pk):
        if not acl.has_permission(request.user, "accounting.account.update"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        account = self._get_account(request.user, pk)
        ser = AccountUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        account = AccountService.update_account(account, request.user, **ser.validated_data)
        return Response(AccountSerializer(account).data)


class AccountDeactivateView(APIView):
    permission_classes = [IsAuthenticated, CanDeactivateAccount]

    def post(self, request, pk):
        account = get_object_or_404(
            accounting_access.get_accessible_accounts(request.user), pk=pk
        )
        account = AccountService.deactivate_account(account, request.user)
        return Response(AccountSerializer(account).data)


class AccountTreeView(APIView):
    """Return full chart of accounts as a hierarchy tree."""
    permission_classes = [IsAuthenticated, CanViewAccount]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response(
                {"detail": "restaurant query parameter required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        restaurant = _get_restaurant(request.user, restaurant_id)
        # Top-level accounts only
        roots = Account.objects.filter(
            restaurant=restaurant,
            parent_account__isnull=True,
            is_active=True,
        ).order_by("code")
        return Response(AccountTreeSerializer(roots, many=True).data)


class AccountStatementView(APIView):
    permission_classes = [IsAuthenticated, CanViewLedger]

    def get(self, request, pk):
        account = get_object_or_404(
            accounting_access.get_accessible_accounts(request.user), pk=pk
        )
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        data = get_account_statement(account, date_from=date_from, date_to=date_to)
        return Response(data)


# =============================================================================
# Accounting Settings
# =============================================================================

class AccountingSettingsView(APIView):
    permission_classes = [IsAuthenticated, CanViewConfig]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response({"detail": "restaurant required."}, status=400)
        restaurant = _get_restaurant(request.user, restaurant_id)
        qs = accounting_access.get_accessible_settings(request.user).filter(
            restaurant=restaurant
        )
        obj = qs.first()
        if not obj:
            return Response({"detail": "Accounting settings not configured."}, status=404)
        return Response(AccountingSettingsSerializer(obj).data)

    def put(self, request):
        if not acl.has_permission(request.user, "accounting.configuration.manage"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response({"detail": "restaurant required."}, status=400)
        restaurant = _get_restaurant(request.user, restaurant_id)

        settings_obj = AccountingSettingsService.get_or_create_settings(restaurant, request.user)
        ser = AccountingSettingsUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Resolve account UUIDs to Account objects
        resolved = {}
        account_fields = [
            "default_sales_account", "default_discount_account",
            "default_cash_account", "default_bank_account",
            "default_accounts_receivable", "default_inventory_account",
            "default_card_clearing_account", "default_upi_clearing_account",
            "default_accounts_payable", "default_tax_payable",
            "default_cogs_account", "default_rounding_account",
            "retained_earnings_account",
        ]
        for field in account_fields:
            val = ser.validated_data.get(field)
            if val is not None:
                acct = get_object_or_404(
                    accounting_access.get_accessible_accounts(request.user), pk=val
                )
                resolved[field] = acct
            elif field in ser.validated_data:
                resolved[field] = None

        settings_obj = AccountingSettingsService.update_settings(
            settings_obj, request.user, **resolved
        )
        return Response(AccountingSettingsSerializer(settings_obj).data)


# =============================================================================
# Journal Entries
# =============================================================================

class JournalEntryListView(APIView):
    permission_classes = [IsAuthenticated, CanViewJournal]

    def get(self, request):
        qs = accounting_access.get_accessible_journal_entries(request.user)
        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)
        period_id = request.query_params.get("period")
        if period_id:
            qs = qs.filter(accounting_period_id=period_id)
        je_status = request.query_params.get("status")
        if je_status:
            qs = qs.filter(status=je_status)
        source_type = request.query_params.get("source_type")
        if source_type:
            qs = qs.filter(source_type=source_type)
        date_from = request.query_params.get("date_from")
        if date_from:
            qs = qs.filter(entry_date__gte=date_from)
        date_to = request.query_params.get("date_to")
        if date_to:
            qs = qs.filter(entry_date__lte=date_to)
        qs = qs.select_related(
            "restaurant", "branch", "accounting_period",
            "created_by", "posted_by",
        ).prefetch_related("lines__account").order_by("-entry_date", "-created_at")

        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            JournalEntrySerializer(page, many=True).data
        )

    def post(self, request):
        """Create and immediately post a manual journal entry."""
        if not acl.has_permission(request.user, "accounting.journal.create"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = JournalEntryCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        restaurant = _get_restaurant(request.user, d["restaurant"])
        period = get_object_or_404(
            accounting_access.get_accessible_periods(request.user),
            pk=d["accounting_period"],
        )
        branch = None
        if d.get("branch"):
            from organizations.models import Branch
            branch = get_object_or_404(Branch, pk=d["branch"])

        # Create draft
        entry = JournalService.create_draft(
            restaurant=restaurant,
            period=period,
            entry_date=d["entry_date"],
            description=d["description"],
            user=request.user,
            source_type=d.get("source_type", "MANUAL"),
            source_id=d.get("source_id"),
            branch=branch,
        )

        # Add lines
        for line_data in d["lines"]:
            account = get_object_or_404(
                accounting_access.get_accessible_accounts(request.user),
                pk=line_data["account"],
            )
            JournalService.add_line(
                journal_entry=entry,
                account=account,
                debit_amount=line_data.get("debit_amount", ZERO),
                credit_amount=line_data.get("credit_amount", ZERO),
                user=request.user,
                description=line_data.get("description", ""),
                reference_type=line_data.get("reference_type", ""),
                reference_id=line_data.get("reference_id"),
            )

        # Auto-post if permission exists
        if acl.has_permission(request.user, "accounting.journal.post"):
            entry = JournalService.post_entry(entry, request.user)

        entry.refresh_from_db()
        return Response(
            JournalEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED,
        )


class JournalEntryDetailView(APIView):
    permission_classes = [IsAuthenticated, CanViewJournal]

    def _get_entry(self, user, pk):
        return get_object_or_404(
            accounting_access.get_accessible_journal_entries(user)
            .select_related(
                "restaurant", "branch", "accounting_period",
                "created_by", "posted_by",
            ).prefetch_related("lines__account"),
            pk=pk,
        )

    def get(self, request, pk):
        entry = self._get_entry(request.user, pk)
        return Response(JournalEntrySerializer(entry).data)


class JournalPostView(APIView):
    permission_classes = [IsAuthenticated, CanPostJournal]

    def post(self, request, pk):
        entry = get_object_or_404(
            accounting_access.get_accessible_journal_entries(request.user), pk=pk
        )
        entry = JournalService.post_entry(entry, request.user)
        return Response(JournalEntrySerializer(entry).data)


class JournalReverseView(APIView):
    permission_classes = [IsAuthenticated, CanReverseJournal]

    def post(self, request, pk):
        entry = get_object_or_404(
            accounting_access.get_accessible_journal_entries(request.user), pk=pk
        )
        ser = JournalReverseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        reversal = JournalService.reverse_entry(
            entry, request.user,
            ser.validated_data["reason"],
            ser.validated_data.get("reversal_date"),
        )
        return Response(JournalEntrySerializer(reversal).data, status=status.HTTP_201_CREATED)


class JournalVoidView(APIView):
    permission_classes = [IsAuthenticated, CanCreateJournal]

    def post(self, request, pk):
        entry = get_object_or_404(
            accounting_access.get_accessible_journal_entries(request.user), pk=pk
        )
        ser = JournalVoidSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        entry = JournalService.void_entry(entry, request.user, ser.validated_data.get("reason", ""))
        return Response(JournalEntrySerializer(entry).data)


# =============================================================================
# Reporting Views
# =============================================================================

class GeneralLedgerView(APIView):
    permission_classes = [IsAuthenticated, CanViewLedger]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response({"detail": "restaurant required."}, status=400)
        restaurant = _get_restaurant(request.user, restaurant_id)
        filters = {
            "account_id": request.query_params.get("account"),
            "branch_id": request.query_params.get("branch"),
            "date_from": request.query_params.get("date_from"),
            "date_to": request.query_params.get("date_to"),
            "period_id": request.query_params.get("period"),
            "source_type": request.query_params.get("source_type"),
        }
        rows = get_general_ledger(restaurant, filters={k: v for k, v in filters.items() if v})
        return Response({"results": rows, "count": len(rows)})


class TrialBalanceView(APIView):
    permission_classes = [IsAuthenticated, CanViewTrialBalance]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response({"detail": "restaurant required."}, status=400)
        restaurant = _get_restaurant(request.user, restaurant_id)
        data = get_trial_balance(
            restaurant,
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            period_id=request.query_params.get("period"),
        )
        return Response(data)


class ProfitLossView(APIView):
    permission_classes = [IsAuthenticated, CanViewProfitLoss]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response({"detail": "restaurant required."}, status=400)
        restaurant = _get_restaurant(request.user, restaurant_id)
        data = get_profit_and_loss(
            restaurant,
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
            period_id=request.query_params.get("period"),
        )
        return Response(data)


class BalanceSheetView(APIView):
    permission_classes = [IsAuthenticated, CanViewBalanceSheet]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response({"detail": "restaurant required."}, status=400)
        restaurant = _get_restaurant(request.user, restaurant_id)
        data = get_balance_sheet(
            restaurant,
            as_of_date=request.query_params.get("as_of_date"),
        )
        return Response(data)


class CashFlowView(APIView):
    permission_classes = [IsAuthenticated, CanViewCashFlow]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant")
        if not restaurant_id:
            return Response({"detail": "restaurant required."}, status=400)
        restaurant = _get_restaurant(request.user, restaurant_id)
        data = get_cash_flow_basic(
            restaurant,
            date_from=request.query_params.get("date_from"),
            date_to=request.query_params.get("date_to"),
        )
        return Response(data)


# =============================================================================
# Payable Payment (Accounting entry for settling a payable)
# =============================================================================

class PayablePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not acl.has_permission(request.user, "accounting.journal.post"):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        ser = PayablePaymentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        from financials.models import Payable
        payable = get_object_or_404(Payable, pk=d["payable"])
        if not acl.can_access_restaurant(request.user, payable.restaurant):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        entry = AccountingPostingService.post_payable_payment(
            payable=payable,
            amount=d["amount"],
            payment_method=d.get("payment_method", "CASH"),
            user=request.user,
        )
        return Response(JournalEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


# =============================================================================
# Audit Log
# =============================================================================

class AccountingAuditLogListView(APIView):
    permission_classes = [IsAuthenticated, CanViewLedger]

    def get(self, request):
        qs = accounting_access.get_accessible_audit_logs(request.user)
        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)
        entity_type = request.query_params.get("entity_type")
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        qs = qs.select_related("actor", "restaurant").order_by("-created_at")

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            AccountingAuditLogSerializer(page, many=True).data
        )
