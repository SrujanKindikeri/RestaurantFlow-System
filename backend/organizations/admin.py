# =============================================================================
# RestaurantFlow — Organizations Admin
# Phase 2
# =============================================================================

from django.contrib import admin

from .models import Organization, Restaurant, Branch, RestaurantSettings, BranchSettings


# =============================================================================
# Inlines
# =============================================================================

class RestaurantInline(admin.TabularInline):
    model = Restaurant
    extra = 0
    fields = ["name", "code", "city", "is_active"]
    readonly_fields = ["code"]
    show_change_link = True


class BranchInline(admin.TabularInline):
    model = Branch
    extra = 0
    fields = ["name", "code", "city", "is_active"]
    readonly_fields = ["code"]
    show_change_link = True


class RestaurantSettingsInline(admin.StackedInline):
    model = RestaurantSettings
    extra = 0
    fields = [
        "currency",
        "timezone",
        "tax_enabled",
        "default_tax_rate",
        "order_prefix",
        "allow_negative_stock",
        "is_active",
    ]
    can_delete = False


class BranchSettingsInline(admin.StackedInline):
    model = BranchSettings
    extra = 0
    fields = [
        "opening_time",
        "closing_time",
        "default_order_type",
        "is_active",
    ]
    can_delete = False


# =============================================================================
# Organization admin
# =============================================================================

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "slug",
        "city",
        "country",
        "currency",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "country", "currency"]
    search_fields = ["name", "legal_name", "slug", "email", "tax_id"]
    ordering = ["name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]
    inlines = [RestaurantInline]

    fieldsets = (
        (
            "Identity",
            {
                "fields": ("id", "name", "legal_name", "slug", "is_active"),
            },
        ),
        (
            "Contact",
            {
                "fields": ("email", "phone"),
                "classes": ("collapse",),
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "address",
                    "city",
                    "state",
                    "country",
                    "postal_code",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Business Details",
            {
                "fields": ("tax_id", "currency", "timezone"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


# =============================================================================
# Restaurant admin
# =============================================================================

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "organization",
        "city",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "organization"]
    search_fields = ["name", "slug", "code", "email", "organization__name"]
    ordering = ["organization__name", "name"]
    readonly_fields = ["id", "slug", "created_at", "updated_at"]
    inlines = [BranchInline, RestaurantSettingsInline]
    raw_id_fields = ["organization"]

    fieldsets = (
        (
            "Identity",
            {
                "fields": (
                    "id",
                    "organization",
                    "name",
                    "slug",
                    "code",
                    "description",
                    "is_active",
                ),
            },
        ),
        (
            "Contact",
            {
                "fields": ("email", "phone"),
                "classes": ("collapse",),
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "address",
                    "city",
                    "state",
                    "country",
                    "postal_code",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


# =============================================================================
# Branch admin
# =============================================================================

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "code",
        "restaurant",
        "city",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "restaurant__organization"]
    search_fields = ["name", "code", "email", "restaurant__name"]
    ordering = ["restaurant__name", "name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [BranchSettingsInline]
    raw_id_fields = ["restaurant"]

    fieldsets = (
        (
            "Identity",
            {
                "fields": ("id", "restaurant", "name", "code", "is_active"),
            },
        ),
        (
            "Contact",
            {
                "fields": ("email", "phone"),
                "classes": ("collapse",),
            },
        ),
        (
            "Address",
            {
                "fields": (
                    "address",
                    "city",
                    "state",
                    "country",
                    "postal_code",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Geolocation",
            {
                "fields": ("latitude", "longitude"),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )


# =============================================================================
# Settings admins
# =============================================================================

@admin.register(RestaurantSettings)
class RestaurantSettingsAdmin(admin.ModelAdmin):
    list_display = [
        "restaurant",
        "currency",
        "tax_enabled",
        "default_tax_rate",
        "order_prefix",
        "is_active",
    ]
    search_fields = ["restaurant__name"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(BranchSettings)
class BranchSettingsAdmin(admin.ModelAdmin):
    list_display = [
        "branch",
        "opening_time",
        "closing_time",
        "default_order_type",
        "is_active",
    ]
    search_fields = ["branch__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
