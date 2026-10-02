# =============================================================================
# RestaurantFlow — Counters Admin
# Phase 4
# =============================================================================

from django.contrib import admin
from .models import Counter, CounterAssignment, Shift, CounterSession


@admin.register(Counter)
class CounterAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "branch", "counter_type", "status", "is_active", "created_at"]
    list_filter = ["status", "counter_type", "is_active"]
    search_fields = ["code", "name", "branch__name"]
    readonly_fields = ["id", "is_active", "created_at", "updated_at"]
    raw_id_fields = ["branch"]


@admin.register(CounterAssignment)
class CounterAssignmentAdmin(admin.ModelAdmin):
    list_display = ["counter", "user", "assigned_by", "assigned_at", "expires_at", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["counter__code", "user__email"]
    readonly_fields = ["id", "assigned_at", "created_at", "updated_at"]
    raw_id_fields = ["counter", "user", "assigned_by"]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["name", "branch", "start_time", "end_time", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "branch__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    raw_id_fields = ["branch"]


@admin.register(CounterSession)
class CounterSessionAdmin(admin.ModelAdmin):
    list_display = [
        "counter", "status", "opened_by", "opened_at", "closed_at",
        "opening_cash", "expected_cash", "actual_cash", "cash_difference",
    ]
    list_filter = ["status"]
    search_fields = ["counter__code", "opened_by__email"]
    readonly_fields = [
        "id", "opened_at", "cash_difference", "created_at", "updated_at",
    ]
    raw_id_fields = ["counter", "shift", "opened_by", "closed_by"]
