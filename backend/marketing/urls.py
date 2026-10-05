# =============================================================================
# RestaurantFlow — Marketing URLs
# Phase 18
# =============================================================================

from django.urls import path
from marketing import views

app_name = "marketing"

urlpatterns = [
    # -------------------------------------------------------------------------
    # Dashboard
    # -------------------------------------------------------------------------
    path(
        "marketing/dashboard/",
        views.MarketingDashboardView.as_view(),
        name="dashboard",
    ),

    # -------------------------------------------------------------------------
    # Campaigns
    # -------------------------------------------------------------------------
    path(
        "marketing/campaigns/",
        views.CampaignListCreateView.as_view(),
        name="campaign-list-create",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/",
        views.CampaignDetailView.as_view(),
        name="campaign-detail",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/submit/",
        views.CampaignSubmitView.as_view(),
        name="campaign-submit",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/approve/",
        views.CampaignApproveView.as_view(),
        name="campaign-approve",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/reject/",
        views.CampaignRejectView.as_view(),
        name="campaign-reject",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/schedule/",
        views.CampaignScheduleView.as_view(),
        name="campaign-schedule",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/pause/",
        views.CampaignPauseView.as_view(),
        name="campaign-pause",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/resume/",
        views.CampaignResumeView.as_view(),
        name="campaign-resume",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/cancel/",
        views.CampaignCancelView.as_view(),
        name="campaign-cancel",
    ),

    # -------------------------------------------------------------------------
    # Audience
    # -------------------------------------------------------------------------
    path(
        "marketing/campaigns/<uuid:pk>/audience/",
        views.CampaignAudienceView.as_view(),
        name="campaign-audience",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/audience/generate/",
        views.CampaignAudienceGenerateView.as_view(),
        name="campaign-audience-generate",
    ),
    path(
        "marketing/campaigns/<uuid:pk>/audience/members/",
        views.CampaignAudienceMembersView.as_view(),
        name="campaign-audience-members",
    ),

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------
    path(
        "marketing/campaigns/<uuid:pk>/analytics/",
        views.CampaignAnalyticsView.as_view(),
        name="campaign-analytics",
    ),

    # -------------------------------------------------------------------------
    # Conversions
    # -------------------------------------------------------------------------
    path(
        "marketing/conversions/",
        views.CampaignConversionsView.as_view(),
        name="conversions",
    ),

    # -------------------------------------------------------------------------
    # Promotions
    # -------------------------------------------------------------------------
    path(
        "marketing/promotions/",
        views.PromotionListCreateView.as_view(),
        name="promotion-list-create",
    ),
    path(
        "marketing/promotions/validate/",
        views.PromotionValidateView.as_view(),
        name="promotion-validate",
    ),
    path(
        "marketing/promotions/<uuid:pk>/",
        views.PromotionDetailView.as_view(),
        name="promotion-detail",
    ),
    path(
        "marketing/promotions/<uuid:pk>/activate/",
        views.PromotionActivateView.as_view(),
        name="promotion-activate",
    ),
    path(
        "marketing/promotions/<uuid:pk>/deactivate/",
        views.PromotionDeactivateView.as_view(),
        name="promotion-deactivate",
    ),
    path(
        "marketing/promotions/<uuid:pk>/usage/",
        views.PromotionUsageListView.as_view(),
        name="promotion-usage",
    ),
    path(
        "marketing/promotions/<uuid:pk>/rules/",
        views.PromotionRuleView.as_view(),
        name="promotion-rules",
    ),

    # -------------------------------------------------------------------------
    # Settings
    # -------------------------------------------------------------------------
    path(
        "marketing/settings/",
        views.MarketingSettingsView.as_view(),
        name="settings",
    ),
]
