# =============================================================================
# RestaurantFlow — Menu Serializers
# Phase 5
#
# Validation rules enforced here:
#   - category.restaurant == menu_item.restaurant
#   - tax_rate.restaurant == menu_item.restaurant (when provided)
#   - branch.restaurant == menu_item.restaurant (prices and availability)
#   - price >= 0
#   - tax_rate >= 0
#   - overlapping active prices rejected
#   - SKU uniqueness within restaurant
#   - slug uniqueness within restaurant
# =============================================================================

import logging
from decimal import Decimal

from rest_framework import serializers

from accounts import access as acl

from .models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch

logger = logging.getLogger("menu")


# =============================================================================
# TaxRate
# =============================================================================

class TaxRateSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)

    class Meta:
        model = TaxRate
        fields = [
            "id", "restaurant", "restaurant_name",
            "name", "code", "rate", "description",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "restaurant_name", "created_at", "updated_at"]

    def validate_rate(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Tax rate cannot be negative.")
        return value

    def validate(self, attrs):
        restaurant = attrs.get("restaurant") or (
            self.instance.restaurant if self.instance else None
        )
        code = attrs.get("code", self.instance.code if self.instance else None)

        if restaurant and code:
            qs = TaxRate.objects.filter(restaurant=restaurant, code=code)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"code": f"Tax rate code '{code}' already exists for this restaurant."}
                )
        return attrs


class TaxRateMinimalSerializer(serializers.ModelSerializer):
    """Lightweight serializer for embedding inside menu item responses."""

    class Meta:
        model = TaxRate
        fields = ["id", "name", "code", "rate", "is_active"]


# =============================================================================
# Category
# =============================================================================

class CategorySerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "restaurant", "restaurant_name",
            "name", "slug", "description", "image",
            "display_order", "is_active",
            "item_count",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug", "restaurant_name", "item_count",
            "created_at", "updated_at",
        ]

    def get_item_count(self, obj):
        return obj.items.filter(is_active=True).count()

    def validate(self, attrs):
        restaurant = attrs.get("restaurant") or (
            self.instance.restaurant if self.instance else None
        )
        name = attrs.get("name", self.instance.name if self.instance else None)

        if restaurant and name:
            from django.utils.text import slugify
            candidate_slug = slugify(name)
            qs = Category.objects.filter(restaurant=restaurant, slug=candidate_slug)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": f"A category with this name already exists for this restaurant."}
                )
        return attrs


class CategoryMinimalSerializer(serializers.ModelSerializer):
    """Lightweight serializer for embedding inside menu item responses."""

    class Meta:
        model = Category
        fields = ["id", "name", "slug", "display_order", "is_active"]


# =============================================================================
# MenuItem
# =============================================================================

class MenuItemSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    tax_rate_detail = TaxRateMinimalSerializer(source="tax_rate", read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            "id", "restaurant", "restaurant_name",
            "category", "category_name",
            "tax_rate", "tax_rate_detail",
            "name", "slug", "sku",
            "description", "short_description",
            "image", "food_type",
            "display_order", "is_active", "is_available",
            "preparation_time_minutes",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "slug",
            "restaurant_name", "category_name", "tax_rate_detail",
            "created_at", "updated_at",
        ]

    def validate(self, attrs):
        restaurant = attrs.get("restaurant") or (
            self.instance.restaurant if self.instance else None
        )
        category = attrs.get("category") or (
            self.instance.category if self.instance else None
        )
        tax_rate = attrs.get("tax_rate") or (
            self.instance.tax_rate if self.instance else None
        )
        name = attrs.get("name", self.instance.name if self.instance else None)
        sku = attrs.get("sku", self.instance.sku if self.instance else None)

        # category must belong to same restaurant
        if category and restaurant:
            if str(category.restaurant_id) != str(restaurant.pk):
                raise serializers.ValidationError(
                    {
                        "category": (
                            "Category must belong to the same restaurant as the menu item. "
                            f"Expected restaurant: '{restaurant.name}', "
                            f"category restaurant: '{category.restaurant.name}'."
                        )
                    }
                )

        # tax_rate must belong to same restaurant
        if tax_rate and restaurant:
            if str(tax_rate.restaurant_id) != str(restaurant.pk):
                raise serializers.ValidationError(
                    {
                        "tax_rate": (
                            "Tax rate must belong to the same restaurant as the menu item."
                        )
                    }
                )

        # SKU uniqueness within restaurant (if SKU provided)
        if sku and restaurant:
            qs = MenuItem.objects.filter(restaurant=restaurant, sku=sku)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"sku": f"SKU '{sku}' already exists for this restaurant."}
                )

        # Slug uniqueness check (based on name since slug is auto-generated)
        if name and restaurant:
            from django.utils.text import slugify
            candidate_slug = slugify(name)
            qs = MenuItem.objects.filter(restaurant=restaurant, slug=candidate_slug)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"name": "A menu item with this name already exists for this restaurant."}
                )

        return attrs


class MenuItemDetailSerializer(MenuItemSerializer):
    """Full detail serializer with prices and branch availability summary."""

    active_prices = serializers.SerializerMethodField()
    branch_availability = serializers.SerializerMethodField()

    class Meta(MenuItemSerializer.Meta):
        fields = MenuItemSerializer.Meta.fields + [
            "active_prices",
            "branch_availability",
        ]

    def get_active_prices(self, obj):
        prices = obj.prices.filter(is_active=True).select_related("branch")
        return [
            {
                "id": str(p.id),
                "branch": str(p.branch_id),
                "branch_name": p.branch.name,
                "price": str(p.price),
                "effective_from": p.effective_from,
                "effective_to": p.effective_to,
            }
            for p in prices
        ]

    def get_branch_availability(self, obj):
        avails = obj.branch_availability.all().select_related("branch")
        return [
            {
                "id": str(a.id),
                "branch": str(a.branch_id),
                "branch_name": a.branch.name,
                "is_available": a.is_available,
                "available_from": str(a.available_from) if a.available_from else None,
                "available_to": str(a.available_to) if a.available_to else None,
            }
            for a in avails
        ]


# =============================================================================
# MenuItemPrice
# =============================================================================

class MenuItemPriceSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source="menu_item.name", read_only=True)
    menu_item_sku = serializers.CharField(source="menu_item.sku", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    restaurant_id = serializers.UUIDField(
        source="menu_item.restaurant.id", read_only=True
    )

    class Meta:
        model = MenuItemPrice
        fields = [
            "id",
            "menu_item", "menu_item_name", "menu_item_sku",
            "branch", "branch_name",
            "restaurant_id",
            "price",
            "effective_from", "effective_to",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id",
            "menu_item_name", "menu_item_sku",
            "branch_name", "restaurant_id",
            "created_at", "updated_at",
        ]

    def validate_price(self, value):
        if value < Decimal("0"):
            raise serializers.ValidationError("Price cannot be negative.")
        return value

    def validate(self, attrs):
        menu_item = attrs.get("menu_item") or (
            self.instance.menu_item if self.instance else None
        )
        branch = attrs.get("branch") or (
            self.instance.branch if self.instance else None
        )
        effective_from = attrs.get(
            "effective_from",
            self.instance.effective_from if self.instance else None,
        )
        effective_to = attrs.get(
            "effective_to",
            self.instance.effective_to if self.instance else None,
        )
        is_active = attrs.get(
            "is_active",
            self.instance.is_active if self.instance else True,
        )

        # branch.restaurant must equal menu_item.restaurant
        if menu_item and branch:
            if str(menu_item.restaurant_id) != str(branch.restaurant_id):
                raise serializers.ValidationError(
                    {
                        "branch": (
                            "Branch must belong to the same restaurant as the menu item. "
                            f"Item restaurant: '{menu_item.restaurant.name}', "
                            f"Branch restaurant: '{branch.restaurant.name}'."
                        )
                    }
                )

        # Check for overlapping active price periods
        if menu_item and branch and is_active:
            qs = MenuItemPrice.objects.filter(
                menu_item=menu_item,
                branch=branch,
                is_active=True,
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                # If effective dates are provided, check for overlap
                if effective_from is not None or effective_to is not None:
                    from django.db.models import Q
                    overlap_qs = qs.filter(
                        Q(effective_to__isnull=True) |
                        Q(effective_to__gt=effective_from or "1900-01-01")
                    )
                    if effective_to:
                        overlap_qs = overlap_qs.filter(
                            Q(effective_from__isnull=True) |
                            Q(effective_from__lt=effective_to)
                        )
                    if overlap_qs.exists():
                        raise serializers.ValidationError(
                            {
                                "is_active": (
                                    "An active price already exists for this item and branch "
                                    "in this time period. "
                                    "Set is_active=False on the existing price first, or "
                                    "specify non-overlapping effective dates."
                                )
                            }
                        )
                else:
                    raise serializers.ValidationError(
                        {
                            "is_active": (
                                "An active price already exists for this menu item and branch. "
                                "Deactivate the existing price before creating a new active one, "
                                "or provide non-overlapping effective dates."
                            )
                        }
                    )

        return attrs


# =============================================================================
# MenuItemBranch (availability)
# =============================================================================

class MenuItemBranchSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source="menu_item.name", read_only=True)
    menu_item_sku = serializers.CharField(source="menu_item.sku", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    restaurant_id = serializers.UUIDField(
        source="menu_item.restaurant.id", read_only=True
    )

    class Meta:
        model = MenuItemBranch
        fields = [
            "id",
            "menu_item", "menu_item_name", "menu_item_sku",
            "branch", "branch_name",
            "restaurant_id",
            "is_available",
            "available_from", "available_to",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id",
            "menu_item_name", "menu_item_sku",
            "branch_name", "restaurant_id",
            "created_at", "updated_at",
        ]

    def validate(self, attrs):
        menu_item = attrs.get("menu_item") or (
            self.instance.menu_item if self.instance else None
        )
        branch = attrs.get("branch") or (
            self.instance.branch if self.instance else None
        )

        # branch.restaurant must equal menu_item.restaurant
        if menu_item and branch:
            if str(menu_item.restaurant_id) != str(branch.restaurant_id):
                raise serializers.ValidationError(
                    {
                        "branch": (
                            "Branch must belong to the same restaurant as the menu item."
                        )
                    }
                )

        # Duplicate check (one record per menu_item+branch)
        if menu_item and branch:
            qs = MenuItemBranch.objects.filter(menu_item=menu_item, branch=branch)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    "An availability record for this menu item and branch already exists."
                )

        return attrs


# =============================================================================
# Catalog (read-optimized for POS / branch view)
# =============================================================================

class CatalogItemSerializer(serializers.Serializer):
    """
    Read-only catalog representation of a MenuItem for POS consumption.
    Includes branch-specific price and tax info.
    Does NOT expose internal costs, margins, or supplier data.
    """
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    sku = serializers.CharField()
    short_description = serializers.CharField()
    food_type = serializers.CharField()
    image = serializers.ImageField(allow_null=True)
    display_order = serializers.IntegerField()
    preparation_time_minutes = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    tax_rate_code = serializers.CharField(allow_null=True)
    tax_rate_name = serializers.CharField(allow_null=True)
    tax_rate = serializers.DecimalField(
        max_digits=6, decimal_places=3, allow_null=True
    )


class CatalogCategorySerializer(serializers.Serializer):
    """Read-only catalog category with nested items."""
    id = serializers.UUIDField()
    name = serializers.CharField()
    slug = serializers.CharField()
    display_order = serializers.IntegerField()
    items = CatalogItemSerializer(many=True)


class BranchCatalogSerializer(serializers.Serializer):
    """Full branch catalog response — used by GET /api/menu/branches/{id}/catalog/."""
    branch = serializers.DictField()
    categories = CatalogCategorySerializer(many=True)
