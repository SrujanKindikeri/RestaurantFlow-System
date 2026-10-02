# =============================================================================
# RestaurantFlow — Menu URL Configuration
# Phase 5
# =============================================================================

from django.urls import path
from . import views

urlpatterns = [
    # -------------------------------------------------------------------------
    # Tax Rates
    # -------------------------------------------------------------------------
    path("menu/tax-rates/",                    views.TaxRateListCreateView.as_view(),    name="taxrate-list-create"),
    path("menu/tax-rates/<uuid:pk>/",          views.TaxRateDetailView.as_view(),        name="taxrate-detail"),
    path("menu/tax-rates/<uuid:pk>/disable/",  views.TaxRateDisableView.as_view(),       name="taxrate-disable"),
    path("menu/tax-rates/<uuid:pk>/enable/",   views.TaxRateEnableView.as_view(),        name="taxrate-enable"),

    # -------------------------------------------------------------------------
    # Categories
    # -------------------------------------------------------------------------
    path("menu/categories/",                   views.CategoryListCreateView.as_view(),   name="category-list-create"),
    path("menu/categories/<uuid:pk>/",         views.CategoryDetailView.as_view(),       name="category-detail"),
    path("menu/categories/<uuid:pk>/disable/", views.CategoryDisableView.as_view(),      name="category-disable"),
    path("menu/categories/<uuid:pk>/enable/",  views.CategoryEnableView.as_view(),       name="category-enable"),

    # -------------------------------------------------------------------------
    # Menu Items
    # -------------------------------------------------------------------------
    path("menu/items/",                        views.MenuItemListCreateView.as_view(),   name="menuitem-list-create"),
    path("menu/items/<uuid:pk>/",              views.MenuItemDetailView.as_view(),       name="menuitem-detail"),
    path("menu/items/<uuid:pk>/disable/",      views.MenuItemDisableView.as_view(),      name="menuitem-disable"),
    path("menu/items/<uuid:pk>/enable/",       views.MenuItemEnableView.as_view(),       name="menuitem-enable"),

    # -------------------------------------------------------------------------
    # Prices
    # -------------------------------------------------------------------------
    path("menu/prices/",                       views.MenuItemPriceListCreateView.as_view(),    name="menuitem-price-list-create"),
    path("menu/prices/<uuid:pk>/",             views.MenuItemPriceDetailView.as_view(),         name="menuitem-price-detail"),
    path("menu/prices/<uuid:pk>/deactivate/",  views.MenuItemPriceDeactivateView.as_view(),     name="menuitem-price-deactivate"),

    # -------------------------------------------------------------------------
    # Branch Availability
    # -------------------------------------------------------------------------
    path("menu/availability/",                 views.MenuItemBranchListCreateView.as_view(),   name="menuitem-branch-list-create"),
    path("menu/availability/<uuid:pk>/",       views.MenuItemBranchDetailView.as_view(),        name="menuitem-branch-detail"),

    # -------------------------------------------------------------------------
    # Branch Catalog (read-optimized POS endpoint)
    # -------------------------------------------------------------------------
    path("menu/branches/<uuid:pk>/catalog/",   views.BranchCatalogView.as_view(),       name="branch-catalog"),

    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------
    path("menu/dashboard/",                    views.MenuDashboardView.as_view(),        name="menu-dashboard"),
]
