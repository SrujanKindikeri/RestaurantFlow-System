# =============================================================================
# RestaurantFlow — Organizations Serializers
# Phase 2
# =============================================================================

import logging
from rest_framework import serializers

from .models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings

logger = logging.getLogger("organizations")


# =============================================================================
# RestaurantSettings
# =============================================================================

class RestaurantSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantSettings
        fields = [
            "id",
            "currency",
            "timezone",
            "tax_enabled",
            "default_tax_rate",
            "receipt_header",
            "receipt_footer",
            "allow_negative_stock",
            "order_prefix",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# BranchSettings
# =============================================================================

class BranchSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchSettings
        fields = [
            "id",
            "opening_time",
            "closing_time",
            "default_order_type",
            "receipt_footer",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# Branch
# =============================================================================

class BranchSerializer(serializers.ModelSerializer):
    """Flat Branch representation — used in list and nested contexts."""

    restaurant_name = serializers.CharField(source="restaurant.name", read_only=True)
    organization_id = serializers.UUIDField(
        source="restaurant.organization.id", read_only=True
    )

    class Meta:
        model = Branch
        fields = [
            "id",
            "restaurant",
            "restaurant_name",
            "organization_id",
            "name",
            "code",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "phone",
            "email",
            "latitude",
            "longitude",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "restaurant_name",
            "organization_id",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        restaurant = attrs.get("restaurant") or (
            self.instance.restaurant if self.instance else None
        )
        code = attrs.get("code", self.instance.code if self.instance else None)

        if restaurant and code:
            qs = Branch.objects.filter(restaurant=restaurant, code=code.strip().upper())
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "code": (
                            f"A branch with code '{code}' already exists "
                            f"in restaurant '{restaurant.name}'."
                        )
                    }
                )

        # Prevent creating branches under a disabled restaurant
        if attrs.get("restaurant") and not attrs["restaurant"].is_active:
            raise serializers.ValidationError(
                {"restaurant": "Cannot add a branch to a disabled restaurant."}
            )

        return attrs


class BranchDetailSerializer(BranchSerializer):
    """Branch with embedded settings."""

    settings = BranchSettingsSerializer(read_only=True)

    class Meta(BranchSerializer.Meta):
        fields = BranchSerializer.Meta.fields + ["settings"]


# =============================================================================
# Restaurant
# =============================================================================

class RestaurantSerializer(serializers.ModelSerializer):
    """Flat Restaurant representation."""

    organization_name = serializers.CharField(source="organization.name", read_only=True)
    branch_count = serializers.IntegerField(read_only=True)
    active_branch_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Restaurant
        fields = [
            "id",
            "organization",
            "organization_name",
            "name",
            "slug",
            "code",
            "description",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "is_active",
            "branch_count",
            "active_branch_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "organization_name",
            "branch_count",
            "active_branch_count",
            "created_at",
            "updated_at",
        ]

    def validate_code(self, value):
        return value.strip().upper()

    def validate(self, attrs):
        organization = attrs.get("organization") or (
            self.instance.organization if self.instance else None
        )
        code = attrs.get("code", self.instance.code if self.instance else None)

        if organization and code:
            qs = Restaurant.objects.filter(
                organization=organization, code=code.strip().upper()
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {
                        "code": (
                            f"A restaurant with code '{code}' already exists "
                            f"in organization '{organization.name}'."
                        )
                    }
                )

        # Prevent creating restaurants under a disabled organization
        if attrs.get("organization") and not attrs["organization"].is_active:
            raise serializers.ValidationError(
                {"organization": "Cannot add a restaurant to a disabled organization."}
            )

        return attrs


class RestaurantDetailSerializer(RestaurantSerializer):
    """Restaurant with embedded settings and branch summary."""

    settings = RestaurantSettingsSerializer(read_only=True)
    branches = BranchSerializer(many=True, read_only=True)

    class Meta(RestaurantSerializer.Meta):
        fields = RestaurantSerializer.Meta.fields + ["settings", "branches"]


# =============================================================================
# Organization
# =============================================================================

class OrganizationSerializer(serializers.ModelSerializer):
    """Flat Organization list representation."""

    restaurant_count = serializers.IntegerField(read_only=True)
    active_restaurant_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "legal_name",
            "slug",
            "email",
            "phone",
            "address",
            "city",
            "state",
            "country",
            "postal_code",
            "tax_id",
            "currency",
            "timezone",
            "is_active",
            "restaurant_count",
            "active_restaurant_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "slug",
            "restaurant_count",
            "active_restaurant_count",
            "created_at",
            "updated_at",
        ]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Organization name cannot be blank.")
        return value


class OrganizationDetailSerializer(OrganizationSerializer):
    """Organization with embedded restaurant summaries."""

    restaurants = RestaurantSerializer(many=True, read_only=True)

    class Meta(OrganizationSerializer.Meta):
        fields = OrganizationSerializer.Meta.fields + ["restaurants"]


# =============================================================================
# Stats (used by the dashboard endpoint)
# =============================================================================

class OrganizationStatsSerializer(serializers.Serializer):
    """Aggregated counts across all organizations — for dashboard use."""

    total_organizations = serializers.IntegerField()
    active_organizations = serializers.IntegerField()
    total_restaurants = serializers.IntegerField()
    active_restaurants = serializers.IntegerField()
    total_branches = serializers.IntegerField()
    active_branches = serializers.IntegerField()
