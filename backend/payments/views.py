# =============================================================================
# RestaurantFlow — Payment Views
# Phase 9
#
# URL layout (see payments/urls.py):
#
#   PAYMENTS:
#   POST   /api/payments/                              create payment
#   GET    /api/payments/                              list payments (filterable)
#   GET    /api/payments/{id}/                         retrieve payment detail
#   POST   /api/payments/{id}/cancel/                  cancel a pending payment
#   GET    /api/payments/bill/{bill_id}/               payments for a bill
#   GET    /api/payments/bill/{bill_id}/summary/       payment summary for a bill
#   GET    /api/payments/bill/{bill_id}/receipt/       receipt data (billing + payments)
#
#   REFUNDS:
#   POST   /api/payments/{id}/refunds/                 request a refund
#   GET    /api/payments/{id}/refunds/                 list refunds for a payment
#   GET    /api/payments/refunds/{refund_id}/          refund detail
#   POST   /api/payments/refunds/{refund_id}/approve/  approve refund
#   POST   /api/payments/refunds/{refund_id}/reject/   reject refund
#   POST   /api/payments/refunds/{refund_id}/process/  process refund
#   POST   /api/payments/refunds/{refund_id}/cancel/   cancel refund
#
#   AUDIT:
#   GET    /api/payments/{id}/audit/                   audit log for a payment
#
# Security:
#   - All querysets scoped via payments.access — IDOR prevention.
#   - get_object() returns 404 (not 403) for unauthorized UUIDs.
#   - Every action checks permission codes, not role names.
#   - Frontend amounts/totals are NEVER trusted.
#   - Bill ownership validated server-side (not from request data).
# =============================================================================

import logging

from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from billing import access as bill_acl
from billing.models import Bill
from billing import services as billing_services

from payments import access as payment_acl
from payments import services
from payments.models import Payment, PaymentRefund, PaymentAuditLog
from payments.permissions import HasPermission, HasPaymentAccess, HasRefundAccess
from payments.serializers import (
    CreatePaymentSerializer,
    CancelPaymentSerializer,
    PaymentReadSerializer,
    PaymentListSerializer,
    PaymentRefundReadSerializer,
    CreateRefundSerializer,
    RejectRefundSerializer,
    ProcessRefundSerializer,
    BillPaymentSummarySerializer,
    PaymentAuditLogSerializer,
)

logger = logging.getLogger("payments")


# =============================================================================
# Helpers
# =============================================================================

def _error(code: str, message: str, http_status: int = 400) -> Response:
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _service_error(exc, fallback_code: str = "REQUEST_FAILED") -> Response:
    """Convert service-layer ValidationError / PermissionDenied to a Response."""
    from rest_framework.exceptions import ValidationError, PermissionDenied as DRFPermDenied

    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        code = detail.get("code", fallback_code)
        message = detail.get("message", str(exc))
        http_status = 400
    elif isinstance(detail, list) and detail:
        first = detail[0]
        code = getattr(first, "code", fallback_code)
        message = str(first)
        http_status = 400
    else:
        code = fallback_code
        message = str(exc)
        http_status = 403 if isinstance(exc, DRFPermDenied) else 400

    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _get_accessible_bill(user, bill_id) -> Bill:
    """
    Resolve a bill by UUID and verify user access.
    Returns 404 for non-existent or inaccessible bills (IDOR safe).
    """
    accessible_bills = bill_acl.get_accessible_bills(user)
    try:
        return accessible_bills.select_related(
            "branch", "branch__restaurant", "branch__restaurant__organization",
            "order",
        ).get(pk=bill_id)
    except Bill.DoesNotExist:
        raise NotFound("Bill not found.")


def _get_accessible_payment(user, payment_id) -> Payment:
    """
    Resolve a payment by UUID and verify user access.
    Returns 404 for non-existent or inaccessible payments.
    """
    accessible = payment_acl.get_accessible_payments(user)
    try:
        return accessible.select_related(
            "bill", "branch", "counter", "counter_session",
            "initiated_by", "completed_by",
        ).get(pk=payment_id)
    except Payment.DoesNotExist:
        raise NotFound("Payment not found.")


def _get_accessible_refund(user, refund_id) -> PaymentRefund:
    """
    Resolve a refund by UUID and verify user access.
    Returns 404 for non-existent or inaccessible refunds.
    """
    accessible = payment_acl.get_accessible_refunds(user)
    try:
        return accessible.select_related(
            "payment", "payment__branch",
            "requested_by", "approved_by", "processed_by",
        ).get(pk=refund_id)
    except PaymentRefund.DoesNotExist:
        raise NotFound("Refund not found.")


# =============================================================================
# Payment Views
# =============================================================================

class CreatePaymentView(APIView):
    """
    POST /api/payments/

    Create a payment against a finalized bill.

    Request body:
        {
            "bill_id": "...",
            "amount": "500.00",
            "payment_method": "CASH",
            "cash_received": "1000.00",       ← required for CASH
            "transaction_reference": "...",    ← required for UPI/CARD
            "idempotency_key": "...",
            "counter_session": "..."           ← required for CASH
        }

    Response: PaymentReadSerializer
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.create")]

    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "VALIDATION_ERROR", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Resolve bill — IDOR safe (only accessible bills returned)
        bill = _get_accessible_bill(request.user, data["bill_id"])

        # Resolve counter_session if provided
        counter_session = None
        if data.get("counter_session"):
            from counters.models import CounterSession
            try:
                counter_session = CounterSession.objects.select_related(
                    "counter", "counter__branch"
                ).get(pk=data["counter_session"])
            except CounterSession.DoesNotExist:
                return _error("COUNTER_SESSION_NOT_FOUND", "Counter session not found.")

        try:
            payment = services.create_payment(
                bill,
                request.user,
                amount=data["amount"],
                payment_method=data["payment_method"],
                cash_received=data.get("cash_received"),
                transaction_reference=data.get("transaction_reference", ""),
                provider_reference=data.get("provider_reference", ""),
                notes=data.get("notes", ""),
                idempotency_key=data.get("idempotency_key", ""),
                counter_session=counter_session,
            )
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import ValidationError
            if isinstance(exc, (PermissionDenied, ValidationError)):
                return _service_error(exc)
            logger.exception("Unexpected error creating payment for bill=%s", bill.bill_number)
            return _error("INTERNAL_ERROR", "An unexpected error occurred.", 500)

        payment.refresh_from_db()
        payment_qs = Payment.objects.prefetch_related("refunds").select_related(
            "bill", "branch", "counter", "counter_session", "initiated_by", "completed_by"
        ).get(pk=payment.pk)
        return Response(
            PaymentReadSerializer(payment_qs).data,
            status=status.HTTP_201_CREATED,
        )


class PaymentListView(APIView):
    """
    GET /api/payments/

    List payments accessible to the current user.
    Filterable by: bill, branch, status, payment_method, date.
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.view")]

    def get(self, request):
        qs = payment_acl.get_accessible_payments(request.user).select_related(
            "bill", "bill__order", "branch", "counter", "initiated_by"
        )

        # Filters
        bill_id = request.query_params.get("bill")
        branch_id = request.query_params.get("branch")
        pmt_status = request.query_params.get("status")
        pmt_method = request.query_params.get("payment_method")
        date_from = request.query_params.get("date_from")
        date_to = request.query_params.get("date_to")
        counter_id = request.query_params.get("counter")
        counter_session_id = request.query_params.get("counter_session")

        if bill_id:
            qs = qs.filter(bill_id=bill_id)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if pmt_status:
            qs = qs.filter(status=pmt_status)
        if pmt_method:
            qs = qs.filter(payment_method=pmt_method)
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)
        if counter_id:
            qs = qs.filter(counter_id=counter_id)
        if counter_session_id:
            qs = qs.filter(counter_session_id=counter_session_id)

        qs = qs.order_by("-created_at")

        # Pagination (reuse DRF default)
        from rest_framework.pagination import PageNumberPagination
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            serializer = PaymentListSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        return Response(PaymentListSerializer(qs, many=True).data)


class PaymentDetailView(APIView):
    """
    GET /api/payments/{id}/

    Retrieve full payment detail including nested refunds.
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.view"), HasPaymentAccess()]

    def get(self, request, pk):
        payment = _get_accessible_payment(request.user, pk)
        qs = Payment.objects.prefetch_related(
            "refunds__requested_by", "refunds__approved_by", "refunds__processed_by"
        ).select_related(
            "bill", "branch", "counter", "counter_session", "initiated_by", "completed_by"
        ).get(pk=payment.pk)
        return Response(PaymentReadSerializer(qs).data)


class CancelPaymentView(APIView):
    """
    POST /api/payments/{id}/cancel/

    Cancel a PENDING payment.
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.cancel"), HasPaymentAccess()]

    def post(self, request, pk):
        payment = _get_accessible_payment(request.user, pk)
        serializer = CancelPaymentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "VALIDATION_ERROR", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = services.cancel_payment(
                payment, request.user, reason=serializer.validated_data["reason"]
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(PaymentReadSerializer(updated).data)


# =============================================================================
# Bill-scoped Payment Views
# =============================================================================

class BillPaymentsView(APIView):
    """
    GET /api/payments/bill/{bill_id}/

    List all payments for a specific bill.
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.view")]

    def get(self, request, bill_id):
        bill = _get_accessible_bill(request.user, bill_id)
        qs = Payment.objects.filter(bill=bill).prefetch_related(
            "refunds"
        ).select_related(
            "branch", "counter", "initiated_by", "completed_by"
        ).order_by("created_at")
        return Response(PaymentReadSerializer(qs, many=True).data)


class BillPaymentSummaryView(APIView):
    """
    GET /api/payments/bill/{bill_id}/summary/

    Payment summary for a bill including totals, remaining amount, and status.

    Response:
    {
        "bill_id": "...",
        "bill_number": "B-2026-000001",
        "bill_total": "1000.00",
        "total_paid": "600.00",
        "total_refunded": "0.00",
        "remaining": "400.00",
        "payment_status": "PARTIALLY_PAID",
        "payments": [...]
    }
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.view")]

    def get(self, request, bill_id):
        bill = _get_accessible_bill(request.user, bill_id)
        summary = services.get_bill_payment_summary(bill)
        return Response(summary)


class BillReceiptView(APIView):
    """
    GET /api/payments/bill/{bill_id}/receipt/

    Full receipt data combining billing information with payment data.
    Extends the billing receipt with Phase 9 payment details.
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.receipt.print")]

    def get(self, request, bill_id):
        bill = _get_accessible_bill(request.user, bill_id)

        # Get base billing receipt data
        receipt_data = billing_services.get_bill_receipt_data(bill)

        # Merge payment data
        payment_data = services.get_payment_receipt_data(bill)
        receipt_data.update(payment_data)

        return Response(receipt_data)


# =============================================================================
# Refund Views
# =============================================================================

class PaymentRefundListCreateView(APIView):
    """
    GET  /api/payments/{id}/refunds/   — list refunds for a payment
    POST /api/payments/{id}/refunds/   — request a refund
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("payment.refund.request")()]
        return [IsAuthenticated(), HasPermission("payment.view")()]

    def get(self, request, pk):
        payment = _get_accessible_payment(request.user, pk)
        refunds = payment.refunds.select_related(
            "requested_by", "approved_by", "processed_by"
        ).order_by("requested_at")
        return Response(PaymentRefundReadSerializer(refunds, many=True).data)

    def post(self, request, pk):
        payment = _get_accessible_payment(request.user, pk)
        serializer = CreateRefundSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "VALIDATION_ERROR", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            refund = services.request_refund(
                payment,
                request.user,
                amount=serializer.validated_data["amount"],
                reason=serializer.validated_data["reason"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except Exception as exc:
            return _service_error(exc)
        refund.refresh_from_db()
        return Response(
            PaymentRefundReadSerializer(refund).data,
            status=status.HTTP_201_CREATED,
        )


class RefundDetailView(APIView):
    """
    GET /api/payments/refunds/{refund_id}/

    Retrieve refund detail.
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.view"), HasRefundAccess()]

    def get(self, request, refund_id):
        refund = _get_accessible_refund(request.user, refund_id)
        return Response(PaymentRefundReadSerializer(refund).data)


class ApproveRefundView(APIView):
    """
    POST /api/payments/refunds/{refund_id}/approve/
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.refund.approve"), HasRefundAccess()]

    def post(self, request, refund_id):
        refund = _get_accessible_refund(request.user, refund_id)
        try:
            updated = services.approve_refund(refund, request.user)
        except Exception as exc:
            return _service_error(exc)
        return Response(PaymentRefundReadSerializer(updated).data)


class RejectRefundView(APIView):
    """
    POST /api/payments/refunds/{refund_id}/reject/
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.refund.approve"), HasRefundAccess()]

    def post(self, request, refund_id):
        refund = _get_accessible_refund(request.user, refund_id)
        serializer = RejectRefundSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "VALIDATION_ERROR", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = services.reject_refund(
                refund, request.user, reason=serializer.validated_data["reason"]
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(PaymentRefundReadSerializer(updated).data)


class ProcessRefundView(APIView):
    """
    POST /api/payments/refunds/{refund_id}/process/
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.refund.process"), HasRefundAccess()]

    def post(self, request, refund_id):
        refund = _get_accessible_refund(request.user, refund_id)
        serializer = ProcessRefundSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "code": "VALIDATION_ERROR", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            updated = services.process_refund(
                refund,
                request.user,
                transaction_reference=serializer.validated_data.get("transaction_reference", ""),
                notes=serializer.validated_data.get("notes", ""),
            )
        except Exception as exc:
            return _service_error(exc)
        return Response(PaymentRefundReadSerializer(updated).data)


class CancelRefundView(APIView):
    """
    POST /api/payments/refunds/{refund_id}/cancel/
    """
    permission_classes = [IsAuthenticated, HasRefundAccess()]

    def post(self, request, refund_id):
        refund = _get_accessible_refund(request.user, refund_id)
        try:
            updated = services.cancel_refund(refund, request.user)
        except Exception as exc:
            return _service_error(exc)
        return Response(PaymentRefundReadSerializer(updated).data)


# =============================================================================
# Audit Log View
# =============================================================================

class PaymentAuditLogView(APIView):
    """
    GET /api/payments/{id}/audit/

    Retrieve the immutable audit trail for a payment.
    Requires payment.view permission.
    """
    permission_classes = [IsAuthenticated, HasPermission("payment.view"), HasPaymentAccess()]

    def get(self, request, pk):
        payment = _get_accessible_payment(request.user, pk)
        logs = PaymentAuditLog.objects.filter(payment=payment).select_related(
            "actor", "refund"
        ).order_by("created_at")
        return Response(PaymentAuditLogSerializer(logs, many=True).data)
