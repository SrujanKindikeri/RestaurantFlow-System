# =============================================================================
# RestaurantFlow — Menu Views
# Phase 5
#
# URL layout (see menu/urls.py):
#
#   GET    /api/menu/tax-rates/              list
#   POST   /api/menu/tax-rates/              create
#   GET    /api/menu/tax-rates/<id>/         retrieve
#   PATCH  /api/menu/tax-rates/<id>/         update
#   POST   /api/menu/tax-rates/<id>/disable/ soft disable
#   POST   /api/menu/tax-rates/<id>/enable/  re-enable
#
#   GET    /api/menu/categories/             list
#   POST   /api/menu/categories/             create
#   GET    /api/menu/categories/<id>/        retrieve
#   PATCH  /api/menu/categories/<id>/        update
#   POST   /api/menu/categories/<id>/disable/
#   POST   /api/menu/categories/<id>/enable/
#
#   GET    /api/menu/items/                  list
#   POST   /api/menu/items/                  create
#   GET    /api/menu/items/<id>/             retrieve (full detail)
#   PATCH  /api/menu/items/<id>/             update
#   POST   /api/menu/items/<id>/disable/
#   POST   /api/menu/items/<id>/enable/
#
#   GET    /api/menu/prices/                 list
#   POST   /api/menu/prices/                 create
#   GET    /api/menu/prices/<id>/            retrieve
#   PATCH  /api/menu/prices/<id>/            update
#   POST   /api/menu/prices/<id>/deactivate/ mark as historical
#
#   GET    /api/menu/availability/           list
#   POST   /api/menu/availability/           create
#   GET    /api/menu/availability/<id>/      retrieve
#   PATCH  /api/menu/availability/<id>/      update
#
#   GET    /api/menu/branches/<id>/catalog/  branch POS catalog (read-optimized)
#   GET    /api/menu/dashboard/              menu management dashboard stats
#
# Security:
#   All list/detail views use scoped querysets via menu.access.
#   get_object() returns 404 (not 403) for inaccessible UUIDs — prevents
#   enumeration (IDOR protection).
# =============================================================================

import logging
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from accounts.permissions import HasPermission

from menu import access as menu_acl
from menu import services
from menu.filters import (
    TaxRateFilter, CategoryFilter, MenuItemFilter,
    MenuItemPriceFilter, MenuItemBranchFilter,
)
from menu.models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch
from menu.permissions import (
    HasTaxRateAccess, HasCategoryAccess, HasMenuItemAccess,
    HasMenuPriceAccess, HasAvailabilityAccess,
)
from menu.serializers import (
    TaxRateSerializer,
    CategorySerializer,
    MenuItemSerializer,
    MenuItemDetailSerializer,
    MenuItemPriceSerializer,
    MenuItemBranchSerializer,
    BranchCatalogSerializer,
)

logger = logging.getLogger("menu")


# =============================================================================
# Helpers
# =============================================================================

def _error(code, message, http_status=400):
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


# =============================================================================
# TaxRate views
# =============================================================================

class TaxRateListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/menu/tax-rates/   — list (scoped to user's accessible restaurants)
    POST /api/menu/tax-rates/   — create (requires tax.create permission)
    """
    filterset_class = TaxRateFilter
    search_fields = ["name", "code", "description"]
    ordering_fields = ["code", "name", "rate", "created_at"]
    ordering = ["code"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("tax.create")()]
        return [IsAuthenticated(), HasPermission("tax.view")()]

    def get_serializer_class(self):
        return TaxRateSerializer

    def get_queryset(self):
        return menu_acl.get_accessible_tax_rates(self.request.user)

    def perform_create(self, serializer):
        restaurant = serializer.validated_data.get("restaurant")
        if restaurant and not acl.can_access_restaurant(self.request.user, restaurant):
            raise PermissionDenied("You do not have access to the specified restaurant.")
        tax_rate = serializer.save()
        logger.info(
            "TaxRate created: %s (id=%s) by user=%s",
            tax_rate.code, tax_rate.pk, self.request.user.email,
        )


class TaxRateDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/menu/tax-rates/<id>/   — retrieve
    PATCH /api/menu/tax-rates/<id>/   — update (requires tax.update)
    """
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("tax.update")(), HasTaxRateAccess()]
        return [IsAuthenticated(), HasPermission("tax.view")(), HasTaxRateAccess()]

    def get_serializer_class(self):
        return TaxRateSerializer

    def get_queryset(self):
        return menu_acl.get_accessible_tax_rates(self.request.user)

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except TaxRate.DoesNotExist:
            raise NotFound("Tax rate not found.")
        self.check_object_permissions(self.request, obj)
        return obj


class TaxRateDisableView(APIView):
    """POST /api/menu/tax-rates/<pk>/disable/"""

    permission_classes = [IsAuthenticated, HasPermission("tax.update")]

    def post(self, request, pk):
        try:
            tax_rate = menu_acl.get_accessible_tax_rates(request.user).get(pk=pk)
        except TaxRate.DoesNotExist:
            raise NotFound("Tax rate not found.")
        tax_rate = services.set_tax_rate_active(request.user, tax_rate, False)
        return Response(TaxRateSerializer(tax_rate).data)


class TaxRateEnableView(APIView):
    """POST /api/menu/tax-rates/<pk>/enable/"""

    permission_classes = [IsAuthenticated, HasPermission("tax.update")]

    def post(self, request, pk):
        try:
            tax_rate = menu_acl.get_accessible_tax_rates(request.user).get(pk=pk)
        except TaxRate.DoesNotExist:
            raise NotFound("Tax rate not found.")
        tax_rate = services.set_tax_rate_active(request.user, tax_rate, True)
        return Response(TaxRateSerializer(tax_rate).data)


# =============================================================================
# Category views
# =============================================================================

class CategoryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/menu/categories/   — list
    POST /api/menu/categories/   — create (requires category.create)
    """
    filterset_class = CategoryFilter
    search_fields = ["name", "description"]
    ordering_fields = ["display_order", "name", "created_at"]
    ordering = ["display_order", "name"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("category.create")()]
        return [IsAuthenticated(), HasPermission("category.view")()]

    def get_serializer_class(self):
        return CategorySerializer

    def get_queryset(self):
        return menu_acl.get_accessible_categories(self.request.user)

    def perform_create(self, serializer):
        restaurant = serializer.validated_data.get("restaurant")
        if restaurant and not acl.can_access_restaurant(self.request.user, restaurant):
            raise PermissionDenied("You do not have access to the specified restaurant.")
        category = serializer.save()
        logger.info(
            "Category created: %s (id=%s) by user=%s",
            category.name, category.pk, self.request.user.email,
        )


class CategoryDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/menu/categories/<id>/
    PATCH /api/menu/categories/<id>/   — requires category.update
    """
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("category.update")(), HasCategoryAccess()]
        return [IsAuthenticated(), HasPermission("category.view")(), HasCategoryAccess()]

    def get_serializer_class(self):
        return CategorySerializer

    def get_queryset(self):
        return menu_acl.get_accessible_categories(self.request.user)

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except Category.DoesNotExist:
            raise NotFound("Category not found.")
        self.check_object_permissions(self.request, obj)
        return obj


class CategoryDisableView(APIView):
    """POST /api/menu/categories/<pk>/disable/"""

    permission_classes = [IsAuthenticated, HasPermission("category.disable")]

    def post(self, request, pk):
        try:
            category = menu_acl.get_accessible_categories(request.user).get(pk=pk)
        except Category.DoesNotExist:
            raise NotFound("Category not found.")
        category = services.set_category_active(request.user, category, False)
        return Response(CategorySerializer(category).data)


class CategoryEnableView(APIView):
    """POST /api/menu/categories/<pk>/enable/"""

    permission_classes = [IsAuthenticated, HasPermission("category.create")]

    def post(self, request, pk):
        try:
            category = menu_acl.get_accessible_categories(request.user).get(pk=pk)
        except Category.DoesNotExist:
            raise NotFound("Category not found.")
        category = services.set_category_active(request.user, category, True)
        return Response(CategorySerializer(category).data)


# =============================================================================
# MenuItem views
# =============================================================================

class MenuItemListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/menu/items/   — list
    POST /api/menu/items/   — create (requires menu.create)
    """
    filterset_class = MenuItemFilter
    search_fields = ["name", "sku", "description", "short_description"]
    ordering_fields = ["display_order", "name", "food_type", "created_at"]
    ordering = ["display_order", "name"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("menu.create")()]
        return [IsAuthenticated(), HasPermission("menu.view")()]

    def get_serializer_class(self):
        return MenuItemSerializer

    def get_queryset(self):
        return menu_acl.get_accessible_menu_items(self.request.user)

    def perform_create(self, serializer):
        restaurant = serializer.validated_data.get("restaurant")
        if restaurant and not acl.can_access_restaurant(self.request.user, restaurant):
            raise PermissionDenied("You do not have access to the specified restaurant.")
        item = serializer.save()
        logger.info(
            "MenuItem created: %s (id=%s) by user=%s",
            item.name, item.pk, self.request.user.email,
        )


class MenuItemDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/menu/items/<id>/   — full detail with prices + availability
    PATCH /api/menu/items/<id>/   — update (requires menu.update)
    """
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("menu.update")(), HasMenuItemAccess()]
        return [IsAuthenticated(), HasPermission("menu.view")(), HasMenuItemAccess()]

    def get_serializer_class(self):
        if self.request.method == "GET":
            return MenuItemDetailSerializer
        return MenuItemSerializer

    def get_queryset(self):
        return menu_acl.get_accessible_menu_items(self.request.user)

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except MenuItem.DoesNotExist:
            raise NotFound("Menu item not found.")
        self.check_object_permissions(self.request, obj)
        return obj


class MenuItemDisableView(APIView):
    """POST /api/menu/items/<pk>/disable/"""

    permission_classes = [IsAuthenticated, HasPermission("menu.disable")]

    def post(self, request, pk):
        try:
            item = menu_acl.get_accessible_menu_items(request.user).get(pk=pk)
        except MenuItem.DoesNotExist:
            raise NotFound("Menu item not found.")
        item = services.set_item_active(request.user, item, False)
        return Response(MenuItemSerializer(item).data)


class MenuItemEnableView(APIView):
    """POST /api/menu/items/<pk>/enable/"""

    permission_classes = [IsAuthenticated, HasPermission("menu.create")]

    def post(self, request, pk):
        try:
            item = menu_acl.get_accessible_menu_items(request.user).get(pk=pk)
        except MenuItem.DoesNotExist:
            raise NotFound("Menu item not found.")
        item = services.set_item_active(request.user, item, True)
        return Response(MenuItemSerializer(item).data)


# =============================================================================
# MenuItemPrice views
# =============================================================================

class MenuItemPriceListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/menu/prices/   — list
    POST /api/menu/prices/   — create (requires menu.price.create)
    """
    filterset_class = MenuItemPriceFilter
    ordering_fields = ["effective_from", "created_at", "price"]
    ordering = ["-effective_from", "-created_at"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("menu.price.create")()]
        return [IsAuthenticated(), HasPermission("menu.price.view")()]

    def get_serializer_class(self):
        return MenuItemPriceSerializer

    def get_queryset(self):
        return menu_acl.get_accessible_prices(self.request.user)

    def perform_create(self, serializer):
        menu_item = serializer.validated_data.get("menu_item")
        branch = serializer.validated_data.get("branch")

        if menu_item and not acl.can_access_restaurant(
            self.request.user, menu_item.restaurant
        ):
            raise PermissionDenied("You do not have access to this menu item's restaurant.")

        if branch and not acl.can_access_branch(self.request.user, branch):
            raise PermissionDenied("You do not have access to the specified branch.")

        price = serializer.save()
        logger.info(
            "MenuItemPrice created: item=%s branch=%s price=%s by user=%s",
            price.menu_item.name, price.branch.name,
            price.price, self.request.user.email,
        )


class MenuItemPriceDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/menu/prices/<id>/
    PATCH /api/menu/prices/<id>/   — requires menu.price.update
    """
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("menu.price.update")(), HasMenuPriceAccess()]
        return [IsAuthenticated(), HasPermission("menu.price.view")(), HasMenuPriceAccess()]

    def get_serializer_class(self):
        return MenuItemPriceSerializer

    def get_queryset(self):
        return menu_acl.get_accessible_prices(self.request.user)

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except MenuItemPrice.DoesNotExist:
            raise NotFound("Menu item price not found.")
        self.check_object_permissions(self.request, obj)
        return obj


class MenuItemPriceDeactivateView(APIView):
    """POST /api/menu/prices/<pk>/deactivate/ — mark as historical."""

    permission_classes = [IsAuthenticated, HasPermission("menu.price.update")]

    def post(self, request, pk):
        try:
            price = menu_acl.get_accessible_prices(request.user).get(pk=pk)
        except MenuItemPrice.DoesNotExist:
            raise NotFound("Menu item price not found.")
        if not menu_acl.can_access_restaurant_menu(request.user, price.menu_item.restaurant):
            raise NotFound("Menu item price not found.")
        price = services.deactivate_price(request.user, price)
        return Response(MenuItemPriceSerializer(price).data)


# =============================================================================
# MenuItemBranch (availability) views
# =============================================================================

class MenuItemBranchListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/menu/availability/   — list
    POST /api/menu/availability/   — create (requires menu.availability.update)
    """
    filterset_class = MenuItemBranchFilter
    ordering_fields = ["created_at"]
    ordering = ["menu_item__name", "branch__name"]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("menu.availability.update")()]
        return [IsAuthenticated(), HasPermission("menu.availability.view")()]

    def get_serializer_class(self):
        return MenuItemBranchSerializer

    def get_queryset(self):
        return menu_acl.get_accessible_branch_availability(self.request.user)

    def perform_create(self, serializer):
        menu_item = serializer.validated_data.get("menu_item")
        branch = serializer.validated_data.get("branch")

        if menu_item and not acl.can_access_restaurant(
            self.request.user, menu_item.restaurant
        ):
            raise PermissionDenied("You do not have access to this menu item's restaurant.")

        if branch and not acl.can_access_branch(self.request.user, branch):
            raise PermissionDenied("You do not have access to the specified branch.")

        avail = serializer.save()
        logger.info(
            "MenuItemBranch created: item=%s branch=%s available=%s by user=%s",
            avail.menu_item.name, avail.branch.name,
            avail.is_available, self.request.user.email,
        )


class MenuItemBranchDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/menu/availability/<id>/
    PATCH /api/menu/availability/<id>/   — requires menu.availability.update
    """
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [
                IsAuthenticated(),
                HasPermission("menu.availability.update")(),
                HasAvailabilityAccess(),
            ]
        return [
            IsAuthenticated(),
            HasPermission("menu.availability.view")(),
            HasAvailabilityAccess(),
        ]

    def get_serializer_class(self):
        return MenuItemBranchSerializer

    def get_queryset(self):
        return menu_acl.get_accessible_branch_availability(self.request.user)

    def get_object(self):
        pk = self.kwargs["pk"]
        try:
            obj = self.get_queryset().get(pk=pk)
        except MenuItemBranch.DoesNotExist:
            raise NotFound("Availability record not found.")
        self.check_object_permissions(self.request, obj)
        return obj


# =============================================================================
# Branch Catalog (read-optimized for POS)
# =============================================================================

class BranchCatalogView(APIView):
    """
    GET /api/menu/branches/<branch_id>/catalog/

    Returns the branch-specific catalog: only active categories containing
    active + available menu items, with branch-specific price and tax info.

    Security:
        - User must be able to access the specified branch.
        - Cashiers and waiters can call this.
        - Internal costs, margins, and supplier data are never included.
    """

    permission_classes = [IsAuthenticated, HasPermission("menu.view")]

    def get(self, request, pk):
        from organizations.models import Branch

        try:
            branch = acl.get_accessible_branches(request.user).get(pk=pk)
        except Branch.DoesNotExist:
            raise NotFound("Branch not found.")

        try:
            catalog = services.get_branch_catalog(branch, request.user)
        except PermissionDenied as e:
            raise e

        return Response(catalog)


# =============================================================================
# Menu Dashboard
# =============================================================================

class MenuDashboardView(APIView):
    """
    GET /api/menu/dashboard/

    Returns summary statistics for the menu management dashboard.
    Scoped to the requesting user's accessible restaurants.
    """

    permission_classes = [IsAuthenticated, HasPermission("menu.view")]

    def get(self, request):
        restaurant_ids = acl.get_accessible_restaurants(request.user).values_list(
            "pk", flat=True
        )
        branch_ids = acl.get_accessible_branches(request.user).values_list(
            "pk", flat=True
        )

        categories_qs = Category.objects.filter(restaurant_id__in=restaurant_ids)
        items_qs = MenuItem.objects.filter(restaurant_id__in=restaurant_ids)
        availability_qs = MenuItemBranch.objects.filter(
            branch_id__in=branch_ids,
            menu_item__restaurant_id__in=restaurant_ids,
        )

        # Branch breakdown
        from organizations.models import Branch
        branches = acl.get_accessible_branches(request.user).filter(is_active=True)
        branch_stats = []
        for branch in branches:
            available_count = availability_qs.filter(
                branch=branch,
                is_available=True,
                menu_item__is_active=True,
            ).count()
            branch_stats.append({
                "id": str(branch.pk),
                "name": branch.name,
                "restaurant_name": branch.restaurant.name,
                "available_items": available_count,
            })

        return Response({
            "categories": {
                "total": categories_qs.count(),
                "active": categories_qs.filter(is_active=True).count(),
                "inactive": categories_qs.filter(is_active=False).count(),
            },
            "items": {
                "total": items_qs.count(),
                "active": items_qs.filter(is_active=True).count(),
                "inactive": items_qs.filter(is_active=False).count(),
                "available": items_qs.filter(is_active=True, is_available=True).count(),
                "unavailable": items_qs.filter(is_active=True, is_available=False).count(),
            },
            "branches": branch_stats,
        })
