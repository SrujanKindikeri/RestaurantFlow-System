# =============================================================================
# RestaurantFlow — CRM Admin
# Phase 17
# =============================================================================

from django.contrib import admin
from crm.models import (
    Customer, CustomerPreference, CustomerVisit,
    CustomerTag, CustomerTagAssignment,
    CustomerSegment, CustomerSegmentAssignment,
    LoyaltyProgram, LoyaltyAccount, LoyaltyTransaction,
    LoyaltyReward, RewardRedemption,
    CustomerFeedback, FeedbackModeration,
    CustomerConsent, CustomerConsentHistory,
    CustomerMergeRequest, CRMAuditLog,
    CustomerSequence,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = [
        "customer_number", "effective_display_name", "phone", "email",
        "restaurant", "is_active", "is_blocked",
        "total_orders", "lifetime_spend", "created_at",
    ]
    list_filter = ["is_active", "is_blocked", "restaurant"]
    search_fields = ["customer_number", "first_name", "last_name", "phone", "email"]
    readonly_fields = [
        "id", "customer_number", "company",
        "total_orders", "total_visits", "lifetime_spend",
        "first_order_at", "last_order_at", "last_visit_at",
        "created_at", "updated_at",
    ]
    ordering = ["-created_at"]


@admin.register(CustomerPreference)
class CustomerPreferenceAdmin(admin.ModelAdmin):
    list_display = ["customer", "dietary_preference", "preferred_order_type"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CustomerVisit)
class CustomerVisitAdmin(admin.ModelAdmin):
    list_display = [
        "customer", "visit_number", "branch",
        "visit_type", "status", "visit_started_at",
    ]
    list_filter = ["status", "visit_type"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CustomerTag)
class CustomerTagAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "restaurant", "is_active"]
    list_filter = ["is_active", "restaurant"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CustomerTagAssignment)
class CustomerTagAssignmentAdmin(admin.ModelAdmin):
    list_display = ["customer", "tag", "is_active", "assigned_at"]
    list_filter = ["is_active"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "restaurant", "is_active"]
    list_filter = ["is_active", "restaurant"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = [
        "name", "restaurant", "is_active",
        "points_per_currency_unit", "minimum_redemption_points",
    ]
    list_filter = ["is_active", "restaurant"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(LoyaltyAccount)
class LoyaltyAccountAdmin(admin.ModelAdmin):
    list_display = [
        "customer", "loyalty_program",
        "points_balance", "lifetime_points_earned",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = [
        "loyalty_account", "transaction_type", "points",
        "balance_before", "balance_after", "created_at",
    ]
    list_filter = ["transaction_type"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def has_change_permission(self, request, obj=None):
        return False  # Immutable


@admin.register(LoyaltyReward)
class LoyaltyRewardAdmin(admin.ModelAdmin):
    list_display = [
        "name", "restaurant", "reward_type",
        "points_required", "is_active",
    ]
    list_filter = ["is_active", "reward_type", "restaurant"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(RewardRedemption)
class RewardRedemptionAdmin(admin.ModelAdmin):
    list_display = [
        "customer", "reward", "points_used",
        "status", "reference_code", "redeemed_at",
    ]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CustomerFeedback)
class CustomerFeedbackAdmin(admin.ModelAdmin):
    list_display = [
        "restaurant", "customer", "rating",
        "service_rating", "food_rating", "status", "created_at",
    ]
    list_filter = ["status", "rating", "restaurant"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(FeedbackModeration)
class FeedbackModerationAdmin(admin.ModelAdmin):
    list_display = ["feedback", "reviewed_by", "status", "reviewed_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CustomerConsent)
class CustomerConsentAdmin(admin.ModelAdmin):
    list_display = ["customer", "consent_type", "status", "updated_at"]
    list_filter = ["consent_type", "status"]
    readonly_fields = ["id", "updated_at"]


@admin.register(CustomerConsentHistory)
class CustomerConsentHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "customer", "consent_type",
        "previous_status", "new_status", "source", "changed_at",
    ]
    readonly_fields = ["id", "changed_at"]

    def has_change_permission(self, request, obj=None):
        return False  # Immutable


@admin.register(CustomerMergeRequest)
class CustomerMergeRequestAdmin(admin.ModelAdmin):
    list_display = [
        "source_customer", "target_customer",
        "status", "requested_by", "created_at",
    ]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CRMAuditLog)
class CRMAuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "entity_id", "actor", "created_at"]
    list_filter = ["action"]
    readonly_fields = ["id", "created_at", "updated_at"]

    def has_change_permission(self, request, obj=None):
        return False  # Immutable


@admin.register(CustomerSequence)
class CustomerSequenceAdmin(admin.ModelAdmin):
    list_display = ["restaurant", "last_sequence"]
    readonly_fields = ["id", "created_at", "updated_at"]
