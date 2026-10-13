# =============================================================================
# RestaurantFlow — Operations Serializers
# Phase 19: Advanced POS & Restaurant Operations
# =============================================================================

from rest_framework import serializers

from operations.models import (
    POSDevice, POSSession,
    MenuModifierGroup, MenuModifierOption, OrderItemModifier,
    OrderFulfillmentStatus, OrderChangeRequest,
    TableFloorPlan, TableOperationalStatus,
    TableTransfer, TableMerge, OrderMergeRequest,
    BillSplit, BillSplitItem,
    ReceiptPrintLog, OperationalShift, ShiftHandoverNote,
)


# ---------------------------------------------------------------------------
# POSDevice
# ---------------------------------------------------------------------------

class POSDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = POSDevice
        fields = [
            "id", "restaurant", "branch", "counter",
            "device_name", "device_identifier", "device_type",
            "is_active", "last_seen_at", "registered_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "registered_by", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# POSSession
# ---------------------------------------------------------------------------

class POSSessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    counter_code = serializers.CharField(source="counter.code", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = POSSession
        fields = [
            "id", "counter", "counter_code",
            "counter_session", "user", "user_email",
            "branch", "branch_name",
            "device_identifier", "status",
            "started_at", "ended_at", "last_activity_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "user", "branch", "started_at", "created_at", "updated_at",
        ]


class POSSessionStartSerializer(serializers.Serializer):
    counter_id = serializers.UUIDField()
    device_identifier = serializers.CharField(max_length=200, required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# Barcode / SKU Scan
# ---------------------------------------------------------------------------

class BarcodeScanSerializer(serializers.Serializer):
    barcode_or_sku = serializers.CharField(max_length=200)


class BarcodeScanResultSerializer(serializers.Serializer):
    menu_item_id = serializers.CharField()
    name = serializers.CharField()
    sku = serializers.CharField()
    price = serializers.CharField(allow_null=True)
    tax_rate = serializers.CharField()
    tax_code = serializers.CharField()


# ---------------------------------------------------------------------------
# MenuModifierGroup / Option
# ---------------------------------------------------------------------------

class MenuModifierOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuModifierOption
        fields = ["id", "name", "price_adjustment", "is_active"]
        read_only_fields = ["id"]


class MenuModifierGroupSerializer(serializers.ModelSerializer):
    options = MenuModifierOptionSerializer(many=True, read_only=True)

    class Meta:
        model = MenuModifierGroup
        fields = [
            "id", "restaurant", "name", "description",
            "is_required", "min_selections", "max_selections",
            "is_active", "options", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class MenuModifierGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuModifierGroup
        fields = [
            "restaurant", "name", "description",
            "is_required", "min_selections", "max_selections", "is_active",
        ]


# ---------------------------------------------------------------------------
# OrderItemModifier
# ---------------------------------------------------------------------------

class OrderItemModifierSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItemModifier
        fields = [
            "id", "order_item", "modifier_option",
            "name", "value", "price_adjustment", "created_at",
        ]
        read_only_fields = ["id", "price_adjustment", "created_at"]


class AddModifierSerializer(serializers.Serializer):
    modifier_option_id = serializers.UUIDField(required=False, allow_null=True)
    name = serializers.CharField(max_length=150)
    value = serializers.CharField(max_length=150)


# ---------------------------------------------------------------------------
# OrderFulfillmentStatus
# ---------------------------------------------------------------------------

class OrderFulfillmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderFulfillmentStatus
        fields = [
            "id", "order", "status", "served_by", "served_at", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "order", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# OrderChangeRequest
# ---------------------------------------------------------------------------

class OrderChangeRequestSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(
        source="requested_by.email", read_only=True
    )
    approved_by_email = serializers.SerializerMethodField()

    class Meta:
        model = OrderChangeRequest
        fields = [
            "id", "order", "requested_by", "requested_by_email",
            "change_type", "reason", "requested_data",
            "status", "approved_by", "approved_by_email",
            "approved_at", "rejected_at", "review_note",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "requested_by", "status", "approved_by",
            "approved_at", "rejected_at", "created_at", "updated_at",
        ]

    def get_approved_by_email(self, obj):
        return obj.approved_by.email if obj.approved_by else None


class OrderChangeRequestCreateSerializer(serializers.Serializer):
    change_type = serializers.ChoiceField(
        choices=[
            "ADD_ITEM", "REMOVE_ITEM", "CHANGE_QUANTITY",
            "CHANGE_NOTE", "CHANGE_TABLE", "CHANGE_WAITER", "CHANGE_CUSTOMER",
        ]
    )
    reason = serializers.CharField()
    requested_data = serializers.DictField(default=dict)


class OrderChangeRequestReviewSerializer(serializers.Serializer):
    review_note = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# TableFloorPlan
# ---------------------------------------------------------------------------

class TableFloorPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableFloorPlan
        fields = [
            "id", "table", "position_x", "position_y",
            "width", "height", "rotation", "shape",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "table", "created_at", "updated_at"]


# ---------------------------------------------------------------------------
# TableOperationalStatus
# ---------------------------------------------------------------------------

class TableOperationalStatusSerializer(serializers.ModelSerializer):
    table_number = serializers.CharField(source="table.table_number", read_only=True)

    class Meta:
        model = TableOperationalStatus
        fields = ["id", "table", "table_number", "status", "notes", "updated_at"]
        read_only_fields = ["id", "table", "updated_at"]


# ---------------------------------------------------------------------------
# TableTransfer
# ---------------------------------------------------------------------------

class TableTransferSerializer(serializers.ModelSerializer):
    source_table_number = serializers.CharField(
        source="source_table.table_number", read_only=True
    )
    destination_table_number = serializers.CharField(
        source="destination_table.table_number", read_only=True
    )

    class Meta:
        model = TableTransfer
        fields = [
            "id", "source_table", "source_table_number",
            "destination_table", "destination_table_number",
            "order", "requested_by", "approved_by",
            "status", "reason", "completed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "requested_by", "approved_by", "status",
            "completed_at", "created_at", "updated_at",
        ]


class TableTransferRequestSerializer(serializers.Serializer):
    destination_table_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# TableMerge
# ---------------------------------------------------------------------------

class TableMergeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableMerge
        fields = [
            "id", "restaurant", "branch",
            "source_tables", "destination_table",
            "requested_by", "approved_by",
            "status", "reason", "completed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "requested_by", "approved_by", "status",
            "completed_at", "created_at", "updated_at",
        ]


class TableMergeRequestSerializer(serializers.Serializer):
    source_table_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1
    )
    destination_table_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# OrderMergeRequest
# ---------------------------------------------------------------------------

class OrderMergeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderMergeRequest
        fields = [
            "id", "source_orders", "destination_order",
            "requested_by", "approved_by",
            "status", "reason", "completed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "requested_by", "approved_by", "status",
            "completed_at", "created_at", "updated_at",
        ]


class OrderMergeRequestCreateSerializer(serializers.Serializer):
    source_order_ids = serializers.ListField(
        child=serializers.UUIDField(), min_length=1
    )
    destination_order_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# BillSplit
# ---------------------------------------------------------------------------

class BillSplitItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillSplitItem
        fields = ["id", "bill_split", "bill_item", "quantity", "amount"]
        read_only_fields = ["id"]


class BillSplitSerializer(serializers.ModelSerializer):
    split_items = BillSplitItemSerializer(many=True, read_only=True)

    class Meta:
        model = BillSplit
        fields = [
            "id", "bill", "split_number", "split_type",
            "amount", "status", "created_by",
            "split_items", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "created_by", "status", "created_at", "updated_at",
        ]


class BillSplitCreateSerializer(serializers.Serializer):
    split_type = serializers.ChoiceField(choices=["ITEM", "QUANTITY", "EQUAL", "GUEST"])
    num_splits = serializers.IntegerField(min_value=2, required=False, default=2)
    item_allocations = serializers.ListField(
        child=serializers.DictField(), required=False, allow_empty=True
    )


# ---------------------------------------------------------------------------
# ReceiptPrintLog
# ---------------------------------------------------------------------------

class ReceiptPrintLogSerializer(serializers.ModelSerializer):
    printed_by_email = serializers.EmailField(
        source="printed_by.email", read_only=True
    )

    class Meta:
        model = ReceiptPrintLog
        fields = [
            "id", "bill", "payment", "printed_by", "printed_by_email",
            "print_type", "reason", "printed_at",
        ]
        read_only_fields = ["id", "printed_by", "printed_at"]


class PrintReceiptSerializer(serializers.Serializer):
    payment_id = serializers.UUIDField(required=False, allow_null=True)
    print_type = serializers.ChoiceField(
        choices=["ORIGINAL", "REPRINT", "DUPLICATE", "KITCHEN"],
        default="ORIGINAL",
    )
    reason = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# OperationalShift
# ---------------------------------------------------------------------------

class OperationalShiftSerializer(serializers.ModelSerializer):
    opened_by_email = serializers.EmailField(
        source="opened_by.email", read_only=True
    )
    closed_by_email = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = OperationalShift
        fields = [
            "id", "branch", "branch_name", "shift_type", "status",
            "started_at", "ended_at",
            "opened_by", "opened_by_email",
            "closed_by", "closed_by_email",
            "notes", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "opened_by", "closed_by", "status",
            "ended_at", "created_at", "updated_at",
        ]

    def get_closed_by_email(self, obj):
        return obj.closed_by.email if obj.closed_by else None


class OperationalShiftCreateSerializer(serializers.Serializer):
    branch_id = serializers.UUIDField()
    shift_type = serializers.ChoiceField(
        choices=["MORNING", "AFTERNOON", "EVENING", "NIGHT", "CUSTOM"]
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class ShiftCloseSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True)


# ---------------------------------------------------------------------------
# ShiftHandoverNote
# ---------------------------------------------------------------------------

class ShiftHandoverNoteSerializer(serializers.ModelSerializer):
    created_by_email = serializers.EmailField(
        source="created_by.email", read_only=True
    )

    class Meta:
        model = ShiftHandoverNote
        fields = [
            "id", "shift", "created_by", "created_by_email",
            "note_type", "content", "priority",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "shift", "created_by", "created_at", "updated_at"]


class ShiftHandoverNoteCreateSerializer(serializers.Serializer):
    note_type = serializers.ChoiceField(
        choices=[
            "GENERAL", "KITCHEN", "INVENTORY", "CUSTOMER",
            "PAYMENT", "EQUIPMENT", "STAFF", "OTHER",
        ]
    )
    content = serializers.CharField()
    priority = serializers.ChoiceField(
        choices=["LOW", "NORMAL", "HIGH"], default="NORMAL"
    )


# ---------------------------------------------------------------------------
# Priority / Hold / Waiter
# ---------------------------------------------------------------------------

class OrderPrioritySerializer(serializers.Serializer):
    priority = serializers.ChoiceField(choices=["NORMAL", "HIGH", "URGENT"])


class OrderWaiterSerializer(serializers.Serializer):
    waiter_id = serializers.IntegerField(
        help_text="User ID (int) of the waiter to assign."
    )


class TableStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            "AVAILABLE", "OCCUPIED", "RESERVED",
            "BILL_PENDING", "CLEANING", "OUT_OF_SERVICE",
        ]
    )
    notes = serializers.CharField(required=False, allow_blank=True)


class OrderHoldSerializer(serializers.Serializer):
    """No body required — action determined by endpoint."""
    pass


class OrderServedSerializer(serializers.Serializer):
    """No body required."""
    pass
