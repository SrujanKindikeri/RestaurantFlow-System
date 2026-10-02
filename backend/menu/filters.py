# =============================================================================
# RestaurantFlow — Menu Filters
# Phase 5
# =============================================================================

import django_filters
from .models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch


class TaxRateFilter(django_filters.FilterSet):
    restaurant = django_filters.UUIDFilter(field_name="restaurant__id")
    is_active = django_filters.BooleanFilter()
    code = django_filters.CharFilter(lookup_expr="iexact")

    class Meta:
        model = TaxRate
        fields = ["restaurant", "is_active", "code"]


class CategoryFilter(django_filters.FilterSet):
    restaurant = django_filters.UUIDFilter(field_name="restaurant__id")
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = Category
        fields = ["restaurant", "is_active"]


class MenuItemFilter(django_filters.FilterSet):
    restaurant = django_filters.UUIDFilter(field_name="restaurant__id")
    category = django_filters.UUIDFilter(field_name="category__id")
    food_type = django_filters.CharFilter(lookup_expr="iexact")
    is_active = django_filters.BooleanFilter()
    is_available = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = MenuItem
        fields = ["restaurant", "category", "food_type", "is_active", "is_available"]

    def filter_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(name__icontains=value)
            | Q(sku__icontains=value)
            | Q(short_description__icontains=value)
        )


class MenuItemPriceFilter(django_filters.FilterSet):
    menu_item = django_filters.UUIDFilter(field_name="menu_item__id")
    branch = django_filters.UUIDFilter(field_name="branch__id")
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = MenuItemPrice
        fields = ["menu_item", "branch", "is_active"]


class MenuItemBranchFilter(django_filters.FilterSet):
    menu_item = django_filters.UUIDFilter(field_name="menu_item__id")
    branch = django_filters.UUIDFilter(field_name="branch__id")
    is_available = django_filters.BooleanFilter()

    class Meta:
        model = MenuItemBranch
        fields = ["menu_item", "branch", "is_available"]
