# =============================================================================
# RestaurantFlow — Marketing DRF Permissions
# Phase 18
# =============================================================================

from rest_framework.permissions import BasePermission
from accounts import access as acl
from marketing.constants import (
    PERM_MARKETING_DASHBOARD_VIEW, PERM_CAMPAIGN_VIEW,
    PERM_PROMOTION_VIEW, PERM_ANALYTICS_VIEW,
    PERM_SETTINGS_VIEW, PERM_SETTINGS_MANAGE,
)


class HasMarketingDashboardPermission(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and acl.has_permission(request.user, PERM_MARKETING_DASHBOARD_VIEW)
        )


class HasCampaignViewPermission(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and acl.has_permission(request.user, PERM_CAMPAIGN_VIEW)
        )


class HasPromotionViewPermission(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and acl.has_permission(request.user, PERM_PROMOTION_VIEW)
        )


class HasAnalyticsViewPermission(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and acl.has_permission(request.user, PERM_ANALYTICS_VIEW)
        )


class HasSettingsViewPermission(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and acl.has_permission(request.user, PERM_SETTINGS_VIEW)
        )


class HasSettingsManagePermission(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and acl.has_permission(request.user, PERM_SETTINGS_MANAGE)
        )
