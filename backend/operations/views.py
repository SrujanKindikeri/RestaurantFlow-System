# =============================================================================
# RestaurantFlow — Operations Views
# Phase 19: Advanced POS & Restaurant Operations
#
# Views are thin — all business logic lives in service modules.
# Security is enforced in access.py and permissions.py.
# =============================================================================

import logging

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl

from operations import services
from operations.access import (
    get_accessible_pos_sessions, get_accessible_shifts,
    get_accessible_bill_splits, get_accessible_modifier_groups,
    get_accessible_change_requests,
)
from operations.exceptions import (
    POSSessionConflict, CounterSessionNotActive, UnauthorizedCounter,
    OrderStateConflict, TableTransferConflict, TableMergeConflict,
    OrderMergeConflict, BillSplitConflict, ModifierValidationError,
    ShiftAlreadyClosed, ReceiptPrintNotAllowed, SKUNotFound,
    BillNotSplittable, TableNotAvailable, IncompatibleOrders,
)
from operations.permissions import (
    CanStartPOSSession, CanPausePOSSession, CanEndPOSSession,
    CanHoldOrder, CanSetUrgentPriority, CanManageModifiers,
    CanRequestOrderChange, CanApproveOrderChange, CanAssignWaiter,
    CanTransferTable, CanMergeTable, CanManageTables, CanSplitBill,
    CanPrintReceipt, CanReprintReceipt, CanManageShifts,
    CanViewOperationsDashboard, CanMergeOrders, HasPOSAccess,
)
from operations.serializers import (
    POSSessionSerializer, POSSessionStartSerializer,
    BarcodeScanSerializer, BarcodeScanResultSerializer,
    MenuModifierGroupSerializer, MenuModifierGroupCreateSerializer,
    MenuModifierOptionSerializer,
    AddModifierSerializer, OrderItemModifierSerializer,
    OrderChangeRequestSerializer, OrderChangeRequestCreateSerializer,
    OrderChangeRequestReviewSerializer,
    TableTransferSerializer, TableTransferRequestSerializer,
    TableMergeSerializer, TableMergeRequestSerializer,
    OrderMergeRequestSerializer, OrderMergeRequestCreateSerializer,
    BillSplitSerializer, BillSplitCreateSerializer,
    ReceiptPrintLogSerializer, PrintReceiptSerializer,
    OperationalShiftSerializer, OperationalShiftCreateSerializer,
    ShiftCloseSerializer, ShiftHandoverNoteSerializer,
    ShiftHandoverNoteCreateSerializer,
    OrderPrioritySerializer, OrderWaiterSerializer,
    TableStatusUpdateSerializer,
    TableOperationalStatusSerializer,
)

logger = logging.getLogger("operations")


# =============================================================================
# POS Session Views
# =============================================================================

class POSSessionView(APIView):
    """GET current POS session info for the authenticated user."""
    permission_classes = [IsAuthenticated, HasPOSAccess]

    def get(self, request):
        sessions = get_accessible_pos_sessions(request.user).filter(
            user=request.user,
            status__in=["ACTIVE", "PAUSED"],
        ).select_related("counter", "counter_session", "branch")
        serializer = POSSessionSerializer(sessions, many=True)
        return Response(serializer.data)


class POSSessionStartView(APIView):
    permission_classes = [IsAuthenticated, CanStartPOSSession]

    def post(self, request):
        ser = POSSessionStartSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        accessible_branches = acl.get_accessible_branches(request.user)
        if not accessible_branches.exists():
            return Response(
                {"detail": "No accessible branches found."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Use the first accessible branch (counter validation will ensure scope)
        branch = accessible_branches.first()

        session = services.start_pos_session(
            user=request.user,
            counter_id=ser.validated_data["counter_id"],
            device_identifier=ser.validated_data.get("device_identifier", ""),
            branch=branch,
        )
        return Response(
            POSSessionSerializer(session).data,
            status=status.HTTP_201_CREATED,
        )


class POSSessionPauseView(APIView):
    permission_classes = [IsAuthenticated, CanPausePOSSession]

    def post(self, request, session_id):
        try:
            session = get_accessible_pos_sessions(request.user).get(pk=session_id)
        except Exception:
            return Response({"detail": "POS session not found."}, status=status.HTTP_404_NOT_FOUND)

        session = services.pause_pos_session(session=session, user=request.user)
        return Response(POSSessionSerializer(session).data)


class POSSessionResumeView(APIView):
    permission_classes = [IsAuthenticated, CanStartPOSSession]

    def post(self, request, session_id):
        try:
            session = get_accessible_pos_sessions(request.user).get(pk=session_id)
        except Exception:
            return Response({"detail": "POS session not found."}, status=status.HTTP_404_NOT_FOUND)

        session = services.resume_pos_session(session=session, user=request.user)
        return Response(POSSessionSerializer(session).data)


class POSSessionEndView(APIView):
    permission_classes = [IsAuthenticated, CanEndPOSSession]

    def post(self, request, session_id):
        try:
            session = get_accessible_pos_sessions(request.user).get(pk=session_id)
        except Exception:
            return Response({"detail": "POS session not found."}, status=status.HTTP_404_NOT_FOUND)

        session = services.end_pos_session(session=session, user=request.user)
        return Response(POSSessionSerializer(session).data)


# =============================================================================
# Barcode / SKU Scan
# =============================================================================

class BarcodeScanView(APIView):
    permission_classes = [IsAuthenticated, HasPOSAccess]

    def post(self, request):
        ser = BarcodeScanSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        accessible_branches = acl.get_accessible_branches(request.user)
        branch = accessible_branches.first()
        if not branch:
            return Response(
                {"detail": "No accessible branch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        result = services.scan_barcode_or_sku(
            barcode_or_sku=ser.validated_data["barcode_or_sku"],
            branch=branch,
        )
        return Response(result)


# =============================================================================
# Order Operations
# =============================================================================

class OrderHoldView(APIView):
    permission_classes = [IsAuthenticated, CanHoldOrder]

    def post(self, request, order_id):
        from orders.models import Order
        accessible = acl.get_accessible_branches(request.user)
        try:
            order = Order.objects.get(pk=order_id, branch__in=accessible)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        order = services.hold_order(order=order, user=request.user)
        return Response({"id": str(order.id), "status": order.status})


class OrderResumeView(APIView):
    permission_classes = [IsAuthenticated, CanHoldOrder]

    def post(self, request, order_id):
        from orders.models import Order
        accessible = acl.get_accessible_branches(request.user)
        try:
            order = Order.objects.get(pk=order_id, branch__in=accessible)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        order = services.resume_order(order=order, user=request.user)
        return Response({"id": str(order.id), "status": order.status})


class OrderPriorityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_id):
        from orders.models import Order
        from operations.constants import PERM_POS_ORDER_PRIORITY

        accessible = acl.get_accessible_branches(request.user)
        try:
            order = Order.objects.get(pk=order_id, branch__in=accessible)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = OrderPrioritySerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        priority = ser.validated_data["priority"]

        # URGENT requires special permission
        if priority == "URGENT" and not (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.has_perm_code("pos.order.priority.urgent")
        ):
            return Response(
                {"detail": "URGENT priority requires pos.order.priority.urgent permission."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.has_perm_code(PERM_POS_ORDER_PRIORITY)
        ):
            return Response(
                {"detail": "Permission denied."},
                status=status.HTTP_403_FORBIDDEN,
            )

        services.set_order_priority(order=order, priority=priority, user=request.user)
        return Response({"id": str(order.id), "priority": priority})


class OrderWaiterView(APIView):
    permission_classes = [IsAuthenticated, CanAssignWaiter]

    def post(self, request, order_id):
        from orders.models import Order
        from django.contrib.auth import get_user_model

        accessible = acl.get_accessible_branches(request.user)
        try:
            order = Order.objects.get(pk=order_id, branch__in=accessible)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = OrderWaiterSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        User = get_user_model()
        try:
            waiter = User.objects.get(pk=ser.validated_data["waiter_id"])
        except User.DoesNotExist:
            return Response({"detail": "Waiter not found."}, status=status.HTTP_404_NOT_FOUND)

        services.assign_waiter(order=order, waiter=waiter, user=request.user)
        return Response({"id": str(order.id), "assigned_waiter": waiter.email})


class OrderChangeRequestView(APIView):
    permission_classes = [IsAuthenticated, CanRequestOrderChange]

    def get(self, request, order_id):
        from orders.models import Order
        accessible = acl.get_accessible_branches(request.user)
        try:
            order = Order.objects.get(pk=order_id, branch__in=accessible)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        requests_qs = order.change_requests.all()
        return Response(OrderChangeRequestSerializer(requests_qs, many=True).data)

    def post(self, request, order_id):
        from orders.models import Order
        accessible = acl.get_accessible_branches(request.user)
        try:
            order = Order.objects.get(pk=order_id, branch__in=accessible)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = OrderChangeRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        change_request = services.create_order_change_request(
            order=order,
            requested_by=request.user,
            **ser.validated_data,
        )
        return Response(
            OrderChangeRequestSerializer(change_request).data,
            status=status.HTTP_201_CREATED,
        )


class OrderChangeRequestApproveView(APIView):
    permission_classes = [IsAuthenticated, CanApproveOrderChange]

    def post(self, request, change_request_id):
        change_requests = get_accessible_change_requests(request.user)
        try:
            change_request = change_requests.get(pk=change_request_id)
        except Exception:
            return Response({"detail": "Change request not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = OrderChangeRequestReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        change_request = services.approve_order_change_request(
            change_request=change_request,
            approver=request.user,
            review_note=ser.validated_data.get("review_note", ""),
        )
        return Response(OrderChangeRequestSerializer(change_request).data)


class OrderChangeRequestRejectView(APIView):
    permission_classes = [IsAuthenticated, CanApproveOrderChange]

    def post(self, request, change_request_id):
        change_requests = get_accessible_change_requests(request.user)
        try:
            change_request = change_requests.get(pk=change_request_id)
        except Exception:
            return Response({"detail": "Change request not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = OrderChangeRequestReviewSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        change_request = services.reject_order_change_request(
            change_request=change_request,
            reviewer=request.user,
            review_note=ser.validated_data.get("review_note", ""),
        )
        return Response(OrderChangeRequestSerializer(change_request).data)


# =============================================================================
# Modifier Views
# =============================================================================

class MenuItemModifiersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, menu_item_id):
        from menu.models import MenuItem
        from operations.selectors import get_modifier_groups_for_menu_item

        try:
            menu_item = MenuItem.objects.get(pk=menu_item_id, is_active=True)
        except MenuItem.DoesNotExist:
            return Response({"detail": "Menu item not found."}, status=status.HTTP_404_NOT_FOUND)

        groups = get_modifier_groups_for_menu_item(menu_item)
        return Response(MenuModifierGroupSerializer(groups, many=True).data)


class OrderItemModifierView(APIView):
    permission_classes = [IsAuthenticated, CanManageModifiers]

    def post(self, request, order_item_id):
        from orders.models import OrderItem
        accessible = acl.get_accessible_branches(request.user)
        try:
            order_item = OrderItem.objects.select_related("order").get(
                pk=order_item_id, order__branch__in=accessible
            )
        except OrderItem.DoesNotExist:
            return Response({"detail": "Order item not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = AddModifierSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        modifier = services.add_item_modifier(
            order_item=order_item,
            modifier_option_id=ser.validated_data.get("modifier_option_id"),
            name=ser.validated_data["name"],
            value=ser.validated_data["value"],
            user=request.user,
        )
        return Response(
            OrderItemModifierSerializer(modifier).data,
            status=status.HTTP_201_CREATED,
        )


class OrderItemModifierDeleteView(APIView):
    permission_classes = [IsAuthenticated, CanManageModifiers]

    def delete(self, request, modifier_id):
        from operations.models import OrderItemModifier
        accessible = acl.get_accessible_branches(request.user)
        try:
            modifier = OrderItemModifier.objects.select_related(
                "order_item__order"
            ).get(
                pk=modifier_id,
                order_item__order__branch__in=accessible,
            )
        except OrderItemModifier.DoesNotExist:
            return Response({"detail": "Modifier not found."}, status=status.HTTP_404_NOT_FOUND)

        services.remove_item_modifier(modifier=modifier, user=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Table Views
# =============================================================================

class TablesOperationalView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from operations.selectors import get_tables_with_status

        accessible_branches = acl.get_accessible_branches(request.user)
        branch_id = request.query_params.get("branch_id")
        if branch_id:
            branch = accessible_branches.filter(pk=branch_id).first()
        else:
            branch = accessible_branches.first()

        if not branch:
            return Response({"detail": "No accessible branch."}, status=status.HTTP_403_FORBIDDEN)

        tables = get_tables_with_status(branch)

        # Build enriched response
        result = []
        for table in tables:
            op_status = getattr(table, "operational_status", None)
            open_session = table.sessions.filter(status="OPEN").first()
            result.append({
                "id": str(table.id),
                "table_number": table.table_number,
                "name": table.name,
                "capacity": table.capacity,
                "section": table.section,
                "display_order": table.display_order,
                "status": table.status,
                "operational_status": op_status.status if op_status else "AVAILABLE",
                "has_open_session": open_session is not None,
                "guest_count": open_session.guest_count if open_session else 0,
            })
        return Response(result)


class TableStatusView(APIView):
    permission_classes = [IsAuthenticated, CanManageTables]

    def patch(self, request, table_id):
        from orders.models import DiningTable
        accessible = acl.get_accessible_branches(request.user)
        try:
            table = DiningTable.objects.get(pk=table_id, branch__in=accessible)
        except DiningTable.DoesNotExist:
            return Response({"detail": "Table not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = TableStatusUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        status_obj = services.set_table_operational_status(
            table=table,
            new_status=ser.validated_data["status"],
            user=request.user,
            notes=ser.validated_data.get("notes", ""),
        )
        return Response(TableOperationalStatusSerializer(status_obj).data)


class TableTransferView(APIView):
    permission_classes = [IsAuthenticated, CanTransferTable]

    def post(self, request, table_id):
        from orders.models import DiningTable, Order
        accessible = acl.get_accessible_branches(request.user)
        try:
            table = DiningTable.objects.get(pk=table_id, branch__in=accessible)
        except DiningTable.DoesNotExist:
            return Response({"detail": "Table not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = TableTransferRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        # Find the active order at this table
        order = Order.objects.filter(
            table=table,
            status__in=["DRAFT", "CONFIRMED"],
        ).first()
        if not order:
            return Response(
                {"detail": "No active order at this table."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dest = DiningTable.objects.get(
                pk=ser.validated_data["destination_table_id"],
                branch__in=accessible,
            )
        except DiningTable.DoesNotExist:
            return Response({"detail": "Destination table not found."}, status=status.HTTP_404_NOT_FOUND)

        transfer = services.request_table_transfer(
            order=order,
            destination_table=dest,
            requested_by=request.user,
            reason=ser.validated_data.get("reason", ""),
        )

        # Auto-complete if user has management permission
        if request.user.is_superuser or request.user.is_staff or request.user.has_perm_code("table.manage"):
            transfer = services.complete_table_transfer(
                transfer=transfer, approver=request.user
            )

        return Response(
            TableTransferSerializer(transfer).data,
            status=status.HTTP_201_CREATED,
        )


class TableMergeView(APIView):
    permission_classes = [IsAuthenticated, CanMergeTable]

    def post(self, request):
        from orders.models import DiningTable
        accessible = acl.get_accessible_branches(request.user)

        ser = TableMergeRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        branch = accessible.first()
        if not branch:
            return Response({"detail": "No accessible branch."}, status=status.HTTP_403_FORBIDDEN)

        source_tables = list(DiningTable.objects.filter(
            pk__in=ser.validated_data["source_table_ids"],
            branch__in=accessible,
        ))
        dest_table = DiningTable.objects.filter(
            pk=ser.validated_data["destination_table_id"],
            branch__in=accessible,
        ).first()

        if not dest_table:
            return Response(
                {"detail": "Destination table not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        merge = services.request_table_merge(
            source_tables=source_tables,
            destination_table=dest_table,
            requested_by=request.user,
            branch=branch,
            reason=ser.validated_data.get("reason", ""),
        )
        return Response(
            TableMergeSerializer(merge).data,
            status=status.HTTP_201_CREATED,
        )


class TableCloseView(APIView):
    permission_classes = [IsAuthenticated, CanManageTables]

    def post(self, request, table_id):
        from orders.models import DiningTable
        accessible = acl.get_accessible_branches(request.user)
        try:
            table = DiningTable.objects.get(pk=table_id, branch__in=accessible)
        except DiningTable.DoesNotExist:
            return Response({"detail": "Table not found."}, status=status.HTTP_404_NOT_FOUND)

        services.close_table(
            table=table, user=request.user, branch=table.branch
        )
        return Response({"detail": "Table closed successfully."})


# =============================================================================
# Order Merge
# =============================================================================

class OrderMergeView(APIView):
    permission_classes = [IsAuthenticated, CanMergeOrders]

    def post(self, request):
        from orders.models import Order
        accessible = acl.get_accessible_branches(request.user)

        ser = OrderMergeRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        source_orders = list(Order.objects.filter(
            pk__in=ser.validated_data["source_order_ids"],
            branch__in=accessible,
        ))
        dest_order = Order.objects.filter(
            pk=ser.validated_data["destination_order_id"],
            branch__in=accessible,
        ).first()

        if not dest_order:
            return Response(
                {"detail": "Destination order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        from operations.validators import validate_order_merge_compatibility
        validate_order_merge_compatibility(source_orders, dest_order)

        from operations.models import OrderMergeRequest
        from django.db import transaction
        from operations.constants import ORDER_MERGE_PENDING

        with transaction.atomic():
            merge_request = OrderMergeRequest.objects.create(
                destination_order=dest_order,
                requested_by=request.user,
                status=ORDER_MERGE_PENDING,
                reason=ser.validated_data.get("reason", ""),
            )
            merge_request.source_orders.set(source_orders)

        # Auto-approve if user has merge permission
        merge_request = services.merge_orders(
            merge_request=merge_request, approver=request.user
        )

        return Response(
            OrderMergeRequestSerializer(merge_request).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# Bill Split Views
# =============================================================================

class BillSplitListCreateView(APIView):
    permission_classes = [IsAuthenticated, CanSplitBill]

    def get(self, request, bill_id):
        from billing.models import Bill
        accessible = acl.get_accessible_branches(request.user)
        try:
            bill = Bill.objects.get(pk=bill_id, branch__in=accessible)
        except Bill.DoesNotExist:
            return Response({"detail": "Bill not found."}, status=status.HTTP_404_NOT_FOUND)

        splits = get_accessible_bill_splits(request.user).filter(bill=bill)
        return Response(BillSplitSerializer(splits, many=True).data)

    def post(self, request, bill_id):
        from billing.models import Bill
        accessible = acl.get_accessible_branches(request.user)
        try:
            bill = Bill.objects.get(pk=bill_id, branch__in=accessible)
        except Bill.DoesNotExist:
            return Response({"detail": "Bill not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = BillSplitCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        splits = services.create_bill_split(
            bill=bill,
            split_type=ser.validated_data["split_type"],
            requested_by=request.user,
            num_splits=ser.validated_data.get("num_splits", 2),
            item_allocations=ser.validated_data.get("item_allocations"),
        )
        return Response(
            BillSplitSerializer(splits, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class BillSplitFinalizeView(APIView):
    permission_classes = [IsAuthenticated, CanSplitBill]

    def post(self, request, bill_id, split_id):
        splits = get_accessible_bill_splits(request.user)
        try:
            split = splits.get(pk=split_id, bill_id=bill_id)
        except Exception:
            return Response({"detail": "Split not found."}, status=status.HTTP_404_NOT_FOUND)

        split = services.finalize_bill_split(bill_split=split, user=request.user)
        return Response(BillSplitSerializer(split).data)


# =============================================================================
# Receipt Print Views
# =============================================================================

class ReceiptPrintView(APIView):
    permission_classes = [IsAuthenticated, CanPrintReceipt]

    def post(self, request, bill_id):
        from billing.models import Bill
        from payments.models import Payment
        accessible = acl.get_accessible_branches(request.user)
        try:
            bill = Bill.objects.get(pk=bill_id, branch__in=accessible)
        except Bill.DoesNotExist:
            return Response({"detail": "Bill not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = PrintReceiptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        payment = None
        if ser.validated_data.get("payment_id"):
            try:
                payment = Payment.objects.get(
                    pk=ser.validated_data["payment_id"], bill=bill
                )
            except Payment.DoesNotExist:
                return Response(
                    {"detail": "Payment not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        log = services.log_receipt_print(
            bill=bill,
            payment=payment,
            printed_by=request.user,
            print_type=ser.validated_data.get("print_type", "ORIGINAL"),
            reason=ser.validated_data.get("reason", ""),
        )

        receipt_data = services.build_receipt_data(bill, payment)
        return Response({
            "print_log": ReceiptPrintLogSerializer(log).data,
            "receipt": receipt_data,
        })


class ReceiptReprintView(APIView):
    permission_classes = [IsAuthenticated, CanReprintReceipt]

    def post(self, request, bill_id):
        from billing.models import Bill
        accessible = acl.get_accessible_branches(request.user)
        try:
            bill = Bill.objects.get(pk=bill_id, branch__in=accessible)
        except Bill.DoesNotExist:
            return Response({"detail": "Bill not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = PrintReceiptSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        reason = ser.validated_data.get("reason", "")
        if not reason:
            return Response(
                {"detail": "A reason is required for reprinting."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        log = services.log_receipt_print(
            bill=bill,
            payment=None,
            printed_by=request.user,
            print_type="REPRINT",
            reason=reason,
        )
        receipt_data = services.build_receipt_data(bill)
        return Response({
            "print_log": ReceiptPrintLogSerializer(log).data,
            "receipt": receipt_data,
        })


# =============================================================================
# Shift Views
# =============================================================================

class ShiftListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shifts = get_accessible_shifts(request.user).select_related(
            "branch", "opened_by", "closed_by"
        ).order_by("-started_at")[:50]
        return Response(OperationalShiftSerializer(shifts, many=True).data)

    def post(self, request):
        if not (
            request.user.is_superuser
            or request.user.is_staff
            or request.user.has_perm_code("shift.create")
        ):
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)

        ser = OperationalShiftCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        accessible = acl.get_accessible_branches(request.user)
        branch = accessible.filter(pk=ser.validated_data["branch_id"]).first()
        if not branch:
            return Response(
                {"detail": "Branch not found or not accessible."},
                status=status.HTTP_404_NOT_FOUND,
            )

        shift = services.open_shift(
            branch=branch,
            shift_type=ser.validated_data["shift_type"],
            opened_by=request.user,
            notes=ser.validated_data.get("notes", ""),
        )
        return Response(
            OperationalShiftSerializer(shift).data,
            status=status.HTTP_201_CREATED,
        )


class ShiftCloseView(APIView):
    permission_classes = [IsAuthenticated, CanManageShifts]

    def post(self, request, shift_id):
        shifts = get_accessible_shifts(request.user)
        try:
            shift = shifts.get(pk=shift_id)
        except Exception:
            return Response({"detail": "Shift not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = ShiftCloseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        shift = services.close_shift(
            shift=shift,
            closed_by=request.user,
            actual_notes=ser.validated_data.get("notes", ""),
        )
        return Response(OperationalShiftSerializer(shift).data)


class ShiftHandoverView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, shift_id):
        shifts = get_accessible_shifts(request.user)
        try:
            shift = shifts.get(pk=shift_id)
        except Exception:
            return Response({"detail": "Shift not found."}, status=status.HTTP_404_NOT_FOUND)

        summary = services.get_shift_summary(shift)
        return Response(summary)

    def post(self, request, shift_id):
        shifts = get_accessible_shifts(request.user)
        try:
            shift = shifts.get(pk=shift_id)
        except Exception:
            return Response({"detail": "Shift not found."}, status=status.HTTP_404_NOT_FOUND)

        ser = ShiftHandoverNoteCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        note = services.add_handover_note(
            shift=shift,
            created_by=request.user,
            **ser.validated_data,
        )
        return Response(
            ShiftHandoverNoteSerializer(note).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# Operations Dashboard
# =============================================================================

class OperationsDashboardView(APIView):
    permission_classes = [IsAuthenticated, CanViewOperationsDashboard]

    def get(self, request):
        accessible = acl.get_accessible_branches(request.user)
        branch_id = request.query_params.get("branch_id")

        if branch_id:
            branch = accessible.filter(pk=branch_id).first()
        else:
            branch = accessible.first()

        if not branch:
            return Response(
                {"detail": "No accessible branch."},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = services.get_operations_dashboard_data(
            branch=branch, user=request.user
        )
        return Response(data)


class POSRecoveryView(APIView):
    """POS session recovery after browser refresh."""
    permission_classes = [IsAuthenticated, HasPOSAccess]

    def get(self, request):
        from counters.models import Counter
        counter_id = request.query_params.get("counter_id")
        if not counter_id:
            return Response(
                {"detail": "counter_id query param required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accessible = acl.get_accessible_branches(request.user)
        try:
            counter = Counter.objects.get(
                pk=counter_id, branch__in=accessible
            )
        except Counter.DoesNotExist:
            return Response(
                {"detail": "Counter not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = services.get_pos_recovery_data(
            user=request.user, counter=counter
        )
        return Response(data)
