# =============================================================================
# RestaurantFlow — Orders Views
# Phase 6
#
# URL layout (see orders/urls.py):
#
#   TABLES:
#   GET    /api/tables/                         list
#   POST   /api/tables/                         create
#   GET    /api/tables/<id>/                    retrieve
#   PATCH  /api/tables/<id>/                    update
#   POST   /api/tables/<id>/disable/            soft disable
#   POST   /api/tables/<id>/enable/             re-enable
#
#   TABLE SESSIONS:
#   GET    /api/table-sessions/                 list
#   GET    /api/table-sessions/<id>/            retrieve
#   POST   /api/tables/<id>/sessions/open/      open session (nested under table)
#   POST   /api/table-sessions/<id>/close/      close session
#
#   ORDERS:
#   GET    /api/orders/                         list (filterable)
#   POST   /api/orders/                         create
#   GET    /api/orders/<id>/                    retrieve (detail with items)
#   PATCH  /api/orders/<id>/                    update notes/waiter on DRAFT
#   POST   /api/orders/<id>/confirm/            confirm DRAFT → CONFIRMED
#   POST   /api/orders/<id>/cancel/             cancel order
#   POST   /api/orders/<id>/assign-waiter/      assign/reassign waiter
#
#   ORDER ITEMS:
#   POST   /api/orders/<id>/items/              add item
#   PATCH  /api/order-items/<id>/               update item
#   DELETE /api/order-items/<id>/               remove item
#
# Security:
#   All views use scoped querysets from orders.access.
#   get_object() returns 404 (not 403) for UUIDs the user cannot see — IDOR.
# =============================================================================

import logging

from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from accounts.models import User
from accounts.permissions import HasPermission

from orders import access as order_acl
from orders import services
from orders.models import (
    DiningTable, TableSession, Order, OrderItem,
    OrderStatus, OrderType, TableStatus,
)
from orders.permissions import (
    HasTableAccess, HasTableSessionAccess,
    HasOrderAccess, HasOrderItemAccess,
)
from orders.serializers import (
    DiningTableSerializer,
    DiningTableListSerializer,
    TableSessionSerializer,
    OpenTableSessionSerializer,
    OrderSerializer,
    OrderDetailSerializer,
    CreateOrderSerializer,
    OrderItemSerializer,
    AddOrderItemSerializer,
    UpdateOrderItemSerializer,
    CancelOrderSerializer,
    AssignWaiterSerializer,
)

logger = logging.getLogger("orders")


# =============================================================================
# Helpers
# =============================================================================

def _error(code, message, http_status=400):
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _service_error(exc, fallback_code="REQUEST_FAILED"):
    """Convert service-layer ValidationError/PermissionDenied to a Response."""
    err = getattr(exc, "detail", None)
    if isinstance(err, dict):
        code = err.get("code", fallback_code)
        message = err.get("message", str(exc))
        return _error(code, message)
    if isinstance(err, list):
        return _error(fallback_code, err[0] if err else str(exc))
    return _error(fallback_code, str(exc))


# =============================================================================
# DiningTable Views
# =============================================================================

class DiningTableListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/tables/   — list tables (scoped to user)
    POST /api/tables/   — create a table (requires table.create)
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("table.create")()]
        return [IsAuthenticated(), HasPermission("table.view")()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return DiningTableListSerializer
        return DiningTableSerializer

    def get_queryset(self):
        qs = order_acl.get_accessible_tables(self.request.user)
        # Optional filters
        branch_id   = self.request.query_params.get("branch")
        section     = self.request.query_params.get("section")
        status_f    = self.request.query_params.get("status")
        occupied    = self.request.query_params.get("occupied")

        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if section:
            qs = qs.filter(section__icontains=section)
        if status_f:
            qs = qs.filter(status=status_f.upper())
        if occupied is not None:
            is_occ = occupied.lower() in ("true", "1", "yes")
            if is_occ:
                qs = qs.filter(sessions__status="OPEN").distinct()
            else:
                qs = qs.exclude(sessions__status="OPEN").distinct()

        return qs.prefetch_related("sessions")

    def perform_create(self, serializer):
        branch = serializer.validated_data.get("branch")
        if branch and not acl.can_access_branch(self.request.user, branch):
            raise PermissionDenied("You do not have access to the specified branch.")
        table = serializer.save()
        logger.info(
            "DiningTable created: %s/%s (id=%s) by user=%s",
            table.branch.name,
            table.table_number,
            table.id,
            self.request.user.email,
        )


class DiningTableDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/tables/<id>/   — retrieve
    PATCH /api/tables/<id>/   — update (requires table.update)
    """

    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [
                IsAuthenticated(),
                HasPermission("table.update")(),
                HasTableAccess(),
            ]
        return [IsAuthenticated(), HasPermission("table.view")(), HasTableAccess()]

    def get_serializer_class(self):
        return DiningTableSerializer

    def get_queryset(self):
        return order_acl.get_accessible_tables(self.request.user).prefetch_related("sessions")

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except DiningTable.DoesNotExist:
            raise NotFound("Dining table not found.")
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_update(self, serializer):
        table = serializer.save()
        logger.info(
            "DiningTable updated: %s (id=%s) by user=%s",
            table.table_number,
            table.id,
            self.request.user.email,
        )


class DiningTableDisableView(APIView):
    """POST /api/tables/<id>/disable/ — soft disable a table."""

    permission_classes = [IsAuthenticated, HasPermission("table.disable")]

    def post(self, request, pk):
        try:
            table = order_acl.get_accessible_tables(request.user).get(pk=pk)
        except DiningTable.DoesNotExist:
            raise NotFound("Dining table not found.")

        # Cannot disable a table with an open session
        if table.sessions.filter(status="OPEN").exists():
            return _error(
                "TABLE_HAS_OPEN_SESSION",
                "Cannot disable a table that has an open session. Close the session first.",
            )

        table.status = TableStatus.INACTIVE
        table.save(update_fields=["status", "updated_at"])
        logger.info(
            "DiningTable disabled: %s (id=%s) by user=%s",
            table.table_number, table.id, request.user.email,
        )
        return Response(DiningTableSerializer(table).data)


class DiningTableEnableView(APIView):
    """POST /api/tables/<id>/enable/ — re-enable a table."""

    permission_classes = [IsAuthenticated, HasPermission("table.update")]

    def post(self, request, pk):
        try:
            table = order_acl.get_accessible_tables(request.user).get(pk=pk)
        except DiningTable.DoesNotExist:
            raise NotFound("Dining table not found.")

        table.status = TableStatus.ACTIVE
        table.save(update_fields=["status", "updated_at"])
        logger.info(
            "DiningTable enabled: %s (id=%s) by user=%s",
            table.table_number, table.id, request.user.email,
        )
        return Response(DiningTableSerializer(table).data)


# =============================================================================
# TableSession — open (nested under table)
# =============================================================================

class TableSessionOpenView(APIView):
    """
    POST /api/tables/<pk>/sessions/open/

    Body: { "guest_count": 2, "notes": "..." }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            table = order_acl.get_accessible_tables(request.user).get(pk=pk)
        except DiningTable.DoesNotExist:
            raise NotFound("Dining table not found.")

        serializer = OpenTableSessionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            session = services.open_table_session(
                request.user,
                table=table,
                guest_count=serializer.validated_data["guest_count"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "TABLE_SESSION_OPEN_FAILED")

        return Response(
            TableSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# TableSession — standalone views
# =============================================================================

class TableSessionListView(generics.ListAPIView):
    """GET /api/table-sessions/"""

    permission_classes = [IsAuthenticated, HasPermission("table.session.view")]
    serializer_class = TableSessionSerializer

    def get_queryset(self):
        qs = order_acl.get_accessible_table_sessions(self.request.user)
        table_id    = self.request.query_params.get("table")
        branch_id   = self.request.query_params.get("branch")
        status_f    = self.request.query_params.get("status")
        if table_id:
            qs = qs.filter(table_id=table_id)
        if branch_id:
            qs = qs.filter(table__branch_id=branch_id)
        if status_f:
            qs = qs.filter(status=status_f.upper())
        return qs


class TableSessionDetailView(generics.RetrieveAPIView):
    """GET /api/table-sessions/<id>/"""

    permission_classes = [
        IsAuthenticated,
        HasPermission("table.session.view"),
        HasTableSessionAccess,
    ]
    serializer_class = TableSessionSerializer

    def get_queryset(self):
        return order_acl.get_accessible_table_sessions(self.request.user)

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except TableSession.DoesNotExist:
            raise NotFound("Table session not found.")
        self.check_object_permissions(self.request, obj)
        return obj


class TableSessionCloseView(APIView):
    """POST /api/table-sessions/<id>/close/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            session = order_acl.get_accessible_table_sessions(request.user).get(pk=pk)
        except TableSession.DoesNotExist:
            raise NotFound("Table session not found.")

        try:
            session = services.close_table_session(request.user, session=session)
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "TABLE_SESSION_CLOSE_FAILED")

        return Response(TableSessionSerializer(session).data)


# =============================================================================
# Order Views
# =============================================================================

class OrderListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/orders/   — list orders (scoped + filterable)
    POST /api/orders/   — create an order
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [IsAuthenticated(), HasPermission("order.view.branch")()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateOrderSerializer
        return OrderSerializer

    def get_queryset(self):
        qs = order_acl.get_accessible_orders(self.request.user)

        # Filtering
        branch_id    = self.request.query_params.get("branch")
        order_type   = self.request.query_params.get("order_type")
        status_f     = self.request.query_params.get("status")
        table_id     = self.request.query_params.get("table")
        counter_id   = self.request.query_params.get("counter")
        waiter_id    = self.request.query_params.get("assigned_waiter")
        created_by   = self.request.query_params.get("created_by")
        date         = self.request.query_params.get("date")  # YYYY-MM-DD

        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        if order_type:
            qs = qs.filter(order_type=order_type.upper())
        if status_f:
            qs = qs.filter(status=status_f.upper())
        if table_id:
            qs = qs.filter(table_id=table_id)
        if counter_id:
            qs = qs.filter(counter_id=counter_id)
        if waiter_id:
            qs = qs.filter(assigned_waiter_id=waiter_id)
        if created_by:
            qs = qs.filter(created_by_id=created_by)
        if date:
            qs = qs.filter(created_at__date=date)

        return qs.prefetch_related("items")

    def create(self, request, *args, **kwargs):
        serializer = CreateOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data

        # Resolve UUIDs to model instances
        from organizations.models import Branch
        from orders.models import DiningTable, TableSession
        from counters.models import Counter, CounterSession

        try:
            branch = Branch.objects.get(pk=data["branch"])
        except Branch.DoesNotExist:
            return _error("BRANCH_NOT_FOUND", "Branch not found.")

        # Resolve optional FKs
        table = table_session = counter = counter_session = assigned_waiter = None

        if data.get("table"):
            try:
                table = DiningTable.objects.get(pk=data["table"])
            except DiningTable.DoesNotExist:
                return _error("TABLE_NOT_FOUND", "Dining table not found.")

        if data.get("table_session"):
            try:
                table_session = TableSession.objects.get(pk=data["table_session"])
            except TableSession.DoesNotExist:
                return _error("TABLE_SESSION_NOT_FOUND", "Table session not found.")

        if data.get("counter"):
            try:
                counter = Counter.objects.get(pk=data["counter"])
            except Counter.DoesNotExist:
                return _error("COUNTER_NOT_FOUND", "Counter not found.")

        if data.get("counter_session"):
            try:
                counter_session = CounterSession.objects.get(pk=data["counter_session"])
            except CounterSession.DoesNotExist:
                return _error("COUNTER_SESSION_NOT_FOUND", "Counter session not found.")

        if data.get("assigned_waiter"):
            try:
                assigned_waiter = User.objects.get(pk=data["assigned_waiter"])
            except User.DoesNotExist:
                return _error("WAITER_NOT_FOUND", "Assigned waiter not found.")

        try:
            order = services.create_order(
                request.user,
                branch=branch,
                order_type=data["order_type"],
                table=table,
                table_session=table_session,
                counter=counter,
                counter_session=counter_session,
                guest_count=data.get("guest_count"),
                assigned_waiter=assigned_waiter,
                notes=data.get("notes", ""),
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "ORDER_CREATE_FAILED")

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class OrderDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/orders/<id>/   — detail with items
    PATCH /api/orders/<id>/   — update notes (DRAFT only)
    """

    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [
                IsAuthenticated(),
                HasPermission("order.update")(),
                HasOrderAccess(),
            ]
        return [IsAuthenticated(), HasPermission("order.view.branch")(), HasOrderAccess()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return OrderDetailSerializer
        return OrderSerializer

    def get_queryset(self):
        return order_acl.get_accessible_orders(
            self.request.user
        ).prefetch_related("items__menu_item")

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except Order.DoesNotExist:
            raise NotFound("Order not found.")
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_update(self, serializer):
        order = self.get_object()
        if order.status != OrderStatus.DRAFT:
            raise PermissionDenied("Only DRAFT orders can be updated.")
        serializer.save()


class OrderConfirmView(APIView):
    """POST /api/orders/<id>/confirm/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = order_acl.get_accessible_orders(request.user).get(pk=pk)
        except Order.DoesNotExist:
            raise NotFound("Order not found.")

        try:
            order = services.confirm_order(request.user, order=order)
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "ORDER_CONFIRM_FAILED")

        return Response(OrderDetailSerializer(order).data)


class OrderCancelView(APIView):
    """POST /api/orders/<id>/cancel/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = order_acl.get_accessible_orders(request.user).get(pk=pk)
        except Order.DoesNotExist:
            raise NotFound("Order not found.")

        serializer = CancelOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = services.cancel_order(
                request.user,
                order=order,
                reason=serializer.validated_data.get("reason", ""),
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "ORDER_CANCEL_FAILED")

        return Response(OrderDetailSerializer(order).data)


class OrderAssignWaiterView(APIView):
    """POST /api/orders/<id>/assign-waiter/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = order_acl.get_accessible_orders(request.user).get(pk=pk)
        except Order.DoesNotExist:
            raise NotFound("Order not found.")

        serializer = AssignWaiterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            waiter = User.objects.get(pk=serializer.validated_data["waiter"])
        except User.DoesNotExist:
            return _error("WAITER_NOT_FOUND", "Waiter not found.")

        try:
            order = services.assign_waiter(request.user, order=order, waiter=waiter)
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "ASSIGN_WAITER_FAILED")

        return Response(OrderSerializer(order).data)


# =============================================================================
# OrderItem Views
# =============================================================================

class OrderItemAddView(APIView):
    """POST /api/orders/<pk>/items/"""

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            order = order_acl.get_accessible_orders(request.user).get(pk=pk)
        except Order.DoesNotExist:
            raise NotFound("Order not found.")

        serializer = AddOrderItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item = services.add_order_item(
                request.user,
                order=order,
                menu_item_id=serializer.validated_data["menu_item"],
                quantity=serializer.validated_data["quantity"],
                notes=serializer.validated_data.get("notes", ""),
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "ORDER_ITEM_ADD_FAILED")

        return Response(
            OrderItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class OrderItemDetailView(APIView):
    """
    PATCH  /api/order-items/<id>/   — update quantity/notes
    DELETE /api/order-items/<id>/   — remove item from DRAFT order
    """

    permission_classes = [IsAuthenticated]

    def _get_item(self, request, pk):
        try:
            return order_acl.get_accessible_order_items(request.user).get(pk=pk)
        except OrderItem.DoesNotExist:
            raise NotFound("Order item not found.")

    def patch(self, request, pk):
        item = self._get_item(request, pk)

        serializer = UpdateOrderItemSerializer(data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"error": True, "message": "Validation error.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            item = services.update_order_item(
                request.user,
                item=item,
                quantity=serializer.validated_data.get("quantity"),
                notes=serializer.validated_data.get("notes"),
            )
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "ORDER_ITEM_UPDATE_FAILED")

        return Response(OrderItemSerializer(item).data)

    def delete(self, request, pk):
        item = self._get_item(request, pk)

        try:
            services.remove_order_item(request.user, item=item)
        except PermissionDenied as e:
            return _error("ACCESS_DENIED", str(e), 403)
        except Exception as e:
            return _service_error(e, "ORDER_ITEM_REMOVE_FAILED")

        return Response(status=status.HTTP_204_NO_CONTENT)
