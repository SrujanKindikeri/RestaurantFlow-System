# =============================================================================
# RestaurantFlow — CRM URL Configuration
# Phase 17
# =============================================================================

from django.urls import path

from crm.views import (
    CustomerListCreateView,
    CustomerDetailView,
    CustomerSearchView,
    CustomerOrderHistoryView,
    CustomerVisitHistoryView,
    CustomerSpendingView,
    CustomerTagsView,
    CustomerTagDeleteView,
    CustomerLoyaltyView,
    CustomerRewardsView,
    RewardRedeemView,
    LoyaltyProgramView,
    RewardListCreateView,
    RewardDetailView,
    SegmentListCreateView,
    SegmentDetailView,
    FeedbackListCreateView,
    FeedbackDetailView,
    FeedbackModerateView,
    ConsentListView,
    CustomerMergeRequestListCreateView,
    CustomerMergeApproveView,
    CustomerMergeRejectView,
    CRMDashboardView,
    CustomerPreferenceView,
)

app_name = "crm"

urlpatterns = [
    # Dashboard
    path("crm/dashboard/", CRMDashboardView.as_view(), name="dashboard"),

    # Customer CRUD + search
    path("crm/customers/",         CustomerListCreateView.as_view(), name="customer-list"),
    path("crm/customers/search/",  CustomerSearchView.as_view(),     name="customer-search"),
    path("crm/customers/<uuid:pk>/", CustomerDetailView.as_view(),   name="customer-detail"),

    # Customer sub-resources
    path("crm/customers/<uuid:pk>/orders/",      CustomerOrderHistoryView.as_view(), name="customer-orders"),
    path("crm/customers/<uuid:pk>/visits/",      CustomerVisitHistoryView.as_view(), name="customer-visits"),
    path("crm/customers/<uuid:pk>/spending/",    CustomerSpendingView.as_view(),     name="customer-spending"),
    path("crm/customers/<uuid:pk>/loyalty/",     CustomerLoyaltyView.as_view(),      name="customer-loyalty"),
    path("crm/customers/<uuid:pk>/rewards/",     CustomerRewardsView.as_view(),      name="customer-rewards"),
    path("crm/customers/<uuid:pk>/tags/",        CustomerTagsView.as_view(),         name="customer-tags"),
    path("crm/customers/<uuid:pk>/tags/<uuid:tag_id>/", CustomerTagDeleteView.as_view(), name="customer-tag-delete"),
    path("crm/customers/<uuid:pk>/preferences/", CustomerPreferenceView.as_view(),   name="customer-preferences"),

    # Reward redemption
    path(
        "crm/customers/<uuid:pk>/rewards/<uuid:reward_id>/redeem/",
        RewardRedeemView.as_view(),
        name="reward-redeem",
    ),

    # Segments
    path("crm/segments/",         SegmentListCreateView.as_view(), name="segment-list"),
    path("crm/segments/<uuid:pk>/", SegmentDetailView.as_view(),   name="segment-detail"),

    # Loyalty programs
    path("crm/loyalty/program/", LoyaltyProgramView.as_view(), name="loyalty-program"),

    # Rewards (management)
    path("crm/rewards/",           RewardListCreateView.as_view(), name="reward-list"),
    path("crm/rewards/<uuid:pk>/", RewardDetailView.as_view(),     name="reward-detail"),

    # Feedback
    path("crm/feedback/",           FeedbackListCreateView.as_view(), name="feedback-list"),
    path("crm/feedback/<uuid:pk>/", FeedbackDetailView.as_view(),     name="feedback-detail"),
    path("crm/feedback/<uuid:pk>/moderate/", FeedbackModerateView.as_view(), name="feedback-moderate"),

    # Consents
    path("crm/consents/", ConsentListView.as_view(), name="consent-list"),

    # Merge requests
    path("crm/customer-merge-requests/",             CustomerMergeRequestListCreateView.as_view(), name="merge-list"),
    path("crm/customer-merge-requests/<uuid:pk>/approve/", CustomerMergeApproveView.as_view(),     name="merge-approve"),
    path("crm/customer-merge-requests/<uuid:pk>/reject/",  CustomerMergeRejectView.as_view(),      name="merge-reject"),
]
