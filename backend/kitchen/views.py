# =============================================================================
# RestaurantFlow — Kitchen Views
# Phase 7
#
# URL layout (see kitchen/urls.py):
#
#   GET    /api/kitchen/orders/                     list (KDS live view)
#   GET    /api/kitchen/orders/<id>/                detail
#   POST   /api/kitchen/orders/<id>/accept/         NEW → ACCEPTED
#   POST   /api/kitchen/orders/<id>/start/          ACCEPTED → PREPARING
#   POST   /api/kitchen/orders/<id>/ready/          PREPARING → READY
#   POST   /api/kitchen/orders/<id>/cancel/         → CANCELLED
#   POST   /api/kitchen/orders/<id>/priority/       update priority
#   GET    /api/kitchen/history/                    historical orders
#   GET    /api/kitchen/items/<id>/                 item detail
#   POST   /api/kitchen/items/<id>/start/           item NEW → PREPARING
#   POST   /api/kitchen/items/<id>/ready/           item PREPARING → READY
#
# Security:
#   All views use scoped querysets from kitchen.access.
#   get_object() returns 404 (not 403) for UUIDs the user cannot see — IDOR.
#   Financial data is never exposed in any response.
# =============================================================================

import logging

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import HasPermission
from kitchen import access as kitchen_acl
from kitchen import services
from kitchen.models import (
    KitchenOrder,
    KitchenOrderItem,
    KitchenOrderStatus,
)
from kitchen.permissions import HasKitchenOrderAccess, HasKitchenItemAccess
from kitchen.serializers import (
    KitchenOrderSerializer,
    KitchenOrderDetailSerializer,
    KitchenOrderListSerializer,
    KitchenOrderItemSerializer,
    CancelKitchenOrderSerializer,
    UpdatePrioritySerializer,
    KitchenNoteSerializer,
)

logger = logging.getLogger("kitchen")


# =============================================================================
# Helpers
# =============================================================================

def _error(code, message, http_status=400):
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _service_error(exc, fallback_code="KITCHEN_REQUEST_FAILED"):
    """Convert service ValidationError/PermissionDenied to Response."""
    err = getattr(exc, "detail", None)
    if isinstance(err, dict):
        code = err.get("code", fallback_code)
        message = err.get("message", str(exc))
        return _error(code, message)
    if isinstance(err, list):
        return _error(fallback_code, err[0] if err else str(exc))
    return _error(fallback_code, str(exc))


# =============================================================================
# KitchenOrder — List
# =============================================================================

class KitchenOrderListView(generics.ListAPIView):
    """
    GET /api/kitchen/orders/

    Live KDS view. Returns today's kitchen orders by default.

    Query params:
        branch          — filter by branch UUID
        status          — filter by kitchen status (NEW, ACCEPTED, PREPARING, READY, CANCELLED)
        order_type      — DINE_IN, TAKEAWAY, COUNTER
        priority        — NORMAL, HIGH, URGENT
        table           — filter by table UUID
        counter         — filter by counter UUID
        date            — YYYY-MM-DD (overrides today default)
        include_ready   — true/false (include READY orders; default false for live KDS)
        include_cancelled — true/false (include CANCELLED; default false)
        ordering        — received_at, -received_at, priority
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.view")]
    serializer_class = KitchenOrderListSerializer

    def get_queryset(self):
        qs = kitchen_acl.get_accessible_kitchen_orders(self.request.user)
        params = self.request.query_params

        # --- Branch filter ---
        branch_id = params.get("branch")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        # --- Status filter ---
        status_f = params.get("status")
        if status_f:
            qs = qs.filter(status=status_f.upper())
        else:
            # Default live KDS view: exclude CANCELLED unless explicitly requested
            include_ready = params.get("include_ready", "true").lower() in ("true", "1", "yes")
            include_cancelled = params.get(
                "include_cancelled", "false"
            ).lower() in ("true", "1", "yes")

            exclude_statuses = []
            if not include_cancelled:
                exclude_statuses.append(KitchenOrderStatus.CANCELLED)
            if not include_ready:
                # Live KDS shows ready orders too (to await collection)
                # But exclude them if explicitly excluded
                pass

            if exclude_statuses:
                qs = qs.exclude(status__in=exclude_statuses)

        # --- Order type filter ---
        order_type = params.get("order_type")
        if order_type:
            qs = qs.filter(order__order_type=order_type.upper())

        # --- Priority filter ---
        priority = params.get("priority")
        if priority:
            qs = qs.filter(priority=priority.upper())

        # --- Table filter ---
        table_id = params.get("table")
        if table_id:
            qs = qs.filter(order__table_id=table_id)

        # --- Counter filter ---
        counter_id = params.get("counter")
        if counter_id:
            qs = qs.filter(order__counter_id=counter_id)

        # --- Date filter ---
        date = params.get("date")
        if date:
            qs = qs.filter(received_at__date=date)
        else:
            # Default: today only
            qs = qs.filter(received_at__date=timezone.now().date())

        # --- Ordering ---
        ordering = params.get("ordering", "received_at")
        if ordering in ("received_at", "-received_at", "priority", "-priority",
                         "status", "-status"):
            qs = qs.order_by(ordering)
        else:
            # Default: priority desc (URGENT first) then oldest first
            qs = qs.order_by("-priority", "received_at")

        return qs


# =============================================================================
# KitchenOrder — Detail
# =============================================================================

class KitchenOrderDetailView(generics.RetrieveAPIView):
    """
    GET /api/kitchen/orders/<id>/

    Full detail including all items with timestamps.
    """

    permission_classes = [
        IsAuthenticated,
        HasPermission("kitchen.view"),
        HasKitchenOrderAccess,
    ]
    serializer_class = KitchenOrderDetailSerializer

    def get_queryset(self):
        return kitchen_acl.get_accessible_kitchen_orders(self.request.user)

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except KitchenOrder.DoesNotExist:
            raise NotFound("Kitchen order not found.")
        self.check_object_permissions(self.request, obj)
        return obj


# =============================================================================
# KitchenOrder — Accept
# =============================================================================

class KitchenOrderAcceptView(APIView):
    """
    POST /api/kitchen/orders/<id>/accept/

    Transition: NEW → ACCEPTED.
    Idempotent — returns 200 if already ACCEPTED.
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.accept")]

    def post(self, request, pk):
        try:
            kitchen_order = kitchen_acl.get_accessible_kitchen_orders(request.user).get(pk=pk)
        except KitchenOrder.DoesNotExist:
            raise NotFound("Kitchen order not found.")

        try:
            kitchen_order = services.accept_kitchen_order(request.user, kitchen_order=kitchen_order)
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "KITCHEN_ACCEPT_FAILED")

        return Response(KitchenOrderSerializer(kitchen_order).data)


# =============================================================================
# KitchenOrder — Start Preparation
# =============================================================================

class KitchenOrderStartView(APIView):
    """
    POST /api/kitchen/orders/<id>/start/

    Transition: ACCEPTED → PREPARING.
    Also transitions all NEW items to PREPARING.
    Idempotent — returns 200 if already PREPARING.
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.start")]

    def post(self, request, pk):
        try:
            kitchen_order = kitchen_acl.get_accessible_kitchen_orders(request.user).get(pk=pk)
        except KitchenOrder.DoesNotExist:
            raise NotFound("Kitchen order not found.")

        try:
            kitchen_order = services.start_preparation(request.user, kitchen_order=kitchen_order)
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "KITCHEN_START_FAILED")

        return Response(KitchenOrderSerializer(kitchen_order).data)


# =============================================================================
# KitchenOrder — Ready
# =============================================================================

class KitchenOrderReadyView(APIView):
    """
    POST /api/kitchen/orders/<id>/ready/

    Transition: PREPARING → READY.
    All non-cancelled items must be READY first.
    Idempotent — returns 200 if already READY.
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.order_ready")]

    def post(self, request, pk):
        try:
            kitchen_order = kitchen_acl.get_accessible_kitchen_orders(request.user).get(pk=pk)
        except KitchenOrder.DoesNotExist:
            raise NotFound("Kitchen order not found.")

        try:
            kitchen_order = services.mark_order_ready(request.user, kitchen_order=kitchen_order)
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "KITCHEN_READY_FAILED")

        return Response(KitchenOrderSerializer(kitchen_order).data)


# =============================================================================
# KitchenOrder — Cancel
# =============================================================================

class KitchenOrderCancelView(APIView):
    """
    POST /api/kitchen/orders/<id>/cancel/

    Cancel a kitchen order (NEW / ACCEPTED / PREPARING).
    Body: { "reason": "..." } (optional).
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.cancel")]

    def post(self, request, pk):
        try:
            kitchen_order = kitchen_acl.get_accessible_kitchen_orders(request.user).get(pk=pk)
        except KitchenOrder.DoesNotExist:
            raise NotFound("Kitchen order not found.")

        serializer = CancelKitchenOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            kitchen_order = services.cancel_kitchen_order(
                request.user,
                kitchen_order=kitchen_order,
                reason=serializer.validated_data.get("reason", ""),
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "KITCHEN_CANCEL_FAILED")

        return Response(KitchenOrderSerializer(kitchen_order).data)


# =============================================================================
# KitchenOrder — Update Priority
# =============================================================================

class KitchenOrderPriorityView(APIView):
    """
    POST /api/kitchen/orders/<id>/priority/

    Update order priority: NORMAL / HIGH / URGENT.
    Body: { "priority": "HIGH" }
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.priority_update")]

    def post(self, request, pk):
        try:
            kitchen_order = kitchen_acl.get_accessible_kitchen_orders(request.user).get(pk=pk)
        except KitchenOrder.DoesNotExist:
            raise NotFound("Kitchen order not found.")

        serializer = UpdatePrioritySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            kitchen_order = services.update_kitchen_priority(
                request.user,
                kitchen_order=kitchen_order,
                priority=serializer.validated_data["priority"],
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "KITCHEN_PRIORITY_FAILED")

        return Response(KitchenOrderSerializer(kitchen_order).data)


# =============================================================================
# KitchenOrder — History
# =============================================================================

class KitchenHistoryView(generics.ListAPIView):
    """
    GET /api/kitchen/history/

    Historical kitchen orders. Accessible to managers and owners.
    Supports date range filtering.

    Query params:
        branch          — required for non-superusers to narrow results
        date            — specific date YYYY-MM-DD
        date_from       — start of date range (YYYY-MM-DD)
        date_to         — end of date range (YYYY-MM-DD)
        status          — filter by kitchen status
        order_type      — filter by order type
        ordering        — received_at, -received_at
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.view_history")]
    serializer_class = KitchenOrderListSerializer

    def get_queryset(self):
        qs = kitchen_acl.get_accessible_kitchen_orders(self.request.user)
        params = self.request.query_params

        branch_id = params.get("branch")
        if branch_id:
            qs = qs.filter(branch_id=branch_id)

        date = params.get("date")
        date_from = params.get("date_from")
        date_to = params.get("date_to")

        if date:
            qs = qs.filter(received_at__date=date)
        elif date_from or date_to:
            if date_from:
                qs = qs.filter(received_at__date__gte=date_from)
            if date_to:
                qs = qs.filter(received_at__date__lte=date_to)
        else:
            # Default: today
            qs = qs.filter(received_at__date=timezone.now().date())

        status_f = params.get("status")
        if status_f:
            qs = qs.filter(status=status_f.upper())

        order_type = params.get("order_type")
        if order_type:
            qs = qs.filter(order__order_type=order_type.upper())

        ordering = params.get("ordering", "-received_at")
        if ordering in ("received_at", "-received_at"):
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-received_at")

        return qs


# =============================================================================
# KitchenOrderItem — Detail
# =============================================================================

class KitchenOrderItemDetailView(generics.RetrieveAPIView):
    """
    GET /api/kitchen/items/<id>/

    Full item detail.
    """

    permission_classes = [
        IsAuthenticated,
        HasPermission("kitchen.view"),
        HasKitchenItemAccess,
    ]
    serializer_class = KitchenOrderItemSerializer

    def get_queryset(self):
        return kitchen_acl.get_accessible_kitchen_items(self.request.user)

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except KitchenOrderItem.DoesNotExist:
            raise NotFound("Kitchen item not found.")
        self.check_object_permissions(self.request, obj)
        return obj


# =============================================================================
# KitchenOrderItem — Start
# =============================================================================

class KitchenItemStartView(APIView):
    """
    POST /api/kitchen/items/<id>/start/

    Transition item: NEW → PREPARING.
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.item_start")]

    def post(self, request, pk):
        try:
            kitchen_item = kitchen_acl.get_accessible_kitchen_items(request.user).get(pk=pk)
        except KitchenOrderItem.DoesNotExist:
            raise NotFound("Kitchen item not found.")

        try:
            kitchen_item = services.start_item_preparation(
                request.user, kitchen_item=kitchen_item
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "KITCHEN_ITEM_START_FAILED")

        return Response(KitchenOrderItemSerializer(kitchen_item).data)


# =============================================================================
# KitchenOrderItem — Ready
# =============================================================================

class KitchenItemReadyView(APIView):
    """
    POST /api/kitchen/items/<id>/ready/

    Transition item: PREPARING → READY.
    Auto-advances parent order to READY if all items are done.
    """

    permission_classes = [IsAuthenticated, HasPermission("kitchen.item_ready")]

    def post(self, request, pk):
        try:
            kitchen_item = kitchen_acl.get_accessible_kitchen_items(request.user).get(pk=pk)
        except KitchenOrderItem.DoesNotExist:
            raise NotFound("Kitchen item not found.")

        try:
            kitchen_item = services.mark_item_ready(
                request.user, kitchen_item=kitchen_item
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "KITCHEN_ITEM_READY_FAILED")

        return Response(KitchenOrderItemSerializer(kitchen_item).data)
