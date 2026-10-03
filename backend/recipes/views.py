# =============================================================================
# RestaurantFlow — Recipe Views
# Phase 11
#
# Security:
#   - All querysets scoped via recipes.access — IDOR prevention.
#   - Every action validates permission codes (never role names).
#   - 404 returned for unauthorized UUIDs.
# =============================================================================

import logging

from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts import access as acl
from recipes import access as rec_acl
from recipes import services, selectors
from recipes.models import (
    Recipe, RecipeItem, ConsumptionBatch, StockConsumption, BranchConsumptionConfig
)
from recipes.permissions import HasPermission
from recipes.serializers import (
    RecipeListSerializer,
    RecipeDetailSerializer,
    CreateRecipeSerializer,
    UpdateRecipeSerializer,
    RecipeItemSerializer,
    AddRecipeItemSerializer,
    UpdateRecipeItemSerializer,
    ConsumptionBatchListSerializer,
    ConsumptionBatchDetailSerializer,
    StockConsumptionSerializer,
    ManualConsumptionSerializer,
    ReversalSerializer,
    BranchConsumptionConfigSerializer,
    UpdateBranchConsumptionConfigSerializer,
)

logger = logging.getLogger("recipes")


# =============================================================================
# Helpers
# =============================================================================

def _error(code, message, http_status=400):
    return Response(
        {"error": True, "code": code, "message": message},
        status=http_status,
    )


def _service_error(exc, fallback_code="REQUEST_FAILED"):
    from rest_framework.exceptions import ValidationError, PermissionDenied as DRFPerm
    err = getattr(exc, "detail", None)
    if isinstance(err, dict):
        code = err.get("code", fallback_code)
        message = err.get("message", str(exc))
        http_status = (
            status.HTTP_403_FORBIDDEN if isinstance(exc, DRFPerm)
            else status.HTTP_400_BAD_REQUEST
        )
        return Response({"error": True, "code": code, "message": message}, status=http_status)
    http_status = (
        status.HTTP_403_FORBIDDEN if isinstance(exc, DRFPerm)
        else status.HTTP_400_BAD_REQUEST
    )
    return Response({"error": True, "code": fallback_code, "message": str(exc)}, status=http_status)


def _get_or_404(qs, pk, label):
    try:
        return qs.get(pk=pk)
    except Exception:
        raise NotFound(f"{label} {pk} not found.")


# =============================================================================
# Recipe List + Create
# =============================================================================

class RecipeListView(APIView):
    """
    GET  /api/recipes/          — list recipes (filterable)
    POST /api/recipes/          — create DRAFT recipe
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("recipe.create")()]
        return [IsAuthenticated(), HasPermission("recipe.view")()]

    def get(self, request):
        from django.db.models import Count
        qs = rec_acl.get_accessible_recipes(request.user).annotate(
            ingredient_count=Count("items")
        ).select_related("menu_item", "restaurant", "created_by", "approved_by")

        params = request.query_params
        if params.get("restaurant"):
            qs = qs.filter(restaurant_id=params["restaurant"])
        if params.get("menu_item"):
            qs = qs.filter(menu_item_id=params["menu_item"])
        if params.get("status"):
            qs = qs.filter(status=params["status"].upper())
        if params.get("search"):
            from django.db.models import Q
            qs = qs.filter(
                Q(name__icontains=params["search"]) |
                Q(menu_item__name__icontains=params["search"])
            )

        return Response(RecipeListSerializer(qs, many=True).data)

    def post(self, request):
        from menu.models import MenuItem
        from organizations.models import Restaurant

        serializer = CreateRecipeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            restaurant = Restaurant.objects.get(pk=d["restaurant_id"])
        except Restaurant.DoesNotExist:
            return _error("NOT_FOUND", "Restaurant not found.", 404)

        try:
            menu_item = MenuItem.objects.get(pk=d["menu_item_id"])
        except MenuItem.DoesNotExist:
            return _error("NOT_FOUND", "Menu item not found.", 404)

        try:
            recipe = services.create_recipe(
                restaurant=restaurant,
                menu_item=menu_item,
                name=d["name"],
                user=request.user,
                yield_quantity=d.get("yield_quantity", "1.000"),
                yield_unit=d.get("yield_unit", "PIECE"),
                preparation_notes=d.get("preparation_notes", ""),
                effective_from=d.get("effective_from"),
                effective_to=d.get("effective_to"),
            )
        except Exception as exc:
            return _service_error(exc)

        return Response(RecipeDetailSerializer(recipe).data, status=201)


# =============================================================================
# Recipe Detail + Update
# =============================================================================

class RecipeDetailView(APIView):
    """
    GET   /api/recipes/{id}/  — get recipe detail
    PATCH /api/recipes/{id}/  — update DRAFT recipe metadata
    """

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("recipe.update")()]
        return [IsAuthenticated(), HasPermission("recipe.view")()]

    def _get_recipe(self, request, pk):
        from django.db.models import Count
        qs = rec_acl.get_accessible_recipes(request.user).annotate(
            ingredient_count=Count("items")
        ).prefetch_related("items__inventory_item")
        return _get_or_404(qs, pk, "Recipe")

    def get(self, request, pk):
        recipe = self._get_recipe(request, pk)
        return Response(RecipeDetailSerializer(recipe).data)

    def patch(self, request, pk):
        recipe = self._get_recipe(request, pk)
        serializer = UpdateRecipeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        try:
            updated = services.update_recipe(recipe, request.user, **serializer.validated_data)
        except Exception as exc:
            return _service_error(exc)

        from django.db.models import Count
        updated = Recipe.objects.annotate(ingredient_count=Count("items")).prefetch_related(
            "items__inventory_item"
        ).get(pk=updated.pk)
        return Response(RecipeDetailSerializer(updated).data)


# =============================================================================
# Recipe Activate
# =============================================================================

class RecipeActivateView(APIView):
    """POST /api/recipes/{id}/activate/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("recipe.activate")()]

    def post(self, request, pk):
        qs = rec_acl.get_accessible_recipes(request.user)
        recipe = _get_or_404(qs, pk, "Recipe")
        try:
            activated = services.activate_recipe(recipe, request.user)
        except Exception as exc:
            return _service_error(exc)

        from django.db.models import Count
        activated = Recipe.objects.annotate(ingredient_count=Count("items")).prefetch_related(
            "items__inventory_item"
        ).get(pk=activated.pk)
        return Response(RecipeDetailSerializer(activated).data)


# =============================================================================
# Recipe Archive
# =============================================================================

class RecipeArchiveView(APIView):
    """POST /api/recipes/{id}/archive/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("recipe.archive")()]

    def post(self, request, pk):
        qs = rec_acl.get_accessible_recipes(request.user)
        recipe = _get_or_404(qs, pk, "Recipe")
        try:
            archived = services.archive_recipe(recipe, request.user)
        except Exception as exc:
            return _service_error(exc)

        from django.db.models import Count
        archived = Recipe.objects.annotate(ingredient_count=Count("items")).prefetch_related(
            "items__inventory_item"
        ).get(pk=archived.pk)
        return Response(RecipeDetailSerializer(archived).data)


# =============================================================================
# Recipe Cost
# =============================================================================

class RecipeCostView(APIView):
    """GET /api/recipes/{id}/cost/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("recipe.cost.view")()]

    def get(self, request, pk):
        qs = rec_acl.get_accessible_recipes(request.user).prefetch_related("items__inventory_item")
        recipe = _get_or_404(qs, pk, "Recipe")
        cost_data = services.calculate_recipe_cost(recipe)
        return Response(cost_data)


# =============================================================================
# Recipes by Menu Item
# =============================================================================

class RecipesByMenuItemView(APIView):
    """GET /api/recipes/menu-item/{menu_item_id}/  — recipe history for a menu item"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("recipe.view")()]

    def get(self, request, menu_item_id):
        from menu.models import MenuItem
        from django.db.models import Count

        try:
            menu_item = MenuItem.objects.get(pk=menu_item_id)
        except MenuItem.DoesNotExist:
            return _error("NOT_FOUND", "Menu item not found.", 404)

        if not acl.can_access_restaurant(request.user, menu_item.restaurant):
            return _error("FORBIDDEN", "You do not have access to this menu item.", 403)

        qs = selectors.get_recipe_versions_for_menu_item(menu_item).annotate(
            ingredient_count=Count("items")
        )
        return Response(RecipeListSerializer(qs, many=True).data)


# =============================================================================
# Recipe Items (ingredients)
# =============================================================================

class RecipeItemListView(APIView):
    """
    GET  /api/recipes/{id}/ingredients/  — list ingredients
    POST /api/recipes/{id}/ingredients/  — add ingredient
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated(), HasPermission("recipe.update")()]
        return [IsAuthenticated(), HasPermission("recipe.view")()]

    def _get_recipe(self, request, pk):
        return _get_or_404(rec_acl.get_accessible_recipes(request.user), pk, "Recipe")

    def get(self, request, pk):
        recipe = self._get_recipe(request, pk)
        items = recipe.items.select_related("inventory_item").order_by("display_order")
        return Response(RecipeItemSerializer(items, many=True).data)

    def post(self, request, pk):
        recipe = self._get_recipe(request, pk)
        serializer = AddRecipeItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            item = services.add_recipe_item(
                recipe=recipe,
                inventory_item_id=d["inventory_item_id"],
                quantity=d["quantity"],
                unit=d["unit"],
                user=request.user,
                preparation_loss_percentage=d.get("preparation_loss_percentage", "0"),
                notes=d.get("notes", ""),
                display_order=d.get("display_order", 0),
            )
        except Exception as exc:
            return _service_error(exc)

        return Response(RecipeItemSerializer(item).data, status=201)


class RecipeItemDetailView(APIView):
    """
    PATCH  /api/recipes/{id}/ingredients/{item_id}/  — update ingredient
    DELETE /api/recipes/{id}/ingredients/{item_id}/  — remove ingredient
    """

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("recipe.update")()]

    def _get_item(self, request, pk, item_id):
        recipe = _get_or_404(rec_acl.get_accessible_recipes(request.user), pk, "Recipe")
        try:
            return recipe.items.select_related("inventory_item").get(pk=item_id)
        except RecipeItem.DoesNotExist:
            raise NotFound(f"Recipe ingredient {item_id} not found.")

    def patch(self, request, pk, item_id):
        item = self._get_item(request, pk, item_id)
        serializer = UpdateRecipeItemSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        try:
            updated = services.update_recipe_item(item, request.user, **serializer.validated_data)
        except Exception as exc:
            return _service_error(exc)
        return Response(RecipeItemSerializer(updated).data)

    def delete(self, request, pk, item_id):
        item = self._get_item(request, pk, item_id)
        try:
            services.remove_recipe_item(item, request.user)
        except Exception as exc:
            return _service_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Consumption Batches
# =============================================================================

class ConsumptionBatchListView(APIView):
    """GET /api/consumption/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.consumption.view")()]

    def get(self, request):
        qs = rec_acl.get_accessible_consumption_batches(request.user).select_related(
            "order", "branch", "triggered_by"
        ).prefetch_related("consumptions")

        params = request.query_params
        if params.get("branch"):
            qs = qs.filter(branch_id=params["branch"])
        if params.get("status"):
            qs = qs.filter(status=params["status"].upper())
        if params.get("date"):
            qs = qs.filter(triggered_at__date=params["date"])
        if params.get("order"):
            qs = qs.filter(order_id=params["order"])

        return Response(ConsumptionBatchListSerializer(qs, many=True).data)


class ConsumptionBatchDetailView(APIView):
    """GET /api/consumption/{id}/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.consumption.view")()]

    def get(self, request, pk):
        qs = rec_acl.get_accessible_consumption_batches(request.user).select_related(
            "order", "branch", "triggered_by"
        ).prefetch_related(
            "consumptions__inventory_item",
            "consumptions__storage_location",
            "consumptions__order_item",
        )
        batch = _get_or_404(qs, pk, "ConsumptionBatch")
        return Response(ConsumptionBatchDetailSerializer(batch).data)


class ConsumptionByOrderView(APIView):
    """GET /api/consumption/order/{order_id}/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.consumption.view")()]

    def get(self, request, order_id):
        from orders.models import Order

        try:
            order = Order.objects.get(pk=order_id)
        except Order.DoesNotExist:
            return _error("NOT_FOUND", "Order not found.", 404)

        if not acl.can_access_branch(request.user, order.branch):
            return _error("FORBIDDEN", "You do not have access to this order's branch.", 403)

        batches = selectors.get_consumption_batches_for_order(order).prefetch_related(
            "consumptions__inventory_item", "consumptions__storage_location"
        )
        return Response(ConsumptionBatchDetailSerializer(batches, many=True).data)


# =============================================================================
# Manual Consumption
# =============================================================================

class ManualConsumptionView(APIView):
    """POST /api/consumption/manual/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.consumption.manual")()]

    def post(self, request):
        from organizations.models import Branch
        from inventory.models import InventoryItem, StorageLocation

        serializer = ManualConsumptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            branch = Branch.objects.get(pk=d["branch_id"])
        except Branch.DoesNotExist:
            return _error("NOT_FOUND", "Branch not found.", 404)

        try:
            inventory_item = InventoryItem.objects.get(pk=d["inventory_item_id"])
        except InventoryItem.DoesNotExist:
            return _error("NOT_FOUND", "Inventory item not found.", 404)

        try:
            storage_location = StorageLocation.objects.get(pk=d["storage_location_id"])
        except StorageLocation.DoesNotExist:
            return _error("NOT_FOUND", "Storage location not found.", 404)

        try:
            consumption = services.manual_consume(
                branch=branch,
                inventory_item=inventory_item,
                storage_location=storage_location,
                quantity=d["quantity"],
                unit=d["unit"],
                reason=d["reason"],
                user=request.user,
            )
        except Exception as exc:
            return _service_error(exc)

        return Response(StockConsumptionSerializer(consumption).data, status=201)


# =============================================================================
# Consumption Reversal
# =============================================================================

class ConsumptionReversalView(APIView):
    """POST /api/consumption/{id}/reverse/"""

    def get_permissions(self):
        return [IsAuthenticated(), HasPermission("inventory.consumption.reverse")()]

    def post(self, request, pk):
        qs = rec_acl.get_accessible_consumption_batches(request.user)
        batch = _get_or_404(qs, pk, "ConsumptionBatch")

        serializer = ReversalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)

        try:
            reversed_batch = services.reverse_consumption_batch(
                batch, request.user, reason=serializer.validated_data.get("reason", "")
            )
        except Exception as exc:
            return _service_error(exc)

        return Response(ConsumptionBatchDetailSerializer(reversed_batch).data)


# =============================================================================
# Branch Consumption Config
# =============================================================================

class BranchConsumptionConfigView(APIView):
    """
    GET   /api/consumption/config/{branch_id}/  — get branch config
    PATCH /api/consumption/config/              — create/update branch config
    """

    def get_permissions(self):
        if self.request.method == "PATCH":
            return [IsAuthenticated(), HasPermission("inventory.update")()]
        return [IsAuthenticated(), HasPermission("inventory.view")()]

    def get(self, request, branch_id):
        from organizations.models import Branch

        try:
            branch = Branch.objects.get(pk=branch_id)
        except Branch.DoesNotExist:
            return _error("NOT_FOUND", "Branch not found.", 404)

        if not acl.can_access_branch(request.user, branch):
            return _error("FORBIDDEN", "You do not have access to this branch.", 403)

        config = selectors.get_branch_consumption_config(branch)
        if config is None:
            return Response({
                "branch": str(branch.id),
                "branch_name": branch.name,
                "consumption_trigger": "KITCHEN_COMPLETED",
                "default_consumption_location": None,
                "location_name": None,
                "message": "No config found — defaults apply.",
            })
        return Response(BranchConsumptionConfigSerializer(config).data)

    def patch(self, request):
        from organizations.models import Branch
        from inventory.models import StorageLocation

        serializer = UpdateBranchConsumptionConfigSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": True, "details": serializer.errors}, status=400)
        d = serializer.validated_data

        try:
            branch = Branch.objects.get(pk=d["branch_id"])
        except Branch.DoesNotExist:
            return _error("NOT_FOUND", "Branch not found.", 404)

        location = None
        if d.get("default_consumption_location_id"):
            try:
                location = StorageLocation.objects.get(pk=d["default_consumption_location_id"])
            except StorageLocation.DoesNotExist:
                return _error("NOT_FOUND", "Storage location not found.", 404)

        try:
            config = services.get_or_create_branch_config(
                branch=branch,
                user=request.user,
                consumption_trigger=d.get("consumption_trigger"),
                default_consumption_location=location,
            )
        except Exception as exc:
            return _service_error(exc)

        return Response(BranchConsumptionConfigSerializer(config).data)
