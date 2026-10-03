# =============================================================================
# RestaurantFlow — Kitchen Serializers
# Phase 7
#
# Serializers intentionally EXCLUDE all financial data:
#   - unit_price_snapshot
#   - tax_rate_snapshot
#   - tax_code_snapshot
#   - sku_snapshot
#   - line_total
#   - cash amounts
#   - accounting data
#
# Kitchen staff see only operational preparation information.
# =============================================================================

import logging

from rest_framework import serializers

from kitchen.models import (
    KitchenOrder,
    KitchenOrderItem,
    KitchenOrderStatus,
    KitchenItemStatus,
    KitchenPriority,
)

logger = logging.getLogger("kitchen")


# =============================================================================
# KitchenOrderItem Serializers
# =============================================================================

class KitchenOrderItemSerializer(serializers.ModelSerializer):
    """
    Full item representation for KDS.
    Financial snapshots are intentionally omitted.
    """

    class Meta:
        model = KitchenOrderItem
        fields = [
            "id",
            "order_item",
            "menu_item",
            "item_name_snapshot",
            "quantity",
            "notes",
            "food_type",
            "preparation_time_minutes",
            "status",
            "station",
            "started_at",
            "ready_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class KitchenOrderItemListSerializer(serializers.ModelSerializer):
    """Lightweight item representation used in KDS order cards."""

    class Meta:
        model = KitchenOrderItem
        fields = [
            "id",
            "item_name_snapshot",
            "quantity",
            "notes",
            "food_type",
            "preparation_time_minutes",
            "status",
            "station",
            "started_at",
            "ready_at",
        ]
        read_only_fields = fields


# =============================================================================
# KitchenOrder Serializers
# =============================================================================

class KitchenOrderSerializer(serializers.ModelSerializer):
    """
    Full KitchenOrder representation for list and detail views.
    Includes denormalized fields from the linked Order for KDS display.
    Excludes all financial data.
    """

    # ---- Denormalized from linked Order ----
    order_number        = serializers.CharField(source="order.order_number",    read_only=True)
    order_type          = serializers.CharField(source="order.order_type",      read_only=True)
    order_notes         = serializers.CharField(source="order.notes",           read_only=True)
    branch_name         = serializers.CharField(source="branch.name",           read_only=True)
    restaurant_id       = serializers.UUIDField(
        source="branch.restaurant.id", read_only=True
    )
    restaurant_name     = serializers.CharField(
        source="branch.restaurant.name", read_only=True
    )

    # ---- Table info (DINE_IN) ----
    table_number        = serializers.SerializerMethodField()
    table_section       = serializers.SerializerMethodField()

    # ---- Counter info (COUNTER / TAKEAWAY) ----
    counter_code        = serializers.SerializerMethodField()
    counter_name        = serializers.SerializerMethodField()

    # ---- Waiter ----
    assigned_waiter_name  = serializers.SerializerMethodField()

    # ---- Timing ----
    age_seconds         = serializers.SerializerMethodField()

    # ---- Items ----
    items               = KitchenOrderItemListSerializer(many=True, read_only=True)

    # ---- Actors (names only — no emails on KDS) ----
    accepted_by_name    = serializers.SerializerMethodField()
    started_by_name     = serializers.SerializerMethodField()
    completed_by_name   = serializers.SerializerMethodField()
    cancelled_by_name   = serializers.SerializerMethodField()

    class Meta:
        model = KitchenOrder
        fields = [
            # Kitchen order identity
            "id",
            "order",
            "order_number",
            "order_type",
            "order_notes",

            # Branch / restaurant
            "branch",
            "branch_name",
            "restaurant_id",
            "restaurant_name",

            # Order context
            "table_number",
            "table_section",
            "counter_code",
            "counter_name",
            "assigned_waiter_name",

            # Kitchen state
            "status",
            "priority",
            "kitchen_note",

            # Timestamps
            "received_at",
            "accepted_at",
            "started_at",
            "ready_at",
            "cancelled_at",
            "age_seconds",
            "created_at",
            "updated_at",

            # Actors
            "accepted_by_name",
            "started_by_name",
            "completed_by_name",
            "cancelled_by_name",
            "cancelled_by",
            "cancellation_reason",

            # Items
            "items",
        ]
        read_only_fields = fields

    def get_table_number(self, obj):
        return obj.order.table.table_number if obj.order.table else None

    def get_table_section(self, obj):
        return obj.order.table.section if obj.order.table else None

    def get_counter_code(self, obj):
        return obj.order.counter.code if obj.order.counter else None

    def get_counter_name(self, obj):
        return obj.order.counter.name if obj.order.counter else None

    def get_assigned_waiter_name(self, obj):
        return obj.order.assigned_waiter.full_name if obj.order.assigned_waiter else None

    def get_age_seconds(self, obj):
        """Return seconds since the kitchen order was received."""
        from django.utils import timezone
        return int((timezone.now() - obj.received_at).total_seconds())

    def get_accepted_by_name(self, obj):
        return obj.accepted_by.full_name if obj.accepted_by else None

    def get_started_by_name(self, obj):
        return obj.started_by.full_name if obj.started_by else None

    def get_completed_by_name(self, obj):
        return obj.completed_by.full_name if obj.completed_by else None

    def get_cancelled_by_name(self, obj):
        return obj.cancelled_by.full_name if obj.cancelled_by else None


class KitchenOrderDetailSerializer(KitchenOrderSerializer):
    """Detail view: uses full item serializer with all item timestamps."""

    items = KitchenOrderItemSerializer(many=True, read_only=True)

    class Meta(KitchenOrderSerializer.Meta):
        pass


class KitchenOrderListSerializer(serializers.ModelSerializer):
    """
    Lightweight list serializer for KDS column views.
    Optimized for minimal data transfer to the KDS.
    """

    order_number    = serializers.CharField(source="order.order_number",  read_only=True)
    order_type      = serializers.CharField(source="order.order_type",    read_only=True)
    table_number    = serializers.SerializerMethodField()
    counter_code    = serializers.SerializerMethodField()
    age_seconds     = serializers.SerializerMethodField()
    item_count      = serializers.SerializerMethodField()
    items           = KitchenOrderItemListSerializer(many=True, read_only=True)

    class Meta:
        model = KitchenOrder
        fields = [
            "id",
            "order_number",
            "order_type",
            "table_number",
            "counter_code",
            "status",
            "priority",
            "kitchen_note",
            "received_at",
            "accepted_at",
            "started_at",
            "ready_at",
            "age_seconds",
            "item_count",
            "items",
        ]
        read_only_fields = fields

    def get_table_number(self, obj):
        return obj.order.table.table_number if obj.order.table else None

    def get_counter_code(self, obj):
        return obj.order.counter.code if obj.order.counter else None

    def get_age_seconds(self, obj):
        from django.utils import timezone
        return int((timezone.now() - obj.received_at).total_seconds())

    def get_item_count(self, obj):
        return obj.items.count()


# =============================================================================
# Action serializers (write only)
# =============================================================================

class CancelKitchenOrderSerializer(serializers.Serializer):
    """Body for cancelling a kitchen order."""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class UpdatePrioritySerializer(serializers.Serializer):
    """Body for updating kitchen order priority."""
    priority = serializers.ChoiceField(choices=KitchenPriority.choices)


class KitchenNoteSerializer(serializers.Serializer):
    """Body for updating the kitchen note on an order."""
    kitchen_note = serializers.CharField(required=False, allow_blank=True, default="")
