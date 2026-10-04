# =============================================================================
# RestaurantFlow — Financials Views
# Phase 12
#
# URL layout (see financials/urls.py):
#
#   EXPENSE CATEGORIES:
#   GET    /api/financials/expense-categories/          list
#   POST   /api/financials/expense-categories/          create
#   GET    /api/financials/expense-categories/{id}/     detail
#   PATCH  /api/financials/expense-categories/{id}/     update
#
#   EXPENSES:
#   GET    /api/financials/expenses/                    list (filterable)
#   POST   /api/financials/expenses/                    create
#   GET    /api/financials/expenses/{id}/               detail
#   PATCH  /api/financials/expenses/{id}/               update (DRAFT only)
#   POST   /api/financials/expenses/{id}/submit/        submit
#   POST   /api/financials/expenses/{id}/approve/       approve
#   POST   /api/financials/expenses/{id}/reject/        reject
#   POST   /api/financials/expenses/{id}/cancel/        cancel
#   GET    /api/financials/expenses/{id}/attachments/   list attachments
#   POST   /api/financials/expenses/{id}/attachments/   upload attachment
#   DELETE /api/financials/expenses/{id}/attachments/{att_id}/  delete
#
#   CORRECTIONS:
#   GET    /api/financials/expense-corrections/         list
#   POST   /api/financials/expenses/{id}/corrections/   request correction
#   GET    /api/financials/expense-corrections/{id}/    detail
#   POST   /api/financials/expense-corrections/{id}/approve/
#   POST   /api/financials/expense-corrections/{id}/reject/
#   POST   /api/financials/expense-corrections/{id}/cancel/
#
#   RECURRING EXPENSES:
#   GET    /api/financials/recurring-expenses/          list
#   POST   /api/financials/recurring-expenses/          create
#   GET    /api/financials/recurring-expenses/{id}/     detail
#   PATCH  /api/financials/recurring-expenses/{id}/     update
#   POST   /api/financials/recurring-expenses/{id}/disable/
#
#   SUPPLIER INVOICES:
#   GET    /api/financials/supplier-invoices/           list
#   POST   /api/financials/supplier-invoices/           create
#   GET    /api/financials/supplier-invoices/{id}/      detail
#   POST   /api/financials/supplier-invoices/{id}/submit/
#   POST   /api/financials/supplier-invoices/{id}/approve/
#   POST   /api/financials/supplier-invoices/{id}/cancel/
#
#   PAYABLES:
#   GET    /api/financials/payables/                    list
#   GET    /api/financials/payables/{id}/               detail
#   POST   /api/financials/payables/{id}/record-payment/ record payment
#
#   DASHBOARD:
#   GET    /api/financials/dashboard/                   financial dashboard
#
# Security:
#   - All querysets scoped via financials.access — IDOR prevention.
#   - get_object() returns 404 (not 403) for unauthorized UUIDs.
#   - Every action checks permission codes, never role names.
#   - Frontend totals are ignored — backend recalculates everything.
# =============================================================================

import logging
from decimal import Decimal

from django.db.models import Q, Sum, Count
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from financials import access as fin_acl
from financials import services
from financials.models import (
    ExpenseCategory, Expense, ExpenseApproval,
    ExpenseCorrectionRequest, ExpenseAttachment,
    RecurringExpense, SupplierInvoice, Payable,
)
from financials.permissions import (
    HasPermission,
    HasExpenseAccess, HasSupplierInvoiceAccess,
    HasPayableAccess, HasCorrectionAccess,
    PERM_EXPENSE_VIEW, PERM_EXPENSE_CREATE, PERM_EXPENSE_UPDATE,
    PERM_EXPENSE_SUBMIT, PERM_EXPENSE_APPROVE, PERM_EXPENSE_REJECT,
    PERM_EXPENSE_CANCEL,
    PERM_CATEGORY_VIEW, PERM_CATEGORY_CREATE, PERM_CATEGORY_UPDATE,
    PERM_ATTACHMENT_VIEW, PERM_ATTACHMENT_CREATE, PERM_ATTACHMENT_DELETE,
    PERM_CORRECTION_REQUEST, PERM_CORRECTION_APPROVE, PERM_CORRECTION_REJECT,
    PERM_RECURRING_VIEW, PERM_RECURRING_CREATE, PERM_RECURRING_UPDATE,
    PERM_RECURRING_DISABLE,
    PERM_SINV_VIEW, PERM_SINV_CREATE, PERM_SINV_SUBMIT,
    PERM_SINV_APPROVE, PERM_SINV_CANCEL,
    PERM_PAYABLE_VIEW, PERM_PAYABLE_MANAGE,
    PERM_FINANCIAL_DASHBOARD,
)
from financials.serializers import (
    ExpenseCategorySerializer,
    CreateExpenseCategorySerializer,
    UpdateExpenseCategorySerializer,
    ExpenseListSerializer,
    ExpenseDetailSerializer,
    CreateExpenseSerializer,
    UpdateExpenseSerializer,
    ApproveExpenseSerializer,
    RejectExpenseSerializer,
    ExpenseAttachmentSerializer,
    UploadAttachmentSerializer,
    ExpenseCorrectionRequestSerializer,
    CreateCorrectionRequestSerializer,
    ReviewCorrectionSerializer,
    RejectCorrectionSerializer,
    RecurringExpenseSerializer,
    CreateRecurringExpenseSerializer,
    UpdateRecurringExpenseSerializer,
    SupplierInvoiceListSerializer,
    SupplierInvoiceDetailSerializer,
    CreateSupplierInvoiceSerializer,
    ApproveInvoiceSerializer,
    CancelInvoiceSerializer,
    PayableSerializer,
    RecordPaymentSerializer,
    FinancialDashboardSerializer,
    PayableDashboardSerializer,
)

logger = logging.getLogger("financials")

ZERO = Decimal("0.00")


# =============================================================================
# Helpers
# =============================================================================

def _error(code, message, http_status=400):
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _service_error(exc, fallback_code="REQUEST_FAILED"):
    """Convert service-layer ValidationError / PermissionDenied to Response."""
    from rest_framework.exceptions import ValidationError, PermissionDenied as DRFPerm
    err = getattr(exc, "detail", None)
    if isinstance(err, dict):
        code = err.get("code", fallback_code)
        message = err.get("message", str(exc))
        http_status = 400
    elif isinstance(err, list) and err:
        first = err[0]
        code = getattr(first, "code", fallback_code) if hasattr(first, "code") else fallback_code
        message = str(first)
        http_status = 400
    else:
        code = fallback_code
        message = str(exc)
        http_status = 403 if isinstance(exc, DRFPerm) else 400
    return Response({"error": True, "code": code, "message": message}, status=http_status)


def _get_or_404(queryset, **kwargs):
    """Get or raise 404. Prevents leaking existence of unauthorized objects."""
    try:
        return queryset.get(**kwargs)
    except queryset.model.DoesNotExist:
        raise NotFound(detail="Not found.")


def _resolve_restaurant(user, restaurant_id):
    """Resolve and validate restaurant access from a UUID string."""
    from organizations.models import Restaurant
    try:
        restaurant = Restaurant.objects.get(pk=restaurant_id)
    except Restaurant.DoesNotExist:
        raise NotFound("Restaurant not found.")
    if not acl.can_access_restaurant(user, restaurant):
        raise PermissionDenied("You do not have access to this restaurant.")
    return restaurant


def _resolve_branch(user, branch_id, restaurant=None):
    """Resolve and validate branch access from a UUID string."""
    from organizations.models import Branch
    try:
        branch = Branch.objects.get(pk=branch_id)
    except Branch.DoesNotExist:
        raise NotFound("Branch not found.")
    if restaurant and branch.restaurant_id != restaurant.pk:
        from rest_framework.exceptions import ValidationError
        raise ValidationError({"branch": "Branch does not belong to this restaurant."})
    if not acl.can_access_branch(user, branch):
        raise PermissionDenied("You do not have access to this branch.")
    return branch


def _resolve_category(user, category_id, restaurant):
    """Resolve an ExpenseCategory belonging to the given restaurant."""
    try:
        return ExpenseCategory.objects.get(pk=category_id, restaurant=restaurant)
    except ExpenseCategory.DoesNotExist:
        raise NotFound("Expense category not found.")


# =============================================================================
# Expense Categories
# =============================================================================

class ExpenseCategoryListView(APIView):
    """
    GET  /api/financials/expense-categories/  — list
    POST /api/financials/expense-categories/  — create
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission(PERM_CATEGORY_CREATE)()]
        return [IsAuthenticated(), HasPermission(PERM_CATEGORY_VIEW)()]

    def get(self, request):
        qs = fin_acl.get_accessible_expense_categories(request.user)

        # Filters
        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)

        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=is_active.lower() == "true")

        search = request.query_params.get("search")
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))

        serializer = ExpenseCategorySerializer(qs.order_by("name"), many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CreateExpenseCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        # data["restaurant"] is a Restaurant instance from ModelSerializer FK resolution
        restaurant_obj = data["restaurant"]
        restaurant = _resolve_restaurant(request.user, restaurant_obj.pk)

        try:
            category = ExpenseCategory.objects.create(
                restaurant=restaurant,
                name=data["name"],
                code=data["code"].upper(),
                description=data.get("description", ""),
                is_active=data.get("is_active", True),
            )
        except Exception as exc:
            return _service_error(exc, "CATEGORY_CREATE_FAILED")

        return Response(ExpenseCategorySerializer(category).data, status=201)


class ExpenseCategoryDetailView(APIView):
    """
    GET   /api/financials/expense-categories/{id}/  — detail
    PATCH /api/financials/expense-categories/{id}/  — update
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsAuthenticated(), HasPermission(PERM_CATEGORY_UPDATE)()]
        return [IsAuthenticated(), HasPermission(PERM_CATEGORY_VIEW)()]

    def _get_category(self, pk, user):
        return _get_or_404(fin_acl.get_accessible_expense_categories(user), pk=pk)

    def get(self, request, pk):
        category = self._get_category(pk, request.user)
        return Response(ExpenseCategorySerializer(category).data)

    def patch(self, request, pk):
        category = self._get_category(pk, request.user)
        serializer = UpdateExpenseCategorySerializer(category, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        serializer.save()
        return Response(ExpenseCategorySerializer(category).data)


# =============================================================================
# Expenses
# =============================================================================

class ExpenseListView(APIView):
    """
    GET  /api/financials/expenses/  — list with filters + pagination
    POST /api/financials/expenses/  — create
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission(PERM_EXPENSE_CREATE)()]
        return [IsAuthenticated(), HasPermission(PERM_EXPENSE_VIEW)()]

    def get(self, request):
        qs = fin_acl.get_accessible_expenses(request.user).select_related(
            "restaurant", "branch", "category", "created_by"
        )

        # Filters
        p = request.query_params
        if p.get("restaurant"):
            qs = qs.filter(restaurant_id=p["restaurant"])
        if p.get("branch"):
            qs = qs.filter(branch_id=p["branch"])
        if p.get("category"):
            qs = qs.filter(category_id=p["category"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("payment_status"):
            qs = qs.filter(payment_status=p["payment_status"])
        if p.get("date_from"):
            qs = qs.filter(expense_date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(expense_date__lte=p["date_to"])
        if p.get("created_by"):
            qs = qs.filter(created_by_id=p["created_by"])
        if p.get("vendor_name"):
            qs = qs.filter(vendor_name__icontains=p["vendor_name"])
        if p.get("search"):
            qs = qs.filter(
                Q(title__icontains=p["search"]) |
                Q(expense_number__icontains=p["search"]) |
                Q(vendor_name__icontains=p["search"])
            )

        # Pagination
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = int(p.get("page_size", 20))
        page = paginator.paginate_queryset(qs.order_by("-created_at"), request)
        serializer = ExpenseListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = CreateExpenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        restaurant = _resolve_restaurant(request.user, data["restaurant"])

        branch = None
        if data.get("branch"):
            branch = _resolve_branch(request.user, data["branch"], restaurant)

        category = _resolve_category(request.user, data["category"], restaurant)

        try:
            expense = services.ExpenseService.create_expense(
                restaurant=restaurant,
                category=category,
                title=data["title"],
                amount=data["amount"],
                expense_date=data["expense_date"],
                user=request.user,
                branch=branch,
                description=data.get("description", ""),
                tax_amount=data.get("tax_amount", ZERO),
                due_date=data.get("due_date"),
                vendor_name=data.get("vendor_name", ""),
                vendor_reference=data.get("vendor_reference", ""),
                notes=data.get("notes", ""),
            )
        except Exception as exc:
            return _service_error(exc, "EXPENSE_CREATE_FAILED")

        return Response(ExpenseDetailSerializer(expense).data, status=201)


class ExpenseDetailView(APIView):
    """
    GET   /api/financials/expenses/{id}/  — detail
    PATCH /api/financials/expenses/{id}/  — update DRAFT
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsAuthenticated(), HasPermission(PERM_EXPENSE_UPDATE)()]
        return [IsAuthenticated(), HasPermission(PERM_EXPENSE_VIEW)()]

    def _get_expense(self, pk, user):
        return _get_or_404(
            fin_acl.get_accessible_expenses(user).select_related(
                "restaurant", "branch", "category",
                "created_by", "submitted_by", "approved_by", "rejected_by",
            ).prefetch_related("attachments", "approvals"),
            pk=pk,
        )

    def get(self, request, pk):
        expense = self._get_expense(pk, request.user)
        return Response(ExpenseDetailSerializer(expense, context={"request": request}).data)

    def patch(self, request, pk):
        expense = self._get_expense(pk, request.user)
        serializer = UpdateExpenseSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        data = serializer.validated_data
        update_kwargs = dict(data)

        # Resolve category if provided
        if "category" in update_kwargs:
            cat_id = update_kwargs.pop("category")
            update_kwargs["category"] = _resolve_category(
                request.user, cat_id, expense.restaurant
            )

        # Resolve branch if provided
        if "branch" in update_kwargs:
            br_id = update_kwargs.pop("branch")
            if br_id:
                update_kwargs["branch"] = _resolve_branch(
                    request.user, br_id, expense.restaurant
                )
            else:
                update_kwargs["branch"] = None

        try:
            expense = services.ExpenseService.update_draft(expense, request.user, **update_kwargs)
        except Exception as exc:
            return _service_error(exc)

        return Response(ExpenseDetailSerializer(expense, context={"request": request}).data)


class ExpenseSubmitView(APIView):
    """POST /api/financials/expenses/{id}/submit/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_EXPENSE_SUBMIT)]

    def post(self, request, pk):
        expense = _get_or_404(fin_acl.get_accessible_expenses(request.user), pk=pk)
        try:
            expense = services.ExpenseService.submit_expense(expense, request.user)
        except Exception as exc:
            return _service_error(exc)
        return Response(ExpenseDetailSerializer(expense).data)


class ExpenseApproveView(APIView):
    """POST /api/financials/expenses/{id}/approve/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_EXPENSE_APPROVE)]

    def post(self, request, pk):
        expense = _get_or_404(fin_acl.get_accessible_expenses(request.user), pk=pk)
        serializer = ApproveExpenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            expense = services.ExpenseService.approve_expense(
                expense, request.user,
                note=serializer.validated_data.get("approval_note", ""),
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(ExpenseDetailSerializer(expense).data)


class ExpenseRejectView(APIView):
    """POST /api/financials/expenses/{id}/reject/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_EXPENSE_REJECT)]

    def post(self, request, pk):
        expense = _get_or_404(fin_acl.get_accessible_expenses(request.user), pk=pk)
        serializer = RejectExpenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            expense = services.ExpenseService.reject_expense(
                expense, request.user,
                reason=serializer.validated_data["rejection_reason"],
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(ExpenseDetailSerializer(expense).data)


class ExpenseCancelView(APIView):
    """POST /api/financials/expenses/{id}/cancel/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_EXPENSE_CANCEL)]

    def post(self, request, pk):
        expense = _get_or_404(fin_acl.get_accessible_expenses(request.user), pk=pk)
        try:
            expense = services.ExpenseService.cancel_expense(expense, request.user)
        except Exception as exc:
            return _service_error(exc)
        return Response(ExpenseDetailSerializer(expense).data)


# =============================================================================
# Expense Attachments
# =============================================================================

class ExpenseAttachmentView(APIView):
    """
    GET  /api/financials/expenses/{pk}/attachments/         — list
    POST /api/financials/expenses/{pk}/attachments/         — upload
    """
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission(PERM_ATTACHMENT_CREATE)()]
        return [IsAuthenticated(), HasPermission(PERM_ATTACHMENT_VIEW)()]

    def _get_expense(self, pk, user):
        return _get_or_404(fin_acl.get_accessible_expenses(user), pk=pk)

    def get(self, request, pk):
        expense = self._get_expense(pk, request.user)
        attachments = fin_acl.get_accessible_attachments(request.user).filter(expense=expense)
        serializer = ExpenseAttachmentSerializer(
            attachments, many=True, context={"request": request}
        )
        return Response(serializer.data)

    def post(self, request, pk):
        expense = self._get_expense(pk, request.user)
        if "file" not in request.FILES:
            return _error("NO_FILE", "No file was uploaded.")
        file = request.FILES["file"]
        try:
            attachment = services.ExpenseAttachmentService.upload_attachment(
                expense, file, request.user
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(
            ExpenseAttachmentSerializer(attachment, context={"request": request}).data,
            status=201,
        )


class ExpenseAttachmentDeleteView(APIView):
    """DELETE /api/financials/expenses/{pk}/attachments/{att_id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_ATTACHMENT_DELETE)]

    def delete(self, request, pk, att_id):
        expense = _get_or_404(fin_acl.get_accessible_expenses(request.user), pk=pk)
        attachment = _get_or_404(
            fin_acl.get_accessible_attachments(request.user).filter(expense=expense),
            pk=att_id,
        )
        try:
            services.ExpenseAttachmentService.delete_attachment(attachment, request.user)
        except Exception as exc:
            return _service_error(exc)
        return Response(status=204)


# =============================================================================
# Expense Corrections
# =============================================================================

class ExpenseCorrectionListView(APIView):
    """
    GET /api/financials/expense-corrections/  — list (filterable)
    """
    permission_classes = [IsAuthenticated, HasPermission(PERM_CORRECTION_REQUEST)]

    def get(self, request):
        qs = fin_acl.get_accessible_corrections(request.user).select_related(
            "expense", "requested_by", "reviewed_by"
        )
        p = request.query_params
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("expense"):
            qs = qs.filter(expense_id=p["expense"])
        if p.get("correction_type"):
            qs = qs.filter(correction_type=p["correction_type"])

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs.order_by("-created_at"), request)
        return paginator.get_paginated_response(
            ExpenseCorrectionRequestSerializer(page, many=True).data
        )


class ExpenseCorrectionRequestView(APIView):
    """POST /api/financials/expenses/{pk}/corrections/ — request a correction"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CORRECTION_REQUEST)]

    def post(self, request, pk):
        expense = _get_or_404(fin_acl.get_accessible_expenses(request.user), pk=pk)
        serializer = CreateCorrectionRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data
        try:
            correction = services.ExpenseCorrectionService.request_correction(
                expense=expense,
                user=request.user,
                correction_type=data["correction_type"],
                requested_data=data["requested_data"],
                reason=data["reason"],
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(ExpenseCorrectionRequestSerializer(correction).data, status=201)


class ExpenseCorrectionDetailView(APIView):
    """GET /api/financials/expense-corrections/{id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CORRECTION_REQUEST)]

    def get(self, request, pk):
        correction = _get_or_404(
            fin_acl.get_accessible_corrections(request.user).select_related(
                "expense", "requested_by", "reviewed_by"
            ),
            pk=pk,
        )
        return Response(ExpenseCorrectionRequestSerializer(correction).data)


class ExpenseCorrectionApproveView(APIView):
    """POST /api/financials/expense-corrections/{id}/approve/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CORRECTION_APPROVE)]

    def post(self, request, pk):
        correction = _get_or_404(fin_acl.get_accessible_corrections(request.user), pk=pk)
        serializer = ReviewCorrectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            correction = services.ExpenseCorrectionService.approve_correction(
                correction, request.user,
                note=serializer.validated_data.get("review_note", ""),
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(ExpenseCorrectionRequestSerializer(correction).data)


class ExpenseCorrectionRejectView(APIView):
    """POST /api/financials/expense-corrections/{id}/reject/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CORRECTION_REJECT)]

    def post(self, request, pk):
        correction = _get_or_404(fin_acl.get_accessible_corrections(request.user), pk=pk)
        serializer = RejectCorrectionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            correction = services.ExpenseCorrectionService.reject_correction(
                correction, request.user,
                note=serializer.validated_data["review_note"],
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(ExpenseCorrectionRequestSerializer(correction).data)


class ExpenseCorrectionCancelView(APIView):
    """POST /api/financials/expense-corrections/{id}/cancel/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CORRECTION_REQUEST)]

    def post(self, request, pk):
        correction = _get_or_404(fin_acl.get_accessible_corrections(request.user), pk=pk)
        try:
            correction = services.ExpenseCorrectionService.cancel_correction(
                correction, request.user
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(ExpenseCorrectionRequestSerializer(correction).data)


# =============================================================================
# Recurring Expenses
# =============================================================================

class RecurringExpenseListView(APIView):
    """
    GET  /api/financials/recurring-expenses/  — list
    POST /api/financials/recurring-expenses/  — create
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission(PERM_RECURRING_CREATE)()]
        return [IsAuthenticated(), HasPermission(PERM_RECURRING_VIEW)()]

    def get(self, request):
        qs = fin_acl.get_accessible_recurring_expenses(request.user).select_related(
            "restaurant", "branch", "category", "created_by"
        )
        p = request.query_params
        if p.get("restaurant"):
            qs = qs.filter(restaurant_id=p["restaurant"])
        if p.get("is_active"):
            qs = qs.filter(is_active=p["is_active"].lower() == "true")
        if p.get("frequency"):
            qs = qs.filter(frequency=p["frequency"])

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs.order_by("-created_at"), request)
        return paginator.get_paginated_response(
            RecurringExpenseSerializer(page, many=True).data
        )

    def post(self, request):
        serializer = CreateRecurringExpenseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data

        restaurant = _resolve_restaurant(request.user, data["restaurant"])
        branch = None
        if data.get("branch"):
            branch = _resolve_branch(request.user, data["branch"], restaurant)
        category = _resolve_category(request.user, data["category"], restaurant)

        try:
            template = services.RecurringExpenseService.create_template(
                restaurant=restaurant,
                category=category,
                title=data["title"],
                amount=data["amount"],
                frequency=data["frequency"],
                start_date=data["start_date"],
                user=request.user,
                branch=branch,
                description=data.get("description", ""),
                tax_amount=data.get("tax_amount", ZERO),
                end_date=data.get("end_date"),
            )
        except Exception as exc:
            return _service_error(exc)

        return Response(RecurringExpenseSerializer(template).data, status=201)


class RecurringExpenseDetailView(APIView):
    """
    GET   /api/financials/recurring-expenses/{id}/
    PATCH /api/financials/recurring-expenses/{id}/
    """

    def get_permissions(self):
        if self.request.method in ("PATCH", "PUT"):
            return [IsAuthenticated(), HasPermission(PERM_RECURRING_UPDATE)()]
        return [IsAuthenticated(), HasPermission(PERM_RECURRING_VIEW)()]

    def _get_template(self, pk, user):
        return _get_or_404(fin_acl.get_accessible_recurring_expenses(user), pk=pk)

    def get(self, request, pk):
        template = self._get_template(pk, request.user)
        return Response(RecurringExpenseSerializer(template).data)

    def patch(self, request, pk):
        template = self._get_template(pk, request.user)
        serializer = UpdateRecurringExpenseSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = dict(serializer.validated_data)

        if "category" in data:
            cat_id = data.pop("category")
            data["category"] = _resolve_category(request.user, cat_id, template.restaurant)

        try:
            template = services.RecurringExpenseService.update_template(
                template, request.user, **data
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(RecurringExpenseSerializer(template).data)


class RecurringExpenseDisableView(APIView):
    """POST /api/financials/recurring-expenses/{id}/disable/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_RECURRING_DISABLE)]

    def post(self, request, pk):
        template = _get_or_404(fin_acl.get_accessible_recurring_expenses(request.user), pk=pk)
        try:
            template = services.RecurringExpenseService.disable_template(
                template, request.user
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(RecurringExpenseSerializer(template).data)


# =============================================================================
# Supplier Invoices
# =============================================================================

class SupplierInvoiceListView(APIView):
    """
    GET  /api/financials/supplier-invoices/  — list
    POST /api/financials/supplier-invoices/  — create
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission(PERM_SINV_CREATE)()]
        return [IsAuthenticated(), HasPermission(PERM_SINV_VIEW)()]

    def get(self, request):
        qs = fin_acl.get_accessible_supplier_invoices(request.user).select_related(
            "restaurant", "branch", "supplier", "purchase_order", "created_by"
        )
        p = request.query_params
        if p.get("restaurant"):
            qs = qs.filter(restaurant_id=p["restaurant"])
        if p.get("supplier"):
            qs = qs.filter(supplier_id=p["supplier"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("branch"):
            qs = qs.filter(branch_id=p["branch"])
        if p.get("date_from"):
            qs = qs.filter(invoice_date__gte=p["date_from"])
        if p.get("date_to"):
            qs = qs.filter(invoice_date__lte=p["date_to"])
        if p.get("search"):
            qs = qs.filter(
                Q(invoice_number__icontains=p["search"]) |
                Q(external_invoice_number__icontains=p["search"]) |
                Q(supplier__name__icontains=p["search"])
            )

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs.order_by("-created_at"), request)
        return paginator.get_paginated_response(
            SupplierInvoiceListSerializer(page, many=True).data
        )

    def post(self, request):
        serializer = CreateSupplierInvoiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        data = serializer.validated_data

        restaurant = _resolve_restaurant(request.user, data["restaurant"])

        branch = None
        if data.get("branch"):
            branch = _resolve_branch(request.user, data["branch"], restaurant)

        # Resolve supplier
        from inventory.models import Supplier
        try:
            supplier = Supplier.objects.get(pk=data["supplier"], restaurant=restaurant)
        except Supplier.DoesNotExist:
            return _error("SUPPLIER_NOT_FOUND", "Supplier not found.", 404)

        # Resolve purchase order
        purchase_order = None
        if data.get("purchase_order"):
            from inventory.models import PurchaseOrder
            try:
                purchase_order = PurchaseOrder.objects.get(
                    pk=data["purchase_order"], restaurant=restaurant
                )
            except PurchaseOrder.DoesNotExist:
                return _error("PO_NOT_FOUND", "Purchase order not found.", 404)

        try:
            invoice = services.SupplierInvoiceService.create_invoice(
                restaurant=restaurant,
                supplier=supplier,
                invoice_date=data["invoice_date"],
                user=request.user,
                branch=branch,
                purchase_order=purchase_order,
                external_invoice_number=data.get("external_invoice_number", ""),
                subtotal=data.get("subtotal", ZERO),
                tax_amount=data.get("tax_amount", ZERO),
                discount_amount=data.get("discount_amount", ZERO),
                due_date=data.get("due_date"),
                notes=data.get("notes", ""),
            )
        except Exception as exc:
            return _service_error(exc)

        return Response(SupplierInvoiceDetailSerializer(invoice).data, status=201)


class SupplierInvoiceDetailView(APIView):
    """GET /api/financials/supplier-invoices/{id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_SINV_VIEW)]

    def get(self, request, pk):
        invoice = _get_or_404(
            fin_acl.get_accessible_supplier_invoices(request.user).select_related(
                "restaurant", "branch", "supplier", "purchase_order",
                "created_by", "approved_by",
            ),
            pk=pk,
        )
        return Response(SupplierInvoiceDetailSerializer(invoice).data)


class SupplierInvoiceSubmitView(APIView):
    """POST /api/financials/supplier-invoices/{id}/submit/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_SINV_SUBMIT)]

    def post(self, request, pk):
        invoice = _get_or_404(fin_acl.get_accessible_supplier_invoices(request.user), pk=pk)
        try:
            invoice = services.SupplierInvoiceService.submit_invoice(invoice, request.user)
        except Exception as exc:
            return _service_error(exc)
        return Response(SupplierInvoiceDetailSerializer(invoice).data)


class SupplierInvoiceApproveView(APIView):
    """POST /api/financials/supplier-invoices/{id}/approve/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_SINV_APPROVE)]

    def post(self, request, pk):
        invoice = _get_or_404(fin_acl.get_accessible_supplier_invoices(request.user), pk=pk)
        serializer = ApproveInvoiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            invoice = services.SupplierInvoiceService.approve_invoice(
                invoice, request.user,
                note=serializer.validated_data.get("note", ""),
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(SupplierInvoiceDetailSerializer(invoice).data)


class SupplierInvoiceCancelView(APIView):
    """POST /api/financials/supplier-invoices/{id}/cancel/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_SINV_CANCEL)]

    def post(self, request, pk):
        invoice = _get_or_404(fin_acl.get_accessible_supplier_invoices(request.user), pk=pk)
        serializer = CancelInvoiceSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            invoice = services.SupplierInvoiceService.cancel_invoice(
                invoice, request.user,
                reason=serializer.validated_data.get("reason", ""),
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(SupplierInvoiceDetailSerializer(invoice).data)


# =============================================================================
# Payables
# =============================================================================

class PayableListView(APIView):
    """GET /api/financials/payables/ — list with filters"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_PAYABLE_VIEW)]

    def get(self, request):
        qs = fin_acl.get_accessible_payables(request.user).select_related(
            "restaurant", "branch",
            "supplier_invoice__supplier",
            "expense",
        )
        p = request.query_params
        if p.get("restaurant"):
            qs = qs.filter(restaurant_id=p["restaurant"])
        if p.get("branch"):
            qs = qs.filter(branch_id=p["branch"])
        if p.get("payable_type"):
            qs = qs.filter(payable_type=p["payable_type"])
        if p.get("status"):
            qs = qs.filter(status=p["status"])
        if p.get("due_date_from"):
            qs = qs.filter(due_date__gte=p["due_date_from"])
        if p.get("due_date_to"):
            qs = qs.filter(due_date__lte=p["due_date_to"])
        if p.get("supplier"):
            qs = qs.filter(supplier_invoice__supplier_id=p["supplier"])
        if p.get("overdue") and p["overdue"].lower() == "true":
            today = timezone.now().date()
            qs = qs.filter(due_date__lt=today, remaining_amount__gt=ZERO).exclude(
                status__in=["PAID", "CANCELLED"]
            )

        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs.order_by("-created_at"), request)
        return paginator.get_paginated_response(PayableSerializer(page, many=True).data)


class PayableDetailView(APIView):
    """GET /api/financials/payables/{id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_PAYABLE_VIEW)]

    def get(self, request, pk):
        payable = _get_or_404(
            fin_acl.get_accessible_payables(request.user).select_related(
                "restaurant", "branch",
                "supplier_invoice__supplier",
                "expense",
            ),
            pk=pk,
        )
        return Response(PayableSerializer(payable).data)


class PayableRecordPaymentView(APIView):
    """POST /api/financials/payables/{id}/record-payment/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_PAYABLE_MANAGE)]

    def post(self, request, pk):
        payable = _get_or_404(fin_acl.get_accessible_payables(request.user), pk=pk)
        serializer = RecordPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        try:
            payable = services.PayableService.record_payment(
                payable,
                serializer.validated_data["payment_amount"],
                request.user,
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(PayableSerializer(payable).data)


# =============================================================================
# Financial Dashboard
# =============================================================================

class FinancialDashboardView(APIView):
    """GET /api/financials/dashboard/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_FINANCIAL_DASHBOARD)]

    def get(self, request):
        from financials.constants import (
            EXPENSE_SUBMITTED, EXPENSE_APPROVED, EXPENSE_REJECTED,
            PAYMENT_STATUS_UNPAID, PAYMENT_STATUS_PARTIALLY_PAID,
            PAYABLE_OVERDUE,
        )

        expenses_qs = fin_acl.get_accessible_expenses(request.user)
        payables_qs = fin_acl.get_accessible_payables(request.user)

        # Apply optional restaurant filter
        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            expenses_qs = expenses_qs.filter(restaurant_id=restaurant_id)
            payables_qs = payables_qs.filter(restaurant_id=restaurant_id)

        # Expense counts
        total_expenses   = expenses_qs.count()
        pending_approval = expenses_qs.filter(status=EXPENSE_SUBMITTED).count()
        approved         = expenses_qs.filter(status=EXPENSE_APPROVED).count()
        rejected         = expenses_qs.filter(status=EXPENSE_REJECTED).count()
        unpaid           = expenses_qs.filter(
            status=EXPENSE_APPROVED, payment_status=PAYMENT_STATUS_UNPAID
        ).count()
        partially_paid   = expenses_qs.filter(
            payment_status=PAYMENT_STATUS_PARTIALLY_PAID
        ).count()

        # Payable aggregates
        payable_agg = payables_qs.aggregate(
            total_amount=Sum("amount"),
            paid_amount=Sum("paid_amount"),
            remaining=Sum("remaining_amount"),
        )
        overdue_count = payables_qs.filter(status=PAYABLE_OVERDUE).count()

        # Category breakdown (top 10)
        cat_summary = list(
            expenses_qs.values(
                "category__name", "category__code"
            ).annotate(
                count=Count("id"),
                total=Sum("total_amount"),
            ).order_by("-total")[:10]
        )

        # Branch breakdown
        branch_summary = list(
            expenses_qs.filter(branch__isnull=False).values(
                "branch__name"
            ).annotate(
                count=Count("id"),
                total=Sum("total_amount"),
            ).order_by("-total")[:10]
        )

        recent_expenses = expenses_qs.select_related(
            "restaurant", "branch", "category", "created_by"
        ).order_by("-created_at")[:10]

        data = {
            "total_expenses":          total_expenses,
            "pending_approval":        pending_approval,
            "approved_expenses":       approved,
            "rejected_expenses":       rejected,
            "unpaid_expenses":         unpaid,
            "partially_paid":          partially_paid,
            "overdue_payables":        overdue_count,
            "total_payable_amount":    payable_agg["total_amount"] or ZERO,
            "total_paid_amount":       payable_agg["paid_amount"] or ZERO,
            "total_remaining_amount":  payable_agg["remaining"] or ZERO,
            "category_summary":        cat_summary,
            "branch_summary":          branch_summary,
            "recent_expenses":         recent_expenses,
        }

        serializer = FinancialDashboardSerializer(data)
        return Response(serializer.data)


class PayableDashboardView(APIView):
    """GET /api/financials/payables/dashboard/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_PAYABLE_VIEW)]

    def get(self, request):
        from financials.constants import (
            PAYABLE_OPEN, PAYABLE_PARTIALLY_PAID, PAYABLE_PAID,
            PAYABLE_OVERDUE, PAYABLE_CANCELLED,
            PAYABLE_TYPE_EXPENSE, PAYABLE_TYPE_SUPPLIER_INVOICE,
        )

        qs = fin_acl.get_accessible_payables(request.user)

        restaurant_id = request.query_params.get("restaurant")
        if restaurant_id:
            qs = qs.filter(restaurant_id=restaurant_id)

        agg = qs.aggregate(
            total_amount=Sum("amount"),
            paid_amount=Sum("paid_amount"),
            remaining=Sum("remaining_amount"),
        )

        data = {
            "total_payables":   qs.count(),
            "open_payables":    qs.filter(status=PAYABLE_OPEN).count(),
            "partially_paid":   qs.filter(status=PAYABLE_PARTIALLY_PAID).count(),
            "paid_payables":    qs.filter(status=PAYABLE_PAID).count(),
            "overdue_payables": qs.filter(status=PAYABLE_OVERDUE).count(),
            "total_amount":     agg["total_amount"] or ZERO,
            "paid_amount":      agg["paid_amount"] or ZERO,
            "remaining_amount": agg["remaining"] or ZERO,
            "by_type": [
                {
                    "type": PAYABLE_TYPE_EXPENSE,
                    "count": qs.filter(payable_type=PAYABLE_TYPE_EXPENSE).count(),
                    "total": qs.filter(payable_type=PAYABLE_TYPE_EXPENSE).aggregate(
                        t=Sum("amount")
                    )["t"] or ZERO,
                },
                {
                    "type": PAYABLE_TYPE_SUPPLIER_INVOICE,
                    "count": qs.filter(payable_type=PAYABLE_TYPE_SUPPLIER_INVOICE).count(),
                    "total": qs.filter(payable_type=PAYABLE_TYPE_SUPPLIER_INVOICE).aggregate(
                        t=Sum("amount")
                    )["t"] or ZERO,
                },
            ],
        }

        return Response(PayableDashboardSerializer(data).data)
