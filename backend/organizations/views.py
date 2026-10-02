# =============================================================================
# RestaurantFlow — Organizations Views
# Phase 2
#
# URL layout (registered in organizations/urls.py → config/urls.py):
#
#   /api/organizations/                     list + create
#   /api/organizations/<id>/                retrieve + partial_update
#   /api/organizations/<id>/restaurants/    list + create restaurants under org
#   /api/organizations/stats/               aggregate dashboard counts
#
#   /api/restaurants/                       list all restaurants (admin-style)
#   /api/restaurants/<id>/                  retrieve + partial_update
#   /api/restaurants/<id>/branches/         list + create branches under restaurant
#   /api/restaurants/<id>/settings/         retrieve + partial_update settings
#
#   /api/branches/                          list all branches (admin-style)
#   /api/branches/<id>/                     retrieve + partial_update
#   /api/branches/<id>/settings/            retrieve + partial_update settings
#
# Security notes (Phase 2):
#   - All endpoints require IsAuthenticated (inherited from DRF default).
#   - Scoped queryset helpers are extracted so Phase 3 can swap in real
#     ownership checks without rewriting views.
#   - IDs are always UUIDs — no sequential exposure.
#   - 404 is returned when a resource exists but belongs to a different scope,
#     preventing information leakage.
# =============================================================================

import logging
from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings
from .serializers import (
    OrganizationSerializer,
    OrganizationDetailSerializer,
    OrganizationStatsSerializer,
    RestaurantSerializer,
    RestaurantDetailSerializer,
    RestaurantSettingsSerializer,
    BranchSerializer,
    BranchDetailSerializer,
    BranchSettingsSerializer,
)

logger = logging.getLogger("organizations")


# =============================================================================
# Queryset helpers — Phase 3 will narrow these to ownership scope
# =============================================================================

def get_organization_queryset(request=None):
    """
    Return the base Organization queryset.
    Phase 3 will filter by request.user.organization or staff flag.
    """
    return Organization.objects.annotate(
        restaurant_count=Count("restaurants"),
        active_restaurant_count=Count(
            "restaurants", filter=Q(restaurants__is_active=True)
        ),
    )


def get_restaurant_queryset(request=None, organization_id=None):
    qs = Restaurant.objects.annotate(
        branch_count=Count("branches"),
        active_branch_count=Count("branches", filter=Q(branches__is_active=True)),
    )
    if organization_id:
        qs = qs.filter(organization_id=organization_id)
    return qs


def get_branch_queryset(request=None, restaurant_id=None):
    qs = Branch.objects.select_related("restaurant__organization")
    if restaurant_id:
        qs = qs.filter(restaurant_id=restaurant_id)
    return qs


# =============================================================================
# Organization views
# =============================================================================

class OrganizationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/organizations/   — list all organizations
    POST /api/organizations/   — create a new organization
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        return OrganizationSerializer

    def get_queryset(self):
        return get_organization_queryset(self.request)

    def perform_create(self, serializer):
        org = serializer.save()
        logger.info(
            "Organization created: %s (id=%s) by user=%s",
            org.name,
            org.id,
            self.request.user.id,
        )


class OrganizationDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/organizations/<id>/    — retrieve detail (with restaurants)
    PATCH /api/organizations/<id>/    — partial update
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return OrganizationDetailSerializer
        return OrganizationSerializer

    def get_queryset(self):
        return get_organization_queryset(self.request)

    def perform_update(self, serializer):
        org = serializer.save()
        logger.info(
            "Organization updated: %s (id=%s) by user=%s",
            org.name,
            org.id,
            self.request.user.id,
        )


class OrganizationStatsView(APIView):
    """
    GET /api/organizations/stats/
    Returns aggregate counts for the dashboard.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        stats = {
            "total_organizations": Organization.objects.count(),
            "active_organizations": Organization.objects.filter(is_active=True).count(),
            "total_restaurants": Restaurant.objects.count(),
            "active_restaurants": Restaurant.objects.filter(is_active=True).count(),
            "total_branches": Branch.objects.count(),
            "active_branches": Branch.objects.filter(is_active=True).count(),
        }
        serializer = OrganizationStatsSerializer(stats)
        return Response(serializer.data)


# =============================================================================
# Restaurant views (nested under Organization)
# =============================================================================

class OrganizationRestaurantListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/organizations/<org_id>/restaurants/
    POST /api/organizations/<org_id>/restaurants/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = RestaurantSerializer

    def _get_organization(self):
        try:
            org = get_organization_queryset(self.request).get(
                pk=self.kwargs["org_id"]
            )
        except Organization.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Organization not found.")
        return org

    def get_queryset(self):
        return get_restaurant_queryset(
            self.request, organization_id=self.kwargs["org_id"]
        )

    def perform_create(self, serializer):
        org = self._get_organization()
        if not org.is_active:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"organization": "Cannot create a restaurant under a disabled organization."}
            )
        restaurant = serializer.save(organization=org)
        # Auto-create settings
        RestaurantSettings.objects.get_or_create(restaurant=restaurant)
        logger.info(
            "Restaurant created: %s (id=%s) under org=%s by user=%s",
            restaurant.name,
            restaurant.id,
            org.id,
            self.request.user.id,
        )


# =============================================================================
# Restaurant views (standalone)
# =============================================================================

class RestaurantListView(generics.ListAPIView):
    """
    GET /api/restaurants/   — list all restaurants across all organizations
    """

    permission_classes = [IsAuthenticated]
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        return get_restaurant_queryset(self.request)


class RestaurantDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/restaurants/<id>/
    PATCH /api/restaurants/<id>/
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return RestaurantDetailSerializer
        return RestaurantSerializer

    def get_queryset(self):
        return get_restaurant_queryset(self.request)

    def perform_update(self, serializer):
        restaurant = serializer.save()
        logger.info(
            "Restaurant updated: %s (id=%s) by user=%s",
            restaurant.name,
            restaurant.id,
            self.request.user.id,
        )


class RestaurantSettingsView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/restaurants/<restaurant_id>/settings/
    PATCH /api/restaurants/<restaurant_id>/settings/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = RestaurantSettingsSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        restaurant_id = self.kwargs["restaurant_id"]
        # Verify restaurant exists and is accessible
        restaurant = generics.get_object_or_404(
            get_restaurant_queryset(self.request), pk=restaurant_id
        )
        settings_obj, _ = RestaurantSettings.objects.get_or_create(
            restaurant=restaurant
        )
        return settings_obj


# =============================================================================
# Branch views (nested under Restaurant)
# =============================================================================

class RestaurantBranchListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/restaurants/<restaurant_id>/branches/
    POST /api/restaurants/<restaurant_id>/branches/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BranchSerializer

    def _get_restaurant(self):
        try:
            return get_restaurant_queryset(self.request).get(
                pk=self.kwargs["restaurant_id"]
            )
        except Restaurant.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Restaurant not found.")

    def get_queryset(self):
        return get_branch_queryset(
            self.request, restaurant_id=self.kwargs["restaurant_id"]
        )

    def perform_create(self, serializer):
        restaurant = self._get_restaurant()
        if not restaurant.is_active:
            from rest_framework.exceptions import ValidationError
            raise ValidationError(
                {"restaurant": "Cannot create a branch under a disabled restaurant."}
            )
        branch = serializer.save(restaurant=restaurant)
        # Auto-create settings
        BranchSettings.objects.get_or_create(branch=branch)
        logger.info(
            "Branch created: %s (id=%s) under restaurant=%s by user=%s",
            branch.name,
            branch.id,
            restaurant.id,
            self.request.user.id,
        )


# =============================================================================
# Branch views (standalone)
# =============================================================================

class BranchListView(generics.ListAPIView):
    """
    GET /api/branches/   — list all branches
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BranchSerializer

    def get_queryset(self):
        return get_branch_queryset(self.request)


class BranchDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/branches/<id>/
    PATCH /api/branches/<id>/
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return BranchDetailSerializer
        return BranchSerializer

    def get_queryset(self):
        return get_branch_queryset(self.request)

    def perform_update(self, serializer):
        branch = serializer.save()
        logger.info(
            "Branch updated: %s (id=%s) by user=%s",
            branch.name,
            branch.id,
            self.request.user.id,
        )


class BranchSettingsView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/branches/<branch_id>/settings/
    PATCH /api/branches/<branch_id>/settings/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = BranchSettingsSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        branch_id = self.kwargs["branch_id"]
        branch = generics.get_object_or_404(
            get_branch_queryset(self.request), pk=branch_id
        )
        settings_obj, _ = BranchSettings.objects.get_or_create(branch=branch)
        return settings_obj
