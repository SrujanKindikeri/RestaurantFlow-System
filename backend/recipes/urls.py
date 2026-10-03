# =============================================================================
# RestaurantFlow — Recipes URL Configuration
# Phase 11
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Recipes
    # -------------------------------------------------------------------------
    path("recipes/", views.RecipeListView.as_view(), name="recipe-list"),
    path("recipes/<uuid:pk>/", views.RecipeDetailView.as_view(), name="recipe-detail"),
    path("recipes/<uuid:pk>/activate/", views.RecipeActivateView.as_view(), name="recipe-activate"),
    path("recipes/<uuid:pk>/archive/", views.RecipeArchiveView.as_view(), name="recipe-archive"),
    path("recipes/<uuid:pk>/cost/", views.RecipeCostView.as_view(), name="recipe-cost"),
    path("recipes/menu-item/<uuid:menu_item_id>/", views.RecipesByMenuItemView.as_view(), name="recipe-by-menu-item"),

    # -------------------------------------------------------------------------
    # Recipe Ingredients
    # -------------------------------------------------------------------------
    path("recipes/<uuid:pk>/ingredients/", views.RecipeItemListView.as_view(), name="recipe-ingredient-list"),
    path("recipes/<uuid:pk>/ingredients/<uuid:item_id>/", views.RecipeItemDetailView.as_view(), name="recipe-ingredient-detail"),

    # -------------------------------------------------------------------------
    # Consumption
    # -------------------------------------------------------------------------
    path("consumption/", views.ConsumptionBatchListView.as_view(), name="consumption-list"),
    path("consumption/manual/", views.ManualConsumptionView.as_view(), name="consumption-manual"),
    path("consumption/config/", views.BranchConsumptionConfigView.as_view(), name="consumption-config-update"),
    path("consumption/config/<uuid:branch_id>/", views.BranchConsumptionConfigView.as_view(), name="consumption-config-detail"),
    path("consumption/order/<uuid:order_id>/", views.ConsumptionByOrderView.as_view(), name="consumption-by-order"),
    path("consumption/<uuid:pk>/", views.ConsumptionBatchDetailView.as_view(), name="consumption-detail"),
    path("consumption/<uuid:pk>/reverse/", views.ConsumptionReversalView.as_view(), name="consumption-reverse"),
]
