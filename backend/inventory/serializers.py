# =============================================================================
# RestaurantFlow — Inventory Serializers
# Phase 10
#
# Two-serializer pattern (mirrors billing/serializers.py):
#   READ  serializers — ModelSerializer, all fields read_only, denormalized.
#   WRITE serializers — plain Serializer, validate input only.
#
# Security:
#   - Never accept computed quantities/costs from the client.
#   - The backend is the authoritative source for all totals.
#   - IDs are validated server-side in services — serializers are shapes only.
# =============================================================================

import logging
from decimal import Decimal

from rest_framework import serializers

from inventory.models import (
    InventoryCategory,
    InventoryItem,
    StorageLocation,
    StockBalance,
    StockMovement,
    Supplier,
    PurchaseOrder,
    PurchaseOrderItem,
    PurchaseReceipt,
    PurchaseReceiptItem,
    StockTransfer,
    StockTransferItem,
    StockWastage,
    StockAdjustment,
)
from inventory.constants import (
    UNIT_CHOICES,
    WASTAGE_TYPE_CHOICES,
    LOCATION_TYPE_CHOICES,
)

logger = logging.getLogger("inventory")


# =============================================================================
# InventoryCategory — Read
# =============================================================================

class InventoryCategorySerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = InventoryCategory
        fields = [
            "id", "restaurant", "restaurant_name",
            "name", "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


# =============================================================================
# InventoryCategory — Write
# =============================================================================

class CreateInventoryCategorySerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Name cannot be blank.")
        return value.strip()


class UpdateInventoryCategorySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


# =============================================================================
# InventoryItem — Read
# =============================================================================

class InventoryItemSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    category_name = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = [
            "id", "restaurant", "restaurant_name",
            "category", "category_name",
            "name", "sku", "description",
            "default_unit", "minimum_stock", "reorder_level",
            "maximum_stock", "average_cost", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_category_name(self, obj):
        return obj.category.name if obj.category_id else None


# =============================================================================
# InventoryItem — Write
# =============================================================================

class CreateInventoryItemSerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    category_id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(max_length=150)
    sku = serializers.CharField(max_length=50)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    default_unit = serializers.ChoiceField(choices=UNIT_CHOICES)
    minimum_stock = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0"), required=False, default="0.000"
    )
    reorder_level = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0"), required=False, default="0.000"
    )
    maximum_stock = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0"), required=False, default="0.000"
    )


class UpdateInventoryItemSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    default_unit = serializers.ChoiceField(choices=UNIT_CHOICES, required=False)
    minimum_stock = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0"), required=False)
    reorder_level = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0"), required=False)
    maximum_stock = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0"), required=False)
    is_active = serializers.BooleanField(required=False)


# =============================================================================
# StorageLocation — Read
# =============================================================================

class StorageLocationSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    restaurant_name = serializers.CharField(source="branch.restaurant.name", read_only=True)

    class Meta:
        model = StorageLocation
        fields = [
            "id", "branch", "branch_name", "restaurant_name",
            "name", "code", "location_type", "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


# =============================================================================
# StorageLocation — Write
# =============================================================================

class CreateStorageLocationSerializer(serializers.Serializer):
    branch_id = serializers.UUIDField()
    name = serializers.CharField(max_length=100)
    code = serializers.CharField(max_length=20)
    location_type = serializers.ChoiceField(choices=LOCATION_TYPE_CHOICES)
    description = serializers.CharField(required=False, allow_blank=True, default="")


class UpdateStorageLocationSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100, required=False)
    code = serializers.CharField(max_length=20, required=False)
    location_type = serializers.ChoiceField(choices=LOCATION_TYPE_CHOICES, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


# =============================================================================
# StockBalance — Read
# =============================================================================

class StockBalanceSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    item_sku = serializers.CharField(source="inventory_item.sku", read_only=True)
    item_unit = serializers.CharField(source="inventory_item.default_unit", read_only=True)
    category_name = serializers.SerializerMethodField()
    location_name = serializers.CharField(source="storage_location.name", read_only=True)
    location_code = serializers.CharField(source="storage_location.code", read_only=True)
    branch_name = serializers.CharField(source="storage_location.branch.name", read_only=True)
    available_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)
    reorder_level = serializers.DecimalField(
        source="inventory_item.reorder_level", max_digits=14, decimal_places=3, read_only=True
    )
    stock_status = serializers.SerializerMethodField()

    class Meta:
        model = StockBalance
        fields = [
            "id", "inventory_item", "item_name", "item_sku", "item_unit",
            "category_name", "storage_location", "location_name",
            "location_code", "branch_name",
            "quantity", "reserved_quantity", "available_quantity",
            "average_cost", "reorder_level", "stock_status",
            "last_movement_at", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_category_name(self, obj):
        if obj.inventory_item.category_id:
            return obj.inventory_item.category.name
        return None

    def get_stock_status(self, obj):
        return obj.get_stock_status()


# =============================================================================
# StockMovement — Read
# =============================================================================

class StockMovementSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    item_sku = serializers.CharField(source="inventory_item.sku", read_only=True)
    item_unit = serializers.CharField(source="inventory_item.default_unit", read_only=True)
    location_name = serializers.CharField(source="storage_location.name", read_only=True)
    branch_name = serializers.CharField(source="storage_location.branch.name", read_only=True)
    performed_by_email = serializers.SerializerMethodField()
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = [
            "id", "inventory_item", "item_name", "item_sku", "item_unit",
            "storage_location", "location_name", "branch_name",
            "movement_type", "quantity", "unit_cost", "total_cost",
            "reference_type", "reference_id",
            "reason", "performed_by", "performed_by_email", "performed_by_name",
            "created_at",
        ]
        read_only_fields = fields

    def get_performed_by_email(self, obj):
        return obj.performed_by.email if obj.performed_by_id else None

    def get_performed_by_name(self, obj):
        if obj.performed_by_id:
            return obj.performed_by.full_name or obj.performed_by.email
        return None


# =============================================================================
# Supplier — Read
# =============================================================================

class SupplierSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = Supplier
        fields = [
            "id", "restaurant", "restaurant_name",
            "name", "code", "contact_person", "phone", "email",
            "address", "tax_identifier", "notes", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


# =============================================================================
# Supplier — Write
# =============================================================================

class CreateSupplierSerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    name = serializers.CharField(max_length=150)
    code = serializers.CharField(max_length=30)
    contact_person = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True, default="")
    email = serializers.EmailField(required=False, allow_blank=True, default="")
    address = serializers.CharField(required=False, allow_blank=True, default="")
    tax_identifier = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class UpdateSupplierSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    code = serializers.CharField(max_length=30, required=False)
    contact_person = serializers.CharField(max_length=100, required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    tax_identifier = serializers.CharField(max_length=50, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)


# =============================================================================
# PurchaseOrderItem — Read
# =============================================================================

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    item_sku = serializers.CharField(source="inventory_item.sku", read_only=True)
    remaining_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = PurchaseOrderItem
        fields = [
            "id", "inventory_item", "item_name", "item_sku",
            "quantity", "unit", "unit_cost", "tax_rate",
            "discount_amount", "total_amount",
            "received_quantity", "remaining_quantity",
            "notes", "created_at",
        ]
        read_only_fields = fields


# =============================================================================
# PurchaseOrder — Read (list)
# =============================================================================

class PurchaseOrderListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    created_by_email = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id", "purchase_number", "restaurant", "restaurant_name",
            "branch", "branch_name", "supplier", "supplier_name",
            "status", "order_date", "expected_date",
            "subtotal", "tax_amount", "discount_amount", "total_amount",
            "created_by", "created_by_email",
            "approved_at", "received_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by_id else None


# =============================================================================
# PurchaseOrder — Read (detail)
# =============================================================================

class PurchaseOrderDetailSerializer(PurchaseOrderListSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)
    approved_by_email = serializers.SerializerMethodField()
    received_by_email = serializers.SerializerMethodField()

    class Meta(PurchaseOrderListSerializer.Meta):
        fields = PurchaseOrderListSerializer.Meta.fields + [
            "notes", "approved_by", "approved_by_email",
            "received_by", "received_by_email", "items",
        ]
        read_only_fields = fields

    def get_approved_by_email(self, obj):
        return obj.approved_by.email if obj.approved_by_id else None

    def get_received_by_email(self, obj):
        return obj.received_by.email if obj.received_by_id else None


# =============================================================================
# PurchaseOrder — Write: Create
# =============================================================================

class PurchaseOrderItemCreateSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.ChoiceField(choices=UNIT_CHOICES)
    unit_cost = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"))
    tax_rate = serializers.DecimalField(max_digits=6, decimal_places=3, min_value=Decimal("0"), required=False, default="0.000")
    discount_amount = serializers.DecimalField(max_digits=14, decimal_places=2, min_value=Decimal("0"), required=False, default="0.00")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CreatePurchaseOrderSerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    branch_id = serializers.UUIDField()
    supplier_id = serializers.UUIDField()
    order_date = serializers.DateField(required=False, allow_null=True)
    expected_date = serializers.DateField(required=False, allow_null=True)
    discount_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0"), required=False, default="0.00"
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = PurchaseOrderItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value


# =============================================================================
# Purchase Receiving — Write
# =============================================================================

class ReceiveItemSerializer(serializers.Serializer):
    purchase_order_item_id = serializers.UUIDField()
    quantity_received = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0.001")
    )


class ReceivePurchaseOrderSerializer(serializers.Serializer):
    storage_location_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = ReceiveItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item must be specified for receiving.")
        return value


# =============================================================================
# PurchaseReceipt — Read
# =============================================================================

class PurchaseReceiptItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="purchase_order_item.inventory_item.name", read_only=True)

    class Meta:
        model = PurchaseReceiptItem
        fields = ["id", "purchase_order_item", "item_name", "quantity_received", "unit_cost"]
        read_only_fields = fields


class PurchaseReceiptSerializer(serializers.ModelSerializer):
    purchase_number = serializers.CharField(source="purchase_order.purchase_number", read_only=True)
    received_by_email = serializers.SerializerMethodField()
    location_name = serializers.CharField(source="storage_location.name", read_only=True)
    items = PurchaseReceiptItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseReceipt
        fields = [
            "id", "purchase_order", "purchase_number",
            "received_by", "received_by_email",
            "storage_location", "location_name",
            "received_at", "notes", "items",
        ]
        read_only_fields = fields

    def get_received_by_email(self, obj):
        return obj.received_by.email if obj.received_by_id else None


# =============================================================================
# StockTransferItem — Read / Write
# =============================================================================

class StockTransferItemSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    item_sku = serializers.CharField(source="inventory_item.sku", read_only=True)

    class Meta:
        model = StockTransferItem
        fields = ["id", "inventory_item", "item_name", "item_sku", "quantity", "unit"]
        read_only_fields = fields


class StockTransferItemCreateSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.ChoiceField(choices=UNIT_CHOICES)


# =============================================================================
# StockTransfer — Read (list)
# =============================================================================

class StockTransferListSerializer(serializers.ModelSerializer):
    source_location_name = serializers.CharField(source="source_location.name", read_only=True)
    destination_location_name = serializers.CharField(source="destination_location.name", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    requested_by_email = serializers.SerializerMethodField()

    class Meta:
        model = StockTransfer
        fields = [
            "id", "transfer_number", "restaurant", "restaurant_name",
            "source_location", "source_location_name",
            "destination_location", "destination_location_name",
            "status", "notes",
            "requested_by", "requested_by_email",
            "requested_at", "approved_at", "completed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_requested_by_email(self, obj):
        return obj.requested_by.email if obj.requested_by_id else None


# =============================================================================
# StockTransfer — Read (detail)
# =============================================================================

class StockTransferDetailSerializer(StockTransferListSerializer):
    items = StockTransferItemSerializer(many=True, read_only=True)
    approved_by_email = serializers.SerializerMethodField()
    completed_by_email = serializers.SerializerMethodField()

    class Meta(StockTransferListSerializer.Meta):
        fields = StockTransferListSerializer.Meta.fields + [
            "approved_by", "approved_by_email",
            "completed_by", "completed_by_email",
            "items",
        ]
        read_only_fields = fields

    def get_approved_by_email(self, obj):
        return obj.approved_by.email if obj.approved_by_id else None

    def get_completed_by_email(self, obj):
        return obj.completed_by.email if obj.completed_by_id else None


# =============================================================================
# StockTransfer — Write
# =============================================================================

class CreateStockTransferSerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    source_location_id = serializers.UUIDField()
    destination_location_id = serializers.UUIDField()
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    items = StockTransferItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value

    def validate(self, attrs):
        if attrs.get("source_location_id") == attrs.get("destination_location_id"):
            raise serializers.ValidationError(
                {"destination_location_id": "Source and destination locations cannot be the same."}
            )
        return attrs


# =============================================================================
# StockWastage — Read
# =============================================================================

class StockWastageSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    item_sku = serializers.CharField(source="inventory_item.sku", read_only=True)
    location_name = serializers.CharField(source="storage_location.name", read_only=True)
    branch_name = serializers.CharField(source="storage_location.branch.name", read_only=True)
    recorded_by_email = serializers.SerializerMethodField()
    approved_by_email = serializers.SerializerMethodField()

    class Meta:
        model = StockWastage
        fields = [
            "id", "inventory_item", "item_name", "item_sku",
            "storage_location", "location_name", "branch_name",
            "quantity", "unit", "wastage_type", "reason",
            "estimated_cost", "status",
            "recorded_by", "recorded_by_email",
            "approved_by", "approved_by_email",
            "approved_at", "rejection_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_recorded_by_email(self, obj):
        return obj.recorded_by.email if obj.recorded_by_id else None

    def get_approved_by_email(self, obj):
        return obj.approved_by.email if obj.approved_by_id else None


# =============================================================================
# StockWastage — Write
# =============================================================================

class CreateStockWastageSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    storage_location_id = serializers.UUIDField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=3, min_value=Decimal("0.001"))
    unit = serializers.ChoiceField(choices=UNIT_CHOICES)
    wastage_type = serializers.ChoiceField(choices=WASTAGE_TYPE_CHOICES)
    reason = serializers.CharField(min_length=5)


class RejectWastageSerializer(serializers.Serializer):
    rejection_reason = serializers.CharField(min_length=5)


# =============================================================================
# StockAdjustment — Read
# =============================================================================

class StockAdjustmentSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    item_sku = serializers.CharField(source="inventory_item.sku", read_only=True)
    location_name = serializers.CharField(source="storage_location.name", read_only=True)
    adjusted_by_email = serializers.SerializerMethodField()

    class Meta:
        model = StockAdjustment
        fields = [
            "id", "inventory_item", "item_name", "item_sku",
            "storage_location", "location_name",
            "quantity_before", "quantity_physical", "quantity_difference",
            "unit", "reason",
            "adjusted_by", "adjusted_by_email",
            "stock_movement", "created_at",
        ]
        read_only_fields = fields

    def get_adjusted_by_email(self, obj):
        return obj.adjusted_by.email if obj.adjusted_by_id else None


# =============================================================================
# StockAdjustment — Write
# =============================================================================

class CreateStockAdjustmentSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    storage_location_id = serializers.UUIDField()
    quantity_physical = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0")
    )
    unit = serializers.ChoiceField(choices=UNIT_CHOICES)
    reason = serializers.CharField(min_length=5)


# =============================================================================
# Dashboard
# =============================================================================

class InventoryDashboardSerializer(serializers.Serializer):
    total_items = serializers.IntegerField()
    low_stock = serializers.IntegerField()
    out_of_stock = serializers.IntegerField()
    pending_purchases = serializers.IntegerField()
    pending_transfers = serializers.IntegerField()
    pending_wastage = serializers.IntegerField()
