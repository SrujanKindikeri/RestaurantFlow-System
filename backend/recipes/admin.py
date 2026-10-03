from django.contrib import admin
from recipes.models import Recipe, RecipeItem, ConsumptionBatch, StockConsumption, BranchConsumptionConfig


class RecipeItemInline(admin.TabularInline):
    model = RecipeItem
    extra = 0
    readonly_fields = ("effective_quantity",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "menu_item", "version", "status", "restaurant", "created_at")
    list_filter = ("status", "restaurant")
    search_fields = ("name", "menu_item__name")
    readonly_fields = ("version", "created_at", "updated_at")
    inlines = [RecipeItemInline]


@admin.register(RecipeItem)
class RecipeItemAdmin(admin.ModelAdmin):
    list_display = ("inventory_item", "recipe", "quantity", "unit", "preparation_loss_percentage")
    list_filter = ("recipe__status",)
    search_fields = ("inventory_item__name", "recipe__name")


@admin.register(ConsumptionBatch)
class ConsumptionBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "branch", "status", "triggered_at", "completed_at")
    list_filter = ("status", "branch")
    readonly_fields = ("idempotency_key", "triggered_at")


@admin.register(StockConsumption)
class StockConsumptionAdmin(admin.ModelAdmin):
    list_display = ("inventory_item", "order", "quantity", "unit", "unit_cost", "total_cost", "status", "consumed_at")
    list_filter = ("status", "branch")
    readonly_fields = ("created_at",)


@admin.register(BranchConsumptionConfig)
class BranchConsumptionConfigAdmin(admin.ModelAdmin):
    list_display = ("branch", "consumption_trigger", "default_consumption_location")
