# =============================================================================
# RestaurantFlow — Marketing Admin
# Phase 18
# =============================================================================

from django.contrib import admin
from marketing.models import (
    MarketingCampaign, CampaignApproval, CampaignAudience,
    CampaignAudienceMember, Promotion, PromotionRule, PromotionUsage,
    CampaignChannel, CampaignMessage, CampaignDelivery,
    CampaignConversion, CampaignEvent, MarketingSettings,
    MarketingContactPolicy, MarketingAuditLog,
)


@admin.register(MarketingCampaign)
class MarketingCampaignAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "campaign_type", "status", "restaurant", "start_at", "end_at"]
    list_filter = ["status", "campaign_type", "restaurant"]
    search_fields = ["name", "code"]
    readonly_fields = ["id", "created_at", "updated_at", "approved_at", "cancelled_at"]
    ordering = ["-created_at"]


@admin.register(CampaignApproval)
class CampaignApprovalAdmin(admin.ModelAdmin):
    list_display = ["campaign", "status", "requested_by", "reviewed_by", "requested_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at", "updated_at", "requested_at", "reviewed_at"]


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "promotion_type", "is_active", "restaurant", "start_at", "end_at"]
    list_filter = ["is_active", "promotion_type", "restaurant"]
    search_fields = ["name", "code"]
    readonly_fields = ["id", "current_usage_count", "created_at", "updated_at"]


@admin.register(PromotionRule)
class PromotionRuleAdmin(admin.ModelAdmin):
    list_display = ["promotion", "rule_type", "priority", "is_active"]
    list_filter = ["rule_type", "is_active"]


@admin.register(PromotionUsage)
class PromotionUsageAdmin(admin.ModelAdmin):
    list_display = ["promotion", "customer", "status", "discount_amount", "used_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CampaignAudience)
class CampaignAudienceAdmin(admin.ModelAdmin):
    list_display = ["campaign", "audience_type", "estimated_count"]
    list_filter = ["audience_type"]


@admin.register(CampaignAudienceMember)
class CampaignAudienceMemberAdmin(admin.ModelAdmin):
    list_display = ["campaign", "customer", "status", "added_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "added_at", "created_at", "updated_at"]


@admin.register(CampaignDelivery)
class CampaignDeliveryAdmin(admin.ModelAdmin):
    list_display = ["campaign", "customer", "channel", "status", "sent_at"]
    list_filter = ["status", "channel"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(CampaignConversion)
class CampaignConversionAdmin(admin.ModelAdmin):
    list_display = ["campaign", "customer", "conversion_type", "conversion_value", "converted_at"]
    list_filter = ["conversion_type"]
    readonly_fields = ["id", "converted_at", "created_at", "updated_at"]


@admin.register(MarketingSettings)
class MarketingSettingsAdmin(admin.ModelAdmin):
    list_display = ["restaurant", "frequency_limit_enabled", "default_daily_contact_limit"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(MarketingContactPolicy)
class MarketingContactPolicyAdmin(admin.ModelAdmin):
    list_display = ["restaurant", "channel", "max_messages_per_day", "max_messages_per_week", "is_active"]
    list_filter = ["channel", "is_active"]


@admin.register(MarketingAuditLog)
class MarketingAuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "entity_id", "actor", "created_at"]
    list_filter = ["action"]
    readonly_fields = [f.name for f in MarketingAuditLog._meta.get_fields()]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
