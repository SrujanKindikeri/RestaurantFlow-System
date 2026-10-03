# =============================================================================
# RestaurantFlow — Inventory Views
# Phase 10
#
# Security:
#   - All querysets scoped via inventory.access — IDOR prevention.
#   - Every action validates permission codes (never role names).
#   - 404 returned for unauthorized UUIDs.
# =============================================================================

import logging

from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from inventory import access as inv_acl
from inventory import services
from inventory.models import (
    InventoryCategory, InventoryItem, StorageLocation,
    StockBalance, StockMovement, Supplier,
    PurchaseOrder, PurchaseReceipt,
    StockTransfer, StockWastage, StockAdjustment,
)
from inventory.permissions import HasPermission
from inventory.serializers import (
    InventoryCategorySerializer,
    CreateInventoryCategorySerializer,
    UpdateInventoryCategorySerializer,
    InventoryItemSerializer,
    CreateInventoryItemSerializer,
    UpdateInventoryItemSerializer,
    StorageLocationSerializer,
    CreateStorageLocationSerializer,
    UpdateStorageLocationSerializer,
    StockBalanceSerializer,
    StockMovementSerializer,
    SupplierSerializer,
    CreateSupplierSerializer,
    UpdateSupplierSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderDetailSerializer,
    CreatePurchaseOrderSerializer,
    ReceivePurchaseOrderSerializer,
    PurchaseReceiptSerializer,
    StockTransferListSerializer,
    StockTransferDetailSerializer,
    CreateStockTransferSerializer,
    StockWastageSerializer,
    CreateStockWastageSerializer,
    RejectWastageSerializer,
    StockAdjustmentSerializer,
    CreateStockAdjustmentSerializer,
    InventoryDashboardSerializer,
)

logger = logging.getLogger("inventory")


# =============================================================================
# Helpers
# =============================================================================

def _error(code, message, http_status=400):
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _service_error(exc, fallback_code="REQUEST_FAILED"):
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
        return Response({"error": True, "code": code, "message": message}, status=http_status)
    http_status = (
        status.HTTP_403_FORBIDDEN
        if isinstance(exc, DRFPermDenied)
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"error": True, "code": fallback_code, "message": str(exc)}, status=http_status)


def _get_or_404(queryset, pk, label):
    try:
        return queryset.get(pk=pk)
    except Exception:
        raise NotFound(f"{label} {pk} not found.")


# =============================================================================
# Dashboard
# =============================================================================

class InventoryDashboardView(APIView):
    """GET /api/inventory/dashboard/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request):
        data = services.get_inventory_dashboard(request.user)
        return Response(InventoryDashboardSerializer(data).data)


# =============================================================================
# Categories
# =============================================================================

class InventoryCategoryListView(APIView):
    """GET /api/inventory/categories/  POST /api/inventory/categories/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("inventory.create")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request):
        qs = inv_acl.get_accessible_categories(request.user).select_related("restaurant")
        if request.query_params.get("restaurant"):
            qs = qs.filter(restaurant_id=request.query_params["restaurant"])
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=(is_active.lower() == "true"))
        return Response(InventoryCategorySerializer(qs, many=True).data)

    def post(self, request):
        from organizations.models import Restaurant
        serializer = CreateInventoryCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            restaurant = Restaurant.objects.get(pk=d["restaurant_id"])
        except Restaurant.DoesNotExist:
            return _error("NOT_FOUND", "Restaurant not found.", 404)
        if not acl.can_access_restaurant(request.user, restaurant):
            return _error("FORBIDDEN", "You do not have access to this restaurant.", 403)

        cat = InventoryCategory.objects.create(
            restaurant=restaurant,
            name=d["name"],
            description=d.get("description", ""),
        )
        logger.info("InventoryCategory created: name=%s by user=%s", cat.name, request.user.email)
        return Response(InventoryCategorySerializer(cat).data, status=201)


class InventoryCategoryDetailView(APIView):
    """GET /api/inventory/categories/{id}/  PATCH /api/inventory/categories/{id}/"""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("inventory.update")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def _get(self, request, pk):
        return _get_or_404(inv_acl.get_accessible_categories(request.user), pk, "InventoryCategory")

    def get(self, request, pk):
        return Response(InventoryCategorySerializer(self._get(request, pk)).data)

    def patch(self, request, pk):
        cat = self._get(request, pk)
        serializer = UpdateInventoryCategorySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data
        for field in ["name", "description", "is_active"]:
            if field in d:
                setattr(cat, field, d[field])
        cat.save()
        return Response(InventoryCategorySerializer(cat).data)


# =============================================================================
# Inventory Items
# =============================================================================

class InventoryItemListView(APIView):
    """GET /api/inventory/items/  POST /api/inventory/items/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("inventory.create")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request):
        from django.db.models import Q
        qs = inv_acl.get_accessible_inventory_items(request.user).select_related("restaurant", "category")
        params = request.query_params
        if params.get("category"):
            qs = qs.filter(category_id=params["category"])
        if params.get("restaurant"):
            qs = qs.filter(restaurant_id=params["restaurant"])
        if params.get("is_active") is not None:
            qs = qs.filter(is_active=(params["is_active"].lower() == "true"))
        if params.get("search"):
            qs = qs.filter(Q(name__icontains=params["search"]) | Q(sku__icontains=params["search"]))
        return Response(InventoryItemSerializer(qs, many=True).data)

    def post(self, request):
        from organizations.models import Restaurant
        serializer = CreateInventoryItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            restaurant = Restaurant.objects.get(pk=d["restaurant_id"])
        except Restaurant.DoesNotExist:
            return _error("NOT_FOUND", "Restaurant not found.", 404)
        if not acl.can_access_restaurant(request.user, restaurant):
            return _error("FORBIDDEN", "You do not have access to this restaurant.", 403)

        category = None
        if d.get("category_id"):
            try:
                category = InventoryCategory.objects.get(pk=d["category_id"], restaurant=restaurant)
            except InventoryCategory.DoesNotExist:
                return _error("NOT_FOUND", "Category not found.", 404)

        if InventoryItem.objects.filter(restaurant=restaurant, sku=d["sku"]).exists():
            return _error("DUPLICATE_SKU", f"SKU '{d['sku']}' already exists for this restaurant.")

        item = InventoryItem.objects.create(
            restaurant=restaurant, category=category,
            name=d["name"], sku=d["sku"],
            description=d.get("description", ""),
            default_unit=d["default_unit"],
            minimum_stock=d.get("minimum_stock", "0.000"),
            reorder_level=d.get("reorder_level", "0.000"),
            maximum_stock=d.get("maximum_stock", "0.000"),
        )
        logger.info("InventoryItem created: sku=%s by user=%s", item.sku, request.user.email)
        return Response(InventoryItemSerializer(item).data, status=201)


class InventoryItemDetailView(APIView):
    """GET /api/inventory/items/{id}/  PATCH /api/inventory/items/{id}/"""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("inventory.update")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def _get(self, request, pk):
        return _get_or_404(
            inv_acl.get_accessible_inventory_items(request.user).select_related("restaurant", "category"),
            pk, "InventoryItem"
        )

    def get(self, request, pk):
        return Response(InventoryItemSerializer(self._get(request, pk)).data)

    def patch(self, request, pk):
        item = self._get(request, pk)
        serializer = UpdateInventoryItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data
        for field in ["name", "description", "default_unit", "minimum_stock", "reorder_level", "maximum_stock", "is_active"]:
            if field in d:
                setattr(item, field, d[field])
        if "category_id" in d:
            if d["category_id"]:
                try:
                    item.category = InventoryCategory.objects.get(pk=d["category_id"], restaurant=item.restaurant)
                except InventoryCategory.DoesNotExist:
                    return _error("NOT_FOUND", "Category not found.", 404)
            else:
                item.category = None
        item.save()
        return Response(InventoryItemSerializer(item).data)


# =============================================================================
# Storage Locations
# =============================================================================

class StorageLocationListView(APIView):
    """GET /api/inventory/locations/  POST /api/inventory/locations/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("inventory.create")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request):
        qs = inv_acl.get_accessible_locations(request.user).select_related("branch", "branch__restaurant")
        if request.query_params.get("branch"):
            qs = qs.filter(branch_id=request.query_params["branch"])
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=(is_active.lower() == "true"))
        return Response(StorageLocationSerializer(qs, many=True).data)

    def post(self, request):
        from organizations.models import Branch
        serializer = CreateStorageLocationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            branch = Branch.objects.get(pk=d["branch_id"])
        except Branch.DoesNotExist:
            return _error("NOT_FOUND", "Branch not found.", 404)
        if not acl.can_access_branch(request.user, branch):
            return _error("FORBIDDEN", "You do not have access to this branch.", 403)

        if StorageLocation.objects.filter(branch=branch, code=d["code"]).exists():
            return _error("DUPLICATE_CODE", f"Location code '{d['code']}' already exists for this branch.")

        loc = StorageLocation.objects.create(
            branch=branch, name=d["name"], code=d["code"],
            location_type=d["location_type"], description=d.get("description", ""),
        )
        logger.info("StorageLocation created: code=%s by user=%s", loc.code, request.user.email)
        return Response(StorageLocationSerializer(loc).data, status=201)


class StorageLocationDetailView(APIView):
    """GET /api/inventory/locations/{id}/  PATCH /api/inventory/locations/{id}/"""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("inventory.update")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def _get(self, request, pk):
        return _get_or_404(
            inv_acl.get_accessible_locations(request.user).select_related("branch", "branch__restaurant"),
            pk, "StorageLocation"
        )

    def get(self, request, pk):
        return Response(StorageLocationSerializer(self._get(request, pk)).data)

    def patch(self, request, pk):
        loc = self._get(request, pk)
        serializer = UpdateStorageLocationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data
        for field in ["name", "code", "location_type", "description", "is_active"]:
            if field in d:
                setattr(loc, field, d[field])
        loc.save()
        return Response(StorageLocationSerializer(loc).data)


# =============================================================================
# Stock Balance
# =============================================================================

class StockBalanceListView(generics.ListAPIView):
    """GET /api/inventory/stock/"""
    serializer_class = StockBalanceSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get_queryset(self):
        qs = inv_acl.get_accessible_stock_balances(self.request.user).select_related(
            "inventory_item", "inventory_item__category",
            "storage_location", "storage_location__branch",
        )
        params = self.request.query_params
        if params.get("location"):
            qs = qs.filter(storage_location_id=params["location"])
        if params.get("item"):
            qs = qs.filter(inventory_item_id=params["item"])
        if params.get("category"):
            qs = qs.filter(inventory_item__category_id=params["category"])
        if params.get("branch"):
            qs = qs.filter(storage_location__branch_id=params["branch"])
        if params.get("status"):
            target = params["status"].upper()
            matching_pks = [b.pk for b in qs if b.get_stock_status() == target]
            qs = qs.filter(pk__in=matching_pks)
        return qs


class StockBalanceByItemView(generics.ListAPIView):
    """GET /api/inventory/stock/{item_id}/"""
    serializer_class = StockBalanceSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get_queryset(self):
        item_id = self.kwargs["item_id"]
        _get_or_404(inv_acl.get_accessible_inventory_items(self.request.user), item_id, "InventoryItem")
        return inv_acl.get_accessible_stock_balances(self.request.user).filter(
            inventory_item_id=item_id
        ).select_related("inventory_item", "storage_location", "storage_location__branch")


# =============================================================================
# Stock Movements
# =============================================================================

class StockMovementListView(generics.ListAPIView):
    """GET /api/inventory/movements/"""
    serializer_class = StockMovementSerializer

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("stock.movement.view")()]

    def get_queryset(self):
        qs = inv_acl.get_accessible_movements(self.request.user).select_related(
            "inventory_item", "storage_location", "storage_location__branch", "performed_by"
        )
        params = self.request.query_params
        if params.get("item"):
            qs = qs.filter(inventory_item_id=params["item"])
        if params.get("location"):
            qs = qs.filter(storage_location_id=params["location"])
        if params.get("movement_type"):
            qs = qs.filter(movement_type=params["movement_type"])
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        if params.get("performed_by"):
            qs = qs.filter(performed_by__email__icontains=params["performed_by"])
        return qs.order_by("-created_at")


# =============================================================================
# Suppliers
# =============================================================================

class SupplierListView(APIView):
    """GET /api/inventory/suppliers/  POST /api/inventory/suppliers/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("supplier.create")()]
        return [IsAuthenticated(), HasPermission("supplier.view")()]

    def get(self, request):
        qs = inv_acl.get_accessible_suppliers(request.user).select_related("restaurant")
        if request.query_params.get("restaurant"):
            qs = qs.filter(restaurant_id=request.query_params["restaurant"])
        is_active = request.query_params.get("is_active")
        if is_active is not None:
            qs = qs.filter(is_active=(is_active.lower() == "true"))
        return Response(SupplierSerializer(qs, many=True).data)

    def post(self, request):
        from organizations.models import Restaurant
        serializer = CreateSupplierSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            restaurant = Restaurant.objects.get(pk=d["restaurant_id"])
        except Restaurant.DoesNotExist:
            return _error("NOT_FOUND", "Restaurant not found.", 404)
        if not acl.can_access_restaurant(request.user, restaurant):
            return _error("FORBIDDEN", "You do not have access to this restaurant.", 403)
        if Supplier.objects.filter(restaurant=restaurant, code=d["code"]).exists():
            return _error("DUPLICATE_CODE", f"Supplier code '{d['code']}' already exists.")

        supplier = Supplier.objects.create(
            restaurant=restaurant, name=d["name"], code=d["code"],
            contact_person=d.get("contact_person", ""),
            phone=d.get("phone", ""), email=d.get("email", ""),
            address=d.get("address", ""), tax_identifier=d.get("tax_identifier", ""),
            notes=d.get("notes", ""),
        )
        logger.info("Supplier created: code=%s by user=%s", supplier.code, request.user.email)
        return Response(SupplierSerializer(supplier).data, status=201)


class SupplierDetailView(APIView):
    """GET /api/inventory/suppliers/{id}/  PATCH /api/inventory/suppliers/{id}/"""

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("supplier.update")()]
        return [IsAuthenticated(), HasPermission("supplier.view")()]

    def _get(self, request, pk):
        return _get_or_404(inv_acl.get_accessible_suppliers(request.user).select_related("restaurant"), pk, "Supplier")

    def get(self, request, pk):
        return Response(SupplierSerializer(self._get(request, pk)).data)

    def patch(self, request, pk):
        supplier = self._get(request, pk)
        serializer = UpdateSupplierSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data
        for field in ["name", "code", "contact_person", "phone", "email", "address", "tax_identifier", "notes", "is_active"]:
            if field in d:
                setattr(supplier, field, d[field])
        supplier.save()
        return Response(SupplierSerializer(supplier).data)


# =============================================================================
# Purchase Orders
# =============================================================================

class PurchaseOrderListView(APIView):
    """GET /api/inventory/purchases/  POST /api/inventory/purchases/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("purchase.create")()]
        return [IsAuthenticated(), HasPermission("purchase.view")()]

    def get(self, request):
        qs = inv_acl.get_accessible_purchase_orders(request.user).select_related(
            "supplier", "branch", "restaurant", "created_by"
        )
        params = request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("supplier"):
            qs = qs.filter(supplier_id=params["supplier"])
        if params.get("branch"):
            qs = qs.filter(branch_id=params["branch"])
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        return Response(PurchaseOrderListSerializer(qs.order_by("-created_at"), many=True).data)

    def post(self, request):
        from organizations.models import Restaurant, Branch
        serializer = CreatePurchaseOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            restaurant = Restaurant.objects.get(pk=d["restaurant_id"])
            branch = Branch.objects.get(pk=d["branch_id"])
            supplier = Supplier.objects.get(pk=d["supplier_id"])
        except Exception as e:
            return _error("NOT_FOUND", f"Resource not found: {e}", 404)

        try:
            po = services.create_purchase_order(
                restaurant=restaurant, branch=branch, supplier=supplier,
                items=d["items"], user=request.user,
                order_date=d.get("order_date"),
                expected_date=d.get("expected_date"),
                discount_amount=d.get("discount_amount", "0.00"),
                notes=d.get("notes", ""),
            )
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "PO_CREATE_FAILED")
        return Response(PurchaseOrderDetailSerializer(po).data, status=201)


class PurchaseOrderDetailView(APIView):
    """GET /api/inventory/purchases/{id}/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("purchase.view")()]

    def get(self, request, pk):
        po = _get_or_404(
            inv_acl.get_accessible_purchase_orders(request.user).select_related(
                "supplier", "branch", "restaurant", "created_by", "approved_by", "received_by"
            ).prefetch_related("items__inventory_item"),
            pk, "PurchaseOrder"
        )
        return Response(PurchaseOrderDetailSerializer(po).data)


class PurchaseOrderSubmitView(APIView):
    """POST /api/inventory/purchases/{id}/submit/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("purchase.submit")()]

    def post(self, request, pk):
        po = _get_or_404(inv_acl.get_accessible_purchase_orders(request.user), pk, "PurchaseOrder")
        try:
            po = services.submit_purchase_order(po, request.user)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "PO_SUBMIT_FAILED")
        return Response(PurchaseOrderDetailSerializer(po).data)


class PurchaseOrderApproveView(APIView):
    """POST /api/inventory/purchases/{id}/approve/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("purchase.approve")()]

    def post(self, request, pk):
        po = _get_or_404(inv_acl.get_accessible_purchase_orders(request.user), pk, "PurchaseOrder")
        try:
            po = services.approve_purchase_order(po, request.user)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "PO_APPROVE_FAILED")
        return Response(PurchaseOrderDetailSerializer(po).data)


class PurchaseOrderReceiveView(APIView):
    """POST /api/inventory/purchases/{id}/receive/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("purchase.receive")()]

    def post(self, request, pk):
        po = _get_or_404(inv_acl.get_accessible_purchase_orders(request.user), pk, "PurchaseOrder")
        serializer = ReceivePurchaseOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            location = StorageLocation.objects.get(pk=d["storage_location_id"])
        except StorageLocation.DoesNotExist:
            return _error("NOT_FOUND", "Storage location not found.", 404)

        try:
            receipt = services.receive_purchase_order(
                po=po, user=request.user,
                storage_location=location,
                receipt_items=d["items"],
                notes=d.get("notes", ""),
            )
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "RECEIVE_FAILED")

        full_receipt = PurchaseReceipt.objects.prefetch_related(
            "items__purchase_order_item__inventory_item"
        ).get(pk=receipt.pk)
        return Response(PurchaseReceiptSerializer(full_receipt).data, status=201)


class PurchaseOrderCancelView(APIView):
    """POST /api/inventory/purchases/{id}/cancel/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("purchase.cancel")()]

    def post(self, request, pk):
        po = _get_or_404(inv_acl.get_accessible_purchase_orders(request.user), pk, "PurchaseOrder")
        try:
            po = services.cancel_purchase_order(po, request.user, reason=request.data.get("reason", ""))
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "PO_CANCEL_FAILED")
        return Response(PurchaseOrderDetailSerializer(po).data)


# =============================================================================
# Stock Transfers
# =============================================================================

class StockTransferListView(APIView):
    """GET /api/inventory/transfers/  POST /api/inventory/transfers/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("inventory.transfer")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request):
        qs = inv_acl.get_accessible_transfers(request.user).select_related(
            "restaurant", "source_location", "destination_location", "requested_by"
        )
        if request.query_params.get("status"):
            qs = qs.filter(status=request.query_params["status"])
        return Response(StockTransferListSerializer(qs.order_by("-created_at"), many=True).data)

    def post(self, request):
        from organizations.models import Restaurant
        serializer = CreateStockTransferSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            restaurant = Restaurant.objects.get(pk=d["restaurant_id"])
            src = StorageLocation.objects.get(pk=d["source_location_id"])
            dst = StorageLocation.objects.get(pk=d["destination_location_id"])
        except Exception as e:
            return _error("NOT_FOUND", f"Resource not found: {e}", 404)

        try:
            transfer = services.create_stock_transfer(
                restaurant=restaurant, source_location=src,
                destination_location=dst, items=d["items"],
                user=request.user, notes=d.get("notes", ""),
            )
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "TRANSFER_CREATE_FAILED")

        full = StockTransfer.objects.prefetch_related("items__inventory_item").get(pk=transfer.pk)
        return Response(StockTransferDetailSerializer(full).data, status=201)


class StockTransferDetailView(APIView):
    """GET /api/inventory/transfers/{id}/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request, pk):
        transfer = _get_or_404(
            inv_acl.get_accessible_transfers(request.user).select_related(
                "restaurant", "source_location", "destination_location",
                "requested_by", "approved_by", "completed_by"
            ).prefetch_related("items__inventory_item"),
            pk, "StockTransfer"
        )
        return Response(StockTransferDetailSerializer(transfer).data)


class StockTransferRequestView(APIView):
    """POST /api/inventory/transfers/{id}/request/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.transfer")()]

    def post(self, request, pk):
        transfer = _get_or_404(inv_acl.get_accessible_transfers(request.user), pk, "StockTransfer")
        try:
            transfer = services.request_stock_transfer(transfer, request.user)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "TRANSFER_REQUEST_FAILED")
        return Response(StockTransferDetailSerializer(transfer).data)


class StockTransferApproveView(APIView):
    """POST /api/inventory/transfers/{id}/approve/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.transfer.approve")()]

    def post(self, request, pk):
        transfer = _get_or_404(inv_acl.get_accessible_transfers(request.user), pk, "StockTransfer")
        try:
            transfer = services.approve_stock_transfer(transfer, request.user)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "TRANSFER_APPROVE_FAILED")
        return Response(StockTransferDetailSerializer(transfer).data)


class StockTransferCompleteView(APIView):
    """POST /api/inventory/transfers/{id}/complete/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.transfer.approve")()]

    def post(self, request, pk):
        transfer = _get_or_404(inv_acl.get_accessible_transfers(request.user), pk, "StockTransfer")
        try:
            transfer = services.complete_stock_transfer(transfer, request.user)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "TRANSFER_COMPLETE_FAILED")
        return Response(StockTransferDetailSerializer(transfer).data)


class StockTransferCancelView(APIView):
    """POST /api/inventory/transfers/{id}/cancel/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.transfer")()]

    def post(self, request, pk):
        transfer = _get_or_404(inv_acl.get_accessible_transfers(request.user), pk, "StockTransfer")
        try:
            transfer = services.cancel_stock_transfer(transfer, request.user)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "TRANSFER_CANCEL_FAILED")
        return Response(StockTransferDetailSerializer(transfer).data)


# =============================================================================
# Wastage
# =============================================================================

class StockWastageListView(APIView):
    """GET /api/inventory/wastage/  POST /api/inventory/wastage/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("inventory.wastage.create")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request):
        qs = inv_acl.get_accessible_wastages(request.user).select_related(
            "inventory_item", "storage_location", "storage_location__branch",
            "recorded_by", "approved_by"
        )
        params = request.query_params
        if params.get("status"):
            qs = qs.filter(status=params["status"])
        if params.get("item"):
            qs = qs.filter(inventory_item_id=params["item"])
        if params.get("location"):
            qs = qs.filter(storage_location_id=params["location"])
        return Response(StockWastageSerializer(qs.order_by("-created_at"), many=True).data)

    def post(self, request):
        serializer = CreateStockWastageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            inv_item = InventoryItem.objects.get(pk=d["inventory_item_id"])
            location = StorageLocation.objects.get(pk=d["storage_location_id"])
        except Exception as e:
            return _error("NOT_FOUND", f"Resource not found: {e}", 404)

        try:
            wastage = services.create_wastage(
                inventory_item=inv_item, storage_location=location,
                quantity=d["quantity"], unit=d["unit"],
                wastage_type=d["wastage_type"], reason=d["reason"],
                user=request.user,
            )
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "WASTAGE_CREATE_FAILED")
        return Response(StockWastageSerializer(wastage).data, status=201)


class StockWastageDetailView(APIView):
    """GET /api/inventory/wastage/{id}/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request, pk):
        wastage = _get_or_404(
            inv_acl.get_accessible_wastages(request.user).select_related(
                "inventory_item", "storage_location", "recorded_by", "approved_by"
            ),
            pk, "StockWastage"
        )
        return Response(StockWastageSerializer(wastage).data)


class StockWastageApproveView(APIView):
    """POST /api/inventory/wastage/{id}/approve/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.wastage.approve")()]

    def post(self, request, pk):
        wastage = _get_or_404(inv_acl.get_accessible_wastages(request.user), pk, "StockWastage")
        try:
            wastage = services.approve_wastage(wastage, request.user)
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "WASTAGE_APPROVE_FAILED")
        return Response(StockWastageSerializer(wastage).data)


class StockWastageRejectView(APIView):
    """POST /api/inventory/wastage/{id}/reject/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.wastage.approve")()]

    def post(self, request, pk):
        wastage = _get_or_404(inv_acl.get_accessible_wastages(request.user), pk, "StockWastage")
        serializer = RejectWastageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        try:
            wastage = services.reject_wastage(
                wastage, request.user,
                rejection_reason=serializer.validated_data["rejection_reason"]
            )
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "WASTAGE_REJECT_FAILED")
        return Response(StockWastageSerializer(wastage).data)


# =============================================================================
# Stock Adjustments
# =============================================================================

class StockAdjustmentListView(APIView):
    """GET /api/inventory/adjustments/  POST /api/inventory/adjustments/"""

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("inventory.adjust")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request):
        qs = inv_acl.get_accessible_adjustments(request.user).select_related(
            "inventory_item", "storage_location", "adjusted_by"
        )
        params = request.query_params
        if params.get("item"):
            qs = qs.filter(inventory_item_id=params["item"])
        if params.get("location"):
            qs = qs.filter(storage_location_id=params["location"])
        if params.get("date_from"):
            qs = qs.filter(created_at__date__gte=params["date_from"])
        if params.get("date_to"):
            qs = qs.filter(created_at__date__lte=params["date_to"])
        return Response(StockAdjustmentSerializer(qs.order_by("-created_at"), many=True).data)

    def post(self, request):
        serializer = CreateStockAdjustmentSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            inv_item = InventoryItem.objects.get(pk=d["inventory_item_id"])
            location = StorageLocation.objects.get(pk=d["storage_location_id"])
        except Exception as e:
            return _error("NOT_FOUND", f"Resource not found: {e}", 404)

        try:
            adjustment = services.create_stock_adjustment(
                inventory_item=inv_item, storage_location=location,
                physical_quantity=d["quantity_physical"],
                unit=d["unit"], reason=d["reason"],
                user=request.user,
            )
        except Exception as exc:
            from rest_framework.exceptions import PermissionDenied
            if isinstance(exc, PermissionDenied):
                raise
            return _service_error(exc, "ADJUSTMENT_FAILED")
        return Response(StockAdjustmentSerializer(adjustment).data, status=201)
