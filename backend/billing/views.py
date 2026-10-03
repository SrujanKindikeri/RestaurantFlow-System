# =============================================================================
# RestaurantFlow — Billing Views
# Phase 8
#
# URL layout (see billing/urls.py):
#
#   BILLS:
#   GET    /api/billing/bills/                          list (filterable)
#   POST   /api/billing/bills/from-order/{order_id}/   create bill from order
#   GET    /api/billing/bills/{id}/                     retrieve detail
#   GET    /api/billing/bills/{id}/calculate/           preview/recalculate totals
#   POST   /api/billing/bills/{id}/discount/            apply discount
#   DELETE /api/billing/bills/{id}/discount/            remove discount
#   POST   /api/billing/bills/{id}/finalize/            finalize (locks bill)
#   POST   /api/billing/bills/{id}/cancel/              cancel
#   POST   /api/billing/bills/{id}/void/                void (escalated)
#   GET    /api/billing/bills/{id}/receipt/             receipt data (JSON)
#
#   CORRECTIONS:
#   GET    /api/billing/bill-corrections/               list corrections
#   POST   /api/billing/bills/{id}/corrections/         request a correction
#   GET    /api/billing/bill-corrections/{id}/          retrieve correction
#   POST   /api/billing/bill-corrections/{id}/approve/  approve correction
#   POST   /api/billing/bill-corrections/{id}/reject/   reject correction
#   POST   /api/billing/bill-corrections/{id}/cancel/   cancel (by requester)
#
# Security:
#   - All querysets are scoped via billing.access — IDOR prevention.
#   - get_object() returns 404 (not 403) for unauthorized UUIDs.
#   - Every action checks permission codes, not role names.
#   - Frontend totals are ignored — backend recalculates everything.
# =============================================================================

import logging
from decimal import Decimal

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from billing import access as bill_acl
from billing import services
from billing.models import Bill, BillItem, BillCorrectionRequest, BillStatus, CorrectionStatus
from billing.permissions import HasPermission, HasBillAccess, HasCorrectionAccess
from billing.serializers import (
    BillListSerializer,
    BillDetailSerializer,
    BillCalculationSerializer,
    ApplyDiscountSerializer,
    FinalizeBillSerializer,
    CancelBillSerializer,
    VoidBillSerializer,
    BillCorrectionRequestSerializer,
    CreateCorrectionRequestSerializer,
    ReviewCorrectionSerializer,
)

logger = logging.getLogger("billing")


# =============================================================================
# Helpers
# =============================================================================

def _error(code, message, http_status=400):
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _service_error(exc, fallback_code="REQUEST_FAILED"):
    """Convert service-layer ValidationError / PermissionDenied to a Response."""
    from rest_framework.exceptions import ValidationError, PermissionDenied as DRFPermDenied
    err = getattr(exc, "detail", None)
    if isinstance(err, dict):
        code = err.get("code", fallback_code)
        message = err.get("message", str(exc))
        http_status = (
            status.HTTP_403_FORBIDDEN
            if isinstance(exc, DRFPermDenied)
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(
            {"error": True, "code": code, "message": message},
            status=http_status,
        )
    if isinstance(err, list):
        msg = err[0] if err else str(exc)
        return Response(
            {"error": True, "code": fallback_code, "message": str(msg)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    http_status = (
        status.HTTP_403_FORBIDDEN
        if isinstance(exc, DRFPermDenied)
        else status.HTTP_400_BAD_REQUEST
    )
    return Response(
        {"error": True, "code": fallback_code, "message": str(exc)},
        status=http_status,
    )


def _get_bill_or_404(user, pk):
    """
    Fetch a bill scoped to the user's accessible branches.
    Returns 404 (not 403) for unauthorized UUIDs — IDOR prevention.
    """
    try:
        return bill_acl.get_accessible_bills(user).select_related(
            "order", "order__table", "order__counter", "order__counter_session",
            "branch", "branch__restaurant", "branch__restaurant__organization",
            "branch__restaurant__settings",
            "created_by", "finalized_by", "cancelled_by",
        ).get(pk=pk)
    except Bill.DoesNotExist:
        raise NotFound(f"Bill {pk} not found.")


def _get_correction_or_404(user, pk):
    """
    Fetch a correction request scoped to the user's accessible branches.
    Returns 404 for unauthorized UUIDs.
    """
    try:
        return bill_acl.get_accessible_corrections(user).select_related(
            "bill", "bill__branch", "requested_by", "reviewed_by"
        ).get(pk=pk)
    except BillCorrectionRequest.DoesNotExist:
        raise NotFound(f"Correction request {pk} not found.")


def _get_max_discount_pct(user) -> Decimal:
    """
    Determine the maximum discount percentage for this user.

    Permission tiers:
        discount.apply_large → 100% maximum
        discount.apply       →  10% maximum (default conservative limit)

    The maximum should ideally come from restaurant configuration.
    In Phase 8, we use permission-based tiers as a practical approach.
    Restaurant-specific maximums can be added via RestaurantSettings in a later phase.
    """
    if acl.has_permission(user, "discount.apply_large"):
        return Decimal("100")
    # Standard cashier discount limit
    return Decimal("10")


# =============================================================================
# Bill List
# =============================================================================

class BillListView(generics.ListAPIView):
    """
    GET /api/billing/bills/

    Returns a paginated list of bills scoped to the requesting user.
    Filterable by: status, order_type, branch, date range, bill_number, cashier.

    Permissions: bill.view
    """

    serializer_class = BillListSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.view")()]

    def get_queryset(self):
        qs = bill_acl.get_accessible_bills(self.request.user).select_related(
            "order", "branch", "branch__restaurant",
            "created_by", "finalized_by",
        )

        params = self.request.query_params

        # Filter by status
        bill_status = params.get("status")
        if bill_status:
            qs = qs.filter(status=bill_status)

        # Filter by order_type
        order_type = params.get("order_type")
        if order_type:
            qs = qs.filter(order__order_type=order_type)

        # Filter by branch
        branch_id = params.get("branch")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        # Filter by bill_number
        bill_number = params.get("bill_number")
        if bill_number:
            qs = qs.filter(bill_number__icontains=bill_number)

        # Filter by order_number
        order_number = params.get("order_number")
        if order_number:
            qs = qs.filter(order__order_number__icontains=order_number)

        # Filter by cashier (email)
        cashier = params.get("cashier")
        if cashier:
            qs = qs.filter(
                Q(created_by__email__icontains=cashier) |
                Q(finalized_by__email__icontains=cashier)
            )

        # Date range filters
        date_from = params.get("date_from")
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = params.get("date_to")
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        return qs.order_by("-created_at")


# =============================================================================
# Create Bill from Order
# =============================================================================

class CreateBillFromOrderView(APIView):
    """
    POST /api/billing/bills/from-order/{order_id}/

    Create a bill from a confirmed order.
    Idempotent: returns the existing bill if one already exists.

    Permissions: bill.create
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.create")()]

    def post(self, request, order_id):
        from orders.models import Order
        from orders import access as order_acl

        # Fetch the order — scoped to user's accessible orders
        try:
            order = order_acl.get_accessible_orders(request.user).select_related(
                "branch", "branch__restaurant"
            ).get(pk=order_id)
        except Order.DoesNotExist:
            raise NotFound(f"Order {order_id} not found.")

        try:
            bill = services.create_bill_from_order(order, request.user)
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "BILL_CREATION_FAILED")

        serializer = BillDetailSerializer(bill)
        # 200 if existing, 201 if newly created
        http_status = (
            status.HTTP_201_CREATED
            if bill.created_at == bill.updated_at
            else status.HTTP_200_OK
        )
        return Response(serializer.data, status=http_status)


# =============================================================================
# Bill Detail
# =============================================================================

class BillDetailView(generics.RetrieveAPIView):
    """
    GET /api/billing/bills/{id}/

    Returns the full bill detail including items, tax breakdown, corrections.

    Permissions: bill.view
    """

    serializer_class = BillDetailSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.view")()]

    def get_object(self):
        return _get_bill_or_404(self.request.user, self.kwargs["pk"])


# =============================================================================
# Bill Calculate (preview)
# =============================================================================

class BillCalculateView(APIView):
    """
    GET /api/billing/bills/{id}/calculate/

    Recalculate and preview bill totals without finalizing.
    For DRAFT bills: saves the recalculated values.
    For FINALIZED bills: returns a preview (does not overwrite).

    Permissions: bill.view
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.view")()]

    def get(self, request, pk):
        bill = _get_bill_or_404(request.user, pk)

        result = services.calculate_bill(bill)
        return Response(result, status=status.HTTP_200_OK)


# =============================================================================
# Apply / Remove Discount
# =============================================================================

class BillDiscountView(APIView):
    """
    POST   /api/billing/bills/{id}/discount/   — apply discount
    DELETE /api/billing/bills/{id}/discount/   — remove discount

    Permissions: discount.apply (POST), discount.apply (DELETE)

    Large discounts additionally require discount.apply_large.
    The maximum allowed discount percentage is determined server-side
    based on the user's permissions — never trusted from the client.
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("discount.apply")()]

    def post(self, request, pk):
        bill = _get_bill_or_404(request.user, pk)

        ser = ApplyDiscountSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        discount_type = ser.validated_data["discount_type"]
        discount_value = ser.validated_data["discount_value"]

        # Check if this is a large discount requiring elevated permission
        if discount_type == "PERCENTAGE" and discount_value > Decimal("10"):
            if not acl.has_permission(request.user, "discount.apply_large"):
                return _error(
                    "LARGE_DISCOUNT_NOT_PERMITTED",
                    f"A discount of {discount_value}% requires the "
                    f"'discount.apply_large' permission.",
                    http_status=403,
                )

        max_pct = _get_max_discount_pct(request.user)

        try:
            updated_bill = services.apply_discount(
                bill,
                request.user,
                discount_type=discount_type,
                value=discount_value,
                max_pct=max_pct,
            )
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "DISCOUNT_FAILED")

        return Response(BillDetailSerializer(updated_bill).data)

    def delete(self, request, pk):
        bill = _get_bill_or_404(request.user, pk)

        try:
            updated_bill = services.remove_discount(bill, request.user)
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "REMOVE_DISCOUNT_FAILED")

        return Response(BillDetailSerializer(updated_bill).data)


# =============================================================================
# Finalize Bill
# =============================================================================

class BillFinalizeView(APIView):
    """
    POST /api/billing/bills/{id}/finalize/

    Finalize a DRAFT bill — locks all financial values.
    Idempotent: returns FINALIZED bill if already finalized.

    Permissions: bill.finalize
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.finalize")()]

    def post(self, request, pk):
        bill = _get_bill_or_404(request.user, pk)

        ser = FinalizeBillSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        notes = ser.validated_data.get("notes", "")
        if notes and bill.status == BillStatus.DRAFT:
            bill.notes = notes
            bill.save(update_fields=["notes", "updated_at"])

        try:
            finalized = services.finalize_bill(bill, request.user)
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "FINALIZE_FAILED")

        return Response(BillDetailSerializer(finalized).data)


# =============================================================================
# Cancel Bill
# =============================================================================

class BillCancelView(APIView):
    """
    POST /api/billing/bills/{id}/cancel/

    Cancel a bill (DRAFT or FINALIZED).
    FINALIZED bills require bill.cancel permission.

    Permissions: bill.cancel
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.cancel")()]

    def post(self, request, pk):
        bill = _get_bill_or_404(request.user, pk)

        ser = CancelBillSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            cancelled = services.cancel_bill(
                bill, request.user, reason=ser.validated_data["reason"]
            )
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "CANCEL_FAILED")

        return Response(BillDetailSerializer(cancelled).data)


# =============================================================================
# Void Bill
# =============================================================================

class BillVoidView(APIView):
    """
    POST /api/billing/bills/{id}/void/

    Void a FINALIZED bill (escalated action, requires bill.void).

    Permissions: bill.void
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.void")()]

    def post(self, request, pk):
        bill = _get_bill_or_404(request.user, pk)

        ser = VoidBillSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            voided = services.void_bill(
                bill, request.user, reason=ser.validated_data["reason"]
            )
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "VOID_FAILED")

        return Response(BillDetailSerializer(voided).data)


# =============================================================================
# Bill Receipt
# =============================================================================

class BillReceiptView(APIView):
    """
    GET /api/billing/bills/{id}/receipt/

    Returns structured receipt data for printing.
    Payment fields are intentionally absent (Phase 9).

    Permissions: bill.print
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.print")()]

    def get(self, request, pk):
        bill = _get_bill_or_404(request.user, pk)

        receipt_data = services.get_bill_receipt_data(bill)
        return Response(receipt_data)


# =============================================================================
# Correction List
# =============================================================================

class BillCorrectionListView(generics.ListAPIView):
    """
    GET /api/billing/bill-corrections/

    Returns paginated corrections scoped to user's accessible branches.
    Filterable by: status, bill_id, correction_type.

    Permissions: bill.correction.request (to see own) or bill.correction.approve
    """

    serializer_class = BillCorrectionRequestSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.view")()]

    def get_queryset(self):
        qs = bill_acl.get_accessible_corrections(self.request.user).select_related(
            "bill", "requested_by", "reviewed_by"
        )

        params = self.request.query_params

        correction_status = params.get("status")
        if correction_status:
            qs = qs.filter(status=correction_status)

        bill_id = params.get("bill")
        if bill_id:
            qs = qs.filter(bill_id=bill_id)

        correction_type = params.get("correction_type")
        if correction_type:
            qs = qs.filter(correction_type=correction_type)

        return qs.order_by("-created_at")


# =============================================================================
# Request Correction
# =============================================================================

class RequestBillCorrectionView(APIView):
    """
    POST /api/billing/bills/{id}/corrections/

    Submit a correction request for a FINALIZED bill.

    Permissions: bill.correction.request
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.correction.request")()]

    def post(self, request, pk):
        bill = _get_bill_or_404(request.user, pk)

        ser = CreateCorrectionRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            correction = services.request_bill_correction(
                bill,
                request.user,
                correction_type=ser.validated_data["correction_type"],
                reason=ser.validated_data["reason"],
            )
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "CORRECTION_REQUEST_FAILED")

        return Response(
            BillCorrectionRequestSerializer(correction).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# Correction Detail
# =============================================================================

class BillCorrectionDetailView(generics.RetrieveAPIView):
    """
    GET /api/billing/bill-corrections/{id}/

    Permissions: bill.view
    """

    serializer_class = BillCorrectionRequestSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.view")()]

    def get_object(self):
        return _get_correction_or_404(self.request.user, self.kwargs["pk"])


# =============================================================================
# Approve Correction
# =============================================================================

class ApproveCorrectionView(APIView):
    """
    POST /api/billing/bill-corrections/{id}/approve/

    Approve a PENDING correction request.
    Reviewer must NOT be the same as the requester.

    Permissions: bill.correction.approve
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.correction.approve")()]

    def post(self, request, pk):
        correction = _get_correction_or_404(request.user, pk)

        ser = ReviewCorrectionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        try:
            approved = services.approve_bill_correction(
                correction,
                request.user,
                note=ser.validated_data.get("review_note", ""),
            )
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "CORRECTION_APPROVE_FAILED")

        return Response(BillCorrectionRequestSerializer(approved).data)


# =============================================================================
# Reject Correction
# =============================================================================

class RejectCorrectionView(APIView):
    """
    POST /api/billing/bill-corrections/{id}/reject/

    Reject a PENDING correction request.
    review_note is required when rejecting.

    Permissions: bill.correction.approve
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("bill.correction.approve")()]

    def post(self, request, pk):
        correction = _get_correction_or_404(request.user, pk)

        ser = ReviewCorrectionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        note = ser.validated_data.get("review_note", "")
        if not note:
            return _error(
                "REVIEW_NOTE_REQUIRED",
                "A review note is required when rejecting a correction request.",
            )

        try:
            rejected = services.reject_bill_correction(
                correction,
                request.user,
                note=note,
            )
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "CORRECTION_REJECT_FAILED")

        return Response(BillCorrectionRequestSerializer(rejected).data)


# =============================================================================
# Cancel Correction
# =============================================================================

class CancelCorrectionView(APIView):
    """
    POST /api/billing/bill-corrections/{id}/cancel/

    Cancel a PENDING correction request (by the original requester
    or someone with bill.correction.approve permission).

    Permissions: bill.correction.request (own) or bill.correction.approve
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def post(self, request, pk):
        correction = _get_correction_or_404(request.user, pk)

        try:
            cancelled = services.cancel_bill_correction(correction, request.user)
        except (PermissionDenied, Exception) as exc:
            from rest_framework.exceptions import PermissionDenied as DRFPerm
            if isinstance(exc, DRFPerm):
                raise
            return _service_error(exc, "CORRECTION_CANCEL_FAILED")

        return Response(BillCorrectionRequestSerializer(cancelled).data)
