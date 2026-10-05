# =============================================================================
# RestaurantFlow — Marketing Views
# Phase 18
#
# Thin views — all business logic in services/selectors.
# Every endpoint: Authentication + Permission + Company/Restaurant scope.
# =============================================================================

import logging
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination

from accounts import access as acl
from marketing.access import (
    get_accessible_campaigns, get_accessible_promotions,
    can_access_campaign, can_access_promotion,
)
from marketing.campaign_services import CampaignService, CampaignApprovalService
from marketing.audience_services import CampaignAudienceService
from marketing.promotion_services import (
    PromotionService, PromotionEligibilityService, PromotionUsageService,
)
from marketing.scheduling_services import CampaignSchedulingService
from marketing.selectors import (
    get_campaigns, get_campaign_by_id, get_promotions,
    get_promotion_by_id, get_campaign_analytics, get_dashboard_stats,
)
from marketing.serializers import (
    CampaignListSerializer, CampaignDetailSerializer,
    CampaignCreateSerializer, CampaignUpdateSerializer,
    CampaignApprovalSerializer,
    CampaignAudienceSerializer, CampaignAudienceCreateSerializer,
    CampaignAudienceMemberSerializer,
    PromotionListSerializer, PromotionDetailSerializer,
    PromotionCreateSerializer, PromotionUpdateSerializer,
    PromotionRuleSerializer, PromotionRuleCreateSerializer,
    PromotionUsageSerializer,
    PromotionValidateRequestSerializer, PromotionValidateResponseSerializer,
    CampaignDeliverySerializer, CampaignConversionSerializer,
    MarketingSettingsSerializer,
)
from marketing.constants import (
    PERM_MARKETING_DASHBOARD_VIEW, PERM_CAMPAIGN_VIEW, PERM_CAMPAIGN_CREATE,
    PERM_CAMPAIGN_UPDATE, PERM_CAMPAIGN_SUBMIT, PERM_CAMPAIGN_APPROVE,
    PERM_CAMPAIGN_REJECT, PERM_CAMPAIGN_SCHEDULE, PERM_CAMPAIGN_PAUSE,
    PERM_CAMPAIGN_RESUME, PERM_CAMPAIGN_CANCEL,
    PERM_AUDIENCE_VIEW, PERM_AUDIENCE_MANAGE,
    PERM_PROMOTION_VIEW, PERM_PROMOTION_CREATE, PERM_PROMOTION_UPDATE,
    PERM_PROMOTION_ACTIVATE, PERM_PROMOTION_DEACTIVATE, PERM_PROMOTION_APPLY,
    PERM_ANALYTICS_VIEW, PERM_SETTINGS_VIEW, PERM_SETTINGS_MANAGE,
    CAMPAIGN_RUNNING, CAMPAIGN_PAUSED, CAMPAIGN_CANCELLED,
    CAMPAIGN_SCHEDULED, CAMPAIGN_PENDING_APPROVAL, CAMPAIGN_APPROVED,
)
from marketing.exceptions import (
    MarketingPermissionDenied, CampaignNotFound, PromotionNotFound,
)
from marketing.models import (
    MarketingCampaign, Promotion, CampaignApproval,
    CampaignAudience, PromotionRule, MarketingSettings,
)

logger = logging.getLogger("marketing")


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _require_perm(user, perm):
    if not acl.has_permission(user, perm):
        raise MarketingPermissionDenied(f"{perm} permission required.")


def _get_campaign_or_404(user, pk):
    campaign = get_campaign_by_id(user, pk)
    if not campaign:
        raise CampaignNotFound()
    return campaign


def _get_promotion_or_404(user, pk):
    promotion = get_promotion_by_id(user, pk)
    if not promotion:
        raise PromotionNotFound()
    return promotion


# =============================================================================
# Dashboard
# =============================================================================

class MarketingDashboardView(APIView):
    """GET /api/marketing/dashboard/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_perm(request.user, PERM_MARKETING_DASHBOARD_VIEW)

        # Determine company scope from user assignments
        orgs = list(acl.get_accessible_organizations(request.user))
        if not orgs:
            return Response({"detail": "No accessible organizations."}, status=status.HTTP_403_FORBIDDEN)

        company = orgs[0]
        restaurant_id = request.query_params.get("restaurant")
        restaurant = None
        if restaurant_id:
            from organizations.models import Restaurant
            try:
                restaurant = Restaurant.objects.get(pk=restaurant_id)
                if not acl.can_access_restaurant(request.user, restaurant):
                    return Response({"detail": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
            except Restaurant.DoesNotExist:
                pass

        data = get_dashboard_stats(company, restaurant=restaurant)
        return Response(data)


# =============================================================================
# Campaign CRUD
# =============================================================================

class CampaignListCreateView(APIView):
    """
    GET  /api/marketing/campaigns/
    POST /api/marketing/campaigns/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_perm(request.user, PERM_CAMPAIGN_VIEW)

        status_filter = request.query_params.get("status")
        type_filter = request.query_params.get("campaign_type")
        restaurant_id = request.query_params.get("restaurant")
        search = request.query_params.get("search")

        qs = get_campaigns(
            request.user,
            status=status_filter,
            campaign_type=type_filter,
        )
        if restaurant_id:
            from django.db.models import Q
            qs = qs.filter(
                Q(restaurant_id=restaurant_id) | Q(restaurant__isnull=True)
            )
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(name__icontains=search) | Q(code__icontains=search)
            )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = CampaignListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        _require_perm(request.user, PERM_CAMPAIGN_CREATE)

        serializer = CampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve company + restaurant
        orgs = list(acl.get_accessible_organizations(request.user))
        if not orgs:
            return Response({"detail": "No accessible organizations."}, status=403)
        company = orgs[0]

        restaurant = None
        if data.get("restaurant"):
            from organizations.models import Restaurant
            try:
                restaurant = Restaurant.objects.get(pk=data["restaurant"], organization=company)
                if not acl.can_access_restaurant(request.user, restaurant):
                    return Response({"detail": "Access denied to restaurant."}, status=403)
            except Restaurant.DoesNotExist:
                return Response({"restaurant": "Not found."}, status=400)

        branch = None
        if data.get("branch"):
            from organizations.models import Branch
            try:
                branch = Branch.objects.get(pk=data["branch"])
                if not acl.can_access_branch(request.user, branch):
                    return Response({"detail": "Access denied to branch."}, status=403)
            except Branch.DoesNotExist:
                return Response({"branch": "Not found."}, status=400)

        campaign = CampaignService.create_campaign(
            company=company,
            restaurant=restaurant,
            branch=branch,
            data=data,
            actor=request.user,
        )
        return Response(CampaignDetailSerializer(campaign).data, status=status.HTTP_201_CREATED)


class CampaignDetailView(APIView):
    """
    GET   /api/marketing/campaigns/{id}/
    PATCH /api/marketing/campaigns/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _require_perm(request.user, PERM_CAMPAIGN_VIEW)
        campaign = _get_campaign_or_404(request.user, pk)
        return Response(CampaignDetailSerializer(campaign).data)

    def patch(self, request, pk):
        _require_perm(request.user, PERM_CAMPAIGN_UPDATE)
        campaign = _get_campaign_or_404(request.user, pk)
        serializer = CampaignUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        campaign = CampaignService.update_campaign(
            campaign, data=serializer.validated_data, actor=request.user
        )
        return Response(CampaignDetailSerializer(campaign).data)


# =============================================================================
# Campaign actions (submit / approve / reject / schedule / pause / resume / cancel)
# =============================================================================

class CampaignSubmitView(APIView):
    """POST /api/marketing/campaigns/{id}/submit/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campaign = _get_campaign_or_404(request.user, pk)
        approval = CampaignApprovalService.submit_for_approval(campaign, request.user)
        return Response(CampaignApprovalSerializer(approval).data)


class CampaignApproveView(APIView):
    """POST /api/marketing/campaigns/{id}/approve/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campaign = _get_campaign_or_404(request.user, pk)
        approval = CampaignApproval.objects.filter(
            campaign=campaign, status="PENDING"
        ).order_by("-requested_at").first()
        if not approval:
            return Response({"detail": "No pending approval request found."}, status=400)
        note = request.data.get("note", "")
        approval = CampaignApprovalService.approve(campaign, approval, actor=request.user, note=note)
        return Response(CampaignApprovalSerializer(approval).data)


class CampaignRejectView(APIView):
    """POST /api/marketing/campaigns/{id}/reject/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campaign = _get_campaign_or_404(request.user, pk)
        approval = CampaignApproval.objects.filter(
            campaign=campaign, status="PENDING"
        ).order_by("-requested_at").first()
        if not approval:
            return Response({"detail": "No pending approval request found."}, status=400)
        note = request.data.get("note", "")
        if not note:
            return Response({"note": "A rejection reason is required."}, status=400)
        approval = CampaignApprovalService.reject(campaign, approval, actor=request.user, note=note)
        return Response(CampaignApprovalSerializer(approval).data)


class CampaignScheduleView(APIView):
    """POST /api/marketing/campaigns/{id}/schedule/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campaign = _get_campaign_or_404(request.user, pk)
        campaign = CampaignSchedulingService.schedule(campaign, actor=request.user)
        return Response(CampaignDetailSerializer(campaign).data)


class CampaignPauseView(APIView):
    """POST /api/marketing/campaigns/{id}/pause/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campaign = _get_campaign_or_404(request.user, pk)
        campaign = CampaignService.transition_status(
            campaign, new_status=CAMPAIGN_PAUSED, actor=request.user
        )
        return Response(CampaignDetailSerializer(campaign).data)


class CampaignResumeView(APIView):
    """POST /api/marketing/campaigns/{id}/resume/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campaign = _get_campaign_or_404(request.user, pk)
        campaign = CampaignService.transition_status(
            campaign, new_status=CAMPAIGN_SCHEDULED, actor=request.user
        )
        return Response(CampaignDetailSerializer(campaign).data)


class CampaignCancelView(APIView):
    """POST /api/marketing/campaigns/{id}/cancel/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        campaign = _get_campaign_or_404(request.user, pk)
        reason = request.data.get("reason", "")
        campaign = CampaignService.transition_status(
            campaign, new_status=CAMPAIGN_CANCELLED, actor=request.user, reason=reason
        )
        return Response(CampaignDetailSerializer(campaign).data)


# =============================================================================
# Campaign Audience
# =============================================================================

class CampaignAudienceView(APIView):
    """
    GET  /api/marketing/campaigns/{id}/audience/
    POST /api/marketing/campaigns/{id}/audience/  (create audience definition)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _require_perm(request.user, PERM_AUDIENCE_VIEW)
        campaign = _get_campaign_or_404(request.user, pk)
        audiences = CampaignAudience.objects.filter(campaign=campaign)
        return Response(CampaignAudienceSerializer(audiences, many=True).data)

    def post(self, request, pk):
        _require_perm(request.user, PERM_AUDIENCE_MANAGE)
        campaign = _get_campaign_or_404(request.user, pk)
        serializer = CampaignAudienceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        audience = CampaignAudienceService.create_audience(
            campaign,
            audience_type=d["audience_type"],
            criteria=d.get("criteria", {}),
            actor=request.user,
        )
        return Response(CampaignAudienceSerializer(audience).data, status=201)


class CampaignAudienceGenerateView(APIView):
    """POST /api/marketing/campaigns/{id}/audience/generate/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        _require_perm(request.user, PERM_AUDIENCE_MANAGE)
        campaign = _get_campaign_or_404(request.user, pk)

        audience = CampaignAudience.objects.filter(campaign=campaign).first()
        if not audience:
            return Response({"detail": "No audience definition found. Create one first."}, status=400)

        # For large campaigns, do asynchronously via Celery
        try:
            from marketing.tasks import generate_campaign_audience
            generate_campaign_audience.delay(
                campaign_id=str(campaign.pk),
                audience_id=str(audience.pk),
            )
            return Response({"detail": "Audience generation queued.", "campaign_id": str(campaign.pk)})
        except Exception:
            # Fallback: synchronous generation
            count = CampaignAudienceService.generate_audience_members(
                campaign, audience, actor=request.user
            )
            return Response({"detail": f"Generated {count} eligible audience members."})


class CampaignAudienceMembersView(APIView):
    """GET /api/marketing/campaigns/{id}/audience/members/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _require_perm(request.user, PERM_AUDIENCE_VIEW)
        campaign = _get_campaign_or_404(request.user, pk)
        from marketing.models import CampaignAudienceMember
        qs = CampaignAudienceMember.objects.filter(
            campaign=campaign
        ).select_related("customer").order_by("-added_at")

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CampaignAudienceMemberSerializer(page, many=True).data
        )


# =============================================================================
# Campaign Analytics
# =============================================================================

class CampaignAnalyticsView(APIView):
    """GET /api/marketing/campaigns/{id}/analytics/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _require_perm(request.user, PERM_ANALYTICS_VIEW)
        campaign = _get_campaign_or_404(request.user, pk)
        data = get_campaign_analytics(campaign)
        return Response(data)


# =============================================================================
# Conversions
# =============================================================================

class CampaignConversionsView(APIView):
    """GET /api/marketing/conversions/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_perm(request.user, PERM_ANALYTICS_VIEW)
        from marketing.models import CampaignConversion
        accessible = get_accessible_campaigns(request.user)
        qs = CampaignConversion.objects.filter(
            campaign__in=accessible
        ).select_related("campaign", "customer", "order", "promotion").order_by("-converted_at")

        campaign_id = request.query_params.get("campaign")
        if campaign_id:
            qs = qs.filter(campaign_id=campaign_id)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CampaignConversionSerializer(page, many=True).data
        )


# =============================================================================
# Promotion CRUD
# =============================================================================

class PromotionListCreateView(APIView):
    """
    GET  /api/marketing/promotions/
    POST /api/marketing/promotions/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _require_perm(request.user, PERM_PROMOTION_VIEW)

        is_active = request.query_params.get("is_active")
        search = request.query_params.get("search")
        restaurant_id = request.query_params.get("restaurant")

        restaurant = None
        if restaurant_id:
            from organizations.models import Restaurant
            try:
                restaurant = Restaurant.objects.get(pk=restaurant_id)
            except Restaurant.DoesNotExist:
                pass

        active_filter = None
        if is_active is not None:
            active_filter = is_active.lower() == "true"

        qs = get_promotions(request.user, restaurant=restaurant, is_active=active_filter)
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(name__icontains=search) | Q(code__icontains=search))

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(PromotionListSerializer(page, many=True).data)

    def post(self, request):
        _require_perm(request.user, PERM_PROMOTION_CREATE)

        serializer = PromotionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        orgs = list(acl.get_accessible_organizations(request.user))
        if not orgs:
            return Response({"detail": "No accessible organizations."}, status=403)
        company = orgs[0]

        restaurant = None
        if data.get("restaurant"):
            from organizations.models import Restaurant
            try:
                restaurant = Restaurant.objects.get(pk=data["restaurant"])
                if not acl.can_access_restaurant(request.user, restaurant):
                    return Response({"detail": "Access denied."}, status=403)
            except Restaurant.DoesNotExist:
                return Response({"restaurant": "Not found."}, status=400)

        branch = None
        if data.get("branch"):
            from organizations.models import Branch
            try:
                branch = Branch.objects.get(pk=data["branch"])
            except Branch.DoesNotExist:
                return Response({"branch": "Not found."}, status=400)

        promotion = PromotionService.create_promotion(
            company=company,
            restaurant=restaurant,
            branch=branch,
            data=data,
            actor=request.user,
        )
        return Response(PromotionDetailSerializer(promotion).data, status=201)


class PromotionDetailView(APIView):
    """
    GET   /api/marketing/promotions/{id}/
    PATCH /api/marketing/promotions/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _require_perm(request.user, PERM_PROMOTION_VIEW)
        promotion = _get_promotion_or_404(request.user, pk)
        return Response(PromotionDetailSerializer(promotion).data)

    def patch(self, request, pk):
        _require_perm(request.user, PERM_PROMOTION_UPDATE)
        promotion = _get_promotion_or_404(request.user, pk)
        serializer = PromotionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        promotion = PromotionService.update_promotion(
            promotion, data=serializer.validated_data, actor=request.user
        )
        return Response(PromotionDetailSerializer(promotion).data)


class PromotionActivateView(APIView):
    """POST /api/marketing/promotions/{id}/activate/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        promotion = _get_promotion_or_404(request.user, pk)
        promotion = PromotionService.activate(promotion, request.user)
        return Response(PromotionDetailSerializer(promotion).data)


class PromotionDeactivateView(APIView):
    """POST /api/marketing/promotions/{id}/deactivate/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        promotion = _get_promotion_or_404(request.user, pk)
        promotion = PromotionService.deactivate(promotion, request.user)
        return Response(PromotionDetailSerializer(promotion).data)


class PromotionUsageListView(APIView):
    """GET /api/marketing/promotions/{id}/usage/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _require_perm(request.user, PERM_PROMOTION_VIEW)
        promotion = _get_promotion_or_404(request.user, pk)
        from marketing.models import PromotionUsage
        qs = PromotionUsage.objects.filter(promotion=promotion).select_related(
            "customer", "order", "bill"
        ).order_by("-created_at")
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(PromotionUsageSerializer(page, many=True).data)


class PromotionRuleView(APIView):
    """
    GET  /api/marketing/promotions/{id}/rules/
    POST /api/marketing/promotions/{id}/rules/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        _require_perm(request.user, PERM_PROMOTION_VIEW)
        promotion = _get_promotion_or_404(request.user, pk)
        rules = PromotionRule.objects.filter(promotion=promotion).order_by("priority")
        return Response(PromotionRuleSerializer(rules, many=True).data)

    def post(self, request, pk):
        _require_perm(request.user, PERM_PROMOTION_UPDATE)
        promotion = _get_promotion_or_404(request.user, pk)
        serializer = PromotionRuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        rule = PromotionRule.objects.create(
            promotion=promotion,
            rule_type=d["rule_type"],
            configuration=d.get("configuration", {}),
            priority=d.get("priority", 10),
            is_active=d.get("is_active", True),
        )
        return Response(PromotionRuleSerializer(rule).data, status=201)


# =============================================================================
# Promotion Validation
# =============================================================================

class PromotionValidateView(APIView):
    """POST /api/marketing/promotions/validate/"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PromotionValidateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Resolve objects from IDs
        customer = None
        if data.get("customer_id"):
            from crm.models import Customer
            try:
                customer = Customer.objects.get(pk=data["customer_id"])
                from marketing.access import get_accessible_campaigns  # noqa
                from crm.access import can_access_customer
                if not can_access_customer(request.user, customer):
                    return Response({"detail": "Access denied."}, status=403)
            except Customer.DoesNotExist:
                return Response({"customer_id": "Customer not found."}, status=400)

        order = None
        if data.get("order_id"):
            from orders.models import Order
            try:
                order = Order.objects.get(pk=data["order_id"])
            except Order.DoesNotExist:
                return Response({"order_id": "Order not found."}, status=400)

        branch = None
        if data.get("branch_id"):
            from organizations.models import Branch
            try:
                branch = Branch.objects.get(pk=data["branch_id"])
            except Branch.DoesNotExist:
                pass

        promotion = None
        if data.get("promotion_id"):
            promotion = get_promotion_by_id(request.user, data["promotion_id"])

        result = PromotionEligibilityService.validate(
            promotion_code=data.get("promotion_code", ""),
            promotion=promotion,
            customer=customer,
            order=order,
            branch=branch,
            order_subtotal=data.get("order_subtotal", 0),
        )
        return Response(PromotionValidateResponseSerializer(result).data)


# =============================================================================
# Marketing Settings
# =============================================================================

class MarketingSettingsView(APIView):
    """
    GET   /api/marketing/settings/
    PATCH /api/marketing/settings/
    """
    permission_classes = [IsAuthenticated]

    def _get_restaurant(self, request):
        restaurant_id = request.query_params.get("restaurant") or request.data.get("restaurant")
        if not restaurant_id:
            return None
        from organizations.models import Restaurant
        try:
            r = Restaurant.objects.get(pk=restaurant_id)
            if not acl.can_access_restaurant(request.user, r):
                return None
            return r
        except Restaurant.DoesNotExist:
            return None

    def get(self, request):
        _require_perm(request.user, PERM_SETTINGS_VIEW)
        restaurant = self._get_restaurant(request)
        if not restaurant:
            return Response({"detail": "Restaurant not found or access denied."}, status=400)
        settings_obj, _ = MarketingSettings.objects.get_or_create(
            restaurant=restaurant,
            defaults={"frequency_limit_enabled": True},
        )
        return Response(MarketingSettingsSerializer(settings_obj).data)

    def patch(self, request):
        _require_perm(request.user, PERM_SETTINGS_MANAGE)
        restaurant = self._get_restaurant(request)
        if not restaurant:
            return Response({"detail": "Restaurant not found or access denied."}, status=400)
        settings_obj, _ = MarketingSettings.objects.get_or_create(
            restaurant=restaurant,
            defaults={"frequency_limit_enabled": True},
        )
        serializer = MarketingSettingsSerializer(
            settings_obj, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
