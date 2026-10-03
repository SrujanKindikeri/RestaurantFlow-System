# =============================================================================
# RestaurantFlow — Orders Serializers
# Phase 6
#
# Validation rules enforced here:
#   - table.branch == order.branch
#   - counter.branch == order.branch
#   - order type-field matrix (DINE_IN needs table, COUNTER needs counter, etc.)
#   - quantity > 0
#   - guest_count >= 1 for DINE_IN
#
# Price/tax snapshots are NEVER accepted from the client — they are resolved
# server-side in the service layer using the branch catalog.
# =============================================================================

import logging
from decimal import Decimal

from rest_framework import serializers

from accounts.models import User
from accounts import access as acl
from orders.models import (
    DiningTable, TableSession, Order, OrderItem,
    OrderType, OrderStatus, TableStatus, TableSessionStatus,
)

logger = logging.getLogger("orders")


# =============================================================================
# DiningTable
# =============================================================================

class DiningTableSerializer(serializers.ModelSerializer):
    branch_name      = serializers.CharField(source="branch.name", read_only=True)
    restaurant_id    = serializers.UUIDField(source="branch.restaurant.id", read_only=True)
    restaurant_name  = serializers.CharField(source="branch.restaurant.name", read_only=True)
    organization_id  = serializers.UUIDField(source="branch.restaurant.organization.id", read_only=True)
    is_occupied      = serializers.SerializerMethodField()
    active_session_id = serializers.SerializerMethodField()

    class Meta:
        model = DiningTable
        fields = [
            "id", "branch", "branch_name",
            "restaurant_id", "restaurant_name", "organization_id",
            "table_number", "name", "capacity", "section",
            "status", "display_order",
            "is_occupied", "active_session_id",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id",
            "branch_name", "restaurant_id", "restaurant_name", "organization_id",
            "is_occupied", "active_session_id",
            "created_at", "updated_at",
        ]

    def get_is_occupied(self, obj):
        return obj.sessions.filter(status=TableSessionStatus.OPEN).exists()

    def get_active_session_id(self, obj):
        session = obj.sessions.filter(status=TableSessionStatus.OPEN).first()
        return str(session.id) if session else None

    def validate_capacity(self, value):
        if value is not None and value < 1:
            raise serializers.ValidationError("Capacity must be at least 1.")
        return value

    def validate(self, attrs):
        branch = attrs.get("branch") or (
            self.instance.branch if self.instance else None
        )
        table_number = attrs.get(
            "table_number",
            self.instance.table_number if self.instance else None,
        )

        if branch and table_number:
            qs = DiningTable.objects.filter(
                branch=branch, table_number=table_number.strip()
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "table_number": (
                            f"Table number '{table_number}' already exists "
                            f"in branch '{branch.name}'."
                        )
                    }
                )
        return attrs


class DiningTableListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for table grid / list views."""

    branch_name   = serializers.CharField(source="branch.name", read_only=True)
    is_occupied   = serializers.SerializerMethodField()
    active_order  = serializers.SerializerMethodField()

    class Meta:
        model = DiningTable
        fields = [
            "id", "branch", "branch_name",
            "table_number", "name", "capacity", "section",
            "status", "display_order",
            "is_occupied", "active_order",
        ]

    def get_is_occupied(self, obj):
        return obj.sessions.filter(status=TableSessionStatus.OPEN).exists()

    def get_active_order(self, obj):
        """Return minimal info about the active order on this table (if any)."""
        session = obj.sessions.filter(status=TableSessionStatus.OPEN).first()
        if not session:
            return None
        order = session.orders.filter(
            status__in=[OrderStatus.DRAFT, OrderStatus.CONFIRMED]
        ).first()
        if not order:
            return None
        return {
            "id": str(order.id),
            "order_number": order.order_number,
            "status": order.status,
            "assigned_waiter": (
                order.assigned_waiter.full_name if order.assigned_waiter else None
            ),
        }


# =============================================================================
# TableSession
# =============================================================================

class TableSessionSerializer(serializers.ModelSerializer):
    table_number   = serializers.CharField(source="table.table_number", read_only=True)
    table_name     = serializers.CharField(source="table.name", read_only=True)
    branch_id      = serializers.UUIDField(source="table.branch.id", read_only=True)
    branch_name    = serializers.CharField(source="table.branch.name", read_only=True)
    restaurant_name = serializers.CharField(source="table.branch.restaurant.name", read_only=True)
    opened_by_email = serializers.CharField(source="opened_by.email", read_only=True)
    opened_by_name  = serializers.CharField(source="opened_by.full_name", read_only=True)
    closed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = TableSession
        fields = [
            "id",
            "table", "table_number", "table_name",
            "branch_id", "branch_name", "restaurant_name",
            "opened_by", "opened_by_email", "opened_by_name",
            "closed_by", "closed_by_email",
            "opened_at", "closed_at",
            "status", "guest_count", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = fields  # All read-only; write is via action serializers

    def get_closed_by_email(self, obj):
        return obj.closed_by.email if obj.closed_by else None


class OpenTableSessionSerializer(serializers.Serializer):
    """Write serializer for opening a table session."""

    guest_count = serializers.IntegerField(min_value=1, default=1)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


# =============================================================================
# OrderItem
# =============================================================================

class OrderItemSerializer(serializers.ModelSerializer):
    """Full OrderItem representation — snapshots are read-only."""

    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id", "order", "menu_item",
            "item_name_snapshot", "sku_snapshot",
            "unit_price_snapshot", "tax_rate_snapshot", "tax_code_snapshot",
            "quantity", "notes",
            "line_total",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id",
            "item_name_snapshot", "sku_snapshot",
            "unit_price_snapshot", "tax_rate_snapshot", "tax_code_snapshot",
            "line_total",
            "created_at", "updated_at",
        ]

    def get_line_total(self, obj):
        return str(obj.line_total)


class AddOrderItemSerializer(serializers.Serializer):
    """Write serializer for adding an item to an order."""

    menu_item = serializers.UUIDField()
    quantity = serializers.DecimalField(
        max_digits=7,
        decimal_places=3,
        min_value=Decimal("0.001"),
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_quantity(self, value):
        if value <= Decimal("0"):
            raise serializers.ValidationError("Quantity must be greater than 0.")
        if value > Decimal("9999.999"):
            raise serializers.ValidationError("Quantity is unreasonably large.")
        return value


class UpdateOrderItemSerializer(serializers.Serializer):
    """Write serializer for updating an order item's quantity and/or notes."""

    quantity = serializers.DecimalField(
        max_digits=7,
        decimal_places=3,
        min_value=Decimal("0.001"),
        required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True)

    def validate_quantity(self, value):
        if value is not None and value <= Decimal("0"):
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value


# =============================================================================
# Order
# =============================================================================

class OrderSerializer(serializers.ModelSerializer):
    """
    Full Order representation — used for list and detail views.
    """

    branch_name        = serializers.CharField(source="branch.name", read_only=True)
    restaurant_id      = serializers.UUIDField(source="branch.restaurant.id", read_only=True)
    restaurant_name    = serializers.CharField(source="branch.restaurant.name", read_only=True)
    organization_id    = serializers.UUIDField(
        source="branch.restaurant.organization.id", read_only=True
    )
    table_number       = serializers.SerializerMethodField()
    table_section      = serializers.SerializerMethodField()
    counter_code       = serializers.SerializerMethodField()
    counter_name       = serializers.SerializerMethodField()
    created_by_email   = serializers.CharField(source="created_by.email", read_only=True)
    created_by_name    = serializers.CharField(source="created_by.full_name", read_only=True)
    assigned_waiter_email = serializers.SerializerMethodField()
    assigned_waiter_name  = serializers.SerializerMethodField()
    item_count         = serializers.SerializerMethodField()
    preview_total      = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "branch", "branch_name",
            "restaurant_id", "restaurant_name", "organization_id",
            "order_number", "order_type",
            "table", "table_number", "table_section",
            "table_session",
            "counter", "counter_code", "counter_name",
            "counter_session",
            "created_by", "created_by_email", "created_by_name",
            "assigned_waiter", "assigned_waiter_email", "assigned_waiter_name",
            "guest_count", "status", "notes",
            "item_count", "preview_total",
            "confirmed_at", "cancelled_at",
            "cancellation_reason",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "order_number",
            "branch_name", "restaurant_id", "restaurant_name", "organization_id",
            "table_number", "table_section",
            "counter_code", "counter_name",
            "created_by", "created_by_email", "created_by_name",
            "assigned_waiter_email", "assigned_waiter_name",
            "item_count", "preview_total",
            "confirmed_at", "cancelled_at",
            "created_at", "updated_at",
        ]

    def get_table_number(self, obj):
        return obj.table.table_number if obj.table else None

    def get_table_section(self, obj):
        return obj.table.section if obj.table else None

    def get_counter_code(self, obj):
        return obj.counter.code if obj.counter else None

    def get_counter_name(self, obj):
        return obj.counter.name if obj.counter else None

    def get_assigned_waiter_email(self, obj):
        return obj.assigned_waiter.email if obj.assigned_waiter else None

    def get_assigned_waiter_name(self, obj):
        return obj.assigned_waiter.full_name if obj.assigned_waiter else None

    def get_item_count(self, obj):
        return obj.items.count()

    def get_preview_total(self, obj):
        """
        Convenience preview: sum of quantity × unit_price_snapshot.
        NOT the authoritative billing total — that belongs to Phase 8 Billing.
        """
        total = sum(item.line_total for item in obj.items.all())
        return str(total)


class OrderDetailSerializer(OrderSerializer):
    """Full order detail with embedded items."""

    items = OrderItemSerializer(many=True, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + ["items"]


class CreateOrderSerializer(serializers.Serializer):
    """Write serializer for creating an order."""

    branch         = serializers.UUIDField()
    order_type     = serializers.ChoiceField(choices=OrderType.choices)
    table          = serializers.UUIDField(required=False, allow_null=True, default=None)
    table_session  = serializers.UUIDField(required=False, allow_null=True, default=None)
    counter        = serializers.UUIDField(required=False, allow_null=True, default=None)
    counter_session = serializers.UUIDField(required=False, allow_null=True, default=None)
    guest_count    = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    assigned_waiter = serializers.IntegerField(required=False, allow_null=True)
    notes          = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        order_type = attrs.get("order_type")

        if order_type == OrderType.DINE_IN:
            if not attrs.get("table"):
                raise serializers.ValidationError(
                    {"table": "table is required for DINE_IN orders."}
                )
            if not attrs.get("table_session"):
                raise serializers.ValidationError(
                    {"table_session": "table_session is required for DINE_IN orders."}
                )
        elif order_type in (OrderType.COUNTER, OrderType.TAKEAWAY):
            if not attrs.get("counter"):
                raise serializers.ValidationError(
                    {"counter": "counter is required for COUNTER/TAKEAWAY orders."}
                )
            if not attrs.get("counter_session"):
                raise serializers.ValidationError(
                    {"counter_session": "counter_session is required for COUNTER/TAKEAWAY orders."}
                )

        return attrs


class CancelOrderSerializer(serializers.Serializer):
    """Write serializer for cancelling an order."""

    reason = serializers.CharField(required=False, allow_blank=True, default="")


class AssignWaiterSerializer(serializers.Serializer):
    """Write serializer for assigning a waiter to an order."""

    waiter = serializers.IntegerField()
