# =============================================================================
# RestaurantFlow — Organizations Views
# Phase 3: Scoped queryset helpers + permission class integration
#
# URL layout:
#   /api/organizations/                     list + create
#   /api/organizations/<id>/                retrieve + partial_update
#   /api/organizations/<id>/restaurants/    list + create restaurants under org
#   /api/organizations/stats/               aggregate dashboard counts
#
#   /api/restaurants/                       list (scoped to user)
#   /api/restaurants/<id>/                  retrieve + partial_update
#   /api/restaurants/<id>/branches/         list + create branches
#   /api/restaurants/<id>/settings/         retrieve + partial_update settings
#
#   /api/branches/                          list (scoped to user)
#   /api/branches/<id>/                     retrieve + partial_update
#   /api/branches/<id>/settings/            retrieve + partial_update settings
#
# Security (Phase 3):
#   - All queryset helpers now filter by user scope via accounts.access.
#   - get_object() always fetches from the scoped queryset — users who know
#     a UUID for a resource they cannot access receive 404, not 403,
#     preventing existence leakage.
#   - OrganizationStatsView returns counts scoped to the user's accessible
#     resources, not global counts.
#   - Superuser / is_staff bypass scope filters as before.
# =============================================================================

import logging
from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from accounts.permissions import HasPermission, HasOrganizationAccess, HasRestaurantAccess, HasBranchAccess

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
# Queryset helpers — Phase 3: scoped to authenticated user
# =============================================================================

def get_organization_queryset(request=None):
    """
    Return the Organizations queryset scoped to the requesting user.

    Superuser / staff  → all organizations (unfiltered).
    Everyone else      → only organizations accessible via their role assignments.
    """
    base_qs = Organization.objects.annotate(
        restaurant_count=Count("restaurants"),
        active_restaurant_count=Count(
            "restaurants", filter=Q(restaurants__is_active=True)
        ),
    )

    if request is None:
        return base_qs

    user = request.user
    if not user or not user.is_authenticated:
        return base_qs.none()

    if user.is_superuser or user.is_staff:
        return base_qs

    # Narrow to organizations accessible to this user
    accessible_ids = acl.get_accessible_organizations(user).values_list("pk", flat=True)
    return base_qs.filter(pk__in=accessible_ids)


def get_restaurant_queryset(request=None, organization_id=None):
    """
    Return the Restaurants queryset scoped to the requesting user.

    organization_id — optional additional filter (for nested URL patterns).
    """
    base_qs = Restaurant.objects.annotate(
        branch_count=Count("branches"),
        active_branch_count=Count("branches", filter=Q(branches__is_active=True)),
    )

    if organization_id:
        base_qs = base_qs.filter(organization_id=organization_id)

    if request is None:
        return base_qs

    user = request.user
    if not user or not user.is_authenticated:
        return base_qs.none()

    if user.is_superuser or user.is_staff:
        return base_qs

    accessible_ids = acl.get_accessible_restaurants(user).values_list("pk", flat=True)
    return base_qs.filter(pk__in=accessible_ids)


def get_branch_queryset(request=None, restaurant_id=None):
    """
    Return the Branches queryset scoped to the requesting user.

    restaurant_id — optional additional filter.
    """
    base_qs = Branch.objects.select_related("restaurant__organization")

    if restaurant_id:
        base_qs = base_qs.filter(restaurant_id=restaurant_id)

    if request is None:
        return base_qs

    user = request.user
    if not user or not user.is_authenticated:
        return base_qs.none()

    if user.is_superuser or user.is_staff:
        return base_qs

    accessible_ids = acl.get_accessible_branches(user).values_list("pk", flat=True)
    return base_qs.filter(pk__in=accessible_ids)


# =============================================================================
# Organization views
# =============================================================================

class OrganizationListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/organizations/   — list accessible organizations
    POST /api/organizations/   — create a new organization (org admins only)
    """

    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("organization.create")()]
        return [IsAuthenticated()]

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
    GET   /api/organizations/<id>/    — retrieve (user must have access)
    PATCH /api/organizations/<id>/    — partial update (requires organization.update)
    """

    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("organization.update")(), HasOrganizationAccess()]
        return [IsAuthenticated(), HasOrganizationAccess()]

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
    Returns counts scoped to the requesting user's accessible resources.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.is_superuser or user.is_staff:
            orgs = Organization.objects.all()
            restaurants = Restaurant.objects.all()
            branches = Branch.objects.all()
        else:
            orgs = acl.get_accessible_organizations(user)
            restaurants = acl.get_accessible_restaurants(user)
            branches = acl.get_accessible_branches(user)

        stats = {
            "total_organizations": orgs.count(),
            "active_organizations": orgs.filter(is_active=True).count(),
            "total_restaurants": restaurants.count(),
            "active_restaurants": restaurants.filter(is_active=True).count(),
            "total_branches": branches.count(),
            "active_branches": branches.filter(is_active=True).count(),
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
            raise NotFound("Organization not found.")
        return org

    def get_queryset(self):
        return get_restaurant_queryset(
            self.request, organization_id=self.kwargs["org_id"]
        )

    def perform_create(self, serializer):
        # Check permission
        if not acl.has_permission(self.request.user, "restaurant.create"):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to create restaurants.")

        org = self._get_organization()
        if not org.is_active:
            raise ValidationError(
                {"organization": "Cannot create a restaurant under a disabled organization."}
            )
        restaurant = serializer.save(organization=org)
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
    """GET /api/restaurants/ — list restaurants scoped to user."""

    permission_classes = [IsAuthenticated]
    serializer_class = RestaurantSerializer

    def get_queryset(self):
        return get_restaurant_queryset(self.request)


class RestaurantDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/restaurants/<id>/
    PATCH /api/restaurants/<id>/
    """

    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("restaurant.update")(), HasRestaurantAccess()]
        return [IsAuthenticated(), HasRestaurantAccess()]

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

    serializer_class = RestaurantSettingsSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("restaurant.update")()]
        return [IsAuthenticated()]

    def get_object(self):
        restaurant_id = self.kwargs["restaurant_id"]
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
            raise NotFound("Restaurant not found.")

    def get_queryset(self):
        return get_branch_queryset(
            self.request, restaurant_id=self.kwargs["restaurant_id"]
        )

    def perform_create(self, serializer):
        if not acl.has_permission(self.request.user, "branch.create"):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to create branches.")

        restaurant = self._get_restaurant()
        if not restaurant.is_active:
            raise ValidationError(
                {"restaurant": "Cannot create a branch under a disabled restaurant."}
            )
        branch = serializer.save(restaurant=restaurant)
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
    """GET /api/branches/ — list branches scoped to user."""

    permission_classes = [IsAuthenticated]
    serializer_class = BranchSerializer

    def get_queryset(self):
        return get_branch_queryset(self.request)


class BranchDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/branches/<id>/
    PATCH /api/branches/<id>/
    """

    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("branch.update")(), HasBranchAccess()]
        return [IsAuthenticated(), HasBranchAccess()]

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

    serializer_class = BranchSettingsSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("branch.update")()]
        return [IsAuthenticated()]

    def get_object(self):
        branch_id = self.kwargs["branch_id"]
        branch = generics.get_object_or_404(
            get_branch_queryset(self.request), pk=branch_id
        )
        settings_obj, _ = BranchSettings.objects.get_or_create(branch=branch)
        return settings_obj
