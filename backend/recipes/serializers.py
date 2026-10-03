# =============================================================================
# RestaurantFlow — Recipe Serializers
# Phase 11
#
# Two-serializer pattern (mirrors inventory/serializers.py):
#   READ  serializers — ModelSerializer, all fields read_only, denormalized.
#   WRITE serializers — plain Serializer, validate input only.
#
# Security:
#   - Never accept cost values from the client.
#   - Never accept recipe_version from the client.
#   - IDs are validated server-side in services.
# =============================================================================

import logging
from decimal import Decimal

from rest_framework import serializers

from inventory.constants import UNIT_CHOICES
from recipes.constants import (
    RECIPE_STATUS_CHOICES,
    BATCH_STATUS_CHOICES,
    CONSUMPTION_STATUS_CHOICES,
    CONSUMPTION_TRIGGER_CHOICES,
)
from recipes.models import (
    Recipe,
    RecipeItem,
    ConsumptionBatch,
    StockConsumption,
    BranchConsumptionConfig,
)

logger = logging.getLogger("recipes")


# =============================================================================
# RecipeItem — Read
# =============================================================================

class RecipeItemSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    inventory_item_sku = serializers.CharField(source="inventory_item.sku", read_only=True)
    inventory_item_unit = serializers.CharField(source="inventory_item.default_unit", read_only=True)
    effective_quantity = serializers.DecimalField(max_digits=14, decimal_places=3, read_only=True)

    class Meta:
        model = RecipeItem
        fields = [
            "id", "recipe",
            "inventory_item", "inventory_item_name", "inventory_item_sku", "inventory_item_unit",
            "quantity", "unit",
            "preparation_loss_percentage",
            "effective_quantity",
            "notes", "display_order",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


# =============================================================================
# Recipe — Read (list)
# =============================================================================

class RecipeListSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source="menu_item.name", read_only=True)
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    created_by_email = serializers.SerializerMethodField()
    approved_by_email = serializers.SerializerMethodField()
    ingredient_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Recipe
        fields = [
            "id", "restaurant", "restaurant_name",
            "menu_item", "menu_item_name",
            "name", "version", "status",
            "yield_quantity", "yield_unit",
            "effective_from", "effective_to",
            "created_by", "created_by_email",
            "approved_by", "approved_by_email",
            "approved_at",
            "ingredient_count",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_created_by_email(self, obj):
        return obj.created_by.email if obj.created_by_id else None

    def get_approved_by_email(self, obj):
        return obj.approved_by.email if obj.approved_by_id else None


# =============================================================================
# Recipe — Read (detail)
# =============================================================================

class RecipeDetailSerializer(RecipeListSerializer):
    ingredients = RecipeItemSerializer(source="items", many=True, read_only=True)

    class Meta(RecipeListSerializer.Meta):
        fields = RecipeListSerializer.Meta.fields + [
            "preparation_notes",
            "ingredients",
        ]
        read_only_fields = fields


# =============================================================================
# Recipe — Write (create)
# =============================================================================

class CreateRecipeSerializer(serializers.Serializer):
    restaurant_id = serializers.UUIDField()
    menu_item_id = serializers.UUIDField()
    name = serializers.CharField(max_length=200)
    yield_quantity = serializers.DecimalField(
        max_digits=10, decimal_places=3,
        min_value=Decimal("0.001"),
        required=False, default="1.000",
    )
    yield_unit = serializers.ChoiceField(choices=UNIT_CHOICES, required=False, default="PIECE")
    preparation_notes = serializers.CharField(required=False, allow_blank=True, default="")
    effective_from = serializers.DateTimeField(required=False, allow_null=True, default=None)
    effective_to = serializers.DateTimeField(required=False, allow_null=True, default=None)

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Recipe name cannot be blank.")
        return value.strip()


# =============================================================================
# Recipe — Write (update)
# =============================================================================

class UpdateRecipeSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    yield_quantity = serializers.DecimalField(
        max_digits=10, decimal_places=3, min_value=Decimal("0.001"), required=False
    )
    yield_unit = serializers.ChoiceField(choices=UNIT_CHOICES, required=False)
    preparation_notes = serializers.CharField(required=False, allow_blank=True)
    effective_from = serializers.DateTimeField(required=False, allow_null=True)
    effective_to = serializers.DateTimeField(required=False, allow_null=True)


# =============================================================================
# RecipeItem — Write (add ingredient)
# =============================================================================

class AddRecipeItemSerializer(serializers.Serializer):
    inventory_item_id = serializers.UUIDField()
    quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0.001")
    )
    unit = serializers.ChoiceField(choices=UNIT_CHOICES)
    preparation_loss_percentage = serializers.DecimalField(
        max_digits=6, decimal_places=3,
        min_value=Decimal("0"), max_value=Decimal("99.999"),
        required=False, default="0.000",
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    display_order = serializers.IntegerField(required=False, default=0, min_value=0)


# =============================================================================
# RecipeItem — Write (update ingredient)
# =============================================================================

class UpdateRecipeItemSerializer(serializers.Serializer):
    quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0.001"), required=False
    )
    unit = serializers.ChoiceField(choices=UNIT_CHOICES, required=False)
    preparation_loss_percentage = serializers.DecimalField(
        max_digits=6, decimal_places=3,
        min_value=Decimal("0"), max_value=Decimal("99.999"),
        required=False,
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    display_order = serializers.IntegerField(required=False, min_value=0)


# =============================================================================
# StockConsumption — Read
# =============================================================================

class StockConsumptionSerializer(serializers.ModelSerializer):
    inventory_item_name = serializers.CharField(source="inventory_item.name", read_only=True)
    inventory_item_sku = serializers.CharField(source="inventory_item.sku", read_only=True)
    location_name = serializers.CharField(source="storage_location.name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    order_number = serializers.SerializerMethodField()
    menu_item_name = serializers.SerializerMethodField()
    consumed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = StockConsumption
        fields = [
            "id", "batch",
            "order", "order_number", "order_item",
            "restaurant", "branch", "branch_name",
            "recipe", "recipe_version", "menu_item_name",
            "inventory_item", "inventory_item_name", "inventory_item_sku",
            "storage_location", "location_name",
            "quantity", "unit",
            "unit_cost", "total_cost",
            "status",
            "consumed_at", "consumed_by", "consumed_by_email",
            "reference_type", "reference_id",
            "created_at",
        ]
        read_only_fields = fields

    def get_order_number(self, obj):
        return obj.order.order_number if obj.order_id else None

    def get_menu_item_name(self, obj):
        if obj.order_item_id and obj.order_item:
            return obj.order_item.item_name_snapshot
        return None

    def get_consumed_by_email(self, obj):
        return obj.consumed_by.email if obj.consumed_by_id else None


# =============================================================================
# ConsumptionBatch — Read (list)
# =============================================================================

class ConsumptionBatchListSerializer(serializers.ModelSerializer):
    order_number = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    triggered_by_email = serializers.SerializerMethodField()
    consumption_count = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = ConsumptionBatch
        fields = [
            "id", "order", "order_number",
            "branch", "branch_name",
            "status", "trigger",
            "triggered_by", "triggered_by_email",
            "triggered_at", "completed_at",
            "failure_reason",
            "consumption_count",
            "total_cost",
            "created_at",
        ]
        read_only_fields = fields

    def get_order_number(self, obj):
        return obj.order.order_number if obj.order_id else None

    def get_triggered_by_email(self, obj):
        return obj.triggered_by.email if obj.triggered_by_id else None

    def get_consumption_count(self, obj):
        return obj.consumptions.count()

    def get_total_cost(self, obj):
        from django.db.models import Sum
        result = obj.consumptions.aggregate(total=Sum("total_cost"))
        return str(result["total"] or "0.00")


# =============================================================================
# ConsumptionBatch — Read (detail)
# =============================================================================

class ConsumptionBatchDetailSerializer(ConsumptionBatchListSerializer):
    items = StockConsumptionSerializer(source="consumptions", many=True, read_only=True)

    class Meta(ConsumptionBatchListSerializer.Meta):
        fields = ConsumptionBatchListSerializer.Meta.fields + ["items"]
        read_only_fields = fields


# =============================================================================
# Manual Consumption — Write
# =============================================================================

class ManualConsumptionSerializer(serializers.Serializer):
    branch_id = serializers.UUIDField()
    inventory_item_id = serializers.UUIDField()
    storage_location_id = serializers.UUIDField()
    quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, min_value=Decimal("0.001")
    )
    unit = serializers.ChoiceField(choices=UNIT_CHOICES)
    reason = serializers.CharField(max_length=500)

    def validate_reason(self, value):
        if not value.strip():
            raise serializers.ValidationError("Reason cannot be blank.")
        return value.strip()


# =============================================================================
# Reversal — Write
# =============================================================================

class ReversalSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


# =============================================================================
# BranchConsumptionConfig — Read
# =============================================================================

class BranchConsumptionConfigSerializer(serializers.ModelSerializer):
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    location_name = serializers.SerializerMethodField()

    class Meta:
        model = BranchConsumptionConfig
        fields = [
            "id", "branch", "branch_name",
            "consumption_trigger",
            "default_consumption_location", "location_name",
            "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_location_name(self, obj):
        if obj.default_consumption_location_id:
            return obj.default_consumption_location.name
        return None


# =============================================================================
# BranchConsumptionConfig — Write
# =============================================================================

class UpdateBranchConsumptionConfigSerializer(serializers.Serializer):
    branch_id = serializers.UUIDField()
    consumption_trigger = serializers.ChoiceField(
        choices=CONSUMPTION_TRIGGER_CHOICES,
        required=False,
    )
    default_consumption_location_id = serializers.UUIDField(required=False, allow_null=True)
