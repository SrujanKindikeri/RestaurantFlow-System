# =============================================================================
# RestaurantFlow — CRM Views
# Phase 17
#
# Views are THIN — all business logic lives in services.
# Views: validate input → call service/selector → return response.
#
# All endpoints enforce:
#   - Authentication
#   - Permission check (via HasPermission factory)
#   - Company / restaurant / branch scope (via access layer)
#   - IDOR prevention (get_object → 404 if out of scope)
# =============================================================================

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from accounts import access as acl
from accounts.permissions import HasPermission
import crm.access as crm_acl
from crm.constants import (
    PERM_CUSTOMER_VIEW, PERM_CUSTOMER_CREATE, PERM_CUSTOMER_UPDATE,
    PERM_CUSTOMER_BLOCK, PERM_CUSTOMER_LINK,
    PERM_CUSTOMER_HISTORY_VIEW, PERM_CUSTOMER_CONTACT_VIEW,
    PERM_CUSTOMER_TAG_VIEW, PERM_CUSTOMER_TAG_MANAGE,
    PERM_CUSTOMER_SEGMENT_VIEW, PERM_CUSTOMER_SEGMENT_MANAGE,
    PERM_CUSTOMER_PREFERENCE_VIEW, PERM_CUSTOMER_PREFERENCE_MANAGE,
    PERM_CUSTOMER_MERGE_REQUEST, PERM_CUSTOMER_MERGE_APPROVE,
    PERM_LOYALTY_VIEW, PERM_LOYALTY_MANAGE,
    PERM_REWARD_VIEW, PERM_REWARD_MANAGE, PERM_REWARD_REDEEM,
    PERM_FEEDBACK_VIEW, PERM_FEEDBACK_CREATE, PERM_FEEDBACK_MODERATE,
    PERM_CUSTOMER_CONSENT_VIEW, PERM_CUSTOMER_CONSENT_MANAGE,
    PERM_CRM_DASHBOARD_VIEW,
    CONSENT_GRANTED, CONSENT_REVOKED,
)
from crm.customer_services import (
    CustomerService, CustomerIdentityService,
    CustomerStatisticsService, CustomerTagService,
    CustomerMergeService,
)
from crm.loyalty_services import LoyaltyService, RewardService
from crm.feedback_services import FeedbackService, FeedbackModerationService
from crm.consent_services import CustomerConsentService
from crm.serializers import (
    CustomerListSerializer, CustomerDetailSerializer,
    CustomerCreateSerializer, CustomerUpdateSerializer,
    CustomerSearchSerializer, CustomerBlockSerializer,
    CustomerVisitSerializer,
    CustomerPreferenceSerializer,
    CustomerTagSerializer, CustomerTagAssignmentSerializer,
    CustomerSegmentSerializer,
    LoyaltyProgramSerializer, LoyaltyAccountSerializer,
    LoyaltyTransactionSerializer, LoyaltyRewardSerializer,
    RewardRedemptionSerializer,
    CustomerFeedbackSerializer, CustomerFeedbackCreateSerializer,
    FeedbackModerationSerializer, FeedbackModerationActionSerializer,
    CustomerConsentSerializer, CustomerConsentUpdateSerializer,
    CustomerConsentHistorySerializer,
    CustomerMergeRequestSerializer, MergeRequestCreateSerializer,
    CustomerOrderHistorySerializer, CustomerSpendingSerializer,
)
import crm.selectors as selectors

logger = logging.getLogger("crm")


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


# =============================================================================
# Customer CRUD
# =============================================================================

class CustomerListCreateView(APIView):
    """GET /api/crm/customers/  POST /api/crm/customers/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_VIEW)]

    def get(self, request):
        filters = {
            "search":         request.query_params.get("search", ""),
            "is_active":      _parse_bool(request.query_params.get("is_active")),
            "is_blocked":     _parse_bool(request.query_params.get("is_blocked")),
            "restaurant_id":  request.query_params.get("restaurant_id"),
            "segment_code":   request.query_params.get("segment"),
            "tag_code":       request.query_params.get("tag"),
            "created_after":  request.query_params.get("created_after"),
            "created_before": request.query_params.get("created_before"),
        }
        # Drop None values
        filters = {k: v for k, v in filters.items() if v is not None}

        qs = selectors.get_customer_list(request.user, filters)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = CustomerListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_CUSTOMER_CREATE):
            raise PermissionDenied("customer.create permission required.")

        ser = CustomerCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        # Resolve restaurant and verify access
        from organizations.models import Restaurant
        restaurant = get_object_or_404(
            acl.get_accessible_restaurants(request.user),
            pk=data.pop("restaurant_id"),
        )

        # Identity check — resolve or create
        customer, created = CustomerIdentityService.resolve_or_create_customer(
            restaurant=restaurant, data=data, actor=request.user,
        )

        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(
            CustomerDetailSerializer(customer).data,
            status=response_status,
        )


class CustomerDetailView(APIView):
    """GET /api/crm/customers/{id}/  PATCH /api/crm/customers/{id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_VIEW)]

    def _get_customer(self, request, pk):
        customer = selectors.get_customer_detail(request.user, pk)
        if not customer:
            from crm.exceptions import CustomerNotFound
            raise CustomerNotFound()
        return customer

    def get(self, request, pk):
        customer = self._get_customer(request, pk)

        # Full PII only for users with contact.view
        if acl.has_permission(request.user, PERM_CUSTOMER_CONTACT_VIEW):
            serializer = CustomerDetailSerializer(customer)
        else:
            serializer = CustomerListSerializer(customer)

        return Response(serializer.data)

    def patch(self, request, pk):
        if not acl.has_permission(request.user, PERM_CUSTOMER_UPDATE):
            raise PermissionDenied("customer.update permission required.")

        customer = self._get_customer(request, pk)
        ser = CustomerUpdateSerializer(data=request.data, partial=True)
        ser.is_valid(raise_exception=True)

        # Handle block/unblock separately
        if "is_blocked" in ser.validated_data:
            if ser.validated_data["is_blocked"]:
                CustomerService.block_customer(
                    customer,
                    reason=ser.validated_data.get("blocked_reason", ""),
                    actor=request.user,
                )
            else:
                CustomerService.unblock_customer(customer, actor=request.user)
            ser.validated_data.pop("is_blocked", None)
            ser.validated_data.pop("blocked_reason", None)

        customer = CustomerService.update_customer(
            customer, ser.validated_data, actor=request.user
        )
        return Response(CustomerDetailSerializer(customer).data)


class CustomerSearchView(APIView):
    """GET /api/crm/customers/search/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_VIEW)]

    def get(self, request):
        q = request.query_params.get("q", "").strip()
        restaurant_id = request.query_params.get("restaurant_id")

        if not q:
            return Response({"results": []})

        filters = {"search": q}
        if restaurant_id:
            filters["restaurant_id"] = restaurant_id

        qs = selectors.get_customer_list(request.user, filters)[:20]
        return Response({"results": CustomerSearchSerializer(qs, many=True).data})


# =============================================================================
# Customer history sub-resources
# =============================================================================

class CustomerOrderHistoryView(APIView):
    """GET /api/crm/customers/{id}/orders/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_HISTORY_VIEW)]

    def get(self, request, pk):
        customer = _get_customer_or_404(request.user, pk)
        filters = {
            "date_from":  request.query_params.get("date_from"),
            "date_to":    request.query_params.get("date_to"),
            "branch_id":  request.query_params.get("branch_id"),
            "order_type": request.query_params.get("order_type"),
            "status":     request.query_params.get("status"),
        }
        filters = {k: v for k, v in filters.items() if v}
        qs = selectors.get_customer_order_history(customer, filters)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = CustomerOrderHistorySerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class CustomerVisitHistoryView(APIView):
    """GET /api/crm/customers/{id}/visits/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_HISTORY_VIEW)]

    def get(self, request, pk):
        customer = _get_customer_or_404(request.user, pk)
        filters = {
            "branch_id": request.query_params.get("branch_id"),
            "status":    request.query_params.get("status"),
        }
        filters = {k: v for k, v in filters.items() if v}
        qs = selectors.get_customer_visits(customer, filters)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CustomerVisitSerializer(page, many=True).data
        )


class CustomerSpendingView(APIView):
    """GET /api/crm/customers/{id}/spending/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_HISTORY_VIEW)]

    def get(self, request, pk):
        customer = _get_customer_or_404(request.user, pk)
        filters = {
            "date_from": request.query_params.get("date_from"),
            "date_to":   request.query_params.get("date_to"),
            "branch_id": request.query_params.get("branch_id"),
        }
        filters = {k: v for k, v in filters.items() if v}
        qs = selectors.get_customer_spending_history(customer, filters)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CustomerSpendingSerializer(page, many=True).data
        )


# =============================================================================
# Customer Tags
# =============================================================================

class CustomerTagsView(APIView):
    """POST /api/crm/customers/{id}/tags/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_TAG_VIEW)]

    def get(self, request, pk):
        customer = _get_customer_or_404(request.user, pk)
        from crm.models import CustomerTagAssignment
        assignments = CustomerTagAssignment.objects.filter(
            customer=customer, is_active=True
        ).select_related("tag")
        return Response(CustomerTagAssignmentSerializer(assignments, many=True).data)

    def post(self, request, pk):
        if not acl.has_permission(request.user, PERM_CUSTOMER_TAG_MANAGE):
            raise PermissionDenied("customer.tag.manage required.")
        customer = _get_customer_or_404(request.user, pk)
        ser = CustomerTagAssignmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        from crm.models import CustomerTag
        tag = get_object_or_404(
            crm_acl.get_accessible_tags(request.user),
            pk=ser.validated_data["tag_id"],
        )
        assignment = CustomerTagService.assign_tag(customer, tag, actor=request.user)
        return Response(
            CustomerTagAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class CustomerTagDeleteView(APIView):
    """DELETE /api/crm/customers/{id}/tags/{tag_id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_TAG_MANAGE)]

    def delete(self, request, pk, tag_id):
        customer = _get_customer_or_404(request.user, pk)
        from crm.models import CustomerTag
        tag = get_object_or_404(
            crm_acl.get_accessible_tags(request.user), pk=tag_id
        )
        CustomerTagService.remove_tag(customer, tag, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# =============================================================================
# Customer Loyalty
# =============================================================================

class CustomerLoyaltyView(APIView):
    """GET /api/crm/customers/{id}/loyalty/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_LOYALTY_VIEW)]

    def get(self, request, pk):
        customer = _get_customer_or_404(request.user, pk)
        accounts = selectors.get_customer_loyalty(customer)
        return Response(LoyaltyAccountSerializer(accounts, many=True).data)


class CustomerRewardsView(APIView):
    """GET /api/crm/customers/{id}/rewards/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_REWARD_VIEW)]

    def get(self, request, pk):
        customer = _get_customer_or_404(request.user, pk)
        redemptions = selectors.get_customer_rewards(customer)
        return Response(RewardRedemptionSerializer(redemptions, many=True).data)


class RewardRedeemView(APIView):
    """POST /api/crm/customers/{id}/rewards/{reward_id}/redeem/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_REWARD_REDEEM)]

    def post(self, request, pk, reward_id):
        customer = _get_customer_or_404(request.user, pk)
        from crm.models import LoyaltyReward, LoyaltyAccount
        reward = get_object_or_404(
            crm_acl.get_accessible_rewards(request.user), pk=reward_id
        )
        # Find the account for the matching program
        account = LoyaltyAccount.objects.filter(
            customer=customer,
            loyalty_account__loyalty_program__restaurant=reward.restaurant,
        ).first()
        if not account:
            account = LoyaltyAccount.objects.filter(customer=customer).first()
        if not account:
            raise ValidationError("No loyalty account found for this customer.")

        redemption = RewardService.redeem_reward(
            customer=customer,
            reward=reward,
            loyalty_account=account,
            actor=request.user,
        )
        return Response(
            RewardRedemptionSerializer(redemption).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# Loyalty Program management
# =============================================================================

class LoyaltyProgramView(APIView):
    """GET /api/crm/loyalty/program/   POST /api/crm/loyalty/program/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_LOYALTY_VIEW)]

    def get(self, request):
        programs = crm_acl.get_accessible_loyalty_programs(request.user)
        return Response(LoyaltyProgramSerializer(programs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_LOYALTY_MANAGE):
            raise PermissionDenied("loyalty.manage permission required.")
        ser = LoyaltyProgramSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        from organizations.models import Restaurant
        restaurant_id = request.data.get("restaurant_id")
        restaurant = get_object_or_404(
            acl.get_accessible_restaurants(request.user), pk=restaurant_id
        )

        from crm.models import LoyaltyProgram
        program = LoyaltyProgram.objects.create(
            restaurant=restaurant, **ser.validated_data
        )
        return Response(
            LoyaltyProgramSerializer(program).data, status=status.HTTP_201_CREATED
        )


# =============================================================================
# Rewards management
# =============================================================================

class RewardListCreateView(APIView):
    """GET /api/crm/rewards/  POST /api/crm/rewards/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_REWARD_VIEW)]

    def get(self, request):
        qs = crm_acl.get_accessible_rewards(request.user)
        if request.query_params.get("active_only"):
            qs = qs.filter(is_active=True)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(LoyaltyRewardSerializer(page, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_REWARD_MANAGE):
            raise PermissionDenied("reward.manage permission required.")
        ser = LoyaltyRewardSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        restaurant_id = request.data.get("restaurant_id")
        from organizations.models import Restaurant
        restaurant = get_object_or_404(
            acl.get_accessible_restaurants(request.user), pk=restaurant_id
        )
        reward = RewardService.create_reward(restaurant, request.data, actor=request.user)
        return Response(LoyaltyRewardSerializer(reward).data, status=status.HTTP_201_CREATED)


class RewardDetailView(APIView):
    """PATCH /api/crm/rewards/{id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_REWARD_MANAGE)]

    def patch(self, request, pk):
        reward = get_object_or_404(crm_acl.get_accessible_rewards(request.user), pk=pk)
        ser = LoyaltyRewardSerializer(reward, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


# =============================================================================
# Segment management
# =============================================================================

class SegmentListCreateView(APIView):
    """GET /api/crm/segments/  POST /api/crm/segments/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_SEGMENT_VIEW)]

    def get(self, request):
        qs = crm_acl.get_accessible_segments(request.user)
        return Response(CustomerSegmentSerializer(qs, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_CUSTOMER_SEGMENT_MANAGE):
            raise PermissionDenied("customer.segment.manage required.")
        ser = CustomerSegmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        restaurant_id = request.data.get("restaurant_id")
        from organizations.models import Restaurant
        restaurant = get_object_or_404(
            acl.get_accessible_restaurants(request.user), pk=restaurant_id
        )
        from crm.models import CustomerSegment
        segment = CustomerSegment.objects.create(restaurant=restaurant, **ser.validated_data)
        return Response(CustomerSegmentSerializer(segment).data, status=status.HTTP_201_CREATED)


class SegmentDetailView(APIView):
    """PATCH /api/crm/segments/{id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_SEGMENT_MANAGE)]

    def patch(self, request, pk):
        segment = get_object_or_404(crm_acl.get_accessible_segments(request.user), pk=pk)
        ser = CustomerSegmentSerializer(segment, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


# =============================================================================
# Feedback
# =============================================================================

class FeedbackListCreateView(APIView):
    """GET /api/crm/feedback/  POST /api/crm/feedback/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_FEEDBACK_VIEW)]

    def get(self, request):
        filters = {
            "branch_id": request.query_params.get("branch_id"),
            "rating":    request.query_params.get("rating"),
            "status":    request.query_params.get("status"),
            "date_from": request.query_params.get("date_from"),
            "date_to":   request.query_params.get("date_to"),
        }
        filters = {k: v for k, v in filters.items() if v}
        qs = selectors.get_feedback_list(request.user, filters)
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            CustomerFeedbackSerializer(page, many=True).data
        )

    def post(self, request):
        if not acl.has_permission(request.user, PERM_FEEDBACK_CREATE):
            raise PermissionDenied("feedback.create required.")

        ser = CustomerFeedbackCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        from organizations.models import Restaurant, Branch
        restaurant = get_object_or_404(
            acl.get_accessible_restaurants(request.user), pk=d["restaurant_id"]
        )
        branch = None
        if d.get("branch_id"):
            branch = get_object_or_404(Branch, pk=d["branch_id"], restaurant=restaurant)

        order = None
        if d.get("order_id"):
            from orders.models import Order
            order = get_object_or_404(Order, pk=d["order_id"], branch__restaurant=restaurant)

        # Customer from the request user (if they are the customer)
        # or from the order link
        customer = None
        if order and order.customer_id:
            customer = order.customer

        feedback = FeedbackService.create_feedback(
            data={
                "customer": customer,
                "restaurant": restaurant,
                "branch": branch,
                "order": order,
                "rating": d["rating"],
                "service_rating": d.get("service_rating"),
                "food_rating": d.get("food_rating"),
                "ambience_rating": d.get("ambience_rating"),
                "comment": d.get("comment", ""),
            },
            actor=request.user,
        )
        return Response(
            CustomerFeedbackSerializer(feedback).data,
            status=status.HTTP_201_CREATED,
        )


class FeedbackDetailView(APIView):
    """GET /api/crm/feedback/{id}/  PATCH /api/crm/feedback/{id}/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_FEEDBACK_VIEW)]

    def get(self, request, pk):
        from crm.models import CustomerFeedback
        feedback = get_object_or_404(
            crm_acl.get_accessible_feedback(request.user), pk=pk
        )
        return Response(CustomerFeedbackSerializer(feedback).data)

    def patch(self, request, pk):
        from crm.models import CustomerFeedback
        feedback = get_object_or_404(
            crm_acl.get_accessible_feedback(request.user), pk=pk
        )
        feedback = FeedbackService.update_feedback(
            feedback, request.data, actor=request.user
        )
        return Response(CustomerFeedbackSerializer(feedback).data)


class FeedbackModerateView(APIView):
    """POST /api/crm/feedback/{id}/moderate/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_FEEDBACK_MODERATE)]

    def post(self, request, pk):
        feedback = get_object_or_404(
            crm_acl.get_accessible_feedback(request.user), pk=pk
        )
        ser = FeedbackModerationActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        moderation = FeedbackModerationService.moderate_feedback(
            feedback=feedback,
            status=d["status"],
            note=d.get("moderation_note", ""),
            actor=request.user,
        )

        if d.get("create_central_issue"):
            FeedbackModerationService.create_central_issue_from_feedback(
                feedback, actor=request.user
            )

        return Response(FeedbackModerationSerializer(moderation).data)


# =============================================================================
# Consents
# =============================================================================

class ConsentListView(APIView):
    """GET /api/crm/consents/  (scoped to a customer)"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_CONSENT_VIEW)]

    def get(self, request):
        customer_id = request.query_params.get("customer_id")
        if not customer_id:
            return Response({"error": True, "message": "customer_id required."}, status=400)
        customer = _get_customer_or_404(request.user, customer_id)
        from crm.models import CustomerConsent
        consents = CustomerConsent.objects.filter(customer=customer)
        return Response(CustomerConsentSerializer(consents, many=True).data)

    def post(self, request):
        if not acl.has_permission(request.user, PERM_CUSTOMER_CONSENT_MANAGE):
            raise PermissionDenied("customer.consent.manage required.")
        ser = CustomerConsentUpdateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        customer_id = request.data.get("customer_id")
        customer = _get_customer_or_404(request.user, customer_id)

        if d["status"] == CONSENT_GRANTED:
            consent = CustomerConsentService.grant_consent(
                customer, d["consent_type"], source=d.get("source", "STAFF"),
                actor=request.user,
            )
        else:
            consent = CustomerConsentService.revoke_consent(
                customer, d["consent_type"], source=d.get("source", "STAFF"),
                actor=request.user,
            )
        return Response(CustomerConsentSerializer(consent).data)


# =============================================================================
# Customer Merge Requests
# =============================================================================

class CustomerMergeRequestListCreateView(APIView):
    """POST /api/crm/customer-merge-requests/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_MERGE_REQUEST)]

    def post(self, request):
        ser = MergeRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        source = _get_customer_or_404(request.user, d["source_customer_id"])
        target = _get_customer_or_404(request.user, d["target_customer_id"])

        merge_request = CustomerMergeService.request_merge(
            source_customer=source,
            target_customer=target,
            reason=d["reason"],
            actor=request.user,
        )
        return Response(
            CustomerMergeRequestSerializer(merge_request).data,
            status=status.HTTP_201_CREATED,
        )


class CustomerMergeApproveView(APIView):
    """POST /api/crm/customer-merge-requests/{id}/approve/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_MERGE_APPROVE)]

    def post(self, request, pk):
        from crm.models import CustomerMergeRequest
        merge_request = get_object_or_404(CustomerMergeRequest, pk=pk)
        # Scope check
        if not crm_acl.can_access_customer(request.user, merge_request.source_customer):
            raise PermissionDenied()
        merge_request = CustomerMergeService.approve_merge(merge_request, actor=request.user)
        return Response(CustomerMergeRequestSerializer(merge_request).data)


class CustomerMergeRejectView(APIView):
    """POST /api/crm/customer-merge-requests/{id}/reject/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_MERGE_APPROVE)]

    def post(self, request, pk):
        from crm.models import CustomerMergeRequest
        merge_request = get_object_or_404(CustomerMergeRequest, pk=pk)
        if not crm_acl.can_access_customer(request.user, merge_request.source_customer):
            raise PermissionDenied()
        merge_request = CustomerMergeService.reject_merge(merge_request, actor=request.user)
        return Response(CustomerMergeRequestSerializer(merge_request).data)


# =============================================================================
# CRM Dashboard KPIs
# =============================================================================

class CRMDashboardView(APIView):
    """GET /api/crm/dashboard/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CRM_DASHBOARD_VIEW)]

    def get(self, request):
        restaurant_id = request.query_params.get("restaurant_id")
        from organizations.models import Restaurant
        restaurant = get_object_or_404(
            acl.get_accessible_restaurants(request.user), pk=restaurant_id
        ) if restaurant_id else acl.get_accessible_restaurants(request.user).first()

        if not restaurant:
            return Response({})

        kpis = selectors.get_crm_dashboard_kpis(restaurant)
        top_customers = selectors.get_top_customers(restaurant, limit=5)
        feedback_summary = selectors.get_feedback_summary(restaurant)

        return Response({
            "kpis": kpis,
            "top_customers": CustomerListSerializer(top_customers, many=True).data,
            "feedback_summary": feedback_summary,
        })


# =============================================================================
# Customer Preferences
# =============================================================================

class CustomerPreferenceView(APIView):
    """GET/PATCH /api/crm/customers/{id}/preferences/"""
    permission_classes = [IsAuthenticated, HasPermission(PERM_CUSTOMER_PREFERENCE_VIEW)]

    def get(self, request, pk):
        customer = _get_customer_or_404(request.user, pk)
        try:
            pref = customer.preference
        except Exception:
            return Response({})
        return Response(CustomerPreferenceSerializer(pref).data)

    def patch(self, request, pk):
        if not acl.has_permission(request.user, PERM_CUSTOMER_PREFERENCE_MANAGE):
            raise PermissionDenied("customer.preference.manage required.")
        customer = _get_customer_or_404(request.user, pk)
        from crm.models import CustomerPreference
        pref, _ = CustomerPreference.objects.get_or_create(
            customer=customer,
            defaults={"restaurant": customer.restaurant},
        )
        ser = CustomerPreferenceSerializer(pref, data=request.data, partial=True)
        ser.is_valid(raise_exception=True)
        ser.save()
        return Response(ser.data)


# =============================================================================
# Helpers
# =============================================================================

def _get_customer_or_404(user, pk):
    """Scope-safe customer lookup — raises 404 instead of 403 to prevent IDOR."""
    customer = crm_acl.get_accessible_customers(user).filter(pk=pk).first()
    if not customer:
        from crm.exceptions import CustomerNotFound
        raise CustomerNotFound()
    return customer


def _parse_bool(value):
    if value is None:
        return None
    return value.lower() in ("true", "1", "yes")
