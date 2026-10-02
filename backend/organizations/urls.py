# =============================================================================
# RestaurantFlow — Organizations URL Configuration
# Phase 2
#
# Mounted at /api/ in config/urls.py, giving final paths of:
#
#   GET    /api/organizations/                           list
#   POST   /api/organizations/                           create
#   GET    /api/organizations/stats/                     aggregate dashboard counts
#   GET    /api/organizations/<id>/                      detail
#   PATCH  /api/organizations/<id>/                      partial update
#   GET    /api/organizations/<id>/restaurants/          list restaurants
#   POST   /api/organizations/<id>/restaurants/          create restaurant
#
#   GET    /api/restaurants/                             list all restaurants
#   GET    /api/restaurants/<id>/                        detail
#   PATCH  /api/restaurants/<id>/                        partial update
#   GET    /api/restaurants/<id>/branches/               list branches
#   POST   /api/restaurants/<id>/branches/               create branch
#   GET    /api/restaurants/<id>/settings/               restaurant settings
#   PATCH  /api/restaurants/<id>/settings/               update settings
#
#   GET    /api/branches/                                list all branches
#   GET    /api/branches/<id>/                           detail
#   PATCH  /api/branches/<id>/                           partial update
#   GET    /api/branches/<id>/settings/                  branch settings
#   PATCH  /api/branches/<id>/settings/                  update settings
# =============================================================================

from django.urls import path

from .views import (
    OrganizationListCreateView,
    OrganizationDetailView,
    OrganizationStatsView,
    OrganizationRestaurantListCreateView,
    RestaurantListView,
    RestaurantDetailView,
    RestaurantSettingsView,
    RestaurantBranchListCreateView,
    BranchListView,
    BranchDetailView,
    BranchSettingsView,
)

urlpatterns = [
    # ------------------------------------------------------------------
    # Organizations
    # ------------------------------------------------------------------
    path(
        "organizations/",
        OrganizationListCreateView.as_view(),
        name="organization-list-create",
    ),
    path(
        "organizations/stats/",
        OrganizationStatsView.as_view(),
        name="organization-stats",
    ),
    path(
        "organizations/<uuid:pk>/",
        OrganizationDetailView.as_view(),
        name="organization-detail",
    ),
    path(
        "organizations/<uuid:org_id>/restaurants/",
        OrganizationRestaurantListCreateView.as_view(),
        name="organization-restaurant-list-create",
    ),
    # ------------------------------------------------------------------
    # Restaurants (standalone)
    # ------------------------------------------------------------------
    path(
        "restaurants/",
        RestaurantListView.as_view(),
        name="restaurant-list",
    ),
    path(
        "restaurants/<uuid:pk>/",
        RestaurantDetailView.as_view(),
        name="restaurant-detail",
    ),
    path(
        "restaurants/<uuid:restaurant_id>/branches/",
        RestaurantBranchListCreateView.as_view(),
        name="restaurant-branch-list-create",
    ),
    path(
        "restaurants/<uuid:restaurant_id>/settings/",
        RestaurantSettingsView.as_view(),
        name="restaurant-settings",
    ),
    # ------------------------------------------------------------------
    # Branches (standalone)
    # ------------------------------------------------------------------
    path(
        "branches/",
        BranchListView.as_view(),
        name="branch-list",
    ),
    path(
        "branches/<uuid:pk>/",
        BranchDetailView.as_view(),
        name="branch-detail",
    ),
    path(
        "branches/<uuid:branch_id>/settings/",
        BranchSettingsView.as_view(),
        name="branch-settings",
    ),
]
