# =============================================================================
# RestaurantFlow — Menu Admin
# Phase 5
# =============================================================================

from django.contrib import admin
from .models import TaxRate, Category, MenuItem, MenuItemPrice, MenuItemBranch


# =============================================================================
# TaxRate
# =============================================================================

@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "rate", "restaurant",
        "is_active", "created_at",
    ]
    list_filter = ["is_active", "restaurant"]
    search_fields = ["code", "name", "description"]
    ordering = ["restaurant", "code"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = [
        ("Identification", {
            "fields": ["id", "restaurant", "code", "name"],
        }),
        ("Rate", {
            "fields": ["rate", "description"],
        }),
        ("Status", {
            "fields": ["is_active"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


# =============================================================================
# Category
# =============================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name", "slug", "restaurant",
        "display_order", "is_active", "created_at",
    ]
    list_filter = ["is_active", "restaurant"]
    search_fields = ["name", "description"]
    ordering = ["restaurant", "display_order", "name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]

    fieldsets = [
        ("Identification", {
            "fields": ["id", "restaurant", "name", "slug"],
        }),
        ("Content", {
            "fields": ["description", "image"],
        }),
        ("Display", {
            "fields": ["display_order", "is_active"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


# =============================================================================
# MenuItem
# =============================================================================

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = [
        "name", "sku", "food_type", "category",
        "restaurant", "is_active", "is_available",
        "preparation_time_minutes", "created_at",
    ]
    list_filter = ["is_active", "is_available", "food_type", "restaurant", "category"]
    search_fields = ["name", "sku", "description", "short_description"]
    ordering = ["restaurant", "category", "display_order", "name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]

    fieldsets = [
        ("Identification", {
            "fields": ["id", "restaurant", "category", "name", "slug", "sku"],
        }),
        ("Content", {
            "fields": ["description", "short_description", "image"],
        }),
        ("Classification", {
            "fields": ["food_type", "tax_rate"],
        }),
        ("Display & Status", {
            "fields": ["display_order", "is_active", "is_available"],
        }),
        ("Operations", {
            "fields": ["preparation_time_minutes"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


# =============================================================================
# MenuItemPrice
# =============================================================================

@admin.register(MenuItemPrice)
class MenuItemPriceAdmin(admin.ModelAdmin):
    list_display = [
        "menu_item", "branch", "price",
        "effective_from", "effective_to",
        "is_active", "created_at",
    ]
    list_filter = ["is_active", "branch", "menu_item__restaurant"]
    search_fields = ["menu_item__name", "menu_item__sku", "branch__name"]
    ordering = ["-effective_from", "-created_at"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = [
        ("Price Record", {
            "fields": ["id", "menu_item", "branch", "price"],
        }),
        ("Effective Period", {
            "fields": ["effective_from", "effective_to", "is_active"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]


# =============================================================================
# MenuItemBranch
# =============================================================================

@admin.register(MenuItemBranch)
class MenuItemBranchAdmin(admin.ModelAdmin):
    list_display = [
        "menu_item", "branch",
        "is_available", "available_from", "available_to",
        "created_at",
    ]
    list_filter = ["is_available", "branch", "menu_item__restaurant"]
    search_fields = ["menu_item__name", "branch__name"]
    ordering = ["menu_item__name", "branch__name"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = [
        ("Availability", {
            "fields": ["id", "menu_item", "branch", "is_available"],
        }),
        ("Time Window", {
            "fields": ["available_from", "available_to"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
